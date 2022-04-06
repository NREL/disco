import json
import logging
import os
import time

from jade.utils.timing_utils import track_timing, Timer

from .fixed_upgrade_parameters import (
    DEFAULT_CAPACITOR_SETTINGS,
    DEFAULT_SUBLTC_SETTINGS,
    DEFAULT_REGCONTROL_SETTINGS
)
from .voltage_upgrade_functions import *
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
    voltage_summary_file,
    output_json_voltage_upgrades_filepath,
    feeder_stats_json_file,
    output_folder,
    ignore_switch=True,
    verbose=False
):
    start_time = time.time()
    logger.info(f"Simulation Start time: {start_time}")
    timepoint_multipliers = voltage_config["timepoint_multipliers"]
    if timepoint_multipliers is not None:
        multiplier_type = "uniform"
    else:
        multiplier_type = "original"
        
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

    if not os.path.exists(thermal_upgrades_dss_filepath):
        raise Exception( f"AutomatedThermalUpgrade did not produce thermal upgrades dss file")
    
    pydss_params = {"enable_pydss_solve": enable_pydss_solve, "pydss_volt_var_model": pydss_volt_var_model}
    dss_file_list = [master_path, thermal_upgrades_dss_filepath]
    simulation_params = reload_dss_circuit(dss_file_list=dss_file_list, commands_list=None, **pydss_params)

    # reading original objects (before upgrades)
    orig_ckt_info = get_circuit_info()
    orig_xfmrs_df =  get_thermal_equipment_info(compute_loading=False, equipment_type="transformer")
    orig_regcontrols_df = get_regcontrol_info(correct_PT_ratio=True, nominal_voltage=voltage_config["nominal_voltage"])
    orig_capacitors_df = get_capacitor_info(correct_PT_ratio=True, nominal_voltage=voltage_config['nominal_voltage'])

    # Initialize dss upgrades file
    dss_commands_list = ["//This file has all the voltage upgrades\n"]
    upgrade_status = ''  # status - whether voltage upgrades done or not

    # determine voltage violations based on initial limits
    voltage_upper_limit = voltage_config["initial_upper_limit"]
    voltage_lower_limit = voltage_config["initial_lower_limit"]

    initial_xfmr_loading_df = get_thermal_equipment_info(compute_loading=True, upper_limit=thermal_config["transformer_upper_limit"], 
                                                        equipment_type="transformer", timepoint_multipliers=timepoint_multipliers, 
                                                        multiplier_type=multiplier_type, **simulation_params)
    initial_line_loading_df = get_thermal_equipment_info(compute_loading=True, upper_limit=thermal_config["line_upper_limit"], 
                                                        equipment_type="line", ignore_switch=ignore_switch, multiplier_type=multiplier_type,
                                                        timepoint_multipliers=timepoint_multipliers, **simulation_params)
    initial_bus_voltages_df, initial_undervoltage_bus_list, initial_overvoltage_bus_list, \
        initial_buses_with_violations = get_bus_voltages(
            voltage_upper_limit=thermal_config['voltage_upper_limit'], voltage_lower_limit=thermal_config['voltage_lower_limit'],
            **simulation_params)

    initial_overloaded_xfmr_list = list(initial_xfmr_loading_df.loc[initial_xfmr_loading_df['status'] ==
                                                                    'overloaded']['name'].unique())
    initial_overloaded_line_list = list(initial_line_loading_df.loc[initial_line_loading_df['status'] ==
                                                                    'overloaded']['name'].unique())

    scenario = get_scenario_name(enable_pydss_solve, pydss_volt_var_model)
    initial_results = UpgradeResultModel(
        name = job_name, 
        scenario = scenario,
        stage = "Initial",
        upgrade_type = "Voltage",
        simulation_time_s = np.nan,
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
    write_to_json(output_results, voltage_summary_file)
    # if there are no buses with violations based on initial check, don't get into upgrade process
    # directly go to end of file
    if len(initial_buses_with_violations) <= 0:
        logger.info("No Voltage Upgrades Required.")
        upgrade_status = 'No Voltage Upgrades needed'  # status - whether voltage upgrades done or not
    # else, if there are bus violations based on initial check, start voltage upgrades process
    else:
        # change voltage checking thresholds. determine violations based on final limits
        voltage_upper_limit = voltage_config["final_upper_limit"]
        voltage_lower_limit = voltage_config["final_lower_limit"]

        upgrade_status = 'Voltage Upgrades were needed'  # status - whether voltage upgrades done or not
        logger.info("Voltage Upgrades Required.")
        # start with capacitors
        if voltage_config["capacitor_action_flag"] and len(orig_capacitors_df) > 0:
            logger.info("Capacitors are present in the network. Perform capacitor bank control modifications.")
            # correct cap control parameters: change to voltage controlled, correct PT ratio. Add cap control if not present
            capcontrol_parameter_commands_list = correct_capacitor_parameters(
                default_capacitor_settings=default_capacitor_settings, orig_capacitors_df=orig_capacitors_df,
                nominal_voltage=voltage_config['nominal_voltage'], **simulation_params)
            dss_commands_list = dss_commands_list + capcontrol_parameter_commands_list
            bus_voltages_df, undervoltage_bus_list, overvoltage_bus_list, buses_with_violations = get_bus_voltages(
                voltage_upper_limit=voltage_upper_limit, voltage_lower_limit=voltage_lower_limit, **simulation_params)

            if len(buses_with_violations) > 0:
                # get capacitors dataframe before any settings changes are made
                nosetting_changes_capacitors_df = get_capacitor_info(correct_PT_ratio=False)
                # sweep through all capacitor settings, and store objective function
                capacitor_sweep_df = sweep_capacitor_settings(voltage_config=voltage_config,
                                                              initial_capacitors_df=nosetting_changes_capacitors_df,
                                                              default_capacitor_settings=default_capacitor_settings,
                                                              voltage_upper_limit=voltage_upper_limit,
                                                              voltage_lower_limit=voltage_lower_limit, **simulation_params)
                # choose best capacitor settings
                capacitors_df, capcontrol_settings_commands_list = choose_best_capacitor_sweep_setting(
                    capacitor_sweep_df=capacitor_sweep_df, initial_capacitors_df=nosetting_changes_capacitors_df,
                    **simulation_params)
                dss_commands_list = dss_commands_list + capcontrol_settings_commands_list
            # determine voltage violations after capacitor changes
            bus_voltages_df, undervoltage_bus_list, overvoltage_bus_list, buses_with_violations = get_bus_voltages(
                voltage_upper_limit=voltage_upper_limit, voltage_lower_limit=voltage_lower_limit, **simulation_params)
        else:
            logger.info("No capacitor banks exist in the system")

        # next: existing regulators
        # Do a settings sweep of existing reg control devices (other than sub LTC) after correcting their other
        #  parameters such as ratios etc
        if voltage_config["existing_regulator_sweep_action"] and (len(orig_regcontrols_df) > 0) and (len(buses_with_violations) > 0):
            # first correct regcontrol parameters (ptratio) including substation LTC, if present
            regcontrols_parameter_command_list = correct_regcontrol_parameters(orig_regcontrols_df=orig_regcontrols_df,
                                                                               **simulation_params)
            logger.info("Settings sweep for existing reg control devices (excluding substation LTC).")
            regcontrol_sweep_df = sweep_regcontrol_settings(voltage_config=voltage_config,
                                                            initial_regcontrols_df=orig_regcontrols_df,
                                                            voltage_upper_limit=voltage_upper_limit, voltage_lower_limit=voltage_lower_limit,
                                                            exclude_sub_ltc=True, only_sub_ltc=False, **simulation_params)
            # reload circuit after settings sweep
            reload_dss_circuit(dss_file_list=dss_file_list, commands_list=dss_commands_list, **simulation_params)
            regcontrols_df, regcontrol_settings_commands_list = choose_best_regcontrol_sweep_setting(
                regcontrol_sweep_df=regcontrol_sweep_df, initial_regcontrols_df=orig_regcontrols_df, exclude_sub_ltc=True,
                only_sub_ltc=False, **simulation_params)
            # added to commands list only if it is different from original
            # will this need to be removed if it's different later
            dss_commands_list = dss_commands_list + regcontrol_settings_commands_list + \
                regcontrols_parameter_command_list
        # Writing out the results before adding new devices
        logger.info("Write upgrades to dss file, before adding new devices.")
        write_text_file(string_list=dss_commands_list, text_file_path=voltage_upgrades_dss_filepath)

        # determine voltage violations after changes
        bus_voltages_df, undervoltage_bus_list, overvoltage_bus_list, buses_with_violations = get_bus_voltages(
            voltage_upper_limit=voltage_upper_limit, voltage_lower_limit=voltage_lower_limit, **simulation_params)

        # Use this block for adding a substation LTC, correcting its settings and running a sub LTC settings sweep.
        # if LTC exists, first try to correct its non set point simulation settings.
        # If this does not correct everything, correct its set points through a sweep.
        # If LTC does not exist, add one including a xfmr if required, then do a settings sweep if required
        if (voltage_config['use_ltc_placement']) and (len(buses_with_violations) > 0):
            logger.info("Enter Substation LTC module.")
            subltc_present_flag = (
                len(orig_regcontrols_df.loc[orig_regcontrols_df['at_substation_xfmr_flag'] == True]) > 0)
            # if there is no substation transformer in the network
            if orig_ckt_info['substation_xfmr'] is None:
                # check add substation transformer and add ltc reg control on it
                add_subxfmr_commands = add_substation_xfmr(**simulation_params)
                pass_flag, add_subltc_commands = add_new_regcontrol_command(
                    xfmr_info_series=pd.Series(orig_ckt_info['substation_xfmr']),
                    default_regcontrol_settings=default_subltc_settings,
                    nominal_voltage=voltage_config["nominal_voltage"], **simulation_params)
                if not pass_flag:
                    logger.info("No convergence after adding regulator control at substation LTC. "
                                "Check if there is any setting that has convergence. Else remove substation LTC")
                    reload_dss_circuit(dss_file_list=dss_file_list, commands_list=dss_commands_list + add_subltc_commands,
                                       **simulation_params)
                # this needs to be collected again, since a new regulator control might have been added at the substation
                initial_sub_regcontrols_df = get_regcontrol_info(correct_PT_ratio=True,
                                                                 nominal_voltage=voltage_config["nominal_voltage"])
                # sweep through settings and identify best setting
                subltc_controls_df, subltc_control_settings_commands_list = sweep_and_choose_regcontrol_setting(
                    voltage_config=voltage_config, initial_regcontrols_df=initial_sub_regcontrols_df,
                    upper_limit=voltage_upper_limit, lower_limit=voltage_lower_limit, exclude_sub_ltc=False,
                    only_sub_ltc=True, dss_file_list=dss_file_list,
                    dss_commands_list=dss_commands_list + add_subltc_commands, **simulation_params)
                circuit_solve_and_check(raise_exception=True, **simulation_params)
                dss_commands_list = dss_commands_list + add_subxfmr_commands + add_subltc_commands + \
                    subltc_control_settings_commands_list
            # if substation transformer is present but there are no regulator controls on the subltc
            elif (orig_ckt_info['substation_xfmr'] is not None) and (not subltc_present_flag):
                pass_flag, add_subltc_commands = add_new_regcontrol_command(
                    xfmr_info_series=pd.Series(orig_ckt_info['substation_xfmr']),
                    default_regcontrol_settings=default_subltc_settings,
                    nominal_voltage=voltage_config["nominal_voltage"], **simulation_params)
                if not pass_flag:
                    logger.info("No convergence after adding regulator control at substation LTC. "
                                "Check if there is any setting that has convergence. Else remove substation LTC")
                    reload_dss_circuit(dss_file_list=dss_file_list, commands_list=dss_commands_list + add_subltc_commands,
                                       **simulation_params)
                # this needs to be collected again, since a new regulator control might have been added at the substation
                initial_sub_regcontrols_df = get_regcontrol_info(correct_PT_ratio=True,
                                                                 nominal_voltage=voltage_config["nominal_voltage"])
                # sweep through settings and identify best setting
                subltc_controls_df, subltc_control_settings_commands_list = sweep_and_choose_regcontrol_setting(
                    voltage_config=voltage_config, initial_regcontrols_df=initial_sub_regcontrols_df,
                    upper_limit=voltage_upper_limit, lower_limit=voltage_lower_limit, exclude_sub_ltc=False,
                    only_sub_ltc=True, dss_file_list=dss_file_list,
                    dss_commands_list=dss_commands_list + add_subltc_commands, **simulation_params)
                circuit_solve_and_check(raise_exception=True, **simulation_params)
                dss_commands_list = dss_commands_list + add_subltc_commands + subltc_control_settings_commands_list
            # if substation transformer, and reg controls are both present
            else:
                initial_sub_regcontrols_df = get_regcontrol_info(correct_PT_ratio=True,
                                                                 nominal_voltage=voltage_config["nominal_voltage"])
                # sweep through settings and identify best setting
                subltc_controls_df, subltc_control_settings_commands_list = sweep_and_choose_regcontrol_setting(
                    voltage_config=voltage_config, initial_regcontrols_df=initial_sub_regcontrols_df,
                    upper_limit=voltage_upper_limit, lower_limit=voltage_lower_limit, exclude_sub_ltc=False,
                    only_sub_ltc=True, dss_file_list=dss_file_list,
                    dss_commands_list=dss_commands_list, **simulation_params)
                circuit_solve_and_check(raise_exception=True, **simulation_params)
                dss_commands_list = dss_commands_list + subltc_control_settings_commands_list

        # determine voltage violations after changes
        bus_voltages_df, undervoltage_bus_list, overvoltage_bus_list, buses_with_violations = get_bus_voltages(
            voltage_upper_limit=voltage_upper_limit, voltage_lower_limit=voltage_lower_limit, **simulation_params)

        if len(buses_with_violations) >= min((100 * len(initial_buses_with_violations)), 500,
                                             len(dss.Circuit.AllBusNames())):
            # if number of buses with violations is very high, the loop for adding new regulators will take very long
            # so disable this block
            logger.info(f"At this point, number of buses with violations is {len(buses_with_violations)}, but initial "
                        f"number of buses with violations is {len(initial_buses_with_violations)}")
            logger.info("So disable option for addition of new regulators")
            voltage_config["place_new_regulators"] = False

        if voltage_config["place_new_regulators"] and (len(buses_with_violations) > 0):
            logger.info("Place new regulators.")
            # do compare objective function and choose best scenario, before placement of new regulators
            max_regulators = int(min(voltage_config["max_regulators"], len(buses_with_violations)))
            circuit_source = orig_ckt_info["source_bus"]
            regcontrol_cluster_commands = determine_new_regulator_location(max_regs=max_regulators,
                                                                           circuit_source=circuit_source,
                                                                           buses_with_violations=buses_with_violations,
                                                                           voltage_upper_limit=voltage_upper_limit,
                                                                           voltage_lower_limit=voltage_lower_limit, create_plot=False,
                                                                           voltage_config=voltage_config,
                                                                           default_regcontrol_settings=DEFAULT_REGCONTROL_SETTINGS, **simulation_params)
            dss_commands_list = dss_commands_list + regcontrol_cluster_commands
            logger.info("Settings sweep for existing reg control devices (other than sub LTC).")
            regcontrol_sweep_df = sweep_regcontrol_settings(voltage_config=voltage_config,
                                                            initial_regcontrols_df=orig_regcontrols_df,
                                                            voltage_upper_limit=voltage_upper_limit, voltage_lower_limit=voltage_lower_limit,
                                                            exclude_sub_ltc=True, only_sub_ltc=False, **simulation_params)
            # reload circuit after settings sweep
            reload_dss_circuit(dss_file_list=dss_file_list, commands_list=dss_commands_list,
                               **simulation_params)  # reload circuit after settings sweep
            regcontrols_df, regcontrol_settings_commands_list = choose_best_regcontrol_sweep_setting(
                regcontrol_sweep_df=regcontrol_sweep_df, initial_regcontrols_df=orig_regcontrols_df, **simulation_params)
            dss_commands_list = dss_commands_list + regcontrol_settings_commands_list

        dss_commands_list = dss_commands_list

    write_text_file(string_list=dss_commands_list, text_file_path=voltage_upgrades_dss_filepath)
    reload_dss_circuit(dss_file_list=[master_path, thermal_upgrades_dss_filepath, voltage_upgrades_dss_filepath],
                       commands_list=None, **simulation_params)
    if os.path.exists(feeder_stats_json_file):
        feeder_stats = read_json_as_dict(feeder_stats_json_file)
    else:
        feeder_stats = {}
    feeder_stats["after_upgrades"] = get_feeder_stats(dss)
    write_to_json(feeder_stats, feeder_stats_json_file)
    # reading new objects (after upgrades)
    new_ckt_info = get_circuit_info()
    new_xfmrs_df = get_thermal_equipment_info(compute_loading=False, equipment_type="transformer")
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
    processed_df[['equipment_type', 'name']] = processed_df['temp'].str.split('.', expand=True)
    processed_df = processed_df.set_index(['equipment_type', 'name']).reset_index()
    del processed_df["temp"]
    write_to_json(processed_df.to_dict('records'), output_json_voltage_upgrades_filepath)
    bus_voltages_df, undervoltage_bus_list, overvoltage_bus_list, buses_with_violations = get_bus_voltages(
        voltage_upper_limit=voltage_upper_limit, voltage_lower_limit=voltage_lower_limit, **simulation_params)
    
    xfmr_loading_df = get_thermal_equipment_info(compute_loading=True, upper_limit=thermal_config["transformer_upper_limit"], 
                                                equipment_type="transformer", timepoint_multipliers=timepoint_multipliers, 
                                                multiplier_type=multiplier_type, **simulation_params)
    line_loading_df = get_thermal_equipment_info(compute_loading=True, upper_limit=thermal_config["line_upper_limit"], 
                                                equipment_type="line", ignore_switch=ignore_switch, multiplier_type=multiplier_type,
                                                timepoint_multipliers=timepoint_multipliers, **simulation_params)
    overloaded_xfmr_list = list(xfmr_loading_df.loc[xfmr_loading_df['status'] == 'overloaded']['name'].unique())
    overloaded_line_list = list(line_loading_df.loc[line_loading_df['status'] == 'overloaded']['name'].unique())
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
    write_to_json(output_results, voltage_summary_file)
    