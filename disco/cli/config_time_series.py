#!/usr/bin/env python

"""Creates JADE configuration for stage 1 of pydss_simulation pipeline."""

import logging
import sys

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


def callback_is_enabled(_, __, value):
    if value is None:
        return None
    return {"true": True, "false": False}[value.lower()]


COMMON_TIME_SERIES_OPTIONS = (
    click.option(
        "-c",
        "--config-file",
        default=CONFIG_FILE,
        show_default=True,
        help="JADE config file to create",
    ),
    click.option(
        "--feeder-losses",
        type=click.Choice(("true", "false"), case_sensitive=False),
        callback=callback_is_enabled,
        default=None,
        show_default=True,
        help="Whether to enable the Feeder Losses report. If not set, use the value in "
        "--reports-filename.",
    ),
    click.option(
        "--pv-clipping",
        type=click.Choice(("true", "false"), case_sensitive=False),
        callback=callback_is_enabled,
        default=None,
        show_default=True,
        help="Whether to enable the PV clipping report. If not set, use the value in "
        "--reports-filename.",
    ),
    click.option(
        "--pv-curtailment",
        type=click.Choice(("true", "false"), case_sensitive=False),
        callback=callback_is_enabled,
        default=None,
        show_default=True,
        help="Whether to enable the PV curtailment report. If not set, use the value in "
        "--reports-filename.",
    ),
    click.option(
        "--thermal-metrics",
        type=click.Choice(("true", "false"), case_sensitive=False),
        callback=callback_is_enabled,
        default=None,
        show_default=True,
        help="Whether to enable the Thermal Metrics report. If not set, use the value in "
        "--reports-filename.",
    ),
    click.option(
        "--voltage-metrics",
        type=click.Choice(("true", "false"), case_sensitive=False),
        callback=callback_is_enabled,
        default=None,
        show_default=True,
        help="Whether to enable the Voltage Metrics report. If not set, use the value in "
        "--reports-filename.",
    ),
    click.option(
        "--capacitor-changes",
        type=click.Choice(("true", "false"), case_sensitive=False),
        callback=callback_is_enabled,
        default=None,
        show_default=True,
        help="Whether to enable the Capacitor State Changes report. If not set, use the value in "
        "--reports-filename.",
    ),
    click.option(
        "--regcontrol-changes",
        type=click.Choice(("true", "false"), case_sensitive=False),
        callback=callback_is_enabled,
        default=None,
        show_default=True,
        help="Whether to enable the RegControl Tap Number Changes report. If not set, use the "
        "value in --reports-filename.",
    ),
    click.option(
        "--export-data-tables",
        default=False,
        is_flag=True,
        show_default=True,
        help="Export collected circuit element properties as tables.",
    ),
    click.option(
        "--exports-filename",
        default=None,
        show_default=True,
        help="PyDSS export options, default is None.",
    ),
    click.option(
        "-r",
        "--reports-filename",
        default=get_default_reports_file(SimulationType.QSTS),
        show_default=True,
        help="PyDSS report options",
    ),
    click.option(
        "--skip-night/--no-skip-night",
        default=False,
        is_flag=True,
        show_default=True,
        help="Don't run controls or collect data during nighttime hours.",
    ),
    click.option(
        "--store-all-time-points/--no-store-all-time-points",
        is_flag=True,
        default=False,
        show_default=True,
        help="Store per-element data at all time points for thermal and voltage metrics.",
    ),
    click.option(
        "--store-per-element-data/--no-store-per-element-data",
        is_flag=True,
        default=False,
        show_default=True,
        help="Store per-element data in thermal and voltage metrics.",
    ),
    click.option(
        "-v",
        "--volt-var-curve",
        default=None,
        help="Update the PyDSS volt-var curve name. If not set, use the pre-configured curve.",
    ),
    click.option(
        "--verbose",
        is_flag=True,
        default=False,
        help="Enable debug logging",
    ),
)


def common_time_series_options(func):
    for option in reversed(COMMON_TIME_SERIES_OPTIONS):
        func = option(func)
    return func


