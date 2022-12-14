import os
import math
import logging
import pathlib

import numpy as np
import pandas as pd
import opendssdirect as dss

from .pydss_parameters import *
from jade.utils.timing_utils import track_timing, Timer

from disco import timer_stats_collector
from disco.enums import LoadMultiplierType
from disco.exceptions import (
    OpenDssCompileError,
    OpenDssConvergenceError,
    UpgradesExternalCatalogRequired,
    UpgradesExternalCatalogMissingObjectDefinition,
    InvalidOpenDssElementError,
)
from disco.models.upgrade_cost_analysis_generic_input_model import (
    _extract_specific_model_properties_, 
    LineCodeCatalogModel, LineGeometryCatalogModel,
    LineModel, LineCatalogModel,
    TransformerModel, TransformerCatalogModel,
)
from disco.models.upgrade_cost_analysis_generic_output_model import UpgradesCostResultSummaryModel, \
    CapacitorControllerResultType,  VoltageRegulatorResultType, EquipmentUpgradeStatusModel

logger = logging.getLogger(__name__)

DSS_XFMR_FLOAT_FIELDS = _extract_specific_model_properties_(model_name=TransformerModel, field_type_key="type", field_type_value="number")
DSS_XFMR_INT_FIELDS = _extract_specific_model_properties_(model_name=TransformerModel, field_type_key="type", field_type_value="integer")
DSS_LINE_FLOAT_FIELDS =  _extract_specific_model_properties_(model_name=LineModel, field_type_key="type", field_type_value="number")
DSS_LINE_INT_FIELDS = _extract_specific_model_properties_(model_name=LineModel, field_type_key="type", field_type_value="integer")
DSS_LINECODE_FLOAT_FIELDS =  _extract_specific_model_properties_(model_name=LineCodeCatalogModel, field_type_key="type", field_type_value="number")
DSS_LINECODE_INT_FIELDS =  _extract_specific_model_properties_(model_name=LineCodeCatalogModel, field_type_key="type", field_type_value="integer")
DSS_LINEGEOMETRY_FLOAT_FIELDS =  _extract_specific_model_properties_(model_name=LineGeometryCatalogModel, field_type_key="type", field_type_value="number")
DSS_LINEGEOMETRY_INT_FIELDS =  _extract_specific_model_properties_(model_name=LineGeometryCatalogModel, field_type_key="type", field_type_value="integer")
DSS_UNIT_CONFIG = {1: "mi", 2: "kft", 3: "m", 4: "Ft", 5: "in", 6: "cm",
                    0: "none"  # 0 maps to none, which means impedance units and line length units match
                    }

@track_timing(timer_stats_collector)
def reload_dss_circuit(dss_file_list, commands_list=None,  **kwargs):
    """This function clears the circuit and loads dss files and commands.
    Also solves the circuit and checks for convergence errors

    Parameters
    ----------
    dss_file_list
    commands_list

    Returns
    -------

    """
    logger.info("Reloading OpenDSS circuit")
    check_dss_run_command("clear")
    if dss_file_list is None:
        raise Exception("No OpenDSS files have been passed to be loaded.")
    for dss_file in dss_file_list:
        logger.info(f"Redirecting '{dss_file}'.")
        check_dss_run_command(f"Redirect '{dss_file}'")
    dc_ac_ratio = kwargs.get('dc_ac_ratio', None)
    if dc_ac_ratio is not None:
        change_pv_pctpmpp(dc_ac_ratio=dc_ac_ratio)
    if commands_list is not None:
        logger.info(f"Running {len(commands_list)} dss commands")
        for command_string in commands_list:
            check_dss_run_command(command_string)
            if "new " in command_string.lower():
                check_dss_run_command("CalcVoltageBases")
    enable_pydss_solve = kwargs.get("enable_pydss_solve", False)
    raise_exception = kwargs.get("raise_exception", True)
    if enable_pydss_solve:
        pydss_params = define_initial_pydss_settings(**kwargs)
        circuit_solve_and_check(raise_exception=raise_exception, **pydss_params)
        return pydss_params
    else:
        max_control_iterations = kwargs.get("max_control_iterations", None)
        if max_control_iterations is not None:
            dss.Solution.MaxControlIterations(max_control_iterations)
        circuit_solve_and_check(raise_exception=raise_exception)
        return kwargs


def run_selective_master_dss(master_filepath, **kwargs):
    """This function executes master.dss file line by line and ignores some commands that Solve yearly mode,
    export or plot data.

    Parameters
    ----------
    master_filepath

    Returns
    -------

    """
    run_dir = os.getcwd()
    check_dss_run_command("Clear")
    # logger.info("Redirecting master file:")
    # check_dss_run_command(f"Redirect {master_filepath}")

    # do this instead of redirect master to ignore some lines (e.g., that solve for the whole year)
    os.chdir(os.path.dirname(master_filepath))
    logger.debug(master_filepath)
    with open(master_filepath, "r") as fr:
        tlines = fr.readlines()
    for line in tlines:
        if ('Solve'.lower() in line.lower()) or ('Export'.lower() in line.lower()) or ('Plot'.lower() in line.lower()):
            logger.info(f"Skipping this line: {line}")
            continue
        else:
            check_dss_run_command(f"{line}")
    circuit_solve_and_check(raise_exception=True, **kwargs)
    os.chdir(run_dir)
    return


@track_timing(timer_stats_collector)
def circuit_solve_and_check(raise_exception=False, **kwargs):
    """This function solves the circuit (both OpenDSS and PyDSS-if enabled)
    and can raise exception if convergence error occurs

    Parameters
    ----------
    raise_exception
    kwargs

    Returns
    -------

    """
    calcvoltagebases = kwargs.pop("calcvoltagebases", False)
    if calcvoltagebases:
        check_dss_run_command("CalcVoltageBases")
    dss_pass_flag = dss_solve_and_check(raise_exception=raise_exception)
    pass_flag = dss_pass_flag
    enable_pydss_solve = kwargs.get("enable_pydss_solve", False)
    if enable_pydss_solve:  # if pydss solver is also to be used
        pydss_pass_flag = pydss_solve_and_check(raise_exception=raise_exception, **kwargs)
        pass_flag = dss_pass_flag and pydss_pass_flag
    return pass_flag


def dss_solve_and_check(raise_exception=False):
    """This function solves OpenDSS and returns bool flag which shows if it has converged or not.

    Parameters
    ----------
    raise_exception

    Returns
    -------
    bool
    """
    dss.Solution.Solve()
    logger.debug("Solving circuit using OpenDSS")
    # check_dss_run_command('CalcVoltageBases')
    dss_pass_flag = dss.Solution.Converged()
    if not dss_pass_flag:
        logger.info(f"OpenDSS Convergence Error")
        if raise_exception:
            raise OpenDssConvergenceError("OpenDSS solution did not converge")
    return dss_pass_flag


def dss_run_command_list(command_list):
    for command_string in command_list:
        check_dss_run_command(command_string)
    return


def write_text_file(string_list, text_file_path, **kwargs):
    """This function writes the string contents of a list to a text file

    Parameters
    ----------
    string_list
    text_file_path

    Returns
    -------

    """
    num_new_lines = kwargs.get("num_new_lines", 2)
    breaks = "\n"*num_new_lines
    pathlib.Path(text_file_path).write_text(breaks.join(string_list))


def create_upgraded_master_dss(dss_file_list, upgraded_master_dss_filepath, original_master_filename="master.dss"):
    """Function to create master dss with redirects to upgrades dss file.
    The redirect paths in this file are:
    * absolute path - to the original master dss file
    * relative path (relative to the upgraded_master dss file) if upgrades dss file"""
    command_list = []
    for filename in dss_file_list:
        if os.path.basename(filename) == original_master_filename:
            new_filename = _get_master_dss_filepath(filename, upgraded_master_dss_filepath)
        else:    
            new_filename = os.path.relpath(filename, os.path.dirname(upgraded_master_dss_filepath))
        command_list.append(f"Redirect {new_filename}")
    return command_list


def _get_master_dss_filepath(original_master, upgraded_master):
    if os.path.isabs(upgraded_master):
        # Here it is not possible to use a relative path in all cases.
        # The runtime output directory may have a different root than the source files.
        return os.path.abspath(original_master)

    return os.path.relpath(original_master, os.path.dirname(upgraded_master))


def create_dataframe_from_nested_dict(user_dict, index_names):
    """This function creates dataframe from a nested dictionary

    Parameters
    ----------
    user_dict
    index_names

    Returns
    -------
    DataFrame
    """
    df = pd.DataFrame.from_dict({(i, j): user_dict[i][j]
                                 for i in user_dict.keys()
                                 for j in user_dict[i].keys()},
                                orient='index')
    df.index.names = index_names
    return df.reset_index()


def get_dictionary_of_duplicates(df, subset, index_field):
    """This creates a mapping dictionary of duplicate indices in a dataframe

    Parameters
    ----------
    df
    subset
    index_field

    Returns
    -------
    Dictionary
    """
    df.set_index(index_field, inplace=True)
    df = df[df.duplicated(keep=False, subset=subset)]
    tuple_list = df.groupby(subset).apply(lambda x: tuple(x.index)).tolist()
    mapping_dict = {v: tup[0] for tup in tuple_list for v in tup}
    return mapping_dict


def convert_length_units(length, unit_in, unit_out):
    """Length unit converter"""
    LENGTH_CONVERSION = {'mm': 0.001, 'cm': 0.01, 'm': 1.0, 'km': 1000., "mi": 1609.34, "kft": 304.8, 
          "ft": 0.3048,  "in": 0.0254,}
    return length*LENGTH_CONVERSION[unit_in]/LENGTH_CONVERSION[unit_out]


def get_scenario_name(enable_pydss_solve, pydss_volt_var_model):
    """This function determines the controller scenario 

    Parameters
    ----------
    enable_pydss_solve : bool
    pydss_volt_var_model 

    Returns
    -------
    str
    """
    if enable_pydss_solve:
        # scenario = pydss_volt_var_model.control1  # TODO can read in name instead
        scenario = "control_mode"
    else:
        scenario = "pf1"
    return scenario


def convert_dict_nan_to_none(temp):
    """Convert np.nan in dictionary to None.
    This does change the data type of the field."""
    for key, value in temp.items():
        if isinstance(value, dict):
            df = pd.DataFrame([value])
            if df.isna().values.any():
                df = df.astype(object).where(df.notna(), None)  # replace NaN with None
                value = df.to_dict() 
            else:
                continue
        elif isinstance(value, list) and bool(value) and isinstance(value[0], dict):  # list of dicts
            df = pd.DataFrame(value)
            if df.isna().values.any():
                df = df.astype(object).where(df.notna(), None)  # replace NaN with None
                value = df.to_dict(orient="records")          
            else:
                continue  
        temp[key] = value
    return temp


