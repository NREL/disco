"""Computes hosting capacity"""

import csv
import itertools
import logging
import os
from concurrent.futures import ProcessPoolExecutor

import click
import pandas as pd

from jade.common import CONFIG_FILE, JOBS_OUTPUT_DIR
from jade.jobs.results_aggregator import ResultsAggregator
from jade.loggers import setup_logging
from jade.utils.utils import get_cli_string, load_data

from disco.extensions.pydss_simulation.pydss_configuration import PyDssConfiguration


@click.command()
@click.option(
    "-o", "--jade-runtime-output",
    required=True,
    help="jade runtime output directory",
)
@click.option(
    "--verbose",
    is_flag=True,
    default=False,
    help="Enable debug logging",
)
def compute_snapshot_hosting_capacity(jade_runtime_output, verbose=False):
    """Merge the pydss simulation results into one CSV file."""
    level = logging.DEBUG if verbose else logging.INFO
    logger = setup_logging(__name__, None, console_level=level)
    logger.info("Run compute_snapshot_hosting_capacity")
    print(get_cli_string())

    output_config_path = os.path.join(jade_runtime_output, CONFIG_FILE)
    config = PyDssConfiguration.deserialize(output_config_path)
    power_flow_job_names = set([
        x.name for x in config.iter_jobs() if x.extension == "pydss_simulation"
    ])
    job_pp_path = os.path.join(jade_runtime_output, JOBS_OUTPUT_DIR)
    all_pp_results = {}

    # build list of only successful results
    job_names = [
        x.name for x in ResultsAggregator.list_results(jade_runtime_output)
        if x.return_code == 0 and x.name in power_flow_job_names
    ]

    # create list of single job path to pass to executor
    job_paths = itertools.repeat(job_pp_path, len(job_names))
    jobs_post_process_results = {}

    with ProcessPoolExecutor() as executor:
        jobs_post_process_results = executor.map(_get_job_post_process_results,
                                                 job_paths, job_names)

    for job in jobs_post_process_results:
        job_config = config.get_job(job.get("name"))
        if job_config.feeder not in all_pp_results:
            all_pp_results.update({job_config.feeder: list()})

        all_pp_results[job_config.feeder].append(job)

    for feeder in all_pp_results:
        # output to csv
        result_df = pd.DataFrame(all_pp_results[feeder],
                                 columns=all_pp_results[feeder][0].keys())

        out_file = f"{feeder}-snapshot-impact-analysis-batch-post-process.csv"
        filename = os.path.join(jade_runtime_output, JOBS_OUTPUT_DIR, out_file)

        result_df.sort_values("penetration", inplace=True)
        result_df.to_csv(filename, index=False)
        logger.info("Dumped aggregated results to %s", out_file)

    # TODO: hosting capacity...


def _get_job_post_process_results(job_output_dir, job_name):
    """Get job post-process-results data

    Parameters
    ----------
    job_output_dir : str
    job_name : str

    Returns
    -------
    dict
        Dictionary of job name and all data from the job post-process results
    """
    results_file = os.path.join(
        job_output_dir,
        job_name,
        "snapshot-impact-analysis-job-post-process.csv",
    )

    with open(results_file) as f_in:
        results = []
        reader = csv.DictReader(f_in)
        results = list(reader)
        assert len(results) == 1, str(results)
        result = results[0]

    # add job name to results
    result["name"] = job_name
    return result
