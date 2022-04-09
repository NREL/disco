import time
import json
import logging
import pandas as pd

from jade.utils.timing_utils import track_timing, Timer
from jade.utils.utils import load_data, dump_data

from .thermal_upgrade_functions import *
from disco.models.upgrade_cost_analysis_generic_model import UpgradeResultModel
from disco import timer_stats_collector


logger = logging.getLogger(__name__)


@track_timing(timer_stats_collector)
def determine_thermal_upgrades(
    job_name,
    master_path,
    enable_pydss_solve,
    pydss_volt_var_model,
    thermal_config,
    line_upgrade_options_file,
    xfmr_upgrade_options_file,
    thermal_summary_file,
    thermal_upgrades_dss_filepath,
    output_json_line_upgrades_filepath,
    output_json_xfmr_upgrades_filepath,
    feeder_stats_json_file,
    ignore_switch=True,
    verbose=False
):
    start_time = time.time()
    logger.info( f"Simulation start time: {start_time}")   
    pydss_params = {"enable_pydss_solve": enable_pydss_solve, "pydss_volt_var_model": pydss_volt_var_model}
    # start upgrades
    simulation_params = reload_dss_circuit(dss_file_list=[master_path], commands_list=None, **pydss_params)
    timepoint_multipliers = thermal_config["timepoint_multipliers"]
    if timepoint_multipliers is not None:
        multiplier_type = "uniform"
    else:
        multiplier_type = "original"
    voltage_upper_limit = thermal_config["voltage_upper_limit"]
    voltage_lower_limit = thermal_config["voltage_lower_limit"]
    feeder_stats = {"before_upgrades": get_feeder_stats(dss)}  # save feeder stats
    dump_data(feeder_stats, feeder_stats_json_file, indent=4)
    if thermal_config["read_external_catalog"]:
        with open(thermal_config["external_catalog"]) as json_file:
            external_upgrades_technical_catalog = json.load(json_file)
        line_upgrade_options = pd.DataFrame.from_dict(external_upgrades_technical_catalog['line'])
        xfmr_upgrade_options = pd.DataFrame.from_dict(external_upgrades_technical_catalog['transformer'])
        # this will remove any duplicates if present
        line_upgrade_options = determine_available_line_upgrades(line_upgrade_options)
        xfmr_upgrade_options = determine_available_xfmr_upgrades(xfmr_upgrade_options)
    else:
        external_upgrades_technical_catalog = {}
        orig_lines_df = get_thermal_equipment_info(compute_loading=False, equipment_type="line")
        orig_xfmrs_df = get_thermal_equipment_info(compute_loading=False, equipment_type="transformer")
        line_upgrade_options = determine_available_line_upgrades(orig_lines_df)
        xfmr_upgrade_options = determine_available_xfmr_upgrades(orig_xfmrs_df)
        dump_data(line_upgrade_options.to_dict('records'), line_upgrade_options_file, indent=4)
        dump_data(xfmr_upgrade_options.to_dict('records'), xfmr_upgrade_options_file, indent=4)

    (
        initial_bus_voltages_df,
        initial_undervoltage_bus_list,
        initial_overvoltage_bus_list,
        initial_buses_with_violations,
    ) = get_bus_voltages(upper_limit=voltage_upper_limit, lower_limit=voltage_lower_limit, **simulation_params)
    initial_xfmr_loading_df = get_thermal_equipment_info(compute_loading=True, upper_limit=thermal_config["transformer_upper_limit"], 
                                                         equipment_type="transformer", timepoint_multipliers=timepoint_multipliers, 
                                                         multiplier_type=multiplier_type, **simulation_params)
    initial_line_loading_df = get_thermal_equipment_info(compute_loading=True, upper_limit=thermal_config["line_upper_limit"], 
                                                         equipment_type="line", ignore_switch=ignore_switch, multiplier_type=multiplier_type,
                                                         timepoint_multipliers=timepoint_multipliers, **simulation_params)
    
    initial_overloaded_xfmr_list = list(initial_xfmr_loading_df.loc[initial_xfmr_loading_df["status"] == 
                                                                    "overloaded"]["name"].unique())
    initial_overloaded_line_list = list(initial_line_loading_df.loc[initial_line_loading_df["status"] == 
                                                                    "overloaded"]["name"].unique())
    
    if len(initial_overloaded_xfmr_list) > 0 or len(initial_overloaded_line_list) > 0:
        upgrade_status = "Thermal Upgrades Required"  # status - whether upgrades done or not
    else:
        upgrade_status = "Thermal Upgrades not Required"  # status - whether upgrades done or not
    logger.info(upgrade_status)

    scenario = get_scenario_name(enable_pydss_solve, pydss_volt_var_model)
    initial_results = UpgradeResultModel(
        name=job_name,
        scenario=scenario,
        stage="Initial",
        upgrade_type="Thermal",
        # upgrade_status = upgrade_status,
        simulation_time_s = np.nan,
        thermal_violations_present=(len(initial_overloaded_xfmr_list) + len(initial_overloaded_line_list)) > 0,
        voltage_violations_present=(len(initial_undervoltage_bus_list) + len(initial_overvoltage_bus_list)) > 0,
        max_bus_voltage=initial_bus_voltages_df['Max per unit voltage'].max(),
        min_bus_voltage=initial_bus_voltages_df['Min per unit voltage'].min(),
        num_of_voltage_violation_buses=len(initial_undervoltage_bus_list) + len(initial_overvoltage_bus_list),
        num_of_overvoltage_violation_buses=len(initial_overvoltage_bus_list),
        voltage_upper_limit=voltage_upper_limit,
        num_of_undervoltage_violation_buses=len(initial_undervoltage_bus_list),
        voltage_lower_limit=voltage_lower_limit,
        max_line_loading=initial_line_loading_df['max_per_unit_loading'].max(),
        max_transformer_loading=initial_xfmr_loading_df['max_per_unit_loading'].max(),
        num_of_line_violations=len(initial_overloaded_line_list),
        line_upper_limit=thermal_config['line_upper_limit'],
        num_of_transformer_violations=len(initial_overloaded_xfmr_list),
        transformer_upper_limit=thermal_config['transformer_upper_limit']
    )
    temp_results = dict(initial_results)
    output_results = [temp_results]
    dump_data(output_results, thermal_summary_file, indent=4)
    
    # Mitigate thermal violations
    iteration_counter = 0
    # if number of violations is very high,  limit it to a small number
    max_upgrade_iteration = min(
        thermal_config["upgrade_iteration_threshold"],
        len(initial_overloaded_xfmr_list) + len(initial_overloaded_line_list),)
    logger.info(f"Maximum allowable number of thermal upgrade iterations: {max_upgrade_iteration}")
    commands_list = []
    line_upgrades_df = pd.DataFrame()
    xfmr_upgrades_df = pd.DataFrame()
    overloaded_line_list = initial_overloaded_line_list
    overloaded_xfmr_list = initial_overloaded_xfmr_list
    while (len(overloaded_line_list) > 0 or len(overloaded_xfmr_list) > 0) and (
        iteration_counter < max_upgrade_iteration):
        line_loading_df = get_thermal_equipment_info(compute_loading=True, upper_limit=thermal_config["line_upper_limit"], 
                                                    equipment_type="line", ignore_switch=ignore_switch, multiplier_type=multiplier_type,
                                                    timepoint_multipliers=timepoint_multipliers, **simulation_params)
        overloaded_line_list = list(line_loading_df.loc[line_loading_df["status"] == "overloaded"]["name"].unique())
        logger.info(f"Iteration_{iteration_counter}: Determined line loadings.")
        logger.info(f"Iteration_{iteration_counter}: Number of line violations: {len(overloaded_line_list)}")
        before_upgrade_num_line_violations = len(overloaded_line_list)
        
        if len(overloaded_line_list) > 0:            
            line_commands_list, temp_line_upgrades_df = correct_line_violations(
                line_loading_df=line_loading_df,
                line_design_pu=thermal_config["line_design_pu"],
                line_upgrade_options=line_upgrade_options,
                parallel_lines_limit=thermal_config["parallel_lines_limit"],
                external_upgrades_technical_catalog=external_upgrades_technical_catalog,)
            logger.info(f"Iteration_{iteration_counter}: Corrected line violations.")
            commands_list = commands_list + line_commands_list
            line_upgrades_df = line_upgrades_df.append(temp_line_upgrades_df)

        xfmr_loading_df = get_thermal_equipment_info(compute_loading=True, upper_limit=thermal_config["transformer_upper_limit"], 
                                                    equipment_type="transformer", timepoint_multipliers=timepoint_multipliers, 
                                                    multiplier_type=multiplier_type, **simulation_params)
        overloaded_xfmr_list = list(xfmr_loading_df.loc[xfmr_loading_df["status"] == "overloaded"]["name"].unique())
        logger.info(f"Iteration_{iteration_counter}: Determined xfmr loadings.")
        logger.info(f"Iteration_{iteration_counter}: Number of xfmr violations: {len(overloaded_xfmr_list)}")
        before_upgrade_num_xfmr_violations = len(overloaded_xfmr_list)
        
        if len(overloaded_xfmr_list) > 0:
            xfmr_commands_list, temp_xfmr_upgrades_df = correct_xfmr_violations(
                xfmr_loading_df=xfmr_loading_df,
                xfmr_design_pu=thermal_config["transformer_design_pu"],
                xfmr_upgrade_options=xfmr_upgrade_options,
                parallel_transformer_limit=thermal_config["parallel_transformer_limit"])
            logger.info(f"Iteration_{iteration_counter}: Corrected xfmr violations.")
            commands_list = commands_list + xfmr_commands_list
            xfmr_upgrades_df = xfmr_upgrades_df.append(temp_xfmr_upgrades_df)

        # compute loading after upgrades
        xfmr_loading_df = get_thermal_equipment_info(compute_loading=True, upper_limit=thermal_config["transformer_upper_limit"], 
                                                    equipment_type="transformer", timepoint_multipliers=timepoint_multipliers, 
                                                    multiplier_type=multiplier_type, **simulation_params)
        overloaded_xfmr_list = list(xfmr_loading_df.loc[xfmr_loading_df["status"] == "overloaded"]["name"].unique())
        line_loading_df = get_thermal_equipment_info(compute_loading=True, upper_limit=thermal_config["line_upper_limit"], 
                                                    equipment_type="line", ignore_switch=ignore_switch, multiplier_type=multiplier_type,
                                                    timepoint_multipliers=timepoint_multipliers, **simulation_params)
        overloaded_line_list = list(line_loading_df.loc[line_loading_df["status"] == "overloaded"]["name"].unique())
        
        if len(overloaded_line_list) > before_upgrade_num_line_violations:
            logger.debug(overloaded_line_list)
            logger.info("Write upgrades till this step to debug upgrades")
            write_text_file(string_list=commands_list, text_file_path=thermal_upgrades_dss_filepath)
            raise Exception(f"Line violations increased from {before_upgrade_num_line_violations} to {len(overloaded_line_list)} "
                f"during upgrade process")
        if len(overloaded_xfmr_list) > before_upgrade_num_xfmr_violations:
            logger.info("Write upgrades till this step to debug upgrades")
            write_text_file(string_list=commands_list, text_file_path=thermal_upgrades_dss_filepath)
            raise Exception(f"Xfmr violations increased from {before_upgrade_num_xfmr_violations} to {len(overloaded_xfmr_list)} "
                f"during upgrade process")

        num_violations_curr_itr = len(overloaded_xfmr_list) + len(overloaded_line_list)
        logger.info(f"Iteration_{iteration_counter}: Number of devices with violations after upgrades in this iteration: {num_violations_curr_itr}")
        iteration_counter += 1
        if iteration_counter > max_upgrade_iteration:
            logger.info(f"Max iterations limit reached, quitting algorithm. This means all thermal violations were not resolved with these limited iterations."
                        f"You can increase the Iteration limit in the thermal_config['upgrade_iteration_threshold']")
            break

    if iteration_counter > 0:
        logger.info(f"Multiple iterations ({iteration_counter}) were needed to resolve thermal violations."
                    f"This indicates that feeder was extremely overloaded to start with.")
    write_text_file(string_list=commands_list, text_file_path=thermal_upgrades_dss_filepath)
    reload_dss_circuit(dss_file_list=[master_path, thermal_upgrades_dss_filepath], commands_list=None, **simulation_params,)
    (
        bus_voltages_df,
        undervoltage_bus_list,
        overvoltage_bus_list,
        buses_with_violations,
    ) = get_bus_voltages(upper_limit=voltage_upper_limit, lower_limit=voltage_lower_limit, **simulation_params)
    xfmr_loading_df = get_thermal_equipment_info(compute_loading=True, upper_limit=thermal_config["transformer_upper_limit"], 
                                                equipment_type="transformer", timepoint_multipliers=timepoint_multipliers, 
                                                multiplier_type=multiplier_type, **simulation_params)
    line_loading_df = get_thermal_equipment_info(compute_loading=True, upper_limit=thermal_config["line_upper_limit"], 
                                                equipment_type="line", ignore_switch=ignore_switch, multiplier_type=multiplier_type,
                                                timepoint_multipliers=timepoint_multipliers, **simulation_params)
    overloaded_xfmr_list = list(xfmr_loading_df.loc[xfmr_loading_df["status"] == "overloaded"]["name"].unique())
    overloaded_line_list = list(line_loading_df.loc[line_loading_df["status"] == "overloaded"]["name"].unique())

    dump_data(line_upgrades_df.to_dict('records'), output_json_line_upgrades_filepath, indent=4)
    dump_data(xfmr_upgrades_df.to_dict('records'), output_json_xfmr_upgrades_filepath, indent=4)
    end_time = time.time()
    logger.info(f"Simulation end time: {end_time}")
    simulation_time = end_time - start_time
    final_results = UpgradeResultModel(
        name=job_name,
        scenario=scenario,
        stage="Final",
        upgrade_type="Thermal",
        # upgrade_status=upgrade_status,
        simulation_time_s=simulation_time,
        thermal_violations_present=(len(overloaded_xfmr_list) + len(overloaded_line_list)) > 0,
        voltage_violations_present=(len(undervoltage_bus_list) + len(overvoltage_bus_list)) > 0,
        max_bus_voltage=bus_voltages_df['Max per unit voltage'].max(),
        min_bus_voltage=bus_voltages_df['Min per unit voltage'].min(),
        num_of_voltage_violation_buses=len(undervoltage_bus_list) + len(overvoltage_bus_list),
        num_of_overvoltage_violation_buses=len(overvoltage_bus_list),
        voltage_upper_limit=voltage_upper_limit,
        num_of_undervoltage_violation_buses=len(undervoltage_bus_list),
        voltage_lower_limit=voltage_lower_limit,
        max_line_loading=line_loading_df['max_per_unit_loading'].max(),
        max_transformer_loading=xfmr_loading_df['max_per_unit_loading'].max(),
        num_of_line_violations=len(overloaded_line_list),
        line_upper_limit=thermal_config['line_upper_limit'],
        num_of_transformer_violations=len(overloaded_xfmr_list),
        transformer_upper_limit=thermal_config['transformer_upper_limit'],
    )
    temp_results = dict(final_results)
    output_results.append(temp_results)
    dump_data(output_results, thermal_summary_file, indent=4)