@track_timing(timer_stats_collector)
def change_pv_pctpmpp(dc_ac_ratio):
    """This function changes PV system pctpmpp based on passed dc-ac ratio
    newpctpmpp = oldpctpmpp / dc_ac_ratio
    """
    dss.PVsystems.First()
    for i in range(dss.PVsystems.Count()):
        newpctpmpp = int(dss.Properties.Value('%Pmpp')) / dc_ac_ratio
        command_string = f"Edit PVSystem.{dss.PVsystems.Name()} %Pmpp={newpctpmpp}"
        check_dss_run_command(command_string)
        dss.PVsystems.Next()


def get_feeder_stats(dss):
    """This function gives metadata stats for a feeder 

    Parameters
    ----------
    dss

    Returns
    -------
    dict
    """
    load_kw = 0
    load_kVABase = 0
    pv_kw = 0
    pv_kVARated = 0
    
    load_df = dss.utils.loads_to_dataframe()
    if len(load_df) > 0:
        load_kw = load_df['kW'].sum()
        load_kVABase = load_df['kVABase'].sum()
    if dss.PVsystems.Count() > 0:
        pv_df = dss.utils.pvsystems_to_dataframe()
        pv_kw = pv_df['kW'].sum()
        pv_kVARated = pv_df['kVARated'].sum()
    data_dict = {
    'total_load(kVABase)': load_kVABase,
    'total_load(kW)': load_kw,
    'total_PV(kW)': pv_kw,
    'total_PV(kVARated)': pv_kVARated,
    }
    return data_dict


def get_upgrade_stage_stats(dss, upgrade_stage, upgrade_type, xfmr_loading_df, line_loading_df, bus_voltages_df, **kwargs):
    """This function gives upgrade stage stats for a feeder 
    upgrade_stage can be Initial or Final
    upgrade_type can be thermal or voltage
    
    """
    final_dict = {"stage": upgrade_stage, "upgrade_type": upgrade_type}
    ckt_info_dict = get_circuit_info()
    final_dict["feeder_components"] = ckt_info_dict
    final_dict["feeder_components"].update({
                                        "num_nodes": dss.Circuit.NumNodes(),
                                        "num_loads": dss.Loads.Count(),
                                        "num_lines": dss.Lines.Count(),
                                        "num_transformers": dss.Transformers.Count(),
                                        "num_pv_systems": dss.PVsystems.Count(),
                                        "num_capacitors": dss.Capacitors.Count(),
                                        "num_regulators": dss.RegControls.Count(),
                                        } )
    equipment_dict = combine_equipment_health_stats(xfmr_loading_df, line_loading_df, bus_voltages_df, **kwargs)
    final_dict.update(equipment_dict)
    return final_dict


def combine_equipment_health_stats(xfmr_loading_df, line_loading_df, bus_voltages_df, **kwargs):
    line_properties = kwargs.get("line_properties", 
                                 ['name', 'phases','normamps', 'kV', 'line_placement',  'length', 'units', 'max_amp_loading', 
                                  'max_per_unit_loading', 'status'])
    xfmr_properties = kwargs.get("xfmr_properties", 
                                 ['name', 'phases', 'windings', 'conns', 'kV', 'kVA', 'amp_limit_per_phase','max_amp_loading', 
                                  'max_per_unit_loading', 'status']  )
    voltage_properties = kwargs.get("voltage_properties", 
                                    ['name', 'max_per_unit_voltage', 'min_per_unit_voltage',  'overvoltage_violation', 
                                     'max_voltage_deviation', 'undervoltage_violation', 'min_voltage_deviation'])
    capacitors_df = kwargs.get("capacitors_df", pd.DataFrame())
    regcontrols_df = kwargs.get("regcontrols_df", pd.DataFrame())
    capacitor_properties = kwargs.get("capacitor_properties", 
                                      ['capacitor_name','capcontrol_present',  'capcontrol_type', 'capcontrol_name', 'kv', 'kvar',
                                       'phases', 'DeadTime', 'Delay', 'OFFsetting', 'ONsetting'])
    regcontrol_properties = kwargs.get("regcontrol_properties", 
                                       ['name', 'transformer', 'vreg', 'band', 'ptratio', 'delay', 'at_substation_xfmr_flag'])
    
    final_dict = {}
    # some file reformatting
    if "windings" in xfmr_properties:
        xfmr_loading_df["windings"] = xfmr_loading_df["windings"].astype(int)
    final_dict.update({"transformer": xfmr_loading_df[xfmr_properties].to_dict(orient="records")})
    final_dict.update({"line": line_loading_df[line_properties].to_dict(orient="records")})
    final_dict.update({"bus_voltage": bus_voltages_df[voltage_properties].to_dict(orient="records")})
    if not capacitors_df.empty :
        final_dict.update({"capacitor_control": capacitors_df[capacitor_properties].to_dict(orient="records")})
    else :
        final_dict.update({"capacitor_control": []})
    if not regcontrols_df.empty:
        final_dict.update({"regulator_control": regcontrols_df[regcontrol_properties].to_dict(orient="records")})
    else:
        final_dict.update({"regulator_control": []})
    return final_dict


def get_circuit_info():
    """This collects circuit information: source bus, feeder head info, substation xfmr information

    Returns
    -------
    Dictionary
    """
    data_dict = {}
    dss.Vsources.First()
    data_dict['source_bus'] = dss.CktElement.BusNames()[0].split(".")[0]
    data_dict["feeder_head_name"] = dss.Circuit.Name()
    dss.Circuit.SetActiveBus(data_dict['source_bus'])
    data_dict["feeder_head_basekv"] = dss.Bus.kVBase()
    data_dict["source_num_nodes"] = dss.Bus.NumNodes()
    data_dict["total_num_buses_in_circuit"] = len(dss.Circuit.AllBusNames())
    if data_dict["source_num_nodes"] > 1:
        data_dict["feeder_head_basekv"] = round(data_dict["feeder_head_basekv"] * math.sqrt(3), 1)
    data_dict["substation_xfmr"] = None

    all_xfmr_df = get_thermal_equipment_info(compute_loading=False, equipment_type="transformer")
    all_xfmr_df["substation_xfmr_flag"] = all_xfmr_df.apply(lambda x: int(
        data_dict["source_bus"].lower() in x['bus_names_only']), axis=1)
    if len(all_xfmr_df.loc[all_xfmr_df["substation_xfmr_flag"] == True]) > 0:
        data_dict["substation_xfmr"] = all_xfmr_df.loc[all_xfmr_df["substation_xfmr_flag"] ==
                                                       True].to_dict(orient='records')[0]
        # this checks if the voltage kVs are the same for the substation transformer
        data_dict["substation_xfmr"]["is_autotransformer_flag"] = len(set(data_dict["substation_xfmr"]["kVs"])) <= 1
    return data_dict


def summarize_upgrades_outputs(overall_outputs, **kwargs):
    """This function creates summary of upgrades and costs results"""
    summary = {"results": {}}
    summary["results"]["name"] = kwargs.get("job_name", None)
    violation_summary = pd.DataFrame(overall_outputs["violation_summary"])
    thermal_violations = sum(violation_summary.loc[(violation_summary["stage"] == "final") & (violation_summary["upgrade_type"] == "thermal")][["num_line_violations", "num_transformer_violations"]].sum())
    voltage_violations = sum(violation_summary.loc[(violation_summary["stage"] == "final") & (violation_summary["upgrade_type"] == "voltage")][["num_voltage_violation_buses"]].sum())
    summary["results"]["num_violations"] = thermal_violations + voltage_violations
    if overall_outputs["costs_per_equipment"]:
        summary["results"]["total_cost_usd"] = pd.DataFrame(overall_outputs["costs_per_equipment"])["total_cost_usd"].sum()
    else:
        summary["results"]["total_cost_usd"] = 0
    return summary


def create_thermal_output_summary(all_original_equipment, all_latest_equipment, thermal_equipment_type_list,
                                    props_dict, thermal_cost_df, upgrades_dict, output_cols):
    """This function creates the thermal output summary file"""
    new_thermal_df = pd.DataFrame(columns=output_cols)
    for equipment_type in thermal_equipment_type_list:
        latest_equipment_df = pd.DataFrame(all_latest_equipment[equipment_type])
        latest_equipment_df = latest_equipment_df.rename(columns={props_dict[equipment_type]["identifier"]: "equipment_name"})
        original_equipment_df = pd.DataFrame(all_original_equipment[equipment_type])
        original_equipment_df = original_equipment_df.rename(columns={props_dict[equipment_type]["identifier"]: "equipment_name"})
        temp_upgrade_df = upgrades_dict[equipment_type]
        temp_upgrade_df = temp_upgrade_df.rename(columns={"final_equipment_name": "equipment_name"})
        if (temp_upgrade_df.empty) and (original_equipment_df.empty):  # if there are no equipment for voltage controls
            continue 
        new_df = latest_equipment_df.copy(deep=True)
        new_df = pd.concat([new_df, pd.DataFrame(columns=list(set(output_cols)-set(new_df.columns)))], axis=1)
        new_df["equipment_type"] = equipment_type
        new_df["total_cost_usd"] = 0
        new_df["status"] = EquipmentUpgradeStatusModel.unchanged.value
        
        if not temp_upgrade_df.empty:
            temp_cost_df = thermal_cost_df.loc[thermal_cost_df.type.str.lower() == equipment_type.lower()]
            temp_cost_df = temp_cost_df.rename(columns={"final_equipment_name": "equipment_name"})
            replaced = list(temp_upgrade_df.loc[temp_upgrade_df["upgrade_type"]=="upgrade"]["equipment_name"].unique())  # list of replaced equipment
            new = list(temp_upgrade_df.loc[temp_upgrade_df["upgrade_type"]=="new_parallel"]["equipment_name"].unique())  # list of new equipment
            # add upgrade status
            new_df.loc[new_df.equipment_name.isin(replaced), "status"] = EquipmentUpgradeStatusModel.replaced.value
            new_df.loc[new_df.equipment_name.isin(new), "status"] = EquipmentUpgradeStatusModel.new.value
            # add cost
            temp_cost_df.set_index("equipment_name", inplace=True)
            new_df.set_index("equipment_name", inplace=True)
            new_df.loc[new_df.index.isin(temp_cost_df.index), "total_cost_usd"] = temp_cost_df.total_cost_usd
        else:
            new = []
            replaced = []
        parameter_list = props_dict[equipment_type]["parameter_list"]
        original_equipment_df.set_index("equipment_name", inplace=True)
        for i in range(0, len(parameter_list)):
            new_df[f"parameter{i+1}_name"] = parameter_list[i]
            new_df[f"parameter{i+1}_original"] = new_df[parameter_list[i]]
            new_df[f"parameter{i+1}_upgraded"] = new_df[parameter_list[i]]
            new_df.loc[new_df.index.isin(new), f"parameter{i+1}_original"] = None # new equipment original rating is None
            new_df.loc[new_df.index.isin(replaced), f"parameter{i+1}_original"] = original_equipment_df.loc[original_equipment_df.index.isin(replaced)][parameter_list[i]]
    
        new_df.reset_index(inplace=True)
        new_df = new_df[output_cols]
        new_thermal_df = pd.concat([new_thermal_df, new_df])
    new_thermal_df = new_thermal_df.replace({np.NaN: None})
    return new_thermal_df


