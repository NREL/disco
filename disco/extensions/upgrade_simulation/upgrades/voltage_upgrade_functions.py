import re
import seaborn as sns
import matplotlib.pyplot as plt
import logging
from sklearn.cluster import AgglomerativeClustering

from .common_functions import *
from .thermal_upgrade_functions import define_xfmr_object

logger = logging.getLogger(__name__)


def edit_capacitor_settings_for_convergence(voltage_config=None, control_command=""):
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
        (
            voltage_config["nominal_voltage"]
            - (voltage_config["cap_sweep_voltage_gap"] + 1) / 2
        ),
        1,
    )
    capacitor_settings["new_capOFF"] = round(
        (
            voltage_config["nominal_voltage"]
            + (voltage_config["cap_sweep_voltage_gap"] + 1) / 2
        ),
        1,
    )
    capacitor_settings["new_deadtime"] = 50
    capacitor_settings["new_delay"] = 50
    logger.info("Changed Initial On and Off Cap settings to avoid convergence issues ")

    new_control_command = control_command
    control_command = control_command.replace("New", "Edit")
    control_command = re.sub("enabled=True", "enabled=False", control_command)
    dss.run_command(control_command)  # disable and run previous control command

    new_control_command = re.sub(
        "DeadTime=\d+",
        "DeadTime=" + str(capacitor_settings["new_deadtime"]),
        new_control_command,
    )
    new_control_command = re.sub(
        "Delay=\d+",
        "Delay=" + str(capacitor_settings["new_delay"]),
        new_control_command,
    )
    new_control_command = re.sub(
        "ONsetting=\d+\.\d+",
        "ONsetting=" + str(capacitor_settings["new_capON"]),
        new_control_command,
    )
    new_control_command = re.sub(
        "OFFsetting=\d+\.\d+",
        "OFFsetting=" + str(capacitor_settings["new_capOFF"]),
        new_control_command,
    )
    return new_control_command


def correct_capacitor_parameters(
    default_capacitor_settings=None,
    orig_capacitors_df=None,
    nominal_voltage=None,
    **kwargs,
):
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
    default_capcontrol_command = (
        f"Type={default_capacitor_settings['cap_control']} "
        f"ONsetting={default_capacitor_settings['capON']} "
        f"OFFsetting={default_capacitor_settings['capOFF']} "
        f"PTphase={default_capacitor_settings['PTphase']} "
        f"Delay={default_capacitor_settings['capONdelay']} "
        f"DelayOFF={default_capacitor_settings['capOFFdelay']} "
        f"DeadTime={default_capacitor_settings['capdeadtime']} enabled=True"
    )
    # Correct settings of those cap banks for which cap control object is available
    capacitors_commands_list = []
    capcontrol_present_df = orig_capacitors_df.loc[
        orig_capacitors_df["capcontrol_present"] == "capcontrol"
    ]
    for index, row in capcontrol_present_df.iterrows():
        # if it is already voltage controlled, modify PT ratio if new is different after re-computation
        if (row["capcontrol_type"].lower() == "voltage") and (
            round(row["ptratio"], 2) != round(row["old_ptratio"], 2)
        ):
            orig_string = " !original, corrected PTratio only"
            command_string = (
                f"Edit CapControl.{row['capcontrol_name']} PTRatio={row['PTratio']}"
                + orig_string
            )
            dss.run_command(command_string)
            # this does not change original settings, so should not cause convergence
            circuit_solve_and_check(raise_exception=True, **kwargs)
        # if capcontrol is present, change to voltage controlled and apply default settings.
        else:
            command_string = (
                f"Edit CapControl.{row['capcontrol_name']} PTRatio={row['PTratio']} "
                f"{default_capcontrol_command}"
            )
            dss.run_command(command_string)
            pass_flag = circuit_solve_and_check(raise_exception=False, **kwargs)
            if not pass_flag:
                command_string = edit_capacitor_settings_for_convergence(command_string)
                dss.run_command(command_string)
                circuit_solve_and_check(
                    raise_exception=True, **kwargs
                )  # raise exception if no convergence even after change
        capacitors_commands_list.append(command_string)

    # if there are capacitors without cap control, add a voltage-controlled cap control
    lines_df = get_all_line_info(compute_loading=False)
    lines_df["bus1_extract"] = lines_df["bus1"].str.split(".").str[0]
    no_capcontrol_present_df = orig_capacitors_df.loc[
        orig_capacitors_df["capcontrol_present"] != "capcontrol"
    ]
    for index, row in no_capcontrol_present_df.iterrows():
        capcontrol_name = "capcontrol" + row["capacitor_name"]
        # extract line name that has the same bus as capacitor
        line_name = lines_df.loc[lines_df["bus1_extract"] == row["bus1"]][
            "name"
        ].values[0]
        default_pt_ratio = (row["kv"] * 1000) / nominal_voltage
        command_string = (
            f"New CapControl.{capcontrol_name} element=Line.{line_name} "
            f"terminal={default_capacitor_settings['terminal']} capacitor={row['capacitor_name']} "
            f"PTRatio={default_pt_ratio} {default_capcontrol_command}"
        )
        dss.run_command(command_string)
        pass_flag = circuit_solve_and_check(raise_exception=False, **kwargs)
        if not pass_flag:
            command_string = edit_capacitor_settings_for_convergence(command_string)
            dss.run_command(command_string)
            circuit_solve_and_check(
                raise_exception=True, **kwargs
            )  # raise exception if no convergence even after change
        capacitors_commands_list.append(command_string)
    return capacitors_commands_list


