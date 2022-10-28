import ast
import time
from .common_functions import *

from jade.utils.timing_utils import track_timing

from disco import timer_stats_collector
from disco.exceptions import ExceededParallelLinesLimit, ExceededParallelTransformersLimit, UpgradesExternalCatalogMissingObjectDefinition
from disco.models.upgrade_cost_analysis_generic_input_model import _extract_specific_model_properties_, TransformerCatalogModel, LineCatalogModel
from disco.models.upgrade_cost_analysis_generic_output_model import TransformerUpgradesTechnicalResultModel, LineUpgradesTechnicalResultModel

logger = logging.getLogger(__name__)

@track_timing(timer_stats_collector)
def correct_line_violations(line_loading_df, line_design_pu, line_upgrade_options, parallel_lines_limit, **kwargs,):
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
    upgrades_dict_parallel = []
    commands_list = []
    # This finds a line code which provides a specified safety margin to a line above its maximum observed loading.
    # If a line code is not found or if line code is too overrated, one or more parallel lines (num_par_lns-1) are added
    overloaded_loading_df = line_loading_df.loc[line_loading_df["status"] == "overloaded"].copy()
    overloaded_loading_df["required_design_amp"] = overloaded_loading_df["max_amp_loading"] / line_design_pu
    deciding_property_list =  _extract_specific_model_properties_(model_name=LineCatalogModel, field_type_key="deciding_property", field_type_value=True)
    line_upgrade_options["kV"] = line_upgrade_options["kV"].round(2)
    overloaded_loading_df["kV"] = overloaded_loading_df["kV"].round(2)
    line_upgrade_options.set_index(deciding_property_list, inplace=True)
    line_upgrade_options = line_upgrade_options.sort_index(level=0)
    overloaded_loading_df.set_index(deciding_property_list, inplace=True)  
    oversize_limit = 2  # limit to determine if chosen upgrade option is too oversized
    extreme_loading_threshold = 2.25  # from observations, if equipment loading is greater than this factor, it is considered extremely overloaded
    # in such extremely loaded cases, the equipment is oversized much more, to avoid iterations in upgrades    
    if len(overloaded_loading_df) > 0:  # if overloading exists
        # iterate over each overloaded line to find a solution
        for index, row in overloaded_loading_df.iterrows():
            logger.debug(row["name"])
            try:
                options = line_upgrade_options.loc[index]
            except KeyError:
                raise UpgradesExternalCatalogMissingObjectDefinition(f"Line of type {dict(zip(deciding_property_list, list(index)))} not found in catalog."
                                                                     f" Please ensure catalog is complete.")
            if isinstance(options, pd.Series):  # if only one option is present, it is returned as series
                options = pd.DataFrame([options])  # convert to required DataFrame format
                options = options.rename_axis(deciding_property_list)  # assign names to the index
            options = options.reset_index().sort_values("normamps")
            if row["max_per_unit_loading"] > extreme_loading_threshold:  # i.e. equipment is very overloaded, then oversize more to avoid multiple upgrade iterations
                row["required_design_amp"] = row["required_design_amp"] * (row["max_per_unit_loading"] * 0.5)
            chosen_option = options.loc[options["normamps"] >= row["required_design_amp"]].sort_values("normamps")
            # TODO: TOGGLE FLAG - EXPLORE IF WE CAN HAVE OPTIONS FOR: PARALLEL, REPLACE,
            # if one chosen option exists and is not very oversized (which is determined by acceptable oversize limit)
            # edit existing line and change line configuration/ampacity
            if (len(chosen_option) != 0) and \
                    (chosen_option["normamps"] <= oversize_limit * row["required_design_amp"]).any():
                chosen_option = chosen_option.sort_values("normamps")
                chosen_option = chosen_option.iloc[0]  # choose lowest available option
                new_config_type = chosen_option["line_definition_type"]     
                new_config_name = chosen_option[new_config_type].lower()
                temp_commands_list = []
                # edit existing line
                if (new_config_type == "geometry") or (new_config_type == "linecode"):
                    external_upgrades_technical_catalog = kwargs.get("external_upgrades_technical_catalog", None)
                    command_string = ensure_line_config_exists(chosen_option, new_config_type, external_upgrades_technical_catalog)
                    if command_string is not None:  # if new line config definition had to be added
                        temp_commands_list.append(command_string)                                                    
                    command_string = f"Edit Line.{row['name']} {new_config_type}={new_config_name} normamps={chosen_option['normamps']}"
                    temp_commands_list.append(command_string)
                # if line geometry and line code is not available
                else:
                    command_string = define_line_object(line_name=row['name'], chosen_option=chosen_option.copy(deep=True), action_type="Edit")
                    temp_commands_list.append(command_string)
                # create dictionary of original equipment
                upgrades_dict[row["name"]] = {}
                upgrades_dict[row["name"]]["original_equipment"] = row.to_dict()
                upgrades_dict[row["name"]]["original_equipment"].update({"equipment_type": equipment_type,
                                                                         "upgrade_type": "upgrade",
                                                                         # "parameter_type": "original_equipment",
                                                                         "action": "remove"})
                upgrades_dict[row["name"]]["original_equipment"] .update(chosen_option[["Switch", "phases",
                                                                                        "line_placement"]].to_dict())
                # create dictionary of new equipment
                upgrades_dict[row["name"]]["new_equipment"] = chosen_option.to_dict()
                # line length units for new_equipment should be same as that of original equipment
                upgrades_dict[row["name"]]["new_equipment"]["units"] = upgrades_dict[row["name"]]["original_equipment"]["units"]  
                upgrades_dict[row["name"]]["new_equipment"].update({"equipment_type": equipment_type,
                                                                    "upgrade_type": "upgrade",
                                                                    # "parameter_type": "new_equipment",
                                                                    "action": "add", "name": row["name"]})
                # run command for upgraded equipment, that resolves overloading for one equipment
                for command_item in temp_commands_list:
                    check_dss_run_command(command_item)
                    circuit_solve_and_check(raise_exception=True, **kwargs)
                commands_list = commands_list + temp_commands_list
            # if higher upgrade is not available or chosen line upgrade rating is much higher than required,
            # dont oversize. Instead, place lines in parallelma
            else:
                external_upgrades_technical_catalog = kwargs.get("external_upgrades_technical_catalog", None)
                parallel_line_commands, temp_upgrades_dict_parallel = identify_parallel_lines(options=options, object_row=row,
                                                                                         parallel_lines_limit=parallel_lines_limit, 
                                                                                         external_upgrades_technical_catalog=external_upgrades_technical_catalog)
                # run command for all parallel equipment added, that resolves overloading for one equipment
                for command_item in parallel_line_commands:
                    check_dss_run_command(command_item)
                    check_dss_run_command('CalcVoltageBases')
                    circuit_solve_and_check(raise_exception=True, **kwargs)
                commands_list = commands_list + parallel_line_commands
                upgrades_dict_parallel = upgrades_dict_parallel + temp_upgrades_dict_parallel  # parallel upgrades is stored in a list (since it has same original_equipment name)
        index_names = ["original_equipment_name", "parameter_type"]
        if upgrades_dict:  # if dictionary is not empty
            line_upgrades_df = create_dataframe_from_nested_dict(user_dict=upgrades_dict, index_names=index_names)
        line_upgrades_df = pd.concat([line_upgrades_df, pd.DataFrame(upgrades_dict_parallel)])
        line_upgrades_df.rename(columns={"name": "final_equipment_name"}, inplace=True)
        line_upgrades_df = line_upgrades_df.set_index(
            ["equipment_type", "upgrade_type", "parameter_type", "action", "final_equipment_name",
             "original_equipment_name"]).reset_index()
    else:  # if there is no overloading
        logger.info("This case has no line violations")
    circuit_solve_and_check(raise_exception=True, **kwargs)  # this is added as a final check for convergence
    output_fields =  list(LineUpgradesTechnicalResultModel.schema(True).get("properties").keys())  # get fields with alias
    line_upgrades_df = line_upgrades_df[output_fields]
    return commands_list, line_upgrades_df