def create_capacitor_output_summary(temp_upgrade_df, temp_cost_df, latest_equipment_df, output_cols, equipment_type):
    # create new dataframe
    new_df = latest_equipment_df.copy(deep=True)
    new_df = pd.concat([new_df, pd.DataFrame(columns=list(set(output_cols)-set(new_df.columns)))], axis=1)
    new_df["equipment_type"] = equipment_type
    new_df["total_cost_usd"] = 0
    new_df["status"] = EquipmentUpgradeStatusModel.unchanged.value
    
    if temp_upgrade_df.empty:  # if there are no upgrades of this equipment type
        return new_df, [], []
    
    new = list(temp_upgrade_df.loc[temp_upgrade_df["new_controller_added"]]["equipment_name"].unique())  # list of new equipment
    setting_changed = list(temp_upgrade_df.loc[temp_upgrade_df["controller_settings_modified"]]["equipment_name"].unique())  # list of setting_changed equipment
    # get unit cost
    unit_cost_calc = temp_cost_df.loc[temp_cost_df.type == CapacitorControllerResultType.change_cap_control.value]
    if not unit_cost_calc.empty:
        setting_changed_unit_cost = (unit_cost_calc["total_cost_usd"] / unit_cost_calc["count"]).values[0]
    else: 
        setting_changed_unit_cost = 0
    unit_cost_calc = temp_cost_df.loc[temp_cost_df.type == CapacitorControllerResultType.add_new_cap_controller.value]
    if not unit_cost_calc.empty:
        add_new_unit_cost = (unit_cost_calc["total_cost_usd"] / unit_cost_calc["count"]).values[0]
    else:
        add_new_unit_cost = 0
    # add upgrade status and cost
    new_df.loc[new_df.equipment_name.isin(setting_changed), "status"] = EquipmentUpgradeStatusModel.setting_changed.value
    new_df.loc[new_df.equipment_name.isin(setting_changed), "total_cost_usd"] = setting_changed_unit_cost
    new_df.loc[new_df.equipment_name.isin(new), "status"] = EquipmentUpgradeStatusModel.new.value
    new_df.loc[new_df.equipment_name.isin(new), "total_cost_usd"] = add_new_unit_cost
    return new_df, new, setting_changed 


def create_regulator_output_summary(temp_upgrade_df, temp_cost_df, latest_equipment_df, output_cols, equipment_type):    
    # create new dataframe
    new_df = latest_equipment_df.copy(deep=True)
    new_df = pd.concat([new_df, pd.DataFrame(columns=list(set(output_cols)-set(new_df.columns)))], axis=1)
    new_df["equipment_type"] = equipment_type
    new_df["total_cost_usd"] = 0
    new_df["status"] = EquipmentUpgradeStatusModel.unchanged.value
    if temp_upgrade_df.empty:  # if there are no upgrades of this equipment type
        return new_df, [], []
    
    new = list(temp_upgrade_df.loc[temp_upgrade_df["new_controller_added"]]["equipment_name"].unique())  # list of new equipment
    setting_changed = list(temp_upgrade_df.loc[temp_upgrade_df["controller_settings_modified"]]["equipment_name"].unique())  # list of setting_changed equipment
    # get unit cost            
    unit_cost_calc = temp_cost_df.loc[temp_cost_df.type == VoltageRegulatorResultType.add_new_reg_control.value]
    if not unit_cost_calc.empty:
        new_vreg_unit_cost = (unit_cost_calc["total_cost_usd"] / unit_cost_calc["count"]).values[0]
        new_df.loc[(new_df.equipment_name.isin(new)) & (new_df.at_substation_xfmr_flag == False), "total_cost_usd"] = new_vreg_unit_cost
    unit_cost_calc = temp_cost_df.loc[temp_cost_df.type == VoltageRegulatorResultType.change_reg_control.value]
    if not unit_cost_calc.empty:
        vreg_setting_changed_unit_cost = (unit_cost_calc["total_cost_usd"] / unit_cost_calc["count"]).values[0]
        new_df.loc[(new_df.equipment_name.isin(setting_changed)) & (new_df.at_substation_xfmr_flag == False), "total_cost_usd"] = vreg_setting_changed_unit_cost
    unit_cost_calc = temp_cost_df.loc[temp_cost_df.type == VoltageRegulatorResultType.add_substation_ltc.value]
    if not unit_cost_calc.empty:
        new_ltc_unit_cost = (unit_cost_calc["total_cost_usd"] / unit_cost_calc["count"]).values[0]
        new_df.loc[(new_df.equipment_name.isin(new)) & (new_df.at_substation_xfmr_flag), "total_cost_usd"] = new_ltc_unit_cost
    unit_cost_calc = temp_cost_df.loc[temp_cost_df.type == VoltageRegulatorResultType.change_ltc_control.value]
    if not unit_cost_calc.empty:
        ltc_setting_changed_unit_cost = (unit_cost_calc["total_cost_usd"] / unit_cost_calc["count"]).values[0]
        new_df.loc[(new_df.equipment_name.isin(setting_changed)) & (new_df.at_substation_xfmr_flag), "total_cost_usd"] = ltc_setting_changed_unit_cost
    # add upgrade status
    new_df.loc[new_df.equipment_name.isin(setting_changed), "status"] = EquipmentUpgradeStatusModel.setting_changed.value
    new_df.loc[new_df.equipment_name.isin(new), "status"] = EquipmentUpgradeStatusModel.new.value
    return new_df, new, setting_changed 


def create_voltage_output_summary(all_original_equipment, all_latest_equipment, voltage_equipment_type_list,
                                    props_dict, voltage_cost_df, upgrades_dict, output_cols):
    # VOLTAGE EQUIPMENT
    voltage_upgrade_df = upgrades_dict["voltage"]
    voltage_upgrade_df = voltage_upgrade_df.rename(columns={"final_equipment_name": "equipment_name"})
    new_voltage_df = pd.DataFrame(columns=output_cols)
    
    for equipment_type in voltage_equipment_type_list:
        latest_equipment_df = pd.DataFrame(all_latest_equipment[equipment_type])
        latest_equipment_df = latest_equipment_df.rename(columns={props_dict[equipment_type]["identifier"]: "equipment_name"})
        original_equipment_df = pd.DataFrame(all_original_equipment[equipment_type])
        original_equipment_df = original_equipment_df.rename(columns={props_dict[equipment_type]["identifier"]: "equipment_name"})
        if (voltage_upgrade_df.empty) and (original_equipment_df.empty):  # if there are no equipment for voltage controls
            continue 
        if not voltage_upgrade_df.empty:  # if there are voltage upgrades, extract for this equipment type
            temp_cost_df = voltage_cost_df.loc[voltage_cost_df.type.isin(props_dict[equipment_type]["model"].list_values())]
            temp_upgrade_df = voltage_upgrade_df.loc[voltage_upgrade_df.equipment_type.str.lower() == props_dict[equipment_type]["upgrades_file_string"].lower()]
        else:
            temp_upgrade_df = pd.DataFrame(columns=voltage_upgrade_df.columns)
            temp_cost_df = pd.DataFrame(columns=voltage_cost_df.columns)
        temp_upgrade_df = temp_upgrade_df.rename(columns={"name": "equipment_name"}) 
        temp_cost_df = temp_cost_df.rename(columns={"final_equipment_name": "equipment_name"})
        if equipment_type == "capacitor_control":
            new_df, new, setting_changed = create_capacitor_output_summary(temp_upgrade_df, temp_cost_df, latest_equipment_df, output_cols, equipment_type)
        elif equipment_type == "regulator_control":
            new_df, new, setting_changed  = create_regulator_output_summary(temp_upgrade_df, temp_cost_df, latest_equipment_df, output_cols, equipment_type)
        if new_df.empty:  # if there are no equipment of this type
            continue            
        new_df.set_index("equipment_name", inplace=True)
        parameter_list = props_dict[equipment_type]["parameter_list"]
        if not original_equipment_df.empty:
            original_equipment_df.set_index("equipment_name", inplace=True)
        for i in range(0, len(parameter_list)):
            new_df[f"parameter{i+1}_name"] = parameter_list[i].lower()
            new_df[f"parameter{i+1}_original"] = new_df[parameter_list[i]]
            new_df[f"parameter{i+1}_upgraded"] = new_df[parameter_list[i]]
            new_df.loc[new_df.index.isin(new), f"parameter{i+1}_original"] = None # new equipment original rating is None
            if not original_equipment_df.empty:
                new_df.loc[new_df.index.isin(setting_changed), f"parameter{i+1}_original"] = original_equipment_df.loc[original_equipment_df.index.isin(setting_changed)][parameter_list[i]]
        new_df.reset_index(inplace=True)
        new_df = new_df[output_cols]
        new_voltage_df = pd.concat([new_voltage_df, new_df])
    return new_voltage_df