# This function increases differences between cap ON and OFF voltages in user defined increments,
#  default 1 volt, until upper and lower bounds are reached.
def sweep_capacitor_settings(
    voltage_config=None,
    initial_capacitors_df=None,
    default_capacitor_settings=None,
    upper_limit=None,
    lower_limit=None,
    **kwargs,
):
    """This function sweeps through capacitor settings and returns dataframe of severity metrics for all the sweeps of capacitor controls with best settings

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
    capacitor_sweep_list = (
        []
    )  # this list will contain severity of each capacitor setting sweep
    # get severity index for original/initial capacitor settings (ie before the settings sweep)
    temp_dict = {
        "cap_on_setting": "original setting",
        "cap_off_setting": "original setting",
    }
    (
        bus_voltages_df,
        undervoltage_bus_list,
        overvoltage_bus_list,
        buses_with_violations,
    ) = get_bus_voltages(
        upper_limit=upper_limit,
        lower_limit=lower_limit,
        raise_exception=False,
        **kwargs,
    )
    pass_flag = circuit_solve_and_check(raise_exception=False, **kwargs)
    if (
        not pass_flag
    ):  # if there is convergence issue at this setting, go onto next setting and dont save
        temp_dict["converged"] = False
    else:
        temp_dict["converged"] = True
    severity_dict = compute_voltage_violation_severity(bus_voltages_df)
    temp_dict.update(severity_dict)
    capacitor_sweep_list.append(temp_dict)
    # start settings sweep
    cap_on_setting = default_capacitor_settings["capON"]
    cap_off_setting = default_capacitor_settings["capOFF"]
    cap_control_gap = voltage_config["capacitor_sweep_voltage_gap"]
    # Apply same capacitor ON and OFF settings to all capacitor controls and determine their impact
    # iterate over capacitor on and off settings while they are within voltage violation limits
    while (cap_on_setting > (lower_limit * voltage_config["nominal_voltage"])) or (
        cap_off_setting < (upper_limit * voltage_config["nominal_voltage"])
    ):
        temp_dict = {
            "cap_on_setting": cap_on_setting,
            "cap_off_setting": cap_off_setting,
        }
        for (
            index,
            row,
        ) in initial_capacitors_df.iterrows():  # apply settings to all capacitors
            dss.run_command(
                f"Edit CapControl.{row['capcontrol_name']} ONsetting={cap_on_setting} "
                f"OFFsetting={cap_off_setting}"
            )
            pass_flag = circuit_solve_and_check(raise_exception=False, **kwargs)
            if (
                not pass_flag
            ):  # if there is convergence issue at this setting, go onto next setting and dont save
                temp_dict["converged"] = False
                break
            else:
                temp_dict["converged"] = True
        (
            bus_voltages_df,
            undervoltage_bus_list,
            overvoltage_bus_list,
            buses_with_violations,
        ) = get_bus_voltages(
            upper_limit=upper_limit,
            lower_limit=lower_limit,
            raise_exception=False,
            **kwargs,
        )
        severity_dict = compute_voltage_violation_severity(bus_voltages_df)
        temp_dict.update(severity_dict)
        capacitor_sweep_list.append(temp_dict)
        if (cap_on_setting - cap_control_gap / 2) <= (
            lower_limit * voltage_config["nominal_voltage"]
        ):
            cap_on_setting = lower_limit * voltage_config["nominal_voltage"]
        else:
            cap_on_setting = cap_on_setting - cap_control_gap / 2
        if (cap_off_setting + cap_control_gap / 2) >= (
            upper_limit * voltage_config["nominal_voltage"]
        ):
            cap_off_setting = upper_limit * voltage_config["nominal_voltage"]
        else:
            cap_off_setting = cap_off_setting + cap_control_gap / 2
    capacitor_sweep_df = pd.DataFrame(capacitor_sweep_list)
    return capacitor_sweep_df


def choose_best_capacitor_sweep_setting(
    capacitor_sweep_df=None, initial_capacitors_df=None, **kwargs
):
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
    original_setting = capacitor_sweep_df.loc[
        capacitor_sweep_df["cap_on_setting"] == "original setting"
    ].iloc[0]
    deciding_field = "deviation_severity"
    min_severity_setting = capacitor_sweep_df.loc[
        capacitor_sweep_df[deciding_field].idxmin()
    ]
    setting_type = ""
    # if min severity is greater than or same as that of original setting,
    # then just assign original setting as min_severity_setting
    if min_severity_setting[deciding_field] >= original_setting[deciding_field]:
        capacitors_df = (
            initial_capacitors_df.copy()
        )  # here best_setting is initial settings
        logger.info(
            "Original capacitor settings are best. No need to change capacitor settings."
        )
        setting_type = "initial_setting"
    else:
        # apply same best setting to all capacitors
        capacitors_df = initial_capacitors_df.copy()
        capacitors_df["ONsetting"] = min_severity_setting["ONsetting"]
        capacitors_df["OFFsetting"] = min_severity_setting["OFFsetting"]
    properties_list = [
        "ONsetting",
        "OFFsetting",
    ]  # list of properties to be edited in commands
    capacitor_settings_commands_list = create_capcontrol_settings_commands(
        properties_list=properties_list,
        capacitors_df=capacitors_df,
        creation_action="Edit",
    )
    for command_string in capacitor_settings_commands_list:
        dss.run_command(command_string)
    circuit_solve_and_check(raise_exception=True, **kwargs)
    if (
        setting_type == "initial_setting"
    ):  # if initial settings are best, no need to return command with settings
        capacitor_settings_commands_list = []
    return capacitors_df, capacitor_settings_commands_list


def create_capcontrol_settings_commands(
    properties_list=None, capacitors_df=None, creation_action="New"
):
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


def compute_voltage_violation_severity(bus_voltages_df=None):
    """This function computes voltage violation severity metrics, based on bus voltages

    Parameters
    ----------
    bus_voltages_df

    Returns
    -------
    Dict
    """
    deviation_severity = (
        bus_voltages_df["Min voltage_deviation"].sum()
        + bus_voltages_df["Max voltage_deviation"].sum()
    )
    undervoltage_bus_list = list(
        bus_voltages_df.loc[bus_voltages_df["Undervoltage violation"] == True][
            "name"
        ].unique()
    )
    overvoltage_bus_list = list(
        bus_voltages_df.loc[bus_voltages_df["Overvoltage violation"] == True][
            "name"
        ].unique()
    )
    buses_with_violations = undervoltage_bus_list + overvoltage_bus_list
    objective_function = len(buses_with_violations) * deviation_severity
    severity_dict = {
        "deviation_severity": deviation_severity,
        "number_buses_with_violations": len(buses_with_violations),
        "objective_function": objective_function,
    }
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
    orig_string = " !original, corrected PTratio only"
    regcontrols_commands_list = []
    for index, row in orig_regcontrols_df.iterrows():
        if round(row["ptratio"], 2) != round(row["old_ptratio"], 2):
            command_string = (
                f"Edit RegControl.{row['name']} ptratio={row['ptratio']}"
                + default_regcontrol_command
                + orig_string
            )
            dss.run_command(command_string)
            circuit_solve_and_check(raise_exception=True, **kwargs)
            # this does not change original settings, so should not cause convergence issues
            regcontrols_commands_list.append(command_string)
    return regcontrols_commands_list


def sweep_regcontrol_settings(
    voltage_config=None,
    initial_regcontrols_df=None,
    upper_limit=None,
    lower_limit=None,
    exclude_sub_ltc=True,
    only_sub_ltc=False,
    **kwargs,
):
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
        initial_df = initial_regcontrols_df.loc[
            initial_regcontrols_df["at_substation_xfmr_flag"] == False
        ]
    if only_sub_ltc:
        initial_df = initial_regcontrols_df.loc[
            initial_regcontrols_df["at_substation_xfmr_flag"] == True
        ]
    regcontrol_sweep_list = []  # this list will contain severity of each setting sweep
    # get severity index for original/initial settings (ie before the settings sweep)
    temp_dict = {"setting": "original"}
    (
        bus_voltages_df,
        undervoltage_bus_list,
        overvoltage_bus_list,
        buses_with_violations,
    ) = get_bus_voltages(
        upper_limit=upper_limit,
        lower_limit=lower_limit,
        raise_exception=False,
        **kwargs,
    )
    pass_flag = circuit_solve_and_check(raise_exception=False, **kwargs)
    if (
        not pass_flag
    ):  # if there is convergence issue at this setting, go onto next setting and dont save
        temp_dict["converged"] = False
    else:
        temp_dict["converged"] = True
    severity_dict = compute_voltage_violation_severity(bus_voltages_df)
    temp_dict.update(severity_dict)
    regcontrol_sweep_list.append(temp_dict)
    # generate list of voltage setpoints
    vregs_list = []
    vreg = lower_limit * voltage_config["nominal_voltage"]
    while vreg < upper_limit * voltage_config["nominal_voltage"]:
        vregs_list.append(vreg)
        vreg += voltage_config["reg_v_delta"]
    # start settings sweep
    for vreg in vregs_list:
        for band in voltage_config["reg_control_bands"]:
            temp_dict = {"setting": f"{vreg}_{band}", "vreg": vreg, "band": band}
            # Apply same settings to all controls and determine their impact
            for index, row in initial_df.iterrows():
                logger.debug(f"{vreg}_{band}")
                dss.run_command(
                    f"Edit RegControl.{row['name']} vreg={vreg} band={band}"
                )
                pass_flag = circuit_solve_and_check(raise_exception=False, **kwargs)
                if (
                    not pass_flag
                ):  # if there is convergence issue at this setting, go onto next setting and dont save
                    temp_dict["converged"] = False
                    break
                else:
                    temp_dict["converged"] = True
                    try:
                        (
                            bus_voltages_df,
                            undervoltage_bus_list,
                            overvoltage_bus_list,
                            buses_with_violations,
                        ) = get_bus_voltages(
                            upper_limit=voltage_config["initial_upper_limit"],
                            lower_limit=voltage_config["initial_lower_limit"],
                            **kwargs,
                        )
                    except:  # catch convergence error
                        temp_dict["converged"] = False
                        break
                    severity_dict = compute_voltage_violation_severity(bus_voltages_df)
                    temp_dict.update(severity_dict)
                regcontrol_sweep_list.append(temp_dict)
    regcontrol_sweep_df = pd.DataFrame(regcontrol_sweep_list)
    return regcontrol_sweep_df


def choose_best_regcontrol_sweep_setting(
    regcontrol_sweep_df=None,
    initial_regcontrols_df=None,
    exclude_sub_ltc=True,
    only_sub_ltc=False,
    **kwargs,
):
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
        initial_df = initial_regcontrols_df.loc[
            initial_regcontrols_df["at_substation_xfmr_flag"] == False
        ]
    if only_sub_ltc:
        initial_df = initial_regcontrols_df.loc[
            initial_regcontrols_df["at_substation_xfmr_flag"] == True
        ]
    # start with assumption that original setting is best setting
    original_setting = regcontrol_sweep_df.loc[
        regcontrol_sweep_df["setting"] == "original"
    ].iloc[0]
    deciding_field = "deviation_severity"
    regcontrol_sweep_df = regcontrol_sweep_df.loc[
        regcontrol_sweep_df["converged"] == True
    ]
    min_severity_setting = regcontrol_sweep_df.loc[
        regcontrol_sweep_df[deciding_field].idxmin()
    ]
    # if min severity is greater than or same as that of original setting,
    # then just assign original setting as min_severity_setting
    if (min_severity_setting[deciding_field] >= original_setting[deciding_field]) and (
        original_setting["converged"]
    ):
        setting_type = "original"
        regcontrols_df = initial_df.copy()  # here best_setting is initial settings
    else:
        setting_type = "changed"
        regcontrols_df = initial_df.copy()
        regcontrols_df["vreg"] = min_severity_setting["vreg"]
        regcontrols_df["band"] = min_severity_setting["band"]
    properties_list = ["vreg", "band"]  # list of properties to be edited in commands
    regcontrol_settings_commands_list = create_regcontrol_settings_commands(
        properties_list=properties_list,
        regcontrols_df=regcontrols_df,
        creation_action="Edit",
    )
    for command_string in regcontrol_settings_commands_list:
        dss.run_command(command_string)
    circuit_solve_and_check(raise_exception=True, **kwargs)
    if (
        setting_type == "original"
    ):  # if original settings, no need to add to upgrades commands list
        regcontrol_settings_commands_list = []
        logger.info("Original Regulator control settings are the best.")
    return regcontrols_df, regcontrol_settings_commands_list


def create_regcontrol_settings_commands(
    properties_list=None, regcontrols_df=None, creation_action="New"
):
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


def add_new_regcontrol(
    xfmr_info_series=None,
    default_regcontrol_settings=None,
    nominal_voltage=None,
    **kwargs,
):
    """This function runs the dss command to add regulator control at the substation transformer.
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
    regcontrol_info_series["transformer"] = xfmr_info_series["name"]

    # use secondary voltage to define ptratio
    # If the winding is Wye, the line-to-neutral voltage is used to compute PTratio.
    # Else, the line-to-line voltage is used.
    sec_conn = convert_list_string_to_list(xfmr_info_series["conns"])[-1]
    if sec_conn.lower() == "wye":
        sec_voltage = xfmr_info_series["kVs"][-1] / (math.sqrt(3))
    else:
        sec_voltage = xfmr_info_series["kVs"][-1]
    regcontrol_info_series["ptratio"] = (sec_voltage * 1000) / nominal_voltage
    # use the primary bus to define name
    regcontrol_info_series["regcontrol_name"] = (
        "new_regcontrol_" + xfmr_info_series["bus_names_only"][0]
    )
    new_regcontrol_command = define_regcontrol_object(
        regcontrol_name=regcontrol_info_series["regcontrol_name"],
        action_type="New",
        regcontrol_info_series=regcontrol_info_series,
        general_property_list=regcontrol_info_series["properties_to_be_defined"],
    )
    dss.run_command(new_regcontrol_command)  # run command
    dss.run_command("CalcVoltageBases")
    pass_flag = circuit_solve_and_check(
        raise_exception=False, **kwargs
    )  # solve circuit
    command_list.append(new_regcontrol_command)
    return pass_flag, command_list


