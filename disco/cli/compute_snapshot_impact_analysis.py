
import logging
import os

import click

from jade.common import CONFIG_FILE
from jade.loggers import setup_logging
from jade.utils.utils import get_cli_string, load_data

from disco.analysis.snapshot_impact_analysis import SnapshotImpactAnalysis
from disco.extensions.pydss_simulation.pydss_configuration import PyDssConfiguration


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
def compute_snapshot_impact_analysis(feeder, jade_runtime_output, verbose=False):
    """Run post-process computations for time series impact analysis."""
    level = logging.DEBUG if verbose else logging.INFO
    filename = os.path.join(jade_runtime_output, f"compute_snapshot_impact_analysis_{feeder}.log")
    logger = setup_logging("disco", filename, console_level=level, file_level=level, packages=["disco"])
    logger.info("Run compute_snapshot_impact_analysis for feeder %s", feeder)
    logger.info(get_cli_string())

    config_file = os.path.join(jade_runtime_output, CONFIG_FILE)
    config = PyDssConfiguration.deserialize(config_file)
    inputs = config.get_user_data("impact_analysis_inputs")
    analysis = SnapshotImpactAnalysis(feeder, overrides=inputs["thresholds"])
    analysis.run(jade_runtime_output)
