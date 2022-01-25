import time
from .common_functions import *

logger = logging.getLogger(__name__)


def correct_line_violations(
    line_loading_df=None,
    line_design_pu=None,
    line_upgrade_options=None,
    parallel_lines_limit=None,
    **kwargs,
):
    """This function determines line upgrades to correct line violations.
    It also updates the opendss model with upgrades.

    Parameters
    ----------
    line_loading_df
    line_design_pu
    line_upgrade_options
    parallel_lines_limit

    Returns
    -------

    """
    equipment_type = "Line"
    line_upgrades_df = pd.DataFrame()
    upgrades_dict = {}
    commands_list = []
    # This finds a line code which provides a specified safety margin to a line above its maximum observed loading.
    # If a line code is not found or if line code is too overrated, one or more parallel lines (num_par_lns-1) are added
    overloaded_loading_df = line_loading_df.loc[
        line_loading_df["status"] == "overloaded"
    ]
    overloaded_loading_df["required_design_amp"] = (
        overloaded_loading_df["max_amp_loading"] / line_design_pu
    )
    property_list = [
        "Switch",
        "kV",
        "phases",
        "line_placement",
    ]  # list of properties based on which upgrade is chosen
    line_upgrade_options.set_index(property_list, inplace=True)
    overloaded_loading_df.set_index(property_list, inplace=True)
    oversize_limit = 2  # limit to determine if chosen upgrade option is too oversized
    if len(overloaded_loading_df) > 0:  # if overloading exists
        # iterate over each overloaded line to find a solution
        for index, row in overloaded_loading_df.iterrows():
            logger.debug(row["name"])
            options = line_upgrade_options.loc[index]
            options = options.reset_index().sort_values("normamps")
            chosen_option = options.loc[
                options["normamps"] >= row["required_design_amp"]
            ].sort_values("normamps")
            # if one chosen option exists and is not very oversized (which is determined by acceptable oversize limit)
            # edit existing line and change line configuration/ampacity
            if (len(chosen_option) != 0) and (
                chosen_option["normamps"] <= oversize_limit * row["required_design_amp"]
            ).any():
                chosen_option = chosen_option.sort_values("amp_limit_per_phase")
                chosen_option = chosen_option.iloc[0]  # choose lowest available option
                new_config_type = chosen_option["line_definition_type"]
                # edit existing line
                if (new_config_type == "geometry") or (new_config_type == "linecode"):
                    command_string = f"Edit Line.{row['name']} {new_config_type}={chosen_option[new_config_type]}"
                    commands_list.append(command_string)
                # if line geometry and line code is not available
                else:
                    # TODO can add more parameters in command (like done for transformer)
                    command_string = (
                        f"Edit Line.{row['name']} normamps={chosen_option['normamps']}"
                    )
                    commands_list.append(command_string)
                # create dictionary of original equipment
                upgrades_dict[row["name"]] = {}
                upgrades_dict[row["name"]]["original_equipment"] = row.to_dict()
                upgrades_dict[row["name"]]["original_equipment"].update(
                    {
                        "Equipment_Type": equipment_type,
                        "Upgrade_Type": "upgrade",
                        # 'Parameter_Type': 'original_equipment',
                        "Action": "remove",
                    }
                )
                upgrades_dict[row["name"]]["original_equipment"].update(
                    chosen_option[["Switch", "phases", "line_placement"]].to_dict()
                )
                # create dictionary of new equipment
                upgrades_dict[row["name"]]["new_equipment"] = chosen_option.to_dict()
                upgrades_dict[row["name"]]["new_equipment"].update(
                    {
                        "Equipment_Type": equipment_type,
                        "Upgrade_Type": "upgrade",
                        # 'Parameter_Type': 'new_equipment',
                        "Action": "add",
                        "name": row["name"],
                    }
                )

                check_dss_run_command(
                    command_string
                )  # run command for upgraded equipment
                circuit_solve_and_check(raise_exception=True, **kwargs)

            # if higher upgrade is not available or chosen line upgrade rating is much higher than required,
            # dont oversize. Instead, place lines in parallel
            else:
                (
                    parallel_line_commands,
                    upgrades_dict_parallel,
                ) = identify_parallel_lines(
                    options=options, row=row, parallel_lines_limit=parallel_lines_limit
                )
                # run command for all parallel equipment added, that resolves overloading for one equipment
                for command_item in parallel_line_commands:
                    check_dss_run_command(command_item)
                    circuit_solve_and_check(raise_exception=True, **kwargs)
                commands_list = commands_list + parallel_line_commands
                upgrades_dict.update(upgrades_dict_parallel)
        index_names = ["original_equipment_name", "Parameter_Type"]
        line_upgrades_df = create_dataframe_from_nested_dict(
            user_dict=upgrades_dict, index_names=index_names
        )
        line_upgrades_df.rename(columns={"name": "final_equipment_name"}, inplace=True)
        line_upgrades_df = line_upgrades_df.set_index(
            [
                "Equipment_Type",
                "Upgrade_Type",
                "Parameter_Type",
                "Action",
                "final_equipment_name",
                "original_equipment_name",
            ]
        ).reset_index()
    else:  # if there is no overloading
        logger.info("This case has no line violations")
    circuit_solve_and_check(
        raise_exception=True, **kwargs
    )  # this is added as a final check for convergence
    return commands_list, line_upgrades_df


