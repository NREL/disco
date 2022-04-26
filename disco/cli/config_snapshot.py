#!/usr/bin/env python

"""Creates JADE configuration for stage 1 of pydss_simulation pipeline."""

import logging
import os
import sys
from datetime import timedelta

import click

from jade.common import CONFIG_FILE
from jade.loggers import setup_logging
from jade.utils.utils import load_data
from PyDSS.common import SnapshotTimePointSelectionMode
from PyDSS.reports.pv_reports import PF1_SCENARIO, CONTROL_MODE_SCENARIO

from disco.enums import SimulationType, AnalysisType
from disco.extensions.pydss_simulation.pydss_configuration import PyDssConfiguration
from disco.pydss.pydss_configuration_base import (
    get_default_exports_file,
    get_default_reports_file,
    DEFAULT_LOAD_SHAPE_START_TIME,
)
from disco.pydss.common import SCENARIO_NAME_DELIMITER

ESTIMATED_EXEC_SECS_PER_JOB = 10

logger = logging.getLogger(__name__)


@click.command()
@click.argument("inputs")
@click.option(
    "-c", "--config-file",
    default=CONFIG_FILE,
    show_default=True,
    help="JADE config file to create",
)
@click.option(
    "--dc-ac-ratio",
    default=None,
    type=float,
    help="Set a custom DC-AC ratio for PV Systems.",
)
@click.option(
    "-e", "--exports-filename",
    default=get_default_exports_file(SimulationType.SNAPSHOT, AnalysisType.IMPACT_ANALYSIS),
    show_default=True,
    help="PyDSS export options",
)
@click.option(
    "-r", "--reports-filename",
    default=get_default_reports_file(SimulationType.SNAPSHOT),
    show_default=True,
    help="PyDSS report options.",
)
@click.option(
    "--pf1/--no-pf1",
    is_flag=True,
    default=True,
    show_default=True,
    help="Include PF1 scenario or not"
)
@click.option(
    "--order-by-penetration/--no-order-by-penetration",
    default=False,
    show_default=True,
    help="Make jobs with higher penetration levels blocked by those with lower levels.",
)
@click.option(
    "--with-loadshape/--no-with-loadshape",
    is_flag=True,
    required=True,
    help="Configure snapshot simulation with loashape profile."
)
@click.option(
    "--auto-select-time-points/--no-auto-select-time-points",
    is_flag=True,
    default=True,
    show_default=True,
    help="Automatically select the time point based on max PV-load ratio. Only applicable if "
         "--with-loadshape."
)
@click.option(
    "-d", "--auto-select-time-points-search-duration-days",
    default=365,
    show_default=True,
    help="Search duration in days. Only applicable with --auto-select-time-points.",
)
@click.option(
    "--shuffle/--no-shuffle",
    is_flag=True,
    default=True,
    show_default=True,
    help="Shuffle order of jobs.",
)
@click.option(
    "--store-per-element-data/--no-store-per-element-data",
    is_flag=True,
    default=False,
    show_default=True,
    help="Store per-element data in thermal and voltage metrics.",
)
@click.option(
    "--strip-whitespace/--no-strip-whitespace",
    is_flag=True,
    default=False,
    show_default=True,
    help="Strip whitespace in file.",
)
@click.option(
    "-v",
    "--volt-var-curve",
    default=None,
    help="Update the PyDSS volt-var curve name. If not set, use the pre-configured curve.",
)
@click.option(
    "--verbose",
    is_flag=True,
    default=False,
    help="Enable debug logging",
)
def snapshot(
    inputs,
    config_file,
    dc_ac_ratio,
    exports_filename,
    reports_filename,
    pf1,
    order_by_penetration,
    with_loadshape,
    auto_select_time_points,
    auto_select_time_points_search_duration_days,
    shuffle,
    store_per_element_data,
    strip_whitespace,
    volt_var_curve,
    verbose=False,
):
    """Create JADE configuration for snapshot simulations."""
    level = logging.DEBUG if verbose else logging.INFO
    setup_logging(__name__, None, console_level=level)

    simulation_config = PyDssConfiguration.get_default_pydss_simulation_config()
    simulation_config["reports"] = load_data(reports_filename)["reports"]
    for report in simulation_config["reports"]["types"]:
        if report["name"] in ("Thermal Metrics", "Voltage Metrics"):
            report["store_per_element_data"] = store_per_element_data

    if with_loadshape:
        simulation_config["project"]["simulation_type"] = SimulationType.QSTS.value
        names = [CONTROL_MODE_SCENARIO]
        if pf1:
            names.append(PF1_SCENARIO)
        if auto_select_time_points:
            scenarios = []
            for scenario_name in names:
                for mode in SnapshotTimePointSelectionMode:
                    if mode == SnapshotTimePointSelectionMode.NONE:
                        continue
                    name = f"{scenario_name}{SCENARIO_NAME_DELIMITER}{mode.value}"
                    duration_min = float(auto_select_time_points_search_duration_days) * 24 * 60
                    scenario = PyDssConfiguration.make_default_pydss_scenario(name)
                    scenario["snapshot_time_point_selection_config"] = {
                        "mode": mode.value,
                        "start_time": DEFAULT_LOAD_SHAPE_START_TIME,
                        "search_duration_min": duration_min,
                    }
                    scenarios.append(scenario)
        else:
            scenarios = [PyDssConfiguration.make_default_pydss_scenario(x) for x in names]
    else:
        exports = {} if exports_filename is None else load_data(exports_filename)
        simulation_config["project"]["simulation_type"] = SimulationType.SNAPSHOT.value
        scenarios = [
            PyDssConfiguration.make_default_pydss_scenario(
                "scenario",
                exports=exports,
            )
        ]

    config = PyDssConfiguration.auto_config(
        inputs,
        simulation_config=simulation_config,
        scenarios=scenarios,
        order_by_penetration=order_by_penetration,
        estimated_exec_secs_per_job=ESTIMATED_EXEC_SECS_PER_JOB,
        dc_ac_ratio=dc_ac_ratio,
    )

    if volt_var_curve is not None:
        config.update_volt_var_curve(volt_var_curve)

    # We can't currently predict how long each job will take. If we did, we could set
    # estimated_run_minutes for each job.
    # Shuffle the jobs randomly so that we have a better chance of getting batches with similar
    # runtimes.
    if shuffle:
        config.shuffle_jobs()

    if with_loadshape:
        config = switch_snapshot_to_qsts(config)

    indent = None if strip_whitespace else 2
    config.dump(filename=config_file, indent=indent)
    print(f"Created {config_file} for Snapshot Analysis")


def switch_snapshot_to_qsts(config):
    """Use QSTS at one time point to perform SNAPSHOT simulation with loadshape profile"""
    for job in config.iter_pydss_simulation_jobs():
        job.model.simulation.simulation_type = SimulationType.QSTS
        job.model.simulation.end_time = job.model.simulation.start_time + timedelta(
            seconds=job.model.simulation.step_resolution
        )
    return config