def create_overall_output_file(feeder_stats, upgrades_dict, costs_dict, **kwargs):
    """This function creates the overall output summary file
    Status can have values: unchanged, replaced, new, setting_changed
    """
    output_cols = UpgradesCostResultSummaryModel.schema(True).get("properties").keys()
    thermal_equipment_type_list = kwargs.get("thermal_equipment_type_list", ["transformer", "line"])
    voltage_equipment_type_list = kwargs.get("voltage_equipment_type_list", ["capacitor_control", "regulator_control"])
    props_dict = {"transformer": {"identifier": "name", "parameter_list": ["kVA"], },
                 "line": {"identifier": "name", "parameter_list": ["normamps"], },
                 "capacitor_control": {"identifier": "capacitor_name", "parameter_list": ["ONsetting", "OFFsetting", "Delay"], "upgrades_file_string": "capacitor", 
                                       "model": CapacitorControllerResultType},
                 "regulator_control": {"identifier": "name", "parameter_list": ["vreg", "band", "delay"], "upgrades_file_string": "regcontrol", 
                                       "model": VoltageRegulatorResultType}, 
    }
    thermal_cost_df = costs_dict["thermal"]
    thermal_cost_df = pd.concat([thermal_cost_df.drop(['equipment_parameters'], axis=1), thermal_cost_df['equipment_parameters'].apply(pd.Series)], axis=1)
    voltage_cost_df = costs_dict["voltage"]
    
    output_file = []
    for stage_item in feeder_stats["stage_results"]:
        if (stage_item["stage"].lower() == "initial") and (stage_item["upgrade_type"].lower() == "thermal"):
            all_original_equipment = stage_item
        if (stage_item["stage"].lower() == "final") and (stage_item["upgrade_type"].lower() == "voltage"):
            all_latest_equipment = stage_item
    
    thermal_summary_df = create_thermal_output_summary(all_original_equipment, all_latest_equipment, thermal_equipment_type_list,
                                                        props_dict, thermal_cost_df, upgrades_dict, output_cols)
    
    voltage_summary_df = create_voltage_output_summary(all_original_equipment, all_latest_equipment, voltage_equipment_type_list,
                                                        props_dict, voltage_cost_df, upgrades_dict, output_cols)
    combined_df = pd.concat([thermal_summary_df, voltage_summary_df])
    combined_df["name"] = kwargs.get("job_name", None)
    return combined_df


def create_opendss_definition(config_definition_dict, action_type="New", property_list=None):
    """This function creates an opendss element definition for any generic equipment

    Returns
    -------
    str
    """
    command_string = f"{action_type} {config_definition_dict['equipment_type']}.{config_definition_dict['name']}"
    logger.debug(f"New {config_definition_dict['equipment_type']}.{config_definition_dict['name']} being defined")
    # these properties contain data (refer OpenDSS manual for more information on these parameters)
    if property_list is None:
        property_list = list(set(config_definition_dict.keys()) - {"name", "equipment_type"})
    empty_field_values = ["----", "nan", "NaN", "None", None, np.nan]
    for property_name in property_list:
        if isinstance(config_definition_dict[property_name], float):
            if np.isnan(config_definition_dict[property_name]):
                continue
        if config_definition_dict[property_name] in empty_field_values:
            continue
        # if the value is not empty and is not nan, only then add it into the command string
        temp_s = f" {property_name}={config_definition_dict[property_name]}"
        command_string = command_string + temp_s
    return command_string


def ensure_line_config_exists(chosen_option, new_config_type, external_upgrades_technical_catalog): 
    """This function check if a line config exists in the network. 
    If it doesn't exist, it checks the external catalog (if available) and returns a new dss definition string.
    
    Returns
    -------
    str
    """
    existing_config_dict = {"linecode": get_line_code(), "geometry": get_line_geometry()}
    new_config_name = chosen_option[new_config_type].lower()
    # if there are no existing config definitions
    if existing_config_dict[new_config_type].empty:
        command_string = add_new_lineconfig_definition(chosen_option, new_config_type, external_upgrades_technical_catalog)
    else:
        # if linecode or linegeometry is not present in existing network definitions
        if not existing_config_dict[new_config_type]["name"].str.lower().isin([new_config_name]).any():  
            command_string = add_new_lineconfig_definition(chosen_option, new_config_type, external_upgrades_technical_catalog)
        else:
            command_string = None   
    return command_string


def add_new_lineconfig_definition(chosen_option, new_config_type, external_upgrades_technical_catalog):
    # add definition for linecode or linegeometry
    if external_upgrades_technical_catalog is None:
        raise UpgradesExternalCatalogRequired(f"External upgrades technical catalog not available to determine line config type")
    if (new_config_type not in external_upgrades_technical_catalog):
        raise UpgradesExternalCatalogMissingObjectDefinition(
            f"{new_config_type} definitions not found in external catalog."
            f" Please check catalog, and add {new_config_type} definitions in it.")
    external_config_df = pd.DataFrame(external_upgrades_technical_catalog[new_config_type])
    if external_config_df.empty: 
        raise UpgradesExternalCatalogMissingObjectDefinition(
            f"{new_config_type} definitions not found in external catalog." 
            f" Please check catalog, and add {new_config_type} definitions in it.")
    new_config_name = chosen_option[new_config_type]
    if external_config_df["name"].str.lower().isin([new_config_name.lower()]).any():
        config_definition_df = external_config_df.loc[external_config_df["name"].str.lower() == new_config_name.lower()].copy()
        if len(config_definition_df) == 1:  # if there is only one definition of that config name
            config_definition_dict = dict(config_definition_df.iloc[0])  
        elif len(config_definition_df) > 1:   # if there is more than one definition of that config name
            config_definition_df["temp_deviation"] = abs(config_definition_df["normamps"] - chosen_option["normamps"])
            config_definition_dict = dict(config_definition_df.loc[config_definition_df["temp_deviation"].idxmin()])
            config_definition_dict.pop("temp_deviation")
        else:  # if definition not found
            raise UpgradesExternalCatalogMissingObjectDefinition(
                f"{new_config_name} definition of {new_config_type} type {new_config_type} not found in external catalog.")
        if config_definition_dict["normamps"] != chosen_option["normamps"]:
            logger.warning(f"Mismatch between noramps for linecode {new_config_name} ({config_definition_dict['normamps']}A) "
                            f"and chosen upgrade option normamps ({chosen_option['normamps']}A): {chosen_option['name']}")
        config_definition_dict["name"] = new_config_name  # to keep same case of config name (for consistency)
        # check format of certain fields, and prepare data to write opendss definition
        matrix_fields = [s for s in config_definition_dict.keys() if 'matrix' in s]
        for field in matrix_fields:
            config_definition_dict[field] = str(config_definition_dict[field]).replace("'","")
            config_definition_dict[field] = config_definition_dict[field].replace("[","(")
            config_definition_dict[field] = config_definition_dict[field].replace("]",")")
        config_definition_dict["equipment_type"] = new_config_type
        command_string = create_opendss_definition(config_definition_dict=config_definition_dict)
    else:
        raise UpgradesExternalCatalogMissingObjectDefinition(
            f"{new_config_type} definition for {new_config_name} not found in external catalog."
        )
    return command_string


def get_present_loading_condition():
    """ Get present loading condition for all loads
    
    Returns
    -------
    DataFrame
    """
    load_dict = {}
    dss.Circuit.SetActiveClass("Load")
    flag = dss.ActiveClass.First()

    while flag > 0:
        # Get the name of the load
        load_dict[dss.CktElement.Name()] = {
                                            'Num_phases': float(dss.Properties.Value("phases")),
                                            'kV': float(dss.Properties.Value("kV")),
                                            'kVA': float(dss.Properties.Value("kVA")),
                                            'kW': float(dss.Properties.Value("kW")),
                                            'pf': dss.Properties.Value("pf"),
                                            'Bus1': dss.Properties.Value("bus1"),
                                            'Powers': dss.CktElement.Powers(),
                                            'NetPower': sum(dss.CktElement.Powers()[::2]),
                                            }
        # Move on to the next Load...
        flag = dss.ActiveClass.Next()
    load_df = pd.DataFrame.from_dict(load_dict, "index")
    return load_df


def get_present_storage_condition():
    """ Get present operating condition for all storage
    
    Returns
    -------
    DataFrame
    """
    storage_dict = {}
    dss.Circuit.SetActiveClass('Storage')
    flag = dss.ActiveClass.First()
    while flag > 0:
        # Get the name of the load
        storage_dict[dss.CktElement.Name()] = {
            'Num_phases': float(dss.Properties.Value("phases")),
            'kV': float(dss.Properties.Value("kV")),
            'kVA': float(dss.Properties.Value("kVA")),
            'kW': float(dss.Properties.Value("kW")),
            'pf': dss.Properties.Value("pf"),
            'Bus1': dss.Properties.Value("bus1"),
            'Powers': dss.CktElement.Powers(),
            'NetPower': sum(dss.CktElement.Powers()[::2]),
        }
        # Move on to the next ...
        flag = dss.ActiveClass.Next()
    storage_df = pd.DataFrame.from_dict(storage_dict, "index")
    return storage_df


def get_present_pvgeneration():
    """ Get present generation for all pv systems
    
    Returns
    -------
    DataFrame
    """
    pv_dict = {}
    dss.Circuit.SetActiveClass("PVSystem")
    flag = dss.ActiveClass.First()
    while flag:
        pv_dict[dss.CktElement.Name()] = {
                                            'Num_phases': float(dss.Properties.Value("phases")),
                                            'kV': float(dss.Properties.Value("kV")),
                                            'kVA': float(dss.Properties.Value("kVA")),
                                            'kvar': float(dss.Properties.Value("kvar")),
                                            'Irradiance': float(dss.Properties.Value("Irradiance")),
                                            'connection': dss.Properties.Value("conn"),
                                            'Pmpp': float(dss.Properties.Value("Pmpp")),
                                            'Powers': dss.CktElement.Powers(),
                                            'NetPower': sum(dss.CktElement.Powers()[::2]),
                                            'pf': dss.Properties.Value("pf"),
                                            'Bus1': dss.Properties.Value("bus1"),
                                            'Voltages': dss.CktElement.Voltages(),
                                            'VoltagesMagAng': dss.CktElement.VoltagesMagAng(),
                                            'VoltagesMag': float(dss.CktElement.VoltagesMagAng()[0]),
                                            }
        flag = dss.ActiveClass.Next() > 0
    pv_df = pd.DataFrame.from_dict(pv_dict, "index")
    return pv_df
   

def check_enabled_property(all_df, element_name):
    """This function checks values for the "enabled" property of a dss object 
    """
    flag = any(ele.lower() in ["yes", "no"] for ele in all_df.enabled.unique())
    if not flag:
        raise OpenDssCompileError(f"Unexpected values {all_df.enabled.unique()} received for 'enabled' {element_name} "
                                  "property. Check OpenDSS version")
    return


def check_switch_property(all_df):
    """This function checks values for the "switch" property of line object 
    """
    flag = any(ele.lower() in ["yes", "no"] for ele in all_df.Switch.unique())
    if not flag:
        raise OpenDssCompileError(f"Unexpected values {all_df.Switch.unique()} received for 'Switch' line "
                                  "property. Check OpenDSS version")
    return