def identify_parallel_lines(options=None, row=None, parallel_lines_limit=None):
    """This function identifies parallel line solutions, when a direct upgrade solution is not available from catalogue

    Parameters
    ----------
    options
    row
    parallel_lines_limit

    Returns
    -------

    """
    commands_list = []
    upgrades_dict_parallel = {}
    # calculate number of parallel lines needed to carry remaining amperes (in addition to existing line)
    options["num_parallel_raw"] = (
        row["required_design_amp"] - row["normamps"]
    ) / options["normamps"]
    options["num_parallel"] = options["num_parallel_raw"].apply(np.ceil)
    options["choose_parallel_metric"] = (
        options["num_parallel"] - options["num_parallel_raw"]
    )
    # choose option that has the least value of this metric- since that represents the per unit oversizing
    chosen_option = pd.DataFrame(
        options.loc[options["choose_parallel_metric"].idxmin()]
    ).T
    num_parallel_lines = int(chosen_option["num_parallel"].values[0])
    if num_parallel_lines > parallel_lines_limit:
        raise Exception(f"Number of parallel lines is greater than limit!")
    new_config_type = chosen_option["line_definition_type"].values[0]
    for line_count in range(0, num_parallel_lines):
        curr_time = str(time.time())
        # this is added to line name to ensure it is unique
        time_stamp = curr_time.split(".")[0] + "_" + curr_time.split(".")[1]
        new_name = "upgrade_" + row["name"] + time_stamp
        chosen_option["name"] = new_name
        upgrades_dict_parallel[row["name"]] = {}
        upgrades_dict_parallel[row["name"]]["new_equipment"] = chosen_option.to_dict(
            "records"
        )[0]
        upgrades_dict_parallel[row["name"]]["new_equipment"]["length"] = row["length"]
        upgrades_dict_parallel[row["name"]]["new_equipment"].update(
            {
                "Equipment_Type": "Line",
                "Upgrade_Type": "new (parallel)",
                # 'Parameter_Type': 'new_equipment',
                "Action": "add",
            }
        )
        if (new_config_type == "geometry") or (new_config_type == "linecode"):
            s = (
                f"New Line.{new_name} bus1={row['bus1']} bus2={row['bus2']} length={row['length']} "
                f"units={row['units']} {new_config_type}={row[new_config_type]} "
                f"phases={chosen_option['phases'].values[0]} enabled=True"
            )
            commands_list.append(s)
        # if line geometry and line code is not available
        # TODO decide what other parameters need to be defined when linecode or geometry is not present
        else:
            s = (
                f"New Line.{row['name']} bus1={row['bus1']} bus2={row['bus2']} length={row['length']} "
                f"units={row['units']} phases={chosen_option['phases'].values[0]} "
                f"normamps={chosen_option['normamps'].values[0]} enabled=True"
            )
            commands_list.append(s)
    return commands_list, upgrades_dict_parallel


