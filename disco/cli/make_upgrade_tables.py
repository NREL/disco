"""Make new upgrade cost analysis tables for all jobs in a batch."""

import csv
import json
import itertools
import logging
from collections import namedtuple
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import click
import pandas as pd

from jade.common import CONFIG_FILE, JOBS_OUTPUT_DIR
from jade.loggers import setup_logging
from jade.jobs.job_configuration_factory import create_config_from_file
from jade.jobs.results_aggregator import ResultsAggregator

from disco.pipelines.utils import ensure_jade_pipeline_output_dir

logger = logging.getLogger(__name__)

JobInfo = namedtuple(
    "JobInfo", ["name", "substation", "feeder", "placement", "sample", "penetration_level"]
)


def parse_batch_results(output_dir):
    """Parse the results from all jobs in a JADE output directory."""
    output_path = Path(output_dir)
    config = create_config_from_file(output_path / CONFIG_FILE)
    jobs = []
    results = ResultsAggregator.list_results(output_dir)
    result_lookup = {x.name: x for x in results}
    for job in config.iter_jobs():
        if job.name not in result_lookup:
            logger.info("Skip missing job %s", job.name)
            continue
        if result_lookup[job.name].return_code != 0:
            logger.info("Skip failed job %s", job.name)
            continue
        jobs.append(job)

    upgrade_summary_table = []
    total_upgrade_costs_table = []

    with ProcessPoolExecutor() as executor:
        for result in executor.map(parse_job_results, jobs, itertools.repeat(output_path)):
            upgrade_summary_table += result[0]
            total_upgrade_costs_table += result[1]

    serialize_table(upgrade_summary_table, output_path / "upgrade_summary.csv")
    serialize_table(total_upgrade_costs_table, output_path / "total_upgrade_costs.csv")


def parse_job_results(job, output_path):
    job_path = output_path / JOBS_OUTPUT_DIR / job.name
    deployment = job.model.deployment
    job_info = JobInfo(
        name=job.name,
        substation=deployment.substation,
        feeder=deployment.feeder,
        placement=deployment.project_data["placement"],
        sample=deployment.project_data["sample"],
        penetration_level=deployment.project_data["penetration_level"],
    )
    upgrade_summary_table = get_upgrade_summary_table(job_path, job_info)
    total_upgrade_costs_table = get_total_upgrade_costs_table(job_path, job_info)
    
    return (
        upgrade_summary_table,
        total_upgrade_costs_table
    )


def get_upgrade_summary_table(job_path, job_info):

    def _get_upgrade_summary(upgrade_type, upgrade_summary_file):
        if not upgrade_summary_file.exists():
            return []
        
        try:
            with open(upgrade_summary_file) as json_file:
                data = json.load(json_file)
            df = pd.DataFrame(data)
        except pd.errors.EmptyDataError:
            logger.exception("Failed to parse upgrade summary file - '%s'", upgrade_summary_file)
            return []
        
        summary_result = []
        records = df.to_dict("records")
        for record in records:
            data = job_info._asdict()
            data.update({"upgrade_type": upgrade_type})
            data.update(record)
            summary_result.append(data)
        return summary_result

    upgrade_summary = []

    thermal_upgrade_summary_file = job_path / "ThermalUpgrades" / "thermal_summary.json"
    upgrade_summary.extend(_get_upgrade_summary("thermal", thermal_upgrade_summary_file))

    voltage_upgrade_summary_file = job_path / "VoltageUpgrades" / "voltage_summary.json"
    upgrade_summary.extend(_get_upgrade_summary("voltage", voltage_upgrade_summary_file))

    return upgrade_summary


def get_total_upgrade_costs_table(job_path, job_info):
    total_upgrade_costs_file = job_path / "UpgradeCosts" / "total_upgrade_costs.json"
    if not total_upgrade_costs_file.exists():
        return []
    
    try:
        with open(total_upgrade_costs_file) as json_file:
            data = json.load(json_file)
        df = pd.DataFrame(data)
    except pd.errors.EmptyDataError:
        logger.exception("Failed to parse total upgrade costs file - '%s'", total_upgrade_costs_file)
        return []
    
    total_upgrade_costs = []
    data = df.to_dict("records")
    for item in data:
        record = job_info._asdict()
        record.update(item)
        total_upgrade_costs.append(record)
    return total_upgrade_costs


def serialize_table(table, filename):
    """Serialize a list of dictionaries to a CSV file."""
    with open(filename, "w") as f:
        assert table, filename
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
def make_upgrade_tables(output_dir, verbose):
    """Make upgrade cost tables for all jobs in a batch."""
    level = logging.DEBUG if verbose else logging.INFO
    setup_logging(__name__, None, console_level=level, packages=["disco"])
    output_dir = ensure_jade_pipeline_output_dir(output_dir)
    parse_batch_results(output_dir)