def get_all_transformer_info_instance(upper_limit=None, compute_loading=True):
    """This collects transformer information

    Returns
    -------
    DataFrame
    """
    all_df = dss.utils.class_to_dataframe("transformer")
    check_enabled_property(all_df, element_name="transformer")
    if len(all_df) == 0:
        return pd.DataFrame()
    all_df["name"] = all_df.index.str.split(".").str[1]
    all_df["equipment_type"] = all_df.index.str.split(".").str[0]
    # extract only enabled lines
    all_df = all_df.loc[all_df["enabled"].str.lower() == "yes"]
    all_df["conn"] = all_df["conn"].str.strip()  # remove trailing space from conn field
    # define empty new columns
    all_df['bus_names_only'] = None
    all_df["amp_limit_per_phase"] = np.nan
    all_df[DSS_XFMR_INT_FIELDS] = all_df[DSS_XFMR_INT_FIELDS].astype(int)
    all_df[DSS_XFMR_FLOAT_FIELDS] = all_df[DSS_XFMR_FLOAT_FIELDS].astype(float)
    if compute_loading:
        all_df["max_amp_loading"] = np.nan
        all_df["max_per_unit_loading"] = np.nan
        all_df["status"] = ""
    for index, row in all_df.iterrows():
        all_df.at[index, "kVs"] = [float(a) for a in row["kVs"]]
        all_df.at[index, "kVAs"] = [float(a) for a in row["kVAs"]]
        try:
            all_df.at[index, "Xscarray"] = [float(a) for a in row["Xscarray"]]  # before opendssdirect version 0.7.0
        except ValueError:
            all_df.at[index, "Xscarray"] = [float(a) for a in row["Xscarray"][0].split(" ")]  # in opendssdirect version 0.7.0
        all_df.at[index, "%Rs"] = [float(a) for a in row["%Rs"]]
        all_df.at[index, "taps"] = [float(a) for a in row["taps"]]
        all_df.at[index, "bus_names_only"] = [a.split(".")[0].lower() for a in row["buses"]]
        # first winding is considered primary winding
        primary_kv = float(row["kVs"][0])
        primary_kva = float(row["kVAs"][0])
        if row["phases"] > 1:
            amp_limit_per_phase = primary_kva / (primary_kv * math.sqrt(3))
        elif row["phases"] == 1:
            amp_limit_per_phase = primary_kva / primary_kv
        else:
            raise InvalidOpenDssElementError(f"Incorrect number of phases for transformer {row['name']}")
        all_df.at[index, "amp_limit_per_phase"] = amp_limit_per_phase
        if compute_loading:
            if upper_limit is None:
                raise Exception("Transformer upper limit is to be passed to function to compute transformer loading")
            dss.Circuit.SetActiveElement("Transformer.{}".format(row["name"]))
            extract_magang = dss.CktElement.CurrentsMagAng()[: 2 * row["phases"]]  # extract elements based on num of ph
            xfmr_current_magnitude = extract_magang[::2]
            max_amp_loading = max(xfmr_current_magnitude)
            max_per_unit_loading = round(max_amp_loading / amp_limit_per_phase, 4)
            all_df.at[index, "max_amp_loading"] = max_amp_loading
            all_df.at[index, "max_per_unit_loading"] = max_per_unit_loading
            if max_per_unit_loading > upper_limit:
                all_df.at[index, "status"] = "overloaded"
            elif max_per_unit_loading == 0:
                all_df.at[index, "status"] = "unloaded"
            else:
                all_df.at[index, "status"] = "normal"
    all_df = all_df.reset_index(drop=True).set_index('name')
    return all_df.reset_index()


def add_info_line_definition_type(all_df):
    all_df["line_definition_type"] = "line_definition"
    all_df.loc[all_df["linecode"] != "", "line_definition_type"] = "linecode"
    all_df.loc[all_df["geometry"] != "", "line_definition_type"] = "geometry"
    return all_df


def determine_line_placement(line_series):
    """ Distinguish between overhead and underground cables.
    Latest opendss version has property "LineType"
    line_placement is determined via:
    1. "LineType" property
    2. height property if defined as line geometry
    # line_placement determined via height takes precedence over linetype property
    # this is because if linetype property is not defined in opendss definition, then default: oh is assigned
    
    If line_placement is still not available, it is determined using presence of string "oh" or "ug" in name

    Parameters
    ----------
    line_series

    Returns
    -------
    dict
    """
    info_dict = {}
    info_dict["line_placement"] = None
    line_placement = None
    # use linetype property to determine line_placement
    if ("LineType" in line_series) and (line_series["LineType"] in ["oh", "ug"]):
        if line_series["LineType"] == "oh":
            linetype_placement = "overhead"
        else:
            linetype_placement = "underground"
    line_placement = linetype_placement
    if line_series["line_definition_type"] == "geometry":
        # use height property to determine line_placement
        dss.Circuit.SetActiveClass("linegeometry")
        dss.ActiveClass.Name(line_series["geometry"])
        h = float(dss.Properties.Value("h"))
        info_dict["h"] = 0
        if h >= 0:
            geom_placement = "overhead"
        else:
            geom_placement = "underground"
        # line_placement determined via height takes precedence over linetype property
        # this is because if linetype property is not defined in opendss definition, then default: oh is assigned
        if linetype_placement != geom_placement:
            line_placement = geom_placement 
    # if line_placement is still None, then use line name to determine line placement
    if line_placement is None:
        if ("oh" in line_series["geometry"].lower()) or ("oh" in line_series["linecode"].lower()) :
            line_placement = "overhead"
        elif ("ug" in line_series["geometry"].lower()) or ("ug" in line_series["linecode"].lower()):
            line_placement = "underground"
        else:
            line_placement = "overhead"  # default is taken as overhead
    info_dict["line_placement"] = line_placement
    return info_dict


def get_all_line_info_instance(upper_limit=None, compute_loading=True, ignore_switch=True):
    """This collects line information.
    
    dss.Lines.Units() gives an integer. It can be mapped as below:
    units_config = ["none", "mi", "kft", "km", "m", "Ft", "in", "cm"]  # Units key for lines taken from OpenDSS
    units_config[dss.Lines.Units() - 1]

    Returns
    -------
    DataFrame
    """
    all_df = dss.utils.class_to_dataframe("line")
    if len(all_df) == 0:
        return pd.DataFrame()
    check_enabled_property(all_df, element_name="line")
    all_df["name"] = all_df.index.str.split(".").str[1]
    all_df["equipment_type"] = all_df.index.str.split(".").str[0]
    # extract only enabled lines
    all_df = all_df.loc[all_df["enabled"].str.lower() == "yes"]
    all_df = add_info_line_definition_type(all_df)
    # define empty new columns
    all_df["kV"] = np.nan
    all_df["h"] = np.nan
    all_df["line_placement"] = ""
    all_df[DSS_LINE_INT_FIELDS] = all_df[DSS_LINE_INT_FIELDS].astype(int)
    all_df[DSS_LINE_FLOAT_FIELDS] = all_df[DSS_LINE_FLOAT_FIELDS].astype(float)
    if compute_loading:
        all_df["max_amp_loading"] = np.nan
        all_df["max_per_unit_loading"] = np.nan
        all_df["status"] = ""
    for index, row in all_df.iterrows():
        dss.Circuit.SetActiveBus(row["bus1"])
        kv_b1 = dss.Bus.kVBase()
        dss.Circuit.SetActiveBus(row["bus2"])
        kv_b2 = dss.Bus.kVBase()
        dss.Circuit.SetActiveElement("Line.{}".format(row["name"]))
        if round(kv_b1) != round(kv_b2):
            raise InvalidOpenDssElementError("To and from bus voltages ({} {}) do not match for line {}".format(
                kv_b2, kv_b1, row['name']))
        all_df.at[index, "kV"] = kv_b1
        # Distinguish between overhead and underground cables
        # currently there is no way to distinguish directy using opendssdirect/pydss etc.
        # It is done here using property 'height' parameter and if string present in name
        placement_dict = determine_line_placement(row)
        for key in placement_dict.keys():
            all_df.at[index, key] = placement_dict[key] 
        if row["units"] == "none":
            # possible unit values: {none | mi|kft|km|m|Ft|in|cm } Default is None - assumes length units match impedance units.
            # if units match, then it returns none: in this case, assign value from other lines present in dataframe
            if dss.Lines.Units() != 0:
                all_df.at[index, "units"] = DSS_UNIT_CONFIG[dss.Lines.Units()]
            else:
                def_unit = all_df.units.unique()[0]
                if def_unit != "none":
                    all_df.at[index, "units"] = def_unit
                else:
                    all_df.at[index, "units"] = "m"  # if a unit was not found, assign default of m
        # if line loading is to be computed
        if compute_loading:
            if upper_limit is None:
                raise Exception("Line upper limit is to be passed to function to compute line loading")
            dss.Circuit.SetActiveElement("Line.{}".format(row["name"]))
            extract_magang = dss.CktElement.CurrentsMagAng()[: 2 * row["phases"]]
            line_current = extract_magang[::2]
            max_amp_loading = max(line_current)
            max_per_unit_loading = round(max_amp_loading / row["normamps"], 4)
            all_df.at[index, "max_amp_loading"] = max_amp_loading
            all_df.at[index, "max_per_unit_loading"] = max_per_unit_loading
            if max_per_unit_loading > upper_limit:
                all_df.at[index, "status"] = "overloaded"
            elif max_per_unit_loading == 0:
                all_df.at[index, "status"] = "unloaded"
            else:
                all_df.at[index, "status"] = "normal"
    all_df = all_df.reset_index(drop=True).set_index('name')
    all_df["kV"] = all_df["kV"].round(5)
    # add units to switch length (needed to plot graph). By default, length of switch is taken as max
    check_switch_property(all_df)
    all_df.loc[(all_df.units == 'none') & (all_df.Switch.str.lower() == "yes"), 'units'] = 'm'
    # if switch is to be ignored
    if ignore_switch:
        all_df = all_df.loc[all_df['Switch'].str.lower() == "no"]
    return all_df.reset_index()


def compare_multiple_dataframes(comparison_dict, deciding_column_name, comparison_type="max"):
    """This function compares all dataframes in a given dictionary based on a deciding column name

    Returns
    -------
    Dataframe
    """
    summary_df = pd.DataFrame()
    for df_name in comparison_dict.keys():
        summary_df[df_name] = comparison_dict[df_name][deciding_column_name]
    if comparison_type == "max":
        label_df = summary_df.idxmax(axis=1)  # find dataframe name that has max 
    elif comparison_type == "min":
        label_df = summary_df.idxmax(axis=1)  # find dataframe name that has min 
    else:
        raise Exception(f"Unknown comparison type {comparison_type} passed.")
    final_list = []
    for index, label in label_df.items():  # index is element name
        temp_dict = dict(comparison_dict[label].loc[index])
        temp_dict.update({"name": index})
        final_list.append(temp_dict)
    final_df = pd.DataFrame(final_list)
    return final_df
        

