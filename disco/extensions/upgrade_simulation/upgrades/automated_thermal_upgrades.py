import time
import json
import logging
import pandas as pd

from jade.utils.timing_utils import track_timing, Timer
from jade.utils.utils import load_data, dump_data

from .thermal_upgrade_functions import *
from .voltage_upgrade_functions import plot_thermal_violations, plot_voltage_violations, plot_feeder

from disco.models.upgrade_cost_analysis_generic_input_model import UpgradeTechnicalCatalogModel
from disco.models.upgrade_cost_analysis_generic_output_model import UpgradeViolationResultModel, AllUpgradesTechnicalResultModel
from disco import timer_stats_collector
from disco.enums import LoadMultiplierType
from disco.exceptions import UpgradesInvalidViolationIncrease


logger = logging.getLogger(__name__)


@track_timing(timer_stats_collector)
def determine_thermal_upgrades(
    job_name,
    master_path,
    enable_pydss_solve,
    pydss_volt_var_model,
    thermal_config,
    internal_upgrades_technical_catalog_filepath,
    thermal_upgrades_dss_filepath,
    upgraded_master_dss_filepath,
    output_json_thermal_upgrades_filepath,
    feeder_stats_json_file,
    thermal_upgrades_directory,
    overall_output_summary_filepath,
    dc_ac_ratio,
    ignore_switch=True,
    verbose=False
):
    start_time = time.time()
    logger.info( f"Simulation start time: {start_time}")   
    initial_simulation_params = {"enable_pydss_solve": enable_pydss_solve, "pydss_volt_var_model": pydss_volt_var_model,
                                 "dc_ac_ratio": dc_ac_ratio}
    logger.info("Initial simulation parameters: %s", initial_simulation_params)
    create_plots = thermal_config["create_plots"]
    # start upgrades
    initial_dss_file_list = [master_path]
    simulation_params = reload_dss_circuit(dss_file_list=initial_dss_file_list, commands_list=None, **initial_simulation_params)
    timepoint_multipliers = thermal_config["timepoint_multipliers"]

    if timepoint_multipliers is not None:
        multiplier_type = LoadMultiplierType.UNIFORM
    else:
        multiplier_type = LoadMultiplierType.ORIGINAL
    simulation_params.update({"timepoint_multipliers": timepoint_multipliers, "multiplier_type": multiplier_type})
    
    voltage_upper_limit = thermal_config["voltage_upper_limit"]
    voltage_lower_limit = thermal_config["voltage_lower_limit"]
    if thermal_config["read_external_catalog"]:
        with open(thermal_config["external_catalog"]) as json_file:
            external_upgrades_technical_catalog = json.load(json_file)
        # perform validation for external catalog
        input_catalog_model = UpgradeTechnicalCatalogModel(**external_upgrades_technical_catalog)
        line_upgrade_options = pd.DataFrame.from_dict(input_catalog_model.dict(by_alias=True)["line"])
        xfmr_upgrade_options = pd.DataFrame.from_dict(input_catalog_model.dict(by_alias=True)["transformer"])
        # this will remove any duplicates if present
        line_upgrade_options = determine_available_line_upgrades(line_upgrade_options)
        xfmr_upgrade_options = determine_available_xfmr_upgrades(xfmr_upgrade_options)
    else:
        external_upgrades_technical_catalog = {}
        orig_lines_df = get_thermal_equipment_info(compute_loading=False, equipment_type="line")
        orig_xfmrs_df = get_thermal_equipment_info(compute_loading=False, equipment_type="transformer")
        orig_linecode_df = get_line_code()
        orig_linegeometry_df = get_line_geometry()
        line_upgrade_options = determine_available_line_upgrades(orig_lines_df)
        xfmr_upgrade_options = determine_available_xfmr_upgrades(orig_xfmrs_df)
        internal_upgrades_technical_catalog = {"line": line_upgrade_options.to_dict('records'), "transformer": xfmr_upgrade_options.to_dict('records'),
                                               "linecode": orig_linecode_df.to_dict('records'), 
                                               "geometry": orig_linegeometry_df.to_dict('records'),
                                               }
        # validate internal upgrades catalog
        input_catalog_model = UpgradeTechnicalCatalogModel(**internal_upgrades_technical_catalog)
        dump_data(input_catalog_model.dict(by_alias=True), 
                  internal_upgrades_technical_catalog_filepath, indent=2)  # write internal catalog to json
        # reassign from model to dataframes, so datatypes are maintained
        line_upgrade_options = pd.DataFrame.from_dict(input_catalog_model.dict(by_alias=True)["line"])
        xfmr_upgrade_options = pd.DataFrame.from_dict(input_catalog_model.dict(by_alias=True)["transformer"])
    # get these feeder details before running powerflow
    feeder_stats = {"feeder_metadata": {}, "stage_results": []}
    feeder_stats["feeder_metadata"].update(get_feeder_stats(dss))
    (
        initial_bus_voltages_df,
        initial_undervoltage_bus_list,
        initial_overvoltage_bus_list,
        initial_buses_with_violations,
    ) = get_bus_voltages(voltage_upper_limit=voltage_upper_limit, voltage_lower_limit=voltage_lower_limit, **simulation_params)
    
    initial_xfmr_loading_df = get_thermal_equipment_info(compute_loading=True, upper_limit=thermal_config["transformer_upper_limit"], 
                                                         equipment_type="transformer", **simulation_params)
    initial_line_loading_df = get_thermal_equipment_info(compute_loading=True, upper_limit=thermal_config["line_upper_limit"], 
                                                         equipment_type="line", ignore_switch=ignore_switch, **simulation_params)
    
    initial_overloaded_xfmr_list = list(initial_xfmr_loading_df.loc[initial_xfmr_loading_df["status"] == 
                                                                    "overloaded"]["name"].unique())
    initial_overloaded_line_list = list(initial_line_loading_df.loc[initial_line_loading_df["status"] == 
                                                                    "overloaded"]["name"].unique())
    orig_ckt_info = get_circuit_info()
    circuit_source = orig_ckt_info['source_bus']
    orig_regcontrols_df = get_regcontrol_info(correct_PT_ratio=False)
    orig_capacitors_df = get_capacitor_info(correct_PT_ratio=False)
    feeder_stats["stage_results"].append(get_upgrade_stage_stats(dss, upgrade_stage="initial", upgrade_type="thermal", xfmr_loading_df=initial_xfmr_loading_df, line_loading_df=initial_line_loading_df, 
                                        bus_voltages_df=initial_bus_voltages_df, capacitors_df=orig_capacitors_df, regcontrols_df=orig_regcontrols_df) )
    dump_data(feeder_stats, feeder_stats_json_file, indent=2)   # save feeder stats
    if len(initial_overloaded_xfmr_list) > 0 or len(initial_overloaded_line_list) > 0:
        n = len(initial_overloaded_xfmr_list) +  len(initial_overloaded_line_list)
        equipment_with_violations = {"Transformer": initial_xfmr_loading_df, "Line": initial_line_loading_df}
        if create_plots:
            plot_thermal_violations(fig_folder=thermal_upgrades_directory, title="Thermal violations before thermal upgrades_"+str(n), 
                                    equipment_with_violations=equipment_with_violations, circuit_source=circuit_source)
            plot_voltage_violations(fig_folder=thermal_upgrades_directory, title="Bus violations before thermal upgrades_"+str(len(initial_buses_with_violations)), 
                                    buses_with_violations=initial_buses_with_violations, circuit_source=circuit_source, enable_detailed=True)
        upgrade_status = "Thermal Upgrades Required"  # status - whether upgrades done or not
    else:
        upgrade_status = "Thermal Upgrades not Required"  # status - whether upgrades done or not
    logger.info(upgrade_status)
    scenario = get_scenario_name(enable_pydss_solve, pydss_volt_var_model)
    initial_results = UpgradeViolationResultModel(
        name=job_name,
        scenario=scenario,
        stage="initial",
        upgrade_type="thermal",
        # upgrade_status = upgrade_status,
        simulation_time_s = 0.0,
        thermal_violations_present=(len(initial_overloaded_xfmr_list) + len(initial_overloaded_line_list)) > 0,
        voltage_violations_present=(len(initial_undervoltage_bus_list) + len(initial_overvoltage_bus_list)) > 0,
        max_bus_voltage=initial_bus_voltages_df['max_per_unit_voltage'].max(),
        min_bus_voltage=initial_bus_voltages_df['min_per_unit_voltage'].min(),
        num_voltage_violation_buses=len(initial_undervoltage_bus_list) + len(initial_overvoltage_bus_list),
        num_overvoltage_violation_buses=len(initial_overvoltage_bus_list),
        voltage_upper_limit=voltage_upper_limit,
        num_undervoltage_violation_buses=len(initial_undervoltage_bus_list),
        voltage_lower_limit=voltage_lower_limit,
        max_line_loading=initial_line_loading_df['max_per_unit_loading'].max(),
        max_transformer_loading=initial_xfmr_loading_df['max_per_unit_loading'].max(),
        num_line_violations=len(initial_overloaded_line_list),
        line_upper_limit=thermal_config['line_upper_limit'],
        num_transformer_violations=len(initial_overloaded_xfmr_list),
        transformer_upper_limit=thermal_config['transformer_upper_limit']
    )
    temp_results = convert_dict_nan_to_none(dict(initial_results))
    if os.path.exists(overall_output_summary_filepath):
        overall_outputs = load_data(overall_output_summary_filepath)
        overall_outputs["violation_summary"].append(temp_results)
    else:
        overall_outputs = {"violation_summary": [temp_results]}
    dump_data(overall_outputs, overall_output_summary_filepath, indent=2, allow_nan=False)
    title = "Feeder"
    plot_feeder(fig_folder=thermal_upgrades_directory, title=title, circuit_source=circuit_source, enable_detailed=True)
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
                                                    equipment_type="line", ignore_switch=ignore_switch, **simulation_params)
        overloaded_line_list = list(line_loading_df.loc[line_loading_df["status"] == "overloaded"]["name"].unique())
        logger.info(f"Iteration_{iteration_counter}: Determined line loadings.")
        logger.info(f"Iteration_{iteration_counter}: Number of line violations: {len(overloaded_line_list)}")
        before_upgrade_num_line_violations = len(overloaded_line_list)
        if len(overloaded_line_list) > 0:            
            line_commands_list, temp_line_upgrades_df = correct_line_violations(
                line_loading_df=line_loading_df,
                line_design_pu=thermal_config["line_design_pu"],
                line_upgrade_options=line_upgrade_options.copy(deep=True),
                parallel_lines_limit=thermal_config["parallel_lines_limit"],
                external_upgrades_technical_catalog=external_upgrades_technical_catalog,)
            logger.info(f"Iteration_{iteration_counter}: Corrected line violations.")
            commands_list = commands_list + line_commands_list
            line_upgrades_df = pd.concat([line_upgrades_df, temp_line_upgrades_df])
        xfmr_loading_df = get_thermal_equipment_info(compute_loading=True, upper_limit=thermal_config["transformer_upper_limit"], 
                                                    equipment_type="transformer", **simulation_params)
        overloaded_xfmr_list = list(xfmr_loading_df.loc[xfmr_loading_df["status"] == "overloaded"]["name"].unique())
        logger.info(f"Iteration_{iteration_counter}: Determined xfmr loadings.")
        logger.info(f"Iteration_{iteration_counter}: Number of xfmr violations: {len(overloaded_xfmr_list)}")
        before_upgrade_num_xfmr_violations = len(overloaded_xfmr_list)
        
        if len(overloaded_xfmr_list) > 0:
            xfmr_commands_list, temp_xfmr_upgrades_df = correct_xfmr_violations(
                xfmr_loading_df=xfmr_loading_df,
                xfmr_design_pu=thermal_config["transformer_design_pu"],
                xfmr_upgrade_options=xfmr_upgrade_options.copy(deep=True),
                parallel_transformers_limit=thermal_config["parallel_transformers_limit"])
            logger.info(f"Iteration_{iteration_counter}: Corrected xfmr violations.")
            commands_list = commands_list + xfmr_commands_list
            xfmr_upgrades_df = pd.concat([xfmr_upgrades_df, temp_xfmr_upgrades_df])
        # compute loading after upgrades
        xfmr_loading_df = get_thermal_equipment_info(compute_loading=True, upper_limit=thermal_config["transformer_upper_limit"], 
                                                    equipment_type="transformer",  **simulation_params)
        overloaded_xfmr_list = list(xfmr_loading_df.loc[xfmr_loading_df["status"] == "overloaded"]["name"].unique())
        line_loading_df = get_thermal_equipment_info(compute_loading=True, upper_limit=thermal_config["line_upper_limit"], 
                                                    equipment_type="line", ignore_switch=ignore_switch, **simulation_params)
        overloaded_line_list = list(line_loading_df.loc[line_loading_df["status"] == "overloaded"]["name"].unique())
        
        if len(overloaded_line_list) > before_upgrade_num_line_violations:
            logger.debug(overloaded_line_list)
            logger.info("Write upgrades till this step to debug upgrades")
            write_text_file(string_list=commands_list, text_file_path=thermal_upgrades_dss_filepath)
            raise UpgradesInvalidViolationIncrease(f"Line violations increased from {before_upgrade_num_line_violations} to {len(overloaded_line_list)} "
                f"during upgrade process")
        if len(overloaded_xfmr_list) > before_upgrade_num_xfmr_violations:
            logger.info("Write upgrades till this step to debug upgrades")
            write_text_file(string_list=commands_list, text_file_path=thermal_upgrades_dss_filepath)
            raise UpgradesInvalidViolationIncrease(f"Xfmr violations increased from {before_upgrade_num_xfmr_violations} to {len(overloaded_xfmr_list)} "
                f"during upgrade process")

        logger.info(f"Iteration_{iteration_counter}: Number of devices with violations after this iteration: Transformers:{len(overloaded_xfmr_list)}, Lines: {len(overloaded_line_list)}")
        iteration_counter += 1
        if iteration_counter > max_upgrade_iteration:
            logger.info(f"Max iterations limit reached, quitting algorithm. This means all thermal violations were not resolved with these limited iterations."
                        f"You can increase the Iteration limit in the thermal_config['upgrade_iteration_threshold']")
            break
    if iteration_counter > 1:
        logger.info(f"Multiple iterations ({iteration_counter}) were needed to resolve thermal violations."
                    f"This indicates that feeder was extremely overloaded to start with.")
    
    if any("new " in string.lower() for string in commands_list):  # if new equipment is added.
        commands_list.append("CalcVoltageBases")
    commands_list.append("Solve")
    write_text_file(string_list=commands_list, text_file_path=thermal_upgrades_dss_filepath)
    redirect_command_list = create_upgraded_master_dss(dss_file_list=initial_dss_file_list + [thermal_upgrades_dss_filepath], upgraded_master_dss_filepath=upgraded_master_dss_filepath,
                                                       original_master_filename=os.path.basename(master_path))
    write_text_file(string_list=redirect_command_list, text_file_path=upgraded_master_dss_filepath)
    reload_dss_circuit(dss_file_list=[upgraded_master_dss_filepath], commands_list=None, **simulation_params,)
    bus_voltages_df, undervoltage_bus_list, overvoltage_bus_list, buses_with_violations = get_bus_voltages(voltage_upper_limit=voltage_upper_limit, 
                                                                                                           voltage_lower_limit=voltage_lower_limit, **simulation_params)
    xfmr_loading_df = get_thermal_equipment_info(compute_loading=True, upper_limit=thermal_config["transformer_upper_limit"], 
                                                equipment_type="transformer", **simulation_params)
    line_loading_df = get_thermal_equipment_info(compute_loading=True, upper_limit=thermal_config["line_upper_limit"], 
                                                equipment_type="line", ignore_switch=ignore_switch, **simulation_params)
    overloaded_xfmr_list = list(xfmr_loading_df.loc[xfmr_loading_df["status"] == "overloaded"]["name"].unique())
    overloaded_line_list = list(line_loading_df.loc[line_loading_df["status"] == "overloaded"]["name"].unique())
    # same equipment could be upgraded(edited) multiple times. Only consider last upgrade edit done. original_equipment details are currently not used.
    line_upgrades_df = line_upgrades_df.drop_duplicates(subset=["upgrade_type", "action", "final_equipment_name"], keep="last")  
    xfmr_upgrades_df = xfmr_upgrades_df.drop_duplicates(subset=["upgrade_type", "action", "final_equipment_name"], keep="last") 
    # validate upgrades output models
    m = AllUpgradesTechnicalResultModel(line=line_upgrades_df.to_dict('records'), transformer=xfmr_upgrades_df.to_dict('records'))
    temp = m.dict(by_alias=True)
    temp.pop("voltage")
    dump_data(temp, output_json_thermal_upgrades_filepath, indent=2)
    n = len(overloaded_xfmr_list) +  len(overloaded_line_list)
    equipment_with_violations = {"Transformer": xfmr_loading_df, "Line": line_loading_df}
    if (upgrade_status == "Thermal Upgrades Required") and create_plots:
        plot_thermal_violations(fig_folder=thermal_upgrades_directory, title="Thermal violations after thermal upgrades_"+str(n), 
                                equipment_with_violations=equipment_with_violations, circuit_source=circuit_source)
        plot_voltage_violations(fig_folder=thermal_upgrades_directory, title="Bus violations after thermal upgrades_"+str(len(buses_with_violations)), 
                                buses_with_violations=buses_with_violations, circuit_source=circuit_source, enable_detailed=True)
    if os.path.exists(feeder_stats_json_file):
        feeder_stats = load_data(feeder_stats_json_file)
    else:
        feeder_stats = {}
    regcontrols_df = get_regcontrol_info(correct_PT_ratio=False)
    capacitors_df = get_capacitor_info(correct_PT_ratio=False)
    feeder_stats["stage_results"].append( get_upgrade_stage_stats(dss, upgrade_stage="final", upgrade_type="thermal", xfmr_loading_df=xfmr_loading_df, line_loading_df=line_loading_df, 
                                        bus_voltages_df=bus_voltages_df, capacitors_df=capacitors_df, regcontrols_df=regcontrols_df) )
    dump_data(feeder_stats, feeder_stats_json_file, indent=2)
    end_time = time.time()
    logger.info(f"Simulation end time: {end_time}")
    simulation_time = end_time - start_time
    final_results = UpgradeViolationResultModel(
        name=job_name,
        scenario=scenario,
        stage="final",
        upgrade_type="thermal",
        # upgrade_status=upgrade_status,
        simulation_time_s=simulation_time,
        thermal_violations_present=(len(overloaded_xfmr_list) + len(overloaded_line_list)) > 0,
        voltage_violations_present=(len(undervoltage_bus_list) + len(overvoltage_bus_list)) > 0,
        max_bus_voltage=bus_voltages_df['max_per_unit_voltage'].max(),
        min_bus_voltage=bus_voltages_df['min_per_unit_voltage'].min(),
        num_voltage_violation_buses=len(undervoltage_bus_list) + len(overvoltage_bus_list),
        num_overvoltage_violation_buses=len(overvoltage_bus_list),
        voltage_upper_limit=voltage_upper_limit,
        num_undervoltage_violation_buses=len(undervoltage_bus_list),
        voltage_lower_limit=voltage_lower_limit,
        max_line_loading=line_loading_df['max_per_unit_loading'].max(),
        max_transformer_loading=xfmr_loading_df['max_per_unit_loading'].max(),
        num_line_violations=len(overloaded_line_list),
        line_upper_limit=thermal_config['line_upper_limit'],
        num_transformer_violations=len(overloaded_xfmr_list),
        transformer_upper_limit=thermal_config['transformer_upper_limit'],
    )
    temp_results = dict(final_results)
    temp_results = convert_dict_nan_to_none(temp_results)
    if os.path.exists(overall_output_summary_filepath):
        overall_outputs = load_data(overall_output_summary_filepath)
        overall_outputs["violation_summary"].append(temp_results)
    else:
        overall_outputs = {"violation_summary": [temp_results]}
    dump_data(overall_outputs, overall_output_summary_filepath, indent=2, allow_nan=False)
