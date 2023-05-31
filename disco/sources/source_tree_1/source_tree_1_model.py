"""Model for Source Type 1 feeder input data"""

import copy
import fileinput
import itertools
import json
import logging
import os
import re
from collections import namedtuple, defaultdict
from pathlib import Path

import click

from jade.exceptions import InvalidParameter
from jade.utils.utils import ExtendedJSONEncoder
from disco.cli.common import handle_existing_dir
from disco.enums import Placement, SimulationType, SimulationHierarchy
from disco.models.base import PyDSSControllerModel, ImpactAnalysisBaseModel
from disco.models.snapshot_impact_analysis_model import SnapshotImpactAnalysisModel
from disco.models.time_series_analysis_model import TimeSeriesAnalysisModel
from disco.models.upgrade_cost_analysis_model import UpgradeCostAnalysisModel
from disco.sources.base import (
    BaseOpenDssModel,
    SOURCE_CONFIGURATION_FILENAME,
    DEFAULT_SNAPSHOT_IMPACT_ANALYSIS_PARAMS,
    DEFAULT_TIME_SERIES_IMPACT_ANALYSIS_PARAMS,
    DEFAULT_PV_DEPLOYMENTS_DIRNAME,
    DEFAULT_UPGRADE_COST_ANALYSIS_PARAMS
)
from .source_tree_1_model_inputs import SourceTree1ModelInputs


logger = logging.getLogger(__name__)


SubstationKey = namedtuple("SampleKey", "substation, placement, sample, penetration_level")


def _process_hierarchy(_, __, val):
    return SimulationHierarchy(val)


COMMON_OPTIONS = (
    click.option(
        "--hierarchy",
        type=click.Choice([x.value for x in SimulationHierarchy]),
        callback=_process_hierarchy,
        default=SimulationHierarchy.FEEDER.value,
        show_default=True,
        help="Level at which to configure the simulation",
    ),
    click.option(
        "-S",
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
        "--samples",
        default=["all"],
        multiple=True,
        show_default=True,
        help="samples to add; use ('all',) to auto-detect and add all samples",
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
        "-c",
        "--copy-load-shape-data-files",
        help="Copy load shape data files into the target directory. Otherwise, use references "
             "to existing files.",
        is_flag=True,
        default=False,
        show_default=True,
    ),
    click.option(
        "-x",
        "--strip-load-shape-profiles",
        is_flag=True,
        default=False,
        show_default=True,
        help="Strip load shape profiles from DSS models"
    ),
    click.option(
        "-P",
        "--pv-deployments-dirname",
        help="The output directory name of PV deployments in feeder",
        type=click.STRING,
        default=DEFAULT_PV_DEPLOYMENTS_DIRNAME,
        show_default=True,
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
    default=None,
    show_default=True,
    help="output directory",
)
@click.pass_context
def snapshot(
    ctx,
    hierarchy,
    substations,
    feeders,
    placements,
    samples,
    penetration_levels,
    master_file,
    copy_load_shape_data_files,
    strip_load_shape_profiles,
    pv_deployments_dirname,
    force,
    start,
    output,
):
    """Transform input data for a snapshot simulation"""
    if output is None:
        output = f"snapshot-{hierarchy.value}-models"
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
        hierarchy=hierarchy,
        simulation_params=simulation_params,
        simulation_model=SnapshotImpactAnalysisModel,
        substations=substations,
        feeders=feeders,
        placements=placements,
        samples=samples,
        penetration_levels=penetration_levels,
        master_file=master_file,
        copy_load_shape_data_files=copy_load_shape_data_files,
        strip_load_shape_profiles=strip_load_shape_profiles,
        pv_deployments_dirname=pv_deployments_dirname
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
    default=None,
    show_default=True,
    help="output directory",
)
@click.pass_context
def time_series(
    ctx,
    hierarchy,
    substations,
    feeders,
    placements,
    samples,
    penetration_levels,
    master_file,
    copy_load_shape_data_files,
    strip_load_shape_profiles,
    pv_deployments_dirname,
    force,
    start,
    end,
    resolution,
    output,
):
    """Transform input data for a time series simulation"""
    if output is None:
        output = f"time-series-{hierarchy.value}-models"
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
        simulation_model=TimeSeriesAnalysisModel,
        substations=substations,
        feeders=feeders,
        placements=placements,
        samples=samples,
        penetration_levels=penetration_levels,
        master_file=master_file,
        hierarchy=hierarchy,
        copy_load_shape_data_files=copy_load_shape_data_files,
        strip_load_shape_profiles=strip_load_shape_profiles,
        pv_deployments_dirname=pv_deployments_dirname
    )
    print(
        f"Transformed data from {input_path} to {output} for TimeSeries Analysis."
    )


