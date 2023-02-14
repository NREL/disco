"""Make hosting capacity summary tables for all jobs in a batch."""

import csv
import itertools
import json
import logging
from collections import namedtuple
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import click

from jade.common import CONFIG_FILE, JOBS_OUTPUT_DIR
from jade.jobs.job_configuration_factory import create_config_from_file
from jade.loggers import setup_logging
from jade.jobs.results_aggregator import ResultsAggregator

from PyDSS.node_voltage_metrics import VOLTAGE_METRIC_FIELDS_TO_INCLUDE_AS_PASS_CRITERIA
from PyDSS.pydss_results import PyDssResults, PyDssScenarioResults
from PyDSS.reports.pv_reports import PF1_SCENARIO, CONTROL_MODE_SCENARIO
from PyDSS.thermal_metrics import create_summary_from_dict

from disco.pipelines.utils import ensure_jade_pipeline_output_dir
from disco.pydss.common import SCENARIO_NAME_DELIMITER


JobInfo = namedtuple(
    "JobInfo", ["name", "substation", "feeder", "placement", "sample", "penetration_level"]
)
SNAPSHOT_TIME_POINT_MAPPING = {
    "max_pv_load_ratio": "Max PV to Load Ratio",
    "max_load": "Max Load",
    "daytime_min_load": "Min Daytime Load",
    "pv_minus_load": "Max PV minus Load",
}


logger = logging.getLogger(__name__)


def parse_batch_results(output_dir):
    """Parse the results from all jobs in a JADE output directory."""
    output_path = Path(output_dir)
    config = create_config_from_file(output_path / CONFIG_FILE)
    jobs = []
    results = ResultsAggregator.list_results(output_dir)
    result_lookup = {x.name: x for x in results}
    for job in config.iter_pydss_simulation_jobs():
        if job.name not in result_lookup:
            logger.info("Skip missing job %s", job.name)
            continue
        if result_lookup[job.name].return_code != 0:
            logger.info("Skip failed job %s", job.name)
            continue
        jobs.append(job)

    feeder_head_table = []
    feeder_losses_table = []
    metadata_table = []
    thermal_metrics_table = []
    voltage_metrics_table = []
    snapshot_time_points_table = []

    # This will create flattened tables for each metric across jobs and PyDSS scenarios
    # within eah job.
    # Every table contains job name, substation, feeder, etc., and scenario name, as
    # well as the metrics.
    with ProcessPoolExecutor() as executor:
        for result in executor.map(parse_job_results, jobs, itertools.repeat(output_path)):
            feeder_head_table += result[0]
            feeder_losses_table += result[1]
            metadata_table += result[2]
            thermal_metrics_table += result[3]
            voltage_metrics_table += result[4]
            snapshot_time_points_table += result[5]

    serialize_table(feeder_head_table, output_path / "feeder_head_table.csv")
    serialize_table(feeder_losses_table, output_path / "feeder_losses_table.csv")
    serialize_table(metadata_table, output_path / "metadata_table.csv")
    serialize_table(thermal_metrics_table, output_path / "thermal_metrics_table.csv")
    serialize_table(voltage_metrics_table, output_path / "voltage_metrics_table.csv")
    if jobs and jobs[0].model.model_type == "SnapshotImpactAnalysisModel":
        serialize_table(snapshot_time_points_table, output_path / "snapshot_time_points_table.csv")


def parse_job_results(job, output_path):
    """Return the tables for a single job."""
    job_path = output_path / JOBS_OUTPUT_DIR / job.name / "pydss_project"
    deployment = job.model.deployment
    if job.model.is_base_case:
        job_info = JobInfo(
            name=job.name,
            substation=deployment.substation,
            feeder=deployment.feeder,
            placement="",
            sample="",
            penetration_level="",
        )
    else:
        job_info = JobInfo(
            name=job.name,
            substation=deployment.substation,
            feeder=deployment.feeder,
            placement=deployment.project_data.get("placement", "NA"),
            sample=deployment.project_data.get("sample", 0.0),
            penetration_level=deployment.project_data.get("penetration_level", 0.0),
        )
    results = PyDssResults(job_path)
    metadata_table = get_metadata_table(results, job_info)
    feeder_head_table = get_feeder_head_info(results, job_info)
    feeder_losses_table = get_feeder_losses(results, job_info)
    thermal_metrics_table = get_thermal_metrics(results, job_info)
    voltage_metrics_table = get_voltage_metrics(results, job_info)
    if job.model.model_type == "SnapshotImpactAnalysisModel":
        snapshot_time_points_table = get_snapshot_time_points_table(results, job_info)
    else:
        snapshot_time_points_table = []

    return (
        feeder_head_table,
        feeder_losses_table,
        metadata_table,
        thermal_metrics_table,
        voltage_metrics_table,
        snapshot_time_points_table,
    )


def add_scenario(row, scenario_name, include_time_point=True):
    """Splits the PyDSS scenario name into name and time point.
    Only applicable to loadshape-based snapshot simulations.

    """
    if SCENARIO_NAME_DELIMITER not in scenario_name:
        row["scenario"] = scenario_name
        return

    name, time_point = scenario_name.split(SCENARIO_NAME_DELIMITER)
    if name not in (CONTROL_MODE_SCENARIO, PF1_SCENARIO):
        raise Exception(f"Unexpected parsing of scenario name: {scenario_name}")
    row["scenario"] = name
    if include_time_point:
        row["time_point"] = time_point


