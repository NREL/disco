"""This code calculates the hosting capcity (checks voltage and thermal violation limits) for
a given feeder.
"""

# -*- coding: utf-8 -*-
"""
Created on Wed Sep 18 14:32:29 2019

@author: ppaudyal
"""

import fileinput
import itertools
import logging
import os
import shutil
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import pandas as pd
import numpy as np
import math
import opendssdirect as dss

from .load_distance_from_SS import calc_dist
from .plot_hosting_capacity import (
    plot_capacity_V,
    plot_capacity_thermal_1,
    plot_capacity_thermal_2,
)
from .number_of_ev_chargers import levels_of_charger


logger = logging.getLogger(__name__)


def run(
    master_file: Path,
    lower_voltage_limit: float,
    upper_voltage_limit: float,
    kw_step_voltage_violation: float,
    voltage_tolerance: float,
    kw_step_thermal_violation: float,
    thermal_tolerance: float,
    extra_percentage_for_existing_overloads: float,
    thermal_loading_limit: float,
    export_circuit_elements: bool,
    # plot_heatmap: bool,
    output_dir: Path,
    num_cpus=None,
):
    # This accounts for master files that enable time series mode.
    backup_file = master_file.with_suffix(".bk")
    shutil.copyfile(master_file, backup_file)
    with fileinput.input(files=[master_file], inplace=True) as f:
        for line in f:
            if not line.strip().lower().startswith("solve"):
                print(line, end="")
        print("Solve mode=snapshot")

    try:
        shutil.copyfile(master_file, output_dir / "Master.dss")
        _run(
            master_file=master_file,
            lower_voltage_limit=lower_voltage_limit,
            upper_voltage_limit=upper_voltage_limit,
            kw_step_voltage_violation=kw_step_voltage_violation,
            voltage_tolerance=voltage_tolerance,
            kw_step_thermal_violation=kw_step_thermal_violation,
            thermal_tolerance=thermal_tolerance,
            extra_percentage_for_existing_overloads=extra_percentage_for_existing_overloads,
            thermal_loading_limit=thermal_loading_limit,
            export_circuit_elements=export_circuit_elements,
            output_dir=output_dir,
            num_cpus=num_cpus,
        )
    finally:
        os.rename(backup_file, master_file)


