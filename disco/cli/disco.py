"""Main CLI command for disco."""

import logging

import click

from disco.cli.config import config
#from disco.cli.configure_analysis import generate_analysis
from disco.cli.simulation_models import simulation_models
from disco.cli.download_source import download_source
from disco.cli.transform_model import transform_model
from disco.cli.prescreen_pv_penetration_levels import prescreen_pv_penetration_levels
from disco.cli.pv_deployments import pv_deployments
from disco.cli.create_pipeline import create_pipeline
from disco.cli.ingest_tables import ingest_tables
from disco.cli.upgrade_cost_analysis import upgrade_cost_analysis


logger = logging.getLogger(__name__)


@click.group()
def cli():
    """Entry point"""


#cli.add_command(generate_analysis)
cli.add_command(config)
cli.add_command(simulation_models)
cli.add_command(download_source)
cli.add_command(transform_model)
cli.add_command(pv_deployments)
cli.add_command(prescreen_pv_penetration_levels)
cli.add_command(create_pipeline)
cli.add_command(ingest_tables)
cli.add_command(upgrade_cost_analysis)
