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
import re
import shutil
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
import time

import sqlite3

import pandas as pd
import numpy as np
import math
import opendssdirect as dss

from .load_distance_from_SS import calc_dist
# from .plot_hosting_capacity import (
#     plot_capacity_V,
#     plot_capacity_thermal_1,
#     plot_capacity_thermal_2,
# )

from .number_of_ev_chargers import levels_of_charger


logger = logging.getLogger(__name__)
logger.setLevel(logging.ERROR)


def run(
    master_file: Path,
    feeder_name: str,
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
    screen_all_buses: bool = True,
):

    from disco.ev.dynamic_hc_model import _find_loads_file

    # Build a snapshot-mode copy of the master as a sibling of the original
    # (so relative `Redirect Lines.dss` etc. still resolve). Original is never modified.
    original_lines = master_file.read_text().splitlines()
    kept_lines = [ln for ln in original_lines
                  if not ln.strip().lower().startswith(("solve", "export", "plot"))]

    # If loads reference time-series shapes, strip the shape attributes into a
    # static loads copy and skip parsing the (then unused) loadshape file —
    # snapshot mode ignores yearly= anyway, so results are unchanged.
    static_loads = None
    try:
        loads_file = _find_loads_file(master_file)
    except FileNotFoundError:
        loads_file = None   # loads defined inline in the master, or no loads at all
    if loads_file is not None and re.search(
            r'\b(yearly|daily|duty)\s*=', loads_file.read_text(), re.IGNORECASE):
        static_loads = master_file.with_name(f"Loads_static_{os.getpid()}.dss")
        static_loads.write_text(re.sub(
            r'\s*(yearly|daily|duty)=[^\s]+', '',
            loads_file.read_text(), flags=re.IGNORECASE))

        loads_name = loads_file.name.lower()
        rewritten = []
        for ln in kept_lines:
            m = re.match(r'\s*redirect\s+"?([^"\s]+\.dss)"?', ln, re.IGNORECASE)
            if m and Path(m.group(1)).name.lower() == loads_name:
                rewritten.append(f'Redirect "{static_loads.name}"')
            elif m and "loadshape" in Path(m.group(1)).name.lower():
                rewritten.append("!" + ln)
            else:
                rewritten.append(ln)
        kept_lines = rewritten

    kept_lines.append("Solve mode=snapshot")

    snapshot_master = master_file.with_name(f"{master_file.stem}_snapshot_{os.getpid()}.dss")
    snapshot_master.write_text("\n".join(kept_lines) + "\n")


    try:
        #shutil.copyfile(master_file, output_dir / "Master.dss")
        return _run(
            master_file=snapshot_master,
            feeder_name=feeder_name,
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
            screen_all_buses=screen_all_buses,
        )
    finally:
        #os.rename(backup_file, master_file)
        #shutil.move(str(backup_file), str(master_file))
        snapshot_master.unlink(missing_ok=True)
        if static_loads is not None:
            static_loads.unlink(missing_ok=True)