@track_timing(timer_stats_collector)
def identify_parallel_lines(options, object_row, parallel_lines_limit, **kwargs):
    """This function identifies parallel line solutions, when a direct upgrade solution is not available from catalogue

    Parameters
    ----------
    options
    row
    parallel_lines_limit

    Returns
    -------

    """
    output_fields = list(LineUpgradesTechnicalResultModel.schema(True).get("properties").keys())
    temp_output_fields = set(output_fields) - {"final_equipment_name"}
    commands_list = []
    temp_dict = {}
    # calculate number of parallel lines needed to carry remaining amperes (in addition to existing line)
    options["num_parallel_raw"] = (object_row["required_design_amp"] - object_row["normamps"]) / options["normamps"]
    options["num_parallel"] = options["num_parallel_raw"].apply(np.ceil)
    options["choose_parallel_metric"] = options["num_parallel"] - options["num_parallel_raw"]
    # choose option that has the least value of this metric- since that represents the per unit oversizing
    chosen_option = pd.DataFrame(options.loc[options["choose_parallel_metric"].idxmin()]).T
    chosen_option = chosen_option.sort_values("normamps")
    chosen_option = chosen_option.iloc[0]  # choose lowest available option
    num_parallel_lines = int(chosen_option["num_parallel"])
    if num_parallel_lines > parallel_lines_limit:
        raise ExceededParallelLinesLimit(f"Number of parallel lines required is {num_parallel_lines}, which exceeds limit of {parallel_lines_limit}."
                                          f" Increase parameter parallel_lines_limit in input config or ensure higher sized equipment is present in technical catalog.")
    new_config_type = chosen_option["line_definition_type"]
    external_upgrades_technical_catalog = kwargs.get("external_upgrades_technical_catalog", None)
    upgrades_dict_parallel = []
    for line_count in range(0, num_parallel_lines):
        curr_time = str(time.time())
        # this is added to line name to ensure it is unique
        time_stamp = curr_time.split(".")[0] + "_" + curr_time.split(".")[1]
        new_name = "upgrade_" + object_row["name"] + time_stamp
        chosen_option["name"] = new_name
        temp_dict = {}
        temp_dict.update(chosen_option.to_dict())
        temp_dict["length"] = object_row["length"]
        temp_dict["units"] = object_row["units"]
        temp_dict.update({"equipment_type": "Line",
                          "original_equipment_name": object_row["name"],
                          "upgrade_type": "new_parallel",
                          "parameter_type": "new_equipment",
                          "action": "add"})
        # # if too much info, can remove this metrics from output. For now, these are included.
        # remove_fields = ['num_parallel_raw', 'num_parallel', 'choose_parallel_metric']
        # for x in remove_fields:
        #     temp_dict.pop(x)
        if (new_config_type == "geometry") or (new_config_type == "linecode"):
            config_command_string = ensure_line_config_exists(chosen_option, new_config_type, external_upgrades_technical_catalog)
            if config_command_string is not None:  # if new line config definition had to be added
                commands_list.append(config_command_string)          
            command_string = f"New Line.{new_name} bus1={object_row['bus1']} bus2={object_row['bus2']} length={object_row['length']} " \
                    f"units={object_row['units']} {new_config_type}={chosen_option[new_config_type]} " \
                    f"phases={chosen_option['phases']} normamps={chosen_option['normamps']} enabled=Yes"
            commands_list.append(command_string)
        # if line geometry and line code is not available, add impedance properties directly
        else:
            command_string = define_line_object(line_name=new_name, chosen_option=chosen_option.copy(deep=True), action_type="New", 
                               bus1=object_row['bus1'], bus2=object_row['bus2'], length=object_row['length'],
                               original_units=object_row['units'])
            commands_list.append(command_string)
        temp_dict.pop("choose_parallel_metric")
        temp_dict.pop("num_parallel_raw")
        missing_fields = list(set(temp_output_fields).difference(temp_dict.keys()))  # find missing fields in temp_dict
        temp_dict.update(object_row[missing_fields].to_dict())
        upgrades_dict_parallel.append(temp_dict)
    return commands_list, upgrades_dict_parallel


