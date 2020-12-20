"""Main CLI command for disco."""

import logging

import click

from disco.cli.config import config
from disco.cli.configure_analysis import generate_analysis
from disco.cli.simulation_models import simulation_models
from disco.cli.download_source import download_source
from disco.cli.transform_model import generate_transform_model_config
from disco.cli.transform_model import transform_model


logger = logging.getLogger(__name__)


@click.group()
def cli():
    """Entry point"""


cli.add_command(generate_analysis)
cli.add_command(config)
cli.add_command(simulation_models)
cli.add_command(download_source)
cli.add_command(generate_transform_model_config)
cli.add_command(transform_model)
