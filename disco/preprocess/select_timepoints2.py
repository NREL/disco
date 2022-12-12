# -*- coding: utf-8 -*-
"""
Created on Fri Dec  2 12:13:24 2022

@author: ksedzro
"""

import logging
import os
import time

import numpy as np
import pandas as pd
import opendssdirect as dss


logger = logging.getLogger(__name__)


def load_feeder(path_to_master):
    if not os.path.exists(path_to_master):
        raise FileNotFoundError(path_to_master)

    dpath, fname = os.path.split(path_to_master)
    newfname = fname.split(".")[0]
    new_master = os.path.join(dpath, f"{newfname}_new.dss")
    with open(path_to_master, "r") as mr:
        slines = mr.readlines()
    found_solve = False
    lines = []
    for line in slines:
        if line.lower().lstrip().startswith("solve"):
            line = "Solve\n"
            found_solve = True
        lines.append(line)
    if not found_solve:
        lines.append("Solve\n")
    with open(new_master, "w") as mw:
        mw.writelines(lines)

    dss.Text.Command(f"redirect {new_master}")


def get_param_values(param_class, bus_data, category="demand"):
    assert category in ["demand", "generation"]

    def get_bus():
        bus = dss.Properties.Value("bus1")
        if "." in bus:
            bus = dss.Properties.Value("bus1").split(".")[0]
        return bus

    def get_profile():
        profile = dss.Properties.Value("yearly")
        if not profile:
            profile = dss.Properties.Value("daily")
        if not profile:
            profile = dss.Properties.Value("duty")
        if not profile:
            raise Exception(f"Did not find profile name for {dss.CktElement.Name()}")
        return profile

    if param_class == "Load":
        flag = dss.Loads.First()
        while flag > 0:
            bus = get_bus()
            if not bus in bus_data.keys():
                bus_data[bus] = {"bus": bus, "demand": [], "generation": []}
            capacity = 0
            size = ""
            if not size:
                size = dss.Properties.Value("kW")
            if not size:
                size = dss.Properties.Value("kva")
            if size:
                capacity = float(size)
            else:
                raise Exception(f"Did not find size for {dss.CktElement.Name()}")

            profile_name = get_profile()
            bus_data[bus][category].append([capacity, profile_name])
            flag = dss.Loads.Next()

    if param_class == "PVSystem":
        flag = dss.PVsystems.First()
        while flag > 0:
            bus = get_bus()
            if not bus in bus_data.keys():
                bus_data[bus] = {"bus": bus, "demand": [], "generation": []}
            capacity = 0
            size = ""
            if not size:
                size = dss.Properties.Value("pmpp")
            if not size:
                size = dss.Properties.Value("kva")
            if size:
                capacity = float(size)
            else:
                raise Exception(f"Did not find size for {dss.CktElement.Name()}")

            profile_name = get_profile()
            bus_data[bus][category].append([capacity, profile_name])
            flag = dss.PVsystems.Next()

    if param_class == "Storage":
        flag = dss.Storages.First()
        while flag > 0:
            bus = get_bus()
            if not bus in bus_data.keys():
                bus_data[bus] = {"bus": bus, "demand": [], "generation": []}
            capacity = 0
            size = ""
            if not size:
                size = dss.Properties.Value("kwrated")
            if not size:
                size = dss.Properties.Value("kva")
            if size:
                capacity = float(size)
            else:
                raise Exception(f"Did not find size for {dss.CktElement.Name()}")

            profile_name = get_profile()
            bus_data[bus][category].append([capacity, profile_name])
            flag = dss.Storages.Next()

    return bus_data


def reset_profile_data(used_profiles, critical_time_indices, profile_types=("active", "reactive")):
    flag = dss.LoadShape.First()
    while flag > 0:
        name = dss.LoadShape.Name()
        number_of_timepoints = len(critical_time_indices)
        # TODO: Kwami, should there be error checking on profile_types?
        original_p_mult = None
        original_q_mult = None

        if name in used_profiles:
            if "active" in profile_types:
                original_p_mult = dss.LoadShape.PMult()

            if "reactive" in profile_types:
                original_q_mult = dss.LoadShape.QMult()

            dss.LoadShape.Npts(number_of_timepoints)

            if original_p_mult is not None and len(original_p_mult) > 1:
                if len(original_p_mult) > max(critical_time_indices):
                    dss.LoadShape.PMult(list(np.array(original_p_mult)[critical_time_indices]))
                else:
                    raise Exception("IndexError: Index out of range")
            if original_q_mult is not None and len(original_q_mult) > 1:
                if len(original_q_mult) > max(critical_time_indices):
                    dss.LoadShape.QMult(list(np.array(original_q_mult)[critical_time_indices]))
                else:
                    raise Exception("IndexError: Index out of range")
        flag = dss.LoadShape.Next()