@track_timing(timer_stats_collector)
def get_thermal_equipment_info(compute_loading, equipment_type, upper_limit=None, ignore_switch=False, **kwargs):
    """This function determines the thermal equipment loading (line, transformer), based on timepoint multiplier

    Returns
    -------
    DataFrame
    """
    timepoint_multipliers = kwargs.get("timepoint_multipliers", None)
    multiplier_type = kwargs.get("multiplier_type", LoadMultiplierType.ORIGINAL)
     # if there are no multipliers, run on rated load i.e. multiplier=1. 0
     # if compute_loading is false, then just run once (no need to check multipliers)
    if (timepoint_multipliers is None) or (not compute_loading) or (multiplier_type == LoadMultiplierType.ORIGINAL): 
        if compute_loading and multiplier_type != LoadMultiplierType.ORIGINAL:
            apply_uniform_timepoint_multipliers(multiplier_name=1, field="with_pv", **kwargs)
        if equipment_type == "line":
            loading_df = get_all_line_info_instance(compute_loading=compute_loading, upper_limit=upper_limit, ignore_switch=ignore_switch)
        elif equipment_type == "transformer":
            loading_df = get_all_transformer_info_instance(compute_loading=compute_loading, upper_limit=upper_limit)
        return loading_df
    if multiplier_type == LoadMultiplierType.UNIFORM:
        comparison_dict = {}
        for pv_field in timepoint_multipliers["load_multipliers"].keys():
            logger.debug(pv_field)
            for multiplier_name in timepoint_multipliers["load_multipliers"][pv_field]:
                logger.debug("Multipler name: %s", multiplier_name)
                # this changes the dss network load and pv
                apply_uniform_timepoint_multipliers(multiplier_name=multiplier_name, field=pv_field, **kwargs)
                if equipment_type.lower() == "line":
                    deciding_column_name = "max_per_unit_loading"
                    loading_df = get_all_line_info_instance(compute_loading=compute_loading, upper_limit=upper_limit, ignore_switch=ignore_switch)
                elif equipment_type.lower() == "transformer":
                    deciding_column_name = "max_per_unit_loading"
                    loading_df = get_all_transformer_info_instance(compute_loading=compute_loading, upper_limit=upper_limit)
                loading_df.set_index("name", inplace=True)
                comparison_dict[pv_field+"_"+str(multiplier_name)] = loading_df
        # compare all dataframe, and create one that contains all worst loading conditions (across all multiplier conditions)
        loading_df = compare_multiple_dataframes(comparison_dict, deciding_column_name, comparison_type="max")
    else:
        raise Exception(f"Undefined multiplier_type {multiplier_type} passed.")   
    return loading_df
    

def get_regcontrol_info(correct_PT_ratio=False, nominal_voltage=None):
    """This collects enabled regulator control information.
    If correcting PT ratio, the following information is followed (based on OpenDSS documentation)
    PT ratio: # If the winding is Wye, the line-to-neutral voltage is used. Else, the line-to-line voltage is used.
              # Here, bus kV is taken from Bus.kVBase
    
    Bus base kV:  Returns L-L voltages for 2- and 3-phase. Else for 1-ph, return L-N voltage

    Returns
    -------
    DataFrame
    """
    all_df = dss.utils.class_to_dataframe("regcontrol")
    if len(all_df) == 0:
        return pd.DataFrame()
    check_enabled_property(all_df, element_name="regcontrol")    
    all_df["name"] = all_df.index.str.split(".").str[1]
    all_df["equipment_type"] = all_df.index.str.split(".").str[0]
    float_columns = ['winding', 'vreg', 'band', 'ptratio', 'delay']
    all_df[float_columns] = all_df[float_columns].astype(float)
    all_df['at_substation_xfmr_flag'] = False  # by default, reg control is considered to be not at substation xfmr
    ckt_info_dict = get_circuit_info()
    sub_xfmr_present = False
    sub_xfmr_name = None
    if ckt_info_dict['substation_xfmr'] is not None:
        sub_xfmr_present = True
        sub_xfmr_name = ckt_info_dict['substation_xfmr']['name']
    if correct_PT_ratio:
        if nominal_voltage is None:
            raise Exception("Nominal voltage not provided to correct regcontrol PT ratio.")
        all_df['old_ptratio'] = all_df['ptratio']
        
    for index, row in all_df.iterrows():
        dss.Circuit.SetActiveElement("Regcontrol.{}".format(row["name"]))
        reg_bus = dss.CktElement.BusNames()[0].split(".")[0]
        all_df.at[index, "reg_bus"] = reg_bus
        dss.Circuit.SetActiveBus(reg_bus)
        all_df.at[index, "bus_num_phases"] = dss.CktElement.NumPhases()
        all_df.at[index, "bus_kv"] = dss.Bus.kVBase()
        dss.Circuit.SetActiveElement("Transformer.{}".format(row["transformer"]))
        all_df.at[index, "transformer_kva"] = float(dss.Properties.Value("kva"))
        dss.Transformers.Wdg(1)  # setting winding to 1, to get kV for winding 1
        all_df.at[index, "transformer_kv"] = dss.Transformers.kV()
        all_df.at[index, "transformer_conn"] = dss.Properties.Value("conn").strip()  # opendss returns conn with a space 
        all_df.at[index, "transformer_bus1"] = dss.CktElement.BusNames()[0].split(".")[0]
        all_df.at[index, "transformer_bus2"] = dss.CktElement.BusNames()[1].split(".")[0]
        if correct_PT_ratio:
            if (all_df.loc[index]["bus_num_phases"] > 1) and (all_df.loc[index]["transformer_conn"].lower() == "wye"):
                kV_to_be_used = all_df.loc[index]["transformer_kv"] * 1000 / math.sqrt(3)
            else:
                kV_to_be_used = all_df.loc[index]["transformer_kv"] * 1000
            # kV_to_be_used = dss.Bus.kVBase() * 1000
            all_df.at[index, "ptratio"] = kV_to_be_used / nominal_voltage
        if sub_xfmr_present and (row["transformer"] == sub_xfmr_name):  # if reg control is at substation xfmr
            all_df.at[index, 'at_substation_xfmr_flag'] = True
    all_df = all_df.reset_index(drop=True).set_index('name')        
    all_df = all_df.loc[all_df['enabled'].str.lower() == "yes"]
    return all_df.reset_index()


def get_capacitor_info(nominal_voltage=None, correct_PT_ratio=False):
    """
    This collects capacitor information.
    For correcting PT ratio, the following information and definitions are followed:
    # cap banks are 3 phase, 2 phase or 1 phase. 1 phase caps will have LN voltage
    # PT ratio: Ratio of the PT that converts the monitored voltage to the control voltage. 
    # If the capacitor is Wye, the 1st phase line-to-neutral voltage is monitored.
    # Else, the line-to-line voltage (1st - 2nd phase) is monitored.
    # Capacitor kv: Rated kV of the capacitor (not necessarily same as bus rating). 
    # For Phases=2 or Phases=3, it is line-to-line (phase-to-phase) rated voltage. 
    # For all other numbers of phases, it is actual rating. (For Delta connection this is always line-to-line rated voltage). 
    This function doesnt currently check if object is "enabled".
    
    Returns
    -------
    DataFrame
    """
    all_df = dss.utils.class_to_dataframe("capacitor")
    if len(all_df) == 0:
        return pd.DataFrame()
    check_enabled_property(all_df, element_name="capacitor")  
    all_df["capacitor_name"] = all_df.index.str.split(".").str[1]
    all_df["equipment_type"] = all_df.index.str.split(".").str[0]
    float_columns = ["phases", "kv"]
    all_df[float_columns] = all_df[float_columns].astype(float)
    all_df = all_df.reset_index(drop=True).set_index("capacitor_name")
    # collect capcontrol information to combine with capcontrols
    capcontrol_df = get_cap_control_info()
    capcontrol_df.rename(columns={'name': 'capcontrol_name', 'capacitor': 'capacitor_name', 'type': 'capcontrol_type',
                                  'equipment_type': 'capcontrol_present'}, inplace=True)
    capcontrol_df = capcontrol_df.set_index("capacitor_name")
    # with capacitor name as index, concatenate capacitor information with cap controls
    all_df = pd.concat([all_df, capcontrol_df], axis=1)
    all_df.index.name = 'capacitor_name'
    all_df = all_df.reset_index().set_index('capacitor_name')
    
    if correct_PT_ratio and (len(capcontrol_df) > 0):
        if nominal_voltage is None:
            raise Exception("Nominal voltage not provided to correct capacitor bank PT ratio.")
        all_df['old_PTratio'] = all_df['PTratio']
    
    # iterate over all capacitors
    for index, row in all_df.iterrows():
        all_df.at[index, "kvar"] = [float(a) for a in row["kvar"]][0]
        # if capcontrol type is empty, then that capacitor does not have controls
        # correct PT ratios for existing cap controls
        if correct_PT_ratio and (len(capcontrol_df) > 0):
            if row["phases"] > 1 and row["conn"].lower() == "wye":
                kv_to_be_used = (row['kv'] * 1000) / math.sqrt(3)
            else:
                kv_to_be_used = row['kv'] * 1000
            all_df.at[index, "PTratio"] = kv_to_be_used / nominal_voltage
    return all_df.reset_index()


def get_cap_control_info():
    """This collects capacitor control information

    Returns
    -------
    DataFrame
    """
    all_df = dss.utils.class_to_dataframe("capcontrol")
    if len(all_df) == 0:
        capcontrol_columns = ["name",  "equipment_type", "element", "terminal", "capacitor", 
                              "type", "PTratio", "CTratio", "ONsetting", "OFFsetting", "Delay", 
                              "VoltOverride", "Vmax", "Vmin", "DelayOFF", "DeadTime", "CTPhase", 
                              "PTPhase", "VBus", "EventLog", "UserModel", "UserData", "pctMinkvar", 
                              "Reset", "basefreq", "enabled", "like"]
        return pd.DataFrame(columns=capcontrol_columns)
    check_enabled_property(all_df, element_name="capcontrol")
    all_df["name"] = all_df.index.str.split(".").str[1]
    all_df["equipment_type"] = all_df.index.str.split(".").str[0]
    CAPCONTROL_FLOAT_FIELDS = ["CTratio", "DeadTime", "Delay", "DelayOFF", "OFFsetting", "ONsetting", "PTratio",
                              "Vmax", "Vmin"]
    all_df[CAPCONTROL_FLOAT_FIELDS] = all_df[CAPCONTROL_FLOAT_FIELDS].astype(float)
    all_df = all_df.reset_index(drop=True).set_index("name")
    return all_df.reset_index()


