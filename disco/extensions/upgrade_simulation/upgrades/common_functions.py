import os
import ast
import math
import json
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

logger = logging.getLogger(__name__)


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
    logger.info("-> Reloading OpenDSS circuit")
    check_dss_run_command("clear")
    if dss_file_list is None:
        raise Exception("No OpenDSS files have been passed to be loaded.")
    for dss_file in dss_file_list:
        logger.info(f"Redirecting {dss_file}.")
        check_dss_run_command(f"Redirect {dss_file}")
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
    if enable_pydss_solve:
        pydss_params = define_initial_pydss_settings(**kwargs)
        circuit_solve_and_check(raise_exception=True, **pydss_params)
        return pydss_params
    else:
        circuit_solve_and_check(raise_exception=True)
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
    # logger.info("-->Redirecting master file:")
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


def write_text_file(string_list, text_file_path):
    """This function writes the string contents of a list to a text file

    Parameters
    ----------
    string_list
    text_file_path

    Returns
    -------

    """
    pathlib.Path(text_file_path).write_text("\n".join(string_list))


def create_upgraded_master_dss(dss_file_list, upgraded_master_dss_filepath):
    """Function to create master dss with redirects to upgrades dss file.
    The redirect paths in this file are relative to the file"""
    command_list = []
    for filename in dss_file_list:
        rel_filename = os.path.relpath(filename, os.path.dirname(upgraded_master_dss_filepath))
        command_list.append(f"Redirect {rel_filename}")
    return command_list


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
    pv_df = dss.utils.pvsystems_to_dataframe()
    if len(pv_df) > 0:
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
    line_properties = kwargs.get("line_properties", None)
    xfmr_properties = kwargs.get("xfmr_properties", None)
    voltage_properties = kwargs.get("voltage_properties", None)
    
    final_dict = {}
    if line_properties is None:
        line_properties = ['name', 'phases','normamps', 'kV', 'line_placement',  'length', 'units', 'max_amp_loading', 
                           'max_per_unit_loading', 'status']
    if xfmr_properties is None:
        xfmr_properties = ['name', 'phases', 'windings', 'conns', 'kVs', 'kVAs', 'amp_limit_per_phase','max_amp_loading', 
                           'max_per_unit_loading', 'status']  
    if voltage_properties is None:
        voltage_properties = ['name', 'Max per unit voltage', 'Min per unit voltage',  'Overvoltage violation', 
                              'Max voltage_deviation', 'Undervoltage violation', 'Min voltage_deviation']
        
    # some file reformatting
    if "conns" in xfmr_properties:
        xfmr_loading_df["conns"] = xfmr_loading_df["conns"].apply(ast.literal_eval)
    if "kVs" in xfmr_properties:
        xfmr_loading_df["kVs"] = xfmr_loading_df["kVs"].apply(ast.literal_eval)
    if "windings" in xfmr_properties:
        xfmr_loading_df["windings"] = xfmr_loading_df["windings"].astype(int)
    
    final_dict.update({"transformer_loading": xfmr_loading_df[xfmr_properties].to_dict(orient="records")})
    final_dict.update({"line_loading": line_loading_df[line_properties].to_dict(orient="records")})
    final_dict.update({"bus_voltage": bus_voltages_df[voltage_properties].to_dict(orient="records")})
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
        data_dict["substation_xfmr"]["kVs"] = ast.literal_eval(data_dict["substation_xfmr"]["kVs"])
        # this checks if the voltage kVs are the same for the substation transformer
        data_dict["substation_xfmr"]["is_autotransformer_flag"] = len(set(data_dict["substation_xfmr"]["kVs"])) <= 1
    return data_dict


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
    # if linecode or linegeometry is not present in existing network definitions
    if not existing_config_dict[new_config_type]["name"].str.lower().isin([new_config_name]).any():  
        # add definition for linecode or linegeometry
        if external_upgrades_technical_catalog is None:
            raise UpgradesExternalCatalogRequired(f"External upgrades technical catalog not available to determine line config type")
        external_config_df = pd.DataFrame(external_upgrades_technical_catalog[new_config_type])
        if external_config_df["name"].str.lower().isin([new_config_name]).any():
            config_definition_df = external_config_df.loc[external_config_df["name"] == new_config_name]
            config_definition_dict = dict(config_definition_df.iloc[0])
            if config_definition_dict["normamps"] != chosen_option["normamps"]:
                logger.warning(f"Mismatch between noramps for linecode {new_config_name} and chosen upgrade option normamps: {chosen_option['name']}")
            # check format of certain fields
            matrix_fields = [s for s in config_definition_dict.keys() if 'matrix' in s]
            for field in matrix_fields:
                config_definition_dict[field] = config_definition_dict[field].replace("'","")
                config_definition_dict[field] = config_definition_dict[field].replace("[","(")
                config_definition_dict[field] = config_definition_dict[field].replace("]",")")
            command_string = create_opendss_definition(config_definition_dict=config_definition_dict)
        else:
            raise UpgradesExternalCatalogMissingObjectDefinition(
                f"{new_config_type} definition for {new_config_name} not found in external catalog."
            )
    else:
        command_string = None   
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


