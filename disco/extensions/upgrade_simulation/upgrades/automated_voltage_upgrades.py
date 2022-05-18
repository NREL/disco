import json
import logging
import os
import time

from jade.utils.timing_utils import track_timing, Timer
from jade.utils.utils import load_data, dump_data

from .fixed_upgrade_parameters import (
    DEFAULT_CAPACITOR_SETTINGS,
    DEFAULT_SUBLTC_SETTINGS,
    DEFAULT_REGCONTROL_SETTINGS
)
from .voltage_upgrade_functions import *
from disco.enums import LoadMultiplierType
from disco.models.upgrade_cost_analysis_generic_model import UpgradeResultModel
from disco import timer_stats_collector

logger = logging.getLogger(__name__)


@track_timing(timer_stats_collector)
def determine_voltage_upgrades(
    job_name,
    master_path,
    enable_pydss_solve,
    pydss_volt_var_model,
    thermal_config,
    voltage_config,
    thermal_upgrades_dss_filepath,
    voltage_upgrades_dss_filepath,
    upgraded_master_dss_filepath,
    voltage_summary_file,
    output_json_voltage_upgrades_filepath,
    feeder_stats_json_file,
    voltage_upgrades_directory,
    dc_ac_ratio,
    output_folder,
    ignore_switch=True,
    verbose=False
):
    start_time = time.time()
    logger.info(f"Simulation Start time: {start_time}")
    timepoint_multipliers = voltage_config["timepoint_multipliers"]
    if timepoint_multipliers is not None:
        multiplier_type = LoadMultiplierType.UNIFORM
    else:
        multiplier_type = LoadMultiplierType.ORIGINAL
    create_plots = voltage_config["create_plots"]
    # default_capacitor settings and customization
    default_capacitor_settings = DEFAULT_CAPACITOR_SETTINGS
    default_capacitor_settings["capON"] = round(
        (
            voltage_config["nominal_voltage"] -
            voltage_config["capacitor_sweep_voltage_gap"] / 2
        ),
        1,
    )
    default_capacitor_settings["capOFF"] = round(
        (
            voltage_config["nominal_voltage"] +
            voltage_config["capacitor_sweep_voltage_gap"] / 2
        ),
        1,
    )
    # default subltc settings and customization
    default_subltc_settings = DEFAULT_SUBLTC_SETTINGS
    default_subltc_settings["vreg"] = 1.03 * voltage_config["nominal_voltage"]
    
    default_regcontrol_settings = DEFAULT_REGCONTROL_SETTINGS
    default_regcontrol_settings["vreg"] = voltage_config["nominal_voltage"]

    if not os.path.exists(thermal_upgrades_dss_filepath):
        raise Exception(f"AutomatedThermalUpgrade did not produce thermal upgrades dss file")
    
    initial_simulation_params = {"enable_pydss_solve": enable_pydss_solve, "pydss_volt_var_model": pydss_volt_var_model,
                                 "dc_ac_ratio": dc_ac_ratio}
    initial_dss_file_list = [master_path, thermal_upgrades_dss_filepath]
    simulation_params = reload_dss_circuit(dss_file_list=initial_dss_file_list, commands_list=None, **initial_simulation_params)
    simulation_params.update({"timepoint_multipliers": timepoint_multipliers, "multiplier_type": multiplier_type})
    # reading original objects (before upgrades)
    orig_ckt_info = get_circuit_info()
    orig_xfmrs_df =  get_thermal_equipment_info(compute_loading=False, equipment_type="transformer")
    orig_regcontrols_df = get_regcontrol_info(correct_PT_ratio=True, nominal_voltage=voltage_config["nominal_voltage"])
    orig_capacitors_df = get_capacitor_info(correct_PT_ratio=True, nominal_voltage=voltage_config['nominal_voltage'])

    # Initialize dss upgrades file
    dss_commands_list = ["//This file has all the voltage upgrades\n"]
    upgrade_status = ''  # status - whether voltage upgrades done or not
    deciding_field = "deviation_severity"
    
    # determine voltage violations based on initial limits
    voltage_upper_limit = voltage_config["initial_upper_limit"]
    voltage_lower_limit = voltage_config["initial_lower_limit"]

    initial_xfmr_loading_df = get_thermal_equipment_info(compute_loading=True, upper_limit=thermal_config["transformer_upper_limit"], 
                                                        equipment_type="transformer", **simulation_params)
    initial_line_loading_df = get_thermal_equipment_info(compute_loading=True, upper_limit=thermal_config["line_upper_limit"], 
                                                        equipment_type="line", ignore_switch=ignore_switch, **simulation_params)
    initial_bus_voltages_df, initial_undervoltage_bus_list, initial_overvoltage_bus_list, \
        initial_buses_with_violations = get_bus_voltages(
            voltage_upper_limit=thermal_config['voltage_upper_limit'], voltage_lower_limit=thermal_config['voltage_lower_limit'],
            **simulation_params)

    initial_overloaded_xfmr_list = list(initial_xfmr_loading_df.loc[initial_xfmr_loading_df['status'] ==
                                                                    'overloaded']['name'].unique())
    initial_overloaded_line_list = list(initial_line_loading_df.loc[initial_line_loading_df['status'] ==
                                                                    'overloaded']['name'].unique())

    if os.path.exists(feeder_stats_json_file):
        feeder_stats = load_data(feeder_stats_json_file)
    else:
        feeder_stats = {}
    feeder_stats["stage_results"].append( get_upgrade_stage_stats(dss, upgrade_stage="Initial", upgrade_type="voltage", xfmr_loading_df=initial_xfmr_loading_df, line_loading_df=initial_line_loading_df, 
                                        bus_voltages_df=initial_bus_voltages_df) )
    dump_data(feeder_stats, feeder_stats_json_file, indent=4)
    scenario = get_scenario_name(enable_pydss_solve, pydss_volt_var_model)
    initial_results = UpgradeResultModel(
        name = job_name, 
        scenario = scenario,
        stage = "Initial",
        upgrade_type = "Voltage",
        simulation_time_s = 0.0,
        thermal_violations_present = (len(initial_overloaded_xfmr_list) + len(initial_overloaded_line_list)) > 0,
        voltage_violations_present = (len(initial_undervoltage_bus_list) + len(initial_overvoltage_bus_list)) > 0,
        max_bus_voltage = initial_bus_voltages_df['Max per unit voltage'].max(),
        min_bus_voltage = initial_bus_voltages_df['Min per unit voltage'].min(),
        num_of_voltage_violation_buses = len(initial_undervoltage_bus_list) + len(initial_overvoltage_bus_list),
        num_of_overvoltage_violation_buses = len(initial_overvoltage_bus_list),
        voltage_upper_limit = voltage_upper_limit,
        num_of_undervoltage_violation_buses = len(initial_undervoltage_bus_list),
        voltage_lower_limit = voltage_lower_limit,
        max_line_loading = initial_line_loading_df['max_per_unit_loading'].max(),
        max_transformer_loading = initial_xfmr_loading_df['max_per_unit_loading'].max(),
        num_of_line_violations = len(initial_overloaded_line_list),
        line_upper_limit = thermal_config['line_upper_limit'],
        num_of_transformer_violations = len(initial_overloaded_xfmr_list),
        transformer_upper_limit = thermal_config['transformer_upper_limit'] 
    )
    temp_results = dict(initial_results)
    output_results = [temp_results]
    dump_data(output_results, voltage_summary_file, indent=4)
    circuit_source = orig_ckt_info["source_bus"]
    bus_voltages_df, undervoltage_bus_list, overvoltage_bus_list, buses_with_violations = get_bus_voltages(
                voltage_upper_limit=voltage_upper_limit, voltage_lower_limit=voltage_lower_limit, **simulation_params)    
    # if there are no buses with violations based on initial check, don't get into upgrade process
    # directly go to end of file
    if len(buses_with_violations) <= 0:
        logger.info("Voltage Upgrades not Required.")
        upgrade_status = 'Voltage Upgrades not Required'  # status - whether voltage upgrades done or not
    # else, if there are bus violations based on initial check, start voltage upgrades process
    else:
        if create_plots:
            plot_voltage_violations(fig_folder=voltage_upgrades_directory, title="Bus violations before voltage upgrades_"+str(len(buses_with_violations)), 
                                    buses_with_violations=buses_with_violations, circuit_source=circuit_source, enable_detailed=True)
        # change voltage checking thresholds. determine violations based on final limits
        voltage_upper_limit = voltage_config["final_upper_limit"]
        voltage_lower_limit = voltage_config["final_lower_limit"]
        upgrade_status = 'Voltage Upgrades Required'  # status - whether voltage upgrades done or not
        logger.info("Voltage Upgrades Required.")
        # start with capacitors
        if voltage_config["capacitor_action_flag"] and len(orig_capacitors_df) > 0:
            capacitor_dss_commands = determine_capacitor_upgrades(voltage_upper_limit, voltage_lower_limit, default_capacitor_settings, orig_capacitors_df, 
                                                                  voltage_config, deciding_field, fig_folder=os.path.join(voltage_upgrades_directory, "interim"), 
                                                                  create_plots=create_plots, circuit_source=circuit_source,**simulation_params)
            dss_commands_list = dss_commands_list + capacitor_dss_commands
            bus_voltages_df, undervoltage_bus_list, overvoltage_bus_list, buses_with_violations = get_bus_voltages(
                voltage_upper_limit=voltage_upper_limit, voltage_lower_limit=voltage_lower_limit, **simulation_params)    
        else:
            logger.info("No capacitor banks exist in the system")
        
        # next: existing regulators
        # Do a settings sweep of existing reg control devices (other than sub LTC) after correcting their other parameters such as ratios etc
        if voltage_config["existing_regulator_sweep_action"] and (len(orig_regcontrols_df) > 0) and (len(buses_with_violations) > 0):
            # first correct regcontrol parameters (ptratio) including substation LTC, if present
            # then perform settings sweep and choose best setting.
            logger.info("Settings sweep for existing reg control devices (excluding substation LTC).")
            regcontrols_df, reg_sweep_commands_list = sweep_and_choose_regcontrol_setting(voltage_config=voltage_config, initial_regcontrols_df=orig_regcontrols_df, 
                                                        upper_limit=voltage_upper_limit, lower_limit=voltage_lower_limit, 
                                                        dss_file_list=initial_dss_file_list, deciding_field=deciding_field, correct_parameters=True, 
                                                        exclude_sub_ltc=True, only_sub_ltc=False, previous_dss_commands_list=dss_commands_list, 
                                                        fig_folder=os.path.join(voltage_upgrades_directory, "interim"), create_plots=create_plots, circuit_source=circuit_source,
                                                        title="Bus violations after existing vreg sweep",
                                                        **simulation_params)
            # added to commands list only if it is different from original
            dss_commands_list = dss_commands_list + reg_sweep_commands_list
            # determine voltage violations after changes
            bus_voltages_df, undervoltage_bus_list, overvoltage_bus_list, buses_with_violations = get_bus_voltages(voltage_upper_limit=voltage_upper_limit, voltage_lower_limit=voltage_lower_limit, **simulation_params)
        # Writing out the results before adding new devices
        logger.info("Write upgrades to dss file, before adding new devices.")
        write_text_file(string_list=dss_commands_list, text_file_path=voltage_upgrades_dss_filepath)

        # Use this block for adding a substation LTC, correcting its settings and running a sub LTC settings sweep.
        comparison_dict = {"before_addition_of_new_device": compute_voltage_violation_severity(
            voltage_upper_limit=voltage_upper_limit, voltage_lower_limit=voltage_lower_limit, **simulation_params)}
        best_setting_so_far = "before_addition_of_new_device"
        if (voltage_config['use_ltc_placement']) and (len(buses_with_violations) > 0):
            subltc_results_dict = determine_substation_ltc_upgrades(voltage_upper_limit=voltage_upper_limit, voltage_lower_limit=voltage_lower_limit, 
                                    orig_regcontrols_df=orig_regcontrols_df, orig_ckt_info=orig_ckt_info, circuit_source=circuit_source, 
                                    default_subltc_settings=default_subltc_settings, voltage_config=voltage_config, dss_file_list=initial_dss_file_list, 
                                    comparison_dict=comparison_dict, deciding_field=deciding_field, previous_dss_commands_list=dss_commands_list, 
                                    best_setting_so_far=best_setting_so_far, fig_folder=os.path.join(voltage_upgrades_directory, "interim"), create_plots=create_plots, 
                                    default_capacitor_settings=default_capacitor_settings, **simulation_params)
            best_setting_so_far = subltc_results_dict["best_setting_so_far"]
            comparison_dict = subltc_results_dict["comparison_dict"]
            subltc_upgrade_commands = subltc_results_dict["subltc_upgrade_commands"]
            dss_commands_list = dss_commands_list + subltc_upgrade_commands
            # determine voltage violations after changes
            bus_voltages_df, undervoltage_bus_list, overvoltage_bus_list, buses_with_violations = get_bus_voltages(
                voltage_upper_limit=voltage_upper_limit, voltage_lower_limit=voltage_lower_limit, **simulation_params)

        if len(buses_with_violations) >= min((100 * len(initial_buses_with_violations)), 500, len(dss.Circuit.AllBusNames())):
            # if number of buses with violations is very high, the loop for adding new regulators will take very long
            # so disable this block
            logger.info(f"At this point, number of buses with violations is {len(buses_with_violations)}, but initial "
                        f"number of buses with violations is {len(initial_buses_with_violations)}")
            logger.info("So disable option for addition of new regulators")
            voltage_config["place_new_regulators"] = False

        if voltage_config["place_new_regulators"] and (len(buses_with_violations) > 0):
            new_reg_results_dict = determine_new_regulator_upgrades(voltage_config=voltage_config, buses_with_violations=buses_with_violations, 
                                             voltage_upper_limit=voltage_upper_limit, voltage_lower_limit=voltage_lower_limit, 
                                             deciding_field=deciding_field, circuit_source=circuit_source, 
                                             default_regcontrol_settings=default_regcontrol_settings, comparison_dict=comparison_dict, 
                                             best_setting_so_far=best_setting_so_far, dss_file_list=initial_dss_file_list, 
                                             previous_dss_commands_list=dss_commands_list, fig_folder=os.path.join(voltage_upgrades_directory, "interim"), 
                                             create_plots=create_plots, **simulation_params)
            best_setting_so_far = new_reg_results_dict["best_setting_so_far"]
            comparison_dict = new_reg_results_dict["comparison_dict"]
            new_reg_upgrade_commands = new_reg_results_dict["new_reg_upgrade_commands"]
            dss_commands_list = dss_commands_list + new_reg_upgrade_commands
            # determine voltage violations after changes
            bus_voltages_df, undervoltage_bus_list, overvoltage_bus_list, buses_with_violations = get_bus_voltages(
                voltage_upper_limit=voltage_upper_limit, voltage_lower_limit=voltage_lower_limit, **simulation_params)           

    if any("new " in string.lower() for string in dss_commands_list):  # if new equipment is added.
        dss_commands_list.append("CalcVoltageBases")
    dss_commands_list.append("Solve")
    write_text_file(string_list=dss_commands_list, text_file_path=voltage_upgrades_dss_filepath)
    redirect_command_list = create_upgraded_master_dss(dss_file_list=initial_dss_file_list + [voltage_upgrades_dss_filepath], upgraded_master_dss_filepath=upgraded_master_dss_filepath)
    write_text_file(string_list=redirect_command_list, text_file_path=upgraded_master_dss_filepath)
    reload_dss_circuit(dss_file_list=[upgraded_master_dss_filepath], commands_list=None, **simulation_params,)
    # reading new objects (after upgrades)
    new_ckt_info = get_circuit_info()
    new_regcontrols_df = get_regcontrol_info(correct_PT_ratio=True, nominal_voltage=voltage_config["nominal_voltage"])
    new_capacitors_df = get_capacitor_info(correct_PT_ratio=True, nominal_voltage=voltage_config['nominal_voltage'])
    processed_cap = get_capacitor_upgrades(orig_capacitors_df=orig_capacitors_df, new_capacitors_df=new_capacitors_df)
    processed_reg = get_regulator_upgrades(orig_regcontrols_df=orig_regcontrols_df, new_regcontrols_df=new_regcontrols_df, 
                                           orig_xfmrs_df=orig_xfmrs_df, new_ckt_info=new_ckt_info)
    processed_cap.update(processed_reg)
    processed_df = pd.DataFrame.from_dict(processed_cap, orient='index')
    processed_df.index.name = 'temp'
    processed_df.reset_index(inplace=True)
    processed_df[['name', 'equipment_type']] = ""
    if not processed_df.empty:  # if there are voltage upgrades
        processed_df[['equipment_type', 'name']] = processed_df['temp'].str.split('.', expand=True)
    processed_df = processed_df.set_index(['equipment_type', 'name']).reset_index()
    del processed_df["temp"]
    dump_data(processed_df.to_dict('records'), output_json_voltage_upgrades_filepath, indent=4)
    bus_voltages_df, undervoltage_bus_list, overvoltage_bus_list, buses_with_violations = get_bus_voltages(
        voltage_upper_limit=voltage_upper_limit, voltage_lower_limit=voltage_lower_limit, **simulation_params)
    
    xfmr_loading_df = get_thermal_equipment_info(compute_loading=True, upper_limit=thermal_config["transformer_upper_limit"], 
                                                equipment_type="transformer", **simulation_params)
    line_loading_df = get_thermal_equipment_info(compute_loading=True, upper_limit=thermal_config["line_upper_limit"], 
                                                equipment_type="line", ignore_switch=ignore_switch, **simulation_params)
    overloaded_xfmr_list = list(xfmr_loading_df.loc[xfmr_loading_df['status'] == 'overloaded']['name'].unique())
    overloaded_line_list = list(line_loading_df.loc[line_loading_df['status'] == 'overloaded']['name'].unique())
    if (upgrade_status == "Voltage Upgrades Required") and create_plots:
        plot_voltage_violations(fig_folder=voltage_upgrades_directory, title="Bus violations after voltage upgrades_"+str(len(buses_with_violations)), 
                                    buses_with_violations=buses_with_violations, circuit_source=circuit_source, enable_detailed=True)
    if os.path.exists(feeder_stats_json_file):
        feeder_stats = load_data(feeder_stats_json_file)
    else:
        feeder_stats = {}
    feeder_stats["stage_results"].append( get_upgrade_stage_stats(dss, upgrade_stage="Final", upgrade_type="voltage", xfmr_loading_df=xfmr_loading_df, line_loading_df=line_loading_df, 
                                        bus_voltages_df=bus_voltages_df) )
    dump_data(feeder_stats, feeder_stats_json_file, indent=4) 
    end_time = time.time()
    logger.info(f"Simulation end time: {end_time}")
    simulation_time = end_time - start_time
    logger.info(f"Simulation time: {simulation_time}")
    final_results = UpgradeResultModel(
        name = job_name, 
        scenario = scenario,
        stage = "Final",
        upgrade_type = "Voltage",
        simulation_time_s = simulation_time,
        thermal_violations_present = (len(overloaded_xfmr_list) + len(overloaded_line_list)) > 0,
        voltage_violations_present = (len(undervoltage_bus_list) + len(overvoltage_bus_list)) > 0,
        max_bus_voltage = bus_voltages_df['Max per unit voltage'].max(),
        min_bus_voltage = bus_voltages_df['Min per unit voltage'].min(),
        num_of_voltage_violation_buses = len(undervoltage_bus_list) + len(overvoltage_bus_list),
        num_of_overvoltage_violation_buses = len(overvoltage_bus_list),
        voltage_upper_limit = voltage_upper_limit,
        num_of_undervoltage_violation_buses = len(undervoltage_bus_list),
        voltage_lower_limit = voltage_lower_limit,
        max_line_loading = line_loading_df['max_per_unit_loading'].max(),
        max_transformer_loading = xfmr_loading_df['max_per_unit_loading'].max(),
        num_of_line_violations = len(overloaded_line_list),
        line_upper_limit = thermal_config['line_upper_limit'],
        num_of_transformer_violations = len(overloaded_xfmr_list),
        transformer_upper_limit = thermal_config['transformer_upper_limit']
    )
    temp_results = dict(final_results)
    output_results.append(temp_results)
    dump_data(output_results, voltage_summary_file, indent=4)
    