@click.command()
@click.argument("inputs")
@common_time_series_options
@click.option(
    "-e",
    "--estimated-run-minutes",
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
    "--dc-ac-ratio",
    default=None,
    type=float,
    help="Set a custom DC-AC ratio for PV Systems.",
)
@click.option(
    "--pf1/--no-pf1",
    is_flag=True,
    default=True,
    show_default=True,
    help="Include PF1 scenario or not",
)
@click.option(
    "--control-mode/--no-control-mode",
    is_flag=True,
    default=True,
    show_default=True,
    help="Include control_mode scenario or not",
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
def time_series(
    inputs,
    config_file,
    feeder_losses,
    pv_clipping,
    pv_curtailment,
    thermal_metrics,
    voltage_metrics,
    capacitor_changes,
    regcontrol_changes,
    export_data_tables,
    exports_filename,
    reports_filename,
    skip_night,
    store_all_time_points,
    store_per_element_data,
    volt_var_curve,
    verbose,
    estimated_run_minutes,
    calc_estimated_run_minutes,
    dc_ac_ratio,
    pf1,
    control_mode,
    order_by_penetration,
):
    """Create JADE configuration for time series simulations."""
    level = logging.DEBUG if verbose else logging.INFO
    setup_logging(__name__, None, console_level=level, packages=["disco"])

    if not pf1 and not control_mode:
        logger.error("At least one of '--pf1' or '--control-mode' must be set.")
        sys.exit(1)

    simulation_config = PyDssConfiguration.get_default_pydss_simulation_config()
    simulation_config["project"]["simulation_type"] = SimulationType.QSTS.value
    simulation_config["reports"] = load_data(reports_filename)["reports"]
    simulation_config["exports"]["export_data_tables"] = export_data_tables
    for report in simulation_config["reports"]["types"]:
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
        if report["name"] in ("Thermal Metrics", "Voltage Metrics"):
            report["store_all_time_points"] = store_all_time_points
            report["store_per_element_data"] = store_per_element_data
        if report["name"] == "Capacitor State Change Counts" and capacitor_changes is not None:
            report["enabled"] = capacitor_changes
        if report["name"] == "RegControl Tap Number Change Counts" and regcontrol_changes is not None:
            report["enabled"] = regcontrol_changes

    exports = {} if exports_filename is None else load_data(exports_filename)
    scenarios = []
    if control_mode:
        scenarios.append(
            PyDssConfiguration.make_default_pydss_scenario(CONTROL_MODE_SCENARIO, exports)
        )
    if pf1:
        scenarios.append(PyDssConfiguration.make_default_pydss_scenario(PF1_SCENARIO, exports))
    config = PyDssConfiguration.auto_config(
        inputs,
        simulation_config=simulation_config,
        scenarios=scenarios,
        order_by_penetration=order_by_penetration,
        estimated_run_minutes=estimated_run_minutes,
        dc_ac_ratio=dc_ac_ratio,
    )

    has_pydss_controllers = config.has_pydss_controllers()
    if control_mode and not has_pydss_controllers:
        scenarios_config = config.get_pydss_config(ConfigType.SCENARIOS)
        assert scenarios_config[0]["name"] == CONTROL_MODE_SCENARIO
        scenarios_config.pop(0)
        logger.info(
            "Excluding %s scenario because there are no pydss controllers.", CONTROL_MODE_SCENARIO
        )
        config.set_pydss_config(ConfigType.SCENARIOS, scenarios_config)

    if volt_var_curve is not None:
        if has_pydss_controllers and control_mode:
            config.update_volt_var_curve(volt_var_curve)
        else:
            logger.warning(
                "Setting a volt_var_curve has no effect when there is no %s scenario.",
                CONTROL_MODE_SCENARIO,
            )

    if calc_estimated_run_minutes:
        generate_estimate_run_minutes(config)

    if skip_night:
        pydss_sim_config = config.get_pydss_config(ConfigType.SIMULATION_CONFIG)
        pydss_sim_config["project"]["simulation_range"] = {"start": "06:00:00", "end": "18:00:00"}
        # Note that we are using the same convergence error threshold percent.
        config.set_pydss_config(ConfigType.SIMULATION_CONFIG, pydss_sim_config)

    config.dump(filename=config_file)

    print(f"Created {config_file} for TimeSeries Analysis")
