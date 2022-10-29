import re
import time
import seaborn as sns
import networkx as nx  # this module requires networkx version 2.6.3
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')
import logging
from sklearn.cluster import AgglomerativeClustering

from .common_functions import *
from .thermal_upgrade_functions import define_xfmr_object
from disco import timer_stats_collector
from disco.models.upgrade_cost_analysis_generic_output_model import VoltageUpgradesTechnicalResultModel
from opendssdirect import DSSException
from jade.utils.timing_utils import track_timing, Timer


logger = logging.getLogger(__name__)

NODE_COLORLEGEND = {'Load': {'node_color': 'blue', 'node_size': 20, "alpha": 1, "label": "Load"},
                'PV': {'node_color': 'orange', 'node_size': 50, "alpha": 0.8, "label": "PV"},
                'Transformer': {'node_color': 'purple', 'node_size': 250, "alpha": 0.75, "label": "Transformer"},
                'Circuit Source': {'node_color': 'black', 'node_size': 500, "alpha": 1, "label": "Source"},
                'Violation': {'node_color': 'red', 'node_size': 500, "alpha": 0.75, "label": "Violation"},   
                'Capacitor': {'node_color': 'green', 'node_size': 100, "alpha": 0.75, "label": "Capacitor"},                
                'Voltage Regulator': {'node_color': 'cyan', 'node_size': 1000, "alpha": 0.75, "label": "Voltage Regulator"},                
                }
EDGE_COLORLEGEND = {'Violation': {'edge_color': 'violet', 'edge_size': 75, 'alpha': 0.75, "label": "Line Violation"}}


def edit_capacitor_settings_for_convergence(voltage_config=None, control_command=''):
    """This function edits the dss command string with new capacitor settings, in case of convergence issues

    Parameters
    ----------
    voltage_config
    control_command

    Returns
    -------
    string
    """
    capacitor_settings = {}
    capacitor_settings["new_capON"] = round(
        (voltage_config["nominal_voltage"] - (voltage_config["cap_sweep_voltage_gap"] + 1) / 2), 1)
    capacitor_settings["new_capOFF"] = round(
        (voltage_config["nominal_voltage"] + (voltage_config["cap_sweep_voltage_gap"] + 1) / 2), 1)
    capacitor_settings["new_deadtime"] = 50
    capacitor_settings["new_delay"] = 50
    logger.info("Changed Initial On and Off Cap settings to avoid convergence issues ")

    new_control_command = control_command
    control_command = control_command.replace('New', 'Edit')
    control_command = re.sub("enabled=Yes", "enabled=No", control_command)
    check_dss_run_command(control_command)  # disable and run previous control command

    new_control_command = re.sub("DeadTime=\d+", 'DeadTime=' +
                                 str(capacitor_settings["new_deadtime"]), new_control_command)
    new_control_command = re.sub("Delay=\d+", 'Delay=' + str(capacitor_settings["new_delay"]), new_control_command)
    new_control_command = re.sub("ONsetting=\d+\.\d+", 'ONsetting=' +
                                 str(capacitor_settings["new_capON"]), new_control_command)
    new_control_command = re.sub("OFFsetting=\d+\.\d+", 'OFFsetting=' +
                                 str(capacitor_settings["new_capOFF"]), new_control_command)
    return new_control_command


def correct_capacitor_parameters(default_capacitor_settings, orig_capacitors_df, nominal_voltage,
                                 **kwargs):
    """Corrects cap control parameters: change to voltage controlled, correct PT ratio. Add cap control if not present

    Parameters
    ----------
    default_capacitor_settings
    orig_capacitors_df
    nominal_voltage

    Returns
    -------

    """
    # correct capacitor settings
    default_capcontrol_command = f"Type={default_capacitor_settings['cap_control']} " \
                                 f"ONsetting={default_capacitor_settings['capON']} " \
                                 f"OFFsetting={default_capacitor_settings['capOFF']} " \
                                 f"PTphase={default_capacitor_settings['PTphase']} " \
                                 f"Delay={default_capacitor_settings['capONdelay']} " \
                                 f"DelayOFF={default_capacitor_settings['capOFFdelay']} " \
                                 f"DeadTime={default_capacitor_settings['capdeadtime']} enabled=Yes"
    # Correct settings of those cap banks for which cap control object is available
    capacitors_commands_list = []
    capcontrol_present_df = orig_capacitors_df.loc[orig_capacitors_df['capcontrol_present'] == 'capcontrol']
    for index, row in capcontrol_present_df.iterrows():
        # if capcontrol is present, change to voltage controlled and apply default settings. (this also adds re-computed PTratio)
        if (row["capcontrol_type"].lower() != "voltage"):
            logger.info(f"Existing control changed to voltage controlled for {row['capcontrol_name']}")
            command_string = f"Edit CapControl.{row['capcontrol_name']} PTRatio={row['PTratio']} " \
                             f"{default_capcontrol_command}"
            check_dss_run_command(command_string)
            pass_flag = circuit_solve_and_check(raise_exception=False, **kwargs)
            if not pass_flag:
                command_string = edit_capacitor_settings_for_convergence(command_string)
                check_dss_run_command(command_string)
                # raise exception if no convergence even after change
                circuit_solve_and_check(raise_exception=True, **kwargs)
            capacitors_commands_list.append(command_string)
       
        # if it is already voltage controlled, modify PT ratio if new is different after re-computation
        if (row["capcontrol_type"].lower() == "voltage") and (round(row['PTratio'], 2) != round(row['old_PTratio'], 2)):
            orig_string = ' !original, corrected PTratio only'
            logger.info(f"PT ratio corrected for existing voltage controlled capcontrol {row['capcontrol_name']}.")
            command_string = f"Edit CapControl.{row['capcontrol_name']} PTRatio={row['PTratio']}" + orig_string
            check_dss_run_command(command_string)
            # this does not change original settings, so should not cause convergence
            circuit_solve_and_check(raise_exception=True, **kwargs)
            capacitors_commands_list.append(command_string)
            
    # if there are capacitors without cap control, add a voltage-controlled cap control
    lines_df = get_thermal_equipment_info(compute_loading=False, equipment_type="line")
    lines_df['bus1_name_only'] = lines_df['bus1'].str.split(".").str[0]
    lines_df['bus2_name_only'] = lines_df['bus2'].str.split(".").str[0]
    no_capcontrol_present_df = orig_capacitors_df.loc[orig_capacitors_df['capcontrol_present'] != 'capcontrol']
    for index, row in no_capcontrol_present_df.iterrows():
        logger.info(f"New capacitor control (voltage controlled) added for {row['capacitor_name']}.")
        capcontrol_name = "capcontrol" + row['capacitor_name']
        line_name = find_line_connected_to_capacitor(capacitor_row=row, lines_df=lines_df)
        default_pt_ratio = (row['kv'] * 1000) / nominal_voltage
        command_string = f"New CapControl.{capcontrol_name} element=Line.{line_name} " \
                         f"terminal={default_capacitor_settings['terminal']} capacitor={row['capacitor_name']} " \
                         f"PTRatio={default_pt_ratio} {default_capcontrol_command}"
        check_dss_run_command(command_string)
        pass_flag = circuit_solve_and_check(raise_exception=False, **kwargs)
        if not pass_flag:
            command_string = edit_capacitor_settings_for_convergence(command_string)
            check_dss_run_command(command_string)
            # raise exception if no convergence even after change
            circuit_solve_and_check(raise_exception=True, **kwargs)
        capacitors_commands_list.append(command_string)
    return capacitors_commands_list


def find_line_connected_to_capacitor(capacitor_row, lines_df):
    """Extract line name that has the same bus as capacitor
    
    First look at bus1 of lines.  If line bus1 names dont match, try looking at line bus2.
    After this, if a line is still not found, check feeder model to ensure network is connected.
    
    If capacitor phases < 3, then first try locating lines with bus name information. 
    If multiple lines are found, then search with bus connectivity information as well.
    
    For 3ph capacitors, it is assumed that it is connected to 3ph line.
    """
    cap_bus_name = capacitor_row["bus1"].split(".")[0]  # to get just bus name (e.g., extract b83 from b83.1)
    if capacitor_row["phases"] <= 3:  
        bus_identifier = "bus1"
        df = lines_df.loc[lines_df[f"{bus_identifier}_name_only"] == cap_bus_name]
        if df.empty:
            bus_identifier = "bus2"
            df = lines_df.loc[lines_df[f"{bus_identifier}_name_only"] == cap_bus_name]
        if df.empty:  # if a line is still not found, check feeder model to ensure network is connected
            raise Exception(f"Line not found at capacitor bus {capacitor_row['bus1']}. Check feeder model.")
        # if there are more than one lines connected to the bus, could be 1ph, so look for exact bus connection
        if len(df) > 1:
            df = df.loc[df[bus_identifier].str.contains(capacitor_row["bus1"])]
        line_name = df["name"].values[0]
    else:   # if 3ph capacitor, then assumed that it is connected to 3ph line
        df = lines_df.loc[lines_df['bus1_name_only'] == capacitor_row['bus1']]
        if df.empty:  # if line bus1 names dont match, try looking at line bus2
            df = lines_df.loc[lines_df['bus2_name_only'] == capacitor_row['bus1']]
        if df.empty:  # if a line is still not found, check feeder model to ensure network is connected
            raise Exception(f"Line not found at capacitor bus {capacitor_row['bus1']}. Check feeder model.")
        line_name = df['name'].values[0]
    return line_name


@track_timing(timer_stats_collector)
def sweep_capacitor_settings(voltage_config, initial_capacitors_df, default_capacitor_settings, voltage_upper_limit,
                             voltage_lower_limit, **kwargs):
    """This function sweeps through capacitor settings and returns dataframe of severity metrics for all the sweeps of capacitor controls with best settings.
       This function increases differences between cap ON and OFF voltages in user defined increments,
       default 1 volt, until upper and lower bounds are reached.

    Parameters
    ----------
    voltage_config
    initial_capacitors_df
    default_capacitor_settings
    upper_limit
    lower_limit

    Returns
    -------
    DataFrame
    """
    # This function increases differences between cap ON and OFF voltages in user defined increments,
    #  default 1 volt, until upper and lower bounds are reached.
    capacitor_sweep_list = []  # this list will contain severity of each capacitor setting sweep
    # get severity index for original/initial capacitor settings (ie before the settings sweep)
    temp_dict = {'cap_on_setting': 'original setting', 'cap_off_setting': 'original setting'}
    pass_flag = circuit_solve_and_check(raise_exception=False, **kwargs)
    if not pass_flag:  # if there is convergence issue at this setting, go onto next setting and dont save
        temp_dict['converged'] = False
    else:
        temp_dict['converged'] = True
    severity_dict = compute_voltage_violation_severity(
        voltage_upper_limit=voltage_upper_limit, voltage_lower_limit=voltage_lower_limit)
    temp_dict.update(severity_dict)
    capacitor_sweep_list.append(temp_dict)
    # start settings sweep
    cap_on_setting = default_capacitor_settings["capON"]
    cap_off_setting = default_capacitor_settings["capOFF"]
    cap_control_gap = voltage_config["capacitor_sweep_voltage_gap"]
    # Apply same capacitor ON and OFF settings to all capacitor controls and determine their impact
    # iterate over capacitor on and off settings while they are within voltage violation limits
    while (cap_on_setting > (voltage_lower_limit * voltage_config["nominal_voltage"])) or \
            (cap_off_setting < (voltage_upper_limit * voltage_config["nominal_voltage"])):
        temp_dict = {'cap_on_setting': cap_on_setting, 'cap_off_setting': cap_off_setting}
        for index, row in initial_capacitors_df.iterrows():  # apply settings to all capacitors
            check_dss_run_command(f"Edit CapControl.{row['capcontrol_name']} ONsetting={cap_on_setting} "
                            f"OFFsetting={cap_off_setting}")
            pass_flag = circuit_solve_and_check(raise_exception=False, **kwargs)
            if not pass_flag:  # if there is convergence issue at this setting, go onto next setting and dont save
                temp_dict['converged'] = False
                break
            else:
                temp_dict['converged'] = True
        bus_voltages_df, undervoltage_bus_list, overvoltage_bus_list, buses_with_violations = get_bus_voltages(
            voltage_upper_limit=voltage_upper_limit, voltage_lower_limit=voltage_lower_limit, raise_exception=False, **kwargs)
        severity_dict = compute_voltage_violation_severity(
            voltage_upper_limit=voltage_upper_limit, voltage_lower_limit=voltage_lower_limit)
        temp_dict.update(severity_dict)
        capacitor_sweep_list.append(temp_dict)
        if (cap_on_setting - cap_control_gap / 2) <= (voltage_lower_limit * voltage_config["nominal_voltage"]):
            cap_on_setting = voltage_lower_limit * voltage_config["nominal_voltage"]
        else:
            cap_on_setting = cap_on_setting - cap_control_gap / 2
        if (cap_off_setting + cap_control_gap / 2) >= (voltage_upper_limit * voltage_config["nominal_voltage"]):
            cap_off_setting = voltage_upper_limit * voltage_config["nominal_voltage"]
        else:
            cap_off_setting = cap_off_setting + cap_control_gap / 2
    capacitor_sweep_df = pd.DataFrame(capacitor_sweep_list)
    return capacitor_sweep_df


def choose_best_capacitor_sweep_setting(capacitor_sweep_df, initial_capacitors_df, deciding_field, **kwargs):
    """This function takes the dataframe containing severity metrics, identifies the best cap control setting out
    of all the sweeps and returns dataframe of capacitor controls with best settings

    Parameters
    ----------
    capacitor_sweep_df
    initial_capacitors_df

    Returns
    -------
    DataFrame
    """
    # start with assumption that original setting is best setting
    original_setting = capacitor_sweep_df.loc[capacitor_sweep_df['cap_on_setting'] == 'original setting'].iloc[0]
    min_severity_setting = capacitor_sweep_df.loc[capacitor_sweep_df[deciding_field].idxmin()]
    setting_type = ''
    # if min severity is greater than or same as severity of original setting,
    # then just assign original setting as min_severity_setting
    if min_severity_setting[deciding_field] >= original_setting[deciding_field]:
        capacitors_df = initial_capacitors_df.copy()  # here best_setting is initial settings
        logger.info("Original capacitor settings are best. No need to change capacitor settings.")
        setting_type = 'initial_setting'
    else:
        logger.info("Capacitor settings changed.")
        # apply same best setting to all capacitors
        capacitors_df = initial_capacitors_df.copy()
        capacitors_df['ONsetting'] = min_severity_setting['cap_on_setting']
        capacitors_df['OFFsetting'] = min_severity_setting['cap_off_setting']
    properties_list = ["ONsetting", "OFFsetting"]  # list of properties to be edited in commands
    capacitor_settings_commands_list = create_capcontrol_settings_commands(properties_list=properties_list,
                                                                           capacitors_df=capacitors_df,
                                                                           creation_action='Edit')
    for command_string in capacitor_settings_commands_list:
        check_dss_run_command(command_string)
    circuit_solve_and_check(raise_exception=True, **kwargs)
    if setting_type == 'initial_setting':  # if initial settings are best, no need to return command with settings
        capacitor_settings_commands_list = []
    return capacitors_df, capacitor_settings_commands_list


