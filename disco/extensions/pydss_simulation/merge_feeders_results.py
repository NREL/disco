"""This is a batch post-process script.

Merge the pydss simulation results into one CSV file.
"""
import logging
import os
from concurrent.futures import ProcessPoolExecutor
import itertools

import click
import pandas as pd

from jade.common import JOBS_OUTPUT_DIR
from jade.result import ResultsSummary
from jade.utils.utils import load_data

from disco.extensions.pydss_simulation.pydss_configuration import PyDssConfiguration

logger = logging.getLogger(__name__)


@click.group()
def cli():
    pass


@cli.command()
@click.argument('previous_stage_output')
@click.argument('current_stage_output')
def run(previous_stage_output, current_stage_output):
    """Merge the pydss simulation results into one CSV file."""
    logger.info("Start batch post-processing...")

    output_config_path = os.path.join(previous_stage_output, 'config.json')
    config = PyDssConfiguration.deserialize(output_config_path)
    job_pp_path = os.path.join(previous_stage_output, JOBS_OUTPUT_DIR)
    all_pp_results = {}

    # build list of only successful results
    stage1_results = ResultsSummary(previous_stage_output)
    job_names = list()
    for job in stage1_results.get_successful_results():
        job_names.append(job.name)

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

        output_csv = f"{feeder}-snapshot-impact-analysis-batch-post-process.csv"
        filename = os.path.join(current_stage_output, JOBS_OUTPUT_DIR, output_csv)

        result_df.sort_values("penetration", inplace=True)
        result_df.to_csv(filename, index=False)
        logger.info("Dumped aggregated results to %s", output_csv)

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
        "post-process-results.json"
    )

    job_post_process_data = load_data(results_file)
    results = job_post_process_data["results"]["outputs"][0]["data"]

    # add job name to results
    results["name"] = job_name

    return results


if __name__ == "__main__":
    cli()