def _run(
    master_file: Path,
    lower_voltage_limit: float,
    upper_voltage_limit: float,
    kw_step_voltage_violation: float,
    voltage_tolerance: float,
    kw_step_thermal_violation: float,
    thermal_tolerance: float,
    extra_percentage_for_existing_overloads: float,
    thermal_loading_limit: float,
    export_circuit_elements: bool,
    # plot_heatmap: bool,
    output_dir: Path,
    num_cpus=None,
):
    dss.Text.Command("clear")
    compile_circuit(master_file)
    ckt_name = dss.Circuit.Name()
    logger.info("Circuit name: %s from %s master_file", ckt_name, master_file)

    if export_circuit_elements:
        export_circuit_element_properties(output_dir)

    # TODO: Priti, this code isn't doing anything. Should we delete it?
    # node_number = len(AllNodeNames)
    # Vbase_allnode = [0] * node_number
    # ii = 0
    # for node in AllNodeNames:
    #     dss.Circuit.SetActiveBus(node)
    #     Vbase_allnode[ii] = dss.Bus.kVBase() * 1000
    #     ii = ii + 1

    # TODO: Priti: these variables are unused. Do we need them?
    # hCapNames = [str(x)[1:-1] for x in dss.Capacitors.AllNames()]
    # hRegNames = [str(x)[1:-1] for x in dss.RegControls.AllNames()]

    dss.Text.Command("solve mode=snap")
    logger.info(
        "Initial condition voltage violation: %s",
        circuit_has_violations(lower_voltage_limit, upper_voltage_limit),
    )
    bus_distances = list_bus_distances()
    np.savetxt(output_dir / "node_distance.csv", bus_distances)

    ####### for thermal overload capapcity #######################################################
    overloads = get_loadings_with_violations(thermal_loading_limit)
    if overloads:
        logger.info("Thermal violation exists initially")
        logger.info("Overloads: %s", overloads)
    else:
        logger.info("No thermal violation initially")

    elements_with_extra_threshold = {
        k: v + extra_percentage_for_existing_overloads for k, v in overloads.items()
    }

    logger.debug("new_threshold=%s", elements_with_extra_threshold)
    loads = get_loads()

    v_output_df = calculate_voltage_hosting_capacity(
        loads,
        master_file,
        lower_voltage_limit,
        upper_voltage_limit,
        kw_step_voltage_violation,
        voltage_tolerance,
        num_cpus,
    )
    v_output_df.to_csv(
        output_dir
        / f"Hosting_capacity_voltage_test_{lower_voltage_limit}_{upper_voltage_limit}.csv"
    )

    # calculate the hosting capacity based on thermal ratings constraint
    th_output_df = calculate_thermal_hosting_capacity(
        loads,
        master_file,
        thermal_loading_limit,
        kw_step_thermal_violation,
        thermal_tolerance,
        elements_with_extra_threshold,
        num_cpus,
    )
    th_output_df.to_csv(output_dir / f"Hosting_capacity_thermal_test_{thermal_loading_limit}.csv")

    #################### for plotting results ####################################################

    load_bus = pd.DataFrame()
    load_bus["Load"] = th_output_df["Load"]  #
    load_bus["Bus"] = th_output_df["Bus"]
    node_distance = pd.DataFrame()
    node_distance["Node"] = dss.Circuit.AllNodeNames()
    node_distance["Distance"] = bus_distances

    dist_file = calc_dist(load_bus, node_distance)

    dist_file["Initial_MW"] = th_output_df["Initial_kW"] / 1000
    dist_file[f"Volt_Violation_{lower_voltage_limit}"] = v_output_df["Volt_Violation"] / 1000
    dist_file[f"Thermal_Violation_{thermal_loading_limit}"] = (
        th_output_df["Thermal_Violation"] / 1000
    )

    plot_df = dist_file.sort_values(by=["Distance"])

    # plot voltage violation scenarios
    plot_capacity_V(
        plot_df,
        "Initial_MW",
        f"Volt_Violation_{lower_voltage_limit}",
        output_dir,
    )

    # plot thermal violation
    # TODO: Priti, is the last parameter correct?
    plot_capacity_thermal_1(
        plot_df,
        "Initial_MW",
        f"Thermal_Violation_{thermal_loading_limit}",
        output_dir,
        thermal_loading_limit,
    )

    ### Assuming the hosting capacity is limited by thermal loading ##############################

    ## Difference of initial load and maximum hosting capacity (assuming always thermal limit occurs first)
    diff = th_output_df["Thermal_Violation"] - th_output_df["Initial_kW"]
    new_df = pd.DataFrame()

    new_df["Load"] = th_output_df["Load"]
    new_df["Bus"] = th_output_df["Bus"]
    new_df["Initial_kW"] = th_output_df["Initial_kW"]
    new_df["Hosting_capacity(kW)"] = diff  # additional load it can support

    new_df.to_csv(
        output_dir / f"Additional_HostingCapacity_{thermal_loading_limit}.csv",
        index=False,
    )

    # Find number of ev chargers for each node.
    chargers_3_2_1 = levels_of_charger(th_output_df)
    chargers_3_2_1.to_csv(output_dir / f"Loadwithlevel3_2_1_{thermal_loading_limit}.csv")


def circuit_has_violations(lower_voltage_limit, upper_voltage_limit) -> bool:
    """Returns True if the current circuit has voltage violations."""
    v = np.array(dss.Circuit.AllBusMagPu())
    return np.any(v > upper_voltage_limit) or np.any(v < lower_voltage_limit)