def get_all_transformer_info_instance(upper_limit=None, compute_loading=True):
    """This collects transformer information

    Returns
    -------
    DataFrame
    """
    all_df = dss.utils.class_to_dataframe("transformer")
    if len(all_df) == 0:
        return pd.DataFrame()
    all_df["name"] = all_df.index.str.split(".").str[1]
    all_df["equipment_type"] = all_df.index.str.split(".").str[0]
    # extract only enabled lines
    all_df = all_df.loc[all_df["enabled"] == True]
    all_df[["wdg", "phases"]] = all_df[["wdg", "phases"]].astype(int)
    float_fields = ["kV", "kVA", "normhkVA", "emerghkVA", "%loadloss", "%noloadloss", "XHL", "XHT", "XLT", "%R",
                    "Rneut", "Xneut", "X12", "X13", "X23", "RdcOhms"]
    all_df[float_fields] = all_df[float_fields].astype(float)
    # define empty new columns
    all_df['bus_names_only'] = None
    all_df["amp_limit_per_phase"] = np.nan
    if compute_loading:
        all_df["max_amp_loading"] = np.nan
        all_df["max_per_unit_loading"] = np.nan
        all_df["status"] = ""
    for index, row in all_df.iterrows():
        # convert type from list to tuple since they are hashable objects (and can be indexed)
        all_df.at[index, "kVs"] = [float(a) for a in row["kVs"]]
        all_df.at[index, "kVAs"] = [float(a) for a in row["kVAs"]]
        all_df.at[index, "Xscarray"] = [float(a) for a in row["Xscarray"]]
        all_df.at[index, "%Rs"] = [float(a) for a in row["%Rs"]]
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
    # convert lists to string type (so they can be set as dataframe index later)
    all_df[['conns', 'kVs']] = all_df[['conns', 'kVs']].astype(str)
    all_df = all_df.reset_index(drop=True).set_index('name')
    return all_df.reset_index()


def add_info_line_definition_type(all_df):
    all_df["line_definition_type"] = "line_definition"
    all_df.loc[all_df["linecode"] != "", "line_definition_type"] = "linecode"
    all_df.loc[all_df["geometry"] != "", "line_definition_type"] = "geometry"
    return all_df


def determine_line_placement(line_series):
    """ Distinguish between overhead and underground cables
        currently there is no way to distinguish directy using opendssdirect/pydss etc.
        It is done here using property 'height' parameter and if string present in name

    Parameters
    ----------
    line_series

    Returns
    -------
    dict
    """
    info_dict = {}
    info_dict["line_placement"] = None
    if line_series["line_definition_type"] == "geometry":
            dss.Circuit.SetActiveClass("linegeometry")
            dss.ActiveClass.Name(line_series["geometry"])
            h = float(dss.Properties.Value("h"))
            info_dict["h"] = 0
            if h >= 0:
                info_dict["line_placement"] = "overhead"
            else:
                info_dict["line_placement"] = "underground"
    else:
        if ("oh" in line_series["geometry"].lower()) or ("oh" in line_series["linecode"].lower()):
            info_dict["line_placement"] = "overhead"
        elif ("ug" in line_series["geometry"].lower()) or ("ug" in line_series["linecode"].lower()):
            info_dict["line_placement"] = "underground"
        else:
            info_dict["line_placement"] = None
    return info_dict


