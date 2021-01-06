"""Command to download input data."""

import click

from disco.sources.epri import (
    download_epri_feeder_opendss_data,
    define_epri_source_format
)


@click.group()
def download_source():
    """Commands to download raw OpenDSS models from the source."""


@click.command()
@click.argument("feeders", nargs=-1)
@click.option(
    "-d", "--directory",
    default=".",
    show_default=True,
    help="local download directory",
)
def epri(feeders, directory):
    """Download EPRI feeder models - J1, K1, and/or M1"""
    for feeder in feeders:
        location = download_epri_feeder_opendss_data(feeder, output_directory=directory)
        print(f"Downloaded EPRI {feeder} to {location}")
    
    define_epri_source_format(output_directory=directory)


download_source.add_command(epri)