def create_capcontrol_settings_commands(properties_list, capacitors_df, creation_action='New'):
    """This function creates a list of capacitor control commands, based on the properties list and cap dataframe passed

    Parameters
    ----------
    properties_list
    capacitors_df
    creation_action

    Returns
    -------
    list
    """
    capacitor_commands_list = []
    if properties_list is None:
        properties_list = ["ONsetting", "OFFsetting"]
    for index, row in capacitors_df.iterrows():
        command_string = f"{creation_action} CapControl.{row['capcontrol_name']}"
        for property_name in properties_list:
            command_string = command_string + f" {property_name}={row[property_name]}"
        capacitor_commands_list.append(command_string)
    return capacitor_commands_list


def determine_capacitor_upgrades(voltage_upper_limit, voltage_lower_limit, default_capacitor_settings, orig_capacitors_df, 
                                 voltage_config, deciding_field, **kwargs):
    """This function corrects capacitor parameters, sweeps through capacitor settings and determines the best capacitor setting.
    It returns the dss commands associated with all these actions
    """
    fig_folder = kwargs.get("fig_folder", None)
    create_plots = kwargs.get("create_plots", False)
    circuit_source = kwargs.get("circuit_source", None)
    title = kwargs.get("title", "Bus violations after existing capacitor sweep module_")
    
    capacitor_dss_commands = []
    logger.info("Capacitors are present in the network. Perform capacitor bank control modifications.")
    capcontrol_parameter_commands_list = correct_capacitor_parameters(
        default_capacitor_settings=default_capacitor_settings, orig_capacitors_df=orig_capacitors_df,
        nominal_voltage=voltage_config['nominal_voltage'], **kwargs)
    capacitor_dss_commands = capacitor_dss_commands + capcontrol_parameter_commands_list
    bus_voltages_df, undervoltage_bus_list, overvoltage_bus_list, buses_with_violations = get_bus_voltages(
        voltage_upper_limit=voltage_upper_limit, voltage_lower_limit=voltage_lower_limit, **kwargs)
    if len(buses_with_violations) > 0:
        # get capacitors dataframe before any settings changes are made
        nosetting_changes_capacitors_df = get_capacitor_info(correct_PT_ratio=False)
        # sweep through all capacitor settings, and store objective function
        capacitor_sweep_df = sweep_capacitor_settings(voltage_config=voltage_config,
                                                        initial_capacitors_df=nosetting_changes_capacitors_df,
                                                        default_capacitor_settings=default_capacitor_settings,
                                                        voltage_upper_limit=voltage_upper_limit,
                                                        voltage_lower_limit=voltage_lower_limit, **kwargs)
        # choose best capacitor settings
        capacitors_df, capcontrol_settings_commands_list = choose_best_capacitor_sweep_setting(
            capacitor_sweep_df=capacitor_sweep_df, initial_capacitors_df=nosetting_changes_capacitors_df,
            deciding_field=deciding_field, **kwargs)
        capacitor_dss_commands = capacitor_dss_commands + capcontrol_settings_commands_list
    # determine voltage violations after capacitor changes
    bus_voltages_df, undervoltage_bus_list, overvoltage_bus_list, buses_with_violations = get_bus_voltages(
        voltage_upper_limit=voltage_upper_limit, voltage_lower_limit=voltage_lower_limit, **kwargs)   
    if (fig_folder is not None) and create_plots:
            plot_voltage_violations(fig_folder=fig_folder, title=title+
                                    str(len(buses_with_violations)), buses_with_violations=buses_with_violations, circuit_source=circuit_source, enable_detailed=True)
    
    return capacitor_dss_commands


def get_capacitor_upgrades(orig_capacitors_df, new_capacitors_df):
    """Postprocessing function to collect capacitor upgrades information, used for cost function.
    """
    if len(orig_capacitors_df) > 0:
        orig_capcontrols = orig_capacitors_df.set_index('capacitor_name').transpose().to_dict()
    else:
        orig_capcontrols = {}
    if len(new_capacitors_df) > 0:
        new_capcontrols = new_capacitors_df.set_index('capacitor_name').transpose().to_dict()
    else:
        new_capcontrols = {}
    
    final_cap_upgrades = {}
    processed_outputs = []
    # STEP 1: account for any new controllers added (which are not there in original)
    change = compare_dict(orig_capcontrols, new_capcontrols, properties_to_check=["capcontrol_present", "capcontrol_name"])
    new_addition = list(change.keys())    
    
    # STEP 2: compare controllers that exist in both: original and new- and get difference
    properties_to_check = ['capacitor_name', 'phases', 'kvar', 'kv', 'conn',
       'normamps', 'emergamps', 'basefreq', 'equipment_type', 
       'capcontrol_name', 'capcontrol_type', 'PTratio', 'CTratio', 'ONsetting', 'OFFsetting',
       'Delay', 'Vmax', 'Vmin', 'DelayOFF', 'DeadTime',
       'basefreq', 'enabled', 'capcontrol_present', 'old_PTratio']
    change = compare_dict(orig_capcontrols, new_capcontrols, properties_to_check)
    modified_capacitors = list(change.keys())
    # remove any new addition capcontrols capacitors from modified list
    modified_capacitors = list(set(modified_capacitors) - set(new_addition))
    # # this checks for addition of new capacitors - can be used if needed in future
    # new_addition = list(set(new_capcontrols.keys()) -
    #                     (set(orig_capcontrols.keys()) & set(new_capcontrols.keys())))
    cap_upgrades = [*modified_capacitors, *new_addition]  # combining these two lists to get upgraded capacitors
    if cap_upgrades:
        for cap_name in cap_upgrades:
            final_cap_upgrades["cap_name"] = "Capacitor." + cap_name
            final_cap_upgrades["ctrl_name"] = new_capcontrols[cap_name]["capcontrol_name"]
            final_cap_upgrades["cap_kvar"] = new_capcontrols[cap_name]["kvar"]
            final_cap_upgrades["cap_kv"] = new_capcontrols[cap_name]["kv"]
            final_cap_upgrades["cap_on"] = new_capcontrols[cap_name]["ONsetting"]
            final_cap_upgrades["cap_off"] = new_capcontrols[cap_name]["OFFsetting"]
            final_cap_upgrades["ctrl_type"] = new_capcontrols[cap_name]["capcontrol_type"]
            final_cap_upgrades["cap_settings"] = True
            # if there are differences between original and new controllers
            if cap_name in modified_capacitors:
                # if control type in original controller is voltage, only settings are changed
                if orig_capcontrols[cap_name]["capcontrol_type"].lower().startswith("volt"):
                    final_cap_upgrades["ctrl_added"] = False
                # if original controller type was current, new controller (voltage type) is said to be added
                elif orig_capcontrols[cap_name]["capcontrol_type"].lower().startswith("current"):
                    final_cap_upgrades["ctrl_added"] = True
            # if there are new controllers
            elif cap_name in new_addition:
                final_cap_upgrades["ctrl_added"] = True
        processed_outputs.append(
            VoltageUpgradesTechnicalResultModel(**{
                "equipment_type": final_cap_upgrades["cap_name"].split(".")[0],
                "name": final_cap_upgrades["cap_name"].split(".")[1],
                "new_controller_added": final_cap_upgrades["ctrl_added"],
                "controller_settings_modified": final_cap_upgrades["cap_settings"],
                "final_settings": {
                    "kvar": final_cap_upgrades["cap_kvar"],
                    "kv": final_cap_upgrades["cap_kv"],
                    "capcontrol_name": final_cap_upgrades["ctrl_name"],
                    "capcontrol_type": final_cap_upgrades["ctrl_type"],
                    "ONsetting": final_cap_upgrades["cap_on"],
                    "OFFsetting": final_cap_upgrades["cap_off"]
                     },
                "new_transformer_added": False,
                "at_substation": False,
        }))
    return processed_outputs


def compute_voltage_violation_severity(voltage_upper_limit, voltage_lower_limit, **kwargs):
    """This function computes voltage violation severity metrics, based on bus voltages

    Parameters
    ----------
    bus_voltages_df

    Returns
    -------
    Dict
    """
    bus_voltages_df, undervoltage_bus_list, overvoltage_bus_list, buses_with_violations = get_bus_voltages(
        voltage_upper_limit=voltage_upper_limit, voltage_lower_limit=voltage_lower_limit, raise_exception=False, **kwargs)
    deviation_severity = bus_voltages_df['min_voltage_deviation'].sum() + bus_voltages_df['max_voltage_deviation'].sum()
    undervoltage_bus_list = list(
        bus_voltages_df.loc[bus_voltages_df['undervoltage_violation'] == True]['name'].unique())
    overvoltage_bus_list = list(bus_voltages_df.loc[bus_voltages_df['overvoltage_violation'] == True]['name'].unique())
    buses_with_violations = undervoltage_bus_list + overvoltage_bus_list
    objective_function = len(buses_with_violations) * deviation_severity
    severity_dict = {'deviation_severity': deviation_severity,
                     'number_buses_with_violations': len(buses_with_violations),
                     'objective_function': objective_function}
    return severity_dict


def correct_regcontrol_parameters(orig_regcontrols_df, **kwargs):
    """This function corrects regcontrol ptratio is different from original. And generates commands list

    Parameters
    ----------
    orig_regcontrols_df

    Returns
    -------
    list
    """
    # correct regcontrol parameters settings
    default_regcontrol_command = " enabled=Yes"
    orig_string = ' !original, corrected PTratio only'
    regcontrols_commands_list = []
    for index, row in orig_regcontrols_df.iterrows():
        if round(row['ptratio'], 2) != round(row['old_ptratio'], 2):
            command_string = f"Edit RegControl.{row['name']} ptratio={row['ptratio']}" + default_regcontrol_command\
                             + orig_string
            check_dss_run_command(command_string)
            circuit_solve_and_check(raise_exception=True, **kwargs)
            # this does not change original settings, so should not cause convergence issues
            regcontrols_commands_list.append(command_string)
    return regcontrols_commands_list


@track_timing(timer_stats_collector)
def sweep_regcontrol_settings(voltage_config, initial_regcontrols_df, voltage_upper_limit, voltage_lower_limit,
                              exclude_sub_ltc=True, only_sub_ltc=False, **kwargs):
    """This function increases differences vreg in user defined increments, until upper and lower bounds are reached.
    At a time, same settings are applied to all regulator controls

    Parameters
    ----------
    voltage_config
    initial_regcontrols_df
    upper_limit
    lower_limit
    exclude_sub_ltc
    only_sub_ltc

    Returns
    -------

    """
    if exclude_sub_ltc:
        initial_df = initial_regcontrols_df.loc[initial_regcontrols_df['at_substation_xfmr_flag'] == False]
    if only_sub_ltc:
        initial_df = initial_regcontrols_df.loc[initial_regcontrols_df['at_substation_xfmr_flag'] == True]
    regcontrol_sweep_list = []  # this list will contain severity of each setting sweep
    # get severity index for original/initial settings (ie before the settings sweep)
    temp_dict = {'setting': 'original'}
    bus_voltages_df, undervoltage_bus_list, overvoltage_bus_list, buses_with_violations = get_bus_voltages(
        voltage_upper_limit=voltage_upper_limit, voltage_lower_limit=voltage_lower_limit, raise_exception=False, **kwargs)
    pass_flag = circuit_solve_and_check(raise_exception=False, **kwargs)
    if not pass_flag:  # if there is convergence issue at this setting, go onto next setting and dont save
        temp_dict['converged'] = False
    else:
        temp_dict['converged'] = True
    severity_dict = compute_voltage_violation_severity(
        voltage_upper_limit=voltage_upper_limit, voltage_lower_limit=voltage_lower_limit)
    temp_dict.update(severity_dict)
    regcontrol_sweep_list.append(temp_dict)
    # generate list of voltage setpoints
    vregs_list = []
    vreg = voltage_lower_limit * voltage_config["nominal_voltage"]
    while vreg < voltage_upper_limit * voltage_config["nominal_voltage"]:
        vregs_list.append(vreg)
        vreg += voltage_config["reg_v_delta"]
    # start settings sweep
    for vreg in vregs_list:
        for band in voltage_config["reg_control_bands"]:
            temp_dict = {'setting': f"{vreg}_{band}", 'vreg': vreg, 'band': band}
            # Apply same settings to all controls and determine their impact
            for index, row in initial_df.iterrows():
                logger.debug(f"{vreg}_{band}")
                check_dss_run_command(f"Edit RegControl.{row['name']} vreg={vreg} band={band}")
                pass_flag = circuit_solve_and_check(raise_exception=False, **kwargs)
                if not pass_flag:  # if there is convergence issue at this setting, go onto next setting and dont save
                    temp_dict['converged'] = False
                    break
                else:
                    temp_dict['converged'] = True
                    try:
                        bus_voltages_df, undervoltage_bus_list, overvoltage_bus_list, buses_with_violations = get_bus_voltages(
                            voltage_upper_limit=voltage_upper_limit,
                            voltage_lower_limit=voltage_lower_limit, **kwargs)
                    except:  # catch convergence error
                        temp_dict['converged'] = False
                        break
                    severity_dict = compute_voltage_violation_severity(
                        voltage_upper_limit=voltage_upper_limit, voltage_lower_limit=voltage_lower_limit)
                    temp_dict.update(severity_dict)
                regcontrol_sweep_list.append(temp_dict)
    regcontrol_sweep_df = pd.DataFrame(regcontrol_sweep_list)
    return regcontrol_sweep_df