def define_xfmr_object(
    xfmr_name="", xfmr_info_series=None, action_type=None, buses_list=None
):
    """This function is used to create a command string to define an opendss transformer object

    Parameters
    ----------
    xfmr_name
    xfmr_info_series
    action_type
    buses_list

    Returns
    -------
    string
    """
    command_string = f"{action_type} Transformer.{xfmr_name}"
    if action_type == "New":
        s_temp = " buses=("
        for bus in buses_list:
            s_temp = s_temp + f"{bus} "
        s_temp = s_temp + ")"
        s_temp = s_temp.replace(" )", ")")
        command_string = (
            command_string + s_temp + f" phases={xfmr_info_series['phases']} "
            f"windings={xfmr_info_series['windings']}"
        )
    for wdg_count in range(xfmr_info_series["wdg"]):
        temp_s = (
            f" wdg={wdg_count+1} kVA={xfmr_info_series['kVAs'][wdg_count]} kV={xfmr_info_series['kVs'][wdg_count]} "
            f"conn={xfmr_info_series['conns'][wdg_count]} %r={xfmr_info_series['%Rs'][wdg_count]} "
            f"rneut={xfmr_info_series['Rneut']} xneut={xfmr_info_series['Xneut']}"
        )
        command_string = command_string + temp_s
    if xfmr_info_series["wdg"] > 1:
        # define reactances between windings
        temp_s = f" XLT={xfmr_info_series['XLT']} XHT={xfmr_info_series['XLT']} XHL={xfmr_info_series['XHL']}"
        command_string = command_string + temp_s
    if xfmr_info_series["phases"] > 1:
        # for higher phase order transformers, also define xscarray
        temp_s = f" Xscarray={xfmr_info_series['Xscarray']}"
        command_string = command_string + temp_s
    # these properties contain general transformer rating data
    # (refer OpenDSS manual for more information on these parameters)
    general_property_list = [
        "LeadLag",
        "Core",
        "thermal",
        "n",
        "m",
        "flrise",
        "hsrise",
        "%noloadloss",
        "%loadloss",
        "normhkVA",
        "emerghkVA",
        "NumTaps",
        "%imag",
        "ppm_antifloat",
        "XRConst",
        "faultrate",
    ]
    for property_name in general_property_list:
        temp_s = f" {property_name}={xfmr_info_series[property_name]}"
        command_string = command_string + temp_s
    command_string = command_string + " enable=True"
    return command_string


def correct_xfmr_violations(
    xfmr_loading_df=None,
    xfmr_design_pu=None,
    xfmr_upgrade_options=None,
    PARALLEL_XFMRS_LIMIT=None,
    **kwargs,
):
    """This function determines transformer upgrades to correct transformer violations.
    It also updates the opendss model with upgrades.

    Parameters
    ----------
    xfmr_loading_df
    xfmr_design_pu
    xfmr_upgrade_options
    PARALLEL_XFMRS_LIMIT

    Returns
    -------

    """
    equipment_type = "Transformer"
    xfmr_upgrades_df = pd.DataFrame()
    upgrades_dict = {}
    commands_list = []
    # This finds a line code which provides a specified safety margin to a line above its maximum observed loading.
    # If a line code is not found or if line code is too overrated, one or more parallel lines (num_par_lns-1) are added
    overloaded_loading_df = xfmr_loading_df.loc[
        xfmr_loading_df["status"] == "overloaded"
    ]
    overloaded_loading_df["required_design_amp"] = (
        overloaded_loading_df["max_amp_loading"] / xfmr_design_pu
    )
    # list of properties based on which upgrade is chosen
    deciding_property_list = [
        "phases",
        "wdg",
        "conn",
        "conns",
        "kV",
        "kVs",
        "LeadLag",
        "basefreq",
    ]
    xfmr_upgrade_options.set_index(deciding_property_list, inplace=True)
    overloaded_loading_df.set_index(deciding_property_list, inplace=True)
    oversize_limit = 2  # limit to determine if chosen upgrade option is too oversized
    if len(overloaded_loading_df) > 0:  # if overloading exists
        # iterate over each overloaded line to find a solution
        for index, row in overloaded_loading_df.iterrows():
            options = xfmr_upgrade_options.loc[index]
            options = options.reset_index().sort_values("amp_limit_per_phase")
            chosen_option = options.loc[
                options["amp_limit_per_phase"] >= row["required_design_amp"]
            ].sort_values("amp_limit_per_phase")
            # if one chosen option exists and is not very oversized (which is determined by acceptable oversize limit)
            # edit existing object
            if (len(chosen_option) != 0) and (
                chosen_option["amp_limit_per_phase"]
                <= oversize_limit * row["required_design_amp"]
            ).any():
                chosen_option = chosen_option.sort_values("amp_limit_per_phase")
                chosen_option = chosen_option.iloc[0]  # choose lowest available option
                chosen_option["conns"] = convert_list_string_to_list(
                    chosen_option["conns"]
                )
                chosen_option["kVs"] = convert_list_string_to_list(chosen_option["kVs"])
                # edit existing transformer
                command_string = define_xfmr_object(
                    xfmr_name=row["name"],
                    xfmr_info_series=chosen_option,
                    action_type="Edit",
                )
                commands_list.append(command_string)
                # create dictionary of original equipment
                upgrades_dict[row["name"]] = {}
                upgrades_dict[row["name"]]["original_equipment"] = row.to_dict()
                upgrades_dict[row["name"]]["original_equipment"].update(
                    {
                        "Equipment_Type": equipment_type,
                        "Upgrade_Type": "upgrade",
                        # 'Parameter_Type': 'original_equipment',
                        "Action": "remove",
                    }
                )
                upgrades_dict[row["name"]]["original_equipment"].update(
                    chosen_option[deciding_property_list].to_dict()
                )
                # create dictionary of new equipment
                upgrades_dict[row["name"]]["new_equipment"] = chosen_option.to_dict()
                upgrades_dict[row["name"]]["new_equipment"].update(
                    {
                        "Equipment_Type": equipment_type,
                        "Upgrade_Type": "upgrade",
                        # 'Parameter_Type': 'new_equipment',
                        "Action": "add",
                        "name": row["name"],
                    }
                )
                check_dss_run_command(
                    command_string
                )  # run command for upgraded equipment
                circuit_solve_and_check(raise_exception=True, **kwargs)
            # if higher upgrade is not available or chosen upgrade rating is much higher than required,
            # dont oversize. Instead, place equipment in parallel
            else:
                (
                    parallel_xfmr_commands,
                    upgrades_dict_parallel,
                ) = identify_parallel_xfmrs(
                    options=options, row=row, PARALLEL_XFMRS_LIMIT=PARALLEL_XFMRS_LIMIT
                )
                # run command for all parallel equipment added, that resolves overloading for one equipment
                for command_item in parallel_xfmr_commands:
                    check_dss_run_command(command_item)
                    circuit_solve_and_check(raise_exception=True, **kwargs)
                commands_list = commands_list + parallel_xfmr_commands
                upgrades_dict.update(upgrades_dict_parallel)
        index_names = ["original_equipment_name", "Parameter_Type"]
        xfmr_upgrades_df = create_dataframe_from_nested_dict(
            user_dict=upgrades_dict, index_names=index_names
        )
        xfmr_upgrades_df.rename(columns={"name": "final_equipment_name"}, inplace=True)
        xfmr_upgrades_df = xfmr_upgrades_df.set_index(
            [
                "Equipment_Type",
                "Upgrade_Type",
                "Parameter_Type",
                "Action",
                "final_equipment_name",
                "original_equipment_name",
            ]
        ).reset_index()

    else:  # if there is no overloading
        logger.info("This case has no transformer violations")
    xfmr_upgrade_options.reset_index(inplace=True)
    circuit_solve_and_check(
        raise_exception=True, **kwargs
    )  # this is added as a final check for convergence
    return commands_list, xfmr_upgrades_df


