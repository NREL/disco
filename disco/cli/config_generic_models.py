import logging
import os

import click

from jade.loggers import setup_logging
from jade.utils.utils import load_data

from PyDSS.reports.pv_reports import PF1_SCENARIO, CONTROL_MODE_SCENARIO

from disco.cli.config_snapshot import (
    switch_snapshot_to_qsts,
    common_snapshot_options,
    make_simulation_config,
)
from disco.cli.config_time_series import common_time_series_options
from disco.models.base import OpenDssDeploymentModel, SimulationModel
from disco.models.power_flow_generic_models import (
    PowerFlowSnapshotSimulationModel,
    PowerFlowTimeSeriesSimulationModel,
)
from disco.distribution.deployment_parameters import DeploymentParameters
from disco.enums import SimulationType
from disco.extensions.pydss_simulation.pydss_configuration import PyDssConfiguration
from disco.pydss.common import ConfigType


logger = logging.getLogger(__name__)


@click.group()
def config_generic_models():
    """Create a JADE config file from a set of generic OpenDSS models."""


@click.command()
@click.argument("power-flow-config-file", type=click.Path(exists=True))
@common_snapshot_options
def snapshot(
    power_flow_config_file,
    config_file,
    exports_filename,
    reports_filename,
    with_loadshape,
    auto_select_time_points,
    auto_select_time_points_search_duration_days,
    shuffle,
    store_per_element_data,
    strip_whitespace,
    volt_var_curve,
    verbose,
):
    """Create a JADE config file for a snapshot power-flow simulation."""
    pf_config = PowerFlowSnapshotSimulationModel.from_file(power_flow_config_file)
    level = logging.DEBUG if verbose else logging.INFO
    setup_logging(__name__, None, console_level=level, packages=["disco"])

    simulation_config, scenarios = make_simulation_config(
        reports_filename,
        exports_filename,
        pf_config.include_pf1,
        pf_config.include_control_mode,
        store_per_element_data,
        with_loadshape,
        auto_select_time_points,
        auto_select_time_points_search_duration_days,
    )
    config = PyDssConfiguration()
    simulation_type = SimulationType.QSTS if with_loadshape else SimulationType.SNAPSHOT
    for job in pf_config.jobs:
        job = DeploymentParameters(
            model_type="SnapshotImpactAnalysisModel",
            name=job.name,
            blocked_by=job.blocked_by,
            base_case=None,
            is_base_case=False,
            estimated_run_minutes=job.estimated_run_minutes,
            deployment=OpenDssDeploymentModel(
                is_standalone=True,
                deployment_file=job.opendss_model_file,
                substation=job.substation or "NA",
                feeder=job.feeder or "NA",
                dc_ac_ratio=1.0,
                directory=os.path.dirname(job.opendss_model_file),
                kva_to_kw_rating=1.0,
                project_data=job.project_data,
                pydss_controllers=job.pydss_controllers,
            ),
            simulation=SimulationModel(
                start_time=pf_config.start_time,
                end_time=pf_config.start_time,
                step_resolution=900,
                simulation_type=simulation_type,
            ),
        )
        config.add_job(job)

    config.check_job_consistency()

    if volt_var_curve is not None:
        if config.has_pydss_controllers() and pf_config.include_control_mode:
            config.update_volt_var_curve(volt_var_curve)
        else:
            logger.warning(
                "Setting a volt_var_curve has no effect when there is no %s scenario.",
                CONTROL_MODE_SCENARIO,
            )

    config.set_pydss_config(ConfigType.SIMULATION_CONFIG, simulation_config)
    config.set_pydss_config(ConfigType.SCENARIOS, scenarios)

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


@click.command()
@click.argument("power-flow-config-file", type=click.Path(exists=True))
@common_time_series_options
def time_series(
    power_flow_config_file,
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
):
    """Create JADE configuration for time series simulations."""
    level = logging.DEBUG if verbose else logging.INFO
    setup_logging(__name__, None, console_level=level, packages=["disco"])

    pf_config = PowerFlowTimeSeriesSimulationModel.from_file(power_flow_config_file)
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
            report["store_all_time_points"] = store_all_time_points
        if report["name"] == "Voltage Metrics" and voltage_metrics is not None:
            report["enabled"] = voltage_metrics
        if report["name"] in ("Thermal Metrics", "Voltage Metrics"):
            report["store_per_element_data"] = store_per_element_data
            report["store_all_time_points"] = store_all_time_points
        if report["name"] == "Capacitor State Change Counts" and capacitor_changes is not None:
            report["enabled"] = capacitor_changes
        if report["name"] == "RegControl Tap Number Change Counts" and regcontrol_changes is not None:
            report["enabled"] = regcontrol_changes

    exports = {} if exports_filename is None else load_data(exports_filename)
    scenarios = []
    if pf_config.include_control_mode:
        scenarios.append(
            PyDssConfiguration.make_default_pydss_scenario(CONTROL_MODE_SCENARIO, exports),
        )
    if pf_config.include_pf1:
        scenarios.append(
            PyDssConfiguration.make_default_pydss_scenario(PF1_SCENARIO, exports),
        )

    config = PyDssConfiguration()
    for job in pf_config.jobs:
        job = DeploymentParameters(
            model_type="TimeSeriesAnalysisModel",
            name=job.name,
            blocked_by=job.blocked_by,
            base_case=None,
            is_base_case=False,
            estimated_run_minutes=job.estimated_run_minutes,
            deployment=OpenDssDeploymentModel(
                is_standalone=True,
                deployment_file=job.opendss_model_file,
                substation=job.substation or "NA",
                feeder=job.feeder or "NA",
                dc_ac_ratio=1.0,
                directory=os.path.dirname(job.opendss_model_file),
                kva_to_kw_rating=1.0,
                project_data=job.project_data,
                pydss_controllers=job.pydss_controllers,
            ),
            simulation=SimulationModel(
                start_time=pf_config.start_time,
                end_time=pf_config.end_time,
                step_resolution=pf_config.step_resolution,
                simulation_type=SimulationType.QSTS,
            ),
        )
        config.add_job(job)

    config.check_job_consistency()

    if volt_var_curve is not None:
        if config.has_pydss_controllers() and pf_config.include_control_mode:
            config.update_volt_var_curve(volt_var_curve)
        else:
            logger.warning(
                "Setting a volt_var_curve has no effect when there is no %s scenario.",
                CONTROL_MODE_SCENARIO,
            )

    if skip_night:
        pydss_sim_config = config.get_pydss_config(ConfigType.SIMULATION_CONFIG)
        pydss_sim_config["project"]["simulation_range"] = {"start": "06:00:00", "end": "18:00:00"}
        # Note that we are using the same convergence error threshold percent.
        config.set_pydss_config(ConfigType.SIMULATION_CONFIG, pydss_sim_config)

    config.set_pydss_config(ConfigType.SIMULATION_CONFIG, simulation_config)
    config.set_pydss_config(ConfigType.SCENARIOS, scenarios)
    config.dump(filename=config_file)

    print(f"Created {config_file} for TimeSeries Analysis")


config_generic_models.add_command(snapshot)
config_generic_models.add_command(time_series)
