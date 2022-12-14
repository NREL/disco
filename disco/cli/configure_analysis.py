"""CLI to automatically create an anlysis configuration."""

import logging
import sys

import click

from jade.jobs.job_post_process import JobPostProcess
from jade.loggers import setup_logging
from jade.utils.custom_click_options import CustomOptions
from jade.utils.utils import load_data
from disco.enums import ANALYSIS_MODEL_TYPES
from disco.analysis import load_custom_overrides
from disco.analysis.configure import create_analysis_config


@click.option(
    "-t", "--analysis-type",
    cls=CustomOptions,
    required=True,
    allowed_values=ANALYSIS_MODEL_TYPES,
    not_required_if='config_file',
    help="Analysis type"
)
@click.option(
    "-f", "--config-file",
    is_eager=True,
    type=click.Path(exists=True),
    help="config file containing overrides specific to analysis type"
)
@click.option(
    "-o", "--overrides",
    is_eager=True,
    callback=load_custom_overrides,
    multiple=True,
    default=[],
    help="Set individual overrides for each analysis input."
)
@click.option(
    "-l", "--list-defaults",
    is_flag=True,
    default=False,
    help="Show default options for analysis type"
)
@click.option(
    "--output-file",
    default="analysis-post-process-config.toml",
    help="Analysis output file name"
)
@click.option(
    "-v", "--verbose",
    is_flag=True,
    default=False,
    help="Enable verbose log output."
)
@click.command()
def generate_analysis(analysis_type, config_file, list_defaults,
                      overrides, output_file, verbose):
    """Generate Analysis configuration for job post-processing."""
    level = logging.DEBUG if verbose else logging.INFO
    setup_logging("generate_analysis", None, console_level=level, packages=["disco"])

    if config_file is None:
        config = {}
    else:
        config = load_data(config)

    # config file overrides
    config_overrides = {}
    if 'overrides' in config:
        for override in config['overrides']:
            config_overrides[override] = config['overrides'][override]

    # explicit user overrides
    if overrides:
        config_overrides.update(overrides)

    analysis_config = create_analysis_config(analysis_type, config_overrides)

    if list_defaults:
        analysis_config.print_inputs()
        sys.exit()

    post_process = JobPostProcess("disco.analysis", analysis_type, data=config_overrides)
    post_process.dump_config(output_file)
