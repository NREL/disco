import logging
import pandas as pd
import ast

from jade.utils.timing_utils import track_timing, Timer
from jade.utils.utils import load_data, dump_data

from disco import timer_stats_collector

logger = logging.getLogger(__name__)
# Dictionary used to convert between different length units and meters, which are used for all the calculations.
# OpenDSS can output results in any of these lengths.
LENGTH_CONVERSION_TO_METRE = {
    "mi": 1609.34,
    "kft": 304.8,
    "km": 1000,
    "ft": 0.3048,
    "in": 0.0254,
    "cm": 0.01,
    "m": 1,
}

@track_timing(timer_stats_collector)
def compute_all_costs(
    output_json_xfmr_upgrades_filepath,
    output_json_line_upgrades_filepath,
    output_json_voltage_upgrades_filepath,
    cost_database_filepath,
    thermal_cost_output_filepath,
    voltage_cost_output_filepath,
    total_cost_output_filepath
):
    # upgrades files
    # TODO add except statement for FileNotFoundError
    xfmr_upgrades_df = pd.DataFrame(load_data(output_json_xfmr_upgrades_filepath))
    line_upgrades_df = pd.DataFrame(load_data(output_json_line_upgrades_filepath))
    voltage_upgrades_df = pd.DataFrame(load_data(output_json_voltage_upgrades_filepath))

    # unit cost database files
    xfmr_cost_database = pd.read_excel(cost_database_filepath, "transformers")
    line_cost_database = pd.read_excel(cost_database_filepath, "lines")
    controls_cost_database = pd.read_excel(cost_database_filepath, "control_changes")
    voltage_regulators_cost_database = pd.read_excel(
        cost_database_filepath, "voltage_regulators"
    )
    misc_database = pd.read_excel(cost_database_filepath, "misc")

    output_columns = ["type", "count", "total_cost_usd", "comment", "equipment_parameters"]

    # reformat data
    if not xfmr_upgrades_df.empty:
        xfmr_upgrades_df, xfmr_cost_database = reformat_xfmr_files(
            xfmr_upgrades_df=xfmr_upgrades_df, xfmr_cost_database=xfmr_cost_database
        )
        # compute thermal upgrade costs
        xfmr_cost_df = compute_transformer_costs(
            xfmr_upgrades_df=xfmr_upgrades_df,
            xfmr_cost_database=xfmr_cost_database,
            misc_database=misc_database,
        )
    else:
        xfmr_cost_df = pd.DataFrame(columns=output_columns).astype({"count": int, "total_cost_usd": float})

    if not line_upgrades_df.empty:
        line_upgrades_df, line_cost_database = reformat_line_files(
            line_upgrades_df=line_upgrades_df, line_cost_database=line_cost_database
        )
        line_cost_df = compute_line_costs(
            line_upgrades_df=line_upgrades_df, line_cost_database=line_cost_database
        )
    else:
        line_cost_df = pd.DataFrame(columns=output_columns).astype({"count": int, "total_cost_usd": float})

    thermal_cost_df = xfmr_cost_df.append(line_cost_df)

    if not voltage_upgrades_df.empty:
        # compute voltage upgrade costs
        cap_cost_df = compute_capcontrol_cost(voltage_upgrades_df=voltage_upgrades_df,
                                            controls_cost_database=controls_cost_database)
        reg_cost_df = compute_voltage_regcontrol_cost(voltage_upgrades_df=voltage_upgrades_df,
                                                    vreg_control_cost_database=controls_cost_database, 
                                                    vreg_xfmr_cost_database=voltage_regulators_cost_database, xfmr_cost_database=xfmr_cost_database)
        voltage_cost_df = cap_cost_df.append(reg_cost_df)
    else:
        voltage_cost_df = pd.DataFrame(columns=output_columns).astype({"count": int, "total_cost_usd": float})

    total_cost_df = get_total_costs(thermal_cost_df, voltage_cost_df)

    # save output files
    dump_data(thermal_cost_df.to_dict('records'), thermal_cost_output_filepath, indent=4)
    dump_data(voltage_cost_df.to_dict('records'), voltage_cost_output_filepath, indent=4)
    dump_data(total_cost_df.to_dict('records'), total_cost_output_filepath, indent=4)


