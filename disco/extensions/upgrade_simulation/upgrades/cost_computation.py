import os
import logging
import pandas as pd
import numpy as np

from jade.utils.timing_utils import track_timing, Timer
from jade.utils.utils import load_data, dump_data

from .common_functions import create_overall_output_file, convert_dict_nan_to_none, summarize_upgrades_outputs, \
    convert_length_units
from disco import timer_stats_collector
from disco.utils.custom_encoders import ExtendedJSONEncoder
from disco.models.upgrade_cost_analysis_generic_input_model import load_cost_database
from disco.models.upgrade_cost_analysis_generic_output_model import AllUpgradesTechnicalResultModel, \
    AllEquipmentUpgradeCostsResultModel, EquipmentTypeUpgradeCostsResultModel, CapacitorControllerResultType, \
        VoltageRegulatorResultType, TotalUpgradeCostsResultModel, AllUpgradesCostResultSummaryModel
    
logger = logging.getLogger(__name__)


@track_timing(timer_stats_collector)
def compute_all_costs(
    job_name,
    output_json_thermal_upgrades_filepath,
    output_json_voltage_upgrades_filepath,
    cost_database_filepath,
    output_equipment_upgrade_costs_filepath,
    output_total_upgrade_costs_filepath,
    overall_output_summary_filepath,
    feeder_stats_json_file,
):
    # upgrades files
    all_upgrades = {}
    all_upgrades.update(load_data(output_json_voltage_upgrades_filepath))
    all_upgrades.update(load_data(output_json_thermal_upgrades_filepath))
    # validate upgrades details for thermal and voltage, using pydantic models
    m = AllUpgradesTechnicalResultModel(**all_upgrades)
    xfmr_upgrades_df = pd.DataFrame(m.dict(by_alias=True)["transformer"])
    line_upgrades_df = pd.DataFrame(m.dict(by_alias=True)["line"])
    voltage_upgrades_df = pd.DataFrame(m.dict(by_alias=True)["voltage"])
    
    (
        xfmr_cost_database,
        line_cost_database,
        controls_cost_database,
        voltage_regulators_cost_database,
        misc_database,
    ) = load_cost_database(cost_database_filepath)
    output_columns = list(EquipmentTypeUpgradeCostsResultModel.schema(True).get("properties").keys())
    # reformat data
    if not xfmr_upgrades_df.empty:
        xfmr_upgrades_df, xfmr_cost_database = reformat_xfmr_files(
            xfmr_upgrades_df=xfmr_upgrades_df, xfmr_cost_database=xfmr_cost_database)
        # compute thermal upgrade costs
        xfmr_cost_df = compute_transformer_costs(xfmr_upgrades_df=xfmr_upgrades_df, xfmr_cost_database=xfmr_cost_database,
                                                 misc_database=misc_database)
        xfmr_cost_df["name"] = job_name
    else:
        xfmr_cost_df = pd.DataFrame(columns=output_columns).astype({"count": int, "total_cost_usd": float})

    if not line_upgrades_df.empty:
        line_upgrades_df, line_cost_database = reformat_line_files(
            line_upgrades_df=line_upgrades_df, line_cost_database=line_cost_database)
        line_cost_df = compute_line_costs(line_upgrades_df=line_upgrades_df, line_cost_database=line_cost_database)
        line_cost_df["name"] = job_name
    else:
        line_cost_df = pd.DataFrame(columns=output_columns).astype({"count": int, "total_cost_usd": float})

    thermal_cost_df = pd.concat([xfmr_cost_df, line_cost_df])

    if not voltage_upgrades_df.empty:
        # compute voltage upgrade costs
        cap_cost_df = compute_capcontrol_cost(voltage_upgrades_df=voltage_upgrades_df,
                                            controls_cost_database=controls_cost_database)
        reg_cost_df = compute_voltage_regcontrol_cost(voltage_upgrades_df=voltage_upgrades_df,
                                                    vreg_control_cost_database=controls_cost_database, 
                                                    vreg_xfmr_cost_database=voltage_regulators_cost_database, xfmr_cost_database=xfmr_cost_database)
        voltage_cost_df = pd.concat([cap_cost_df, reg_cost_df])
        voltage_cost_df["name"] = job_name
    else:
        voltage_cost_df = pd.DataFrame(columns=output_columns).astype({"count": int, "total_cost_usd": float})

    voltage_cost_df = voltage_cost_df.loc[voltage_cost_df["count"] != 0]
    thermal_cost_df = thermal_cost_df.loc[thermal_cost_df["count"] != 0]
    total_cost_df = get_total_costs(thermal_cost_df, voltage_cost_df)
    equipment_costs = AllEquipmentUpgradeCostsResultModel(thermal=thermal_cost_df.to_dict('records'), voltage=voltage_cost_df.to_dict('records'))
    dump_data(convert_dict_nan_to_none(equipment_costs.dict(by_alias=True)), 
              output_equipment_upgrade_costs_filepath, indent=2, cls=ExtendedJSONEncoder, allow_nan=False)
    total_cost_df["name"] = job_name
    m = [TotalUpgradeCostsResultModel(**x) for x in total_cost_df.to_dict(orient="records")]
    total_costs_per_equipment = convert_dict_nan_to_none({"costs_per_equipment": total_cost_df.to_dict('records')})
    feeder_stats = load_data(feeder_stats_json_file)
    output_summary = create_overall_output_file(upgrades_dict={"transformer": xfmr_upgrades_df, "line": line_upgrades_df, "voltage": voltage_upgrades_df},
                                                costs_dict={"thermal": thermal_cost_df, "voltage": voltage_cost_df}, feeder_stats=feeder_stats, job_name=job_name)
    output_summary_model = AllUpgradesCostResultSummaryModel(equipment=output_summary.to_dict(orient="records"))
    output_summary = convert_dict_nan_to_none(output_summary_model.dict(by_alias=True))
    if os.path.exists(overall_output_summary_filepath):
        overall_outputs = load_data(overall_output_summary_filepath)
        overall_outputs.update(total_costs_per_equipment)
    else:
        overall_outputs = total_costs_per_equipment
    overall_outputs.update(output_summary)  
    overall_outputs.update(summarize_upgrades_outputs(overall_outputs, job_name=job_name))
    desired_order_list = ["results", "costs_per_equipment", "violation_summary", "equipment"]
    reordered_dict = {k: overall_outputs[k] for k in desired_order_list}
    dump_data(reordered_dict, overall_output_summary_filepath, indent=2, cls=ExtendedJSONEncoder, allow_nan=False) 
    