def define_line_object(line_name, chosen_option, action_type, **kwargs):
    """This function is used to create a command string to define an opendss line object
    """
    command_string = f"{action_type} Line.{line_name} normamps={chosen_option['normamps']} emergamps={chosen_option['emergamps']}"
    if action_type == "New":
        bus1 = kwargs.get("bus1", None)
        bus2 = kwargs.get("bus2", None)
        length = kwargs.get("length", None)
        original_units = kwargs.get("original_units", None)
        if bus1 is None or bus2 is None or length is None or original_units is None:
            raise ValueError(f"Bus and length information is needed when defining a new line object.")
        if original_units != chosen_option["units"]:  # if units are different
            # keep units of chosen option because impedances are defined in this unit
            units = chosen_option["units"]  
            # change length to be reflected in the new units
            length = convert_length_units(length, unit_in=original_units, unit_out=chosen_option["units"])
        else:
            units = original_units
            
        command_string = command_string + f" bus1={bus1} bus2={bus2} Length={length} " \
                         f"Units={units} phases={chosen_option['phases']}"
    # Impedances may be specified by symmetrical component values or by matrix values
    # (refer OpenDSS manual for more information on these parameters)
    matrix_impedance_prop = _extract_specific_model_properties_(model_name=LineCatalogModel, field_type_key="matrix_impedance_property", field_type_value=True)
    symm_impedance_prop = _extract_specific_model_properties_(model_name=LineCatalogModel, field_type_key="symmetrical_impedance_property", field_type_value=True)
    
    method = "matrix_impedance"  # first try matrix impedance, else add symm component
    matrix_fields = [s for s in matrix_impedance_prop if 'matrix' in s]
    for field in matrix_fields:
        chosen_option[field] = str(chosen_option[field]).replace("'","")
        chosen_option[field] = chosen_option[field].replace("[","(")
        chosen_option[field] = chosen_option[field].replace("]",")")
    for property_name in matrix_impedance_prop:
        if chosen_option[property_name]:
            temp_s = f" {property_name}={chosen_option[property_name]}"
            command_string = command_string + temp_s
        else:
            method = "symmetrical_impedance"
            break       
    if method == "symmetrical_impedance":
        for property_name in symm_impedance_prop:
            if chosen_option[property_name]:
                temp_s = f" {property_name}={chosen_option[property_name]}"
                command_string = command_string + temp_s
            else:
                break
    command_string = command_string + " enabled=Yes"
    return command_string


