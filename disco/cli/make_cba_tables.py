"""Make cost benefit analysis summary tables for all jobs in a batch."""

import csv
import itertools
import json
import logging
from collections import namedtuple
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import click
import numpy as np
import pandas as pd

from jade.common import CONFIG_FILE, JOBS_OUTPUT_DIR
from jade.jobs.job_configuration_factory import create_config_from_file
from jade.loggers import setup_logging
from jade.jobs.results_aggregator import ResultsAggregator

from PyDSS.exceptions import InvalidParameter
from PyDSS.pydss_results import PyDssResults
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

    powers_tables = []
    capacitor_table = []
    reg_control_change_table = []
    element_infos = []

    # This will create flattened tables for each metric across jobs and PyDSS scenarios
    # within eah job.
    # Every table contains job name, substation, feeder, etc., and scenario name, as
    # well as the metrics.
    with ProcessPoolExecutor() as executor:
        for result in executor.map(parse_job_results, jobs, itertools.repeat(output_path)):
            result = parse_job_results(job, output_path)
            powers_tables.append(result[0])
            capacitor_table += result[1]
            reg_control_change_table += result[2]
            element_infos += result[3]

    df = pd.concat(powers_tables)
    df.to_csv(output_path / "powers_table.csv")
    logger.info("Wrote power data to %s", output_path / "powers_table.csv")
    serialize_table(capacitor_table, output_path / "capacitor_table.csv")
    serialize_table(
        reg_control_change_table, output_path / "reg_control_tap_value_change_table.csv"
    )
    # TODO: element_infos


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
    powers_table = get_powers_table(results, job_info)
    capacitor_table = get_capacitor_table(results, job_info)
    reg_control_table = get_reg_control_table(results, job_info)
    element_infos = {}  # get_element_info(results, job_info)

    return (
        powers_table,
        capacitor_table,
        reg_control_table,
        element_infos,
    )


# TODO: We're not sure exactly how this information will be used yet.
def get_element_info(results: PyDssResults, job_info: JobInfo):
    """Return a dict of pd.DataFrames for static information about each circuit element."""
    # All scenarios have the same information.
    scenario = results.scenarios[0]
    dfs = {}
    for filename in scenario.list_element_info_files():
        # Format follows this example: "Exports/pf1/LoadsInfo.csv"
        name = filename.split("/")[2].split("Info")[0]
        dfs[name] = scenario.read_element_info_file(filename)
        for field, val in job_info._asdict().items():
            dfs[name][field] = val
        dfs[name]["scenario"] = np.NaN

    return dfs


def get_powers_table(results: PyDssResults, job_info: JobInfo):
    """Return pd.DataFrame containing all power data."""
    dfs = []
    column_order = list(job_info._asdict().keys()) + [
        "scenario",
        "Loads__Powers__commercial (kW)",
        "Loads__Powers__residential (kW)",
        "PVSystems__Powers__commercial (kW)",
        "PVSystems__Powers__residential (kW)",
        "Circuits__TotalPower (kW)",
        "Circuits__Losses (kW)",
    ]
    for scenario in results.scenarios:
        main_df = pd.DataFrame()
        missing = []
        for customer in ("commercial", "residential"):
            for elem_class in ("Loads", "PVSystems"):
                column = f"{elem_class}__Powers__{customer} (kW)"
                if elem_class not in scenario.list_element_classes():
                    # Base case doesn't have PVSystems.
                    missing.append(column)
                    continue
                prop = f"Powers__{customer}"
                if prop in scenario.list_summed_element_time_series_properties(elem_class):
                    df = scenario.get_summed_element_dataframe(elem_class, prop)
                    if len(main_df) == 0:
                        main_df.index = df.index
                    # Exclude neutral phase.
                    cols = [col for col in df.columns if "__N" not in col]
                    main_df[column] = [x.real for x in df[cols].sum(axis=1)]
                else:
                    # Not all jobs will have commercial and residential.
                    missing.append(column)
        for column in missing:
            main_df[column] = np.NaN

        df = scenario.get_full_dataframe("Circuits", "TotalPower")
        assert len(df.columns) == 1
        main_df["Circuits__TotalPower (kW)"] = [x.real for x in df[df.columns[0]]]
        # OpenDSS returns this in Watts.
        df = scenario.get_full_dataframe("Circuits", "Losses") / 1000
        assert len(df.columns) == 1
        main_df["Circuits__Losses (kW)"] = [x.real for x in df[df.columns[0]]]

        for field, val in job_info._asdict().items():
            main_df[field] = val
        main_df["scenario"] = scenario.name
        main_df = main_df[column_order]
        dfs.append(main_df)

    return pd.concat(dfs)


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
            f.write('""\n')
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