def choose_best_regcontrol_sweep_setting(regcontrol_sweep_df, initial_regcontrols_df, deciding_field, exclude_sub_ltc=True,
                                         only_sub_ltc=False, **kwargs):
    """This function takes the dataframe containing severity metrics, identifies the best regcontrol setting out
    of all the sweeps and returns dataframe of regcontrols with best settings

    Parameters
    ----------
    regcontrol_sweep_df
    initial_regcontrols_df

    Returns
    -------
    DataFrame
    """
    if exclude_sub_ltc:
        initial_df = initial_regcontrols_df.loc[initial_regcontrols_df['at_substation_xfmr_flag'] == False]
    if only_sub_ltc:
        initial_df = initial_regcontrols_df.loc[initial_regcontrols_df['at_substation_xfmr_flag'] == True]
    # start with assumption that original setting is best setting
    original_setting = regcontrol_sweep_df.loc[regcontrol_sweep_df['setting'] == 'original'].iloc[0]
    regcontrol_sweep_df = regcontrol_sweep_df.loc[regcontrol_sweep_df['converged'] == True]
    min_severity_setting = regcontrol_sweep_df.loc[regcontrol_sweep_df[deciding_field].idxmin()]
    # if min severity is greater than or same as that of original setting,
    # then just assign original setting as min_severity_setting
    if (min_severity_setting[deciding_field] >= original_setting[deciding_field]) and (original_setting['converged']):
        setting_type = 'original'
        regcontrols_df = initial_df.copy()  # here best_setting is initial settings
    else:
        setting_type = 'changed'
        regcontrols_df = initial_df.copy()
        regcontrols_df['vreg'] = min_severity_setting['vreg']
        regcontrols_df['band'] = min_severity_setting['band']
    properties_list = ["vreg", "band"]  # list of properties to be edited in commands
    regcontrol_settings_commands_list = create_regcontrol_settings_commands(properties_list=properties_list,
                                                                            regcontrols_df=regcontrols_df,
                                                                            creation_action='Edit')
    for command_string in regcontrol_settings_commands_list:
        check_dss_run_command(command_string)
    circuit_solve_and_check(raise_exception=True, **kwargs)
    if setting_type == 'original':  # if original settings, no need to add to upgrades commands list
        regcontrol_settings_commands_list = []
        logger.info("Original Regulator control settings are the best.")
    return regcontrols_df, regcontrol_settings_commands_list


def create_regcontrol_settings_commands(properties_list, regcontrols_df, creation_action='New'):
    """This function creates a list of regcontrol commands, based on the properties list and regcontrol dataframe passed

    Parameters
    ----------
    properties_list
    regcontrols_df
    creation_action

    Returns
    -------
    list
    """
    regcontrol_commands_list = []
    if properties_list is None:
        properties_list = ["vreg", "band"]
    for index, row in regcontrols_df.iterrows():
        command_string = f"{creation_action} RegControl.{row['name']}"
        for property_name in properties_list:
            command_string = command_string + f" {property_name}={row[property_name]}"
        regcontrol_commands_list.append(command_string)
    return regcontrol_commands_list


def add_new_regcontrol_command(xfmr_info_series, default_regcontrol_settings, nominal_voltage, action_type='New', **kwargs):
    """This function runs and returns the dss command to add regulator control at a transformer.
    It also solves the circuit and calculates voltage bases after the regulator has been added to the circuit.
    It calls another function to create the dss command.

    Parameters
    ----------
    xfmr_info_series
    default_regcontrol_settings
    nominal_voltage

    Returns
    -------

    """
    command_list = []
    regcontrol_info_series = pd.Series(default_regcontrol_settings)
    regcontrol_info_series['transformer'] = xfmr_info_series['name']
    regcontrol_info_series['winding'] = xfmr_info_series['windings']

    # use secondary voltage to define ptratio
    # If the winding is Wye, the line-to-neutral voltage is used to compute PTratio.
    # Else, the line-to-line voltage is used.
    sec_conn = xfmr_info_series['conns'][-1]
    if sec_conn.lower() == 'wye':
        sec_voltage = xfmr_info_series['kVs'][-1] / (math.sqrt(3))
    else:
        sec_voltage = xfmr_info_series['kVs'][-1]
     # If the winding is Wye, the line-to-neutral voltage is used. Else, the line-to-line voltage is used.
    # Here, bus kV is taken from Bus.kVBase
    dss.Circuit.SetActiveBus(xfmr_info_series['bus'].split('.')[0])  # get base kV of node at which regulator is placed.
    regcontrol_info_series["ptratio"] = (dss.Bus.kVBase() * 1000) / nominal_voltage
    
    # use the primary bus to define name
    curr_time = str(time.time())
    # timestamp is added to name to ensure it is unique
    time_stamp = curr_time.split(".")[0] + "_" + curr_time.split(".")[1]
    regcontrol_info_series['regcontrol_name'] = 'new_regcontrol_' + xfmr_info_series['bus_names_only'][0] + "_" + time_stamp
    temp_df = get_regcontrol_info()
    if not temp_df.empty:
        enabled_regcontrol_exists = len(
            temp_df.loc[(temp_df['name'] == regcontrol_info_series['regcontrol_name']) & (temp_df['enabled'].str.lower() == "yes")]) > 0
        if enabled_regcontrol_exists:
            logger.debug(f"Enabled regcontrol already exists: {regcontrol_info_series['name']}")
            return None
    if not temp_df.empty:
        disabled_regcontrol_exists = len(
            temp_df.loc[(temp_df['name'] == regcontrol_info_series['regcontrol_name']) & (temp_df['enabled'].str.lower() == "no")]) > 0
        if disabled_regcontrol_exists:
            action_type = 'Edit'
    new_regcontrol_command = define_regcontrol_object(regcontrol_name=regcontrol_info_series['regcontrol_name'],
                                                      action_type=action_type, regcontrol_info_series=regcontrol_info_series,
                                                      general_property_list=regcontrol_info_series["properties_to_be_defined"])
    check_dss_run_command(new_regcontrol_command)  # run command
    check_dss_run_command('CalcVoltageBases')
    # max control iterations could exceed here as well, when adding a new regulator
    pass_flag = circuit_solve_and_check(raise_exception=False, calcvoltagebases=True, **kwargs)  # solve circuit
    command_list.append(new_regcontrol_command)
    return {'command_list': command_list, 'new_regcontrol_name': regcontrol_info_series['regcontrol_name'], 'pass_flag': pass_flag}


def define_regcontrol_object(regcontrol_name, action_type, regcontrol_info_series, general_property_list=None):
    """This function is used to create a command string to define an opendss regcontrol object at a given bus.
    A transformer should already exist at this bus. Regulator control will be placed on this transformer.

    Parameters
    ----------
    regcontrol_name
    action_type
    regcontrol_info_series
    general_property_list

    Returns
    -------

    """
    # transformer should exist at this bus. Reg control should not exist on the transformer
    command_string = f"{action_type} RegControl.{regcontrol_name}"
    if action_type == "New":
        command_string = command_string + f" transformer={regcontrol_info_series['transformer']}"
    # these properties contain regcontrol data (refer OpenDSS manual for more information on these parameters)
    if general_property_list is None:
        general_property_list = ['winding', 'ptratio', 'band', 'vreg', 'delay']
    for property_name in general_property_list:
        temp_s = f" {property_name}={regcontrol_info_series[property_name]}"
        command_string = command_string + temp_s
    command_string = command_string + " enabled=Yes"
    return command_string


def sweep_and_choose_regcontrol_setting(voltage_config, initial_regcontrols_df, upper_limit, lower_limit, 
                                        dss_file_list, deciding_field, correct_parameters=False, exclude_sub_ltc=True, 
                                        only_sub_ltc=False, previous_dss_commands_list=None, **kwargs):
    """This function combines the regcontrol settings sweep and choosing of best setting.

    Parameters
    ----------
    voltage_config
    initial_regcontrols_df
    upper_limit
    lower_limit
    exclude_sub_ltc
    only_sub_ltc
    dss_file_list
    dss_commands_list

    Returns
    -------

    """
    fig_folder = kwargs.get("fig_folder", None)
    create_plots = kwargs.get("create_plots", False)
    circuit_source = kwargs.get("circuit_source", None)
    title = kwargs.get("title", None)
    
    reg_sweep_commands_list = []
    if correct_parameters:
        # first correct regcontrol parameters (ptratio) including substation LTC, if present
        regcontrols_parameter_command_list = correct_regcontrol_parameters(orig_regcontrols_df=initial_regcontrols_df,
                                                                            **kwargs)
        reg_sweep_commands_list = regcontrols_parameter_command_list
    # sweep through settings and identify best setting
    regcontrol_sweep_df = sweep_regcontrol_settings(voltage_config=voltage_config,
                                                    initial_regcontrols_df=initial_regcontrols_df,
                                                    voltage_upper_limit=upper_limit, voltage_lower_limit=lower_limit,
                                                    exclude_sub_ltc=exclude_sub_ltc, only_sub_ltc=only_sub_ltc,
                                                    **kwargs)
    # reload circuit after settings sweep
    reload_dss_circuit(dss_file_list=dss_file_list, commands_list=previous_dss_commands_list+reg_sweep_commands_list, **kwargs)
    # choose best setting
    regcontrols_df, regcontrol_settings_commands_list = choose_best_regcontrol_sweep_setting(
        regcontrol_sweep_df=regcontrol_sweep_df, initial_regcontrols_df=initial_regcontrols_df,
        exclude_sub_ltc=exclude_sub_ltc, only_sub_ltc=only_sub_ltc, deciding_field=deciding_field, **kwargs)
    reg_sweep_commands_list = reg_sweep_commands_list + regcontrol_settings_commands_list
    if (fig_folder is not None) and create_plots and (title is not None):
        bus_voltages_df, undervoltage_bus_list, overvoltage_bus_list, buses_with_violations = get_bus_voltages(
            voltage_upper_limit=upper_limit, voltage_lower_limit=lower_limit, **kwargs)
        plot_voltage_violations(fig_folder=fig_folder, title=title+
                                    str(len(buses_with_violations)), buses_with_violations=buses_with_violations, circuit_source=circuit_source, enable_detailed=True)

    return regcontrols_df, reg_sweep_commands_list


def determine_substation_ltc_upgrades(voltage_upper_limit, voltage_lower_limit, orig_regcontrols_df, orig_ckt_info, circuit_source, 
                                      default_subltc_settings, voltage_config, dss_file_list, comparison_dict, deciding_field, 
                                      previous_dss_commands_list, best_setting_so_far, **kwargs):
    """Function determine substation LTC upgrades:
    # Use this block for adding a substation LTC, correcting its settings and running a sub LTC settings sweep.
        # if LTC exists, first try to correct its non set point simulation settings.
        # If this does not correct everything, correct its set points through a sweep.
        # If LTC does not exist, add one including a xfmr if required, then do a settings sweep if required
    """
    fig_folder = kwargs.get("fig_folder", None)
    create_plots = kwargs.get("create_plots", False)
    
    results_dict = {}
    all_commands_list = previous_dss_commands_list
    subltc_upgrade_commands = []
    logger.info("Enter Substation LTC module.")
    if orig_regcontrols_df.empty:  # if there are no reg controls
        subltc_present_flag = False
    else:
        subltc_present_flag = (
            len(orig_regcontrols_df.loc[orig_regcontrols_df['at_substation_xfmr_flag'] == True]) > 0)
    # if there is no substation transformer in the network
    if orig_ckt_info['substation_xfmr'] is None:
        logger.info("Substation transformer does not exist. So adding transformer and regcontrol on it.")
        # check add substation transformer and add ltc reg control on it
        new_subxfmr_added_dict = add_new_node_and_xfmr(action_type='New', node=circuit_source, circuit_source=circuit_source, 
                                                    xfmr_conn_type="wye" ,**kwargs)
        add_subxfmr_commands = new_subxfmr_added_dict['commands_list']
        comparison_dict["temp_afterxfmr"] = compute_voltage_violation_severity(voltage_upper_limit=voltage_upper_limit, 
                                                                               voltage_lower_limit=voltage_lower_limit, **kwargs)
        updated_ckt_info = get_circuit_info()
        bus_voltages_df, undervoltage_bus_list, overvoltage_bus_list, buses_with_violations = get_bus_voltages(voltage_upper_limit=voltage_upper_limit, 
                                                                                                               voltage_lower_limit=voltage_lower_limit, **kwargs)
        new_subltc_added_dict = add_new_regcontrol_command(
            xfmr_info_series=pd.Series(updated_ckt_info['substation_xfmr']),
            default_regcontrol_settings=default_subltc_settings,
            nominal_voltage=voltage_config["nominal_voltage"], **kwargs)
        comparison_dict["temp_afterltc"] = compute_voltage_violation_severity(voltage_upper_limit=voltage_upper_limit, voltage_lower_limit=voltage_lower_limit, **kwargs)
        add_subltc_commands = new_subltc_added_dict["command_list"]
        if not new_subltc_added_dict["pass_flag"]:
            logger.info("No convergence after adding regulator control at substation LTC. "
                        "Check if there is any setting that has convergence. Else remove substation LTC")
            reload_dss_circuit(dss_file_list=dss_file_list, commands_list=all_commands_list + add_subxfmr_commands + add_subltc_commands,
                                calcvoltagebases=True, **kwargs)
        # this needs to be collected again, since a new regulator control might have been added at the substation
        initial_sub_regcontrols_df = get_regcontrol_info(correct_PT_ratio=True,
                                                            nominal_voltage=voltage_config["nominal_voltage"])
        # sweep through settings and identify best setting
        subltc_controls_df, subltc_control_settings_commands_list = sweep_and_choose_regcontrol_setting(
            voltage_config=voltage_config, initial_regcontrols_df=initial_sub_regcontrols_df, deciding_field=deciding_field,
            upper_limit=voltage_upper_limit, lower_limit=voltage_lower_limit, exclude_sub_ltc=False,
            only_sub_ltc=True, dss_file_list=dss_file_list,
            previous_dss_commands_list=all_commands_list + add_subxfmr_commands + add_subltc_commands, **kwargs)
        circuit_solve_and_check(raise_exception=True, **kwargs)
        subltc_upgrade_commands = add_subxfmr_commands + add_subltc_commands + subltc_control_settings_commands_list
        all_commands_list = all_commands_list + subltc_upgrade_commands
    # if substation transformer is present but there are no regulator controls on the subltc
    elif (orig_ckt_info['substation_xfmr'] is not None) and (not subltc_present_flag):
        logger.info("Substation transformer exists, but there are no regulator controls on it. Adding..")
        
        new_subltc_added_dict = add_new_regcontrol_command(
            xfmr_info_series=pd.Series(updated_ckt_info['substation_xfmr']),
            default_regcontrol_settings=default_subltc_settings,
            nominal_voltage=voltage_config["nominal_voltage"], **kwargs)
        comparison_dict["temp_afterltc"] = compute_voltage_violation_severity(voltage_upper_limit=voltage_upper_limit, voltage_lower_limit=voltage_lower_limit, **kwargs)
        add_subltc_commands = new_subltc_added_dict["command_list"]
        if not new_subltc_added_dict["pass_flag"]:
            logger.info("No convergence after adding regulator control at substation LTC. "
                        "Check if there is any setting that has convergence. Else remove substation LTC")
            reload_dss_circuit(dss_file_list=dss_file_list, commands_list=all_commands_list + add_subltc_commands,
                                **kwargs)
        # this needs to be collected again, since a new regulator control might have been added at the substation
        initial_sub_regcontrols_df = get_regcontrol_info(correct_PT_ratio=True,
                                                            nominal_voltage=voltage_config["nominal_voltage"])
        # sweep through settings and identify best setting
        subltc_controls_df, subltc_control_settings_commands_list = sweep_and_choose_regcontrol_setting(
            voltage_config=voltage_config, initial_regcontrols_df=initial_sub_regcontrols_df, deciding_field=deciding_field,
            upper_limit=voltage_upper_limit, lower_limit=voltage_lower_limit, exclude_sub_ltc=False,
            only_sub_ltc=True, dss_file_list=dss_file_list,
            previous_dss_commands_list=all_commands_list + add_subltc_commands, **kwargs)
        circuit_solve_and_check(raise_exception=True, **kwargs)
        subltc_upgrade_commands = add_subltc_commands + subltc_control_settings_commands_list
        all_commands_list = all_commands_list + subltc_upgrade_commands
    # if substation transformer, and reg controls are both present
    else:
        logger.info("Substation transformer and regcontrol exists on it.")
        initial_sub_regcontrols_df = get_regcontrol_info(correct_PT_ratio=True,
                                                            nominal_voltage=voltage_config["nominal_voltage"])
        # sweep through settings and identify best setting
        subltc_controls_df, subltc_control_settings_commands_list = sweep_and_choose_regcontrol_setting(
            voltage_config=voltage_config, initial_regcontrols_df=initial_sub_regcontrols_df, deciding_field=deciding_field,
            upper_limit=voltage_upper_limit, lower_limit=voltage_lower_limit, exclude_sub_ltc=False,
            only_sub_ltc=True, dss_file_list=dss_file_list,
            previous_dss_commands_list=all_commands_list, **kwargs)
        circuit_solve_and_check(raise_exception=True, **kwargs)
        subltc_upgrade_commands = subltc_control_settings_commands_list
        all_commands_list = all_commands_list + subltc_upgrade_commands
    
    reload_dss_circuit(dss_file_list=dss_file_list, commands_list=all_commands_list, calcvoltagebases=True, **kwargs)
    # determine voltage violations after changes
    bus_voltages_df, undervoltage_bus_list, overvoltage_bus_list, buses_with_violations = get_bus_voltages(
        voltage_upper_limit=voltage_upper_limit, voltage_lower_limit=voltage_lower_limit, **kwargs)
    comparison_dict["after_sub_ltc_checking"] = compute_voltage_violation_severity(voltage_upper_limit=voltage_upper_limit, 
                                                                                    voltage_lower_limit=voltage_lower_limit, **kwargs)
    if comparison_dict["after_sub_ltc_checking"][deciding_field] < comparison_dict[best_setting_so_far][deciding_field]:
        best_setting_so_far = "after_sub_ltc_checking"
        if (fig_folder is not None) and create_plots:
            plot_voltage_violations(fig_folder=fig_folder, title="Bus violations after substation ltc module_"+
                                    str(len(buses_with_violations)), buses_with_violations=buses_with_violations, circuit_source=circuit_source, enable_detailed=True)
    else:
        all_commands_list = list(set(all_commands_list) - set(subltc_upgrade_commands))
        subltc_upgrade_commands = []
        reload_dss_circuit(dss_file_list=dss_file_list, commands_list=all_commands_list, **kwargs)
    
    if (best_setting_so_far == "after_sub_ltc_checking") and (len(buses_with_violations) > 0):
        # after this, also run settings sweep on all vregs (other than substation LTC), since this can impact those settings too.
        orig_regcontrols_df = get_regcontrol_info(correct_PT_ratio=True, nominal_voltage=voltage_config["nominal_voltage"])
        orig_regcontrols_df = orig_regcontrols_df.loc[orig_regcontrols_df['at_substation_xfmr_flag'] == False]
        if (not orig_regcontrols_df.empty) and voltage_config["existing_regulator_sweep_action"]:
            logger.info("After substation LTC module, settings sweep for existing reg control devices (excluding substation LTC).")
            kwargs["title"] = "Bus violations after subltc and vreg sweep"
            regcontrols_df, reg_sweep_commands_list = sweep_and_choose_regcontrol_setting(voltage_config=voltage_config, initial_regcontrols_df=orig_regcontrols_df, 
                                                        upper_limit=voltage_upper_limit, lower_limit=voltage_lower_limit, 
                                                        dss_file_list=dss_file_list, deciding_field=deciding_field, correct_parameters=False, 
                                                        exclude_sub_ltc=True, only_sub_ltc=False, previous_dss_commands_list=all_commands_list, 
                                                        **kwargs)
            comparison_dict["after_sub_ltc_and_vreg_checking"] = compute_voltage_violation_severity(voltage_upper_limit=voltage_upper_limit, 
                                                                                                     voltage_lower_limit=voltage_lower_limit, **kwargs)
            best_setting_so_far = "after_sub_ltc_and_vreg_checking"
            # added to commands list
            subltc_upgrade_commands = subltc_upgrade_commands + reg_sweep_commands_list
        
        orig_capacitors_df = get_capacitor_info(correct_PT_ratio=True, nominal_voltage=voltage_config['nominal_voltage'])
        if voltage_config["capacitor_action_flag"] and len(orig_capacitors_df) > 0:
            default_capacitor_settings = kwargs.pop("default_capacitor_settings", None)
            kwargs["title"] = "Bus violations after subltc_vreg_cap sweep"
            capacitor_dss_commands = determine_capacitor_upgrades(voltage_upper_limit, voltage_lower_limit, default_capacitor_settings, orig_capacitors_df, 
                                                                  voltage_config, deciding_field, **kwargs)
            subltc_upgrade_commands = subltc_upgrade_commands + capacitor_dss_commands
            comparison_dict["after_sub_ltc_vreg_cap_checking"] = compute_voltage_violation_severity(voltage_upper_limit=voltage_upper_limit, 
                                                                                                     voltage_lower_limit=voltage_lower_limit, **kwargs)
            best_setting_so_far = "after_sub_ltc_vreg_cap_checking"
            
    
    results_dict["comparison_dict"] = comparison_dict
    results_dict["best_setting_so_far"] = best_setting_so_far
    results_dict["subltc_upgrade_commands"] = subltc_upgrade_commands
    return results_dict