def save_circuit(output_folder):
    dss.Text.Command(f"Save Circuit Dir={output_folder}")
    logger.info("Saved circuit to %s", output_folder)


def get_profile_data():
    """
    This function builds a dictionary called profile_data.
    The profile_data collects for each timeseries profile:
        the name
        the numpy array of the profile timeseries data
    INPUT:
        None
    OUTPUT:
        proile_data: a dictionary (see description above)
    """
    profile_data = {}
    flag = dss.LoadShape.First()
    while flag > 0:
        profile_name = dss.LoadShape.Name()
        profile_array = np.array(dss.LoadShape.PMult())
        if profile_name in profile_data:
            raise Exception(f"Detected duplicate profile name: {profile_name}")
        profile_data[profile_name] = {
            "profile_name": profile_name,
            "time_series": profile_array,
        }
        flag = dss.LoadShape.Next()

    return profile_data


def agregate_series(
    bus_data, profile_data, critical_conditions, recreate_profiles, destination_dir
):
    ag_series = {}
    critical_time_indices = []
    head_critical_time_indices = []
    used_profiles = []
    for bus, dic in bus_data.items():
        ag_series[bus] = {
            "critical_time_idx": [],
            "condition": [],
        }

        if dic["demand"]:
            for data in dic["demand"]:
                if "demand" in ag_series[bus]:
                    ag_series[bus]["demand"] += data[0] * profile_data[data[1]]["time_series"]
                else:
                    ag_series[bus]["demand"] = data[0] * profile_data[data[1]]["time_series"]
                used_profiles.append(data[1])
            if "max_demand" in critical_conditions:
                max_demand_idx = np.where(
                    ag_series[bus]["demand"] == np.amax(ag_series[bus]["demand"])
                )[0].tolist()[0]
                ag_series[bus]["critical_time_idx"].append(max_demand_idx)
                ag_series[bus]["condition"].append("max_demand")

            if "min_demand" in critical_conditions:
                min_demand_idx = np.where(
                    ag_series[bus]["demand"] == np.amin(ag_series[bus]["demand"])
                )[0].tolist()[0]
                ag_series[bus]["critical_time_idx"].append(min_demand_idx)
                ag_series[bus]["condition"].append("min_demand")
                # ag_series[bus]['critical_time_idx'] += [max_demand_idx, min_demand_idx]

        if dic["generation"]:
            for data in dic["generation"]:
                if "generation" in ag_series[bus]:
                    ag_series[bus]["generation"] += data[0] * profile_data[data[1]]["time_series"]
                else:
                    ag_series[bus]["generation"] = data[0] * profile_data[data[1]]["time_series"]
                used_profiles.append(data[1])
            if "max_generation" in critical_conditions:
                max_gen_idx = np.where(
                    ag_series[bus]["generation"] == np.amax(ag_series[bus]["generation"])
                )[0].tolist()[0]
                ag_series[bus]["critical_time_idx"].append(max_gen_idx)
                ag_series[bus]["condition"].append("max_generation")
            if "demand" in ag_series[bus] and "max_net_generation" in critical_conditions:
                arr = ag_series[bus]["generation"] - ag_series[bus]["demand"]
                max_netgen_idx = np.where(arr == np.amax(arr))[0].tolist()[0]
                ag_series[bus]["critical_time_idx"].append(max_netgen_idx)
                ag_series[bus]["condition"].append("max_net_generation")

    total_gen = sum([dic["generation"] for bus, dic in ag_series.items() if "generation" in dic])
    total_dem = sum([dic["demand"] for bus, dic in ag_series.items() if "demand" in dic])
    net_total_gen = total_gen - total_dem
    if "max_demand" in critical_conditions:
        max_demand_idx = np.where(total_dem == np.amax(total_dem))[0].tolist()[0]
        head_critical_time_indices.append(max_demand_idx)
    if "min_demand" in critical_conditions:
        min_demand_idx = np.where(total_dem == np.amin(total_dem))[0].tolist()[0]
        head_critical_time_indices.append(min_demand_idx)
    if "max_generation" in critical_conditions:
        max_gen_idx = np.where(total_gen == np.amax(total_gen))[0].tolist()[0]
        head_critical_time_indices.append(max_gen_idx)
    if "max_net_generation" in critical_conditions:
        max_netgen_idx = np.where(net_total_gen == np.amax(net_total_gen))[0].tolist()[0]
        head_critical_time_indices.append(max_netgen_idx)

    critical_time_indices = [
        t
        for bus, dic in ag_series.items()
        for t in dic["critical_time_idx"]
        if "critical_time_idx" in dic
    ]
    critical_time_indices += head_critical_time_indices
    critical_time_indices = list(set(critical_time_indices))
    critical_time_indices.sort()
    destination_model_dir = os.path.join(destination_dir, "new_model")
    os.makedirs(destination_model_dir, exist_ok=True)
    compression_rate = 0
    if recreate_profiles:
        destination_profile_dir = os.path.join(destination_dir, "new_profiles")
        os.makedirs(destination_profile_dir, exist_ok=True)

        for profile, val in profile_data.items():
            if profile in used_profiles:
                base_len = len(val["time_series"])
                compression_rate = len(critical_time_indices) / base_len
                if recreate_profiles:
                    data = val["time_series"][critical_time_indices]
                    new_profile_path = os.path.join(destination_profile_dir, f"{profile}.csv")
                    pd.DataFrame(data).to_csv(new_profile_path, index=False, header=False)

    reset_profile_data(used_profiles, critical_time_indices)
    save_circuit(destination_model_dir)

    return ag_series, head_critical_time_indices, critical_time_indices, compression_rate


