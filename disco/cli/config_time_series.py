#!/usr/bin/env python

"""Creates JADE configuration for stage 1 of pydss_simulation pipeline."""

import logging

import click

from jade.common import CONFIG_FILE
from jade.loggers import setup_logging
from jade.utils.utils import load_data
from PyDSS.reports.pv_reports import PF1_SCENARIO, CONTROL_MODE_SCENARIO

from disco.enums import SimulationType
from disco.extensions.pydss_simulation.pydss_configuration import PyDssConfiguration
from disco.extensions.pydss_simulation.estimate_run_minutes import generate_estimate_run_minutes
from disco.pydss.common import ConfigType
from disco.pydss.pydss_configuration_base import get_default_reports_file

logger = logging.getLogger(__name__)


def _callback_is_enabled(_, __, value):
    if value is None:
        return None
    return {"true": True, "false": False}[value.lower()]


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
    "--calc-estimated-run-minutes/--no-calc-estimated-run-minutes",
    is_flag=True,
    default=True,
    show_default=True,
    help="Calculate estimated per-job runtime by parsing the OpenDSS files.",
)
@click.option(
    "--feeder-losses",
    type=click.Choice(("true", "false"), case_sensitive=False),
    callback=_callback_is_enabled,
    default=None,
    show_default=True,
    help="Whether to enable the Feeder Losses report. If not set, use the value in "
         "--reports-filename.",
)
@click.option(
    "--pv-clipping",
    type=click.Choice(("true", "false"), case_sensitive=False),
    callback=_callback_is_enabled,
    default=None,
    show_default=True,
    help="Whether to enable the PV clipping report. If not set, use the value in "
         "--reports-filename.",
)
@click.option(
    "--pv-curtailment",
    type=click.Choice(("true", "false"), case_sensitive=False),

    callback=_callback_is_enabled,
    default=None,
    show_default=True,
    help="Whether to enable the PV curtailment report. If not set, use the value in "
         "--reports-filename.",
)
@click.option(
    "--thermal-metrics",
    type=click.Choice(("true", "false"), case_sensitive=False),
    callback=_callback_is_enabled,
    default=None,
    show_default=True,
    help="Whether to enable the Thermal Metrics report. If not set, use the value in "
         "--reports-filename.",
)
@click.option(
    "--voltage-metrics",
    type=click.Choice(("true", "false"), case_sensitive=False),
    callback=_callback_is_enabled,
    default=None,
    show_default=True,
    help="Whether to enable the Voltage Metrics report. If not set, use the value in "
         "--reports-filename.",
)
@click.option(
    "-r",
    "--reports-filename",
    default=get_default_reports_file(SimulationType.QSTS),
    show_default=True,
    help="PyDSS report options",
)
@click.option(
    "--skip-night/--no-skip-night",
    default=False,
    is_flag=True,
    show_default=True,
    help="Don't run convergence algorithm or collect data during nighttime hours."
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
    calc_estimated_run_minutes,
    feeder_losses,
    pv_clipping,
    pv_curtailment,
    thermal_metrics,
    voltage_metrics,
    reports_filename=None,
    order_by_penetration=True,
    skip_night=False,
    verbose=False,
):
    """Create JADE configuration for time series simulations."""
    level = logging.DEBUG if verbose else logging.INFO
    setup_logging(__name__, None, console_level=level)

    simulation_config = PyDssConfiguration.get_default_pydss_simulation_config()
    simulation_config["Project"]["Simulation Type"] = SimulationType.QSTS.value
    simulation_config["Reports"] = load_data(reports_filename)["Reports"]
    for report in simulation_config["Reports"]["Types"]:
        if report["name"] == "Feeder Losses" and feeder_losses is not None:
            report["enabled"] = feeder_losses
        if report["name"] == "PV Clipping" and pv_clipping is not None:
            report["enabled"] = pv_clipping
        if report["name"] == "PV Curtailment" and pv_curtailment is not None:
            report["enabled"] = pv_curtailment
        if report["name"] == "Thermal Metrics" and thermal_metrics is not None:
            report["enabled"] = thermal_metrics
        if report["name"] == "Voltage Metrics" and voltage_metrics is not None:
            report["enabled"] = voltage_metrics

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
    
    if calc_estimated_run_minutes:
        generate_estimate_run_minutes(config)

    if skip_night:
        pydss_sim_config = config.get_pydss_config(ConfigType.SIMULATION_CONFIG)
        pydss_sim_config["Project"]["Simulation range"] = {"start": "06:00:00", "end": "18:00:00"}
        # Note that we are using the same convergence error threshold percent.
        config.set_pydss_config(ConfigType.SIMULATION_CONFIG, pydss_sim_config)

    config.dump(filename=config_file)

    print(f"Created {config_file} for TimeSeries Analysis")
