import logging

import click

from jade.loggers import setup_logging
from jade.utils.utils import get_cli_string
#from disco.enums import SimulationType
from disco.models.snapshot_impact_analysis_model import SnapshotImpactAnalysisModel
# from disco.models.time_series_impact_analysis_model import TimeSeriesImpactAnalysisModel
from disco.models.upgrade_cost_analysis_model import UpgradeCostAnalysisModel
from disco.sources.gem import GemOpenDssModel


logger = logging.getLogger(__name__)


@click.group()
@click.argument("gem_file")
def gem(gem_file):
    level = logging.INFO
    setup_logging(__name__, "transform_gem.log", console_level=level, file_level=level)
    logger.info(get_cli_string())


@click.command()
@click.option(
    "-o", "--output",
    default="gem-snapshot-impact-analysis-models",
    show_default=True,
    help="output directory",
)
@click.pass_context
def snapshot_impact_analysis(ctx, output):
    """Transform input data for a snapshot impact analysis simulation"""
    GemOpenDssModel.transform(
        input_file=ctx.parent.params["gem_file"],
        output_path=output,
        simulation_model=SnapshotImpactAnalysisModel,
    )


# As of now there are no time series simulations planned with GEM data.
# That could be extended here.

#@click.command()
#@click.option(
#    "-s", "--start",
#    default="2020-06-17T15:00:00.000",
#    show_default=True,
#    help="simulation start time",
#)
#@click.option(
#    "-e", "--end",
#    default="2020-06-24T15:00:00.000",
#    show_default=True,
#    help="simulation end time",
#)
#@click.option(
#    "-o", "--output",
#    default="gem-time-series-impact-analysis-models",
#    show_default=True,
#    help="output directory",
#)
#@click.option(
#    "-p", "--pv-profile",
#    type=str,
#    help="load shape profile name to apply to all PVSystems",
#)
#@click.option(
#    "-r", "--resolution",
#    default=900,
#    type=int,
#    show_default=True,
#    help="simulation step resolution in seconds",
#)
#@click.pass_context
#def time_series_impact_analysis(ctx, start, end, output, pv_profile, resolution):
#    """Transform input data for a time series simulation"""
#    simulation_params = {
#        "start_time": start,
#        "end_time": end,
#        "step_resolution": resolution,
#        "simulation_type": SimulationType.QSTS,
#    }
#    GemOpenDssModel.transform(
#        input_path=ctx.parent.params["input_path"],
#        output_path=output,
#        simulation_params=simulation_params,
#        simulation_model=TimeSeriesImpactAnalysisModel,
#        feeders=ctx.parent.params["feeders"],
#        pv_profile=pv_profile,
#    )


@click.command()
@click.option(
    "-o", "--output",
    default="gem-upgrade-cost-analysis-models",
    show_default=True,
    help="output directory."
)
@click.pass_context
def upgrade_cost_analysis(ctx, output):
    """Transform input data for an upgrade cost analysis simulation."""
    GemOpenDssModel.transform(
        input_file=ctx.parent.params["gem_file"],
        output_path=output,
        simulation_model=UpgradeCostAnalysisModel
    )


gem.add_command(snapshot_impact_analysis)
#gem.add_command(time_series_impact_analysis)
gem.add_command(upgrade_cost_analysis)
