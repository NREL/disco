
import logging

import click

from jade.loggers import setup_logging
from jade.utils.utils import get_cli_string


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
    """Run post-process computations for snapshot impact analysis."""
    level = logging.DEBUG if verbose else logging.INFO
    logger = setup_logging(__name__, None, console_level=level)
    print(get_cli_string())