def define_regcontrol_object(
    regcontrol_name="",
    action_type="",
    regcontrol_info_series=None,
    general_property_list=None,
):
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
        command_string = (
            command_string + f" transformer={regcontrol_info_series['transformer']}"
        )
    # these properties contain regcontrol data (refer OpenDSS manual for more information on these parameters)
    if general_property_list is None:
        general_property_list = ["winding", "ptratio", "band", "vreg", "delay"]
    for property_name in general_property_list:
        temp_s = f" {property_name}={regcontrol_info_series[property_name]}"
        command_string = command_string + temp_s
    command_string = command_string + " enabled=True"
    return command_string


def sweep_and_choose_regcontrol_setting(
    voltage_config=None,
    initial_regcontrols_df=None,
    upper_limit=None,
    lower_limit=None,
    exclude_sub_ltc=True,
    only_sub_ltc=False,
    dss_file_list=None,
    dss_commands_list=None,
    **kwargs,
):
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
    regcontrol_sweep_df = sweep_regcontrol_settings(
        voltage_config=voltage_config,
        initial_regcontrols_df=initial_regcontrols_df,
        upper_limit=upper_limit,
        lower_limit=lower_limit,
        exclude_sub_ltc=exclude_sub_ltc,
        only_sub_ltc=only_sub_ltc,
        **kwargs,
    )
    # reload circuit after settings sweep
    reload_dss_circuit(
        dss_file_list=dss_file_list, commands_list=dss_commands_list, **kwargs
    )
    # choose best setting
    (
        regcontrols_df,
        regcontrol_settings_commands_list,
    ) = choose_best_regcontrol_sweep_setting(
        regcontrol_sweep_df=regcontrol_sweep_df,
        initial_regcontrols_df=initial_regcontrols_df,
        exclude_sub_ltc=exclude_sub_ltc,
        only_sub_ltc=only_sub_ltc,
        **kwargs,
    )
    return regcontrols_df, regcontrol_settings_commands_list


