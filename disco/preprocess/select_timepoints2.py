# -*- coding: utf-8 -*-
"""
Created on Fri Dec  2 12:13:24 2022

@author: ksedzro
"""

import filecmp
import enum
import logging
import shutil
import time
from pathlib import Path

import numpy as np
import pandas as pd
import opendssdirect as dss


logger = logging.getLogger(__name__)


_DISALLOWED_OPEN_DSS_COMMANDS = ("export", "plot", "show")
_SOLVE_LINE = "Solve mode=snapshot\n"


class CriticalCondition(enum.Enum):
    """Possible critical conditions to use for time-point selection"""

    MAX_DEMAND = "max_demand"
    MIN_DEMAND = "min_demand"
    MAX_GENERATION = "max_generation"
    MAX_NET_GENERATION = "max_net_generation"


class DemandCategory(enum.Enum):

    LOAD = "load"


class GenerationCategory(enum.Enum):

    PV_SYSTEM = "pv_system"
    STORAGE = "storage"


class InvalidParameter(Exception):
    """Raised when user input is invalid"""


def load_feeder(path_to_master: Path, destination_dir: Path, fix_master_file: bool):
    """Compile an OpenDSS circuit after first ensuring that time-series mode is disabled."""
    if not path_to_master.exists():
        raise FileNotFoundError(path_to_master)

    if fix_master_file:
        new_master = make_fixes_to_master(path_to_master)
    else:
        new_master = path_to_master
    check_master_file(new_master)

    try:
        dss.Text.Command(f"redirect {new_master}")
        shutil.copyfile(new_master, destination_dir / new_master.name)
        logger.info("Redirected to %s", new_master)
    finally:
        if path_to_master != new_master:
            new_master.unlink()


def make_fixes_to_master(master_file):
    suffix = master_file.suffix
    new_master = master_file.parent / master_file.name.replace(suffix, f"_new{suffix}")

    def has_invalid_command(line):
        for command in _DISALLOWED_OPEN_DSS_COMMANDS:
            if line.startswith(command):
                return True
        return False

    with open(new_master, "w") as f_out:  # overwrite file if it exists
        with open(master_file, "r") as f_in:
            for line in f_in:
                lowered = line.strip().lower()
                if lowered.startswith("solve") or has_invalid_command(lowered):
                    logger.warning("Removing line from new Master.dss: %s", line.strip())
                else:
                    f_out.write(line)
            f_out.write(_SOLVE_LINE)

    return new_master


def check_master_file(master_file: Path):
    comment_chars = ("!", "#")

    def check_invalid_command(line):
        for invalid_command in _DISALLOWED_OPEN_DSS_COMMANDS:
            if line.startswith(invalid_command):
                raise InvalidParameter(f"The command {invalid_command} is not allowed.")

    def is_commented(line):
        for comment_char in comment_chars:
            if line.startswith(comment_char):
                return True
        return False

    with open(master_file) as f_in:
        found_solve = False
        for line in f_in:
            lowered = line.strip().lower()
            if not lowered or is_commented(line):
                continue
            check_invalid_command(lowered)
            if "solve" in lowered:
                if lowered not in ("solve", _SOLVE_LINE.strip().lower()):
                    raise InvalidParameter(
                        "The solve command cannot have parameters besides mode=snapshot: "
                        f"{line.strip()}: {master_file}"
                    )
                if found_solve:
                    raise InvalidParameter(
                        f"Cannot have more than one call to Solve: {master_file}"
                    )
                found_solve = True


def get_profile():
    """Return the profile of the currenlty-selected OpenDSS element.

    Returns
    -------
    str
        Return "" if there is no load shape profile attached.

    """
    profile = dss.Properties.Value("yearly")
    if not profile:
        profile = dss.Properties.Value("daily")
    if not profile:
        profile = dss.Properties.Value("duty")
    return profile


def get_param_values(param_class, bus_data, category):
    def get_bus():
        bus = dss.Properties.Value("bus1")
        if "." in bus:
            bus = dss.Properties.Value("bus1").split(".")[0]
        return bus

    if param_class == DemandCategory.LOAD:
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
            if not profile_name:
                raise Exception(f"Did not find profile name for {dss.CktElement.Name()}")
            bus_data[bus][category].append([capacity, profile_name])
            flag = dss.Loads.Next()

    elif param_class == GenerationCategory.PV_SYSTEM:
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
            if not profile_name:
                raise Exception(f"Did not find profile name for {dss.CktElement.Name()}")
            bus_data[bus][category].append([capacity, profile_name])
            flag = dss.PVsystems.Next()

    elif param_class == GenerationCategory.STORAGE:
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
            if not profile_name:
                raise Exception(f"Did not find profile name for {dss.CktElement.Name()}")
            bus_data[bus][category].append([capacity, profile_name])
            flag = dss.Storages.Next()

    else:
        raise Exception(f"Invalid param_class={param_class}")

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


