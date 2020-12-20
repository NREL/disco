"""Model for Source Type 2 feeder input data"""

import copy
import itertools
import json
import logging
import os

from jade.utils.utils import ExtendedJSONEncoder
from PyDSS.common import ControllerType
from disco.enums import Placement, Scale
from disco.models.base import PyDSSControllerModel
from disco.sources.base import BaseSourceDataModel, BaseOpenDssModel, \
    SOURCE_CONFIGURATION_FILENAME
from .source_tree_2_model_inputs import SourceTree2ModelInputs


logger = logging.getLogger(__name__)


class SourceTree2Model(BaseOpenDssModel):
    """Source Type 2 Feeder Model Inputs Class"""

    DEFAULT_SELECTIONS = {
        "feeders": ["all"],
        "dc_ac_ratios": ["all"],
        "scales": ["all"],
        "placements": ["all"],
        "deployments": ["all"],
        "penetration_levels": ["all"],
        "master_file": "Master_noPV.dss",
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
        self._name = self.make_name(
            self._feeder, self._dcac, self._scale, self._placement,
            self._deployment, self._penetration_level,
        )
        data.pop("deployment_file")
        assert not data, str(data)

    @staticmethod
    def get_default_transformation_selections(analysis_type):
        defaults = BaseSourceDataModel.get_default_transformation_selections(analysis_type)
        defaults.update({"model_params": SourceTree2Model.DEFAULT_SELECTIONS})
        return defaults

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

    @classmethod
    def transform(cls, config, simulation_model, output_path):
        def get_val(name):
            val = config["model_params"][name]
            if val == ["all"]:
                return "all"
            return val

        input_path = config["input_path"]
        feeders = get_val("feeders")
        dcac_ratios = get_val("dcac_ratios")
        scales = get_val("scales")
        placements = get_val("placements")
        deployments = get_val("deployments")
        penetration_levels = get_val("penetration_levels")
        master_file = config["model_params"]["master_file"]
        pv_profile = config["model_params"].get("pv_profile")
        simulation_params = config["simulation_params"]

        inputs = SourceTree2ModelInputs(input_path)

        if feeders == "all":
            feeders = inputs.list_feeders()
        if dcac_ratios == "all":
            dcac_ratios = inputs.list_dcac_ratios()
        elif not isinstance(dcac_ratios[0], float):
            dcac_ratios = [float(x) for x in dcac_ratios]
        if scales == "all":
            scales = inputs.list_scales()
        elif not isinstance(scales[0], Scale):
            scales = [Scale(x) for x in scales]
        if placements == "all":
            placements = inputs.list_placements()
        elif not isinstance(placements[0], float):
            placements = [Placement(x) for x in placements]

        config = []
        for feeder, dcac, scale, placement in itertools.product(feeders, dcac_ratios, scales, placements):
            key = inputs.create_key(feeder, dcac, scale, placement)
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
                    }
                    model = cls(data)
                    path = os.path.join(output_path, feeder)
                    out_deployment = model.create_deployment(model.name, path, pv_profile=pv_profile)
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