def main(
    path_to_master,
    category_class_dict,
    critical_conditions=("max_demand", "min_demand", "max_generation", "max_net_generation"),
    recreate_profiles=False,
    destination_dir=None,
):
    """
    INPUT:
        category_path_dict: a dictionary where:
            the keys are power conversion asset categories: "demand" and "generation"
            the values are a list of paths pointing to the corresponding power conversions assets' .dss files such as "Loads.dss" and "PVSystems.dss" files
            example: category_path_dict = {'demand': [LOAD_PATH, EVLOAD_PATH], 'generation': [PV_PATH]}
        profile_files: a list of paths pointing to shape (profile) files such as "LoadShapes.dss"
    OUTPUT:
        bus_data:
        profile_data:
        ag_series:
        head_time_indices: list of critical time indices when only feeder-head timeseries are considered
        critical_time_indices: all critical time indices (individual buses as well as feeder-head considered)
        compression_rate: ratio between the number of critical timepoints and the total number of timepoints in the timeseries

    """
    folder, _ = os.path.split(path_to_master)
    if destination_dir is None:
        folder, _ = os.path.split(path_to_master)
        destination_dir = folder
    else:
        os.makedirs(destination_dir, exist_ok=True)

    bus_data = {}
    load_feeder(path_to_master)
    for category, param_classes in category_class_dict.items():
        for param_class in param_classes:
            bus_data = get_param_values(param_class, bus_data, category)
    profile_data = get_profile_data()
    ag_series, head_time_indices, critical_time_indices, compression_rate = agregate_series(
        bus_data, profile_data, critical_conditions, recreate_profiles, destination_dir
    )
    return (
        bus_data,
        profile_data,
        ag_series,
        head_time_indices,
        critical_time_indices,
        compression_rate,
    )


if __name__ == "__main__":
    path_to_master = r"C:\Users\KSEDZRO\Documents\Projects\LA-equity-resilience\data\P12U\sb9_p12uhs3_1247_trans_264--p12udt8475\Master.dss"
    destination = r"C:\Users\KSEDZRO\Documents\Projects\LA-equity-resilience\data\P12U"
    st = time.time()
    category_class_dict = {"demand": ["Load"], "generation": ["PVSystem"]}
    critical_conditions = ["max_demand", "max_net_generation"]

    (
        bus_data,
        profile_data,
        ag_series,
        head_time_indices,
        critical_time_indices,
        compression_rate,
    ) = main(
        path_to_master,
        category_class_dict,
        critical_conditions=critical_conditions,
        destination_dir=destination,
        recreate_profiles=True,
    )
    et = time.time()
    elapse_time = et - st