def get_loadings_with_violations(threshold: float) -> dict[str, float]:
    """Return a dict of elements with loading violations."""
    return {
        x: y
        for (x, y) in zip(dss.PDElements.AllNames(), dss.PDElements.AllPctNorm())
        if y >= threshold
    }


def get_loads() -> list[dict]:
    """Return a list of all Loads in the circuit."""
    loads = []
    load_flag = dss.Loads.First()

    while load_flag:
        datum = {
            "name": dss.Loads.Name(),
            "kV": dss.Loads.kV(),
            "kW": dss.Loads.kW(),
            "PF": dss.Loads.PF(),
            "Delta_conn": dss.Loads.IsDelta(),
        }

        cktElement = dss.CktElement
        bus = cktElement.BusNames()[0].split(".")
        datum["kVar"] = (
            float(datum["kW"])
            / float(datum["PF"])
            * math.sqrt(1 - float(datum["PF"]) * float(datum["PF"]))
        )
        datum["bus1"] = bus[0]
        datum["numPhases"] = len(bus[1:])
        datum["phases"] = bus[1:]
        if not datum["numPhases"]:
            datum["numPhases"] = 3
            datum["phases"] = ["1", "2", "3"]
        datum["voltageMag"] = cktElement.VoltagesMagAng()[0]
        datum["voltageAng"] = cktElement.VoltagesMagAng()[1]
        datum["power"] = dss.CktElement.Powers()[0:2]

        loads.append(datum)
        load_flag = dss.Loads.Next()

    return loads


def list_bus_distances() -> list[float]:
    """Return a list of bus distances."""
    distances = []
    for node in dss.Circuit.AllNodeNames():
        dss.Circuit.SetActiveBus(node)
        distances.append(dss.Bus.Distance())
    return distances


def calculate_voltage_hosting_capacity(
    loads,
    master_file,
    lower_limit,
    upper_limit,
    kw_step_voltage_violation,
    voltage_tolerance,
    num_cpus,
) -> pd.DataFrame:
    """Calculate hosting capacity based on voltage and store the result in a DataFrame."""
    v_lst = []
    v_output_list = []
    v_threshold = []
    v_allow_limit = []
    v_names = []
    v_bus_name = []
    v_default_load = []
    v_maxv = []
    v_minv = []
    with ProcessPoolExecutor(max_workers=num_cpus) as executor:
        for result in executor.map(
            node_V_capacity_check,
            loads,
            itertools.repeat(master_file),
            itertools.repeat(lower_limit),
            itertools.repeat(upper_limit),
            itertools.repeat(kw_step_voltage_violation),
            itertools.repeat(voltage_tolerance),
        ):
            load, cap_limit, vmax, vmin = result
            logger.debug("Ran voltage check on load=%s", load["name"])
            v_allowable_load = cap_limit - kw_step_voltage_violation
            v_threshold.append(cap_limit)
            v_allow_limit.append(v_allowable_load)
            v_names.append(load["name"])
            v_bus_name.append(load["bus1"])
            v_default_load.append(load["kW"])
            v_maxv.append(vmax)
            v_minv.append(vmin)

        v_lst = [v_names, v_bus_name, v_default_load, v_threshold, v_allow_limit, v_maxv, v_minv]
        v_output_list = list(map(list, zip(*v_lst)))
        v_output_df = pd.DataFrame(
            v_output_list,
            columns=[
                "Load",
                "Bus",
                "Initial_kW",
                "Volt_Violation",
                "Maximum_kW",
                "Max_voltage",
                "Min_voltage",
            ],
        )
    return v_output_df


