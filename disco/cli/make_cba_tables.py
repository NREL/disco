"""Make cost benefit analysis summary tables for all jobs in a batch."""

import csv
import itertools
import json
import logging
from collections import defaultdict, namedtuple
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import click
import pandas as pd
import toml

from jade.common import CONFIG_FILE, JOBS_OUTPUT_DIR
from jade.jobs.job_configuration_factory import create_config_from_file
from jade.loggers import setup_logging
from jade.jobs.results_aggregator import ResultsAggregator
from jade.utils.subprocess_manager import check_run_command
from jade.utils.utils import load_data

from PyDSS.pydss_results import PyDssResults

from disco.pipelines.utils import ensure_jade_pipeline_output_dir


JobInfo = namedtuple(
    "JobInfo", ["name", "substation", "feeder", "placement", "sample", "penetration_level"]
)
REQUIRED_RESOLUTION = pd.Timedelta(hours=1)

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
    load_sum_group_files = set()
    pv_sum_group_files = set()

    # This will create flattened tables for each metric across jobs and PyDSS scenarios
    # within eah job.
    # Every table contains job name, substation, feeder, etc., and scenario name, as
    # well as the metrics.
    with ProcessPoolExecutor() as executor:
        for result in executor.map(parse_job_results, jobs, itertools.repeat(output_path)):
            powers_tables.append(result[0])
            capacitor_table += result[1]
            reg_control_change_table += result[2]
            load_sum_group_files.update(result[3])
            pv_sum_group_files.update(result[4])

    df = pd.concat(powers_tables)
    powers_file = output_path / "powers_table.csv"
    df.to_csv(powers_file)
    logger.info("Wrote power data to %s", output_path / "powers_table.csv")
    serialize_table(capacitor_table, output_path / "capacitor_table.csv")
    serialize_table(
        reg_control_change_table, output_path / "reg_control_tap_value_change_table.csv"
    )
    loads = make_customer_type_table(load_sum_group_files, "Load")
    serialize_table(loads, output_path / "load_customer_types.csv")
    pvs = make_customer_type_table(pv_sum_group_files, "PVSystem")
    serialize_table(pvs, output_path / "pv_system_customer_types.csv")
    check_run_command(f"disco-internal cba-post-process {powers_file}")


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
            placement=deployment.project_data["placement"],
            sample=deployment.project_data["sample"],
            penetration_level=deployment.project_data["penetration_level"],
        )
    results = PyDssResults(job_path)
    powers_table = get_powers_table(results, job_info)
    capacitor_table = get_capacitor_table(results, job_info)
    reg_control_table = get_reg_control_table(results, job_info)
    load_sum_group_files, pv_sum_group_files = get_sum_group_files(results)

    return (
        powers_table,
        capacitor_table,
        reg_control_table,
        load_sum_group_files,
        pv_sum_group_files,
    )


def get_powers_table(results: PyDssResults, job_info: JobInfo):
    """Return pd.DataFrame containing all power data."""
    dfs = []
    column_order = list(job_info._asdict().keys()) + [
        "scenario",
        "Loads__Powers__commercial (kWh)",
        "Loads__Powers__residential (kWh)",
        "PVSystems__Powers__commercial (kWh)",
        "PVSystems__Powers__residential (kWh)",
        "Circuits__TotalPower (kWh)",
        "Circuits__Losses (kWh)",
    ]
    for scenario in results.scenarios:
        main_df = pd.DataFrame()
        missing = []
        for customer in ("commercial", "residential"):
            for elem_class in ("Loads", "PVSystems"):
                column = f"{elem_class}__Powers__{customer} (kWh)"
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
                    assert len(df.columns) == 1
                    series = df.iloc[:, 0]
                    if elem_class == "Loads":
                        data = series.values
                    else:
                        data = series.apply(get_pv_power_value).values
                    main_df[column] = data
                else:
                    # Not all jobs will have commercial and residential.
                    missing.append(column)
        for column in missing:
            main_df[column] = 0.0

        df = scenario.get_full_dataframe("Circuits", "TotalPower")
        assert len(df.columns) == 1
        main_df["Circuits__TotalPower (kWh)"] = [x.real for x in df[df.columns[0]]]
        # OpenDSS returns this in Watts.
        df = scenario.get_full_dataframe("Circuits", "Losses") / 1000
        assert len(df.columns) == 1
        main_df["Circuits__Losses (kWh)"] = [x.real for x in df[df.columns[0]]]
        if main_df.index[1] - main_df.index[0] == REQUIRED_RESOLUTION:
            df = main_df
        else:
            df = main_df.resample(REQUIRED_RESOLUTION).mean()

        for field, val in job_info._asdict().items():
            df[field] = val
        df["scenario"] = scenario.name
        df = df[column_order]
        dfs.append(df)

    return pd.concat(dfs)


def get_pv_power_value(val):
    if val > 0.0:
        if val < 0.001:  # 1 Watt
            val = 0.0
        else:
            logger.warning("Unexpected PVSystem power value: %s", val)
            val *= -1
    else:
        val *= -1
    return val


def get_capacitor_table(results: PyDssResults, job_info: JobInfo):
    """Return capacitor state changes for all scenarios."""
    capacitor_table = []
    data = json.loads(results.read_file("Reports/capacitor_state_changes.json"))
    for scenario in data["scenarios"]:
        for capacitor in scenario["capacitors"]:
            row = job_info._asdict()
            row["device_name"] = capacitor["name"]
            row["action_count"] = capacitor["change_count"]
            capacitor_table.append(row)
    return capacitor_table


def get_reg_control_table(results: PyDssResults, job_info: JobInfo):
    """Return reg_control state changes for all scenarios."""
    reg_control_table = []
    data = json.loads(results.read_file("Reports/reg_control_tap_value_changes.json"))
    for scenario in data["scenarios"]:
        for reg_control in scenario["reg_controls"]:
            row = job_info._asdict()
            row["device_name"] = reg_control["name"]
            row["action_count"] = reg_control["change_count"]
            reg_control_table.append(row)
    return reg_control_table


def get_sum_group_files(results: PyDssResults):
    """Return a set of filenames defining sum_groups and Load/PV customer types."""
    load_sum_group_files = set()
    pv_sum_group_files = set()
    for scenario in results.scenarios:
        data = toml.loads(
            scenario.read_file(f"Scenarios/{scenario.name}/ExportLists/Exports.toml")
        )
        load_sum_group_files.add(data["Loads"]["Powers"]["sum_groups_file"])
        pv_sum_group_files.add(data["PVSystems"]["Powers"]["sum_groups_file"])
    return load_sum_group_files, pv_sum_group_files


def make_customer_type_table(sum_group_files, element_type):
    """Return a dict of customer type to set of element names."""
    elements = defaultdict(set)
    for filename in sum_group_files:
        data = load_data(filename)
        for group in data["sum_groups"]:
            elements[group["name"]].update(set(group["elements"]))

    table = []
    for group, element_names in elements.items():
        for name in element_names:
            table.append({"customer_type": group, "element_type": element_type, "name": name})
    return table


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
    output_dir = Path(ensure_jade_pipeline_output_dir(output_dir))
    log_file = output_dir / "make_cba_tables.log"
    setup_logging(__name__, log_file, file_level=level, console_level=level, packages=["disco"])
    parse_batch_results(output_dir)
