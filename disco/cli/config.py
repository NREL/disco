
import click

from disco.cli.config_snapshot import snapshot
from disco.cli.config_time_series import time_series
from disco.cli.config_upgrade_cost_analysis import upgrade_cost_analysis


@click.group()
def config():
    """Create JADE configurations for DISCO analysis types"""


config.add_command(snapshot)
config.add_command(time_series)
config.add_command(upgrade_cost_analysis)