def add_substation_xfmr(chosen_option_row=None, data_row=None, **kwargs):

    command_string = define_xfmr_object(
        xfmr_name=data_row["name"],
        xfmr_info_series=chosen_option_row,
        action_type="New",
        buses_list=data_row["buses"],
    )
    dss.run_command(command_string)
    circuit_solve_and_check(
        raise_exception=True, **kwargs
    )  # solve circuit and CalcVoltageBases

    return command_string


def compare_objective_function():
    final_settings_commands = []
    return final_settings_commands


def add_new_xfmr(node=None, circuit_source=None, sub_xfmr_conn_type=None, **kwargs):
    """This function adds a new transformer by creating a new node
    (before or after a line, depending on whether it is a substation xfmr)

    Parameters
    ----------
    node
    circuit_source
    sub_xfmr_conn_type

    Returns
    -------

    """
    commands_list = []
    # Find line to which this node is connected to
    substation_node_flag = False
    node = node.lower()
    if node == circuit_source.lower():
        substation_node_flag = True
    all_lines_df = get_all_line_info()
    all_lines_df["bus1_name"] = (
        all_lines_df["bus1"].str.split(".", expand=True)[0].str.lower()
    )
    all_lines_df["bus2_name"] = (
        all_lines_df["bus2"].str.split(".", expand=True)[0].str.lower()
    )

    # For sub LTC, substation transformer will be placed at first bus of line (i.e. before the line)
    # make bus1 of line as regcontrol node
    if substation_node_flag:
        chosen_line_info = all_lines_df.loc[all_lines_df["bus1_name"] == node].iloc[0]
        new_node = chosen_line_info["bus2_name"] + "_regcontrol"
        xfmr_name = "New_xfmr_" + node
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
        kVA = int(
            kV_DT * chosen_line_info["normamps"] * 1.1
        )  # 10% over sized transformer
        new_xfmr_command_string = (
            f"New Transformer.{xfmr_name} phases={chosen_line_info['phases']} "
            f"windings=2 buses=({chosen_line_info['bus1_name']}, {new_node}) "
            f"conns=({sub_xfmr_conn_type},{sub_xfmr_conn_type}) kvs=({kV_DT},{kV_DT}) "
            f"kvas=({kVA},{kVA}) xhl=0.001 wdg=1 %r=0.001 wdg=2 %r=0.001 Maxtap=1.1 Mintap=0.9 "
            f"enabled=True"
        )
        property_list = [
            "phases",
            "windings",
            "buses",
            "conns",
            "kvs",
            "kvas",
            "xhl",
            "%Rs",
            "Maxtap",
            "Mintap",
        ]
        edit_line_command_string = (
            f"Edit Line.{chosen_line_info['name']} bus1={new_node}"
        )

    # If not subltc: For regulator, transformer will be placed after line. (i.e. new node will be created after bus2)
    else:
        # if there are more than one lines at a node, then iterate over them?
        chosen_line_info = all_lines_df.loc[all_lines_df["bus2_name"] == node].iloc[0]
        new_node = node + "_regcontrol"
        xfmr_name = "New_xfmr_" + node
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
        kVA = int(
            kV_DT * chosen_line_info["normamps"] * 1.1
        )  # 10% over sized transformer
        property_list = [
            "phases",
            "windings",
            "buses",
            "conns",
            "kvs",
            "kvas",
            "xhl",
            "%Rs",
            "Maxtap",
            "Mintap",
        ]
        new_xfmr_command_string = (
            f"New Transformer.{xfmr_name} phases={chosen_line_info['phases']} "
            f"windings=2 buses=({new_node},{chosen_line_info['bus2_name']}) "
            f"conns=(wye,wye) kvs=({kV_DT},{kV_DT}) kvas=({kVA},{kVA}) xhl=0.001 "
            f"wdg=1 %r=0.001 wdg=2 %r=0.001 Maxtap=1.1 Mintap=0.9 enabled=True"
        )
        edit_line_command_string = (
            f"Edit Line.{chosen_line_info['name']} bus2={new_node}"
        )
    dss.run_command(edit_line_command_string)
    dss.run_command(new_xfmr_command_string)
    # Update system admittance matrix
    dss.run_command("CalcVoltageBases")
    dss.Circuit.SetActiveBus(new_node)
    dss.Bus.X(x)
    dss.Bus.Y(y)

    commands_list.append(edit_line_command_string)
    commands_list.append(new_xfmr_command_string)
    commands_list.append(f"//{new_node.split('.')[0]},{x},{y}")
    circuit_solve_and_check(raise_exception=True, **kwargs)

    G, position_dict = generate_networkx_representation(circuit_source=circuit_source)
    return commands_list, G, position_dict