def identify_parallel_xfmrs(options=None, row=None, PARALLEL_XFMRS_LIMIT=None):
    """This function identifies parallel transformer solutions, when a direct upgrade solution is not available from catalogue

    Parameters
    ----------
    options
    row
    PARALLEL_XFMRS_LIMIT

    Returns
    -------

    """
    equipment_type = "Transformer"
    commands_list = []
    upgrades_dict_parallel = {}
    # calculate number of parallel equipment needed to carry remaining amperes (in addition to existing equipment)
    options["num_parallel_raw"] = (
        row["required_design_amp"] - row["amp_limit_per_phase"]
    ) / options["amp_limit_per_phase"]
    options["num_parallel"] = options["num_parallel_raw"].apply(np.ceil)
    options["choose_parallel_metric"] = (
        options["num_parallel"] - options["num_parallel_raw"]
    )
    options = options.loc[options["num_parallel"] <= PARALLEL_XFMRS_LIMIT]
    if len(options) == 0:
        raise Exception(f"Number of parallel transformers is greater than limit!")
    # choose option that has the least value of this metric- since that represents the per unit oversizing
    chosen_option = options.loc[options["choose_parallel_metric"].idxmin()]
    num_parallel_xfmrs = int(chosen_option["num_parallel"])
    chosen_option["conns"] = convert_list_string_to_list(chosen_option["conns"])
    chosen_option["kVs"] = convert_list_string_to_list(chosen_option["kVs"])
    for xfmr_count in range(0, num_parallel_xfmrs):
        curr_time = str(time.time())
        # the timestamp is added to line name to ensure it is unique
        time_stamp = curr_time.split(".")[0] + "_" + curr_time.split(".")[1]
        new_name = "upgrade_" + row["name"] + time_stamp
        chosen_option["name"] = new_name
        upgrades_dict_parallel[row["name"]] = {}
        upgrades_dict_parallel[row["name"]]["new_equipment"] = chosen_option.to_dict()
        upgrades_dict_parallel[row["name"]]["new_equipment"].update(
            {
                "Equipment_Type": equipment_type,
                "Upgrade_Type": "new (parallel)",
                # 'Parameter_Type': 'new_equipment',
                "Action": "add",
            }
        )

        command_string = define_xfmr_object(
            xfmr_name=new_name,
            xfmr_info_series=chosen_option,
            action_type="New",
            buses_list=row["buses"],
        )
        commands_list.append(command_string)
    return commands_list, upgrades_dict_parallel