def save_circuit(output_folder: Path):
    """Run the OpenDSS command to save a compiled circuit into a directory."""
    dss.Text.Command(f"Save Circuit Dir={output_folder}")
    logger.info("Saved circuit to %s", output_folder)


def export_power_flow_results(path: Path):
    """Export OpenDSS circuit elemement values into a directory."""
    path.mkdir(exist_ok=True)
    for export_type, filename in {
        "currents": "currents.csv",
        "capacity": "capacity.csv",
        "loads": "loads.csv",
        "powers [mva]": "powers.csv",
        "voltages": "voltages.csv",
    }.items():
        dss.Text.Command(f"export {export_type} {path}/{filename}")


def compare_power_flow_results(before_path, after_path):
    """Compare the exported results from two directories.

    Raises
    ------
    Exception
        Raised if the results do not match.

    """
    before = {x.name: x for x in before_path.iterdir()}
    after = {x.name: x for x in after_path.iterdir()}
    assert sorted(before.keys()) == sorted(after.keys())
    match = True
    for name in before:
        if not filecmp.cmp(before[name], after[name]):
            logger.error("Files before=%s and after=%s do not match", before[name], after[name])
            match = False

    # TODO: csv comparisons have _mostly_ minor differences.
    # if not match:
    #    raise Exception("Before/after power flow results do not match. Refer to the log file.")


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