def disable_added_xfmr(transformer_name=None, **kwargs):
    """This function disables an added transformer in the feeder.
    since OpenDSS disables by transformer by opening the circuit instead of creating a short circuit,
    this function will remove the transformer by first disabling it, then it will connect the line properly to
    remove the islands.
    Substation will always have a xfmr by this point so only regulator transformers have to be removed

    Parameters
    ----------
    transformer_name

    Returns
    -------

    """
    # since OpenDSS disables by transformer by opening the circuit instead of creating a short circuit,
    # this function will remove the transformer by first disabling it, then it will connect the line properly to
    # remove the islands
    # Substation will always have a xfmr by this point so only regulator transformers have to be removed

    all_xfmr_df = get_all_transformer_info()
    all_xfmr_df["name"] = all_xfmr_df["name"].str.lower()

    chosen_xfmr = all_xfmr_df.loc[all_xfmr_df["name"] == transformer_name.lower()]
    dss.Transformers.First()
    while True:
        if dss.Transformers.Name().lower() == transformer_name.lower():
            prim_bus = dss.CktElement.BusNames()[0].split(".")[0]
            sec_bus = dss.CktElement.BusNames()[1]
            command_string = f"Edit Transformer.{transformer_name} enabled=False"
            dss.run_command(command_string)
            command_string = "Edit Transformer.{xfmr} buses=({b1},{b2})".format(
                xfmr=transformer_name,
                b1=dss.CktElement.BusNames()[0],
                b2=dss.CktElement.BusNames()[0],
            )
            dss.run_command(command_string)
            dss.Lines.First()
            while True:
                if dss.Lines.Bus2().split(".")[0].lower() == prim_bus.lower():
                    command_string = "Edit Line.{ln} bus2={b}".format(
                        ln=dss.Lines.Name(), b=sec_bus
                    )
                    dss.run_command(command_string)
                    # Update system admittance matrix
                    dss.run_command("CalcVoltageBases")
                    circuit_solve_and_check(raise_exception=True, **kwargs)
                    # generate_nx_representation()
                    break
                if not dss.Lines.Next() > 0:
                    break
            break
        if not dss.Transformers.Next() > 0:
            break
    return