def compute_transformer_costs(xfmr_upgrades_df, xfmr_cost_database, **kwargs):
    """This function computes the transformer costs.
    -Unit equipment cost for new_parallel and "upgrade" transformers are the same in the database.
    The difference would be the fixed costs added (if present in misc_database)
    -For transformers that are of action "upgrade":
    transformers of old rating are removed, and that of upgraded rating is added.
    -For transformers that are of action "new_parallel":
    A new transformer is placed in parallel with the existing transformer
    -These are the properties considered while choosing unit cost:
    ["rated_kVA", "phases", "primary_kV", "secondary_kV", "primary_connection_type", "secondary_connection_type",
    "num_windings"]
    -For a given transformer, if unit cost pertaining to these properties is not available,
    then the closest "rated_kVA" unit cost is chosen.
    User can decide if they want to choose backup based on another property.
    Parameters
    ----------
    xfmr_upgrades_df
    xfmr_cost_database
    kwargs

    Returns
    -------

    """
    output_cost_field = "total_cost_usd"
    output_count_field = "count"
    deciding_columns = ["rated_kVA", "phases", "primary_kV", "secondary_kV", "primary_connection_type",
                        "secondary_connection_type", "num_windings"]
    output_columns_list = ["type", output_count_field, output_cost_field, "comment", "equipment_parameters"]
    backup_deciding_property = kwargs.get("backup_deciding_property", "rated_kVA")
    misc_database = kwargs.get("misc_database", None)
    # choose which properties are to be saved
    upgrade_type_list = ["upgrade", "new_parallel"]
    added_xfmr_df = xfmr_upgrades_df.loc[(xfmr_upgrades_df["upgrade_type"].isin(upgrade_type_list)) & (xfmr_upgrades_df["action"] == "add")]
    computed_cost = []
    for index, row in added_xfmr_df.iterrows():
        unit_cost = xfmr_cost_database.loc[(xfmr_cost_database["rated_kVA"] == row["rated_kVA"]) &
                                           (xfmr_cost_database["phases"] == row["phases"]) &
                                           (xfmr_cost_database["primary_kV"] == row["primary_kV"]) &
                                           (xfmr_cost_database["secondary_kV"] == row["secondary_kV"]) &
                                           (xfmr_cost_database["primary_connection_type"] == row["primary_connection_type"]) &
                                           (xfmr_cost_database["secondary_connection_type"] == row["secondary_connection_type"]) &
                                           (xfmr_cost_database["num_windings"] == row["num_windings"])
                                           ]["cost"]
        params_dict = dict(row[['final_equipment_name'] + deciding_columns])
        row["equipment_parameters"] = params_dict
        row["type"] = "Transformer"
        if len(unit_cost) > 0:  # if there are more than one rows, the first one is chosen in random
            unit_cost = unit_cost.values[0]
            row[output_cost_field] = unit_cost
            row["comment"] = ""
            row[output_count_field] = 1
        else:  # if costs are not present for this transformer, then choose closest rated_kVA
            # (or whatever backup deciding property is passed) (ignore other properties)
            closest = xfmr_cost_database.loc[abs(xfmr_cost_database[backup_deciding_property] -
                                                 row[backup_deciding_property]).idxmin()].copy()
            row[output_cost_field] = closest["cost"]
            row[output_count_field] = 1
            for key, value in closest.items():  # make it json serializable
                if isinstance(value, np.int64):
                    closest[key] = int(value)
            comment_string = {"text": f"Transformer {row['final_equipment_name']}: Exact cost not available. " \
                                      f"Unit cost for transformer with these parameters used " \
                                      f"(based on closest {backup_deciding_property}", 
                             "params": dict(closest)}
            logger.debug(comment_string)
            row["comment"] = comment_string
        # add transformer fixed costs, if given in database. (depending on upgrade type)
        if (misc_database is not None) and (not misc_database.empty):
            misc_xfmr_fields = {"replace": "Replace transformer (fixed cost)",
                                "new": "Add new transformer (fixed cost)"}
            # if equipment is upgraded, and misc database contains fixed cost for replacing xfmr
            if (row["upgrade_type"].lower() == "upgrade") and \
                    ((misc_database["description"] == misc_xfmr_fields["replace"]).any()):
                field_name = misc_xfmr_fields["replace"]
                fixed_cost = misc_database.loc[misc_database["description"] == field_name]
            # if equipment is new, and misc database contains fixed cost for adding new xfmr
            elif row["upgrade_type"].lower() == "new_parallel" and \
                    ((misc_database["description"] == misc_xfmr_fields["new"]).any()):
                field_name = misc_xfmr_fields["new"]
                fixed_cost = misc_database.loc[misc_database["description"] == field_name]
            else:
                fixed_cost = pd.DataFrame()
            if not fixed_cost.empty:
                row[output_cost_field] += misc_database.loc[misc_database["description"]
                                                            == field_name]["total_cost"].values[0]

        computed_cost.append(row[output_columns_list])
    xfmr_cost_df = pd.DataFrame(computed_cost)
    return xfmr_cost_df


