"""Model for Source Type 1 feeder input data"""

import copy
import itertools
import json
import logging
import os

import click

from jade.exceptions import InvalidParameter
from jade.utils.utils import ExtendedJSONEncoder
from disco.cli.common import handle_existing_dir
from disco.enums import Placement, SimulationType
from disco.models.base import PyDSSControllerModel
from disco.models.snapshot_impact_analysis_model import SnapshotImpactAnalysisModel
from disco.models.time_series_impact_analysis_model import TimeSeriesImpactAnalysisModel
from disco.sources.base import (
    BaseOpenDssModel,
    SOURCE_CONFIGURATION_FILENAME,
    DEFAULT_SNAPSHOT_IMPACT_ANALYSIS_PARAMS,
    DEFAULT_TIME_SERIES_IMPACT_ANALYSIS_PARAMS,
)
from .source_tree_1_model_inputs import SourceTree1ModelInputs


logger = logging.getLogger(__name__)


COMMON_OPTIONS = (
    click.option(
        "-s",
        "--substations",
        default=["all"],
        multiple=True,
        show_default=True,
        help="substations to add; use ('all',) to auto-detect and add all substations",
    ),
    click.option(
        "-f",
        "--feeders",
        default=["all"],
        multiple=True,
        show_default=True,
        help="feeders to add; use ('all',) to auto-detect and add all feeders",
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
        default="Master.dss",
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
def snapshot_impact_analysis(
    ctx,
    substations,
    feeders,
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
    SourceTree1Model.transform(
        input_path=input_path,
        output_path=output,
        simulation_params=simulation_params,
        simulation_model=SnapshotImpactAnalysisModel,
        substations=substations,
        feeders=feeders,
        placements=placements,
        deployments=deployments,
        penetration_levels=penetration_levels,
        master_file=master_file,
    )
    print(f"Transformed data from {input_path} to {output} for SnapshotImpactAnalysis.")


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
@click.pass_context
def time_series_impact_analysis(
    ctx,
    substations,
    feeders,
    placements,
    deployments,
    penetration_levels,
    master_file,
    force,
    start,
    end,
    resolution,
    output,
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
    SourceTree1Model.transform(
        input_path=input_path,
        output_path=output,
        simulation_params=simulation_params,
        simulation_model=TimeSeriesImpactAnalysisModel,
        substations=substations,
        feeders=feeders,
        placements=placements,
        deployments=deployments,
        penetration_levels=penetration_levels,
        master_file=master_file,
    )
    print(
        f"Transformed data from {input_path} to {output} for TimeSeriesImpactAnalysis."
    )


class SourceTree1Model(BaseOpenDssModel):
    """OpenDSS Model for Source Tree 1"""

    DEPLOYMENT_FILE = "PVSystems.dss"
    TRANSFORM_SUBCOMMANDS = {
        "snapshot-impact-analysis": snapshot_impact_analysis,
        "time-series-impact-analysis": time_series_impact_analysis,
    }

    def __init__(self, data):
        data = copy.deepcopy(data)
        self._path = data.pop("path")
        self._substation = data.pop("substation")
        self._feeder = data.pop("feeder")
        self._master_file = data.pop("master", "Master_noPV.dss")
        self._placement = data.pop("placement")
        self._deployment = data.pop("deployment")
        self._penetration_level = data.pop("penetration_level")
        self._loadshape_directory = data.pop("loadshape_directory")
        self._opendss_directory = data.pop("opendss_directory")
        self._pv_locations = data.pop("pv_locations")
        self._pydss_controllers = data.pop("pydss_controllers")
        self._name = self.make_name(
            self._substation,
            self._feeder,
            self._placement,
            self._deployment,
            self._penetration_level,
        )
        data.pop("deployment_file")
        assert not data, str(data)

    @staticmethod
    def get_transform_subcommand(name):
        if name not in SourceTree1Model.TRANSFORM_SUBCOMMANDS:
            raise InvalidParameter(f"{name} is not supported")
        return SourceTree1Model.TRANSFORM_SUBCOMMANDS[name]

    @staticmethod
    def list_transform_subcommands():
        return sorted(list(SourceTree1Model.TRANSFORM_SUBCOMMANDS.keys()))

    @property
    def substation(self):
        return self._substation

    @property
    def feeder(self):
        return self._feeder

    @property
    def dc_ac_ratio(self):
        return 1.15

    @property
    def loadshape_directory(self):
        return self._loadshape_directory

    @property
    def opendss_directory(self):
        return self._opendss_directory

    @property
    def master_file(self):
        return os.path.join(self._opendss_directory, self._master_file)

    @property
    def name(self):
        return self._name

    @property
    def pv_locations(self):
        return self._pv_locations

    @property
    def pydss_controllers(self):
        return self._pydss_controllers

    @classmethod
    def transform(
        cls,
        input_path,
        output_path,
        simulation_model,
        simulation_params,
        substations=("all",),
        feeders=("all",),
        placements=("all",),
        deployments=("all",),
        penetration_levels=("all",),
        master_file="Master.dss",
    ):
        inputs = SourceTree1ModelInputs(input_path)

        if substations == ("all",):
            substations = inputs.list_substations()
        if feeders == ("all",):
            feeders = inputs.list_feeders()
        if placements == ("all",):
            placements = inputs.list_placements()
        elif not isinstance(placements[0], float):
            placements = [Placement(x) for x in placements]

        config = []
        for substation, feeder, placement in itertools.product(
            substations, feeders, placements
        ):
            key = inputs.create_key(substation, feeder, placement)
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
                    pv_configs = inputs.list_pv_configs(
                        substation, feeder, placement, deployment
                    )
                    # Validation of a PyDSSControllerModel is currently slow.
                    # This is a workaround.
                    # TODO DT
                    # update: may be fixed. test on large dataset
                    pydss_controllers = set()
                    pv_profiles = {}
                    pydss_controller = None
                    for pv_config in pv_configs:
                        # TODO DT: the overall model needs to support a mapping
                        # instead of a single controller
                        tmp = pv_config["pydss_controller"]
                        ctrl = (tmp["controller_type"], tmp["name"])
                        if ctrl[1] != "pf1" and ctrl not in pydss_controllers:
                            pydss_controller = PyDSSControllerModel.validate(
                                pv_config["pydss_controller"]
                            )
                            pydss_controllers.add(ctrl)
                        pv_profiles[pv_config["name"]] = pv_config["pv_profile"]
                    if len(pydss_controllers) > 1:
                        raise Exception(
                            f"only 1 pydss controller is currently supported: {pydss_controllers}"
                        )
                    data = {
                        "path": input_path,
                        "substation": substation,
                        "feeder": feeder,
                        "master": master_file,
                        "placement": placement.value,
                        "deployment": deployment,
                        "penetration_level": level,
                        "deployment_file": deployment_file,
                        "loadshape_directory": None,
                        "opendss_directory": inputs.get_opendss_directory(
                            substation, feeder
                        ),
                        "pv_locations": [deployment_file],
                        "pydss_controllers": pydss_controller,
                    }
                    # TODO DT: add pv_profiles to models?
                    # TODO DT: change 'deployment' to 'sample', per Kwami
                    model = cls(data)
                    path = os.path.join(output_path, substation, feeder)
                    out_deployment = model.create_deployment(
                        model.name, path, pv_profile=pv_profiles
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
    def make_name(substation, feeder, placement, deployment, penetration_level):
        fields = (substation, feeder, placement, deployment, penetration_level)
        return "__".join([str(x) for x in fields])
