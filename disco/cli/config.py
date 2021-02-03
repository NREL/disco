
import click

from disco.cli.config_snapshot import snapshot
from disco.cli.config_time_series import time_series
from disco.cli.config_upgrade import upgrade


@click.group()
def config():
    """Create JADE configurations for DISCO analysis types"""


config.add_command(snapshot)
config.add_command(time_series)
config.add_command(upgrade)