def define_xfmr_object(xfmr_name, xfmr_info_series, action_type, buses_list=None):
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
    if isinstance(xfmr_info_series["conns"], str):
        xfmr_info_series["conns"] = ast.literal_eval(xfmr_info_series["conns"])
    if isinstance(xfmr_info_series["kVs"], str):
        xfmr_info_series["kVs"] = ast.literal_eval(xfmr_info_series["kVs"])
    if isinstance(xfmr_info_series["%Rs"], str):
        xfmr_info_series["%Rs"] = ast.literal_eval(xfmr_info_series["%Rs"])
    if isinstance(xfmr_info_series["kVAs"], str):
        xfmr_info_series["kVAs"] = ast.literal_eval(xfmr_info_series["kVAs"])
    command_string = f"{action_type} Transformer.{xfmr_name}"
    if action_type == "New":
        if buses_list is None:
            raise Exception("Buses list has to be passed if defining new transformer object.")
        s_temp = " buses=("
        for bus in buses_list:
            s_temp = s_temp + f"{bus} "
        s_temp = s_temp + ")"
        s_temp = s_temp.replace(" )", ")")
        command_string = command_string + s_temp + f" phases={xfmr_info_series['phases']} " \
                                                   f"windings={xfmr_info_series['windings']}"
    for wdg_count in range(xfmr_info_series["wdg"]):
        temp_s = f" wdg={wdg_count+1} kVA={xfmr_info_series['kVAs'][wdg_count]} kV={xfmr_info_series['kVs'][wdg_count]} " \
                 f"conn={xfmr_info_series['conns'][wdg_count]} %r={xfmr_info_series['%Rs'][wdg_count]} " \
                 f"rneut={xfmr_info_series['Rneut']} xneut={xfmr_info_series['Xneut']}"
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
    general_property_list =  _extract_specific_model_properties_(model_name=TransformerCatalogModel, field_type_key="write_property", field_type_value=True)
    for property_name in general_property_list:
        temp_s = f" {property_name}={xfmr_info_series[property_name]}"
        command_string = command_string + temp_s
    command_string = command_string + " enabled=Yes"
    return command_string