def determine_new_regulator_upgrades(voltage_config, buses_with_violations, voltage_upper_limit, voltage_lower_limit, deciding_field,
                                     circuit_source, default_regcontrol_settings, comparison_dict, best_setting_so_far, dss_file_list, 
                                     previous_dss_commands_list, fig_folder=None, create_plots=False, **kwargs):
    """Function to determine dss upgrade commands if new regulator is to be placed to resolve voltage violations in circuit.
    """
    dss_commands_list = previous_dss_commands_list
    new_reg_upgrade_commands = []
    logger.info("Place new regulators.")
    max_regulators = int(min(voltage_config["max_regulators"], len(buses_with_violations)))
    regcontrol_cluster_commands = determine_new_regulator_location(max_regs=max_regulators,
                                                                    circuit_source=circuit_source,
                                                                    initial_buses_with_violations=buses_with_violations,
                                                                    voltage_upper_limit=voltage_upper_limit,
                                                                    voltage_lower_limit=voltage_lower_limit, create_plots=create_plots,
                                                                    voltage_config=voltage_config,
                                                                    default_regcontrol_settings=default_regcontrol_settings, 
                                                                    deciding_field=deciding_field,
                                                                    fig_folder=fig_folder, **kwargs)
                
    if not regcontrol_cluster_commands:  # if there are no regcontrol commands
        reload_dss_circuit(dss_file_list=dss_file_list, commands_list=previous_dss_commands_list, **kwargs)
        comparison_dict["after_addition_new_regcontrol"] = compute_voltage_violation_severity(
            voltage_upper_limit=voltage_upper_limit, voltage_lower_limit=voltage_lower_limit, **kwargs)
        return {"new_reg_upgrade_commands": [], "comparison_dict": comparison_dict, "best_setting_so_far": best_setting_so_far}

    reg_upgrade_commands = get_newly_added_regulator_settings(dss_file_list, previous_dss_commands_list, regcontrol_cluster_commands, voltage_lower_limit, voltage_upper_limit,
                                       voltage_config, deciding_field, **kwargs)
    dss_commands_list = previous_dss_commands_list + reg_upgrade_commands
    comparison_dict["after_addition_new_regcontrol"] = compute_voltage_violation_severity(
        voltage_upper_limit=voltage_upper_limit, voltage_lower_limit=voltage_lower_limit, **kwargs)
    if comparison_dict["after_addition_new_regcontrol"][deciding_field] < comparison_dict[best_setting_so_far][deciding_field]:
        best_setting_so_far = "after_addition_new_regcontrol"
        new_reg_upgrade_commands = reg_upgrade_commands
    else: 
        new_reg_upgrade_commands = []
        remove_commands_list = reg_upgrade_commands
        if remove_commands_list:
            dss_commands_list = [i for i in dss_commands_list if i not in remove_commands_list]

        reload_dss_circuit(dss_file_list=dss_file_list, commands_list=dss_commands_list, **kwargs)
        comparison_dict["disabled_new_regcontrol"] = compute_voltage_violation_severity(
                                                        voltage_upper_limit=voltage_upper_limit, voltage_lower_limit=voltage_lower_limit, **kwargs)

    return {"new_reg_upgrade_commands": new_reg_upgrade_commands, "comparison_dict": comparison_dict, "best_setting_so_far": best_setting_so_far}


def get_newly_added_regulator_settings(dss_file_list, previous_dss_commands_list, regcontrol_cluster_commands, voltage_lower_limit, voltage_upper_limit,
                                       voltage_config, deciding_field, **kwargs):
    """this function finalizes the settings with the newly added voltage regulator. 
    It also takes into account errors encountered due to max control iterations being exceeded.
    """
    # reload circuit after settings sweep
    try:
        logger.info("Settings sweep for existing reg control devices (other than sub LTC).")
        regcontrol_df = get_regcontrol_info()
        regcontrol_sweep_df = sweep_regcontrol_settings(voltage_config=voltage_config,
                                                        initial_regcontrols_df=regcontrol_df,
                                                        voltage_upper_limit=voltage_upper_limit, voltage_lower_limit=voltage_lower_limit,
                                                        exclude_sub_ltc=True, only_sub_ltc=False, **kwargs)
        regcontrols_df, regcontrol_settings_commands_list = choose_best_regcontrol_sweep_setting(deciding_field=deciding_field,
            regcontrol_sweep_df=regcontrol_sweep_df, initial_regcontrols_df=regcontrol_df, **kwargs)
        reload_dss_circuit(dss_file_list=dss_file_list, commands_list=previous_dss_commands_list + regcontrol_cluster_commands + regcontrol_settings_commands_list, **kwargs)  # reload circuit after settings sweep
        reg_upgrade_commands = regcontrol_cluster_commands + regcontrol_settings_commands_list
    except DSSException as err:  # if there is an error: dss._cffi_api_util.DSSException: (#485)
        if err.args[0] != 485:
            raise
        logger.info(f"First attempt at regulator settings sweep failed with error: {err}.")
        reload_dss_circuit(dss_file_list=dss_file_list, commands_list=previous_dss_commands_list, **kwargs)  # reload circuit before clustering        
        temp = []
        for command in regcontrol_cluster_commands:  # extract only new addition commands
            if "edit regcontrol." not in command.lower():
                temp.append(command)        
        # control iterations are exceeded
        max_control_iterations = kwargs.get("max_control_iterations", dss.Solution.MaxControlIterations())  # get setting
        increase_control_iterations = max_control_iterations + 50  # here iterations are increased by 50, to reach a solution
        logger.info(f"Increased MaxControlIterations from {dss.Solution.MaxControlIterations()} to {increase_control_iterations}")
        dss.Solution.MaxControlIterations(increase_control_iterations)
        kwargs["max_control_iterations"] = max_control_iterations
        # The usual reason for exceeding MaxControlIterations is conflicting controls i.e., one or more RegControl devices are oscillating between taps
        # so try increasing band of reg control
        new_voltage_config = voltage_config.copy()
        new_voltage_config["reg_control_bands"] = [2]
        try:
            # First try for regulator controls (without subLTC)
            logger.info(f"Retrying settings sweep for existing reg control devices (other than sub LTC) with increased band to resolve error.")
            reload_dss_circuit(dss_file_list=dss_file_list, commands_list=previous_dss_commands_list+temp, **kwargs)  # reload circuit before settings edits
            regcontrol_df = get_regcontrol_info()
            regcontrol_sweep_df = sweep_regcontrol_settings(voltage_config=new_voltage_config,
                                                            initial_regcontrols_df=regcontrol_df,
                                                            voltage_upper_limit=voltage_upper_limit, voltage_lower_limit=voltage_lower_limit,
                                                            exclude_sub_ltc=True, only_sub_ltc=False, **kwargs)
            regcontrols_df, regcontrol_settings_commands_list = choose_best_regcontrol_sweep_setting(deciding_field=deciding_field,
                regcontrol_sweep_df=regcontrol_sweep_df, initial_regcontrols_df=regcontrol_df, **kwargs)
            reload_dss_circuit(dss_file_list=dss_file_list, commands_list=previous_dss_commands_list+temp+regcontrol_settings_commands_list, **kwargs)  # reload circuit after settings sweep
            bus_voltages_df, undervoltage_bus_list, overvoltage_bus_list, buses_with_violations = get_bus_voltages(
                voltage_upper_limit=voltage_upper_limit, voltage_lower_limit=voltage_lower_limit, **kwargs)
            reg_upgrade_commands =  temp + regcontrol_settings_commands_list
            if len(buses_with_violations) > 0:
                regcontrol_df = get_regcontrol_info()
                regcontrol_sweep_df = sweep_regcontrol_settings(voltage_config=new_voltage_config,
                                                                initial_regcontrols_df=regcontrol_df,
                                                                voltage_upper_limit=voltage_upper_limit, voltage_lower_limit=voltage_lower_limit,
                                                                exclude_sub_ltc=False, only_sub_ltc=True, **kwargs)
                regcontrols_df, subltc_settings_commands_list = choose_best_regcontrol_sweep_setting(deciding_field=deciding_field,
                    regcontrol_sweep_df=regcontrol_sweep_df, initial_regcontrols_df=regcontrol_df, **kwargs)
                reg_upgrade_commands =  reg_upgrade_commands + subltc_settings_commands_list
                
        except DSSException as err:
            if err.args[0] != 485:
                raise
            # next try for sub LTC only (if it exists)
            logger.info(f"Control iterations exceeded. Retrying settings sweep for sub LTC with increased band to resolve error.")
            reload_dss_circuit(dss_file_list=dss_file_list, commands_list=previous_dss_commands_list+temp, **kwargs)  # reload circuit before settings edits
            regcontrol_df = get_regcontrol_info()
            regcontrol_sweep_df = sweep_regcontrol_settings(voltage_config=new_voltage_config,
                                                            initial_regcontrols_df=regcontrol_df,
                                                            voltage_upper_limit=voltage_upper_limit, voltage_lower_limit=voltage_lower_limit,
                                                            exclude_sub_ltc=False, only_sub_ltc=True, **kwargs)
            regcontrols_df, regcontrol_settings_commands_list = choose_best_regcontrol_sweep_setting(deciding_field=deciding_field,
                regcontrol_sweep_df=regcontrol_sweep_df, initial_regcontrols_df=regcontrol_df, **kwargs)
            reload_dss_circuit(dss_file_list=dss_file_list, commands_list=previous_dss_commands_list+temp+regcontrol_settings_commands_list, **kwargs)  # reload circuit after settings sweep
            reg_upgrade_commands =  temp + regcontrol_settings_commands_list
    return reg_upgrade_commands


