import logging

import click

from jade.loggers import setup_logging
from disco.pipelines.utils import ensure_jade_pipeline_output_dir
from disco.postprocess.plots import plot_voltage, plot_hc

logger = logging.getLogger(__name__)


@click.command()
@click.argument("output_dir")
@click.option(
    "--scenario",
    type=click.STRING,
    default="scenario",
    show_default=True,
    help="Input the PyDSS scenario"
)
@click.option(
    "--verbose", is_flag=True, default=False, show_default=True, help="Enable verbose logging"
)
def plot(output_dir, scenario, verbose):
    """Plot voltage and hosting capacity charts"""
    level = logging.DEBUG if verbose else logging.INFO
    setup_logging(__name__, None, console_level=level, packages=["disco"])
    output_dir = ensure_jade_pipeline_output_dir(output_dir)
    plot_voltage(output_dir, scenario)
    plot_hc(output_dir, scenario)