def node_V_capacity_check(
    load, master_file, lower_limit, upper_limit, kw_step_voltage_violation, tolerance
):
    """Returns the lowest capacity at which a violation occurs."""
    compile_circuit(master_file)
    initial_kW = load["kW"] + kw_step_voltage_violation
    initial_value = initial_kW
    new_kW = initial_kW
    logger.debug("initial_kW=%s", initial_kW)
    bisector = ViolationBisector(
        lower_bound=initial_kW, initial_value=initial_value, tolerance=tolerance
    )
    done = False
    vmax = 0.0
    vmin = 0.0
    cap_limit = 0.0

    while not done:
        logger.debug("Check voltage violation with kW=%s", new_kW)
        voltages = set_load_and_solve(load["name"], new_kW)
        last_result_violation = circuit_has_violations(lower_limit, upper_limit)
        logger.debug(
            "Checked voltage violation load=%s kW=%s last_result_violation=%s",
            load["name"],
            new_kW,
            last_result_violation,
        )
        new_kW, done = bisector.get_next_value(last_result_violation=last_result_violation)

    cap_limit = bisector.get_lowest_violation()
    set_load_and_solve(load["name"], cap_limit)
    voltages = np.array(dss.Circuit.AllBusMagPu())
    vmax = np.max(voltages)
    vmin = np.min(voltages)
    return load, cap_limit, vmax, vmin


def set_load_and_solve(load_name, kw):
    dss.Text.Command(f"edit Load.{load_name} kW={kw}")
    dss.Text.Command("solve mode = snap")


def calculate_thermal_hosting_capacity(
    loads,
    master_file,
    loading_limit,
    kw_step_thermal_violation,
    thermal_tolerance,
    elements_with_extra_threshold,
    num_cpus,
):
    """Calculate hosting capacity based on voltage and store the result in a DataFrame."""
    th_threshold = []
    th_allow_limit = []
    th_names = []
    th_bus_name = []
    th_default_load = []
    th_lst = []
    with ProcessPoolExecutor(max_workers=num_cpus) as executor:
        for result in executor.map(
            thermal_overload_check,
            loads,
            itertools.repeat(master_file),
            itertools.repeat(loading_limit),
            itertools.repeat(kw_step_thermal_violation),
            itertools.repeat(thermal_tolerance),
            itertools.repeat(elements_with_extra_threshold),
        ):
            load, th_node_cap = result
            logger.debug("Ran thermal check on limit=%s load=%s", loading_limit, load["name"])
            # reduce the value of add_kW
            th_allowable_load = th_node_cap - kw_step_thermal_violation
            th_threshold.append(th_node_cap)
            th_allow_limit.append(th_allowable_load)
            th_names.append(load["name"])
            th_bus_name.append(load["bus1"])
            th_default_load.append(load["kW"])

    th_lst = [
        th_names,
        th_bus_name,
        th_default_load,
        th_threshold,
        th_allow_limit,
    ]
    th_output_list = list(map(list, zip(*th_lst)))
    th_output_df = pd.DataFrame(
        th_output_list,
        columns=["Load", "Bus", "Initial_kW", "Thermal_Violation", "Maximum_kW"],
    )
    return th_output_df


def thermal_overload_check(
    load,
    master_file,
    th_limit,
    kw_step_thermal_violation,
    tolerance,
    elements_with_extra_threshold,
):
    """Returns the lowest capacity at which a violation occurs."""
    compile_circuit(master_file)
    initial_kW = load["kW"] + kw_step_thermal_violation
    new_kW = initial_kW
    logger.debug("initial_kW=%s", initial_kW)
    bisector = ViolationBisector(
        lower_bound=initial_kW, initial_value=initial_kW, tolerance=tolerance
    )
    done = False
    load_name = load["name"]

    while not done:
        # while the elements loadings are within limits keep on increasing
        cmd = f"edit Load.{load_name} kW={new_kW}"
        dss.Text.Command(cmd)
        dss.Text.Command("solve mode = snap")
        loadings = get_loadings_with_violations(th_limit)

        last_result_violation = False
        if not loadings:
            last_result_violation = False
        elif set(loadings).intersection(elements_with_extra_threshold):
            for name, pct_loading in loadings.items():
                if name in elements_with_extra_threshold:
                    if pct_loading >= elements_with_extra_threshold[name]:
                        last_result_violation = True
                        break
                else:
                    last_result_violation = True
                    break
        else:
            last_result_violation = True

        logger.debug(
            "Checked thermal violation load=%s kW=%s last_result_violation=%s",
            load_name,
            new_kW,
            last_result_violation,
        )
        new_kW, done = bisector.get_next_value(last_result_violation=last_result_violation)

    return load, bisector.get_lowest_violation()


