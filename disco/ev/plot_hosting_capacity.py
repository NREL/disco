# -*- coding: utf-8 -*-
"""
Created on Wed Sep 18 15:55:53 2019

@author: ppaudyal
"""
import matplotlib.pyplot as plt
import os


def plot_capacity_V(file, caseA, caseB, caseC, caseD, feeder):
    fig, ax1 = plt.subplots(nrows=1, figsize=(14, 8))  # figsize=(18,12)
    vplot1 = ax1.plot(range(len(file)), file[caseA], c="k", marker="o", label="Initial load")
    vplot2 = ax1.plot(
        range(len(file)),
        file[caseB],
        c="r",
        marker="+",
        label="Volt violation MW [range:(0.95, 1.05)]",
    )
    vplot3 = ax1.plot(
        range(len(file)),
        file[caseC],
        c="g",
        marker="*",
        label="Volt violation MW [range:(0.975, 1.05)]",
    )
    vplot4 = ax1.plot(
        range(len(file)),
        file[caseD],
        c="b",
        marker=".",
        label="Volt violation MW [range:(0.985, 1.05)]",
    )
    ax1.margins(x=0)
    ax1.tick_params(axis="both", which="major", labelsize=33)
    ax1.tick_params(axis="both", which="minor", labelsize=33)
    ax1.set_ylabel("Power (MW)", fontsize=33)
    ax1.legend(loc="upper right", fontsize=33)
    ax1.set_ylim(-2, 65)
    ax1.grid()
    # ax1.set_xlabel('Load # according to distance from SS', fontsize=40)
    ax1.set_xlabel(
        "Feeder Node (where highest is furthest from substation)", fontsize=33
    )  ##'Load indices, according to distance from SS \n(load #' + str(len(file)) + ' is the furthest from SS)'
    # plt.tight_layout()
    plt.savefig(str(feeder) + "_Cap_by_V_limit.png", bbox_inches="tight", dpi=150)


def plot_capacity_thermal_2(file, caseA, caseB, caseC, feeder):
    fig, ax1 = plt.subplots(nrows=1, figsize=(14, 8))
    thplot1 = ax1.plot(range(len(file)), file[caseA], c="k", marker="o", label="Initial load")
    thplot2 = ax1.plot(
        range(len(file)),
        file[caseB],
        c="r",
        marker="+",
        label="Thermal violation MW[100% loading]",
    )
    thplot3 = ax1.plot(
        range(len(file)),
        file[caseC],
        c="b",
        marker="*",
        label="Thermal violation MW[120% loading]",
    )
    ax1.margins(x=0)
    ax1.tick_params(axis="both", which="major", labelsize=30)
    ax1.tick_params(axis="both", which="minor", labelsize=30)
    ax1.set_ylabel("Power (MW)", fontsize=30)
    ax1.legend(loc="upper right", fontsize=30)
    ax1.grid()
    # ax1.set_xlabel('Load # according to distance from SS', fontsize=40)
    ax1.set_xlabel(
        "Feeder Node (where highest is furthest from substation)", fontsize=30
    )  # ax1.set_xlabel('Load indices, according to distance from SS \n(load #' + str(len(file)) + ' is the furthest from SS)', fontsize=40)
    plt.tight_layout()
    plt.savefig(str(feeder) + "_Cap_by_thermal_limit.png", dpi=150)


def plot_capacity_thermal_1(file, caseA, caseB, feeder, extra):
    fig, ax1 = plt.subplots(nrows=1, figsize=(14, 8))
    thplot1 = ax1.plot(range(len(file)), file[caseA], c="k", marker="o", label="Initial load")
    thplot2 = ax1.plot(
        range(len(file)), file[caseB], c="r", marker="+", label="Thermal violation MW"
    )
    ax1.margins(x=0)
    ax1.tick_params(axis="both", which="major", labelsize=33)
    ax1.tick_params(axis="both", which="minor", labelsize=33)
    ax1.set_ylabel("Power (MW)", fontsize=33)
    ax1.legend(loc="upper right", fontsize=33)
    ax1.grid()
    # ax1.set_xlabel('Load # according to distance from SS', fontsize=40)
    ax1.set_xlabel(
        "Feeder Node (where highest is furthest from substation)", fontsize=33
    )  # ax1.set_xlabel('Load indices, according to distance from SS \n(load #' + str(len(file)) + ' is the furthest from SS)', fontsize=40)
    # fig.tight_layout()
    plt.savefig(
        str(feeder) + "_Cap_by_thermal_limit_" + str(extra) + ".png", bbox_inches="tight", dpi=150
    )


if __name__ == "__main__":

    import pandas as pd
    import load_distance_from_SS

    limit = 100
    feeder_folder = "BaseCaseWRR074"
    os.chdir(str(os.getcwd()) + "/" + str(feeder_folder))
    # Read Csv
    th_output_df = pd.read_csv("Thermal_capacity_test_" + str(feeder_folder) + "_100.csv")
    v_output_df = []
    lmt = [0.95, 0.975, 0.985]
    for i in range(len(lmt)):
        v_output_df.append(
            pd.read_csv("Hosting_capacity_test_" + str(feeder_folder) + "_" + str(lmt[i]) + ".csv")
        )

    bus_dist_df = pd.read_csv("node_distance_" + str(feeder_folder) + ".csv", header=None)
    bus_dist_df.columns = ["Distance"]
    Bus_Distance = bus_dist_df["Distance"].to_list()
    node_name_df = pd.read_csv("Allnodenames.csv")
    AllNodeNames = node_name_df["Node"].to_list()

    load_bus = pd.DataFrame()
    load_bus["Load"] = th_output_df["Load"]
    load_bus["Bus"] = th_output_df["Bus"]  # load_bus.to_csv("   ") save as csv if required
    node_distance = pd.DataFrame()
    node_distance["Node"] = AllNodeNames
    node_distance[
        "Distance"
    ] = Bus_Distance  # node_distance.to_csv("    ") save as csv if required

    dist_file_lst = load_distance_from_SS.calc_dist(load_bus, node_distance)

    dist_file = dist_file_lst[0]

    dist_file["Initial_MW"] = th_output_df["Initial_kW"] / 1000
    dist_file["Volt_Violation_0.95"] = v_output_df[0]["Volt_Violation"] / 1000
    dist_file["Volt_Violation_0.975"] = v_output_df[1]["Volt_Violation"] / 1000
    dist_file["Volt_Violation_0.985"] = v_output_df[2]["Volt_Violation"] / 1000

    dist_file["Thermal_Violation_100"] = th_output_df["Thermal_Violation"] / 1000

    plot_df = dist_file.sort_values(by=["Distance"])

    os.chdir("../Results_HC/update_for_paper_jan2021")
    # plot voltage violation scenarios
    plot_capacity_V(
        plot_df,
        "Initial_MW",
        "Volt_Violation_0.95",
        "Volt_Violation_0.975",
        "Volt_Violation_0.985",
        feeder_folder,
    )

    # plot thermal violation
    plot_capacity_thermal_1(plot_df, "Initial_MW", "Thermal_Violation_100", feeder_folder, limit)
