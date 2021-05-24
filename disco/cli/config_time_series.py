#!/usr/bin/env python

"""Creates JADE configuration for stage 1 of pydss_simulation pipeline."""

import logging
import os
import sys

import click

from jade.common import CONFIG_FILE
from jade.loggers import setup_logging
from jade.jobs.job_post_process import JobPostProcess
from jade.utils.utils import load_data
from PyDSS.reports.pv_reports import PF1_SCENARIO, CONTROL_MODE_SCENARIO

import disco
from disco.enums import SimulationType
from disco.extensions.pydss_simulation.pydss_configuration import PyDssConfiguration

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
    "-e", "--estimated-run-minutes",
    type=int,
    help="Estimated per-job runtime. Default is None.",
)
@click.option(
    "-r",
    "--reports-filename",
    default=os.path.join(
        os.path.dirname(getattr(disco, "__path__")[0]),
        "disco",
        "extensions",
        "pydss_simulation",
        "time_series_reports.toml",
    ),
    show_default=True,
    help="PyDSS report options",
)
@click.option(
    "--order-by-penetration/--no-order-by-penetration",
    default=False,
    show_default=True,
    help="Make jobs with higher penetration levels blocked by those with lower levels. This "
         "can be beneficial if you want the higher-penetration-level jobs to be "
         "canceled if a job with a lower penetration level fails. However, it can significantly "
         "reduce the number of jobs that can run simultaneously.",
)
@click.option(
    "--verbose",
    is_flag=True,
    default=False,
    help="Enable debug logging",
)
def time_series(
    inputs,
    config_file,
    estimated_run_minutes,
    reports_filename=None,
    order_by_penetration=True,
    verbose=False,
):
    """Create JADE configuration for time series simulations."""
    level = logging.DEBUG if verbose else logging.INFO
    setup_logging(__name__, None, console_level=level)

    simulation_config = PyDssConfiguration.get_default_pydss_simulation_config()
    simulation_config["Project"]["Simulation Type"] = SimulationType.QSTS.value
    simulation_config["Reports"] = load_data(reports_filename)["Reports"]

    scenarios = [
        PyDssConfiguration.make_default_pydss_scenario(CONTROL_MODE_SCENARIO),
        PyDssConfiguration.make_default_pydss_scenario(PF1_SCENARIO),
    ]
    config = PyDssConfiguration.auto_config(
        inputs,
        simulation_config=simulation_config,
        scenarios=scenarios,
        order_by_penetration=order_by_penetration,
        estimated_run_minutes=estimated_run_minutes,
    )

    config.dump(filename=config_file)
    print(f"Created {config_file} for TimeSeries Analysis")
