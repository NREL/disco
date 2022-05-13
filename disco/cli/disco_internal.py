"""Main CLI command for disco."""

import logging

import click

from disco.cli.compute_snapshot_hosting_capacity import compute_snapshot_hosting_capacity
from disco.cli.compute_snapshot_impact_analysis import compute_snapshot_impact_analysis
from disco.cli.compute_time_series_hosting_capacity import compute_time_series_hosting_capacity
from disco.cli.compute_time_series_impact_analysis import compute_time_series_impact_analysis
from disco.cli.make_cba_tables import make_cba_tables
from disco.cli.make_upgrade_tables import make_upgrade_tables
from disco.cli.compute_hosting_capacity import compute_hosting_capacity
from disco.cli.cba_post_process import cba_post_process
from disco.cli.compute_cba import compute_cba
from disco.cli.plots import plot


logger = logging.getLogger(__name__)


@click.group()
def cli():
    """DISCO internal commands"""


cli.add_command(compute_snapshot_hosting_capacity)
cli.add_command(compute_snapshot_impact_analysis)
cli.add_command(compute_time_series_hosting_capacity)
cli.add_command(compute_time_series_impact_analysis)
cli.add_command(make_cba_tables)
cli.add_command(make_upgrade_tables)
cli.add_command(compute_hosting_capacity)
cli.add_command(cba_post_process)
cli.add_command(compute_cba)
cli.add_command(plot)