@click.command()
@common_options
@click.option(
    "-s",
    "--start",
    default=DEFAULT_UPGRADE_COST_ANALYSIS_PARAMS["start_time"],
    show_default=True,
    help="simulation start time",
)
@click.option(
    "-o",
    "--output",
    default=None,
    show_default=True,
    help="output directory"
)
@click.pass_context
def upgrade(
    ctx,
    hierarchy,
    substations,
    feeders,
    placements,
    samples,
    penetration_levels,
    master_file,
    copy_load_shape_data_files,
    strip_load_shape_profiles,
    pv_deployments_dirname,
    force,
    start,
    output
):
    """Transform input data for an automated upgrade simulation"""
    if output is None:
        output = f"upgrade-{hierarchy.value}-models"
    
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
        hierarchy=hierarchy,
        simulation_params=simulation_params,
        simulation_model=UpgradeCostAnalysisModel,
        substations=substations,
        feeders=feeders,
        placements=placements,
        samples=samples,
        penetration_levels=penetration_levels,
        master_file=master_file,
        copy_load_shape_data_files=copy_load_shape_data_files,
        strip_load_shape_profiles=strip_load_shape_profiles,
        pv_deployments_dirname=pv_deployments_dirname
    )
    print(f"Transformed data from {input_path} to {output} for UpgradeCostAnalysis.")