def add_new_regcontrol_at_node(
    node, default_regcontrol_settings=None, nominal_voltage=None, **kwargs
):
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
    all_xfmr_df = get_all_transformer_info()
    regcontrols_df = get_regcontrol_info()
    temp_df = all_xfmr_df["bus_names_only"].apply(pd.Series)
    all_xfmr_df["primary_bus"] = temp_df[0].str.lower()
    all_xfmr_df["secondary_bus"] = temp_df[1].str.lower()
    chosen_xfmr = all_xfmr_df.loc[
        (all_xfmr_df["primary_bus"] == node) | (all_xfmr_df["secondary_bus"] == node)
    ].iloc[0]
    # do if regcontrol does not exist on transformer
    command_string = add_new_regcontrol(
        xfmr_info_series=chosen_xfmr,
        default_regcontrol_settings=default_regcontrol_settings,
        nominal_voltage=nominal_voltage,
        **kwargs,
    )
    dss.run_command(command_string)
    circuit_solve_and_check(raise_exception=True, **kwargs)
    dss.run_command("CalcVoltageBases")
    return [command_string]


def add_bus_nodes(G=None, bus_coordinates_df=None):
    buses_list = bus_coordinates_df.to_dict("records")
    for item in buses_list:
        G.add_node(item["bus_name"], pos=[item["x_coordinate"], item["y_coordinate"]])
    return G


def generate_networkx_representation(create_plot=False, circuit_source=None, **kwargs):
    bus_coordinates_df = get_bus_coordinates()
    G = nx.DiGraph()
    G = add_bus_nodes(G=G, bus_coordinates_df=bus_coordinates_df)

    # nx.from_pandas_edgelist(df, 'from', 'to')
    # G = generate_nodes(all_bus_names=all_bus_names, G=G)
    G = generate_edges(G=G)
    position_dict = nx.get_node_attributes(G, "pos")
    if create_plot:
        G, position_dict = correct_node_coords(
            G=G, position_dict=position_dict, circuit_source=circuit_source
        )
    return G, position_dict


def identify_common_upstream_nodes(G=None, clusters_dict=None, circuit_source=None):
    """In this function the very first common upstream node and all upstream nodes for all members of the
    cluster are stored

    Parameters
    ----------
    G
    clusters_dict
    circuit_source

    Returns
    -------

    """
    # notes: can include some type of optimization - such as look at multiple upstream nodes and place where sum of
    # downstream node voltage deviations is minimum as long as it doesn't overlap with other clusters
    # Currently it only identifies the common upstream nodes for all cluster nodes
    upstream_nodes_dict = {}
    temp_graph = G
    new_graph = temp_graph.to_undirected()
    for key, items in clusters_dict.items():
        paths_dict_cluster = {}
        common_nodes = []
        for buses in items:
            path = nx.shortest_path(new_graph, source=circuit_source, target=buses)
            paths_dict_cluster[buses] = path
        for common_bus in path:
            flag = 1
            for bus, paths in paths_dict_cluster.items():
                if common_bus not in paths:
                    flag = 0
                    break
            if flag == 1:
                common_nodes.append(common_bus)
        upstream_nodes_dict[key] = common_nodes
        # upstream_reg_node[key] = common_nodes[-1]
    return upstream_nodes_dict