def reformat_xfmr_files(xfmr_upgrades_df, xfmr_cost_database):
    """This function renames, reformats transformer upgrades dataframe to match cost database columns

    Parameters
    ----------
    xfmr_upgrades_df
    xfmr_cost_database

    Returns
    -------

    """
    xfmr_upgrades_df.rename(columns={"kVA": "rated_kVA", "windings": "num_windings"}, inplace=True)
    xfmr_upgrades_df["rated_kVA"] = xfmr_upgrades_df["rated_kVA"].astype(float)
    xfmr_upgrades_df["num_windings"] = xfmr_upgrades_df["num_windings"].astype(int)
    xfmr_upgrades_df["phases"] = xfmr_upgrades_df["phases"].astype(int)
    xfmr_upgrades_df["primary_kV"] = xfmr_upgrades_df["kVs"].str[0].astype(float)
    xfmr_upgrades_df["secondary_kV"] = xfmr_upgrades_df["kVs"].str[-1].astype(float)
    xfmr_upgrades_df["primary_connection_type"] = xfmr_upgrades_df["conns"].str[0]
    xfmr_upgrades_df["secondary_connection_type"] = xfmr_upgrades_df["conns"].str[-1]

    xfmr_cost_database["rated_kVA"] = xfmr_cost_database["rated_kVA"].astype(float)
    xfmr_cost_database["num_windings"] = xfmr_cost_database["num_windings"].astype(int)
    xfmr_cost_database["phases"] = xfmr_cost_database["phases"].astype(int)
    xfmr_cost_database["primary_kV"] = xfmr_cost_database["primary_kV"].astype(float)
    xfmr_cost_database["secondary_kV"] = xfmr_cost_database["secondary_kV"].astype(float)
    xfmr_cost_database["cost"] = xfmr_cost_database["cost"].astype(float)

    return xfmr_upgrades_df, xfmr_cost_database


