"""Command to download input data."""

import click

from disco.cli.download_epri import epri


@click.group()
def download_source():
    """Commands to download raw OpenDSS models from the source."""


download_source.add_command(epri)
