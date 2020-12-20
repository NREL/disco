"""Model for Source Type 1 feeder input data"""

import copy
import itertools
import json
import logging
import os

from jade.utils.utils import ExtendedJSONEncoder
from disco.enums import Placement
from disco.models.base import PyDSSControllerModel
from disco.sources.base import BaseSourceDataModel, BaseOpenDssModel, \
    SOURCE_CONFIGURATION_FILENAME
from .source_tree_1_model_inputs import SourceTree1ModelInputs


logger = logging.getLogger(__name__)


class SourceTree1Model(BaseOpenDssModel):
    """OpenDSS Model for Source Tree 1"""

    DEFAULT_SELECTIONS = {
        "substations": ["all"],
        "feeders": ["all"],
        "placements": ["all"],
        "deployments": ["all"],
        "penetration_levels": ["all"],
        "master_file": "Master.dss",
    }
    DEPLOYMENT_FILE = "PVSystems.dss"

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
            self._substation, self._feeder, self._placement, self._deployment,
            self._penetration_level,
        )
        data.pop("deployment_file")
        assert not data, str(data)

    @staticmethod
    def get_default_transformation_selections(analysis_type):
        defaults = BaseSourceDataModel.get_default_transformation_selections(analysis_type)
        defaults.update({"model_params": SourceTree1Model.DEFAULT_SELECTIONS})
        return defaults

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
    def transform(cls, config, simulation_model, output_path):
        def get_val(name):
            val = config["model_params"][name]
            if val == ["all"]:
                return "all"
            return val

        input_path = config["input_path"]
        substations = get_val("substations")
        feeders = get_val("feeders")
        placements = get_val("placements")
        deployments = get_val("deployments")
        penetration_levels = get_val("penetration_levels")
        master_file = config["model_params"]["master_file"]
        simulation_params = config["simulation_params"]

        inputs = SourceTree1ModelInputs(input_path)

        if substations == "all":
            substations = inputs.list_substations()
        if feeders == "all":
            feeders = inputs.list_feeders()
        if placements == "all":
            placements = inputs.list_placements()
        elif not isinstance(placements[0], float):
            placements = [Placement(x) for x in placements]

        config = []
        for substation, feeder, placement in itertools.product(substations, feeders, placements):
            key = inputs.create_key(substation, feeder, placement)
            if deployments == "all":
                _deployments = inputs.list_deployments(key)
            else:
                _deployments = deployments
            for deployment in _deployments:
                if penetration_levels == "all":
                    levels = inputs.list_penetration_levels(key, deployment)
                else:
                    levels = penetration_levels
                for level in levels:
                    deployment_file = inputs.get_deployment_file(key, deployment, level)
                    pv_configs = inputs.list_pv_configs(substation, feeder, placement, deployment)
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
                            pydss_controller = PyDSSControllerModel.validate(pv_config["pydss_controller"])
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
                        "opendss_directory": inputs.get_opendss_directory(substation, feeder),
                        "pv_locations": [deployment_file],
                        "pydss_controllers": pydss_controller,
                    }
                    # TODO DT: add pv_profiles to models?
                    # TODO DT: change 'deployment' to 'sample', per Kwami
                    model = cls(data)
                    path = os.path.join(output_path, substation, feeder)
                    out_deployment = model.create_deployment(model.name, path, pv_profile=pv_profiles)
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
