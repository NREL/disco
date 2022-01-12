
import click

from disco.cli.config_snapshot import snapshot
from disco.cli.config_time_series import time_series


@click.group()
def config():
    """Create JADE configurations for DISCO analysis types"""


config.add_command(snapshot)
config.add_command(time_series)
