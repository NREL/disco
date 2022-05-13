"""
Defines EPRI Open DSS model.
The model can be transformed into DISCO OpenDSS model with PV deployments.
"""

import json
import logging
import os

import click

from jade.exceptions import InvalidParameter
from jade.utils.utils import ExtendedJSONEncoder
from PyDSS.common import ControllerType

from disco.cli.common import handle_existing_dir
from disco.enums import SimulationType, SimulationHierarchy
from disco.models.base import PyDSSControllerModel
from disco.models.snapshot_impact_analysis_model import SnapshotImpactAnalysisModel
from disco.models.time_series_analysis_model import TimeSeriesAnalysisModel
from disco.sources.base import (
    BaseOpenDssModel,
    SOURCE_CONFIGURATION_FILENAME,
    DEFAULT_SNAPSHOT_IMPACT_ANALYSIS_PARAMS,
    DEFAULT_TIME_SERIES_IMPACT_ANALYSIS_PARAMS,
)


logger = logging.getLogger(__name__)


COMMON_OPTIONS = (
    click.option(
        "-f",
        "--feeders",
        default=["all"],
        multiple=True,
        show_default=True,
        help="feeders to add; use 'all' to auto-detect and add all feeders",
    ),
    click.option(
        "-F",
        "--force",
        help="overwrite existing directory",
        is_flag=True,
        default=False,
        show_default=True
    )
)

def common_options(func):
    for option in reversed(COMMON_OPTIONS):
        func = option(func)
    return func


@click.command()
@common_options
@click.option(
    "-s",
    "--start",
    default=DEFAULT_SNAPSHOT_IMPACT_ANALYSIS_PARAMS["start_time"],
    show_default=True,
    help="simulation start time",
)
@click.option(
    "-o",
    "--output",
    default=DEFAULT_SNAPSHOT_IMPACT_ANALYSIS_PARAMS["output_dir"],
    show_default=True,
    help="output directory",
)
@click.pass_context
def snapshot(ctx, feeders, force, start, output):
    """Transform input data for a snapshot simulation"""
    input_path = ctx.parent.params["input_path"]
    handle_existing_dir(output, force)
    simulation_params = {
        "start_time": start,
        "end_time": start,
        "step_resolution": 900,
        "simulation_type": SimulationType.SNAPSHOT,
    }
    EpriModel.transform(
        input_path=input_path,
        output_path=output,
        simulation_params=simulation_params,
        simulation_model=SnapshotImpactAnalysisModel,
        feeders=feeders,
    )
    print(f"Transformed data from {input_path} to {output} for Snapshot Analysis.")


@click.command()
@common_options
@click.option(
    "-s",
    "--start",
    default=DEFAULT_TIME_SERIES_IMPACT_ANALYSIS_PARAMS["start_time"],
    show_default=True,
    help="simulation start time",
)
@click.option(
    "-e",
    "--end",
    default=DEFAULT_TIME_SERIES_IMPACT_ANALYSIS_PARAMS["end_time"],
    show_default=True,
    help="simulation end time",
)
@click.option(
    "-p",
    "--pv-profile",
    type=str,
    help="load shape profile name to apply to all PVSystems",
)
@click.option(
    "-r",
    "--resolution",
    default=DEFAULT_TIME_SERIES_IMPACT_ANALYSIS_PARAMS["step_resolution"],
    type=int,
    show_default=True,
    help="simulation step resolution in seconds",
)
@click.option(
    "-o",
    "--output",
    default=DEFAULT_TIME_SERIES_IMPACT_ANALYSIS_PARAMS["output_dir"],
    show_default=True,
    help="output directory",
)
@click.pass_context
def time_series(
    ctx, feeders, force, start, end, pv_profile, resolution, output
):
    """Transform input data for a time series simulation"""
    input_path = ctx.parent.params["input_path"]
    handle_existing_dir(output, force)
    simulation_params = {
        "start_time": start,
        "end_time": end,
        "step_resolution": resolution,
        "simulation_type": SimulationType.QSTS,
    }
    EpriModel.transform(
        input_path=input_path,
        output_path=output,
        simulation_params=simulation_params,
        simulation_model=TimeSeriesAnalysisModel,
        feeders=feeders,
        pv_profile=pv_profile,
    )
    print(
        f"Transformed data from {input_path} to {output} for TimeSeries Analysis."
    )