def add_new_node_and_xfmr(node, circuit_source, xfmr_conn_type=None, action_type='New',
                          **kwargs):
    """This function adds a new transformer by creating a new node
    (before or after a line, depending on whether it is a substation xfmr)
    action_type parameter is 'New' by default, unless we're redefining, and the 'Edit' has to be passed.

    Parameters
    ----------
    node
    circuit_source
    sub_xfmr_conn_type

    Returns
    -------

    """
    substation_node_flag = False
    commands_list = []
    node = node.lower()
    if node == circuit_source.lower():
        substation_node_flag = True
    # Find line to which this node is connected to
    all_lines_df = get_thermal_equipment_info(compute_loading=False, equipment_type="line")
    all_lines_df["bus1_name"] = all_lines_df["bus1"].str.split(".", expand=True)[0].str.lower()
    all_lines_df["bus2_name"] = all_lines_df["bus2"].str.split(".", expand=True)[0].str.lower()

    # For substation LTC, substation transformer will be placed at first bus of line (i.e. before the line)
    # make bus1 of line as regcontrol node
    if substation_node_flag:
        # lines in opendss aren't directional, so it may be connected to bus 1 or two
        if sum(all_lines_df["bus1_name"] == node)>0:
            feed_in_bus_name = "bus1_name"
            feed_in_bus = "bus1"
            second_bus = "bus2"
            second_bus_name = "bus2_name"
        else:
            feed_in_bus_name = "bus2_name"
            feed_in_bus = "bus2"
            second_bus = "bus1"
            second_bus_name = "bus1_name"

        chosen_line_info = all_lines_df.loc[all_lines_df[feed_in_bus_name] == node].iloc[0]
        new_node = "newnode_" + chosen_line_info[second_bus]  # contains terminal information too
        new_node_name = "newnode_" + chosen_line_info[second_bus_name]
            
        curr_time = str(time.time())
        # this is added to name to ensure it is unique
        time_stamp = curr_time.split(".")[0] + "_" + curr_time.split(".")[1]
        xfmr_name = "New_xfmr_" + node + time_stamp
        dss.Circuit.SetActiveBus(chosen_line_info[feed_in_bus_name])
        x = dss.Bus.X()
        y = dss.Bus.Y()
        dss.Circuit.SetActiveBus(chosen_line_info[second_bus_name])
        kV_node = dss.Bus.kVBase()
        if chosen_line_info["phases"] > 1:
            kV_DT = kV_node * math.sqrt(3)  # L-L voltage
        # if single phase node
        else:
            kV_DT = kV_node  # L-N voltage
        # ideally we would use an auto transformer which would need a much smaller kVA rating
        kVA = int(kV_DT * chosen_line_info["normamps"] * 1.1)   # 10% over sized transformer
        if xfmr_conn_type is None:
            raise Exception("Transformer winding connection type (wye or delta) should be passed as parameter for adding new substation transformer")
        new_xfmr_command_string = f"{action_type} Transformer.{xfmr_name} phases={chosen_line_info['phases']} " \
                                  f"windings=2 buses=({chosen_line_info[feed_in_bus]}, {new_node}) " \
                                  f"conns=({xfmr_conn_type},{xfmr_conn_type}) kvs=({kV_DT},{kV_DT}) " \
                                  f"kvas=({kVA},{kVA}) xhl=0.001 wdg=1 %r=0.001 wdg=2 %r=0.001 Maxtap=1.1 Mintap=0.9 " \
                                  f"enabled=Yes"
        property_list = ["phases", "windings", "buses", "conns", "kvs", "kvas", "xhl", "%Rs", "Maxtap", "Mintap"]
        edit_line_command_string = f"Edit Line.{chosen_line_info['name']} bus1={new_node}"

    # If not subltc: For regulator, transformer will be placed after line. (i.e. new node will be created after bus2)
    # for this, wye transformer will be added.
    
    else:
        if xfmr_conn_type is None:
            xfmr_conn_type = "wye"
        # if there are more than one lines at a node, then iterate over them?
        chosen_line_info = all_lines_df.loc[all_lines_df["bus2_name"] == node]
        if len(chosen_line_info) == 0:  # if no line is connected to the node
            logger.debug(f"No line is connected to that node {node}. So not placing transformer here.")
            return None
        chosen_line_info = chosen_line_info.iloc[0]
        new_node = "newnode_" + chosen_line_info["bus2"]  # contains terminal information too
        new_node_name = "newnode_" + chosen_line_info["bus2_name"]
        curr_time = str(time.time())
        # this is added to name to ensure it is unique
        time_stamp = curr_time.split(".")[0] + "_" + curr_time.split(".")[1]
        xfmr_name = "New_xfmr_" + node + time_stamp
        dss.Circuit.SetActiveBus(chosen_line_info["bus2_name"])
        x = dss.Bus.X()
        y = dss.Bus.Y()
        kV_node = dss.Bus.kVBase()
        # is number of phases > 1
        if chosen_line_info["phases"] > 1:
            kV_DT = kV_node * math.sqrt(3)  # L-L voltage
        # for single phase
        else:
            kV_DT = kV_node  # L-N voltage
        # ideally we would use an auto transformer which would need a much smaller kVA rating
        kVA = int(kV_DT * chosen_line_info["normamps"] * 1.1)  # 10% over sized transformer
        property_list = ["phases", "windings", "buses", "conns", "kvs", "kvas", "xhl", "%Rs", "Maxtap",
                         "Mintap"]
        new_xfmr_command_string = f"{action_type} Transformer.{xfmr_name} phases={chosen_line_info['phases']} " \
                                  f"windings=2 buses=({new_node},{chosen_line_info['bus2']}) " \
                                  f"conns=({xfmr_conn_type},{xfmr_conn_type}) kvs=({kV_DT},{kV_DT}) kvas=({kVA},{kVA}) xhl=0.001 " \
                                  f"wdg=1 %r=0.001 wdg=2 %r=0.001 Maxtap=1.1 Mintap=0.9 enabled=Yes"
        edit_line_command_string = f"Edit Line.{chosen_line_info['name']} bus2={new_node}"

    check_dss_run_command(edit_line_command_string)
    check_dss_run_command(new_xfmr_command_string)
    # Update system admittance matrix
    check_dss_run_command("CalcVoltageBases")
    # update coordinates of new node
    dss.Circuit.SetActiveBus(new_node_name)
    dss.Bus.X(x)
    dss.Bus.Y(y)

    commands_list.append(edit_line_command_string)
    commands_list.append(new_xfmr_command_string)
    commands_list.append(f"// new node added {new_node.split('.')[0]},{x},{y}")
    circuit_solve_and_check(raise_exception=True, calcvoltagebases=True, **kwargs)
    info_dict = {'commands_list': commands_list, 'new_xfmr_name': xfmr_name,
                 'modified_line_name': chosen_line_info["name"]}
    return info_dict


def disable_new_xfmr_and_edit_line(transformer_name_to_disable, line_name_to_modify, **kwargs):
    """This function disables an added transformer in the feeder.
    since OpenDSS disables by transformer by opening the circuit instead of creating a short circuit,
    this function will remove the transformer by first disabling it, then it will connect the line properly to
    remove the islands. (note: we cant remove the element definition completely)
    Substation will always have a xfmr by this point so only regulator transformers have to be removed

    Parameters
    ----------
    transformer_name

    Returns
    -------

    """
    commands_list = []
    # for regulators, added transformer is always placed after the line (i.e. after 'to' node of line)
    # i.e. for this transformer: primary bus: newly created node, secondary bus: existing node
    all_xfmr_df = get_thermal_equipment_info(compute_loading=False, equipment_type="transformer")
    all_xfmr_df['name'] = all_xfmr_df['name'].str.lower()
    chosen_xfmr = all_xfmr_df.loc[all_xfmr_df['name'] == transformer_name_to_disable.lower()]
    if len(chosen_xfmr) == 0:
        logger.debug("Transformer to be removed does not exist")
        return []
    chosen_xfmr = chosen_xfmr.iloc[0]
    xfmr_prim_bus = chosen_xfmr['buses'][0]
    xfmr_sec_bus = chosen_xfmr['buses'][1]  # contains terminal information as well

    # disable xfmr and edit xfmr buses to be the same (primary bus). (This is because primary bus was the new node)
    command_string = f"Edit Transformer.{transformer_name_to_disable} enabled=No"
    check_dss_run_command(command_string)
    commands_list.append(command_string)
    command_string = f"Edit Transformer.{transformer_name_to_disable} buses=({xfmr_prim_bus}, {xfmr_prim_bus})"
    check_dss_run_command(command_string)
    commands_list.append(command_string)

    # edit line, so its 'to' node (i.e. bus2) is set back to the previous existing node
    # this node used to be the xfmr sec node, so in this way, the xfmr is removed, and line is directly connected to circuit
    command_string = f"Edit Line.{line_name_to_modify} bus2={xfmr_sec_bus}"
    commands_list.append(command_string)
    check_dss_run_command(command_string)
    # Update system admittance matrix
    check_dss_run_command("CalcVoltageBases")
    circuit_solve_and_check(raise_exception=True, **kwargs)
    return commands_list


def add_new_regcontrol_at_node(node, default_regcontrol_settings, nominal_voltage, **kwargs):
    """This function adds a new regcontrol at a node. It identifies the correct transformer and places regcontrol there.
    Identify whether or not a reg contrl exists at the transformer connected to this bus - if not, place new regcontrol

    Parameters
    ----------
    node
    default_regcontrol_settings
    nominal_voltage

    Returns
    -------

    """
    all_xfmr_df = get_thermal_equipment_info(compute_loading=False, equipment_type="transformer")
    temp_df = all_xfmr_df['bus_names_only'].apply(pd.Series)
    all_xfmr_df["primary_bus"] = temp_df[0].str.lower()
    all_xfmr_df["secondary_bus"] = temp_df[1].str.lower()
    chosen_xfmr = all_xfmr_df.loc[(all_xfmr_df['primary_bus'] == node) | (all_xfmr_df['secondary_bus'] == node)]
    # if transformer does not exist on node
    if len(chosen_xfmr) == 0:
        raise Exception(f"Transformer needs to exist at node {node} in order to place regulator control.")
    chosen_xfmr = chosen_xfmr.iloc[0]
    regcontrols_df = get_regcontrol_info()
    enabled_regcontrol_exists = False
    if not regcontrols_df.empty: 
        enabled_regcontrols_df = regcontrols_df.loc[regcontrols_df['enabled'].str.lower() == "yes"]
        enabled_regcontrol_exists = len(enabled_regcontrols_df.loc[(enabled_regcontrols_df['transformer_bus1'] == node) | (
                                        enabled_regcontrols_df['transformer_bus2'] == node)]) > 0
    if enabled_regcontrol_exists:
        logger.debug("Enabled regcontrol already exists.")
        return None
    else:  # if enabled regcontrol does not exist on transformer
        # this runs the command and returns the command list
        new_regcontrol_dict = add_new_regcontrol_command(xfmr_info_series=chosen_xfmr, default_regcontrol_settings=default_regcontrol_settings,
                                                         nominal_voltage=nominal_voltage, **kwargs)
    return new_regcontrol_dict


def add_bus_nodes(G, bus_coordinates_df):
    buses_list = bus_coordinates_df.to_dict('records')
    for item in buses_list:
        G.add_node(item['bus_name'], pos=[item['x_coordinate'], item['y_coordinate']])
    return G


def extract_common_element_from_lists(list_of_lists):
    # common element extraction from multiple lists
    common_element_list = list(set.intersection(*map(set, list_of_lists)))
    return common_element_list


def identify_common_upstream_nodes(G, buses_list):
    """ In this function the very first common upstream node and all upstream nodes for the members of the
    cluster are identified

    Parameters
    ----------
    G
    buses_list

    Returns
    -------

    """
    # notes: can include some type of optimization - such as look at multiple upstream nodes and place where sum of
    # downstream node voltage deviations is minimum as long as it doesn't overlap with other clusters
    # Currently it only identifies the common upstream nodes for all buses in the list
    # for one cluster:
    bus_ancestors = {}
    # iterating over each bus in the cluster to get ancestors (upstream nodes) of each bus
    for bus in buses_list:
        bus_ancestors[bus] = nx.ancestors(G, source=bus)
    # extract common upstream nodes for all buses in this cluster
    common_nodes_list = extract_common_element_from_lists(list_of_lists=list(bus_ancestors.values()))
    return common_nodes_list