def get_metadata_table(results: PyDssResults, job_info: JobInfo):
    """Return capacity stats for each scenario in the PyDSS project"""
    metadata_table = []
    for scenario in results.scenarios:
        total_pv = compute_total_pv_kw(scenario)
        total_load = compute_total_load_kw(scenario)
        pct_pv_to_load_ratio = 100 * total_pv / max(total_load, 1e-3)
        row = job_info._asdict()
        row.update(
            {
                "pct_pv_to_load_ratio": pct_pv_to_load_ratio,
                "pv_capacity_kw": total_pv,
                "load_capacity_kw": total_load,
            }
        )
        add_scenario(row, scenario.name, include_time_point=False)
        metadata_table.append(row)

    return metadata_table


def _read_file(results, path):
    try:
        return json.loads(results.read_file(path))
    except KeyError:
        return []


def get_feeder_losses(results: PyDssResults, job_info: JobInfo):
    """Return feeder losses for all scenarios."""
    feeder_losses_table = []
    data = _read_file(results, "Reports/feeder_losses.json")
    if not data:
        return feeder_losses_table
    for scenario, values in data["scenarios"].items():
        row = job_info._asdict()
        add_scenario(row, scenario)
        row.update(values)
        feeder_losses_table.append(row)
    return feeder_losses_table


def get_feeder_head_info(results: PyDssResults, job_info: JobInfo):
    """Return feeder head info for the control_mode scenario."""
    feeder_head_table = []
    for scenario in results.scenarios:
        data = json.loads(results.read_file(f"Exports/{scenario.name}/FeederHeadInfo.json"))
        row = job_info._asdict()
        add_scenario(row, scenario.name)
        row.update(data)
        feeder_head_table.append(row)
    return feeder_head_table


def get_thermal_metrics(results: PyDssResults, job_info: JobInfo):
    """Return the thermal metrics for all scenarios."""
    thermal_metrics_table = []
    data = _read_file(results, "Reports/thermal_metrics.json")
    if not data:
        return thermal_metrics_table
    
    for scenario, metrics in create_summary_from_dict(data).items():
        row = job_info._asdict()
        add_scenario(row, scenario)
        row.update(metrics)
        thermal_metrics_table.append(row)

    return thermal_metrics_table


def get_voltage_metrics(results: PyDssResults, job_info: JobInfo):
    """Return the voltage metrics for all scenarios."""
    voltage_metrics_table = []
    data = _read_file(results, "Reports/voltage_metrics.json")
    if not data:
        return voltage_metrics_table
    
    for scenario in data["scenarios"]:
        for node_type in data["scenarios"][scenario]:
            row = job_info._asdict()
            add_scenario(row, scenario)
            row["node_type"] = node_type
            for field in VOLTAGE_METRIC_FIELDS_TO_INCLUDE_AS_PASS_CRITERIA:
                summary = row[field] = data["scenarios"][scenario][node_type]["summary"]
                if summary is not None:
                    row[field] = data["scenarios"][scenario][node_type]["summary"][field]
            voltage_metrics_table.append(row)

    return voltage_metrics_table


def get_snapshot_time_points_table(results: PyDssResults, job_info: JobInfo):
    """Return the snapshot time points determined by each job."""
    try:
        data = json.loads(results.read_file(f"Exports/snapshot_time_points.json"))
    except KeyError:
        # Time points are only available if load shapes are used.
        return []

    row = {"name": job_info.name}
    for time_point in SNAPSHOT_TIME_POINT_MAPPING:
        timestamp = data.get(SNAPSHOT_TIME_POINT_MAPPING[time_point])
        if timestamp is not None:
            timestamp = timestamp["Timepoints"]
        row[time_point] = timestamp
    return [row]


def compute_total_pv_kw(scenario: PyDssScenarioResults):
    """Return the total PV capacity in kw."""
    df = scenario.read_element_info_file(f"Exports/{scenario.name}/PVSystemsInfo.csv")
    if "Name" not in df.columns or df.Name.isnull().all():
        return 0
    return df["Pmpp"].sum()


def compute_total_load_kw(scenario: PyDssScenarioResults):
    """Return the total load capacity in kw."""
    df = scenario.read_element_info_file(f"Exports/{scenario.name}/LoadsInfo.csv")
    return df["kW"].sum()


def serialize_table(table, filename):
    """Serialize a list of dictionaries to a CSV file."""
    with open(filename, "w") as f:
        if not table:
            logger.info("No data to write to %s", filename)
            return
        fields = table[0].keys()
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(table)
        logger.info("Wrote %s", filename)


@click.command()
@click.argument("output_dir")
@click.option(
    "--verbose", is_flag=True, default=False, show_default=True, help="Enable verbose logging"
)
def make_summary_tables(output_dir, verbose):
    """Make hosting capacity summary tables for all jobs in a batch."""
    level = logging.DEBUG if verbose else logging.INFO
    setup_logging(__name__, None, console_level=level, packages=["disco"])
    output_dir = ensure_jade_pipeline_output_dir(output_dir)
    parse_batch_results(output_dir)
