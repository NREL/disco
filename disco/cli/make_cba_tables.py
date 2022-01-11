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


JobInfo = namedtuple(
    "JobInfo", ["name", "substation", "feeder", "placement", "sample", "penetration_level"]
)

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

    capacitor_table = []
    reg_control_change_table = []

    # This will create flattened tables for each metric across jobs and PyDSS scenarios
    # within eah job.
    # Every table contains job name, substation, feeder, etc., and scenario name, as
    # well as the metrics.
    with ProcessPoolExecutor() as executor:
        for result in executor.map(parse_job_results, jobs, itertools.repeat(output_path)):
            capacitor_table += result[0]
            reg_control_change_table += result[1]

    serialize_table(capacitor_table, output_path / "capacitor_table.csv")
    serialize_table(reg_control_change_table, output_path / "reg_control_tap_value_change_table.csv")


def parse_job_results(job, output_path):
    """Return the tables for a single job."""
    job_path = output_path / JOBS_OUTPUT_DIR / job.name / "pydss_project"
    deployment = job.model.deployment
    if job.model.is_base_case:
        job_info = JobInfo(
            name=job.name,
            substation=deployment.substation,
            feeder=deployment.feeder,
            placement="None",
            sample="None",
            penetration_level="None",
        )
    else:
        job_info = JobInfo(
            name=job.name,
            substation=deployment.substation,
            feeder=deployment.feeder,
            placement=deployment.project_data["placement"],
            sample=deployment.project_data["sample"],
            penetration_level=deployment.project_data["penetration_level"],
        )
    results = PyDssResults(job_path)
    capacitor_table = get_capacitor_table(results, job_info)
    reg_control_table = get_reg_control_table(results, job_info)

    return (
        capacitor_table,
        reg_control_table,
    )


def get_capacitor_table(results: PyDssResults, job_info: JobInfo):
    """Return capacitor state changes for all scenarios."""
    capacitor_table = []
    data = json.loads(results.read_file("Reports/capacitor_state_changes.json"))
    for scenario in data["scenarios"]:
        for capacitor in scenario["capacitors"]:
            row = job_info._asdict()
            row["capacitor_name"] = capacitor["name"]
            row["change_count"] = capacitor["change_count"]
            capacitor_table.append(row)
    return capacitor_table


def get_reg_control_table(results: PyDssResults, job_info: JobInfo):
    """Return reg_control state changes for all scenarios."""
    reg_control_table = []
    data = json.loads(results.read_file("Reports/reg_control_tap_value_changes.json"))
    for scenario in data["scenarios"]:
        for reg_control in scenario["reg_controls"]:
            row = job_info._asdict()
            row["reg_control_name"] = reg_control["name"]
            row["change_count"] = reg_control["change_count"]
            reg_control_table.append(row)
    return reg_control_table


def serialize_table(table, filename):
    """Serialize a list of dictionaries to a CSV file."""
    with open(filename, "w") as f:
        if table:
            fields = table[0].keys()
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            writer.writerows(table)
        else:
            f.write("\"\"\n")
        logger.info("Wrote %s", filename)


@click.command()
@click.argument("output_dir")
@click.option(
    "--verbose", is_flag=True, default=False, show_default=True, help="Enable verbose logging"
)
def make_cba_tables(output_dir, verbose):
    """Make cost benefit analysis summary tables for all jobs in a batch."""
    level = logging.DEBUG if verbose else logging.INFO
    setup_logging(__name__, None, console_level=level)
    output_dir = ensure_jade_pipeline_output_dir(output_dir)
    parse_batch_results(output_dir)
