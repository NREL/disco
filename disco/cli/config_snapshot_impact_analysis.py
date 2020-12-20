#!/usr/bin/env python

"""Creates JADE configuration for stage 1 of pydss_simulation pipeline."""

import logging
import os

import click

from jade.common import CONFIG_FILE
from jade.loggers import setup_logging
from jade.jobs.job_post_process import JobPostProcess
from jade.utils.utils import load_data
import disco
from disco.enums import SimulationType
from disco.extensions.pydss_simulation.pydss_configuration import PyDssConfiguration

ESTIMATED_EXEC_SECS_PER_JOB = 5

logger = logging.getLogger(__name__)


@click.command()
@click.argument("inputs")
@click.option(
    "-c",
    "--config-file",
    default=CONFIG_FILE,
    show_default=True,
    help="JADE config file to create",
)
@click.option(
    "-e",
    "--exports-filename",
    default=os.path.join(
        os.path.dirname(getattr(disco, "__path__")[0]),
        "disco",
        "pydss",
        "config",
        "Exports.toml",
    ),
    show_default=True,
    help="PyDSS export options",
)
@click.option(
    "--verbose",
    is_flag=True,
    default=False,
    help="Enable debug logging",
)
def snapshot_impact_analysis(
    inputs,
    config_file,
    exports_filename=None,
    verbose=False,
):
    """Create JADE configuration for snapshot impact analysis."""
    level = logging.DEBUG if verbose else logging.INFO
    setup_logging(__name__, None, console_level=level)
    post_process = JobPostProcess("disco.analysis", "SnapshotImpactAnalysis")

    simulation_config = PyDssConfiguration.get_default_pydss_simulation_config()
    simulation_config["Project"]["Simulation Type"] = SimulationType.SNAPSHOT.value

    exports = {} if exports_filename is None else load_data(exports_filename)
    scenarios = [
        PyDssConfiguration.make_default_pydss_scenario(
            "scenario",
            exports=exports,
        )
    ]
    config = PyDssConfiguration.auto_config(
        inputs,
        exports_filename=exports_filename,
        job_post_process_config=post_process.serialize(),
        simulation_config=simulation_config,
        scenarios=scenarios,
        estimated_exec_secs_per_job=ESTIMATED_EXEC_SECS_PER_JOB,
    )

    config.dump(filename=config_file)
    print(f"Created {config_file} for SnapshotImpactAnalysis")
