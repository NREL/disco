"""This code calculates the hosting capcity (checks voltage and thermal violation limits) for
a given feeder.
"""

# -*- coding: utf-8 -*-
"""
Created on Wed Sep 18 14:32:29 2019

@author: ppaudyal
"""


import logging
import os
from pathlib import Path

import pandas as pd
import numpy as np
import math
import opendssdirect as dss

from jade.utils.timing_utils import track_timing, Timer
from disco import timer_stats_collector
from .load_distance_from_SS import calc_dist
from .plot_hosting_capacity import (
    plot_capacity_V,
    plot_capacity_thermal_1,
    plot_capacity_thermal_2,
)
from .number_of_ev_chargers import levels_of_charger


logger = logging.getLogger(__name__)


@track_timing(timer_stats_collector)
def run(
    master_file: Path,
    lower_voltage_limit: float,
    upper_voltage_limit: float,
    kw_step_voltage_violation: float,
    kw_step_thermal_violation: float,
    extra_percentages_for_existing_overloads: tuple[float],
    thermal_loading_limits: tuple[float],
    export_circuit_elements: bool,
    # plot_heatmap: bool,
    output_dir: Path,
):
    dss.Text.Command("clear")
    compile_circuit(master_file)
    circuit = dss.Circuit
    ckt_name = circuit.Name()
    logger.info(" Circuit name: %s from %s folder", ckt_name, master_file)

    if export_circuit_elements:
        export_circuit_element_properties(output_dir)

    v_limit = [(lower_voltage_limit, upper_voltage_limit)]
    # TODO: do we need more limits?
    # assert lower_voltage_limit == 0.95
    # v_limit += [(0.975, upper_voltage_limit), (0.985, upper_voltage_limit)]
    # TODO: Priti, how to calculate these programmatically?

    AllNodeNames = circuit.YNodeOrder()

    # --------- Voltage Base kV Information -----
    node_number = len(AllNodeNames)
    Vbase_allnode = [0] * node_number
    ii = 0
    for node in AllNodeNames:
        circuit.SetActiveBus(node)
        Vbase_allnode[ii] = dss.Bus.kVBase() * 1000
        ii = ii + 1

    # --------- Capacitor Information ----------
    capNames = dss.Capacitors.AllNames()
    hCapNames = [None] * len(capNames)
    for i, n in enumerate(capNames):
        hCapNames[i] = str(n)
    hCapNames = str(hCapNames)[1:-1]

    # --------- Regulator Information ----------
    regNames = dss.RegControls.AllNames()
    hRegNames = [None] * len(regNames)
    for i, n in enumerate(regNames):
        hRegNames[i] = str(n)
    hRegNames = str(hRegNames)[1:-1]

    dss.Text.Command("solve mode=snap")
    # dss.Text.Command('export voltages')
    v = np.array(dss.Circuit.AllBusMagPu())

    volt_violation = np.any(v > upper_voltage_limit) or np.any(v < lower_voltage_limit)
    logger.info("Initial condition voltage violation: %s", volt_violation)

    Bus_Distance = []
    for node in AllNodeNames:
        circuit.SetActiveBus(node)
        Bus_Distance.append(dss.Bus.Distance())
    np.savetxt(output_dir / "node_distance.csv", Bus_Distance)

    ####### for thermal overload capapcity #######################################################
    dss.Text.Command("solve mode = snap")
    overloads_filename = output_dir / "overloads.csv"
    dss.Text.Command(f"export Overloads {overloads_filename}")

    # read this overload file and record the ' %Normal' for each line in this file
    overload_df = pd.read_csv(overloads_filename)
    # len(overload_df)
    if len(overload_df) == 0:
        logger.info("No thermal violation initially")
    else:
        logger.info("Thermal violation exists initially")
        logger.info("Overloads: %s", overload_df.head())

    elements = [[], []]
    amps = [[], []]
    new_threshold = [[], []]
    for j in range(len(extra_percentages_for_existing_overloads)):
        for i in range(len(overload_df)):
            overload_df["Element"] = overload_df["Element"].str.strip()
            element = overload_df["Element"][i]
            amp = overload_df[" %Normal"][i]
            element_new_limit = amp + extra_percentages_for_existing_overloads[j]
            elements[j].append(str(element))
            amps[j].append(amp)
            new_threshold[j].append(element_new_limit)

    logger.debug("new_threshold=%s", new_threshold)

    ##############################################################################################
    # get the load data
    [Load, totalkW] = get_loads(dss, circuit, 0, "")

    # calculate the hosting capacity based on voltage constraints
    v_output_df = []
    for j in range(len(v_limit)):
        lmt1 = v_limit[j][0]
        lmt2 = v_limit[j][1]
        v_lst = []
        v_output_list = []
        v_threshold = []
        v_allow_limit = []
        v_names = []
        v_bus_name = []
        v_default_load = []
        v_maxv = []
        v_minv = []
        for i in range(len(Load)):
            logger.info("Run voltage check on load index=%s", i)
            v_node_cap = node_V_capacity_check(
                master_file, Load[i], lmt1, lmt2, kw_step_voltage_violation
            )  # v_node_cap is a list
            v_allowable_load = v_node_cap[0] - kw_step_voltage_violation
            v_threshold.append(v_node_cap[0])
            v_allow_limit.append(v_allowable_load)
            v_names.append(Load[i]["name"])
            v_bus_name.append(Load[i]["bus1"])
            v_default_load.append(Load[i]["kW"])
            v_maxv.append(v_node_cap[1])
            v_minv.append(v_node_cap[2])

        v_lst = [v_names, v_bus_name, v_default_load, v_threshold, v_allow_limit, v_maxv, v_minv]
        v_output_list = list(map(list, zip(*v_lst)))
        # v_output_df[0] = pd.DataFrame(v_output_list, columns = ['Load' , 'Bus', 'Initial_kW', 'Volt_Violation', 'Maximum_kW', 'Max_voltage', 'Min_voltage'])
        v_output_df.append(
            pd.DataFrame(
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
        )

        v_output_df[j].to_csv(output_dir / f"Hosting_capacity_test_{lmt1}.csv")

    # calculate the hosting capacity based on thermal ratings constraint
    th_threshold = [[], []]
    th_allow_limit = [[], []]
    th_names = [[], []]
    th_bus_name = [[], []]
    th_default_load = [[], []]

    th_output_df = []
    for i in range(len(thermal_loading_limits)):
        logger.info("Run thermal check on index=%s limit=%s", i, thermal_loading_limits[i])
        th_lst = []
        for j in range(len(Load)):
            if j == 0:
                continue
            th_node_cap = thermal_overload_check(
                Load[j], thermal_loading_limits[i], i, kw_step_thermal_violation, output_dir
            )  # th_node_cap is a list
            th_allowable_load = (
                th_node_cap[0] - kw_step_thermal_violation
            )  # 5 # th_node_cap[0] is a float  # reduce the value of add_kW
            th_threshold[i].append(th_node_cap[0])
            th_allow_limit[i].append(th_allowable_load)
            th_names[i].append(Load[j]["name"])
            th_bus_name[i].append(Load[j]["bus1"])
            th_default_load[i].append(Load[j]["kW"])

        th_lst = [
            th_names[i],
            th_bus_name[i],
            th_default_load[i],
            th_threshold[i],
            th_allow_limit[i],
        ]
        th_output_list = list(map(list, zip(*th_lst)))
        th_output_df.append(
            pd.DataFrame(
                th_output_list,
                columns=["Load", "Bus", "Initial_kW", "Thermal_Violation", "Maximum_kW"],
            )
        )

        th_output_df[i].to_csv(
            output_dir / f"Thermal_capacity_test_{thermal_loading_limits[i]}.csv"
        )

    #################### for plotting results ####################################################

    load_bus = pd.DataFrame()
    load_bus["Load"] = th_output_df[0]["Load"]  #
    load_bus["Bus"] = th_output_df[0]["Bus"]
    node_distance = pd.DataFrame()
    node_distance["Node"] = AllNodeNames
    node_distance["Distance"] = Bus_Distance

    dist_file = calc_dist(load_bus, node_distance)

    dist_file["Initial_MW"] = th_output_df[0]["Initial_kW"] / 1000
    dist_file["Volt_Violation_0.95"] = v_output_df[0]["Volt_Violation"] / 1000
    dist_file["Volt_Violation_0.975"] = v_output_df[1]["Volt_Violation"] / 1000
    dist_file["Volt_Violation_0.985"] = v_output_df[2]["Volt_Violation"] / 1000

    dist_file["Thermal_Violation_100"] = th_output_df[0]["Thermal_Violation"] / 1000
    # dist_file["Thermal_Violation_120"] = th_output_df[1]["Thermal_Violation"]/1000

    plot_df = dist_file.sort_values(by=["Distance"])

    # plot voltage violation scenarios
    plot_capacity_V(
        plot_df,
        "Initial_MW",
        "Volt_Violation_0.95",
        "Volt_Violation_0.975",
        "Volt_Violation_0.985",
        output_dir,
    )

    # plot thermal violation
    plot_capacity_thermal_1(plot_df, "Initial_MW", "Thermal_Violation_100", output_dir, 100)
    # plot_capacity_thermal_2(plot_df, 'Initial_MW', 'Thermal_Violation_100', 'Thermal_Violation_120', output_dir)

    ### Assuming the hosting capacity is limited by thermal loading ##############################

    ## Difference of initial load and maximum hosting capacity (assuming always thermal limit occurs first) ##

    for i in range(len(thermal_loading_limits)):
        diff = th_output_df[i]["Thermal_Violation"] - th_output_df[i]["Initial_kW"]
        new_df = pd.DataFrame()

        new_df["Load"] = th_output_df[i]["Load"]
        new_df["Bus"] = th_output_df[i]["Bus"]
        new_df["Initial_kW"] = th_output_df[i]["Initial_kW"]
        new_df["Hosting_capacity(kW)"] = diff  # additional load it can support

        new_df.to_csv(
            output_dir / "Additional_HostingCapacity_" + str(thermal_loading_limits[i]) + ".csv",
            index=False,
        )

        ## find number of ev chargers for each node ##

        chargers_3_2_1 = levels_of_charger(th_output_df[i])
        chargers_3_2_1.to_csv(
            output_dir / "Loadwithlevel3_2_1_" + str(thermal_loading_limits[i]) + ".csv"
        )


# --------- Load Information ----------
@track_timing(timer_stats_collector)
def get_loads(dss, circuit, loadshape_flag, loadshape_folder):
    data = []
    load_flag = dss.Loads.First()
    total_load = 0

    while load_flag:
        load = dss.Loads
        datum = {
            "name": load.Name(),
            "kV": load.kV(),
            "kW": load.kW(),
            "PF": load.PF(),
            "Delta_conn": load.IsDelta(),
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

        data.append(datum)
        load_flag = dss.Loads.Next()
        total_load += datum["kW"]

    return [data, total_load]


############################ for voltage violation capacity ######################################
@track_timing(timer_stats_collector)
def node_V_capacity_check(master_file, which_load, low_lmt, high_lmt, kw_step_voltage_violation):
    initial_kW = which_load["kW"]
    logger.debug("initial_kW=%s", initial_kW)
    tmp_kW = initial_kW
    volt_violation = False
    v = None

    while not volt_violation:
        with Timer(timer_stats_collector, "check_voltage_violation_after_increasing_kw"):
            # while the voltages are within limits keep on increasing
            new_kW = tmp_kW + kw_step_voltage_violation
            logger.info("Check voltage violation with kW=%s", new_kW)
            dss.Text.Command("edit Load." + str(which_load["name"]) + " kW=" + str(new_kW))
            dss.Text.Command("solve mode = snap")
            v = np.array(dss.Circuit.AllBusMagPu())
            volt_violation = np.any(v > high_lmt) or np.any(v < low_lmt)
            logger.debug("Voltage violation = %s", volt_violation)
            if volt_violation:
                vmax = np.max(v)
                vmin = np.min(v)
                cap_limit = new_kW
                # TODO: no point in doing this, right?
                # dss.Text.Command("edit Load." + str(which_load["name"]) + " kW=" + str(initial_kW))
                compile_circuit(master_file)
            else:
                tmp_kW = new_kW

    return [cap_limit, vmax, vmin]


@track_timing(timer_stats_collector)
def thermal_overload_check(
    which_load, th_limit, case, kw_step_thermal_violation, output_dir: Path
):
    initial_kW = which_load["kW"]
    logger.debug("initial_kW=%s", initial_kW)
    tmp_kW = initial_kW
    thermal_violation = False

    while not thermal_violation:
        with Timer(timer_stats_collector, "check_thermal_violation_after_increasing_kw"):
            # while the elements loadings are within limits keep on increasing
            new_kW = tmp_kW + kw_step_thermal_violation
            logger.info("Check thermal violation with kW=%s", new_kW)
            dss.Text.Command("edit Load." + str(which_load["name"]) + " kW=" + str(new_kW))
            dss.Text.Command("solve mode = snap")
            overloads_filename = output_dir / "overloads.csv"
            dss.Text.Command("export Overloads {overloads_filename}")
            report = pd.read_csv(overloads_filename)
            report["Element"] = report["Element"].str.strip()

            if len(report) == 0:  # if no any overload element
                thermal_violation = False

            elif report["Element"].isin(elements[case]).any():
                for i in range(len(report)):
                    if report["Element"][i] in elements[case]:
                        indx_ = elements[case].index(report["Element"][i])  # find the index of
                        if report[" %Normal"][i] >= new_threshold[case][indx_]:
                            thermal_violation = True  # just exit here (get out of for loop)
                            break
                        else:
                            thermal_violation = False
                    else:
                        # check the percentage normal if greater than specified % then only violation
                        if report[" %Normal"][i] >= th_limit:
                            thermal_violation = True
                            break
                        else:
                            thermal_violation = False

            else:
                # check the percentage normal if greater than specified % then only violation
                for i in range(len(report)):
                    if report[" %Normal"][i] >= th_limit:
                        thermal_violation = True
                        break
                    else:
                        thermal_violation = False

            logger.debug("thermal_violation=%s", thermal_violation)
            if thermal_violation:
                logger.debug("thermal_violation=%s", thermal_violation)
                dss.Text.Command(f"export Capacity {output_dir / 'capacity.csv'}")
                dss.Text.Command(f"export Currents {output_dir / 'currents.csv'}")
                cap_limit = new_kW
                # TODO: no point in doing this, right?
                # dss.Text.Command("edit Load." + str(which_load["name"]) + " kW=" + str(initial_kW))
                compile_circuit(master_file)
            else:
                tmp_kW = new_kW

    return [cap_limit]


@track_timing(timer_stats_collector)
def compile_circuit(master_file: Path):
    logger.info("Compile circuit from %s", master_file)
    orig = os.getcwd()
    try:
        dss.Text.Command(f"Compile {master_file}")
    finally:
        os.chdir(orig)


@track_timing(timer_stats_collector)
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

    all_node_names = circuit.YNodeOrder()
    pd.DataFrame(all_node_names).to_csv(output_dir / "Allnodenames.csv")
