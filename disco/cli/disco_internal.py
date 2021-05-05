"""Main CLI command for disco."""

import logging

import click

from disco.cli.compute_snapshot_hosting_capacity import compute_snapshot_hosting_capacity
from disco.cli.compute_snapshot_impact_analysis import compute_snapshot_impact_analysis
from disco.cli.compute_time_series_hosting_capacity import compute_time_series_hosting_capacity
from disco.cli.compute_time_series_impact_analysis import compute_time_series_impact_analysis
from disco.cli.make_hosting_capacity_summary_tables import make_summary_tables


logger = logging.getLogger(__name__)


@click.group()
def cli():
    """DISCO internal commands"""


cli.add_command(compute_snapshot_hosting_capacity)
cli.add_command(compute_snapshot_impact_analysis)
cli.add_command(compute_time_series_hosting_capacity)
cli.add_command(compute_time_series_impact_analysis)
cli.add_command(make_summary_tables)