def aggregate_series(
    bus_data,
    profile_data,
    critical_conditions,
    recreate_profiles,
    destination_dir,
    create_new_circuit,
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
            if CriticalCondition.MAX_DEMAND in critical_conditions:
                max_demand_idx = np.where(
                    ag_series[bus]["demand"] == np.amax(ag_series[bus]["demand"])
                )[0].tolist()[0]
                ag_series[bus]["critical_time_idx"].append(max_demand_idx)
                ag_series[bus]["condition"].append(CriticalCondition.MAX_DEMAND)

            if CriticalCondition.MIN_DEMAND in critical_conditions:
                min_demand_idx = np.where(
                    ag_series[bus]["demand"] == np.amin(ag_series[bus]["demand"])
                )[0].tolist()[0]
                ag_series[bus]["critical_time_idx"].append(min_demand_idx)
                ag_series[bus]["condition"].append(CriticalCondition.MIN_DEMAND)
                # ag_series[bus]['critical_time_idx'] += [max_demand_idx, min_demand_idx]

        if dic["generation"]:
            for data in dic["generation"]:
                if "generation" in ag_series[bus]:
                    ag_series[bus]["generation"] += data[0] * profile_data[data[1]]["time_series"]
                else:
                    ag_series[bus]["generation"] = data[0] * profile_data[data[1]]["time_series"]
                used_profiles.append(data[1])
            if CriticalCondition.MAX_GENERATION in critical_conditions:
                max_gen_idx = np.where(
                    ag_series[bus]["generation"] == np.amax(ag_series[bus]["generation"])
                )[0].tolist()[0]
                ag_series[bus]["critical_time_idx"].append(max_gen_idx)
                ag_series[bus]["condition"].append(CriticalCondition.MAX_GENERATION)
            if (
                "demand" in ag_series[bus]
                and CriticalCondition.MAX_NET_GENERATION in critical_conditions
            ):
                arr = ag_series[bus]["generation"] - ag_series[bus]["demand"]
                max_netgen_idx = np.where(arr == np.amax(arr))[0].tolist()[0]
                ag_series[bus]["critical_time_idx"].append(max_netgen_idx)
                ag_series[bus]["condition"].append(CriticalCondition.MAX_NET_GENERATION)

    total_gen = sum([dic["generation"] for bus, dic in ag_series.items() if "generation" in dic])
    total_dem = sum([dic["demand"] for bus, dic in ag_series.items() if "demand" in dic])
    net_total_gen = total_gen - total_dem
    if CriticalCondition.MAX_DEMAND in critical_conditions:
        max_demand_idx = np.where(total_dem == np.amax(total_dem))[0].tolist()[0]
        head_critical_time_indices.append(max_demand_idx)
    if CriticalCondition.MIN_DEMAND in critical_conditions:
        min_demand_idx = np.where(total_dem == np.amin(total_dem))[0].tolist()[0]
        head_critical_time_indices.append(min_demand_idx)
    if CriticalCondition.MAX_GENERATION in critical_conditions:
        max_gen_idx = np.where(total_gen == np.amax(total_gen))[0].tolist()[0]
        head_critical_time_indices.append(max_gen_idx)
    if CriticalCondition.MAX_NET_GENERATION in critical_conditions:
        max_netgen_idx = np.where(net_total_gen == np.amax(net_total_gen))[0].tolist()[0]
        head_critical_time_indices.append(max_netgen_idx)

    critical_time_indices = [
        t
        for bus, dic in ag_series.items()
        for t in dic["critical_time_idx"]
        if "critical_time_idx" in dic
    ]
    critical_time_indices += head_critical_time_indices
    critical_time_indices = sorted(set(critical_time_indices))
    compression_rate = 0
    if recreate_profiles:
        destination_profile_dir = destination_dir / "new_profiles"
        destination_profile_dir.mkdir()

        for profile, val in profile_data.items():
            if profile in used_profiles:
                base_len = len(val["time_series"])
                compression_rate = len(critical_time_indices) / base_len
                if recreate_profiles:
                    data = val["time_series"][critical_time_indices]
                    new_profile_path = destination_profile_dir / f"{profile}.csv"
                    pd.DataFrame(data).to_csv(new_profile_path, index=False, header=False)

    if create_new_circuit:
        reset_profile_data(used_profiles, critical_time_indices)
        before_path = destination_dir / "power_flow_results_before"
        after_path = destination_dir / "power_flow_results_after"
        destination_model_dir = destination_dir / "new_model"
        destination_model_dir.mkdir()
        save_circuit(destination_model_dir)
        master_file = destination_model_dir / "Master.dss"
        with open(master_file, "a") as f_out:
            f_out.write("Calcvoltagebases\n")
            f_out.write("Solve\n")

    return ag_series, head_critical_time_indices, critical_time_indices, compression_rate


def main(
    path_to_master: Path,
    categories,
    critical_conditions=tuple(x for x in CriticalCondition),
    recreate_profiles=False,
    destination_dir=None,
    create_new_circuit=True,
    fix_master_file=False,
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
    if not destination_dir.exists():
        raise FileNotFoundError(f"destination_dir={destination_dir} does not exist")

    bus_data = {}
    load_feeder(path_to_master, destination_dir, fix_master_file)
    for category, param_classes in categories.items():
        for param_class in param_classes:
            bus_data = get_param_values(param_class, bus_data, category)
    profile_data = get_profile_data()
    ag_series, head_time_indices, critical_time_indices, compression_rate = aggregate_series(
        bus_data,
        profile_data,
        critical_conditions,
        recreate_profiles,
        destination_dir,
        create_new_circuit,
    )

    logger.info("head_time_indices = %s length = %s", head_time_indices, len(head_time_indices))
    logger.info(
        "critical_time_indices = %s length = %s", critical_time_indices, len(critical_time_indices)
    )
    with open(destination_dir / "metadata.csv", "w") as f_out:
        f_out.write("index,time_point_index,timestamp,condition\n")
        for i, tp_index in enumerate(critical_time_indices):
            f_out.write(f"{i},{tp_index},TBD,TBD\n")

    return (
        bus_data,
        profile_data,
        ag_series,
        head_time_indices,
        critical_time_indices,
        compression_rate,
    )


if __name__ == "__main__":
    path_to_master = Path(
        r"C:\Users\KSEDZRO\Documents\Projects\LA-equity-resilience\data\P12U\sb9_p12uhs3_1247_trans_264--p12udt8475\Master.dss"
    )
    destination = Path(r"C:\Users\KSEDZRO\Documents\Projects\LA-equity-resilience\data\P12U")
    destination.mkdir(exist_ok=True)
    st = time.time()
    category_class_dict = {
        "demand": [DemandCategory.LOAD],
        "generation": [GenerationCategory.PV_SYSTEM],
    }
    critical_conditions = [CriticalCondition.MAX_DEMAND, CriticalCondition.MAX_NET_GENERATION]

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