def test_new_regulator_placement_on_common_nodes(voltage_upper_limit, voltage_lower_limit, nominal_voltage,
                                                 common_upstream_nodes_list, circuit_source,
                                                 default_regcontrol_settings, deciding_field, **kwargs):
    """ In each cluster group, place a new regulator control at each common upstream node, unless it is the source bus
    (since that already contains the LTC) or if it has a distribution transformer.

    If a transformer exists, simply add a new reg control -
    in fact calling the add_new_regctrl function will automatically check whether a reg control exists or not
    -  so only thing to be ensured is that a transformer should exist.

    Parameters
    ----------
    voltage_upper_limit
    common_upstream_nodes_dict
    circuit_source

    Returns
    -------

    """
    intra_cluster_group_severity_dict = {}
    for node in common_upstream_nodes_list:
        new_xfmr_added_dict = None
        new_regcontrol_dict = None
        logger.debug(node)        
        node = node.lower()
        # do not add a new reg control to source bus as it already has a LTC
        if node == circuit_source.lower():
            logger.debug("This is the source node. Skip.")
            continue
        all_xfmr_df = get_thermal_equipment_info(compute_loading=False, equipment_type="transformer")
        temp_df = all_xfmr_df['bus_names_only'].apply(pd.Series)
        all_xfmr_df["primary_bus"] = temp_df[0].str.lower()
        all_xfmr_df["secondary_bus"] = temp_df[1].str.lower()        
        # if enabled transformer is already present at this node, skip.
        # These pre-existing xfmrs will be "primary to secondary DTs" which we do not want to control.
        # Regulators are primarily in line and not on individual distribution transformers
        if len(all_xfmr_df[(all_xfmr_df["primary_bus"].str.lower() == node.lower()) & (all_xfmr_df["enabled"].str.lower() == "yes")]) or \
            len(all_xfmr_df[(all_xfmr_df["secondary_bus"].str.lower() == node.lower()) & (all_xfmr_df["enabled"].str.lower() == "yes")]):
            logger.debug("Distribution transformer already exists on this node. Skip.")
            continue
        # add new transformer at this node
        new_xfmr_added_dict = add_new_node_and_xfmr(action_type='New', node=node, circuit_source=circuit_source, **kwargs)
        if new_xfmr_added_dict is None:  # if new transformer elements were not added, continue
            logger.debug("New transformer elements could not be added on this node.")
            continue
        # add new regulator control at this node
        # These are just default settings and do not have to be written in the output file
        new_regcontrol_dict = add_new_regcontrol_at_node(node=node, default_regcontrol_settings=default_regcontrol_settings,
                                                         nominal_voltage=nominal_voltage, **kwargs)
        if new_regcontrol_dict is None:
            logger.debug("New regulator elements could not be added on this node.")
            if new_xfmr_added_dict is not None:
                disable_new_xfmr_and_edit_line(transformer_name_to_disable=new_xfmr_added_dict['new_xfmr_name'],
                                               line_name_to_modify=new_xfmr_added_dict['modified_line_name'])
            continue
        intra_cluster_group_severity_dict[node] = {}
        intra_cluster_group_severity_dict[node]['add_new_devices_command_list'] = new_xfmr_added_dict['commands_list'] + \
            new_regcontrol_dict['command_list']
        pass_flag = circuit_solve_and_check(raise_exception=False, **kwargs)
        intra_cluster_group_severity_dict[node]['converged'] = pass_flag
        severity_dict = compute_voltage_violation_severity(voltage_upper_limit=voltage_upper_limit, voltage_lower_limit=voltage_lower_limit, **kwargs)
        intra_cluster_group_severity_dict[node].update(severity_dict)
        intra_cluster_group_severity_dict[node].update({'new_xfmr_name': new_xfmr_added_dict['new_xfmr_name'], 'modified_line_name': new_xfmr_added_dict['modified_line_name'],
                                                        'new_regcontrol_name': new_regcontrol_dict['new_regcontrol_name']})
        # Now disable the added regulator control and remove the added transformer
        command_string = f"Edit RegControl.{new_regcontrol_dict['new_regcontrol_name']} enabled=No"
        check_dss_run_command(command_string)
        intra_cluster_group_severity_dict[node]['disable_new_devices_command_list'] = disable_new_xfmr_and_edit_line(transformer_name_to_disable=new_xfmr_added_dict['new_xfmr_name'],
                                                                                                                     line_name_to_modify=new_xfmr_added_dict['modified_line_name'],
                                                                                                                     **kwargs)
        if intra_cluster_group_severity_dict[node][deciding_field] == 0:
            break
    # For a given list of common nodes in a cluster, identify the node which leads to minimum number of violations
    deciding_df = pd.DataFrame.from_dict(intra_cluster_group_severity_dict, orient='index')
    if len(deciding_df) == 0:  # If no nodes is found break the loop and go to next number of clusters
        chosen_node = None
        logger.debug("There were no regulators found on any common node.")
        return None
    deciding_df = deciding_df.loc[deciding_df['converged'] == True]
    chosen_node = deciding_df[deciding_field].idxmin()  # node with minimum violations severity
    logger.debug(f"Node with minimum violation {deciding_field} is: {chosen_node}")
    
    # Since this is an optimal location add the transformer here - this transformer will stay as long as clustering_option_number (num_clusters) does not increment. 
    # If clustering_option_number changes then all devices at nodes mentioned should be disabled
    chosen_node_dict = intra_cluster_group_severity_dict[chosen_node]
    chosen_node_dict['node'] = chosen_node
    re_enable_added_regcontrol_objects(chosen_node_dict)
    circuit_solve_and_check(raise_exception=True, **kwargs)    
    return chosen_node_dict


def re_enable_added_regcontrol_objects(chosen_node_dict):
    """If new object was added previously, and then disabled. Then only edit and enable that object.
    If an object was edited previously, then run the whole command string as is.
    This should contain only transformer, line and regcontrol commands.
    """
    for command_string in chosen_node_dict["add_new_devices_command_list"]:
        if command_string.lower().startswith("new"):
            new_string = command_string.lower().replace("new ", "edit ")
            check_dss_run_command(new_string)
        elif command_string.lower().startswith("edit"):
            check_dss_run_command(command_string)
        elif command_string.startswith("//"):
            continue
        else:
            raise Exception("Unknown DSS command received in circuit element renabling function.")
        check_dss_run_command("CalcVoltageBases")
    return
    

def correct_node_coords(G, position_dict, circuit_source):
    """If node doesn't have node attributes, attach parent or child node's attributes
    Parameters
    ----------
    G
    position_dict
    circuit_source

    Returns
    -------

    """

    new_temp_graph = G
    temp_graph = new_temp_graph.to_undirected()
    for key, vals in position_dict.items():
        if vals[0] == 0.0 and vals[1] == 0.0:
            new_x = 0
            new_y = 0
            pred_buses = nx.shortest_path(temp_graph, source=key, target=circuit_source)
            if len(pred_buses) > 0:
                for pred_bus in pred_buses:
                    if pred_bus == key:
                        continue
                    if position_dict[pred_bus][0] != 0.0 and position_dict[pred_bus][1] != 0.0:
                        new_x = position_dict[pred_bus][0]
                        new_y = position_dict[pred_bus][1]
                        G.node[key]["pos"] = [new_x, new_y]
                        break
            if new_x == 0 and new_y == 0:
                # Since either predecessor nodes were not available or they did not have
                # non-zero coordinates, try successor nodes
                # Get a leaf node
                for x in G.nodes():
                    if G.out_degree(x) == 0 and G.in_degree(x) == 1:
                        leaf_node = x
                        break
                succ_buses = nx.shortest_path(temp_graph, source=key, target=leaf_node)
                if len(succ_buses) > 0:
                    for pred_bus in succ_buses:
                        if pred_bus == key:
                            continue
                        if position_dict[pred_bus][0] != 0.0 and position_dict[pred_bus][1] != 0.0:
                            new_x = position_dict[pred_bus][0]
                            new_y = position_dict[pred_bus][1]
                            G.node[key]["pos"] = [new_x, new_y]
                            break
    # Update position dict with new coordinates
    position_dict = nx.get_node_attributes(G, 'pos')
    return G, position_dict


def get_full_distance_df(upper_triang_paths_dict):
    """This function creates full distance dictionary as a square array from the upper triangular dictionary.

    Parameters
    ----------
    upper_triang_paths_dict

    Returns
    -------

    """
    square_dict = {}
    temp_nodes_list = []
    # find max length in upper trianguler dict. This defines size of array
    max_length = max([len(x) for x in list(upper_triang_paths_dict.values())])
    # Create a square dict with zeros for lower triangle values
    for key, values in upper_triang_paths_dict.items():
        temp_nodes_list.append(key)
        temp_list = []
        if len(values) < max_length:
            new_items_req = max_length - len(values)
            for items_cnt in range(0, new_items_req, 1):
                temp_list.append(0.0)
        for item in values:
            temp_list.append(float(item))
        square_dict[key] = temp_list
    # # from dict create a list of lists
    list_of_lists = []
    for key, values in square_dict.items():
        list_of_lists.append(values)
    # Create numpy array from list of lists
    square_array = np.array(list_of_lists)
    # Replace lower triangle zeros with upper triangle values
    square_array = square_array + square_array.T - np.diag(np.diag(square_array))

    square_dist_df = pd.DataFrame(square_array, index=upper_triang_paths_dict.keys(),
                                  columns=upper_triang_paths_dict.keys())
    return square_dist_df


def get_upper_triangular_dist(G, buses_with_violations):
    """ Identify shortest dijkstra paths between all buses with violations.
    Returns a dictionary of nodes with distances to other nodes (only upper triangular)

    Parameters
    ----------
    G
    buses_with_violations

    Returns
    -------

    """
    new_graph = G.to_undirected()
    calculated_buses = []
    upper_triang_paths_dict = {}
    # Get upper triangular distance matrix - reduces computational time by half
    for bus1 in buses_with_violations:
        upper_triang_paths_dict[bus1] = []
        for bus_n in buses_with_violations:
            if bus_n == bus1:
                path_length = 0.0
            elif bus_n in calculated_buses:
                continue
            else:
                # path = nx.dijkstra_path(new_graph, source=bus1, target=bus_n, weight='length')
                path_length = nx.dijkstra_path_length(new_graph, source=bus1, target=bus_n, weight='length')
            upper_triang_paths_dict[bus1].append(round(path_length, 3))
        calculated_buses.append(bus1)
    return upper_triang_paths_dict


def perform_clustering(num_clusters, square_distance_array, buses_with_violations):
    """This function performs clustering and returns a dictionary with cluster_number as key and
    list of buses in each cluster as values.

    Parameters
    ----------
    num_clusters
    square_array
    buses_with_violations

    Returns
    -------

    """
    clusters_dict = {}
    # model = AgglomerativeClustering(n_clusters=num_clusters, affinity='euclidean', linkage='ward')
    model = AgglomerativeClustering(n_clusters=num_clusters, affinity='precomputed', linkage='average')
    model.fit(square_distance_array)
    labels_list = model.labels_
    # create a dictionary containing cluster_number as keys, and list of buses in that cluster as values
    for label in range(len(labels_list)):
        if labels_list[label] not in clusters_dict:
            clusters_dict[labels_list[label]] = [buses_with_violations[label]]
        else:
            clusters_dict[labels_list[label]].append(buses_with_violations[label])
    return clusters_dict


def per_cluster_group_regulator_analysis(G, buses_list, voltage_config, voltage_upper_limit, voltage_lower_limit, 
                                         default_regcontrol_settings, circuit_source, deciding_field, **kwargs):
    """This function performs analysis on one cluster group of buses with violations. 
    It determines the common upstream buses for all the buses with violations in that cluster group. 
    It places regulators on each of these common noeds, and determines the best node to place the regulator for that group.
    Also determines the best reg control settings with this newly added regulator.

    """
    cluster_group_info_dict = {}
    nominal_voltage = voltage_config['nominal_voltage']
    # this identifies common upstream nodes for all buses with violations in a given cluster
    # these common upstream nodes are where regulator control can be placed
    common_upstream_nodes_list = identify_common_upstream_nodes(G=G, buses_list=buses_list)
    cluster_group_info_dict['common_upstream_nodes_list'] = common_upstream_nodes_list
    # this adds new regulator on each common node (one at a time)
    chosen_node_dict = test_new_regulator_placement_on_common_nodes(voltage_upper_limit=voltage_upper_limit, voltage_lower_limit=voltage_lower_limit,
                                                                    nominal_voltage=nominal_voltage, deciding_field=deciding_field,
                                                                    common_upstream_nodes_list=common_upstream_nodes_list, circuit_source=circuit_source,
                                                                    default_regcontrol_settings=default_regcontrol_settings, **kwargs)
    
    if chosen_node_dict is None:  # if there is no common node on which regulator can be placed (for this cluster group)
        return None
    cluster_group_info_dict.update(chosen_node_dict)
    # choose best settings for all regulators (with new regulator added)
    # max control iterations could be exceeded here as well
    init_regcontrols_df = get_regcontrol_info(correct_PT_ratio=True, nominal_voltage=nominal_voltage)
    regcontrol_sweep_df = sweep_regcontrol_settings(voltage_config=voltage_config, initial_regcontrols_df=init_regcontrols_df,
                                                    voltage_upper_limit=voltage_upper_limit, voltage_lower_limit=voltage_lower_limit,
                                                    exclude_sub_ltc=True, only_sub_ltc=False, **kwargs)
    regcontrols_df, regcontrol_settings_commands_list = choose_best_regcontrol_sweep_setting(
        regcontrol_sweep_df=regcontrol_sweep_df, initial_regcontrols_df=init_regcontrols_df, deciding_field=deciding_field, exclude_sub_ltc=True,
        only_sub_ltc=False, **kwargs)
    # determine violation severity after changes
    severity_dict = compute_voltage_violation_severity(voltage_upper_limit=voltage_upper_limit, voltage_lower_limit=voltage_lower_limit, **kwargs)
    cluster_group_info_dict.update(severity_dict)
    cluster_group_info_dict['settings_commands_list'] = regcontrol_settings_commands_list
    return cluster_group_info_dict


def cluster_and_place_regulator(G, square_distance_df, initial_buses_with_violations, num_clusters,
                                voltage_config, voltage_upper_limit, voltage_lower_limit,
                                default_regcontrol_settings, circuit_source, deciding_field,
                                **kwargs):
    """ This function performs clustering on buses with violations, then iterates through each cluster group, performs regulator placement analysis
    Returns the best regulator placement for each cluster group, in the form of a dict.
    """
    fig_folder = kwargs.get("fig_folder", None)
    create_plots = kwargs.get("create_plots", False)
    if len(initial_buses_with_violations) == 1:  # if there is only one violation, then clustering cant be performed. So directly assign bus to cluster
        clusters_dict = {0: initial_buses_with_violations}
    else:
        # this creates clusters of buses based on distance matrix. So nearby buses are clustered together
        clusters_dict = perform_clustering(square_distance_array=square_distance_df, num_clusters=num_clusters,
                                          buses_with_violations=initial_buses_with_violations)
    cluster_group_info_dict = {}
    # iterate through each cluster group
    for cluster_id, buses_list in clusters_dict.items():
        logger.debug(f"Cluster group: {cluster_id}")
        cluster_group_info_dict[cluster_id] = per_cluster_group_regulator_analysis(G=G, buses_list=buses_list, voltage_config=voltage_config,
                                                                                   voltage_upper_limit=voltage_upper_limit, voltage_lower_limit=voltage_lower_limit, 
                                                                                   default_regcontrol_settings=default_regcontrol_settings,
                                                                                   circuit_source=circuit_source, deciding_field=deciding_field, **kwargs)
        if cluster_group_info_dict[cluster_id] is None:
            logger.debug("There is no common node on which regulator can be placed (for this cluster group)")
            return cluster_group_info_dict         
        cluster_group_info_dict[cluster_id].update({"buses_list": buses_list,})
        # determine voltage violations after changes
        bus_voltages_df, undervoltage_bus_list, overvoltage_bus_list, buses_with_violations = get_bus_voltages(
            voltage_upper_limit=voltage_upper_limit, voltage_lower_limit=voltage_lower_limit, **kwargs)
        if (len(buses_with_violations)) == 0:
            logger.info("All nodal violations have been removed successfully by new regulator placement.")
            break
    if create_plots and (fig_folder is not None):
        plot_created_clusters(fig_folder=fig_folder, circuit_source=circuit_source, clusters_dict=cluster_group_info_dict)
    return cluster_group_info_dict


