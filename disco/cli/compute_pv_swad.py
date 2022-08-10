# -*- coding: utf-8 -*-
"""
Created on Thu Feb 24 15:26:33 2022

@author: senam
"""

import logging
import os
import sys
from pathlib import Path

import click
import opendssdirect as dss

from jade.loggers import setup_logging


logger = logging.getLogger("swad")


def get_load_info():
    """
    This function returns the following information pertaining to loads on a feeder:
        load name
        bus where each load is connected
        kW load capacity
        number of phases
    """
    load_info = {}
    # load_names = dss.Loads.AllNames()

    dss.Circuit.SetActiveClass("Load")
    flag = dss.ActiveClass.First()
    while flag > 0:
        name = dss.CktElement.Name()
        bus = dss.CktElement.BusNames()[0]
        load_kw = sum(dss.CktElement.Powers()[0::2])
        nphases = dss.CktElement.NumPhases()
        load_info[name] = {"name": name, "bus": bus, "kW": load_kw, "nphases": nphases}
        flag = dss.ActiveClass.Next()

    return load_info


def get_existing_pvs():
    total_existing_pv = 0
    existing_pv_dict = {}
    existing_pv_dist_dict = {}
    flag = dss.PVsystems.First()

    while flag > 0:
        bus = dss.Properties.Value("bus1")
        if bus not in existing_pv_dict:
            dss.Circuit.SetActiveBus(bus)
            existing_pv_dist_dict[bus] = dss.Bus.Distance()
            existing_pv_dict[bus] = dss.PVsystems.kVARated()
        else:
            existing_pv_dict[bus] += dss.PVsystems.kVARated()

        total_existing_pv += dss.PVsystems.kVARated()
        flag = dss.PVsystems.Next()

    return total_existing_pv, existing_pv_dict, existing_pv_dist_dict


def compute_weighted_average_pv_distance(load_info, option="size"):
    wavg_pv_distance = 0
    total_existing_pv, existing_pv_dict, existing_pv_dist_dict = get_existing_pvs()

    slack_dico = {k: v * existing_pv_dist_dict[k] for k, v in existing_pv_dict.items()}

    if option == "size":
        wavg_pv_distance = sum(slack_dico.values()) / max(0.001, total_existing_pv)

    elif option == "nodal_ratio":
        load_per_bus = {v["bus"]: v["kW"] for k, v in load_info.items()}

        slack_dico = {
            k: v * existing_pv_dist_dict[k] / max(0.001, load_per_bus[k])
            for k, v in existing_pv_dict.items()
        }
        ratio_sum = sum([v / max(0.001, load_per_bus[k]) for k, v in existing_pv_dict.items()])
        wavg_pv_distance = sum(slack_dico.values()) / max(0.001, ratio_sum)

    return wavg_pv_distance


def collect_weighted_average_pv_distance(filename: Path, option):
    orig = os.getcwd()
    try:
        reply = dss.Text.Command(f"compile '{filename}'")
        if reply is not None:
            logger.error("Failed to compile OpenDSS model %s: %s", filename, reply)
            sys.exit(1)

        load_info = get_load_info()
        avg = compute_weighted_average_pv_distance(load_info, option=option)
        logger.info("Computed weighted average PV distance %s for %s", avg, filename)
    finally:
        os.chdir(orig)
    return avg


def collect_weighted_average_pv_distances(path: Path, option):
    results = []
    for substation_path in path.iterdir():
        if substation_path.is_dir():
            for feeder_path in substation_path.iterdir():
                pv_path = feeder_path / "PVDeployments"
                if pv_path.is_dir():
                    for filename in pv_path.iterdir():
                        job_name = filename.name.replace(".dss", "")
                        fields = job_name.split("__")
                        if len(fields) != 5:
                            continue
                        substation, feeder, placement, sample, penetration_level = fields
                        wavg_pv_distance = collect_weighted_average_pv_distance(filename, option)
                        results.append(
                            {
                                "job_name": job_name,
                                "substation": substation,
                                "feeder": feeder,
                                "placement": placement,
                                "sample": sample,
                                "penetration_level": penetration_level,
                                "weighted_average_pv_distance": wavg_pv_distance,
                                "option": option,
                            }
                        )
    return results


@click.command()
@click.argument("path", type=click.Path(exists=True), callback=lambda _, __, x: Path(x))
@click.option(
    "--option",
    default="size",
    type=click.Choice(["size", "nodal_ratio"], case_sensitive=False),
    show_default=True,
    help="Computation methodology",
)
@click.option(
    "--verbose", is_flag=True, default=False, show_default=True, help="Enable verbose logging"
)
def compute_pv_swad(path, option, verbose):
    """Compute weighted average PV distance for each model. Requires an EnergyMeter."""
    level = logging.DEBUG if verbose else logging.INFO
    setup_logging("swad", None, console_level=level, packages=["disco"])
    results = collect_weighted_average_pv_distances(path, option)
    if results:
        output_file = path / "weighted_average_pv_distances.csv"
        fields = results[0].keys()
        with open(output_file, "w") as f_out:
            f_out.write(",".join(fields))
            f_out.write("\n")
            for result in results:
                f_out.write(",".join([str(x) for x in result.values()]))
                f_out.write("\n")
        logger.info("Created %s", output_file)
    else:
        logger.info("There were no PV deployment files in %s", path)


if __name__ == "__main__":
    compute_pv_swad()
