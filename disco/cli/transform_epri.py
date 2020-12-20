import json
import logging
import os

import click

from jade.exceptions import InvalidParameter
from jade.loggers import setup_logging
from jade.utils.utils import load_data, get_cli_string
from disco.enums import SimulationType
from disco.models.snapshot_impact_analysis_model import SnapshotImpactAnalysisModel
from disco.models.time_series_impact_analysis_model import TimeSeriesImpactAnalysisModel
from disco.sources.epri import EpriOpenDssModel


logger = logging.getLogger(__name__)


def _get_simulation_type(ctx, params, value):
    return SimulationType(value)


@click.group()
@click.argument("input_path")
@click.option(
    "-f", "--feeders",
    default=["all"],
    multiple=True,
    show_default=True,
    help="feeders to add; use 'all' to auto-detect and add all feeders",
)
def epri(input_path, feeders):
    level = logging.INFO
    setup_logging(__name__, "transform_epri.log", console_level=level, file_level=level)
    logger.info(get_cli_string())

@click.command()
@click.option(
    "-o", "--output",
    default="epri-snapshot-impact-analysis-models",
    show_default=True,
    help="output directory",
)
@click.option(
    "-s", "--start",
    default="2020-06-17T15:00:00.000",
    show_default=True,
    help="simulation start time",
)
@click.pass_context
def snapshot_impact_analysis(ctx, output, start):
    """Transform input data for a snapshot simulation"""
    simulation_params = {
        "start_time": start,
        "end_time": start,
        "step_resolution": 900,
        "simulation_type": SimulationType.SNAPSHOT,
    }

    EpriOpenDssModel.transform(
        input_path=ctx.parent.params["input_path"],
        output_path=output,
        simulation_params=simulation_params,
        simulation_model=SnapshotImpactAnalysisModel,
        feeders=ctx.parent.params["feeders"],
    )


@click.command()
@click.option(
    "-s", "--start",
    default="2020-06-17T15:00:00.000",
    show_default=True,
    help="simulation start time",
)
@click.option(
    "-e", "--end",
    default="2020-06-24T15:00:00.000",
    show_default=True,
    help="simulation end time",
)
@click.option(
    "-o", "--output",
    default="epri-time-series-impact-analysis-models",
    show_default=True,
    help="output directory",
)
@click.option(
    "-p", "--pv-profile",
    type=str,
    help="load shape profile name to apply to all PVSystems",
)
@click.option(
    "-r", "--resolution",
    default=900,
    type=int,
    show_default=True,
    help="simulation step resolution in seconds",
)
@click.pass_context
def time_series_impact_analysis(ctx, start, end, output, pv_profile, resolution):
    """Transform input data for a time series simulation"""
    simulation_params = {
        "start_time": start,
        "end_time": end,
        "step_resolution": resolution,
        "simulation_type": SimulationType.QSTS,
    }
    EpriOpenDssModel.transform(
        input_path=ctx.parent.params["input_path"],
        output_path=output,
        simulation_params=simulation_params,
        simulation_model=TimeSeriesImpactAnalysisModel,
        feeders=ctx.parent.params["feeders"],
        pv_profile=pv_profile,
    )


epri.add_command(snapshot_impact_analysis)
epri.add_command(time_series_impact_analysis)
