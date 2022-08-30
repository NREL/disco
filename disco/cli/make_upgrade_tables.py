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
from jade.utils.utils import load_data, dump_data

from disco.models.upgrade_cost_analysis_generic_output_model import (
    UpgradeViolationResultModel,
    TotalUpgradeCostsResultModel,
)
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

    output_json = {
        "results": [],
        "costs_per_equipment": [],
        "violation_summary": [],
        "equipment": [],
    }

    with ProcessPoolExecutor() as executor:
        for tables in executor.map(parse_job_results, jobs, itertools.repeat(output_path)):
            output_json = combine_job_outputs(output_json, tables)

    for key in output_json: 
        if not output_json[key]:
            logger.warning("There were no %s results.", key)
    
    filename = output_path / "upgrade_summary.json"
    dump_data(output_json, filename, indent=2)
    logger.info("Output summary data to %s", filename)
    # serialize_table(upgrade_summary_table, output_path / "upgrade_summary.csv")
    # serialize_table(total_upgrade_costs_table, output_path / "total_upgrade_costs.csv")


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
    overall_output_summary_file = job_path / "output.json"
    data = load_data(overall_output_summary_file)
    tables = get_upgrade_tables(data)
    return tables


def get_upgrade_tables(data):
    tables = {}
    # the key "results" is a dict, but all others are lists of dict
    # so convert "results" dict to list
    for key, value in data.items():
        if key == "results":
            tables[key] = [value]
        else:
            tables[key] = value
    return tables


def combine_job_outputs(output_json, tables):    
    # It might seem odd to go from dict to model back to dict, but this validates
    # fields and types.
    for record in tables["violation_summary"]:
        output_json["violation_summary"].append(UpgradeViolationResultModel(**record).dict())
    for record in tables["costs_per_equipment"]:
        output_json["costs_per_equipment"].append(TotalUpgradeCostsResultModel(**record).dict())
    output_json["equipment"] += tables["equipment"]
    output_json["results"] += tables["results"]
    return output_json


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
