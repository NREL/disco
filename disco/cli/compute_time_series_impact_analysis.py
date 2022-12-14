
import logging
import os

import click

from jade.loggers import setup_logging
from jade.utils.utils import get_cli_string
from disco.analysis.postprocess_time_series import aggregate_deployments, compute_hosting_capacity


@click.command()
@click.argument("feeder")
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
def compute_time_series_impact_analysis(feeder, jade_runtime_output, verbose=False):
    """Run post-process computations for time series impact analysis."""
    level = logging.DEBUG if verbose else logging.INFO
    filename = os.path.join(jade_runtime_output, f"compute_time_series_impact_analysis_{feeder}.log")
    logger = setup_logging("disco", filename, console_level=level, file_level=level, packages=["disco"])
    logger.info("Run compute_time_series_impact_analysis for feeder %s", feeder)
    logger.info(get_cli_string())

    job_outputs = os.path.join(jade_runtime_output, "job-outputs")
    dfs = aggregate_deployments(job_outputs)