def get_line_geometry():
    """This collects all line geometry information

    Returns
    -------
    DataFrame
    """
    active_class_name = 'linegeometry'
    all_df = dss.utils.class_to_dataframe(active_class_name)
    if len(all_df) == 0:
        return pd.DataFrame()
    all_df['name'] = all_df.index.str.split('.').str[1]
    all_df['equipment_type'] = all_df.index.str.split('.').str[0]
    all_df.reset_index(inplace=True, drop=True)
    all_df[DSS_LINEGEOMETRY_FLOAT_FIELDS] = all_df[DSS_LINEGEOMETRY_FLOAT_FIELDS].astype("float")
    all_df[DSS_LINEGEOMETRY_INT_FIELDS] = all_df[DSS_LINEGEOMETRY_INT_FIELDS].astype("int")
    all_df = all_df[list(LineGeometryCatalogModel.schema(True).get("properties").keys())]
    return all_df


def get_line_code():
    """This collects all line codes information

    Returns
    -------
    DataFrame
    """
    active_class_name = 'linecode'
    all_df = dss.utils.class_to_dataframe(active_class_name)
    if len(all_df) == 0:
        return pd.DataFrame()
    all_df['name'] = all_df.index.str.split('.').str[1]
    all_df['equipment_type'] = all_df.index.str.split('.').str[0]
    all_df.reset_index(inplace=True, drop=True)
    all_df[DSS_LINECODE_FLOAT_FIELDS] = all_df[DSS_LINECODE_FLOAT_FIELDS].astype("float")
    all_df[DSS_LINECODE_INT_FIELDS] = all_df[DSS_LINECODE_INT_FIELDS].astype("int")
    all_df = all_df[list(LineCodeCatalogModel.schema(True).get("properties").keys())]
    return all_df


def get_wire_data():
    """This collects all wire data information

    Returns
    -------
    DataFrame
    """
    active_class_name = 'wiredata'
    all_df = dss.utils.class_to_dataframe(active_class_name)
    if len(all_df) == 0:
        return pd.DataFrame()
    all_df['name'] = all_df.index.str.split('.').str[1]
    all_df['equipment_type'] = all_df.index.str.split('.').str[0]
    all_df.reset_index(inplace=True, drop=True)
    return all_df


def get_cn_data():
    """This collects all cn data information

    Returns
    -------
    DataFrame
    """
    active_class_name = 'cndata'
    all_df = dss.utils.class_to_dataframe(active_class_name)
    if len(all_df) == 0:
        return pd.DataFrame()
    all_df['name'] = all_df.index.str.split('.').str[1]
    all_df['equipment_type'] = all_df.index.str.split('.').str[0]
    all_df.reset_index(inplace=True, drop=True)
    return all_df


def check_dss_run_command(command_string):
    """Runs dss command
    And checks for exception

    Parameters
    ----------
    command_string : str
        dss command to be run

    Raises
    -------
    OpenDssCompileError
        Raised if the command fails

    """
    logger.debug(f"Running DSS command: {command_string}")
    result = dss.Text.Command(f"{command_string}")
    if result is not None:
        raise OpenDssCompileError(f"OpenDSS run_command failed with message: {result}. \nCommand: {command_string}")


@track_timing(timer_stats_collector)
def get_bus_voltages(voltage_upper_limit, voltage_lower_limit, raise_exception=True, **kwargs):
    """This function determines the voltages, based on timepoint multiplier

    Returns
    -------
    DataFrame
    """
    timepoint_multipliers = kwargs.get("timepoint_multipliers", None)
    multiplier_type = kwargs.get("multiplier_type", LoadMultiplierType.ORIGINAL)
     # if there are no multipliers, run on rated load i.e. multiplier=1. 0
     # if compute_loading is false, then just run once (no need to check multipliers)
    if (timepoint_multipliers is None) or (multiplier_type == LoadMultiplierType.ORIGINAL): 
        if multiplier_type != LoadMultiplierType.ORIGINAL:
            apply_uniform_timepoint_multipliers(multiplier_name=1, field="with_pv", **kwargs)
            # determine voltage violations after changes
        bus_voltages_df, undervoltage_bus_list, overvoltage_bus_list, buses_with_violations = get_bus_voltages_instance(
            voltage_upper_limit=voltage_upper_limit, voltage_lower_limit=voltage_lower_limit, raise_exception=raise_exception, 
            **kwargs)
        return bus_voltages_df, undervoltage_bus_list, overvoltage_bus_list, buses_with_violations
    if multiplier_type == LoadMultiplierType.UNIFORM:
        comparison_dict = {}
        for pv_field in timepoint_multipliers["load_multipliers"].keys():
            logger.debug(pv_field)
            for multiplier_name in timepoint_multipliers["load_multipliers"][pv_field]:
                logger.debug("Multipler name: %s", multiplier_name)
                # this changes the dss network load and pv
                apply_uniform_timepoint_multipliers(multiplier_name=multiplier_name, field=pv_field, **kwargs)
                bus_voltages_df, undervoltage_bus_list, overvoltage_bus_list, buses_with_violations = get_bus_voltages_instance(
                    voltage_upper_limit=voltage_upper_limit, voltage_lower_limit=voltage_lower_limit, raise_exception=raise_exception, **kwargs)
                bus_voltages_df.set_index("name", inplace=True)
                comparison_dict[pv_field+"_"+str(multiplier_name)] = bus_voltages_df
        # compare all dataframe, and create one that contains all worst loading conditions (across all multiplier conditions)
        deciding_column_dict = {"max_per_unit_voltage": "max", "min_per_unit_voltage": "min"}
        bus_voltages_df, undervoltage_bus_list, overvoltage_bus_list, buses_with_violations = compare_multiple_dataframes_voltage(comparison_dict=comparison_dict, 
                                                                                                                                  deciding_column_dict=deciding_column_dict,
                                                                                                                                  voltage_upper_limit=voltage_upper_limit,
                                                                                                                                  voltage_lower_limit=voltage_lower_limit)
    else:
        raise Exception(f"Undefined multiplier_type {multiplier_type} passed.")    
    return bus_voltages_df, undervoltage_bus_list, overvoltage_bus_list, buses_with_violations
    

@track_timing(timer_stats_collector)
def get_bus_voltages_instance(voltage_upper_limit, voltage_lower_limit, raise_exception=True, **kwargs):
    """This computes per unit voltages for all buses in network

    Returns
    -------
    DataFrame
    """
    circuit_solve_and_check(raise_exception=raise_exception, **kwargs)  # this is added as a final check for convergence
    all_dict = {}
    all_bus_names = dss.Circuit.AllBusNames()
    for bus_name in all_bus_names:
        dss.Circuit.SetActiveBus(bus_name)
        data_dict = {
            "name": bus_name,
            "voltages": dss.Bus.puVmagAngle()[::2],
            # "kvbase": dss.Bus.kVBase(),
        }
        data_dict["max_per_unit_voltage"] = max(data_dict["voltages"])
        data_dict["min_per_unit_voltage"] = min(data_dict["voltages"])
        data_dict['phase_imbalance'] = data_dict["max_per_unit_voltage"] - data_dict["min_per_unit_voltage"]

        # check for overvoltage violation
        if data_dict["max_per_unit_voltage"] > voltage_upper_limit:
            data_dict['overvoltage_violation'] = True
            data_dict["max_voltage_deviation"] = data_dict["max_per_unit_voltage"] - voltage_upper_limit
        else:
            data_dict['overvoltage_violation'] = False
            data_dict["max_voltage_deviation"] = 0.0

        # check for undervoltage violation
        if data_dict["min_per_unit_voltage"] < voltage_lower_limit:
            data_dict['undervoltage_violation'] = True
            data_dict["min_voltage_deviation"] = voltage_lower_limit - data_dict["min_per_unit_voltage"]
        else:
            data_dict['undervoltage_violation'] = False
            data_dict["min_voltage_deviation"] = 0.0
        all_dict[data_dict["name"]] = data_dict

    all_df = pd.DataFrame.from_dict(all_dict, orient='index').reset_index(drop=True)
    undervoltage_bus_list = list(all_df.loc[all_df['undervoltage_violation'] == True]['name'].unique())
    overvoltage_bus_list = list(all_df.loc[all_df['overvoltage_violation'] == True]['name'].unique())
    buses_with_violations = list(set(undervoltage_bus_list + overvoltage_bus_list))
    return all_df, undervoltage_bus_list, overvoltage_bus_list, buses_with_violations


def compare_multiple_dataframes_voltage(comparison_dict, deciding_column_dict, voltage_upper_limit, voltage_lower_limit):
    """This function compares all dataframes in a given dictionary based on a deciding column 

    Returns
    -------
    Dataframe
    """
    all_df = pd.DataFrame()
    for deciding_column_name in deciding_column_dict.keys():
        summary_df = pd.DataFrame()
        comparison_type = deciding_column_dict[deciding_column_name]
        for df_name in comparison_dict.keys():
            label_df = pd.DataFrame()
            summary_df[df_name] = comparison_dict[df_name][deciding_column_name]
            if comparison_type == "max":
                label_df[deciding_column_name] = summary_df.idxmax(axis=1)  # find dataframe name that has max 
            elif comparison_type == "min":
               label_df[deciding_column_name] = summary_df.idxmin(axis=1)  # find dataframe name that has min 
            else:
                raise Exception(f"Unknown comparison type {comparison_type} passed.")
        final_list = []
        for index, row in label_df.iterrows():  # index is element name
            label = row[deciding_column_name]
            temp_dict = {deciding_column_name: comparison_dict[label].loc[index][deciding_column_name]}
            temp_dict.update({"name": index})
            final_list.append(temp_dict)
        temp_df = pd.DataFrame(final_list)
        temp_df.set_index("name", inplace=True)
        all_df = pd.concat([all_df, temp_df], axis=1)
    bus_voltages_df, undervoltage_bus_list, overvoltage_bus_list, buses_with_violations = get_voltage_violations(voltage_upper_limit=voltage_upper_limit, 
                                                                                                voltage_lower_limit=voltage_lower_limit, 
                                                                                                bus_voltages_df=all_df)
    return bus_voltages_df, undervoltage_bus_list, overvoltage_bus_list, buses_with_violations
        
        