def add_new_regulator_on_common_nodes(
    voltage_upper_limit=None,
    voltage_lower_limit=None,
    nominal_voltage=None,
    upstream_nodes_dict=None,
    circuit_source=None,
    default_regcontrol_settings=None,
    **kwargs,
):
    """In each cluster, place a new regulator control at each common upstream node, unless it is the source bus
    (since that already contains the LTC) or has a distribution transformer.

    Identify whether a transformer exists at this node or not. If yes simply add a new reg control -
    in fact calling the add_new_regctrl function will automatically check whether a reg control exists or not
    -  so only thing to be ensured is that a transformer should exist - for next time when this function is called
    a new set of clusters will be passed

    Parameters
    ----------
    voltage_upper_limit
    upstream_nodes_dict
    circuit_source

    Returns
    -------

    """
    commands_list = []
    deciding_field = "severity"
    # In terms of interpretation, false=0, true=1
    upstream_reg_node = {}
    all_xfmr_df = get_all_transformer_info()
    temp_df = all_xfmr_df["bus_names_only"].apply(pd.Series)
    all_xfmr_df["primary_bus"] = temp_df[0].str.lower()
    all_xfmr_df["secondary_bus"] = temp_df[1].str.lower()
    cluster_severity_dict = {}
    for cluster, common_nodes in upstream_nodes_dict.items():
        cluster_severity_dict[cluster] = {}
        vdev_cluster_nodes = {}
        for node in common_nodes:
            # Here do not add a new reg control to source bus as it already has a LTC
            if node.lower() == circuit_source.lower():
                continue
            # if transformer is already present at this node.
            if (len(all_xfmr_df[all_xfmr_df["primary_bus"] == node.lower()]) > 0) or (
                len(all_xfmr_df[all_xfmr_df["secondary_bus"] == node.lower()]) > 0
            ):
                # if transformer is already present at this node, skip. This is because:
                # we are skipping over LTC node already. So all other other nodes with
                # pre-existing xfmrs will be (primary to secondary DTs) which we do not want to control as regs are
                # primarily in line and not on individual distribution transformers
                continue
            cluster_severity_dict[cluster][node] = {}
            new_xfmr_commands_list, G, position_dict = add_new_xfmr(
                node=node, circuit_source=circuit_source, **kwargs
            )
            # These are just default settings and do not have to be written in the output file
            new_regcontrol_command = add_new_regcontrol_at_node(
                node,
                default_regcontrol_settings=default_regcontrol_settings,
                nominal_voltage=nominal_voltage,
                **kwargs,
            )
            (
                bus_voltages_df,
                undervoltage_bus_list,
                overvoltage_bus_list,
                buses_with_violations,
            ) = get_bus_voltages(
                upper_limit=voltage_upper_limit,
                lower_limit=voltage_lower_limit,
                raise_exception=False,
                **kwargs,
            )
            pass_flag = circuit_solve_and_check(raise_exception=False, **kwargs)
            severity_dict = compute_voltage_violation_severity(bus_voltages_df)
            cluster_severity_dict[cluster][node].update(severity_dict)
            cluster_severity_dict[cluster][node]["converged"] = pass_flag
            # vdev_cluster_nodes[node] = severity_indices[2]
            # Now disable the added regulator control and remove the added transformer
            command_string = f"Edit RegControl.{'New_regctrl_' + node} enabled=No"
            dss.run_command(command_string)
            disable_added_xfmr(transformer_name="New_xfmr_" + node, **kwargs)
        # For a given cluster identify the node which leads to minimum number of buses with violations
        min_severity = 1000000000
        min_node = ""
        for key, value in vdev_cluster_nodes.items():
            if value <= min_severity:
                min_severity = value
                min_node = key
        logger.debug("Min node is: %s", min_node)
        # If no nodes is found break the loop and go to next number of clusters:
        if min_node == "":
            continue
        upstream_reg_node[cluster] = min_node
        # Since this is an optimal location add the transformer here - this transformer will stay as long as
        # optimal_clusters does not increment. If this parameter changes then all devices at nodes mentioned
        # in previous optimal cluster number in cluster_optimal_reg_nodes should be disabled
        add_new_xfmr(min_node, **kwargs)
        command_string = f"Edit RegControl.{'New_regctrl_' + min_node} enabled=True"
        dss.run_command(command_string)
        circuit_solve_and_check(raise_exception=True, **kwargs)
        # Even here we do not need to write out the setting as the only setting to be written would
        # write_dss_file(command_string)
    # if no reg control nodes are found then continue
    if len(upstream_reg_node) == 0:
        no_reg_flag = 1
    return commands_list


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
                    if (
                        position_dict[pred_bus][0] != 0.0
                        and position_dict[pred_bus][1] != 0.0
                    ):
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
                        if (
                            position_dict[pred_bus][0] != 0.0
                            and position_dict[pred_bus][1] != 0.0
                        ):
                            new_x = position_dict[pred_bus][0]
                            new_y = position_dict[pred_bus][1]
                            G.node[key]["pos"] = [new_x, new_y]
                            break
    # Update position dict with new coordinates
    position_dict = nx.get_node_attributes(G, "pos")
    return G, position_dict


def get_full_distance_dict(upper_triang_paths_dict=None):
    """This function creates full distance dictionary as a square array from the upper triangular dictionary.

    Parameters
    ----------
    upper_triang_paths_dict

    Returns
    -------

    """
    square_dict = {}
    cluster_nodes_list = []
    temp_nodes_list = []
    max_length = 0
    for key, values in upper_triang_paths_dict.items():
        cluster_nodes_list.append(key)  # this is basically buses with violations
        if len(values) > max_length:
            max_length = len(values)  # this defines size of array
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

    # # Replace lower triangle zeros with upper triangle values
    # key_count = 0
    # ll = []
    # for key, values in upper_triang_paths_dict.items():
    #     for items_count in range(len(values)):
    #         square_dict[temp_nodes_list[items_count]][key_count] = values[items_count]
    #     key_count += 1
    #     temp_nodes_list.remove(key)
    # # from dict create a list of lists
    # for key, values in square_dict.items():
    #     ll.append(values)
    # # Create numpy array from list of lists
    # square_array = np.array(ll)
    return square_array


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
    all_lines_df = get_all_line_info()
    all_lines_df["bus1"] = (
        all_lines_df["bus1"].str.split(".", expand=True)[0].str.lower()
    )
    all_lines_df["bus2"] = (
        all_lines_df["bus2"].str.split(".", expand=True)[0].str.lower()
    )
    all_lines_df.apply(lambda x: x.length * length_conversion_to_metre[x.units])
    all_lines_df.apply(lambda x: x["length"] * length_conversion_to_metre[x["units"]])
    all_lines_df.apply(lambda x: print(x))
    # convert length to metres

    all_lines_df["units"]
    all_xfmrs_df = get_all_transformer_info()

    dss.Lines.First()
    while True:
        from_bus = dss.Lines.Bus1().split(".")[0].lower()
        to_bus = dss.Lines.Bus2().split(".")[0].lower()
        phases = dss.Lines.Phases()
        length = dss.Lines.Length()
        name = dss.Lines.Name()
        G.add_edge(from_bus, to_bus, phases=phases, length=length, name=name)
        if not dss.Lines.Next() > 0:
            break

    dss.Transformers.First()
    while True:
        bus_names = dss.CktElement.BusNames()
        from_bus = bus_names[0].split(".")[0].lower()
        to_bus = bus_names[1].split(".")[0].lower()
        phases = dss.CktElement.NumPhases()
        length = 0.0
        name = dss.Transformers.Name()
        G.add_edge(from_bus, to_bus, phases=phases, length=length, name=name)
        if not dss.Transformers.Next() > 0:
            break
    return G