@track_timing(timer_stats_collector)
def determine_new_regulator_location(circuit_source, initial_buses_with_violations, voltage_upper_limit, voltage_lower_limit, 
                                     voltage_config, default_regcontrol_settings, max_regs, deciding_field,
                                     **kwargs):
    """Function to determine new regulator location. This decision is made after testing out various clustering and placement options.
    """
    fig_folder = kwargs.get("fig_folder", None)
    create_plots = kwargs.get("create_plots", False)

    # prepare for clustering
    G = generate_networkx_representation()
    upper_triang_paths_dict = get_upper_triangular_dist(G=G, buses_with_violations=initial_buses_with_violations)
    square_distance_df = get_full_distance_df(upper_triang_paths_dict=upper_triang_paths_dict)
    # if create_plots:
    #     fig_folder = kwargs.get('fig_folder', None)
    #     plot_heatmap_distmatrix(square_array=square_distance_df, fig_folder=fig_folder)  # currently not used

    options_dict = {}
    # Clustering the distance matrix into clusters equal to optimal clusters
    # Iterate by changing number of clusters to be considered in the network, and perform analysis.
    for option_num in range(1, max_regs + 1, 1):
        cluster_option_name = f"cluster_option_{option_num}"
        logger.info(f"Clustering option: num_of_clusters: {option_num}")

        temp_dict = cluster_and_place_regulator(G=G, square_distance_df=square_distance_df, deciding_field=deciding_field,
                                                initial_buses_with_violations=initial_buses_with_violations, num_clusters=option_num,
                                                voltage_config=voltage_config, voltage_upper_limit=voltage_upper_limit, voltage_lower_limit=voltage_lower_limit,
                                                default_regcontrol_settings=default_regcontrol_settings, circuit_source=circuit_source,
                                                **kwargs)
        options_dict[cluster_option_name] = {}
        options_dict[cluster_option_name]["details"] = temp_dict
        # get severity for this option 
        severity_dict = compute_voltage_violation_severity(
            voltage_upper_limit=voltage_upper_limit, voltage_lower_limit=voltage_lower_limit, **kwargs)
        # determine voltage violations after changes
        bus_voltages_df, undervoltage_bus_list, overvoltage_bus_list, buses_with_violations = get_bus_voltages(
                voltage_upper_limit=voltage_upper_limit, voltage_lower_limit=voltage_lower_limit, **kwargs)
        if (fig_folder is not None) and create_plots:
            plot_voltage_violations(fig_folder=fig_folder, title="Bus violations for "+cluster_option_name+" voltage regulators"+"_"+
                                    str(len(buses_with_violations)), buses_with_violations=buses_with_violations, circuit_source=circuit_source, enable_detailed=True)
        options_dict[cluster_option_name].update(severity_dict)
        if (len(buses_with_violations)) == 0:
            logger.info("All nodal violations have been removed successfully.")
            break
        # disable previous clustering option before moving onto next cluster option
        disable_previous_clustering_option(cluster_group_info_dict=options_dict[cluster_option_name]["details"])
        
    # choose best clustering option based on severity dict
    deciding_df = pd.DataFrame.from_dict(options_dict, orient='index')
    # deciding_df = deciding_df.loc[deciding_df['converged'] == True]
    chosen_cluster_option = deciding_df[deciding_field].idxmin()
    chosen_cluster_details = options_dict[chosen_cluster_option]["details"]
    new_commands = []
    for group_num in chosen_cluster_details.keys():
        if chosen_cluster_details[group_num] is not None:
            new_commands = new_commands + chosen_cluster_details[group_num]["add_new_devices_command_list"] + \
                            chosen_cluster_details[group_num]["settings_commands_list"]
    return new_commands


def disable_previous_clustering_option(cluster_group_info_dict):
    """Function to disable opendss objects in previous clustering option"""
    for cluster_id in cluster_group_info_dict.keys():
        if cluster_group_info_dict[cluster_id] is None:
            return
        command_list = cluster_group_info_dict[cluster_id]['disable_new_devices_command_list']
        command_list.append(f"Edit regcontrol.{cluster_group_info_dict[cluster_id]['new_regcontrol_name']} enabled=No")  # disabling regcontrol command does not exist in the previous list
        dss_run_command_list(command_list)  # runs each command in this list, in opendss
        dss_solve_and_check(raise_exception=True)
    return


def plot_heatmap_distmatrix(square_array, fig_folder):
    # TODO THIS FUNCTION is not used
    fig = plt.figure(figsize=(7, 7))
    ax = sns.heatmap(square_array, linewidth=0.5)
    title = "Distance matrix of nodes with violations"
    plt.title(title)
    title = title.lower()
    title = title.replace(" ", "_")
    plt.savefig(os.path.join(fig_folder, title+".pdf"))
    plt.close(fig)


def plot_feeder(fig_folder, title, circuit_source=None, enable_detailed=False):
    """Function to plot feeder network.
    """
    G = generate_networkx_representation()
    bus_coordinates_df = get_bus_coordinates()
    complete_flag = check_buscoordinates_completeness(bus_coordinates_df)  # check if sufficient buscoordinates data is available
    if not complete_flag:  # feeder cannot be plotted if sufficient buscoordinates data is unavailable
        logger.warning(f"Unable to plot {title} because feeder model bus coordinates are not provided.")
        return
    position_dict = nx.get_node_attributes(G, 'pos')
    nodes_list = G.nodes()
    Un_G = G.to_undirected()

    fig = plt.figure(figsize=(40, 40), dpi=10)
    nx.draw_networkx_edges(Un_G, pos=position_dict, alpha=1.0, width=0.3)
    default_node_size = 2
    default_node_color = 'black'
    
    NodeLegend = {
        "Load": get_load_buses(dss), 
        "PV": get_pv_buses(dss), 
        "Transformer": list(get_all_transformer_info_instance(compute_loading=False)['bus_names_only'].str[0].values),
    }
    if circuit_source is not None:
        NodeLegend["Circuit Source"] = [circuit_source]
    if enable_detailed:
        if enable_detailed:
            cap_df = get_capacitor_info()
        if not cap_df.empty:
            NodeLegend["Capacitor"] = list(cap_df['bus1'].str.split(".").str[0].unique())
        reg_df =  get_regcontrol_info()
        if not reg_df.empty:
            reg_df = reg_df.loc[reg_df.enabled.str.lower() == "yes"]
        if not reg_df.empty:
            NodeLegend["Voltage Regulator"] = list(reg_df['transformer_bus1'].unique())
    colored_nodelist = []
    for key in NodeLegend.keys():
        temp_list = NodeLegend[key]
        colored_nodelist  = colored_nodelist + temp_list
        if  len(temp_list) != 0:
            nx.draw_networkx_nodes(Un_G, pos=filter_dictionary(dict_data=position_dict, wanted_keys=temp_list),
                                nodelist=temp_list, node_size=NODE_COLORLEGEND[key]["node_size"], node_color=NODE_COLORLEGEND[key]["node_color"],
                                alpha=NODE_COLORLEGEND[key]["alpha"], label=NODE_COLORLEGEND[key]["label"])
    
    remaining_nodes = list(set(nodes_list) - set(colored_nodelist)) 
    nx.draw_networkx_nodes(Un_G, pos=filter_dictionary(dict_data=position_dict, wanted_keys=remaining_nodes),
                                nodelist=remaining_nodes, node_size=default_node_size, node_color=default_node_color)
    plt.title(title, fontsize=50)
    # plt.axis("off")
    plt.legend(fontsize=50)
    title = title.lower()
    title = title.replace(" ", "_")
    plt.savefig(os.path.join(fig_folder, title+".pdf"))
    plt.close(fig)
    return


def plot_voltage_violations(fig_folder, title, buses_with_violations, circuit_source=None, enable_detailed=False):
    """Function to plot voltage violations in network.
    """
    os.makedirs(fig_folder, exist_ok=True)
    default_node_size = 2
    default_node_color = 'black'
    G = generate_networkx_representation()
    bus_coordinates_df = get_bus_coordinates()
    complete_flag = check_buscoordinates_completeness(bus_coordinates_df)  # check if sufficient buscoordinates data is available
    if not complete_flag:  # feeder cannot be plotted if sufficient buscoordinates data is unavailable
        logger.warning(f"Unable to plot {title} because feeder model bus coordinates are not provided.")
        return
    position_dict = nx.get_node_attributes(G, 'pos')
    nodes_list = G.nodes()
    Un_G = G.to_undirected()

    fig = plt.figure(figsize=(40, 40), dpi=10)
    nx.draw_networkx_edges(Un_G, pos=position_dict, alpha=1.0, width=0.3)
    nx.draw_networkx_nodes(Un_G, pos=position_dict, alpha=1.0, node_size=default_node_size, node_color=default_node_color)
    
    NodeLegend = {
        # "Load": get_load_buses(dss), 
        # "PV": get_pv_buses(dss), 
        # "Transformer": list(get_all_transformer_info_instance(compute_loading=False)['bus_names_only'].str[0].values),
        "Violation": buses_with_violations,
    }
    if circuit_source is not None:
        NodeLegend["Circuit Source"] = [circuit_source]
    if enable_detailed:
        cap_df = get_capacitor_info()
        if not cap_df.empty:
            NodeLegend["Capacitor"] = list(cap_df['bus1'].str.split(".").str[0].unique())
        reg_df =  get_regcontrol_info()
        if not reg_df.empty:
            reg_df = reg_df.loc[reg_df.enabled.str.lower() == "yes"]
        if not reg_df.empty:
            NodeLegend["Voltage Regulator"] = list(reg_df['transformer_bus1'].unique())
                           
    colored_nodelist = []
    for key in NodeLegend.keys():
        temp_list = NodeLegend[key]
        colored_nodelist  = colored_nodelist + temp_list
        if  len(temp_list) != 0:
            if key == "Violation":
                label = "Bus " + NODE_COLORLEGEND[key]["label"]
            else:
                label = NODE_COLORLEGEND[key]["label"]
            nx.draw_networkx_nodes(Un_G, pos=filter_dictionary(dict_data=position_dict, wanted_keys=temp_list),
                                nodelist=temp_list, node_size=NODE_COLORLEGEND[key]["node_size"], node_color=NODE_COLORLEGEND[key]["node_color"], 
                                alpha=NODE_COLORLEGEND[key]["alpha"], label=label)
    
    # remaining_nodes = list(set(nodes_list) - set(colored_nodelist)) 
    # nx.draw_networkx_nodes(Un_G, pos=filter_dictionary(dict_data=position_dict, wanted_keys=remaining_nodes),
    #                             nodelist=remaining_nodes, node_size=default_node_size, node_color=default_node_color)
    plt.title(title, fontsize=50)
    plt.legend(fontsize=50)
    title = title.lower()
    title = title.replace(" ", "_")
    plt.savefig(os.path.join(fig_folder, title+".pdf"))
    plt.close()
    return


def plot_thermal_violations(fig_folder, title, equipment_with_violations, circuit_source=None):
    """Function to plot thermal violations in network.
    """
    default_node_size = 2
    default_node_color = 'black'
    G = generate_networkx_representation()
    bus_coordinates_df = get_bus_coordinates()
    complete_flag = check_buscoordinates_completeness(bus_coordinates_df)  # check if sufficient buscoordinates data is available
    if not complete_flag:  # feeder cannot be plotted if sufficient buscoordinates data is unavailable
        logger.warning(f"Unable to plot {title} because feeder model bus coordinates are not provided.")
        return
    position_dict = nx.get_node_attributes(G, 'pos')
    # nodes_list = G.nodes()
    # edges_list = G.edges()
    Un_G = G.to_undirected()
    fig = plt.figure(figsize=(40, 40), dpi=10)
    nx.draw_networkx_edges(Un_G, pos=position_dict, alpha=1.0, width=0.3)
    nx.draw_networkx_nodes(Un_G, pos=position_dict, alpha=1.0, node_size=default_node_size, node_color=default_node_color)
    
    NodeLegend = {}
    if circuit_source is not None:
        NodeLegend["Circuit Source"] = [circuit_source]
    colored_nodelist = []
    for key in NodeLegend.keys():
        temp_list = NodeLegend[key]
        colored_nodelist  = colored_nodelist + temp_list
        if  len(temp_list) != 0:
            label = NODE_COLORLEGEND[key]["label"]
            nx.draw_networkx_nodes(Un_G, pos=filter_dictionary(dict_data=position_dict, wanted_keys=temp_list),
                                nodelist=temp_list, node_size=NODE_COLORLEGEND[key]["node_size"], node_color=NODE_COLORLEGEND[key]["node_color"], 
                                alpha=NODE_COLORLEGEND[key]["alpha"], label=label)
    temp_xfmr_nodelist = []
    temp_line_nodelist = []
    for equipment_name in equipment_with_violations.keys():
        if equipment_name == "Transformer":
            # primary bus of transformer is plotted as a node
            xfmr_df = equipment_with_violations[equipment_name]
            temp_xfmr_nodelist = list(xfmr_df.loc[xfmr_df['status'] == 'overloaded']['bus_names_only'].str[0].values)
            key = "Violation"
            nx.draw_networkx_nodes(Un_G, pos=filter_dictionary(dict_data=position_dict, wanted_keys=temp_xfmr_nodelist),
                                nodelist=temp_xfmr_nodelist, node_size=NODE_COLORLEGEND[key]["node_size"], 
                                node_color=NODE_COLORLEGEND[key]["node_color"], alpha=NODE_COLORLEGEND[key]["alpha"], 
                                label="Transformer " + NODE_COLORLEGEND[key]["label"])
        elif equipment_name == "Line":
            # line violations are plotted as edges
            line_df = equipment_with_violations["Line"]
            line_df = line_df.loc[line_df['status'] == 'overloaded'].copy()
            if len(line_df) > 0: 
                line_df.loc[:, "bus1"] = line_df['bus1'].str.split('.', expand=True)[0].str.lower()
                line_df.loc[:, "bus2"] = line_df['bus2'].str.split('.', expand=True)[0].str.lower()
                temp_edgelist = list(zip(line_df.bus1, line_df.bus2))
                temp_line_nodelist = list(line_df['bus1'].unique()) + list(line_df['bus2'].unique())
                key = "Violation"
                nx.draw_networkx_edges(Un_G, pos=filter_dictionary(dict_data=position_dict, wanted_keys=temp_line_nodelist), 
                                    edgelist=temp_edgelist, edge_color=EDGE_COLORLEGEND[key]["edge_color"], alpha=EDGE_COLORLEGEND[key]["alpha"], 
                                    width=EDGE_COLORLEGEND[key]["edge_size"], label=EDGE_COLORLEGEND[key]["label"])
            
    plt.title(title, fontsize=50)
    plt.legend(fontsize=50)
    title = title.lower()
    title = title.replace(" ", "_")
    # plt.axis("off")
    plt.savefig(os.path.join(fig_folder, title+".pdf"))
    plt.close(fig)
    return


