"""Model for GEM feeder input data.
The model can be transformed into DISCO OpenDSS model with PV deployments.
"""

import logging
import os
import shutil

import click

from jade.exceptions import InvalidParameter
from disco.cli.common import handle_existing_dir
from disco.models.snapshot_impact_analysis_model import SnapshotImpactAnalysisModel
from disco.sources.base import BaseOpenDssModel, DEFAULT_SNAPSHOT_IMPACT_ANALYSIS_PARAMS
from .factory import read_config_data


logger = logging.getLogger(__name__)


COMMON_OPTIONS = (
    click.option(
        "-F",
        "--force",
        help="overwrite existing directory",
        is_flag=True,
        default=False,
        show_default=True,
    ),
)

def common_options(func):
    for option in reversed(COMMON_OPTIONS):
        func = option(func)
    return func


@click.command()
@common_options
@click.option(
    "-o",
    "--output",
    default=DEFAULT_SNAPSHOT_IMPACT_ANALYSIS_PARAMS["output_dir"],
    show_default=True,
    help="output directory",
)
@click.pass_context
def snapshot(ctx, force, output):
    """Transform input data for a snapshot impact analysis simulation"""
    input_path = ctx.parent.params["input_path"]
    handle_existing_dir(output, force)
    GemModel.transform(
        input_file=input_path,
        output_path=output,
        simulation_model=SnapshotImpactAnalysisModel,
    )
    print(f"Transformed data from {input_path} to {output} for Snapshot Analysis.")


class GemModel(BaseOpenDssModel):
    """GEM Feeder Model Inputs Class"""

    TRANSFORM_SUBCOMMANDS = {
        "snapshot": snapshot
    }

    @property
    def substation(self):
        return None

    @staticmethod
    def get_transform_subcommand(name):
        """Return a click command for name."""
        if name not in GemModel.TRANSFORM_SUBCOMMANDS:
            raise InvalidParameter(f"{name} is not supported")
        return GemModel.TRANSFORM_SUBCOMMANDS[name]

    @staticmethod
    def list_transform_subcommands():
        return sorted(list(GemModel.TRANSFORM_SUBCOMMANDS.keys()))

    @classmethod
    def transform(
        cls, input_file, output_path, simulation_model, include_pv_systems=True
    ):
        """Transform GEM input data to a DISCO data model.

        Parameters
        ----------
        input_file : str
        output_path : str

        """
        if os.path.exists(output_path):
            shutil.rmtree(output_path)
        os.makedirs(output_path)
        read_config_data(input_file).generate_output_data(
            output_path, include_pv_systems, simulation_model
        )