def get_shortest_path(G=None, buses_with_violations=None):
    new_graph = G.to_undirected()
    precal_paths = []
    upper_triang_paths_dict = {}
    # Get upper triangular distance matrix - reduces computational time by half
    for bus1 in buses_with_violations:
        upper_triang_paths_dict[bus1] = []
        for bus_n in buses_with_violations:
            if bus_n == bus1:
                path_length = 0.0
            elif bus_n in precal_paths:
                continue
            else:
                path = nx.shortest_path(new_graph, source=bus1, target=bus_n)
                path_length = 0.0
                for nodes_count in range(len(path) - 1):
                    path_length += float(
                        new_graph[path[nodes_count + 1]][path[nodes_count]]["length"]
                    )
            upper_triang_paths_dict[bus1].append(round(path_length, 3))
        precal_paths.append(bus1)
    return upper_triang_paths_dict


def cluster_square_array(
    G=None,
    max_regs=2,
    square_array=None,
    circuit_source=None,
    buses_with_violations=None,
    voltage_upper_limit=None,
    voltage_lower_limit=None,
    create_plot=False,
    fig_folder=None,
    nominal_voltage=None,
    default_regcontrol_settings=None,
    **kwargs,
):
    # Clustering the distance matrix into clusters equal to optimal clusters
    if create_plot:
        plot_heatmap_distmatrix(square_array=square_array, fig_folder=fig_folder)
    for optimal_clusters in range(1, max_regs + 1, 1):
        breakpoint()
        no_reg_flag = 0
        clusters_dict = {}
        model = AgglomerativeClustering(
            n_clusters=optimal_clusters, affinity="euclidean", linkage="ward"
        )
        model.fit(square_array)
        labels_list = model.labels_
        # create a dictionary containing cluster_number as keys, and list of buses in that cluster as values
        for label in range(len(labels_list)):
            if labels_list[label] not in clusters_dict:
                clusters_dict[labels_list[label]] = [buses_with_violations[label]]
            else:
                clusters_dict[labels_list[label]].append(buses_with_violations[label])
        upstream_nodes_dict = identify_common_upstream_nodes(
            G=G, clusters_dict=clusters_dict, circuit_source=circuit_source
        )
        new_regcontrol_commands = add_new_regulator_on_common_nodes(
            voltage_upper_limit=voltage_upper_limit,
            voltage_lower_limit=voltage_lower_limit,
            nominal_voltage=nominal_voltage,
            upstream_nodes_dict=upstream_nodes_dict,
            circuit_source=circuit_source,
            default_regcontrol_settings=default_regcontrol_settings,
            **kwargs,
        )
        if no_reg_flag == 1:
            continue
        write_flag = 0
        # reg_controls_sweep(upper_limit=volta, lower_limit=lower_limit)
        # regcontrols_df, regcontrol_settings_commands_list = choose_best_regcontrol_sweep_setting(
        #     regcontrol_sweep_df=regcontrol_sweep_df, initial_regcontrols_df=orig_regcontrols_df, exclude_sub_ltc=True,
        #     only_sub_ltc=False)
        # write_flag = 1
        # # determine voltage violations after changes
        # bus_voltages_df, undervoltage_bus_list, overvoltage_bus_list, buses_with_violations = get_bus_voltages(
        #     upper_limit=voltage_upper_limit, lower_limit=voltage_lower_limit, **kwargs)
        #
        # cluster_optimal_reg_nodes[optimal_clusters] = [severity_indices[2],
        #                                                          [v_sp, reg_band], []]
        # # Store all optimal nodes for a given number of clusters
        # for key, vals in upstream_reg_node.items():
        #     cluster_optimal_reg_nodes[optimal_clusters][2].append(vals)
        #
        # logger.info("max_V_viol=%s, min_V_viol=%s, severity_indices=%s",
        #                  max_V_viol, min_V_viol, severity_indices)
        # disable_regctrl_current_cluster()
        # if (len(buses_with_violations)) == 0:
        #     logger.info("All nodal violations have been removed successfully.....quitting")
        #     break
    return new_regcontrol_commands


def plot_heatmap_distmatrix(square_array=None, fig_folder=None):
    plt.figure(figsize=(7, 7))
    ax = sns.heatmap(square_array, linewidth=0.5)
    plt.title("Distance matrix of nodes with violations")
    plt.savefig(os.path.join(fig_folder, "Nodal_violations_heatmap.pdf"))