def _run(
    master_file: Path,
    feeder_name: str,
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
    screen_all_buses: bool = True,
):
    db_path = output_dir / "disco_ev_hc.db"
    conn = sqlite3.connect(db_path)
    t0 = time.perf_counter()


    
    dss.Text.Command("clear")
    compile_circuit(master_file)
    
    try:
    
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

        if circuit_has_violations(lower_voltage_limit, upper_voltage_limit):
            logger.warning("Initial condition has voltage violation before EV load is added")
            #print("violation exists initially")

        # logger.warning(
        #     "Initial condition voltage violation: %s",
        #     circuit_has_violations(lower_voltage_limit, upper_voltage_limit),
        # )
        bus_distances = list_bus_distances()
        #np.savetxt(output_dir / "node_distance.csv", bus_distances)
        
        node_df = pd.DataFrame({
            "node": dss.Circuit.AllNodeNames(),
            "distance": bus_distances,
        })
        node_df.to_sql("bus_distances", conn, if_exists="replace", index=False)

        coords_df, lines_df = _extract_topology()
        coords_df.to_sql("bus_coordinates", conn, if_exists="replace", index=False)
        lines_df.to_sql("line_segments", conn, if_exists="replace", index=False)

        ####### for thermal overload capapcity #######################################################
        overloads = get_loadings_with_violations(thermal_loading_limit)
        if overloads:
            logger.warning("Thermal violation exists initially")
            #logger.warning("Overloads: %s", overloads)
        else:
            logger.info("No thermal violation initially")

        elements_with_extra_threshold = {
            k: v + extra_percentage_for_existing_overloads for k, v in overloads.items()
        }

        logger.debug("new_threshold=%s", elements_with_extra_threshold)
        #loads = get_loads()
        loads = get_probe_loads() if screen_all_buses else get_loads()

        v_output_df = calculate_voltage_hosting_capacity(
            loads,
            master_file,
            lower_voltage_limit,
            upper_voltage_limit,
            kw_step_voltage_violation,
            voltage_tolerance,
            num_cpus,
            screen_all_buses = screen_all_buses,
        )
        # v_output_df.to_csv(
        #     output_dir
        #     / f"Hosting_capacity_voltage_test_{lower_voltage_limit}_{upper_voltage_limit}.csv"
        # )
        v_output_df.to_sql("voltage_screen", conn, if_exists="replace", index=False)
        
        # calculate the hosting capacity based on thermal ratings constraint
        th_output_df = calculate_thermal_hosting_capacity(
            loads,
            master_file,
            thermal_loading_limit,
            kw_step_thermal_violation,
            thermal_tolerance,
            elements_with_extra_threshold,
            num_cpus,
            screen_all_buses = screen_all_buses,
        )
        th_output_df.to_sql("thermal_screen", conn, if_exists="replace", index=False)

        #################### for plotting results ####################################################

        load_bus = pd.DataFrame()
        #load_bus["Load"] = th_output_df["Load"]  #
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


        ## Hosting capacity = min(voltage, thermal) - initial, per bus
        hc_join = th_output_df[["Bus", "Initial_kW", "Maximum_kW"]].rename(
            columns={"Maximum_kW": "Maximum_kW_thermal"}
        ).merge(
            v_output_df[["Bus", "Maximum_kW"]].rename(columns={"Maximum_kW": "Maximum_kW_voltage"}),
            on="Bus", how="outer",
        )
        
        hosting_capacity_df = pd.DataFrame()
        hosting_capacity_df["Bus"] = hc_join["Bus"]
        hosting_capacity_df["Initial_kW"] = hc_join["Initial_kW"]
        hosting_capacity_df["Maximum_kW"] = np.minimum(
            hc_join["Maximum_kW_voltage"], hc_join["Maximum_kW_thermal"]
        )
        hosting_capacity_df["Hosting_capacity_kW"] = np.maximum(
            hosting_capacity_df["Maximum_kW"] - hosting_capacity_df["Initial_kW"], 0.0
        )
        hosting_capacity_df["Binding_constraint"] = np.where(
            hc_join["Maximum_kW_voltage"] < hc_join["Maximum_kW_thermal"], "voltage", "thermal"
        )

        hosting_capacity_df.to_sql("hosting_capacity", conn, if_exists="replace", index=False)
        

        # Find number of ev chargers for each node.
        
        chargers_3_2_1 = levels_of_charger(th_output_df)
        chargers_3_2_1.to_sql("chargers", conn, if_exists="replace", index=False)
        dist_file.to_sql("bus_distances", conn, if_exists="replace", index=False)

        _write_simulation_metadata(                                  # ← Step 4
            conn,
            feeder_name=feeder_name,
            lower_voltage_limit=lower_voltage_limit,
            upper_voltage_limit=upper_voltage_limit,
            thermal_loading_limit=thermal_loading_limit,
            run_timestamp=pd.Timestamp.now().isoformat(),
            runtime_seconds=round(time.perf_counter() - t0, 2),
            screen_all_buses=screen_all_buses,
        )




        return v_output_df, th_output_df, plot_df

    finally:
        conn.close()

def circuit_has_violations(lower_voltage_limit, upper_voltage_limit) -> bool:
    """Returns True if the current circuit has voltage violations OR the solver failed."""
    if not dss.Solution.Converged():
        return True
    
    v = np.array(dss.Circuit.AllBusMagPu())
    v = v[v > 0.1]   # de-energized nodes (open ties, isolated islands) are not voltage violations

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
        # datum["kVar"] = (
        #     float(datum["kW"])
        #     / float(datum["PF"])
        #     * math.sqrt(1 - float(datum["PF"]) * float(datum["PF"]))
        # )
        datum["kVar"] = dss.Loads.kvar()

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

def get_service_xfmr_secondary_buses(max_kv_ln: float = 1.0) -> set:
    """Stripped bus names on the LV side of service transformers.

    Winding 1 is the primary; windings 2..n are secondaries. The kV-base
    filter drops MV secondary windings (e.g. the substation transformer).
    """
    candidates = set()
    flag = dss.Transformers.First()
    while flag:
        for b in dss.CktElement.BusNames()[1:]:
            candidates.add(b.split(".")[0].lower())
        flag = dss.Transformers.Next()

    buses = set()
    for bus in candidates:
        dss.Circuit.SetActiveBus(bus)
        if 0 < dss.Bus.kVBase() < max_kv_ln:
            buses.add(bus)
    return buses