@track_timing(timer_stats_collector)
def correct_xfmr_violations(xfmr_loading_df, xfmr_design_pu, xfmr_upgrade_options,
                            parallel_transformers_limit, **kwargs):
    """This function determines transformer upgrades to correct transformer violations.
    It also updates the opendss model with upgrades.

    Parameters
    ----------
    xfmr_loading_df
    xfmr_design_pu
    xfmr_upgrade_options
    parallel_transformers_limit

    Returns
    -------

    """
    equipment_type = "Transformer"
    xfmr_upgrades_df = pd.DataFrame()
    upgrades_dict = {}
    upgrades_dict_parallel = []
    commands_list = []
    # This finds a line code which provides a specified safety margin to a line above its maximum observed loading.
    # If a line code is not found or if line code is too overrated, one or more parallel lines (num_par_lns-1) are added
    overloaded_loading_df = xfmr_loading_df.loc[xfmr_loading_df["status"] == "overloaded"].copy()
    overloaded_loading_df["required_design_amp"] = overloaded_loading_df["max_amp_loading"] / xfmr_design_pu
    # list of properties based on which upgrade is chosen
    deciding_property_list =  _extract_specific_model_properties_(model_name=TransformerCatalogModel, field_type_key="deciding_property", field_type_value=True)
    # round to same precision for upgrade options, and overloaded equipment
    xfmr_upgrade_options["kV"] = xfmr_upgrade_options["kV"].round(2)
    overloaded_loading_df["kV"] = overloaded_loading_df["kV"].round(2)
    xfmr_upgrade_options["kVs"] = xfmr_upgrade_options["kVs"].apply(lambda x: [round(a, 2) for a in x])
    overloaded_loading_df["kVs"] = overloaded_loading_df["kVs"].apply(lambda x: [round(a, 2) for a in x])
    # convert lists to string type (so they can be set as dataframe index later)
    xfmr_upgrade_options[['conns', 'kVs']] = xfmr_upgrade_options[['conns', 'kVs']].astype(str)
    overloaded_loading_df[['conns', 'kVs']] = overloaded_loading_df[['conns', 'kVs']].astype(str)
    xfmr_upgrade_options.set_index(deciding_property_list, inplace=True)
    xfmr_upgrade_options = xfmr_upgrade_options.sort_index(level=0)
    overloaded_loading_df.set_index(deciding_property_list, inplace=True)
    equipment_oversize_limit = 2  # limit to determine if chosen upgrade option is too oversized
    extreme_loading_threshold = 2.25  # if equipment loading is greater than this factor, it is considered extremely overloaded
    # in such extremely loaded cases, the equipment is oversized much more, to avoid iterations in upgrades
    if len(overloaded_loading_df) > 0:  # if overloading exists
        xfmr_upgrades_df = pd.DataFrame()
        # iterate over each overloaded line to find a solution
        for index, row in overloaded_loading_df.iterrows():
            try:
                options = xfmr_upgrade_options.loc[index]
            except KeyError:
                raise UpgradesExternalCatalogMissingObjectDefinition(f"Transformer of type {dict(zip(deciding_property_list, list(index)))} not found in catalog."
                                                                     f" Please ensure catalog is complete.")
            if isinstance(options, pd.Series):  # if only one option is present, it is returned as series
                options = pd.DataFrame([options])  # convert to required DataFrame format
                options = options.rename_axis(deciding_property_list)  # assign names to the index
            options = options.reset_index().sort_values("amp_limit_per_phase")
            if row["max_per_unit_loading"] > extreme_loading_threshold:  # i.e. equipment is very overloaded, then oversize to avoid multiple upgrade iterations
                row["required_design_amp"] = row["required_design_amp"] * (row["max_per_unit_loading"] * 0.5)
            chosen_option = options.loc[options["amp_limit_per_phase"] >=
                                        row["required_design_amp"]].sort_values("amp_limit_per_phase")
            # if one chosen option exists and is not very oversized (which is determined by acceptable oversize limit)
            # edit existing object
            if (len(chosen_option) != 0) and \
                    (chosen_option["amp_limit_per_phase"] <= equipment_oversize_limit * row["required_design_amp"]).any():
                chosen_option = chosen_option.sort_values("amp_limit_per_phase")
                chosen_option = chosen_option.iloc[0]  # choose lowest available option
                chosen_option["conns"] = ast.literal_eval(chosen_option["conns"])
                chosen_option["kVs"] = ast.literal_eval(chosen_option["kVs"])
                if isinstance(chosen_option["%Rs"], str):
                    chosen_option["%Rs"] = ast.literal_eval(chosen_option["%Rs"])
                if isinstance(chosen_option["kVAs"], str):
                    chosen_option["kVAs"] = ast.literal_eval(chosen_option["kVAs"])
                # edit existing transformer
                command_string = define_xfmr_object(xfmr_name=row["name"], xfmr_info_series=chosen_option,
                                                    action_type="Edit")
                commands_list.append(command_string)
                # create dictionary of original equipment
                upgrades_dict[row["name"]] = {}
                upgrades_dict[row["name"]]["original_equipment"] = row.to_dict()
                upgrades_dict[row["name"]]["original_equipment"].update({"equipment_type": equipment_type,
                                                                         "upgrade_type": "upgrade",
                                                                         # "parameter_type": "original_equipment",
                                                                         "action": "remove"})
                upgrades_dict[row["name"]]["original_equipment"].update(chosen_option[deciding_property_list].to_dict())
                # create dictionary of new equipment
                upgrades_dict[row["name"]]["new_equipment"] = chosen_option.to_dict()
                upgrades_dict[row["name"]]["new_equipment"].update({"equipment_type": equipment_type,
                                                                    "upgrade_type": "upgrade",
                                                                    # "parameter_type": "new_equipment",
                                                                    "action": "add", "name": row["name"]})
                check_dss_run_command(command_string)  # run command for upgraded equipment
                circuit_solve_and_check(raise_exception=True, **kwargs)
            # if higher upgrade is not available or chosen upgrade rating is much higher than required,
            # dont oversize. Instead, place equipment in parallel
            else:
                parallel_xfmr_commands, temp_upgrades_dict_parallel = identify_parallel_xfmrs(upgrade_options=options, object_row=row,
                                                                                         parallel_transformers_limit=parallel_transformers_limit)
                # run command for all new parallel equipment added, that resolves overloading for one equipment
                for command_item in parallel_xfmr_commands:
                    check_dss_run_command(command_item)
                    check_dss_run_command('CalcVoltageBases')
                    circuit_solve_and_check(raise_exception=True, **kwargs)
                commands_list = commands_list + parallel_xfmr_commands
                upgrades_dict_parallel = upgrades_dict_parallel + temp_upgrades_dict_parallel  # parallel upgrades is stored in a list (since it has same original_equipment name)
        index_names = ["original_equipment_name", "parameter_type"]
        if upgrades_dict:  # if dictionary is not empty
            xfmr_upgrades_df = create_dataframe_from_nested_dict(user_dict=upgrades_dict, index_names=index_names)
        xfmr_upgrades_df = pd.concat([xfmr_upgrades_df, pd.DataFrame(upgrades_dict_parallel)])
        xfmr_upgrades_df.rename(columns={"name": "final_equipment_name"}, inplace=True)
        xfmr_upgrades_df = xfmr_upgrades_df.set_index(
            ["equipment_type", "upgrade_type", "parameter_type", "action", "final_equipment_name",
             "original_equipment_name"]).reset_index()

    else:  # if there is no overloading
        logger.info("This case has no transformer violations")
    circuit_solve_and_check(raise_exception=True, **kwargs)  # this is added as a final check for convergence
    output_fields =  list(TransformerUpgradesTechnicalResultModel.schema(True).get("properties").keys())  # get fields with alias
    xfmr_upgrades_df = xfmr_upgrades_df[output_fields]
    return commands_list, xfmr_upgrades_df