class ViolationBisector:
    """Helper class to find the lowest value that will cause a violation."""

    def __init__(self, lower_bound, initial_value=None, tolerance=10):
        self._lower_bound = lower_bound
        self._initial_value = initial_value or lower_bound
        self._cur_value = self._initial_value
        self._last_fail_value = None
        self._found_first_violation = False
        self._lowest_violation = sys.maxsize
        self._highest_pass = -1.0
        self._tolerance = tolerance

    def get_next_value(self, last_result_violation: bool):
        done = False
        if last_result_violation:
            if not self._found_first_violation:
                self._found_first_violation = True
            assert self._cur_value < self._lowest_violation
            self._lowest_violation = self._cur_value
            if self._lowest_violation <= self._lower_bound:
                done = True
            else:
                low = self._highest_pass or self._lower_bound
                self._cur_value = low + ((self._lowest_violation - low) // 2)
        else:
            assert self._highest_pass is None or self._cur_value > self._highest_pass
            self._highest_pass = self._cur_value
            if self._found_first_violation:
                self._cur_value += (self._lowest_violation - self._cur_value) // 2
            else:
                self._cur_value *= 2

        if not done and (self._lowest_violation is not None and self._highest_pass is not None):
            assert (
                self._lowest_violation > self._highest_pass
            ), f"{self._highest_pass=} {self._lowest_violation=}"
            done = self._lowest_violation - self._highest_pass <= self._tolerance

        logger.debug(
            "end last_result=%s cur_value=%s lowest_fail=%s highest_pass=%s",
            last_result_violation,
            self._cur_value,
            self._lowest_violation,
            self._highest_pass,
        )
        return self._cur_value, done

    def get_lowest_violation(self):
        return self._lowest_violation


def compile_circuit(master_file: Path):
    """Compiles a circuit and ensures that execution remains in the current directory."""
    logger.debug("Compile circuit from %s", master_file)
    orig = os.getcwd()
    try:
        dss.Text.Command(f"Compile {master_file}")
    finally:
        os.chdir(orig)


def export_circuit_element_properties(output_dir: Path):
    export_dir = output_dir / "circuit_elements"
    export_dir.mkdir()
    exports = (
        ("Capacitor", dss.Capacitors.Count),
        ("Fuse", dss.Fuses.Count),
        ("Generator", dss.Generators.Count),
        ("Isource", dss.Isource.Count),
        ("Line", dss.Lines.Count),
        ("Load", dss.Loads.Count),
        ("Monitor", dss.Monitors.Count),
        ("PVSystem", dss.PVsystems.Count),
        ("Recloser", dss.Reclosers.Count),
        ("RegControl", dss.RegControls.Count),
        ("Relay", dss.Relays.Count),
        ("Sensor", dss.Sensors.Count),
        ("Transformer", dss.Transformers.Count),
        ("Vsource", dss.Vsources.Count),
        ("XYCurve", dss.XYCurves.Count),
    )

    for class_name, count_func in exports:
        if count_func() > 0:
            filename = export_dir / +f"{class_name}.csv"
            df = dss.utils.class_to_dataframe(class_name)
            df.to_csv(filename)
            logger.info("Exported %s information to %s.", class_name, filename)
        else:
            logger.info("There are no elements of type=%s to export", class_name)

    all_node_names = dss.Circuit.AllNodeNames()
    pd.DataFrame(all_node_names).to_csv(output_dir / "Allnodenames.csv")
