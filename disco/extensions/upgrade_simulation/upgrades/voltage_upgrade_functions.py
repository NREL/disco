import re
import seaborn as sns
import networkx as nx
import matplotlib.pyplot as plt
import logging
from sklearn.cluster import AgglomerativeClustering

from .common_functions import *
from .thermal_upgrade_functions import define_xfmr_object
from disco import timer_stats_collector
from jade.utils.timing_utils import track_timing, Timer

logger = logging.getLogger(__name__)


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
    control_command = re.sub("enabled=True", "enabled=False", control_command)
    dss.run_command(control_command)  # disable and run previous control command

    new_control_command = re.sub("DeadTime=\d+", 'DeadTime=' +
                                 str(capacitor_settings["new_deadtime"]), new_control_command)
    new_control_command = re.sub("Delay=\d+", 'Delay=' + str(capacitor_settings["new_delay"]), new_control_command)
    new_control_command = re.sub("ONsetting=\d+\.\d+", 'ONsetting=' +
                                 str(capacitor_settings["new_capON"]), new_control_command)
    new_control_command = re.sub("OFFsetting=\d+\.\d+", 'OFFsetting=' +
                                 str(capacitor_settings["new_capOFF"]), new_control_command)
    return new_control_command


def correct_capacitor_parameters(default_capacitor_settings=None, orig_capacitors_df=None, nominal_voltage=None,
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
                                 f"DeadTime={default_capacitor_settings['capdeadtime']} enabled=True"
    # Correct settings of those cap banks for which cap control object is available
    capacitors_commands_list = []
    capcontrol_present_df = orig_capacitors_df.loc[orig_capacitors_df['capcontrol_present'] == 'capcontrol']
    for index, row in capcontrol_present_df.iterrows():
        # if it is already voltage controlled, modify PT ratio if new is different after re-computation
        if (row["capcontrol_type"].lower() == "voltage") and (round(row['PTratio'], 2) != round(row['old_PTratio'], 2)):
            orig_string = ' !original, corrected PTratio only'
            command_string = f"Edit CapControl.{row['capcontrol_name']} PTRatio={row['PTratio']}" + orig_string
            dss.run_command(command_string)
            # this does not change original settings, so should not cause convergence
            circuit_solve_and_check(raise_exception=True, **kwargs)
        # if capcontrol is present, change to voltage controlled and apply default settings.
        else:
            command_string = f"Edit CapControl.{row['capcontrol_name']} PTRatio={row['PTratio']} " \
                             f"{default_capcontrol_command}"
            dss.run_command(command_string)
            pass_flag = circuit_solve_and_check(raise_exception=False, **kwargs)
            if not pass_flag:
                command_string = edit_capacitor_settings_for_convergence(command_string)
                dss.run_command(command_string)
                # raise exception if no convergence even after change
                circuit_solve_and_check(raise_exception=True, **kwargs)
        capacitors_commands_list.append(command_string)

    # if there are capacitors without cap control, add a voltage-controlled cap control
    lines_df = get_thermal_equipment_info(compute_loading=False, equipment_type="line")
    lines_df['bus1_extract'] = lines_df['bus1'].str.split(".").str[0]
    no_capcontrol_present_df = orig_capacitors_df.loc[orig_capacitors_df['capcontrol_present'] != 'capcontrol']
    for index, row in no_capcontrol_present_df.iterrows():
        capcontrol_name = "capcontrol" + row['capacitor_name']
        # extract line name that has the same bus as capacitor
        line_name = lines_df.loc[lines_df['bus1_extract'] == row['bus1']]['name'].values[0]
        default_pt_ratio = (row['kv'] * 1000) / nominal_voltage
        command_string = f"New CapControl.{capcontrol_name} element=Line.{line_name} " \
                         f"terminal={default_capacitor_settings['terminal']} capacitor={row['capacitor_name']} " \
                         f"PTRatio={default_pt_ratio} {default_capcontrol_command}"
        dss.run_command(command_string)
        pass_flag = circuit_solve_and_check(raise_exception=False, **kwargs)
        if not pass_flag:
            command_string = edit_capacitor_settings_for_convergence(command_string)
            dss.run_command(command_string)
            # raise exception if no convergence even after change
            circuit_solve_and_check(raise_exception=True, **kwargs)
        capacitors_commands_list.append(command_string)
    return capacitors_commands_list


@track_timing(timer_stats_collector)
def sweep_capacitor_settings(voltage_config=None, initial_capacitors_df=None, default_capacitor_settings=None, voltage_upper_limit=None,
                             voltage_lower_limit=None, **kwargs):
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
            dss.run_command(f"Edit CapControl.{row['capcontrol_name']} ONsetting={cap_on_setting} "
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


def choose_best_capacitor_sweep_setting(capacitor_sweep_df=None, initial_capacitors_df=None, **kwargs):
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
    deciding_field = 'deviation_severity'
    min_severity_setting = capacitor_sweep_df.loc[capacitor_sweep_df[deciding_field].idxmin()]
    setting_type = ''
    # if min severity is greater than or same as severity of original setting,
    # then just assign original setting as min_severity_setting
    if min_severity_setting[deciding_field] >= original_setting[deciding_field]:
        capacitors_df = initial_capacitors_df.copy()  # here best_setting is initial settings
        logger.info("Original capacitor settings are best. No need to change capacitor settings.")
        setting_type = 'initial_setting'
    else:
        # apply same best setting to all capacitors
        capacitors_df = initial_capacitors_df.copy()
        capacitors_df['ONsetting'] = min_severity_setting['cap_on_setting']
        capacitors_df['OFFsetting'] = min_severity_setting['cap_off_setting']
    properties_list = ["ONsetting", "OFFsetting"]  # list of properties to be edited in commands
    capacitor_settings_commands_list = create_capcontrol_settings_commands(properties_list=properties_list,
                                                                           capacitors_df=capacitors_df,
                                                                           creation_action='Edit')
    for command_string in capacitor_settings_commands_list:
        dss.run_command(command_string)
    circuit_solve_and_check(raise_exception=True, **kwargs)
    if setting_type == 'initial_setting':  # if initial settings are best, no need to return command with settings
        capacitor_settings_commands_list = []
    return capacitors_df, capacitor_settings_commands_list


def create_capcontrol_settings_commands(properties_list=None, capacitors_df=None, creation_action='New'):
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


def compute_voltage_violation_severity(voltage_upper_limit=None, voltage_lower_limit=None, **kwargs):
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
    deviation_severity = bus_voltages_df['Min voltage_deviation'].sum() + bus_voltages_df['Max voltage_deviation'].sum()
    undervoltage_bus_list = list(
        bus_voltages_df.loc[bus_voltages_df['Undervoltage violation'] == True]['name'].unique())
    overvoltage_bus_list = list(bus_voltages_df.loc[bus_voltages_df['Overvoltage violation'] == True]['name'].unique())
    buses_with_violations = undervoltage_bus_list + overvoltage_bus_list
    objective_function = len(buses_with_violations) * deviation_severity
    severity_dict = {'deviation_severity': deviation_severity,
                     'number_buses_with_violations': len(buses_with_violations),
                     'objective_function': objective_function}
    return severity_dict


def correct_regcontrol_parameters(orig_regcontrols_df=None, **kwargs):
    """This function corrects regcontrol ptratio is different from original. And generates commands list

    Parameters
    ----------
    orig_regcontrols_df

    Returns
    -------
    list
    """
    # correct regcontrol parameters settings
    default_regcontrol_command = " enabled=True"
    orig_string = ' !original, corrected PTratio only'
    regcontrols_commands_list = []
    for index, row in orig_regcontrols_df.iterrows():
        if round(row['ptratio'], 2) != round(row['old_ptratio'], 2):
            command_string = f"Edit RegControl.{row['name']} ptratio={row['ptratio']}" + default_regcontrol_command\
                             + orig_string
            dss.run_command(command_string)
            circuit_solve_and_check(raise_exception=True, **kwargs)
            # this does not change original settings, so should not cause convergence issues
            regcontrols_commands_list.append(command_string)
    return regcontrols_commands_list


@track_timing(timer_stats_collector)
def sweep_regcontrol_settings(voltage_config=None, initial_regcontrols_df=None, voltage_upper_limit=None, voltage_lower_limit=None,
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
                dss.run_command(f"Edit RegControl.{row['name']} vreg={vreg} band={band}")
                pass_flag = circuit_solve_and_check(raise_exception=False, **kwargs)
                if not pass_flag:  # if there is convergence issue at this setting, go onto next setting and dont save
                    temp_dict['converged'] = False
                    break
                else:
                    temp_dict['converged'] = True
                    try:
                        bus_voltages_df, undervoltage_bus_list, overvoltage_bus_list, buses_with_violations = get_bus_voltages(
                            voltage_upper_limit=voltage_config['initial_upper_limit'],
                            voltage_lower_limit=voltage_config['initial_lower_limit'], **kwargs)
                    except:  # catch convergence error
                        temp_dict['converged'] = False
                        break
                    severity_dict = compute_voltage_violation_severity(
                        voltage_upper_limit=voltage_upper_limit, voltage_lower_limit=voltage_lower_limit)
                    temp_dict.update(severity_dict)
                regcontrol_sweep_list.append(temp_dict)
    regcontrol_sweep_df = pd.DataFrame(regcontrol_sweep_list)
    return regcontrol_sweep_df


def choose_best_regcontrol_sweep_setting(regcontrol_sweep_df=None, initial_regcontrols_df=None, exclude_sub_ltc=True,
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
    deciding_field = 'deviation_severity'
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
        dss.run_command(command_string)
    circuit_solve_and_check(raise_exception=True, **kwargs)
    if setting_type == 'original':  # if original settings, no need to add to upgrades commands list
        regcontrol_settings_commands_list = []
        logger.info("Original Regulator control settings are the best.")
    return regcontrols_df, regcontrol_settings_commands_list


def create_regcontrol_settings_commands(properties_list=None, regcontrols_df=None, creation_action='New'):
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


def add_new_regcontrol_command(xfmr_info_series=None, default_regcontrol_settings=None, nominal_voltage=None, action_type='New', **kwargs):
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
    if type(xfmr_info_series['kVs']) == str:
        xfmr_info_series['kVs'] = ast.literal_eval(xfmr_info_series['kVs'])
    if xfmr_info_series['conns'] == str:
        xfmr_info_series['conns'] = ast.literal_eval(xfmr_info_series['conns'])
    sec_conn = xfmr_info_series['conns'][-1]
    if sec_conn.lower() == 'wye':
        sec_voltage = xfmr_info_series['kVs'][-1] / (math.sqrt(3))
    else:
        sec_voltage = xfmr_info_series['kVs'][-1]
    regcontrol_info_series["ptratio"] = (sec_voltage * 1000) / nominal_voltage
    # use the primary bus to define name
    regcontrol_info_series['regcontrol_name'] = 'new_regcontrol_' + xfmr_info_series['bus_names_only'][0]
    temp_df = get_regcontrol_info()
    enabled_regcontrol_exists = len(
        temp_df.loc[(temp_df['name'] == regcontrol_info_series['regcontrol_name']) & (temp_df['enabled'] == True)]) > 0
    if enabled_regcontrol_exists:
        logger.debug(f"Enabled regcontrol already exists: {regcontrol_info_series['name']}")
        # return {'command_list': [], 'new_regcontrol_name': None}
        return None
    disabled_regcontrol_exists = len(
        temp_df.loc[(temp_df['name'] == regcontrol_info_series['regcontrol_name']) & (temp_df['enabled'] == False)]) > 0
    if disabled_regcontrol_exists:
        action_type = 'Edit'
    new_regcontrol_command = define_regcontrol_object(regcontrol_name=regcontrol_info_series['regcontrol_name'],
                                                      action_type=action_type, regcontrol_info_series=regcontrol_info_series,
                                                      general_property_list=regcontrol_info_series["properties_to_be_defined"])
    check_dss_run_command(new_regcontrol_command)  # run command
    check_dss_run_command('CalcVoltageBases')
    pass_flag = circuit_solve_and_check(raise_exception=False, **kwargs)  # solve circuit
    command_list.append(new_regcontrol_command)
    return {'command_list': command_list, 'new_regcontrol_name': regcontrol_info_series['regcontrol_name']}


def define_regcontrol_object(regcontrol_name='', action_type='', regcontrol_info_series=None,
                             general_property_list=None):
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
    command_string = command_string + " enabled=True"
    return command_string


def sweep_and_choose_regcontrol_setting(voltage_config=None, initial_regcontrols_df=None, upper_limit=None,
                                        lower_limit=None, exclude_sub_ltc=True, only_sub_ltc=False, dss_file_list=None,
                                        dss_commands_list=None, **kwargs):
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
    # sweep through settings and identify best setting
    regcontrol_sweep_df = sweep_regcontrol_settings(voltage_config=voltage_config,
                                                    initial_regcontrols_df=initial_regcontrols_df,
                                                    voltage_upper_limit=upper_limit, voltage_lower_limit=lower_limit,
                                                    exclude_sub_ltc=exclude_sub_ltc, only_sub_ltc=only_sub_ltc,
                                                    **kwargs)
    # reload circuit after settings sweep
    reload_dss_circuit(dss_file_list=dss_file_list, commands_list=dss_commands_list, **kwargs)
    # choose best setting
    regcontrols_df, regcontrol_settings_commands_list = choose_best_regcontrol_sweep_setting(
        regcontrol_sweep_df=regcontrol_sweep_df, initial_regcontrols_df=initial_regcontrols_df,
        exclude_sub_ltc=exclude_sub_ltc, only_sub_ltc=only_sub_ltc, **kwargs)
    return regcontrols_df, regcontrol_settings_commands_list


def add_substation_xfmr(chosen_option_row=None, data_row=None, **kwargs):

    command_string = define_xfmr_object(xfmr_name=data_row['name'], xfmr_info_series=chosen_option_row,
                                        action_type='New', buses_list=data_row['buses'])
    dss.run_command(command_string)
    circuit_solve_and_check(raise_exception=True, **kwargs)  # solve circuit and CalcVoltageBases

    return command_string


def compare_objective_function():
    final_settings_commands = []
    return final_settings_commands


def add_new_node_and_xfmr(node=None, circuit_source=None, sub_xfmr_conn_type=None, action_type='New',
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
        chosen_line_info = all_lines_df.loc[all_lines_df["bus1_name"] == node].iloc[0]
        new_node = "newnode_" + chosen_line_info["bus2"]  # contains terminal information too
        new_node_name = "newnode_" + chosen_line_info["bus2_name"]
        curr_time = str(time.time())
        # this is added to name to ensure it is unique
        time_stamp = curr_time.split(".")[0] + "_" + curr_time.split(".")[1]
        xfmr_name = "New_xfmr_" + node + time_stamp
        dss.Circuit.SetActiveBus(chosen_line_info["bus1_name"])
        x = dss.Bus.X()
        y = dss.Bus.Y()
        dss.Circuit.SetActiveBus(chosen_line_info["bus2_name"])
        kV_node = dss.Bus.kVBase()
        if chosen_line_info["phases"] > 1:
            kV_DT = kV_node * math.sqrt(3)  # L-L voltage
        # if single phase node
        else:
            kV_DT = kV_node  # L-N voltage
        # ideally we would use an auto transformer which would need a much smaller kVA rating
        kVA = int(kV_DT * chosen_line_info["normamps"] * 1.1)   # 10% over sized transformer
        new_xfmr_command_string = f"{action_type} Transformer.{xfmr_name} phases={chosen_line_info['phases']} " \
                                  f"windings=2 buses=({chosen_line_info['bus1']}, {new_node}) " \
                                  f"conns=({sub_xfmr_conn_type},{sub_xfmr_conn_type}) kvs=({kV_DT},{kV_DT}) " \
                                  f"kvas=({kVA},{kVA}) xhl=0.001 wdg=1 %r=0.001 wdg=2 %r=0.001 Maxtap=1.1 Mintap=0.9 " \
                                  f"enabled=True"
        property_list = ["phases", "windings", "buses", "conns", "kvs", "kvas", "xhl", "%Rs", "Maxtap", "Mintap"]
        edit_line_command_string = f"Edit Line.{chosen_line_info['name']} bus1={new_node}"

    # If not subltc: For regulator, transformer will be placed after line. (i.e. new node will be created after bus2)
    else:
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
                                  f"conns=(wye,wye) kvs=({kV_DT},{kV_DT}) kvas=({kVA},{kVA}) xhl=0.001 " \
                                  f"wdg=1 %r=0.001 wdg=2 %r=0.001 Maxtap=1.1 Mintap=0.9 enabled=True"
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
    circuit_solve_and_check(raise_exception=True, **kwargs)
    info_dict = {'commands_list': commands_list, 'new_xfmr_name': xfmr_name,
                 'modified_line_name': chosen_line_info["name"]}
    return info_dict


def disable_new_xfmr_and_edit_line(transformer_name_to_disable=None, line_name_to_modify=None, **kwargs):
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
    command_string = f"Edit Transformer.{transformer_name_to_disable} enabled=False"
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


def add_new_regcontrol_at_node(node=None, default_regcontrol_settings=None, nominal_voltage=None, **kwargs):
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
    enabled_regcontrols_df = regcontrols_df.loc[regcontrols_df['enabled'] == True]
    enabled_regcontrol_exists = len(enabled_regcontrols_df.loc[(enabled_regcontrols_df['transformer_bus1'] == node) | (
        enabled_regcontrols_df['transformer_bus2'] == node)]) > 0
    if enabled_regcontrol_exists:
        return None
    else:  # if enabled regcontrol does not exist on transformer
        # this runs the command and returns the command list
        new_regcontrol_dict = add_new_regcontrol_command(xfmr_info_series=chosen_xfmr, default_regcontrol_settings=default_regcontrol_settings,
                                                         nominal_voltage=nominal_voltage, **kwargs)
    return new_regcontrol_dict


def add_bus_nodes(G=None, bus_coordinates_df=None):
    buses_list = bus_coordinates_df.to_dict('records')
    for item in buses_list:
        G.add_node(item['bus_name'], pos=[item['x_coordinate'], item['y_coordinate']])
    return G


def extract_common_element_from_lists(list_of_lists=None):
    # common element extraction from multiple lists
    common_element_list = list(set.intersection(*map(set, list_of_lists)))
    return common_element_list


def identify_common_upstream_nodes(G=None, buses_list=None):
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


def test_new_regulator_placement_on_common_nodes(voltage_upper_limit=None, voltage_lower_limit=None, nominal_voltage=None,
                                                 common_upstream_nodes_list=None, circuit_source=None,
                                                 default_regcontrol_settings=None, **kwargs):
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
    deciding_field = 'deviation_severity'
    intra_cluster_group_severity_dict = {}

    for node in common_upstream_nodes_list:
        print(node)
        node = node.lower()
        # do not add a new reg control to source bus as it already has a LTC
        if node == circuit_source.lower():
            continue
        all_xfmr_df = get_thermal_equipment_info(compute_loading=False, equipment_type="transformer")
        temp_df = all_xfmr_df['bus_names_only'].apply(pd.Series)
        all_xfmr_df["primary_bus"] = temp_df[0].str.lower()
        all_xfmr_df["secondary_bus"] = temp_df[1].str.lower()
        # if transformer is already present at this node, skip. This is because:
        # These pre-existing xfmrs will be "primary to secondary DTs" which we do not want to control.
        # Regulators are primarily in line and not on individual distribution transformers
        if (len(all_xfmr_df[all_xfmr_df["primary_bus"] == node]) > 0) or \
                (len(all_xfmr_df[all_xfmr_df["secondary_bus"] == node]) > 0):
            continue
        # add new transformer at this node
        new_xfmr_added_dict = add_new_node_and_xfmr(
            action_type='New', node=node, circuit_source=circuit_source, **kwargs)
        if new_xfmr_added_dict is None:  # if new elements were not added, continue
            continue
        # add new regulator control at this node
        # These are just default settings and do not have to be written in the output file
        new_regcontrol_dict = add_new_regcontrol_at_node(node=node, default_regcontrol_settings=default_regcontrol_settings,
                                                         nominal_voltage=nominal_voltage, **kwargs)
        if new_regcontrol_dict is None:
            if new_xfmr_added_dict is not None:
                disable_new_xfmr_and_edit_line(transformer_name_to_disable=new_xfmr_added_dict['new_xfmr_name'],
                                               line_name_to_modify=new_xfmr_added_dict['modified_line_name'])
            continue
        intra_cluster_group_severity_dict[node] = {}
        intra_cluster_group_severity_dict[node]['add_new_devices_command_list'] = new_xfmr_added_dict['commands_list'] + \
            new_regcontrol_dict['command_list']
        pass_flag = circuit_solve_and_check(raise_exception=False, **kwargs)
        intra_cluster_group_severity_dict[node]['converged'] = pass_flag
        severity_dict = compute_voltage_violation_severity(
            voltage_upper_limit=voltage_upper_limit, voltage_lower_limit=voltage_lower_limit, **kwargs)
        intra_cluster_group_severity_dict[node].update(severity_dict)
        intra_cluster_group_severity_dict[node].update({'new_xfmr_name': new_xfmr_added_dict['new_xfmr_name'], 'modified_line_name': new_xfmr_added_dict['modified_line_name'],
                                                        'new_regcontrol_name': new_regcontrol_dict['new_regcontrol_name']})
        # Now disable the added regulator control and remove the added transformer
        command_string = f"Edit RegControl.{new_regcontrol_dict['new_regcontrol_name']} enabled=No"
        check_dss_run_command(command_string)
        intra_cluster_group_severity_dict[node]['disable_new_devices_command_list'] = disable_new_xfmr_and_edit_line(transformer_name_to_disable=new_xfmr_added_dict['new_xfmr_name'],
                                                                                                                     line_name_to_modify=new_xfmr_added_dict[
                                                                                                                         'modified_line_name'],
                                                                                                                     **kwargs)

    # For a given list of common nodes in a cluster, identify the node which leads to minimum number of violations
    deciding_df = pd.DataFrame.from_dict(intra_cluster_group_severity_dict, orient='index')
    if len(deciding_df) == 0:  # If no nodes is found break the loop and go to next number of clusters
        chosen_node = None
        return None
    deciding_df = deciding_df.loc[deciding_df['converged'] == True]
    chosen_node = deciding_df[deciding_field].idxmin()  # node with minimum violations severity
    logger.debug(f"Node with minimum violation {deciding_field} is: {chosen_node}")

    # Since this is an optimal location add the transformer here - this transformer will stay as long as
    # clustering_option_number (num_clusters) does not increment. If this parameter changes then all devices at nodes mentioned
    # should be disabled
    add_new_node_and_xfmr(node=chosen_node, circuit_source=circuit_source, action_type='New', **kwargs)
    chosen_node_dict = intra_cluster_group_severity_dict[chosen_node]
    chosen_node_dict['node'] = chosen_node
    command_string = f"Edit RegControl.{chosen_node_dict['new_regcontrol_name']} enabled=True"
    check_dss_run_command(command_string)
    circuit_solve_and_check(raise_exception=True, **kwargs)
    return chosen_node_dict


def correct_node_coords(G=None, position_dict=None, circuit_source=None):
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


def get_full_distance_df(upper_triang_paths_dict=None):
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


def generate_edges(G=None):
    """All lines, switches, reclosers etc are modeled as lines, so calling lines takes care of all of them.
    However we also need to loop over transformers as they form the edge between primary and secondary nodes

    Parameters
    ----------
    G

    Returns
    -------

    """
    length_conversion_to_metre = {
        "mi": 1609.34,
        "kft": 304.8,
        "km": 1000,
        "ft": 0.3048,
        "in": 0.0254,
        "cm": 0.01,
        "m": 1,
    }

    # prepare lines dataframe
    all_lines_df = get_thermal_equipment_info(compute_loading=False, equipment_type="line")
    all_lines_df['bus1'] = all_lines_df['bus1'].str.split('.', expand=True)[0].str.lower()
    all_lines_df['bus2'] = all_lines_df['bus2'].str.split('.', expand=True)[0].str.lower()
    all_lines_df.apply(lambda x: x.length * length_conversion_to_metre[x.units])
    all_lines_df.apply(lambda x: x['length'] * length_conversion_to_metre[x['units']])
    all_lines_df.apply(lambda x: print(x))
    # convert length to metres

    all_lines_df['units']
    all_xfmrs_df = get_thermal_equipment_info(compute_loading=False, equipment_type="transformer")

    dss.Lines.First()
    while True:
        from_bus = dss.Lines.Bus1().split('.')[0].lower()
        to_bus = dss.Lines.Bus2().split('.')[0].lower()
        phases = dss.Lines.Phases()
        length = dss.Lines.Length()
        name = dss.Lines.Name()
        G.add_edge(from_bus, to_bus, phases=phases, length=length, name=name)
        if not dss.Lines.Next() > 0:
            break

    dss.Transformers.First()
    while True:
        bus_names = dss.CktElement.BusNames()
        from_bus = bus_names[0].split('.')[0].lower()
        to_bus = bus_names[1].split('.')[0].lower()
        phases = dss.CktElement.NumPhases()
        length = 0.0
        name = dss.Transformers.Name()
        G.add_edge(from_bus, to_bus, phases=phases, length=length, name=name)
        if not dss.Transformers.Next() > 0:
            break
    return G


def get_upper_triangular_dist(G=None, buses_with_violations=None):
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


def perform_clustering(num_clusters=None, square_distance_array=None, buses_with_violations=None):
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
    model = AgglomerativeClustering(n_clusters=num_clusters, affinity='euclidean', linkage='ward')
    model.fit(square_distance_array)
    labels_list = model.labels_
    # create a dictionary containing cluster_number as keys, and list of buses in that cluster as values
    for label in range(len(labels_list)):
        if labels_list[label] not in clusters_dict:
            clusters_dict[labels_list[label]] = [buses_with_violations[label]]
        else:
            clusters_dict[labels_list[label]].append(buses_with_violations[label])
    return clusters_dict


def per_cluster_group_regulator_analysis(G=None, buses_list=None, voltage_config=None,
                                         voltage_upper_limit=None, voltage_lower_limit=None, default_regcontrol_settings=None,
                                         circuit_source=None, **kwargs):
    """This function performs analysis on one cluster group of buses with violations. 
    It determines the common upstream buses for all the buses with violations in that cluster group. 
    It places regulators on each of these common noeds, and determines the best node to place the regulator for that group.
    Also determines the best reg control settings with this newly added regulator.

    Args:
        G (_type_, optional): _description_. Defaults to None.
        cluster_id (_type_, optional): _description_. Defaults to None.
        buses_list (_type_, optional): _description_. Defaults to None.
        voltage_config (_type_, optional): _description_. Defaults to None.
        voltage_upper_limit (_type_, optional): _description_. Defaults to None.
        voltage_lower_limit (_type_, optional): _description_. Defaults to None.
        default_regcontrol_settings (_type_, optional): _description_. Defaults to None.
        circuit_source (_type_, optional): _description_. Defaults to None.

    Returns:
        _type_: _description_
    """
    cluster_group_info_dict = {}
    nominal_voltage = voltage_config['nominal_voltage']
    # this identifies common upstream nodes for all buses with violations in a given cluster
    # these common upstream nodes are where regulator control can be placed
    common_upstream_nodes_list = identify_common_upstream_nodes(G=G, buses_list=buses_list)
    cluster_group_info_dict['common_upstream_nodes_list'] = common_upstream_nodes_list
    # this adds new regulator on each common node (one at a time)
    chosen_node_dict = test_new_regulator_placement_on_common_nodes(voltage_upper_limit=voltage_upper_limit, voltage_lower_limit=voltage_lower_limit,
                                                                    nominal_voltage=nominal_voltage,
                                                                    common_upstream_nodes_list=common_upstream_nodes_list, circuit_source=circuit_source,
                                                                    default_regcontrol_settings=default_regcontrol_settings, **kwargs)
    if chosen_node_dict is None:  # if there is no common node on which regulator can be placed (for this cluster group)
        return None
    cluster_group_info_dict.update(chosen_node_dict)
    write_flag = 0
    # choose best settings for all regulators (with new regulator added)
    init_regcontrols_df = get_regcontrol_info(correct_PT_ratio=True, nominal_voltage=nominal_voltage)
    regcontrol_sweep_df = sweep_regcontrol_settings(voltage_config=voltage_config, initial_regcontrols_df=init_regcontrols_df,
                                                    voltage_upper_limit=voltage_upper_limit, voltage_lower_limit=voltage_lower_limit,
                                                    exclude_sub_ltc=True, only_sub_ltc=False, **kwargs)
    regcontrols_df, regcontrol_settings_commands_list = choose_best_regcontrol_sweep_setting(
        regcontrol_sweep_df=regcontrol_sweep_df, initial_regcontrols_df=init_regcontrols_df, exclude_sub_ltc=True,
        only_sub_ltc=False, **kwargs)
    # determine violation severity after changes
    severity_dict = compute_voltage_violation_severity(
        voltage_upper_limit=voltage_upper_limit, voltage_lower_limit=voltage_lower_limit, **kwargs)
    cluster_group_info_dict.update(severity_dict)
    cluster_group_info_dict['settings_commands_list'] = regcontrol_settings_commands_list

    return cluster_group_info_dict


def cluster_and_place_regulator(G=None, square_distance_df=None, buses_with_violations=None, num_clusters=None,
                                voltage_config=None, voltage_upper_limit=None, voltage_lower_limit=None,
                                default_regcontrol_settings=None, circuit_source=None, **kwargs):
    # this function performs clustering on buses with violations, then iterates through each cluster group, performs regulator placement analysis
    # Returns the best regulator placement for each cluster group, in the form of a dict

    # this creates clusters of buses based on distance matrix. So nearby buses are clustered together
    clusters_dict = perform_clustering(square_distance_array=square_distance_df, num_clusters=num_clusters,
                                       buses_with_violations=buses_with_violations)
    cluster_group_info_dict = {}
    # iterate through each cluster group
    for cluster_id, buses_list in clusters_dict.items():
        logger.debug(f"Cluster group: {cluster_id}")
        cluster_group_info_dict[cluster_id] = per_cluster_group_regulator_analysis(G=G, buses_list=buses_list, voltage_config=voltage_config,
                                                                                   voltage_upper_limit=voltage_upper_limit, voltage_lower_limit=voltage_lower_limit, default_regcontrol_settings=default_regcontrol_settings,
                                                                                   circuit_source=circuit_source, **kwargs)
        # determine voltage violations after capacitor changes
        bus_voltages_df, undervoltage_bus_list, overvoltage_bus_list, buses_with_violations = get_bus_voltages(
            voltage_upper_limit=voltage_upper_limit, voltage_lower_limit=voltage_lower_limit, **kwargs)
        if (len(buses_with_violations)) == 0:
            logger.info("All nodal violations have been removed successfully.....quitting")
            break

    return cluster_group_info_dict


@track_timing(timer_stats_collector)
def determine_new_regulator_location(max_regs=2, circuit_source=None, buses_with_violations=None,
                                     voltage_upper_limit=None, voltage_lower_limit=None, create_plot=False, voltage_config=None,
                                     default_regcontrol_settings=None, **kwargs):
    deciding_field = 'deviation_severity'
    # prepare for clustering
    G = generate_networkx_representation(create_plot=False)
    upper_triang_paths_dict = get_upper_triangular_dist(G=G, buses_with_violations=buses_with_violations)
    square_distance_df = get_full_distance_df(upper_triang_paths_dict=upper_triang_paths_dict)
    if create_plot:
        fig_folder = kwargs.get('fig_folder', None)
        plot_heatmap_distmatrix(square_array=square_distance_df, fig_folder=fig_folder)
    cluster_options_dict = {}

    # Clustering the distance matrix into clusters equal to optimal clusters
    # change number of clusters to be considered in the network, and perform analysis.
    for num_clusters in range(1, max_regs + 1, 1):
        cluster_option_name = f"cluster_option_{num_clusters}"
        print(f"Clustering: {num_clusters}")
        logger.debug(f"\nClustering option: {num_clusters}")
        temp_dict = cluster_and_place_regulator(G=G, square_distance_df=square_distance_df,
                                                buses_with_violations=buses_with_violations, num_clusters=num_clusters,
                                                voltage_config=voltage_config, voltage_upper_limit=voltage_upper_limit, voltage_lower_limit=voltage_lower_limit,
                                                default_regcontrol_settings=default_regcontrol_settings, circuit_source=circuit_source, **kwargs)
        cluster_options_dict[cluster_option_name] = {}
        cluster_options_dict[cluster_option_name]["details"] = temp_dict
        severity_dict = compute_voltage_violation_severity(
            voltage_upper_limit=voltage_upper_limit, voltage_lower_limit=voltage_lower_limit, **kwargs)
        # disable previous clustering option before moving onto next cluster option
        disable_previous_clustering_option(cluster_group_info_dict=cluster_options_dict[cluster_option_name]["details"])
        cluster_options_dict[cluster_option_name].update(severity_dict)
        # determine voltage violations after changes
        bus_voltages_df, undervoltage_bus_list, overvoltage_bus_list, buses_with_violations = get_bus_voltages(
            voltage_upper_limit=voltage_upper_limit, voltage_lower_limit=voltage_lower_limit, **kwargs)
        if (len(buses_with_violations)) == 0:
            logger.info("All nodal violations have been removed successfully.....quitting")
            break
    # choose best clustering option based on severity dict
    deciding_df = pd.DataFrame.from_dict(cluster_options_dict, orient='index')
    # deciding_df = deciding_df.loc[deciding_df['converged'] == True]
    chosen_cluster_option = deciding_df[deciding_field].idxmin()
    chosen_cluster_details = cluster_options_dict[chosen_cluster_option]["details"]
    new_commands = []
    for group_num in chosen_cluster_details.keys():
        if chosen_cluster_details[group_num] is not None:
            new_commands = chosen_cluster_details[group_num]["add_new_devices_command_list"] + \
                chosen_cluster_details[group_num]["settings_commands_list"]
    return new_commands


def disable_previous_clustering_option(cluster_group_info_dict):
    for cluster_id in cluster_group_info_dict.keys():
        if cluster_group_info_dict[cluster_id] is None:
            return
        command_list = cluster_group_info_dict[cluster_id]['disable_new_devices_command_list']
        dss_run_command_list(command_list)  # runs each command in this list, in opendss
        dss_solve_and_check(raise_exception=True)
    return


def plot_heatmap_distmatrix(square_array=None, fig_folder=None):
    plt.figure(figsize=(7, 7))
    ax = sns.heatmap(square_array, linewidth=0.5)
    plt.title("Distance matrix of nodes with violations")
    plt.savefig(os.path.join(fig_folder, "Nodal_violations_heatmap.pdf"))


def plot_feeder(G=None, show_fig=False, fig_folder=None):
    position_dict = nx.get_node_attributes(G, 'pos')
    nodes_list = G.nodes()

    plt.figure(figsize=(7, 7))
    plt.figure(figsize=(40, 40), dpi=10)
    plt.clf()
    ec = nx.draw_networkx_edges(G, pos=position_dict, alpha=1.0, width=0.3)
    ldn = nx.draw_networkx_nodes(G, pos=position_dict, nodelist=nodes_list, node_size=2,
                                 node_color='k')

    # ld = nx.draw_networkx_nodes(G, pos=position_dict, nodelist=nodes_list, node_size=6,
    #                             node_color='yellow', alpha=0.7)

    # nx.draw_networkx_labels(G, pos=position_dict, node_size=1, font_size=15)
    plt.title("Feeder with all customers having DPV systems")
    plt.axis("off")
    plt.savefig(os.path.join(fig_folder, "Feeder.pdf"))
    if show_fig:
        plt.show()
    return


def plot_voltage_violations(G=None, buses_with_violations=None, fig_folder=None, circuit_source=None):
    position_dict = nx.get_node_attributes(G, 'pos')
    nodes_list = G.nodes()

    # convert to undirected
    Un_G = G.to_undirected()

    #plt.figure(figsize=(8, 7))
    plt.figure(figsize=(40, 40), dpi=10)
    plt.clf()
    numV = len(buses_with_violations)
    plt.title("Number of buses in the feeder with voltage violations: {}".format(numV))
    ec = nx.draw_networkx_edges(Un_G, pos=position_dict, alpha=1.0, width=0.3)
    ld = nx.draw_networkx_nodes(Un_G, pos=position_dict, nodelist=nodes_list, node_size=2, node_color='b')
    nx.draw_networkx_nodes(Un_G, pos=filter_dictionary(dict_data=position_dict, wanted_keys=[circuit_source]),
                           nodelist=[circuit_source], node_size=10, node_color='Y')

    buses_with_violations_pos = filter_dictionary(dict_data=position_dict, wanted_keys=buses_with_violations)
    # Show buses with violations
    if len(buses_with_violations) > 0:
        m = nx.draw_networkx_nodes(Un_G, pos=buses_with_violations_pos,
                                   nodelist=buses_with_violations, node_size=10, node_color='r')
    plt.axis("off")
    plt.savefig(os.path.join(fig_folder, "Nodal_voltage_violations_{}.pdf".format(str(numV))))
    return


def plot_thermal_violations(G=None, edge_size_list=None, edge_pos_plt_dict=None, edge_to_plt_dict=None, DT_sec_coords=None, DT_sec_lst=None, DT_size_list=None, fig_folder=None):
    position_dict = nx.get_node_attributes(G, 'pos')
    nodes_list = G.nodes()
    # convert to undirected
    Un_G = G.to_undirected()

    plt.figure(figsize=(40, 40), dpi=10)
    if len(edge_size_list) > 0:
        de = nx.draw_networkx_edges(Un_G, pos=edge_pos_plt_dict, edgelist=edge_to_plt_dict, edge_color="r",
                                    alpha=0.5, width=edge_size_list)
    ec = nx.draw_networkx_edges(Un_G, pos=position_dict, alpha=1.0, width=1)
    if len(DT_sec_lst) > 0:
        dt = nx.draw_networkx_nodes(Un_G, pos=DT_sec_coords, nodelist=DT_sec_lst, node_size=DT_size_list,
                                    node_color='deeppink', alpha=1)
    ldn = nx.draw_networkx_nodes(Un_G, pos=position_dict, nodelist=nodes_list, node_size=1,
                                 node_color='k', alpha=1)
    # nx.draw_networkx_labels(G, pos=pos_dict, node_size=1, font_size=15)
    plt.title("Thermal violations")
    plt.axis("off")
    plt.savefig(os.path.join(fig_folder, "Thermal_violations_{}.pdf".format(str(len(DT_sec_lst)))))


def plot_created_clusters(G=None, clusters_dict=None, upstream_nodes_dict=None, upstream_reg_node=None, cluster_nodes_list=None, optimal_clusters=None, fig_folder=None):
    plt.figure(figsize=(7, 7))
    # Plots clusters and common paths from clusters to source
    plt.clf()
    position_dict = nx.get_node_attributes(G, 'pos')
    ec = nx.draw_networkx_edges(G, pos=position_dict, alpha=1.0, width=0.3)
    ld = nx.draw_networkx_nodes(G, pos=position_dict, nodelist=cluster_nodes_list, node_size=2,
                                node_color='b')
    # Show min V violations
    col = 0
    try:
        for key, values in clusters_dict.items():
            nodal_violations_pos = {}
            common_nodes_pos = {}
            reg_nodes_pos = {}
            for cluster_nodes in values:
                nodal_violations_pos[cluster_nodes] = position_dict[cluster_nodes]
            for common_nodes in upstream_nodes_dict[key]:
                common_nodes_pos[common_nodes] = position_dict[common_nodes]
            logger.info("%s", upstream_reg_node[key])
            reg_nodes_pos[upstream_reg_node[key]] = position_dict[upstream_reg_node[key]]
            nx.draw_networkx_nodes(G, pos=nodal_violations_pos,
                                   nodelist=values, node_size=5, node_color='C{}'.format(col))
            nx.draw_networkx_nodes(G, pos=common_nodes_pos,
                                   nodelist=upstream_nodes_dict[key], node_size=5,
                                   node_color='C{}'.format(col), alpha=0.3)
            nx.draw_networkx_nodes(G, pos=reg_nodes_pos,
                                   nodelist=[upstream_reg_node[key]], node_size=25, node_color='r')
            col += 1
    except:
        pass
    plt.axis("off")
    plt.title("All buses with violations grouped in {} clusters".format(optimal_clusters))
    plt.savefig(
        os.path.join(fig_folder, "Cluster_{}_reglocations.pdf".format(str(optimal_clusters))))


def add_graph_bus_nodes(G=None, bus_coordinates_df=None):
    buses_list = bus_coordinates_df.to_dict('records')
    for item in buses_list:
        pos = [item['x_coordinate'], item['y_coordinate']]
        G.add_node(item['bus_name'], pos=pos)
    return G


def get_graph_edges_dataframe(attr_fields=None):
    """This function adds lines and transformers as edges to the graph
    All lines, switches, reclosers etc are modeled as lines, so calling lines takes care of all of them.
    Transformers are also added as edges since they form the edge between primary and secondary nodes

    """
    length_conversion_to_metre = {
        "mi": 1609.34,
        "kft": 304.8,
        "km": 1000,
        "ft": 0.3048,
        "in": 0.0254,
        "cm": 0.01,
        "m": 1,
    }
    chosen_fields = ['bus1', 'bus2'] + attr_fields

    # prepare lines dataframe
    all_lines_df = get_thermal_equipment_info(compute_loading=False, equipment_type="line")
    all_lines_df['bus1'] = all_lines_df['bus1'].str.split('.', expand=True)[0].str.lower()
    all_lines_df['bus2'] = all_lines_df['bus2'].str.split('.', expand=True)[0].str.lower()
    # convert length to metres
    all_lines_df['length'] = all_lines_df.apply(lambda x: x.length * length_conversion_to_metre[x.units], axis=1)
    all_lines_df['equipment_type'] = 'line'

    # prepare transformer dataframe
    all_xfmrs_df = get_thermal_equipment_info(compute_loading=False, equipment_type="transformer")
    all_xfmrs_df['length'] = 0.0
    all_xfmrs_df['bus1'] = all_xfmrs_df['bus_names_only'].str[0].str.lower()
    all_xfmrs_df['bus2'] = all_xfmrs_df['bus_names_only'].str[-1].str.lower()
    all_xfmrs_df['equipment_type'] = 'transformer'

    all_edges_df = all_lines_df[chosen_fields].append(all_xfmrs_df[chosen_fields])
    return all_edges_df


def add_graph_edges(G=None, edges_df=None, attr_fields=None, source='bus1', target='bus2'):
    # add edges from dataframe
    # # for networkx 1.10 version (but doing this removes the node attributes) -- so resorting to looping through edges
    # G = nx.from_pandas_dataframe(df=edges_df, source=source, target=target, edge_attr=attr_fields,
    #                              create_using=G)

    # looping through all edges to add into graph
    for index, row in edges_df.iterrows():
        G.add_edge(u=row[source], v=row[target], attr_dict=dict(row[attr_fields]))

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


def generate_networkx_representation(**kwargs):
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
    create_plot = kwargs.get('create_plot', False)
    # if create_plot:  # if plot is to be created, check if all nodes have coordinates
    G = correct_node_coordinates(G=G)
    # position_dict = nx.get_node_attributes(G, 'pos')  # to be removed. kept here as sample
    return G


def correct_node_coordinates(G=None):
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

    # iterate over all nodes with missing coordinates
    for missing_node in missing_coords_nodes:
        parent_node = G.predecessors(missing_node)  # find list of parent nodes
        child_node = G.successors(missing_node)  # find list of child nodes
        reference_coord_set = {0}
        if len(parent_node) != 0:  # parent node exists
            reference_coord = G.node[parent_node[0]]["pos"]
            if set(reference_coord) == {0}:  # if parent node also has [0,0] coordinates
                ancestors_list = G.ancestors(missing_node)  # find list of ancestors, and iterate over them
                for ancestor in ancestors_list:
                    reference_coord = G.node[ancestor]["pos"]
                    # once an ancestor with non zero coordinates is found, stop iteration
                    if set(reference_coord) != {0}:
                        break
            G.node[missing_node]["pos"] = reference_coord  # assign coordinates
        elif len(child_node) != 0:  # child node exists
            reference_coord = G.node[child_node[0]]["pos"]
            if set(reference_coord) == {0}:  # if child node also has [0,0] coordinates
                successors_list = nx.dfs_successors(G, missing_node)
                for successor in successors_list:
                    reference_coord = G.node[successor]["pos"]
                    # once a node with non zero coordinates is found, stop iteration
                    if set(reference_coord) != {0}:
                        break
            G.node[missing_node]["pos"] = reference_coord  # assign coordinates
        else:  # if there are no parent or child nodes
            continue  # can't correct coordinates cause no parent or child nodes found.
    return G


# function to get capacitor upgrades
def get_capacitor_upgrades(orig_capacitors_df=None, new_capacitors_df=None):
    if len(orig_capacitors_df) > 0:
        orig_capcontrols = orig_capacitors_df.set_index('capacitor_name').transpose().to_dict()
    else:
        orig_capcontrols = {}
    if len(new_capacitors_df) > 0:
        new_capcontrols = new_capacitors_df.set_index('capacitor_name').transpose().to_dict()
    else:
        new_capcontrols = {}
    
    final_cap_upgrades = {}
    processed_outputs = {}
    # STEP 1: compare controllers that exist in both: original and new- and get difference
    change = compare_dict(orig_capcontrols, new_capcontrols)
    modified_capacitors = list(change.keys())
    # STEP 2: account for any new controllers added (which are not there in original)
    new_addition = list(set(new_capcontrols.keys()) -
                        (set(orig_capcontrols.keys()) & set(new_capcontrols.keys())))
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
        processed_outputs[final_cap_upgrades["cap_name"]] = {
            "New controller added": final_cap_upgrades["ctrl_added"],
            "Controller settings modified": final_cap_upgrades["cap_settings"],
            "Final Settings": {
                "capctrl name": final_cap_upgrades["ctrl_name"],
                "cap kvar": final_cap_upgrades["cap_kvar"],
                "cap kV": final_cap_upgrades["cap_kv"],
                "ctrl type": final_cap_upgrades["ctrl_type"],
                "ON setting (V)": final_cap_upgrades["cap_on"],
                "OFF setting (V)": final_cap_upgrades["cap_off"]
            }
        }
    return processed_outputs


# function to assign settings if regulator upgrades are on substation transformer
def check_substation_LTC(new_ckt_info=None, xfmr_name=None):
    if new_ckt_info["substation_xfmr"]["name"].lower() == xfmr_name:
        subltc_dict = {}        
        subltc_dict["substation_xfmr"] = True
        subltc_dict["xfmr_kva"] = new_ckt_info["substation_xfmr"]["kVA"]
        subltc_dict["xfmr_kv"] = new_ckt_info["substation_xfmr"]["kV"]
    else:
        subltc_dict = None
    return subltc_dict


# function to check for regulator upgrades
def get_regulator_upgrades(orig_regcontrols_df=None, new_regcontrols_df=None, orig_xfmrs_df=None, new_ckt_info=None):
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
    processed_outputs = {}
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
            if new_reg_controls[ctrl_name]['enabled'] == True:
                final_reg_upgrades["reg_settings"] = "changed"  # settings are changed
                final_reg_upgrades["reg_ctrl_name"] = ctrl_name.lower()
                final_reg_upgrades["reg_vsp"] = float(new_reg_controls[ctrl_name]["vreg"])
                final_reg_upgrades["reg_band"] = float(new_reg_controls[ctrl_name]["band"])
                final_reg_upgrades["xfmr_kva"] = new_reg_controls[ctrl_name]["transformer_kva"]
                final_reg_upgrades["xfmr_kv"] = new_reg_controls[ctrl_name]["transformer_kv"]
                final_reg_upgrades["xfmr_name"] = new_reg_controls[ctrl_name]["transformer"]
                final_reg_upgrades["new_xfmr"] = False  # default = False: new transformer is not added
                final_reg_upgrades["sub_xfmr"] = False  # default False; (is not substation xfmr)
                # if regulators are modified (and exist in both original and new)
                if ctrl_name in modified_regulators:
                    final_reg_upgrades["reg_added"] = False  # not a new regulator
                    subltc_dict = check_substation_LTC(new_ckt_info=new_ckt_info, 
                                                       xfmr_name=final_reg_upgrades["xfmr_name"])  # check if regulator is on substation transformer
                    if subltc_dict is not None:
                        final_reg_upgrades.update(subltc_dict)
                elif ctrl_name in new_addition:
                    final_reg_upgrades["reg_added"] = True  # is a new regulator
                    subltc_dict = check_substation_LTC(new_ckt_info=new_ckt_info, 
                                                       xfmr_name=final_reg_upgrades["xfmr_name"])   # check if regulator is on substation transformer
                    if subltc_dict is not None:
                        final_reg_upgrades.update(subltc_dict)
                    # if regulator transformer is not in the original xfmr list, then a new xfmr
                    if final_reg_upgrades["xfmr_name"] not in orig_xfmr_info:
                        final_reg_upgrades["new_xfmr"] = True  # is a new xfmr
                processed_outputs["Regctrl." + final_reg_upgrades["reg_ctrl_name"]] = {
                    "New controller added": final_reg_upgrades["reg_added"],
                    "Controller settings modified": final_reg_upgrades["reg_settings"],
                    "New transformer added": final_reg_upgrades["new_xfmr"],
                    "Substation LTC": final_reg_upgrades["sub_xfmr"],
                    "Final settings": {
                        "Transformer name": final_reg_upgrades["xfmr_name"],
                        "Transformer kVA": final_reg_upgrades["xfmr_kva"],
                        "Transformer kV": final_reg_upgrades["xfmr_kv"],
                        "Reg ctrl V set point": final_reg_upgrades["reg_vsp"],
                        "Reg ctrl deadband": final_reg_upgrades["reg_band"]
                    }
                    }
    return processed_outputs