class EpriModel(BaseOpenDssModel):
    """EPRI Feeder Model Inputs Class"""

    TRANSFORM_SUBCOMMANDS = {
        "snapshot": snapshot,
        "time-series": time_series,
    }
    MASTER_FILENAME_BY_FEEDER = {
        "J1": "Master_noPV.dss",
        "K1": "Master_NoPV.dss",
        "M1": "Master_NoPV.dss",
    }

    def __init__(self, data):
        self._feeder = data.pop("feeder")
        self._loadshape_directory = data.pop("loadshape_directory")
        self._opendss_directory = data.pop("opendss_directory")
        self._metadata_directory = data.pop("metadata_directory", None)
        self._master = data.pop("master")
        self._name = data.pop("name")
        self._pv_locations = data.pop("pv_locations")

    @property
    def dc_ac_ratio(self):
        return 1.15

    @property
    def substation(self):
        return None

    @property
    def feeder(self):
        return self._feeder

    @property
    def loadshape_directory(self):
        return self._loadshape_directory

    @property
    def opendss_directory(self):
        return self._opendss_directory

    @property
    def master_file(self):
        return os.path.join(self._opendss_directory, self._master)

    @property
    def metadata_directory(self):
        return self._metadata_directory

    @property
    def name(self):
        return self._name

    @property
    def pv_locations(self):
        if not self._pv_locations:
            return []

        files = []
        for pv_location in self._pv_locations:
            _file = os.path.join(self._opendss_directory, pv_location)
            if not os.path.exists(_file):
                raise FileNotFoundError(f"File not exist - {_file}")
            files.append(_file)

        return files

    @property
    def pydss_controllers(self):
        return PyDSSControllerModel(
            controller_type=ControllerType.PV_CONTROLLER,
            name="volt_var_ieee_1547_2018_catB",
        )

    @staticmethod
    def get_transform_subcommand(name):
        if name not in EpriModel.TRANSFORM_SUBCOMMANDS:
            raise InvalidParameter(f"{name} is not supported")
        return EpriModel.TRANSFORM_SUBCOMMANDS[name]

    @staticmethod
    def list_transform_subcommands():
        return sorted(list(EpriModel.TRANSFORM_SUBCOMMANDS.keys()))

    @classmethod
    def transform(
        cls,
        input_path,
        output_path,
        simulation_params,
        simulation_model,
        feeders=("all",),
        existing_pv=True,
        pv_profile=None,
    ):
        config = []
        os.makedirs(output_path, exist_ok=True)

        if feeders == ("all",):
            feeders = [
                x
                for x in os.listdir(input_path)
                if os.path.isdir(os.path.join(input_path, x))
            ]

        for i, feeder in enumerate(feeders):
            pv_locations = []
            pv_path = os.path.join(input_path, feeder, "ExistingPV.dss")
            if existing_pv and os.path.exists(pv_path):
                pv_locations.append("ExistingPV.dss")
            master_filename = cls.MASTER_FILENAME_BY_FEEDER[feeder]
            name = f"{feeder}__deployment{i + 1}"
            data = {
                "feeder": feeder,
                "loadshape_directory": None,
                "opendss_directory": os.path.join(input_path, feeder),
                "master": master_filename,
                "name": name,
                "pv_locations": pv_locations,
            }
            model = cls(data)
            path = os.path.join(output_path, feeder)
            deployment = model.create_deployment(
                name,
                path,
                pv_profile=pv_profile,
                hierarchy=SimulationHierarchy.FEEDER,
            )

            item = {
                "deployment": deployment,
                "simulation": simulation_params,
                "name": model.name,
                "model_type": simulation_model.__name__,
            }
            config.append(simulation_model.validate(item).dict())

        filename = os.path.join(output_path, SOURCE_CONFIGURATION_FILENAME)
        with open(filename, "w") as f_out:
            json.dump(config, f_out, indent=2, cls=ExtendedJSONEncoder)
        logger.info("Wrote config to %s", filename)