def reformat_xfmr_upgrades_file(xfmr_upgrades_df):
    xfmr_upgrades_df.rename(columns={"kVA": "rated_kVA", "windings": "num_windings"}, inplace=True)
    xfmr_upgrades_df["rated_kVA"] = xfmr_upgrades_df["rated_kVA"].astype(float)
    xfmr_upgrades_df["num_windings"] = xfmr_upgrades_df["num_windings"].astype(int)
    xfmr_upgrades_df["phases"] = xfmr_upgrades_df["phases"].astype(int)
    xfmr_upgrades_df["primary_kV"] = xfmr_upgrades_df["kVs"].str[0].astype(float)
    xfmr_upgrades_df["secondary_kV"] = xfmr_upgrades_df["kVs"].str[-1].astype(float)
    xfmr_upgrades_df["primary_connection_type"] = xfmr_upgrades_df["conns"].str[0]
    xfmr_upgrades_df["secondary_connection_type"] = xfmr_upgrades_df["conns"].str[-1]
    return xfmr_upgrades_df


def compute_line_costs(line_upgrades_df, line_cost_database, **kwargs):
    """This function computes the line costs.
    -Unit equipment cost for new_parallel and "upgrade" line are the not same in the database.
    There are different costs given for reconductored and new lines
    -For lines that are of action "upgrade": "reconductored" line unit costs need to be used
    -For lines that are of action "new_parallel": "new" line unit costs need to be used
    -Upgraded lines and new lines run along existing circuit, so length is the same for both
    -These are the properties considered while choosing unit cost:
    ["phases", "voltage_kV", "ampere_rating", "line_placement", "description" (i.e. whether new or reconductored)]
    -For a given line, if unit cost pertaining to these properties is not available,
    then the closest "ampere_rating" unit cost is chosen.
    User can decide if they want to choose backup based on another property.
    For 3 phase lines, voltage_kV should be LN voltage (# TODO check if this is correct)

    Parameters
    ----------
    line_upgrades_df
    line_cost_database
    kwargs

    Returns
    -------

    """
    output_cost_field = "total_cost_usd"
    output_count_field = "count"
    deciding_columns = ["phases", "voltage_kV", "ampere_rating", "line_placement", "upgrade_type"]
    output_columns_list = ["type", output_count_field, output_cost_field, "comment", "equipment_parameters"]
    backup_deciding_property = kwargs.get("backup_deciding_property", "ampere_rating")
    # choose which properties are to be saved
    upgrade_type_list = ["upgrade", "new_parallel"]
    
    added_line_df = line_upgrades_df.loc[(line_upgrades_df["upgrade_type"].isin(upgrade_type_list)) & (line_upgrades_df["action"] == "add")]
    computed_cost = []
    for index, row in added_line_df.iterrows():
        if row["upgrade_type"] == "upgrade":
            upgrade_type = "reconductored_line"
        elif row["upgrade_type"] == "new_parallel":
            upgrade_type = "new_line"
        else:
            # if anything else, by default, use new_line prices
            upgrade_type = "new_line"
        row["upgrade_type"] = upgrade_type
        unit_cost = line_cost_database.loc[(line_cost_database["phases"] == row["phases"]) &
                                           (line_cost_database["voltage_kV"] == row["voltage_kV"]) &
                                           (line_cost_database["ampere_rating"] == row["ampere_rating"]) &
                                           (line_cost_database["line_placement"] == row["line_placement"]) &
                                           (line_cost_database["upgrade_type"] == upgrade_type)
                                           ]["cost_per_m"]
        # OpenDSS can output results in any of these lengths.
        # convert line length to metres
        line_length_m = convert_length_units(length=row["length"], unit_in=row["units"], unit_out="m")
        params_dict = dict(row[['final_equipment_name'] + deciding_columns])
        row["equipment_parameters"] = params_dict
        row["type"] = "Line"
        if len(unit_cost) > 0:  # if there are more than one rows, the first one is chosen in random
            unit_cost = unit_cost.values[0]
            row[output_cost_field] = unit_cost * line_length_m
            row[output_count_field] = 1
            row["comment"] = ""
        else:  # if costs are not present for this transformer, then choose closest ampere_rating
            # (or whatever backup deciding property is passed) (ignore other properties)
            closest = line_cost_database.loc[abs(line_cost_database[backup_deciding_property] -
                                                 row[backup_deciding_property]).idxmin()].copy()
            row[output_cost_field] = closest["cost_per_m"] * line_length_m
            for key, value in closest.items():  # make it json serializable
                if isinstance(value, np.int64):
                    closest[key] = int(value)
            comment_string = {"text": f"Line {row['final_equipment_name']}: Exact cost not available. " \
                                      f"Unit cost for line with these parameters used " \
                                      f"(based on closest {backup_deciding_property}.",
                             "params": dict(closest)}
            
            logger.debug(comment_string)
            row["comment"] = comment_string
            row[output_count_field] = 1
        computed_cost.append(row[output_columns_list])
    line_cost_df = pd.DataFrame(computed_cost)
    return line_cost_df