def get_all_line_info_instance(upper_limit=None, compute_loading=True, ignore_switch=True):
    """This collects line information

    Returns
    -------
    DataFrame
    """
    all_df = dss.utils.class_to_dataframe("line")
    if len(all_df) == 0:
        return pd.DataFrame()
    all_df["name"] = all_df.index.str.split(".").str[1]
    all_df["equipment_type"] = all_df.index.str.split(".").str[0]
    # extract only enabled lines
    all_df = all_df.loc[all_df["enabled"] == True]
    all_df["phases"] = all_df["phases"].astype(int)
    all_df[["normamps", "length"]] = all_df[["normamps", "length"]].astype(float)
    all_df = add_info_line_definition_type(all_df)
    # define empty new columns
    all_df["kV"] = np.nan
    all_df["h"] = np.nan
    all_df["line_placement"] = ""
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
    all_df.loc[(all_df.units == 'none') & (all_df.Switch == True), 'units'] = 'm'
    # if switch is to be ignored
    if ignore_switch:
        all_df = all_df.loc[all_df['Switch'] == False]
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
    for index, label in label_df.iteritems():  # index is element name
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
        all_df.at[index, "transformer_conn"] = dss.Properties.Value("conn").replace(" ", "")  # opendss returns conn with a space 
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
    all_df = all_df.loc[all_df['enabled'] == True]
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
    # TODO are any other checks needed before concatenating dataframes? i.e. if capacitor is not present
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
        capcontrol_columns = ['name', 'capacitor', 'type', 'equipment_type']
        return pd.DataFrame(columns=capcontrol_columns)
    all_df["name"] = all_df.index.str.split(".").str[1]
    all_df["equipment_type"] = all_df.index.str.split(".").str[0]
    float_columns = ["CTPhase", "CTratio", "DeadTime", "Delay", "DelayOFF", "OFFsetting", "ONsetting", "PTratio",
                     "Vmax", "Vmin"]
    all_df[float_columns] = all_df[float_columns].astype(float)
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
    result = dss.run_command(f"{command_string}")
    if result != "":
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
        deciding_column_dict = {"Max per unit voltage": "max", "Min per unit voltage": "min"}
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
        data_dict["Max per unit voltage"] = max(data_dict["voltages"])
        data_dict["Min per unit voltage"] = min(data_dict["voltages"])
        data_dict['Phase imbalance'] = data_dict["Max per unit voltage"] - data_dict["Min per unit voltage"]

        # check for overvoltage violation
        if data_dict["Max per unit voltage"] > voltage_upper_limit:
            data_dict['Overvoltage violation'] = True
            data_dict["Max voltage_deviation"] = data_dict["Max per unit voltage"] - voltage_upper_limit
        else:
            data_dict['Overvoltage violation'] = False
            data_dict["Max voltage_deviation"] = 0.0

        # check for undervoltage violation
        if data_dict["Min per unit voltage"] < voltage_lower_limit:
            data_dict['Undervoltage violation'] = True
            data_dict["Min voltage_deviation"] = voltage_lower_limit - data_dict["Min per unit voltage"]
        else:
            data_dict['Undervoltage violation'] = False
            data_dict["Min voltage_deviation"] = 0.0
        all_dict[data_dict["name"]] = data_dict

    all_df = pd.DataFrame.from_dict(all_dict, orient='index').reset_index(drop=True)
    undervoltage_bus_list = list(all_df.loc[all_df['Undervoltage violation'] == True]['name'].unique())
    overvoltage_bus_list = list(all_df.loc[all_df['Overvoltage violation'] == True]['name'].unique())
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
    bus_voltages_df['Overvoltage violation'] = False
    bus_voltages_df['Undervoltage violation'] = False
    bus_voltages_df['Max voltage_deviation'] = 0.0
    bus_voltages_df['Min voltage_deviation'] = 0.0
    
    for index, row in bus_voltages_df.iterrows():
        # check for overvoltage violation
        if row["Max per unit voltage"] > voltage_upper_limit:
            bus_voltages_df.at[index, 'Overvoltage violation'] = True
            bus_voltages_df.at[index, "Max voltage_deviation"] = row["Max per unit voltage"] - voltage_upper_limit
        else:
            bus_voltages_df.at[index, 'Overvoltage violation'] = False
            bus_voltages_df.at[index, "Max voltage_deviation"] = 0.0

        # check for undervoltage violation
        if row["Min per unit voltage"] < voltage_lower_limit:
            bus_voltages_df.at[index, 'Undervoltage violation'] = True
            bus_voltages_df.at[index, "Min voltage_deviation"] = voltage_lower_limit - row["Min per unit voltage"]
        else:
            bus_voltages_df.at[index, 'Undervoltage violation'] = False
            bus_voltages_df.at[index, "Min voltage_deviation"] = 0.0
    
    bus_voltages_df.reset_index(inplace=True)
    undervoltage_bus_list = list(bus_voltages_df.loc[bus_voltages_df['Undervoltage violation'] == True]['name'].unique())
    overvoltage_bus_list = list(bus_voltages_df.loc[bus_voltages_df['Overvoltage violation'] == True]['name'].unique())
    buses_with_violations = list(set(undervoltage_bus_list + overvoltage_bus_list))
    return bus_voltages_df, undervoltage_bus_list, overvoltage_bus_list, buses_with_violations
            