def plot_created_clusters(fig_folder, clusters_dict, circuit_source=None):
    """Function to plot created clusters in network, while placing voltage regulators.
    """
    os.makedirs(fig_folder, exist_ok=True)
    default_node_size = 2
    default_node_color = 'black'
    G = generate_networkx_representation()
    bus_coordinates_df = get_bus_coordinates()
    complete_flag = check_buscoordinates_completeness(bus_coordinates_df)  # check if sufficient buscoordinates data is available
    if not complete_flag:  # feeder cannot be plotted if sufficient buscoordinates data is unavailable
        logger.warning(f"Unable to plot {title} because feeder model bus coordinates are not provided.")
        return
    position_dict = nx.get_node_attributes(G, 'pos')
    Un_G = G.to_undirected()
    
    fig = plt.figure(figsize=(40, 40), dpi=10)
    nx.draw_networkx_edges(Un_G, pos=position_dict, alpha=1.0, width=0.3)
    nx.draw_networkx_nodes(Un_G, pos=position_dict, alpha=1.0, node_size=default_node_size, node_color=default_node_color)
    if circuit_source is not None:
        key = "Circuit Source"
        nx.draw_networkx_nodes(G, pos=filter_dictionary(dict_data=position_dict, wanted_keys=[circuit_source]),
                                nodelist=[circuit_source], node_size=NODE_COLORLEGEND[key]["node_size"], 
                                node_color=NODE_COLORLEGEND[key]["node_color"], alpha=NODE_COLORLEGEND[key]["alpha"], label=NODE_COLORLEGEND[key]["label"])
    num_clusters = len(clusters_dict.keys())
    col = 0
    for key, values in clusters_dict.items():
        buses_list = values["buses_list"]
        reg_node = values["node"]
        common_upstream_nodes_list = values["common_upstream_nodes_list"]
        nx.draw_networkx_nodes(G, pos=filter_dictionary(dict_data=position_dict, wanted_keys=buses_list),
                                nodelist=buses_list, node_size=500, node_color='C{}'.format(col), label=f"Bus Violations_cluster{key}")
        
        nx.draw_networkx_nodes(G, pos=filter_dictionary(dict_data=position_dict, wanted_keys=common_upstream_nodes_list),
                                nodelist=common_upstream_nodes_list, node_size=500, node_color='C{}'.format(col), alpha=0.3, 
                                label=f"Common Upstream Nodes_cluster{key}")
        
        nx.draw_networkx_nodes(G, pos=filter_dictionary(dict_data=position_dict, wanted_keys=[reg_node]),  nodelist=[reg_node], node_size=1000, node_color='r', 
                               label=f"Voltage Regulator_cluster{key}")
        col += 1
    
    title = f"all_bus_violations_grouped_in_{num_clusters}_clusters"
    plt.title(title, fontsize=50)
    plt.legend(fontsize=50)
    title = title.lower()
    title = title.replace(" ", "_")
    plt.savefig(os.path.join(fig_folder, title+".pdf"))
    plt.close(fig)
    return


def add_graph_bus_nodes(G, bus_coordinates_df):
    """Adds feeder buses as nodes to graph nodes
    """
    buses_list = bus_coordinates_df.to_dict('records')
    for item in buses_list:
        pos = [item['x_coordinate'], item['y_coordinate']]
        G.add_node(item['bus_name'], pos=pos)
    return G


def get_graph_edges_dataframe(attr_fields):
    """This function adds lines and transformers as edges to the graph
    All lines, switches, reclosers etc are modeled as lines, so calling lines takes care of all of them.
    Transformers are also added as edges since they form the edge between primary and secondary nodes

    """
    chosen_fields = ['bus1', 'bus2'] + attr_fields
    # prepare lines dataframe
    all_lines_df = get_thermal_equipment_info(compute_loading=False, equipment_type="line")
    all_lines_df['bus1'] = all_lines_df['bus1'].str.split('.', expand=True)[0].str.lower()
    all_lines_df['bus2'] = all_lines_df['bus2'].str.split('.', expand=True)[0].str.lower()
    # convert length to metres
    all_lines_df['length'] = all_lines_df.apply(lambda x: convert_length_units(length=x.length, unit_in=x.units, unit_out="m"), axis=1)
    all_lines_df['equipment_type'] = 'line'
    # prepare transformer dataframe
    all_xfmrs_df = get_thermal_equipment_info(compute_loading=False, equipment_type="transformer")
    all_xfmrs_df['length'] = 0.0
    all_xfmrs_df['bus1'] = all_xfmrs_df['bus_names_only'].str[0].str.lower()
    all_xfmrs_df['bus2'] = all_xfmrs_df['bus_names_only'].str[-1].str.lower()
    all_xfmrs_df['equipment_type'] = 'transformer'
    all_edges_df = pd.concat([all_lines_df[chosen_fields], all_xfmrs_df[chosen_fields]])
    return all_edges_df


def add_graph_edges(G, edges_df, attr_fields, source='bus1', target='bus2'):
    """add networkx edges from dataframe
    """
    # # for networkx 1.10 version (but doing this removes the node attributes) -- so resorting to looping through edges
    # G = nx.from_pandas_dataframe(df=edges_df, source=source, target=target, edge_attr=attr_fields,
    #                              create_using=G)

    # looping through all edges to add into graph
    for index, row in edges_df.iterrows():
        G.add_edge(u_of_edge=row[source], v_of_edge=row[target], attr_dict=dict(row[attr_fields]))

    # # will need to use this for networkx > 2.0
    # nx.convert_matrix.from_pandas_edgelist(all_lines_df[chosen_fields], source='bus1', target='bus2', edge_attr=attr_fields,
    #                              create_using=G)

    return G


def searchDictKey(dct, value):
    """This function returns a list of dictionary keys that have a certain value

    Parameters
    ----------
    dct
    value

    Returns
    -------

    """
    return [key for key in dct if (dct[key] == value)]


def generate_networkx_representation():
    """This function generates a networkx graph of the circuit

    Parameters
    ----------
    kwargs

    Returns
    -------

    """
    bus_coordinates_df = get_bus_coordinates()
    G = nx.DiGraph()
    G = add_graph_bus_nodes(G=G, bus_coordinates_df=bus_coordinates_df)  # add buses as nodes to the graph
    attr_fields = ['phases', 'length', 'name', 'equipment_type']  # define edge attributes
    edges_df = get_graph_edges_dataframe(attr_fields=attr_fields)  # get edges dataframe (from lines and transformers)
    # add edges to graph
    G = add_graph_edges(G=G, edges_df=edges_df, attr_fields=attr_fields, source='bus1', target='bus2')
    complete_flag = check_buscoordinates_completeness(bus_coordinates_df, verbose=True)  # check if sufficient buscoordinates data is available
    if complete_flag:
        # these new buscoords could be written out to a file after correction
        G, commands_list = correct_node_coordinates(G=G)  # corrects node coordinates 
    return G


def check_buscoordinates_completeness(bus_coordinates_df, verbose=False):
    """This function checks if complete bus coordinates are present. This is needed to plot feeder figures.
    """
    # if coordinates for a buses are [0,0], then it is considered incomplete/unavailable data
    percent_missing = len(bus_coordinates_df.loc[(bus_coordinates_df["x_coordinate"] == 0) & (bus_coordinates_df["y_coordinate"] == 0)]) * 100 / len(bus_coordinates_df)
    complete_flag = percent_missing <= 25
    # if buscoordinates data is incomplete, log the completeness of data
    if not complete_flag:
        if verbose:
            logger.warning(f"Buscoordinates missing for {percent_missing:.2f}% of buses in feeder model. Please verify accurate buscoordinates.dss is present, to plot figures.")
    return complete_flag


def correct_node_coordinates(G):
    """If node doesn't have node attributes, attach parent or child node's attributes
    Parameters
    ----------
    G
    circuit_source

    Returns
    -------

    """
    position_dict = nx.get_node_attributes(G, 'pos')
    missing_coords_nodes = searchDictKey(position_dict, [0, 0])  # get list of nodes with missing coordinates ([0,0])
    commands_list = []

    # iterate over all nodes with missing coordinates
    for missing_node in missing_coords_nodes:
        position_dict = nx.get_node_attributes(G, 'pos')
        parent_node = list(G.predecessors(missing_node))  # find list of parent nodes
        child_node = list(G.successors(missing_node))  # find list of child nodes
        reference_coord_set = {0}
        if len(parent_node) != 0:  # parent node exists
            reference_coord = position_dict[parent_node[0]]
            if set(reference_coord) == {0}:  # if parent node also has [0,0] coordinates
                ancestors_list = list(nx.ancestors(G, missing_node))  # find list of ancestors, and iterate over them
                for ancestor in ancestors_list:
                    reference_coord = position_dict[ancestor]
                    # once an ancestor with non zero coordinates is found, stop iteration
                    if set(reference_coord) != {0}:
                        break
            nx.set_node_attributes(G, {missing_node: reference_coord}, name="pos")  # assign coordinates
            commands_list.append("{} {} {}".format(missing_node, reference_coord[0], reference_coord[1]))
        elif len(child_node) != 0:  # child node exists
            reference_coord = position_dict[child_node[0]]
            if set(reference_coord) == {0}:  # if child node also has [0,0] coordinates
                successors_list = list(nx.dfs_successors(G, missing_node))   # find list of successors, and iterate over them
                for successor in successors_list:
                    reference_coord = position_dict[successor]
                    # once a node with non zero coordinates is found, stop iteration
                    if set(reference_coord) != {0}:
                        break
            nx.set_node_attributes(G, {missing_node: reference_coord}, name="pos")  # assign coordinates
            commands_list.append("{} {} {}".format(missing_node, reference_coord[0], reference_coord[1]))
        else:  # if there are no parent or child nodes
            continue  # can't correct coordinates cause no parent or child nodes found.
    return G, commands_list


def check_substation_LTC(new_ckt_info, xfmr_name):
    """Function to assign settings if regulator upgrades are on substation transformer

    """
    subltc_dict = None      
    if isinstance(new_ckt_info["substation_xfmr"], dict):
        if new_ckt_info["substation_xfmr"]["name"].lower() == xfmr_name:
            subltc_dict = {}
            subltc_dict["at_substation"] = True
            subltc_dict.update(new_ckt_info["substation_xfmr"])         
    return subltc_dict


def get_regulator_upgrades(orig_regcontrols_df, new_regcontrols_df, orig_xfmrs_df, new_ckt_info):
    """function to check for regulator upgrades
    """
    if len(orig_regcontrols_df) > 0:
        orig_reg_controls = orig_regcontrols_df.set_index('name').transpose().to_dict()
    else:
        orig_reg_controls = {}
    if len(new_regcontrols_df) > 0:
        new_reg_controls = new_regcontrols_df.set_index('name').transpose().to_dict()
    else:
        new_reg_controls = {}
    if len(orig_xfmrs_df) > 0:
        orig_xfmr_info = orig_xfmrs_df.set_index('name').transpose().to_dict()
    else:
        orig_xfmr_info = {}
    
    final_reg_upgrades = {}
    processed_outputs = []
    # STEP 1: compare controllers that exist in both: original and new
    change = compare_dict(orig_reg_controls, new_reg_controls)
    modified_regulators = list(change.keys())
    # STEP 2: account for any new controllers added (which are not there in original)
    new_addition = list(set(new_reg_controls.keys()) -
                        (set(orig_reg_controls.keys()) & set(new_reg_controls.keys())))
    reg_upgrades = [*modified_regulators, *new_addition]  # combining these two lists to get upgraded regulators
    # if there are any upgrades & enabled, only then write to the file
    if reg_upgrades:
        for ctrl_name in reg_upgrades:
            if new_reg_controls[ctrl_name]['enabled'] == "Yes":
                final_reg_upgrades["reg_settings"] = True  # settings are changed
                final_reg_upgrades["reg_ctrl_name"] = ctrl_name.lower()
                final_reg_upgrades["reg_vsp"] = float(new_reg_controls[ctrl_name]["vreg"])
                final_reg_upgrades["reg_band"] = float(new_reg_controls[ctrl_name]["band"])
                final_reg_upgrades["xfmr_kva"] = new_reg_controls[ctrl_name]["transformer_kva"]
                final_reg_upgrades["xfmr_kv"] = new_reg_controls[ctrl_name]["transformer_kv"]
                final_reg_upgrades["xfmr_name"] = new_reg_controls[ctrl_name]["transformer"]
                final_reg_upgrades["new_xfmr"] = False  # default = False: new transformer is not added
                final_reg_upgrades["at_substation"] = False  # default False; (is not at substation)
                # if regulators are modified (and exist in both original and new)
                subltc_dict = None
                xfmr_dict = None
                if ctrl_name in modified_regulators:
                    final_reg_upgrades["reg_added"] = False  # not a new regulator
                    subltc_dict = check_substation_LTC(new_ckt_info=new_ckt_info, 
                                                       xfmr_name=final_reg_upgrades["xfmr_name"])  # check if regulator is on substation transformer
                    if subltc_dict is not None:  # if transformer is at substation
                        final_reg_upgrades.update(subltc_dict)
                    else:  # voltage regcontrol is not at substation_xfmr
                        xfmr_df = get_thermal_equipment_info(equipment_type="transformer", compute_loading=False)
                        xfmr_dict = xfmr_df.loc[xfmr_df["name"] == final_reg_upgrades['xfmr_name']].to_dict(orient='records')[0]
                        
                elif ctrl_name in new_addition:
                    final_reg_upgrades["reg_added"] = True  # is a new regulator
                    final_reg_upgrades["reg_settings"] = False  # settings are not changed
                    subltc_dict = check_substation_LTC(new_ckt_info=new_ckt_info, 
                                                       xfmr_name=final_reg_upgrades["xfmr_name"])   # check if regulator is on substation transformer
                    if subltc_dict is not None:  # if transformer is at substation
                        final_reg_upgrades.update(subltc_dict)
                    else:  # voltage regcontrol is not at substation_xfmr
                        xfmr_df = get_thermal_equipment_info(equipment_type="transformer", compute_loading=False)
                        xfmr_dict = xfmr_df.loc[xfmr_df["name"] == final_reg_upgrades['xfmr_name']].to_dict(orient='records')[0]
                    # if regulator transformer is not in the original xfmr list, then a new xfmr
                    if final_reg_upgrades["xfmr_name"] not in orig_xfmr_info:
                        final_reg_upgrades["new_xfmr"] = True  # is a new xfmr
                temp = {
                    "equipment_type": "RegControl",
                    "name": final_reg_upgrades["reg_ctrl_name"],
                    "new_controller_added": final_reg_upgrades["reg_added"],
                    "controller_settings_modified": final_reg_upgrades["reg_settings"],
                    "new_transformer_added": final_reg_upgrades["new_xfmr"],
                    "at_substation": final_reg_upgrades["at_substation"],
                    "final_settings": {
                        "vreg": final_reg_upgrades["reg_vsp"],
                        "band": final_reg_upgrades["reg_band"]
                    }}
                if subltc_dict is not None:
                    temp["final_settings"].update(subltc_dict)
                if xfmr_dict is not None:
                    temp["final_settings"].update(xfmr_dict)
                m = VoltageUpgradesTechnicalResultModel(**temp)
                processed_outputs.append(m)    
    return processed_outputs
