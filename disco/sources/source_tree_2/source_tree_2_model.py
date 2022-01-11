"""Model for Source Type 2 feeder input data"""

import copy
import itertools
import json
import logging
import os

import click

from jade.exceptions import InvalidParameter
from jade.utils.utils import ExtendedJSONEncoder
from PyDSS.common import ControllerType
from disco.cli.common import handle_existing_dir
from disco.enums import Placement, Scale, SimulationType
from disco.models.base import PyDSSControllerModel
from disco.models.snapshot_impact_analysis_model import SnapshotImpactAnalysisModel
from disco.models.time_series_analysis_model import TimeSeriesAnalysisModel
from disco.sources.base import (
    BaseSourceDataModel,
    BaseOpenDssModel,
    SOURCE_CONFIGURATION_FILENAME,
    DEFAULT_SNAPSHOT_IMPACT_ANALYSIS_PARAMS,
    DEFAULT_TIME_SERIES_IMPACT_ANALYSIS_PARAMS,
)
from .source_tree_2_model_inputs import SourceTree2ModelInputs


logger = logging.getLogger(__name__)


COMMON_OPTIONS = (
    click.option(
        "-f",
        "--feeders",
        default=["all"],
        multiple=True,
        show_default=True,
        help="feeders to add; use ('all',) to auto-detect and add all feeders",
    ),
    click.option(
        "-d",
        "--dc-ac-ratios",
        default=["all"],
        multiple=True,
        show_default=True,
        help="DC/AC ratios to add; use ('all',) to auto-detect and add all DC/AC ratios",
    ),
    click.option(
        "-s",
        "--scales",
        default=["all"],
        multiple=True,
        show_default=True,
        help="scales to add; use ('all',) to auto-detect and add all scales",
    ),
    click.option(
        "-p",
        "--placements",
        default=["all"],
        multiple=True,
        show_default=True,
        help="placements to add; use ('all',) to auto-detect and add all placements",
    ),
    click.option(
        "-d",
        "--deployments",
        default=["all"],
        multiple=True,
        show_default=True,
        help="deployments to add; use ('all',) to auto-detect and add all deployments",
    ),
    click.option(
        "-l",
        "--penetration-levels",
        default=["all"],
        multiple=True,
        show_default=True,
        help="penetration-levels to add; use ('all',) to auto-detect and add all penetration-levels",
    ),
    click.option(
        "-m",
        "--master-file",
        default="Master_noPV.dss",
        show_default=True,
        help="Master file for the OpenDSS model",
    ),
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
def snapshot(
    ctx,
    feeders,
    dc_ac_ratios,
    scales,
    placements,
    deployments,
    penetration_levels,
    master_file,
    force,
    start,
    output,
):
    """Transform input data for a snapshot simulation"""
    input_path = ctx.parent.params["input_path"]
    handle_existing_dir(output, force)
    simulation_params = {
        "start_time": start,
        "end_time": start,
        "step_resolution": 900,
        "simulation_type": SimulationType.SNAPSHOT,
    }
    SourceTree2Model.transform(
        input_path=input_path,
        output_path=output,
        simulation_params=simulation_params,
        simulation_model=SnapshotImpactAnalysisModel,
        feeders=feeders,
        dc_ac_ratios=dc_ac_ratios,
        scales=scales,
        placements=placements,
        deployments=deployments,
        penetration_levels=penetration_levels,
        master_file=master_file,
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
@click.option(
    "--pv-profile",
    default=None,
    type=str,
    help="profile to use for all PV Systems",
)
@click.pass_context
def time_series(
    ctx,
    feeders,
    dc_ac_ratios,
    scales,
    placements,
    deployments,
    penetration_levels,
    master_file,
    force,
    start,
    end,
    resolution,
    output,
    pv_profile,
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
    SourceTree2Model.transform(
        input_path=input_path,
        output_path=output,
        simulation_params=simulation_params,
        simulation_model=TimeSeriesAnalysisModel,
        feeders=feeders,
        dc_ac_ratios=dc_ac_ratios,
        scales=scales,
        placements=placements,
        deployments=deployments,
        penetration_levels=penetration_levels,
        master_file=master_file,
        pv_profile=pv_profile,
    )
    print(
        f"Transformed data from {input_path} to {output} for TimeSeries Analysis."
    )


class SourceTree2Model(BaseOpenDssModel):
    """Source Type 2 Feeder Model Inputs Class"""

    TRANSFORM_SUBCOMMANDS = {
        "snapshot": snapshot,
        "time-series": time_series,
    }

    def __init__(self, data):
        data = copy.deepcopy(data)
        self._path = data.pop("path")
        self._feeder = data.pop("feeder")
        self._master = data.pop("master", "Master_noPV.dss")
        self._dcac = data.pop("dcac")
        self._scale = data.pop("scale")
        self._placement = data.pop("placement")
        self._deployment = data.pop("deployment")
        self._penetration_level = data.pop("penetration_level")
        self._loadshape_directory = data.pop("loadshape_directory")
        self._opendss_directory = data.pop("opendss_directory")
        self._pv_locations = data.pop("pv_locations")
        self._metadata_directory = data.pop("metadata_directory", None)
        if data.pop("is_base_case"):
            self._name = self.make_base_case_name(self._feeder, self._dcac)
        else:
            self._name = self.make_name(
                self._feeder,
                self._dcac,
                self._scale,
                self._placement,
                self._deployment,
                self._penetration_level,
            )
        data.pop("deployment_file")
        assert not data, str(data)

    @property
    def dc_ac_ratio(self):
        return self._dcac

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
        return self._pv_locations

    @property
    def pydss_controllers(self):
        return PyDSSControllerModel(
            controller_type=ControllerType.PV_CONTROLLER,
            name="volt-var",
        )

    @staticmethod
    def get_transform_subcommand(name):
        if name not in SourceTree2Model.TRANSFORM_SUBCOMMANDS:
            raise InvalidParameter(f"{name} is not supported")
        return SourceTree2Model.TRANSFORM_SUBCOMMANDS[name]

    @staticmethod
    def list_transform_subcommands():
        return sorted(list(SourceTree2Model.TRANSFORM_SUBCOMMANDS.keys()))

    @classmethod
    def transform(
        cls,
        input_path,
        output_path,
        simulation_model,
        simulation_params,
        feeders=("all",),
        dc_ac_ratios=("all",),
        scales=("all",),
        placements=("all",),
        deployments=("all",),
        penetration_levels=("all",),
        master_file="Master.dss",
        pv_profile=None,
    ):
        inputs = SourceTree2ModelInputs(input_path)

        if feeders == ("all",):
            feeders = inputs.list_feeders()
        if dc_ac_ratios == ("all",):
            dc_ac_ratios = inputs.list_dcac_ratios()
        elif not isinstance(dc_ac_ratios[0], float):
            dc_ac_ratios = [float(x) for x in dc_ac_ratios]
        if scales == ("all",):
            scales = inputs.list_scales()
        elif not isinstance(scales[0], Scale):
            scales = [Scale(x) for x in scales]
        if placements == ("all",):
            placements = inputs.list_placements()
        elif not isinstance(placements[0], float):
            placements = [Placement(x) for x in placements]

        config = []
        for feeder, dcac, scale, placement in itertools.product(
            feeders, dc_ac_ratios, scales, placements
        ):
            key = inputs.create_key(feeder, dcac, scale, placement)
            if deployments == ("all",):
                _deployments = inputs.list_deployments(key)
            else:
                _deployments = [int(x) for x in deployments]
            for deployment in _deployments:
                if penetration_levels == ("all",):
                    levels = inputs.list_penetration_levels(key, deployment)
                else:
                    levels = [int(x) for x in penetration_levels]
                for level in levels:
                    deployment_file = inputs.get_deployment_file(key, deployment, level)
                    data = {
                        "path": input_path,
                        "feeder": feeder,
                        "master": master_file,
                        "dcac": dcac,
                        "scale": scale.value,
                        "placement": placement.value,
                        "deployment": deployment,
                        "penetration_level": level,
                        "deployment_file": deployment_file,
                        "loadshape_directory": inputs.get_loadshape_directory(feeder),
                        "opendss_directory": inputs.get_opendss_directory(feeder),
                        "pv_locations": [deployment_file],
                        "is_base_case": False,
                    }
                    model = cls(data)
                    path = os.path.join(output_path, feeder)
                    out_deployment = model.create_deployment(
                        model.name, path, pv_profile=pv_profile
                    )
                    item = {
                        "deployment": out_deployment,
                        "simulation": simulation_params,
                        "name": model.name,
                        "model_type": simulation_model.__name__,
                    }
                    config.append(simulation_model.validate(item).dict())

        filename = os.path.join(output_path, SOURCE_CONFIGURATION_FILENAME)
        with open(filename, "w") as f_out:
            json.dump(config, f_out, indent=2, cls=ExtendedJSONEncoder)
        logger.info("Wrote config to %s", filename)

    @staticmethod
    def make_name(feeder, dcac, scale, placement, deployment, penetration_level):
        fields = (feeder, dcac, scale, placement, deployment, penetration_level)
        return "__".join([str(x) for x in fields])

    @staticmethod
    def make_base_case_name(feeder, dcac):
        fields = (feeder, dcac, -1, -1, -1)
        return "__".join([str(x) for x in fields])
