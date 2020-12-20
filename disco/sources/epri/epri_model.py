"""
Defines EPRI Open DSS model.
The model can be transformed into DISCO OpenDSS model with PV deployments.
"""

import json
import logging
import os

from jade.utils.utils import ExtendedJSONEncoder

from PyDSS.common import ControllerType
from disco.models.base import PyDSSControllerModel
from disco.sources.base import BaseOpenDssModel, SOURCE_CONFIGURATION_FILENAME


logger = logging.getLogger(__name__)


class EpriModel(BaseOpenDssModel):
    """EPRI Feeder Model Inputs Class"""

    MASTER_FILENAME_BY_FEEDER = {
        "J1": "Master_noPV.dss",
        "K1": "Master_NoPV.dss",
        "M1": "Master_NoPV.dss",
    }

    def __init__(self, data):
        self._feeder = data.pop("feeder")
        self._loadshape_directory = data.pop("loadshape_directory")
        self._opendss_directory = data.pop("opendss_directory")
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
            name="volt-var",
        )

    @classmethod
    def transform(cls, input_path, output_path, simulation_params,
                  simulation_model, feeders=("all",), existing_pv=True,
                  pv_profile=None):
        config = []
        os.makedirs(output_path, exist_ok=True)

        if feeders == ("all",):
            feeders = [x for x in os.listdir(input_path)
                       if os.path.isdir(os.path.join(input_path, x))]

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
            deployment = model.create_deployment(name, path, pv_profile=pv_profile)

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