def determine_available_line_upgrades(line_loading_df):
    property_list = ['line_definition_type', 'linecode', 'phases', 'kV', 'Switch',
                     'normamps', 'r1', 'x1', 'r0', 'x0', 'C1', 'C0',
                     'rmatrix', 'xmatrix', 'cmatrix', 'Rg', 'Xg', 'rho', 'units', 'spacing',
                     # 'wires', 'EarthModel', 'cncables', 'tscables', 'B1', 'B0', 'emergamps',
                     # 'faultrate', 'pctperm', 'repair', 'basefreq', 'enabled', 'like',
                     'h', 'line_placement']
    if 'line_definition_type' not in line_loading_df.columns:  # add line_definition_type if not present
        line_loading_df = add_info_line_definition_type(line_loading_df)
    if 'line_placement' not in line_loading_df.columns:
        for index, row in line_loading_df.iterrows():  # add line_placement and h if not present
            info_dict = determine_line_placement(row)
            for key in info_dict.keys():
                line_loading_df.at[index, key] = info_dict[key] 
    line_upgrade_options = line_loading_df[property_list + ['geometry']]
    # remove duplicate line upgrade options (that might have a different name, but same parameters)
    line_upgrade_options = line_upgrade_options.loc[line_upgrade_options.astype(str).drop_duplicates(
        subset=property_list).index]
    line_upgrade_options.reset_index(drop=True, inplace=True)
    line_upgrade_options = line_upgrade_options.reset_index().rename(columns={'index': 'name'})
    line_upgrade_options['name'] = 'line_' + line_upgrade_options['name'].astype(str)
    line_upgrade_options["kV"] = line_upgrade_options["kV"].round(5)
    return line_upgrade_options


def determine_available_xfmr_upgrades(xfmr_loading_df):
    """This function creates a dataframe of available transformer upgrades by dropping duplicates from transformer dataframe passed.
    Input dataframe will need to contain "amp_limit_per_phase" column. So if external catalog is supplied, ensure it contains that column.
    """
    property_list = ['phases', 'windings', 'wdg', 'conn', 'kV', 'kVA',
                     'tap', '%R', 'Rneut', 'Xneut', 'conns', 'kVs', 'kVAs', 'taps', 'XHL', 'XHT',
                     'XLT', 'Xscarray', 'thermal', 'n', 'm', 'flrise', 'hsrise', '%loadloss',
                     '%noloadloss', 'normhkVA', 'emerghkVA', 'sub', 'MaxTap', 'MinTap',
                     'NumTaps', 'subname', '%imag', 'ppm_antifloat', '%Rs', 'bank',
                     'XfmrCode', 'XRConst', 'X12', 'X13', 'X23', 'LeadLag',
                     'Core', 'RdcOhms', 'normamps', 'emergamps', 'faultrate', 'pctperm',
                     'basefreq', 'amp_limit_per_phase']
    # TODO: can add capability to add "amp_limit_per_phase" column if not present in input dataframe.
    # if 'amp_limit_per_phase' not in xfmr_loading_df.columns:
    xfmr_upgrade_options = xfmr_loading_df[property_list]
    xfmr_upgrade_options = xfmr_upgrade_options.loc[xfmr_upgrade_options.astype(str).drop_duplicates().index]
    xfmr_upgrade_options.reset_index(drop=True, inplace=True)
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
    return pd.DataFrame(buses_list)


def convert_summary_dict_to_df(summary_dict):
    df = pd.DataFrame.from_dict(summary_dict, orient='index')
    df.index.name = "stage"
    return df


def filter_dictionary(dict_data, wanted_keys):
    return {k: dict_data.get(k, None) for k in wanted_keys}


def compare_dict(old, new):
    """function to compare two dictionaries with same format. 
    Only compares common elements present in both original and new dictionaries
    
    """
    field_list = []
    change = {}
    sharedKeys = set(old.keys()).intersection(new.keys())
    for key in sharedKeys:
        change_flag = False
        for sub_field in old[key]:
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
        check_dss_run_command("BatchEdit PVSystem..* Enabled=True")
    elif field == "without_pv":    
        check_dss_run_command("BatchEdit PVSystem..* Enabled=False")
    else:
        raise Exception(f"Unknown parameter {field} passed in uniform timepoint multiplier dict."
                        f"Acceptable values are 'with_pv', 'without_pv'")
    check_dss_run_command(f"set LoadMult = {multiplier_name}")
    circuit_solve_and_check(raise_exception=True, **kwargs)
    return True