def reformat_line_files(line_upgrades_df, line_cost_database):
    """This function renames, reformats line upgrades dataframe to match cost database columns

    Parameters
    ----------
    line_upgrades_df
    line_cost_database

    Returns
    -------

    """
    line_upgrades_df.rename(columns={"normamps": "ampere_rating", "kV": "voltage_kV"}, inplace=True)
    line_upgrades_df["ampere_rating"] = line_upgrades_df["ampere_rating"].astype(float).round(2)
    line_upgrades_df["phases"] = line_upgrades_df["phases"].astype(int)
    line_upgrades_df["voltage_kV"] = line_upgrades_df["voltage_kV"].astype(float).round(2)
    # assign original equipment length to new equipment
    line_upgrades_df["length"] = line_upgrades_df.groupby("original_equipment_name")["length"].transform("first")

    line_cost_database["ampere_rating"] = line_cost_database["ampere_rating"].astype(float).round(2)
    line_cost_database["phases"] = line_cost_database["phases"].astype(int)
    line_cost_database["voltage_kV"] = line_cost_database["voltage_kV"].astype(float).round(2)
    line_cost_database["cost_per_m"] = line_cost_database["cost_per_m"].astype(float)
    return line_upgrades_df, line_cost_database


def compute_capcontrol_cost(voltage_upgrades_df, controls_cost_database, keyword="Capacitor"):
    """This function computes the capacitor controller related costs.
    Note we currently are not adding new capacitors to integrate PV.
    Considered here: new controllers, control setting changes

    Parameters
    ----------
    voltage_upgrades_df
    controls_cost_database

    Returns
    -------

    """
    output_cost_field = "total_cost_usd"
    output_count_field = "count"
    output_columns_list = ["type", output_count_field, output_cost_field, "comment"]

    type_rows = CapacitorControllerResultType.list_values()  # from enum
    capcontrol_upgrade_fields = {"add_new_cap_controller": "new_controller_added",
                         "change_cap_control": "controller_settings_modified"}
    cost_database_fields = {"add_new_cap_controller": "Add new capacitor controller",
                            "change_cap_control": "Change capacitor controller settings",
                            "replace_cap_controller": "Replace capacitor controller"
                            }
    empty_cap_cost_dict = {"type": type_rows,
                           "count": [0] * len(type_rows),  "total_cost_usd": [0] * len(type_rows)}
    zero_cost_df = pd.DataFrame.from_dict(empty_cap_cost_dict)

    if voltage_upgrades_df.empty:  # if there are no voltage upgrades
        return zero_cost_df
    cap_upgrades_df = voltage_upgrades_df.loc[voltage_upgrades_df['equipment_type'].str.contains(keyword)]
    if cap_upgrades_df.empty:  # if there are no capacitor control upgrades
        return zero_cost_df
    cap_cost = []
    # if there are new capacitor controller 
    count_new_controller = cap_upgrades_df[capcontrol_upgrade_fields["add_new_cap_controller"]].sum()
    unit_cost_new_controller = controls_cost_database.loc[controls_cost_database["type"]
                                                          == cost_database_fields["add_new_cap_controller"]]["cost"].values[0]
    total_cost_new_controller = count_new_controller * unit_cost_new_controller
    cap_cost.append( {"type": CapacitorControllerResultType.add_new_cap_controller.value,
                 "count": count_new_controller, "total_cost_usd": total_cost_new_controller}
    )
    
    # if there are setting changes
    count_setting_changes = cap_upgrades_df[capcontrol_upgrade_fields["change_cap_control"]].sum()
    unit_cost_setting_changes = controls_cost_database.loc[controls_cost_database["type"] ==
                                                           cost_database_fields["change_cap_control"]]["cost"].values[0]
    total_cost_setting_changes = count_setting_changes * unit_cost_setting_changes
    cap_cost.append( {"type": CapacitorControllerResultType.change_cap_control.value,
                     "count": count_setting_changes, "total_cost_usd": total_cost_setting_changes}
    )
    cap_cost_df = pd.DataFrame(cap_cost)
    cap_cost_df["comment"] = ""
    cap_cost_df = cap_cost_df[output_columns_list]
    return cap_cost_df