def compute_transformer_costs(xfmr_upgrades_df, xfmr_cost_database, **kwargs):
    """This function computes the transformer costs.
    -Unit equipment cost for new(parallel) and "upgrade" transformers are the same in the database.
    The difference would be the fixed costs added (if present in misc_database)
    -For transformers that are of ActionType "upgrade":
    transformers of old rating are removed, and that of upgraded rating is added.
    -For transformers that are of ActionType "new(parallel)":
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
    upgrade_type_list = ["upgrade", "new (parallel)"]
    added_xfmr_df = xfmr_upgrades_df.loc[(xfmr_upgrades_df["Upgrade_Type"].isin(upgrade_type_list)) & (xfmr_upgrades_df["Action"] == "add")]
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
                                                 row[backup_deciding_property]).idxmin()]
            row[output_cost_field] = closest["cost"]
            row[output_count_field] = 1
            comment_string = f"Transformer {row['final_equipment_name']}: Exact cost not available. " \
                             f"Unit cost for transformer with these parameters used " \
                             f"(based on closest {backup_deciding_property}:  {dict(closest)}"
            logger.debug(comment_string)
            row["comment"] = comment_string
        # add transformer fixed costs, if given in database. (depending on upgrade type)
        if (misc_database is not None) and (not misc_database.empty):
            misc_xfmr_fields = {"replace": "Replace transformer (fixed cost)",
                                "new": "Add new transformer (fixed cost)"}
            # if equipment is upgraded, and misc database contains fixed cost for replacing xfmr
            if (row["Upgrade_Type"].lower() == "upgrade") and \
                    ((misc_database["Description"] == misc_xfmr_fields["replace"]).any()):
                field_name = misc_xfmr_fields["replace"]
                fixed_cost = misc_database.loc[misc_database["Description"] == field_name]
            # if equipment is new, and misc database contains fixed cost for adding new xfmr
            elif row["Upgrade_Type"].lower() == "new (parallel)" and \
                    ((misc_database["Description"] == misc_xfmr_fields["new"]).any()):
                field_name = misc_xfmr_fields["new"]
                fixed_cost = misc_database.loc[misc_database["Description"] == field_name]
            else:
                fixed_cost = pd.DataFrame()
            if not fixed_cost.empty:
                row[output_cost_field] += misc_database.loc[misc_database["Description"]
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
    xfmr_upgrades_df["conns"] = xfmr_upgrades_df["conns"].apply(ast.literal_eval)
    xfmr_upgrades_df["primary_connection_type"] = xfmr_upgrades_df["conns"].str[0]
    xfmr_upgrades_df["secondary_connection_type"] = xfmr_upgrades_df["conns"].str[-1]
    return xfmr_upgrades_df


def compute_line_costs(line_upgrades_df, line_cost_database, **kwargs):
    """This function computes the line costs.
    -Unit equipment cost for new(parallel) and "upgrade" line are the not same in the database.
    There are different costs given for reconductored and new lines
    -For lines that are of ActionType "upgrade": "reconductored" line unit costs need to be used
    -For lines that are of ActionType "new (parallel)": "new" line unit costs need to be used
    -Upgraded lines and new lines run along existing circuit, so length is the same for both
    -These are the properties considered while choosing unit cost:
    ["phases", "voltage_kV", "ampere_rating", "line_placement", "Description" (i.e. whether new or reconductored)]
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
    deciding_columns = ["phases", "voltage_kV", "ampere_rating", "line_placement", "Description"]
    output_columns_list = ["type", output_count_field, output_cost_field, "comment", "equipment_parameters"]
    backup_deciding_property = kwargs.get("backup_deciding_property", "ampere_rating")
    # choose which properties are to be saved
    upgrade_type_list = ["upgrade", "new (parallel)"]
    added_line_df = line_upgrades_df.loc[(line_upgrades_df["Upgrade_Type"].isin(upgrade_type_list)) & (line_upgrades_df["Action"] == "add")]
    computed_cost = []
    for index, row in added_line_df.iterrows():
        if row["Upgrade_Type"] == "upgrade":
            description = "reconductored_line"
        elif row["Upgrade_Type"] == "new (parallel)":
            description = "new_line"
        else:
            # if anything else, by default, use new_line prices
            description = "new_line"
        row["Description"] = description
        unit_cost = line_cost_database.loc[(line_cost_database["phases"] == row["phases"]) &
                                           (line_cost_database["voltage_kV"] == row["voltage_kV"]) &
                                           (line_cost_database["ampere_rating"] == row["ampere_rating"]) &
                                           (line_cost_database["line_placement"] == row["line_placement"]) &
                                           (line_cost_database["Description"] == description)
                                           ]["cost_per_m"]
        # convert line length to metres
        line_length_m = row["length"] * LENGTH_CONVERSION_TO_METRE[row["units"]]
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
                                                 row[backup_deciding_property]).idxmin()]
            row[output_cost_field] = closest["cost_per_m"] * line_length_m
            comment_string = f"Line {row['final_equipment_name']}: Exact cost not available. " \
                             f"Unit cost for line with these parameters used " \
                             f"(based on closest {backup_deciding_property}: {dict(closest)}"
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

    output_rows = ["New Capacitor controller", "Capacitor controller setting change"]
    capcontrol_fields = {"add_new_cap_controller": "New controller added",
                         "change_cap_control": "Controller settings modified"}
    cost_database_fields = {"add_new_cap_controller": "Add new capacitor controller",
                            "change_cap_control": "Change capacitor controller settings",
                            "replace_cap_controller": "Replace capacitor controller"
                            }
    empty_cap_cost_dict = {"type": output_rows,
                           "count": [0] * len(output_rows),  "total_cost_usd": [0] * len(output_rows)}
    zero_cost_df = pd.DataFrame.from_dict(empty_cap_cost_dict)

    if voltage_upgrades_df.empty:  # if there are no voltage upgrades
        return zero_cost_df
    cap_upgrades_df = voltage_upgrades_df.loc[voltage_upgrades_df['equipment_type'].str.contains(keyword)]
    if cap_upgrades_df.empty:  # if there are no capacitor control upgrades
        return zero_cost_df
    # if there are capacitor controller upgrades
    count_new_controller = cap_upgrades_df[capcontrol_fields["add_new_cap_controller"]].sum()
    unit_cost_new_controller = controls_cost_database.loc[controls_cost_database["Type"]
                                                          == cost_database_fields["add_new_cap_controller"]]["cost"].values[0]
    total_cost_new_controller = count_new_controller * unit_cost_new_controller

    count_setting_changes = cap_upgrades_df[capcontrol_fields["change_cap_control"]].sum()
    unit_cost_setting_changes = controls_cost_database.loc[controls_cost_database["Type"] ==
                                                           cost_database_fields["change_cap_control"]]["cost"].values[0]
    total_cost_setting_changes = count_setting_changes * unit_cost_setting_changes

    cap_cost_dict = {
        "type": output_rows,
        "count": [count_new_controller, count_setting_changes],
        "total_cost_usd": [total_cost_new_controller, total_cost_setting_changes],
    }
    cap_cost_df = pd.DataFrame.from_dict(cap_cost_dict)
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
    upgrade_fields_dict = {"add_new_reg_control": "New controller added",
                      "change_reg_control": "Controller settings modified",
                      "add_new_transformer": "New transformer added",
                      "at_substation": "At Substation",
                    #   "change_ltc_control": "Substation LTC settings modified",
                        }
    cost_database_fields_dict = {"add_new_reg_control": "Add new voltage regulator controller",
                            "change_reg_control": "Change voltage regulator controller settings",
                            # "replace_reg_control": "Replace voltage regulator controller",   # this is not used currently
                            "add_substation_ltc": "Add new LTC controller",
                            "change_ltc_control": "Change LTC settings",
                            "add_new_transformer": "Add new voltage regulator transformer"}
    
    output_fields_dict = {"add_new_reg_control": "New in-line voltage regulator",
                        "change_reg_control": "In-line voltage regulator control setting change",
                        # "replace_reg_control": "Replace in-line voltage regulator controller",   # this is not used currently
                        "add_substation_ltc": "New substation LTC",
                        "change_ltc_control": "Substation LTC setting change",
                        "add_new_vreg_transformer": "Transformer for voltage regulator",
                        "add_new_substation_transformer":  "Substation transformer"}
    
    
    output_rows = ["New in-line voltage regulator", "In-line voltage regulator control setting change",
                   "Replace in-line voltage regulator controller",
                   "New substation LTC", "Substation LTC setting change",
                   "Substation transformer", "Transformer for voltage regulator"]

    control_computation_fields = ["add_new_reg_control", "change_reg_control"]
    xfmr_fields = ["add_new_transformer"]

    empty_reg_cost_dict = {"type": output_rows, "count": [0] * len(output_rows),  "total_cost_usd": [0] * len(output_rows)}
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
            unit_cost = vreg_control_cost_database.loc[vreg_control_cost_database["Type"] == cost_database_fields_dict[cost_field]]["cost"].values[0]
            total_cost = count * unit_cost
        else:
            count = 0
            total_cost = 0
        cost_list.append({"type": output_fields_dict[cost_field], "count": count, "total_cost_usd": total_cost, "comment": ""})
        
        # if not at substation
        not_at_substation_df = reg_upgrades_df.loc[reg_upgrades_df[upgrade_fields_dict["at_substation"]] == False]
        cost_field = field
        if not not_at_substation_df.empty:  # if not at substation
            count = not_at_substation_df[upgrade_fields_dict[field]].sum()
            unit_cost = vreg_control_cost_database.loc[vreg_control_cost_database["Type"] == cost_database_fields_dict[cost_field]]["cost"].values[0]
            total_cost = count * unit_cost
        else:
            count = 0
            total_cost = 0
        cost_list.append({"type": output_fields_dict[cost_field], "count": count, "total_cost_usd": total_cost, "comment": ""})
    
    # add costs for added transformers (needed for voltage regulators)
    vreg_xfmr_cost_database = vreg_xfmr_cost_database.append(xfmr_cost_database)
    for field in xfmr_fields:
        cost_field = field
        # if at substation
        new_xfmr_added_df = reg_upgrades_df.loc[reg_upgrades_df[upgrade_fields_dict["add_new_transformer"]] == True]    
        for index, row in new_xfmr_added_df.iterrows():
            output_row = {}
            added_xfmr_details = row["Final Settings"]
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
                closest = vreg_xfmr_cost_database.loc[abs(vreg_xfmr_cost_database[backup_deciding_property] - added_xfmr_details[backup_deciding_property]).idxmin()]
                output_row[output_cost_field] = closest["cost"]
                output_row[output_count_field] = 1
                comment_string = f"Transformer {added_xfmr_details['name']}: Exact cost not available. " \
                                f"Unit cost for transformer with these parameters used " \
                                f"(based on closest {backup_deciding_property}:  {dict(closest)}"
                logger.debug(comment_string)
                output_row["comment"] = comment_string
            if row[upgrade_fields_dict["at_substation"]]:
                output_row["type"] = output_fields_dict["add_new_substation_transformer"]
            else: 
                output_row["type"] = output_fields_dict["add_new_vreg_transformer"]
            cost_list.append(output_row)

    reg_cost_df = pd.DataFrame(cost_list)
    reg_cost_df = reg_cost_df[output_columns_list]
    return reg_cost_df


def get_total_costs(thermal_cost_df, voltage_cost_df):
    """This function combines voltage and thermal upgrades costs into one file.
    """
    total_cost_df = thermal_cost_df.append(voltage_cost_df)
    total_cost_df = total_cost_df.groupby('type').sum()
    total_cost_df.reset_index(inplace=True)
    return total_cost_df


if __name__ == "__main__":
    compute_all_costs()