def get_probe_loads(exclude_source: bool = True) -> list[dict]:
    """Add a small probe Load at every non-source bus on top of any existing
    loads. The probe's physical kW (1.0) is a placeholder — the bisector
    overwrites it on iteration 1. """
    source_bus = None
    if exclude_source:
        sources = dss.Vsources.AllNames()
        if sources:
            dss.Vsources.Name(sources[0])
            source_bus = dss.CktElement.BusNames()[0].split(".")[0].lower()

        # Sum real-load kW by stripped bus name — becomes Initial_kW for each probe.
    baseline_kw_by_bus: dict[str, float] = {}
    real_flag = dss.Loads.First()
    while real_flag:
        bus_str = dss.CktElement.BusNames()[0].split(".")[0].lower()
        baseline_kw_by_bus[bus_str] = baseline_kw_by_bus.get(bus_str, 0.0) + dss.Loads.kW()
        real_flag = dss.Loads.Next()

      
    xfmr_lv_buses = get_service_xfmr_secondary_buses()
    
    probes = []
    for bus in dss.Circuit.AllBusNames():
        bus_lower = bus.lower()
        if exclude_source and bus_lower == source_bus:
            continue

        dss.Circuit.SetActiveBus(bus)
        nodes = list(dss.Bus.Nodes())
        if not nodes:
            continue

        kv_ln = dss.Bus.kVBase()
        if kv_ln == 0:
            logger.warning(
                "Skipping bus %s for probe-load injection: kVBase()==0 "
                "(check the model — every bus should have a defined kV base)",
                bus,
            )
            continue

        if kv_ln < 1.0 and bus_lower not in xfmr_lv_buses:
            continue
        
        nphases = len(nodes)
        kv = kv_ln * np.sqrt(3) if nphases == 3 else kv_ln

        name = f"probe_{bus_lower}"
        bus1 = f"{bus}." + ".".join(str(n) for n in nodes)
        dss.Text.Command(
            f"New Load.{name} Bus1={bus1} Phases={nphases} "
            f"kV={kv:.6f} kW=1.0 PF=1.0 conn=wye Model=1"
        )

        probes.append({
            "name": name,
            "kV": kv,
            "kW": baseline_kw_by_bus.get(bus_lower, 0.0),            # reported as Initial_kW; probe contributes no baseline
            "PF": 1.0,
            "Delta_conn": False,
            "kVar": 0.0,
            "bus1": bus_lower,
            "numPhases": nphases,
            "phases": [str(n) for n in nodes],
            "voltageMag": 0.0,
            "voltageAng": 0.0,
            "power": [0.0, 0.0],
        })
    return probes





def list_bus_distances() -> list[float]:
    """Return a list of bus distances."""
    _ensure_energymeter_at_source()
    distances = []
    for node in dss.Circuit.AllNodeNames():
        dss.Circuit.SetActiveBus(node)
        distances.append(round(dss.Bus.Distance(), 2))
    return distances


def calculate_voltage_hosting_capacity(
    loads,
    master_file,
    lower_limit,
    upper_limit,
    kw_step_voltage_violation,
    voltage_tolerance,
    num_cpus,
    screen_all_buses = False,
) -> pd.DataFrame:
    """Calculate hosting capacity based on voltage and store the result in a DataFrame."""
    v_lst = []
    v_output_list = []
    v_threshold = []
    v_allow_limit = []
    #v_names = []
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
            itertools.repeat(screen_all_buses),
        ):
            load, cap_limit, vmax, vmin = result
            logger.debug("Ran voltage check on load=%s", load["name"])
            v_allowable_load = cap_limit - kw_step_voltage_violation
            v_threshold.append(cap_limit)
            v_allow_limit.append(v_allowable_load)
            #v_names.append(load["name"])
            v_bus_name.append(load["bus1"])
            v_default_load.append(load["kW"])
            v_maxv.append(vmax)
            v_minv.append(vmin)

        v_lst = [v_bus_name, v_default_load, v_threshold, v_allow_limit, v_maxv, v_minv]
        v_output_list = list(map(list, zip(*v_lst)))
        v_output_df = pd.DataFrame(
            v_output_list,
            columns=[
                #"Load",
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
    load, master_file, lower_limit, upper_limit, kw_step_voltage_violation, tolerance,
    with_probes,
):
    """Returns the lowest capacity at which a violation occurs."""
    compile_circuit(master_file, with_probes=with_probes)
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
    return load, cap_limit + load["kW"], vmax, vmin


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
    screen_all_buses: bool = False,
):
    """Calculate hosting capacity based on voltage and store the result in a DataFrame."""
    th_threshold = []
    th_allow_limit = []
    #th_names = []
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
            itertools.repeat(screen_all_buses),
        ):
            load, th_node_cap = result
            logger.debug("Ran thermal check on limit=%s load=%s", loading_limit, load["name"])
            # reduce the value of add_kW
            th_allowable_load = th_node_cap - kw_step_thermal_violation
            th_threshold.append(th_node_cap)
            th_allow_limit.append(th_allowable_load)
            #th_names.append(load["name"])
            th_bus_name.append(load["bus1"])
            th_default_load.append(load["kW"])

    th_lst = [
        #th_names,
        th_bus_name,
        th_default_load,
        th_threshold,
        th_allow_limit,
    ]
    th_output_list = list(map(list, zip(*th_lst)))
    th_output_df = pd.DataFrame(
        th_output_list,
        columns=[
            #"Load", 
            "Bus", 
            "Initial_kW", "Thermal_Violation", "Maximum_kW"],
    )
    return th_output_df