def compute_voltage_regcontrol_cost(voltage_upgrades_df, vreg_control_cost_database, vreg_xfmr_cost_database, xfmr_cost_database, keyword="RegControl"):
    """This function computes the voltage regulator controller related costs.
    Considered here: new voltage regulator controllers, control setting changes

    Parameters
    ----------
    voltage_upgrades_df
    controls_cost_database

    Returns
    -------

    """
    output_cost_field = "total_cost_usd"
    output_count_field = "count"
    output_columns_list = ["type", output_count_field, output_cost_field, "comment"]
    upgrade_fields_dict = {"add_new_reg_control": "new_controller_added",
                      "change_reg_control": "controller_settings_modified",
                      "add_new_transformer": "new_transformer_added",
                      "at_substation": "at_substation",
                    #   "change_ltc_control": "Substation LTC settings modified",
                        }
    cost_database_fields_dict = {"add_new_reg_control": "Add new voltage regulator controller",
                            "change_reg_control": "Change voltage regulator controller settings",
                            # "replace_reg_control": "Replace voltage regulator controller",   # this is not used currently
                            "add_substation_ltc": "Add new LTC controller",
                            "change_ltc_control": "Change LTC settings",
                            "add_new_transformer": "Add new voltage regulator transformer"}
    
    type_fields_dict = {i.name: i.value for i in VoltageRegulatorResultType}
    type_rows = list(type_fields_dict.keys())
    
    control_computation_fields = ["add_new_reg_control", "change_reg_control"]
    xfmr_fields = ["add_new_transformer"]

    empty_reg_cost_dict = {"type": type_rows, "count": [0] * len(type_rows),  "total_cost_usd": [0] * len(type_rows)}
    zero_cost_df = pd.DataFrame.from_dict(empty_reg_cost_dict)

    if voltage_upgrades_df.empty:  # if there are no voltage upgrades
        return zero_cost_df
    reg_upgrades_df = voltage_upgrades_df.loc[voltage_upgrades_df['equipment_type'].str.contains(keyword)]
    if reg_upgrades_df.empty:  # if there are no regulator controller upgrades
        return zero_cost_df

    cost_list = []
    # if there are regulator controller upgrades
    for field in control_computation_fields:
        # if at substation
        at_substation_df = reg_upgrades_df.loc[reg_upgrades_df[upgrade_fields_dict["at_substation"]] == True]
        if field == "add_new_reg_control":
            cost_field = "add_substation_ltc"
        elif field == "change_reg_control":
            cost_field = "change_ltc_control"
        else:
            raise Exception(f"Unknown field {field} in regulator cost computation")
        if not at_substation_df.empty:  # if there are no regcontrols at substation
            count = at_substation_df[upgrade_fields_dict[field]].sum()
            unit_cost = vreg_control_cost_database.loc[vreg_control_cost_database["type"] == cost_database_fields_dict[cost_field]]["cost"].values[0]
            total_cost = count * unit_cost
            cost_list.append({"type": type_fields_dict[cost_field], "count": count, "total_cost_usd": total_cost, "comment": ""})
        
        # if not at substation
        not_at_substation_df = reg_upgrades_df.loc[reg_upgrades_df[upgrade_fields_dict["at_substation"]] == False]
        cost_field = field
        if not not_at_substation_df.empty:  # if not at substation
            count = not_at_substation_df[upgrade_fields_dict[field]].sum()
            unit_cost = vreg_control_cost_database.loc[vreg_control_cost_database["type"] == cost_database_fields_dict[cost_field]]["cost"].values[0]
            total_cost = count * unit_cost
            cost_list.append({"type": type_fields_dict[cost_field], "count": count, "total_cost_usd": total_cost, "comment": ""})
    
    # add costs for added transformers (needed for voltage regulators)
    vreg_xfmr_cost_database = vreg_xfmr_cost_database.drop(columns=["type"])
    vreg_xfmr_cost_database = pd.concat([vreg_xfmr_cost_database, xfmr_cost_database])
    for field in xfmr_fields:
        cost_field = field
        # if at substation
        new_xfmr_added_df = reg_upgrades_df.loc[reg_upgrades_df[upgrade_fields_dict["add_new_transformer"]] == True]    
        for index, row in new_xfmr_added_df.iterrows():
            output_row = {}
            added_xfmr_details = row["final_settings"]
            added_xfmr_details = reformat_xfmr_upgrades_file(pd.DataFrame([added_xfmr_details]))
            deciding_columns = ["rated_kVA", "phases", "primary_kV", "secondary_kV", "primary_connection_type",
                        "secondary_connection_type", "num_windings"]
            params_dict = added_xfmr_details[["name"] + deciding_columns].to_dict(orient="records")[0]
            added_xfmr_details = added_xfmr_details.to_dict(orient="records")[0]
            output_row["equipment_parameters"] = params_dict
            # reformat xfmr dict
            unit_cost = vreg_xfmr_cost_database.loc[(vreg_xfmr_cost_database["rated_kVA"] == added_xfmr_details["rated_kVA"]) &
                                            (vreg_xfmr_cost_database["primary_kV"] == added_xfmr_details["primary_kV"]) &
                                            (vreg_xfmr_cost_database["secondary_kV"] == added_xfmr_details["secondary_kV"]) &
                                            (vreg_xfmr_cost_database["phases"] == added_xfmr_details["phases"]) &
                                            (vreg_xfmr_cost_database["num_windings"] == added_xfmr_details["num_windings"]) &
                                            (vreg_xfmr_cost_database["primary_connection_type"] == added_xfmr_details["primary_connection_type"]) &
                                            (vreg_xfmr_cost_database["secondary_connection_type"] == added_xfmr_details["secondary_connection_type"])
                                            ]["cost"]
            if len(unit_cost) > 0:  # if there are more than one rows, the first one is chosen in random
                unit_cost = unit_cost.values[0]
                output_row[output_cost_field] = unit_cost
                output_row["comment"] = ""
                output_row[output_count_field] = 1
            else:  # if costs are not present for this transformer, then choose from other xfmr database rated_kVA
                backup_deciding_property = "rated_kVA"
                closest = vreg_xfmr_cost_database.loc[abs(vreg_xfmr_cost_database[backup_deciding_property] - added_xfmr_details[backup_deciding_property]).idxmin()].copy()
                if isinstance(closest, pd.DataFrame):
                    closest = closest.iloc[0]
                output_row[output_cost_field] = closest["cost"]
                output_row[output_count_field] = 1
                for key, value in closest.items():  # make it json serializable
                    if isinstance(value, np.int64):
                        closest[key] = int(value)
                comment_string =  {"text": f"Transformer {added_xfmr_details['name']}: Exact cost not available. " \
                                           f"Unit cost for transformer with these parameters used " \
                                           f"(based on closest {backup_deciding_property}", 
                                  "params": dict(closest)}
                                  
                logger.debug(comment_string)
                output_row["comment"] = comment_string
            if row[upgrade_fields_dict["at_substation"]]:
                output_row["type"] = type_fields_dict["add_new_substation_transformer"]
            else: 
                output_row["type"] = type_fields_dict["add_new_vreg_transformer"]
            cost_list.append(output_row)

    reg_cost_df = pd.DataFrame(cost_list)
    reg_cost_df = reg_cost_df[output_columns_list]
    return reg_cost_df


def get_total_costs(thermal_cost_df, voltage_cost_df):
    """This function combines voltage and thermal upgrades costs into one file.
    """
    total_cost_df = pd.concat([thermal_cost_df, voltage_cost_df])
    total_cost_df = total_cost_df.groupby('type').sum(numeric_only=True)
    total_cost_df.reset_index(inplace=True)
    return total_cost_df


if __name__ == "__main__":
    compute_all_costs()