def get_voltage_violations(voltage_upper_limit, voltage_lower_limit, bus_voltages_df):
    """Function to determine voltage violations
    """
    bus_voltages_df['overvoltage_violation'] = False
    bus_voltages_df['undervoltage_violation'] = False
    bus_voltages_df['max_voltage_deviation'] = 0.0
    bus_voltages_df['min_voltage_deviation'] = 0.0
    
    for index, row in bus_voltages_df.iterrows():
        # check for overvoltage violation
        if row["max_per_unit_voltage"] > voltage_upper_limit:
            bus_voltages_df.at[index, 'overvoltage_violation'] = True
            bus_voltages_df.at[index, "max_voltage_deviation"] = row["max_per_unit_voltage"] - voltage_upper_limit
        else:
            bus_voltages_df.at[index, 'overvoltage_violation'] = False
            bus_voltages_df.at[index, "max_voltage_deviation"] = 0.0

        # check for undervoltage violation
        if row["min_per_unit_voltage"] < voltage_lower_limit:
            bus_voltages_df.at[index, 'undervoltage_violation'] = True
            bus_voltages_df.at[index, "min_voltage_deviation"] = voltage_lower_limit - row["min_per_unit_voltage"]
        else:
            bus_voltages_df.at[index, 'undervoltage_violation'] = False
            bus_voltages_df.at[index, "min_voltage_deviation"] = 0.0
    
    bus_voltages_df.reset_index(inplace=True)
    undervoltage_bus_list = list(bus_voltages_df.loc[bus_voltages_df['undervoltage_violation'] == True]['name'].unique())
    overvoltage_bus_list = list(bus_voltages_df.loc[bus_voltages_df['overvoltage_violation'] == True]['name'].unique())
    buses_with_violations = list(set(undervoltage_bus_list + overvoltage_bus_list))
    return bus_voltages_df, undervoltage_bus_list, overvoltage_bus_list, buses_with_violations
            

def determine_available_line_upgrades(line_loading_df):
    """This function creates a dataframe of available line upgrades by dropping duplicates from line dataframe passed.
    """
    all_property_list = list(LineCatalogModel.schema(True).get("properties").keys())
    determining_property_list =  _extract_specific_model_properties_(model_name=LineCatalogModel, field_type_key="determine_upgrade_option", field_type_value=True)
    line_loading_df["kV"] = line_loading_df["kV"].round(5)
    if 'line_definition_type' not in line_loading_df.columns:  # add line_definition_type if not present
        line_loading_df = add_info_line_definition_type(line_loading_df)
    if 'line_placement' not in line_loading_df.columns:
        for index, row in line_loading_df.iterrows():  # add line_placement and h if not present
            info_dict = determine_line_placement(row)
            for key in info_dict.keys():
                line_loading_df.at[index, key] = info_dict[key] 
    line_upgrade_options = line_loading_df[all_property_list]
    # remove duplicate line upgrade options (that might have a different name, but same parameters)
    line_upgrade_options = line_upgrade_options.loc[line_upgrade_options.astype(str).drop_duplicates(subset=determining_property_list, keep="first").index]
    line_upgrade_options.reset_index(drop=True, inplace=True)
    if not line_upgrade_options["name"].is_unique:  # if line upgrade option names are not unique, create new names
        line_upgrade_options = line_upgrade_options.reset_index().rename(columns={'index': 'name'})
        line_upgrade_options['name'] = 'line_' + line_upgrade_options['name'].astype(str)
    return line_upgrade_options[all_property_list]


def determine_available_xfmr_upgrades(xfmr_loading_df):
    """This function creates a dataframe of available transformer upgrades by dropping duplicates from transformer dataframe passed.
    Input dataframe will need to contain "amp_limit_per_phase" column. So if external catalog is supplied, ensure it contains that column.
    """
    all_property_list = list(TransformerCatalogModel.schema(True).get("properties").keys())
    determining_property_list =  _extract_specific_model_properties_(model_name=TransformerCatalogModel, field_type_key="determine_upgrade_option", field_type_value=True)
    xfmr_upgrade_options = xfmr_loading_df[all_property_list]
    xfmr_upgrade_options = xfmr_upgrade_options.loc[xfmr_upgrade_options.astype(str).drop_duplicates(subset=determining_property_list, keep="first").index]
    xfmr_upgrade_options.reset_index(drop=True, inplace=True)
    if not xfmr_upgrade_options["name"].is_unique:  # if xfmr upgrade option names are not unique, create new names
        xfmr_upgrade_options = xfmr_upgrade_options.reset_index().rename(columns={'index': 'name'})
        xfmr_upgrade_options['name'] = 'xfmr_' + xfmr_upgrade_options['name'].astype(str)
    return xfmr_upgrade_options


def get_pv_buses(dss):
    pv_buses = []
    flag = dss.PVsystems.First()
    while flag > 0:
        pv_buses.append(dss.Properties.Value('bus1').split('.')[0])
        flag = dss.PVsystems.Next()
    return pv_buses


def get_load_buses(dss):
    load_buses = []
    flag = dss.Loads.First()
    while flag > 0:
        load_buses.append(dss.Properties.Value('bus1').split('.')[0])
        flag = dss.Loads.Next()
    return load_buses


def get_bus_coordinates():
    """This function creates a dataframe of all buses in the circuit with their x and y coordinates

    Returns
    -------

    """
    all_bus_names = dss.Circuit.AllBusNames()
    buses_list = []
    for b in all_bus_names:
        bus_dict = {}
        dss.Circuit.SetActiveBus(b)
        bus_dict['bus_name'] = b.lower()
        bus_dict['x_coordinate'] = dss.Bus.X()
        bus_dict['y_coordinate'] = dss.Bus.Y()
        buses_list.append(bus_dict)
    bus_coordinates_df = pd.DataFrame(buses_list)
    if all(bus_coordinates_df["x_coordinate"].unique() == [0]) and all( bus_coordinates_df["y_coordinate"].unique() == [0]):
        logger.info("Buscoordinates not provided for feeder model.")
    return bus_coordinates_df


def convert_summary_dict_to_df(summary_dict):
    df = pd.DataFrame.from_dict(summary_dict, orient='index')
    df.index.name = "stage"
    return df


def filter_dictionary(dict_data, wanted_keys):
    return {k: dict_data.get(k, None) for k in wanted_keys}


def compare_dict(old, new, properties_to_check=None):
    """function to compare two dictionaries with same format. 
    Only compares common elements present in both original and new dictionaries
    
    """
    field_list = []
    change = {}
    sharedKeys = set(old.keys()).intersection(new.keys())
    if not sharedKeys:  # if there are no shared keys, then exit function
        return change
    all_properties = old[list(sharedKeys)[0]].keys()
    if properties_to_check is None:
        # get all properties from first element of dictionary
        properties_to_check = all_properties
    else:
        properties_to_check = list(set(all_properties) & set(properties_to_check))
    for key in sharedKeys:
        change_flag = False
        for sub_field in properties_to_check:
            if pd.isna(old[key][sub_field]) and pd.isna(new[key][sub_field]):
                continue
            if old[key][sub_field] != new[key][sub_field]:
                change_flag = True
                field_list.append(sub_field)
        if change_flag:
            change[key] = field_list
    return change


def create_timepoint_multipliers_dict(timepoint_multipliers):
    """Creates a dictionary with new load rating, for every property and multiplier.
    Currently, it only does this for loads. But can be modified to accommodate other elements like PV as well.
    In raw_dict, value can be accessed as follows:
    value = raw_dict[property_name][object_name][multiplier_name]
    
    In reformatted_dict (which is returned from this function), value can be accessed as follows:
    value = raw_dict[object_name][property_name][multiplier_name]
    This value will need to be assigned to the object and run.
    This hasnt been used yet.
    
    Returns
    -------
    dict
    """
    for field in timepoint_multipliers.keys():
        if field == "load_multipliers":
            property_list = ["kW"]
            object_name = "Load"
            multiplier_list = []
            # get combined list of multipliers
            for key, value in timepoint_multipliers[field].items():
                multiplier_list = multiplier_list + value
            df = dss.utils.class_to_dataframe(object_name)
            df.reset_index(inplace=True)
            df['name'] = df['index'].str.split(".", expand=True)[1]
            name_list = list(df['name'].values)
            del df["index"]
            df.set_index('name', inplace=True)
            raw_dict = {}
            for property in property_list:
                logger.debug(property)
                df[property] = df[property].astype(float)
                new_df = pd.DataFrame(index=name_list, columns=multiplier_list)
                new_df.index.name = 'name'
                for multiplier in multiplier_list:
                    logger.debug(multiplier)
                    new_df[multiplier] = df[property] * multiplier
                raw_dict[property] = new_df.T.to_dict()
            # reformat dictionary to create desired format
            reformatted_dict = {}
            for name in name_list:
                reformatted_dict[name] = {}
                for property in property_list:
                    reformatted_dict[name][property] = raw_dict[property][name]
        else:
            raise Exception(f"Timepoint multiplier has Unsupported key: {field}. Presently, key 'load_multipliers' is supported.")
    return reformatted_dict


@track_timing(timer_stats_collector)
def apply_timepoint_multipliers_dict(reformatted_dict, multiplier_name, property_list=None, field="load_multipliers",
                                     **kwargs):
    """This uses a dictionary with the format of output received from create_timepoint_multipliers_dict
    Currently, it only does works loads. But can be modified to accommodate other elements like PV as well.

    In input dict: value can be accessed as follows:
    value = raw_dict[object_name][property_name][multiplier_name]
    In this function, value will be assigned to corresponding property and run.
    This hasnt been used yet.
    
    Returns
    -------
    dict
    """
    name_list = list(reformatted_dict.keys())
    if property_list is None:
        property_list = list(reformatted_dict[name_list[0]].keys())
    if field == "load_multipliers":
        flag = dss.Loads.First()
        while flag > 0:
            flag = dss.Loads.Next()
            name = dss.Loads.Name()
            if name not in name_list:  # if load name is not present in dictionary keys, continue
                continue
            for property in property_list:
                value = reformatted_dict[name][property][multiplier_name]
                if property == "kW":
                    dss.Loads.kW(value)
                else:
                    raise Exception(f"Property {property} not defined in multipliers dict")
        circuit_solve_and_check(raise_exception=True, **kwargs)
    else:
        raise Exception(f"Unsupported key in dictionary. Presently, load_multipliers is supported.")
    return reformatted_dict


def apply_uniform_timepoint_multipliers(multiplier_name, field, **kwargs):
    """This function applies a uniform mulitplier to all elements. 
    Currently, the multiplier only does works on loads. But can be modified to accommodate other elements like PV as well.
    It has two options, 1) all pv is enabled. 2) all pv is disabled.
    
    Returns
    -------
    bool
    """
    if field == "with_pv":
        check_dss_run_command("BatchEdit PVSystem..* Enabled=Yes")
    elif field == "without_pv":    
        check_dss_run_command("BatchEdit PVSystem..* Enabled=No")
    else:
        raise Exception(f"Unknown parameter {field} passed in uniform timepoint multiplier dict."
                        f"Acceptable values are 'with_pv', 'without_pv'")
    check_dss_run_command(f"set LoadMult = {multiplier_name}")
    circuit_solve_and_check(raise_exception=True, **kwargs)
    return True