@track_timing(timer_stats_collector)
def identify_parallel_xfmrs(upgrade_options, object_row, parallel_transformers_limit):
    """This function identifies parallel transformer solutions, when a direct upgrade solution is not available from catalogue

    Parameters
    ----------
    options
    row
    parallel_transformers_limit

    Returns
    -------

    """
    output_fields = list(TransformerUpgradesTechnicalResultModel.schema(True).get("properties").keys())
    temp_output_fields = set(output_fields) - {"final_equipment_name"}
    equipment_type = "Transformer"
    commands_list = []
    upgrades_dict_parallel = {}
    # calculate number of parallel equipment needed to carry remaining amperes (in addition to existing equipment)
    upgrade_options["num_parallel_raw"] = (object_row["required_design_amp"] -
                                   object_row["amp_limit_per_phase"]) / upgrade_options["amp_limit_per_phase"]
    upgrade_options["num_parallel"] = upgrade_options["num_parallel_raw"].apply(np.ceil)
    upgrade_options["choose_parallel_metric"] = upgrade_options["num_parallel"] - upgrade_options["num_parallel_raw"]
    n = upgrade_options['num_parallel'].min()
    upgrade_options = upgrade_options.loc[upgrade_options["num_parallel"] <= parallel_transformers_limit]
    if len(upgrade_options) == 0:
        raise ExceededParallelTransformersLimit(f"Number of parallel transformers required is {int(n)}, which exceeds limit of {parallel_transformers_limit}."
                                                f" Increase parameter parallel_transformers_limit in input config or ensure higher sized equipment is present in technical catalog.")
    # choose option that has the least value of this metric- since that represents the per unit oversizing
    chosen_option = upgrade_options.loc[upgrade_options["choose_parallel_metric"].idxmin()].copy()
    chosen_option["conns"] = ast.literal_eval(chosen_option["conns"])
    chosen_option["kVs"] = ast.literal_eval(chosen_option["kVs"])
    if isinstance(chosen_option["%Rs"], str):
        chosen_option["%Rs"] = ast.literal_eval(chosen_option["%Rs"])
    if isinstance(chosen_option["kVAs"], str):
        chosen_option["kVAs"] = ast.literal_eval(chosen_option["kVAs"])
    num_parallel_xfmrs = int(chosen_option["num_parallel"])
    upgrades_dict_parallel = []
    for xfmr_count in range(0, num_parallel_xfmrs):
        curr_time = str(time.time())
        # the timestamp is added to line name to ensure it is unique
        time_stamp = curr_time.split(".")[0] + "_" + curr_time.split(".")[1]
        new_name = "upgrade_" + object_row["name"] + time_stamp
        chosen_option["name"] = new_name
        temp_dict = {}
        temp_dict.update(chosen_option.to_dict())
        temp_dict.update({"equipment_type": equipment_type,
                        "original_equipment_name": object_row["name"],
                        "upgrade_type": "new_parallel",
                        "parameter_type": "new_equipment",
                        "action": "add"})
        command_string = define_xfmr_object(xfmr_name=new_name, xfmr_info_series=chosen_option, action_type="New",
                                            buses_list=object_row["buses"])
        commands_list.append(command_string)
        temp_dict.pop("choose_parallel_metric")
        temp_dict.pop("num_parallel_raw")
        missing_fields = list(set(temp_output_fields).difference(temp_dict.keys()))  # find missing fields in temp_dict
        temp_dict.update(object_row[missing_fields].to_dict())
        upgrades_dict_parallel.append(temp_dict)
    return commands_list, upgrades_dict_parallel
