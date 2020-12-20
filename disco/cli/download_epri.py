"""Command to download input data."""

import click

from disco.sources.epri import download_epri_feeder_opendss_data


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