def thermal_overload_check(
    load,
    master_file,
    th_limit,
    kw_step_thermal_violation,
    tolerance,
    elements_with_extra_threshold,
    with_probes,
):
    """Returns the lowest capacity at which a violation occurs."""
    compile_circuit(master_file, with_probes=with_probes)
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

    return load, bisector.get_lowest_violation() + load["kW"]


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
        self.UPPER_CAP = 1e6  # This is an arbitrary number that is sufficiently high to be above any hosting capacity.

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
                if self._cur_value >= self.UPPER_CAP:                  # <-- added
                    self._lowest_violation = self.UPPER_CAP            # <-- added
                    done = True                                        # <-- added
                else:
                    self._cur_value = min(self._cur_value * 2, self.UPPER_CAP)

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


def compile_circuit(master_file: Path, with_probes: bool = False) -> None:
    """Compiles a circuit and ensures that execution remains in the current directory."""
    logger.debug("Compile circuit from %s", master_file)
    orig = os.getcwd()
    try:
        dss.Text.Command(f"Compile [{master_file}]")
        dss.Text.Command("Set ControlMode=OFF") # wenbo added, to freeze control
        _ensure_energymeter_at_source()
        if with_probes:
            get_probe_loads() 
    finally:
        os.chdir(orig)

def _ensure_energymeter_at_source() -> None:
    """If the master DSS doesn't define an EnergyMeter, place one on the
    first PD element at the source bus. Required for dss.Bus.Distance()
    to return non-zero values."""
    if dss.Meters.Count() > 0:
        return

    sources = dss.Vsources.AllNames()
    if not sources:
        return

    dss.Vsources.Name(sources[0])
    source_bus = dss.CktElement.BusNames()[0].split(".")[0]
    dss.Circuit.SetActiveBus(source_bus)

    candidates = dss.Bus.LineList()
    if not candidates:
        candidates = [
            e for e in dss.Bus.AllPDEatBus()
            if not e.lower().startswith("vsource.")
        ]

    if not candidates:
        logger.warning(
            "No PD element found at source bus %s; bus distances will be 0",
            source_bus,
        )
        return

    target = candidates[0]
    dss.Text.Command(f"New EnergyMeter.AutoMeter element={target} terminal=1")
    logger.info("Auto-added EnergyMeter on %s for distance computation", target)

def _write_simulation_metadata(conn, **kwargs) -> None:
    """Write a key/value table of run-config parameters into the SQLite DB."""
    rows = [{"key": k, "value": str(v)} for k, v in kwargs.items()]
    pd.DataFrame(rows).to_sql("simulation_metadata", conn, if_exists="replace", index=False)


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


def _extract_topology():
    def _bus_name(bus):
        return bus.split(".")[0].lower()

    coords = []
    for bus in dss.Circuit.AllBusNames():
        dss.Circuit.SetActiveBus(bus)
        x, y = dss.Bus.X(), dss.Bus.Y()
        if x != 0.0 or y != 0.0:   # OpenDSS returns 0,0 when no coord set
            coords.append({"Bus": bus.lower(), "X": x, "Y": y})

    lines = []
    line_name = dss.Lines.First()
    while line_name:
        lines.append({
            "Element_Type": "Line",
            "Element": dss.Lines.Name(),
            "From_Bus": _bus_name(dss.Lines.Bus1()),
            "To_Bus": _bus_name(dss.Lines.Bus2()),
            "Length":   dss.Lines.Length(),
        })
        line_name = dss.Lines.Next()

    transformer_name = dss.Transformers.First()
    while transformer_name:
        dss.Circuit.SetActiveElement(f"Transformer.{dss.Transformers.Name()}")
        buses = dss.CktElement.BusNames()
        if len(buses) >= 2:
            lines.append({
                "Element_Type": "Transformer",
                "Element": dss.Transformers.Name(),
                "From_Bus": _bus_name(buses[0]),
                "To_Bus": _bus_name(buses[1]),
                "Length": 0.0,
            })
        transformer_name = dss.Transformers.Next()

    return pd.DataFrame(coords), pd.DataFrame(lines)