class SourceTree1Model(BaseOpenDssModel):
    """OpenDSS Model for Source Tree 1"""

    DEPLOYMENT_FILE = "PVSystems.dss"
    TRANSFORM_SUBCOMMANDS = {
        "snapshot": snapshot,
        "time-series": time_series,
        "upgrade": upgrade,
    }

    def __init__(self, data):
        data = copy.deepcopy(data)
        self._path = data.pop("path")
        self._substation = data.pop("substation")
        self._feeder = data.pop("feeder")
        self._master_file = data.pop("master", "Master_noPV.dss")
        self._placement = data.pop("placement")
        self._sample = data.pop("sample")
        self._penetration_level = data.pop("penetration_level")
        self._loadshape_directory = data.pop("loadshape_directory")
        self._opendss_directory = data.pop("opendss_directory")
        self._pv_locations = data.pop("pv_locations")
        self._pydss_controllers = data.pop("pydss_controllers")
        self._metadata_directory = data.pop("metadata_directory", None)
        if data.pop("is_base_case"):
            self._name = self.make_feeder_base_case_name(
                self._substation,
                self._feeder,
            )
        else:
            self._name = self.make_name(
                self._substation,
                self._feeder,
                self._placement,
                self._sample,
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
        return self._pydss_controllers

    @staticmethod
    def get_transform_defaults():
        return {
            "substations": "all",
            "feeders": "all",
            "placements": "all",
            "samples": "all",
            "penetration_levels": "all",
            "hierarchy": "feeder",
            "master_file": "Master.dss",
            "force": False
        }

    @classmethod
    def transform(
        cls,
        input_path,
        output_path,
        hierarchy,
        simulation_model,
        simulation_params,
        substations=("all",),
        feeders=("all",),
        placements=("all",),
        samples=("all",),
        penetration_levels=("all",),
        master_file="Master.dss",
        copy_load_shape_data_files=False,
        strip_load_shape_profiles=False,
        pv_deployments_dirname=DEFAULT_PV_DEPLOYMENTS_DIRNAME
    ):
        inputs = SourceTree1ModelInputs(input_path, pv_deployments_dirname)

        if substations == ("all",):
            substations = inputs.list_substations()
        if placements == ("all",):
            placements = inputs.list_placements()
        elif not isinstance(placements[0], float):
            placements = [Placement(x) for x in placements]

        if hierarchy == SimulationHierarchy.FEEDER:
            func = cls._transform_by_feeder
        elif hierarchy == SimulationHierarchy.SUBSTATION:
            func = cls._transform_by_substation
        else:
            assert False

        os.makedirs(output_path, exist_ok=True)
        func(
            inputs,
            input_path,
            output_path,
            simulation_model,
            simulation_params,
            substations,
            feeders,
            placements,
            samples,
            penetration_levels,
            master_file,
            copy_load_shape_data_files,
            strip_load_shape_profiles
        )

    @classmethod
    def _transform_by_feeder(
        cls,
        inputs,
        input_path,
        output_path,
        simulation_model,
        simulation_params,
        substations,
        feeders,
        placements,
        samples,
        penetration_levels,
        master_file,
        copy_load_shape_data_files,
        strip_load_shape_profiles
    ):
        config = []
        base_cases = set()
        for substation, placement in itertools.product(substations, placements):
            for feeder in inputs.list_feeders(substation):
                if feeders != ("all",) and feeder not in feeders:
                    continue
                base_case_name = SourceTree1Model.make_feeder_base_case_name(substation, feeder)
                if base_case_name not in base_cases and issubclass(simulation_model, ImpactAnalysisBaseModel):
                    data = {
                        "path": input_path,
                        "substation": substation,
                        "feeder": feeder,
                        "master": master_file,
                        "placement": None,
                        "sample": None,
                        "penetration_level": None,
                        "deployment_file": None,
                        "loadshape_directory": None,
                        "opendss_directory": inputs.get_opendss_directory(
                            substation, feeder
                        ),
                        "metadata_directory": inputs.get_metadata_directory(substation, feeder),
                        "pv_locations": [],
                        "pydss_controllers": None,
                        "is_base_case": True,
                    }
                    model = cls(data)
                    path = os.path.join(output_path, substation, feeder)
                    out_deployment = model.create_base_case(
                        base_case_name,
                        path,
                        copy_load_shape_data_files=copy_load_shape_data_files,
                    )
                    item = {
                        "deployment": out_deployment,
                        "simulation": simulation_params,
                        "name": base_case_name,
                        "model_type": simulation_model.__name__,
                        "job_order": 0,
                        "is_base_case": True,
                    }
                    config.append(simulation_model.validate(item).dict())
                    base_cases.add(base_case_name)
                key = inputs.create_key(substation, feeder, placement)
                if samples == ("all",):
                    _samples = inputs.list_samples(key)
                else:
                    _samples = [int(x) for x in samples]
                for sample in _samples:
                    if penetration_levels == ("all",):
                        levels = inputs.list_penetration_levels(key, sample)
                    else:
                        levels = [int(x) for x in penetration_levels]
                    pv_configs = inputs.list_pv_configs(
                        substation, feeder, placement, sample
                    )
                    for level in levels:
                        deployment_file = inputs.get_deployment_file(key, sample, level)
                        pydss_controller, pv_profiles = get_pydss_controller_and_profiles(pv_configs)
                        data = {
                            "path": input_path,
                            "substation": substation,
                            "feeder": feeder,
                            "master": master_file,
                            "placement": placement.value,
                            "sample": sample,
                            "penetration_level": level,
                            "deployment_file": deployment_file,
                            "loadshape_directory": None,
                            "opendss_directory": inputs.get_opendss_directory(
                                substation, feeder
                            ),
                            "metadata_directory": inputs.get_metadata_directory(substation, feeder),
                            "pv_locations": [deployment_file],
                            "pydss_controllers": pydss_controller,
                            "is_base_case": False,
                        }
                        model = cls(data)
                        path = os.path.join(output_path, substation, feeder)
                        out_deployment = model.create_deployment(
                            model.name,
                            path,
                            pv_profile=pv_profiles,
                            hierarchy=SimulationHierarchy.FEEDER,
                            copy_load_shape_data_files=copy_load_shape_data_files,
                            strip_load_shape_profiles=strip_load_shape_profiles
                        )
                        out_deployment.project_data["placement"] = placement
                        out_deployment.project_data["sample"] = sample
                        out_deployment.project_data["penetration_level"] = level
                        item = {
                            "deployment": out_deployment,
                            "simulation": simulation_params,
                            "name": model.name,
                            "model_type": simulation_model.__name__,
                            "job_order": level
                        }
                        if issubclass(simulation_model, ImpactAnalysisBaseModel):
                            item["base_case"] = base_case_name
                        config.append(simulation_model.validate(item).dict())

        filename = os.path.join(output_path, SOURCE_CONFIGURATION_FILENAME)
        with open(filename, "w") as f_out:
            json.dump(config, f_out, indent=2, cls=ExtendedJSONEncoder)
        logger.info("Wrote config to %s", filename)

    @classmethod
    def _transform_by_substation(
            cls,
            inputs,
            input_path,
            output_path,
            simulation_model,
            simulation_params,
            substations,
            feeders,
            placements,
            samples,
            penetration_levels,
            master_file,
            copy_load_shape_data_files,
            strip_load_shape_profiles
    ):
        config = []
        deployment_files_by_key = defaultdict(list)
        base_case_names = set()
        for substation, placement in itertools.product(substations, placements):
            if issubclass(simulation_model, ImpactAnalysisBaseModel):
                base_case_name = cls.make_substation_base_case_name(substation)
                if base_case_name not in base_case_names:
                    data = {
                        "path": input_path,
                        "substation": substation,
                        "feeder": None,
                        "master": master_file,
                        "placement": None,
                        "sample": None,
                        "penetration_level": None,
                        "deployment_file": None,
                        "loadshape_directory": None,
                        "opendss_directory": inputs.get_substation_opendss_directory(
                            substation,
                        ),
                        "pv_locations": [],
                        "pydss_controllers": None,
                        "is_base_case": True,
                    }
                    model = cls(data)
                    path = os.path.join(output_path, substation)
                    out_deployment = model.create_substation_base_case(
                        base_case_name,
                        path,
                        copy_load_shape_data_files=copy_load_shape_data_files,
                    )
                    item = {
                        "deployment": out_deployment,
                        "simulation": simulation_params,
                        "name": base_case_name,
                        "model_type": simulation_model.__name__,
                        "job_order": 0,
                        "is_base_case": True,
                    }
                    config.append(simulation_model.validate(item).dict())
                    base_case_names.add(base_case_name)
                    fix_substation_master_file(Path(output_path) / substation / master_file)
            for feeder in inputs.list_feeders(substation):
                if feeders != ("all",) and feeder not in feeders:
                    continue
                key = inputs.create_key(substation, feeder, placement)
                if samples == ("all",):
                    _samples = inputs.list_samples(key)
                else:
                    _samples = [int(x) for x in samples]
                for sample in _samples:
                    if penetration_levels == ("all",):
                        levels = inputs.list_penetration_levels(key, sample)
                    else:
                        levels = [int(x) for x in penetration_levels]
                    for level in levels:
                        substation_key = SubstationKey(substation, placement, sample, level)
                        job_deployment_file = inputs.get_deployment_file(key, sample, level)
                        pv_configs = inputs.list_pv_configs(
                            substation, feeder, placement, sample
                        )
                        pydss_controller, pv_profiles = get_pydss_controller_and_profiles(pv_configs)
                        data = {
                            "path": input_path,
                            "substation": substation,
                            "feeder": "None",
                            "master": master_file,
                            "placement": placement.value,
                            "sample": sample,
                            "penetration_level": level,
                            "deployment_file": job_deployment_file,
                            "loadshape_directory": None,
                            "opendss_directory": inputs.get_opendss_directory(substation, feeder),
                            "pv_locations": [job_deployment_file],
                            "pydss_controllers": pydss_controller,
                            "is_base_case": False,
                        }
                        model = cls(data)
                        path = os.path.join(output_path, substation, feeder)
                        out_deployment = model.create_deployment(
                            model.name,
                            path,
                            pv_profile=pv_profiles,
                            hierarchy=SimulationHierarchy.SUBSTATION,
                            copy_load_shape_data_files=copy_load_shape_data_files,
                            strip_load_shape_profiles=strip_load_shape_profiles
                        )
                        out_deployment.project_data["placement"] = placement
                        out_deployment.project_data["sample"] = sample
                        out_deployment.project_data["penetration_level"] = level
                        out_job_deployment_file = out_deployment.deployment_file
                        if not deployment_files_by_key[substation_key]:
                            # Need to create a job at the substation level.
                            # All params except for the file and name are the same as the job.
                            out_deployment.deployment_file = str(substation_key_to_dss_filename(output_path, substation_key))
                            item = {
                                "deployment": out_deployment,
                                "simulation": simulation_params,
                                "name": cls.make_substation_job_name(substation_key),
                                "model_type": simulation_model.__name__,
                                "job_order": level,
                            }
                            if issubclass(simulation_model, ImpactAnalysisBaseModel):
                                item["base_case"] = base_case_name
                            config.append(simulation_model.validate(item).dict())
                        deployment_files_by_key[substation_key].append(out_job_deployment_file)

        for substation_key, deployment_files in deployment_files_by_key.items():
            make_substation_pv_deployments(output_path, substation_key, deployment_files)

        filename = os.path.join(output_path, SOURCE_CONFIGURATION_FILENAME)
        with open(filename, "w") as f_out:
            json.dump(config, f_out, indent=2, cls=ExtendedJSONEncoder)
        logger.info("Wrote config to %s", filename)

    @staticmethod
    def make_name(substation, feeder, placement, sample, penetration_level):
        fields = (substation, feeder, placement, sample, penetration_level)
        return "__".join([str(x) for x in fields])

    @staticmethod
    def make_substation_job_name(key: SubstationKey):
        return "__".join(
            (
                key.substation,
                key.placement.value,
                str(key.sample),
                str(key.penetration_level),
            )
        )

    @staticmethod
    def make_feeder_base_case_name(substation, feeder):
        fields = (substation, feeder, -1, -1, -1)
        return "__".join([str(x) for x in fields])

    @staticmethod
    def make_substation_base_case_name(substation):
        fields = (substation, -1, -1, -1)
        return "__".join([str(x) for x in fields])


def make_substation_pv_deployments(output_path, key, deployment_files):
    filename = substation_key_to_dss_filename(output_path, key)
    with open(filename, "w") as f_out:
        f_out.write(f"Redirect ../Master.dss\n\n")
        for deployment_file in deployment_files:
            # We have the option of either redirecting to each file or include the content
            # of each file.
            # I'm choosing the latter because PyDSS has code to parse all PVSystems from
            # one file in order to construct PvController.toml files, and so this makes that work.
            # We could make that recurse.
            # It might also be helpful for debugging and analysis to see the PVSystems in one
            # file.
            f_out.write(Path(deployment_file).read_text())
            os.remove(deployment_file)
        f_out.write("\nSolve\n")
    logger.info("Wrote substation-level deployment files to %s", filename)


def substation_key_to_dss_filename(output_path, key):
    path = Path(output_path) / key.substation / "PVDeployments"
    os.makedirs(path, exist_ok=True)
    return path / (SourceTree1Model.make_substation_job_name(key) + ".dss")


def get_pydss_controller_and_profiles(pv_configs):
    pydss_controllers = set()
    pv_profiles = {}
    pydss_controller = None
    for pv_config in pv_configs:
        if pv_config["pydss_controller"] is None:
            ctrl = None
        else:
            ctrl = (pv_config["pydss_controller"]["controller_type"],
                    pv_config["pydss_controller"]["name"])
            if ctrl[1] != "pf1" and ctrl not in pydss_controllers:
                pydss_controller = PyDSSControllerModel.validate(
                    pv_config["pydss_controller"]
                )
                pydss_controllers.add(ctrl)
        pv_profiles[pv_config["name"]] = pv_config.get("pv_profile")

    if len(pydss_controllers) > 1:
        raise Exception(
            f"only 1 pydss controller is currently supported: {pydss_controllers}"
        )

    #assert pydss_controller is not None
    return pydss_controller, pv_profiles


def fix_substation_master_file(filename):
    # These master files have "Redirect <substation>--<feeder>".
    # For better or worse, DISCO has already removed substation and then added
    # "/OpenDSS", so we have to patch the references here.
    # Use "edirect" instead of "Redirect" to avoid case-insensitive checks.
    regex = re.compile(r"edirect \w+--(\w+)")

    def remove_substation(match):
        return "edirect " + match.group(1) + "/OpenDSS"

    with fileinput.input(files=[filename], inplace=True) as f_in:
        for line in f_in:
            line = re.sub(regex, remove_substation, line)
            print(line, end="")
