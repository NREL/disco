import copy
import logging
import os

from PyDSS.common import ControllerType
from jade.utils.utils import load_data

import disco
from disco.pydss.common import ConfigType
from disco.extensions.upgrade_simulation.upgrade_inputs import UpgradeInputs
from disco.pydss.pydss_configuration_base import PyDssConfigurationBase


logger = logging.getLogger(__name__)


DEFAULT_CONTROLLER_CONFIG_FILE = os.path.join(
    os.path.dirname(getattr(disco, "__path__")[0]), "disco", "pydss",
    "config", "pv_controllers.toml"
)

DEFAULT_PYDSS_CONFIG = {
    ConfigType.SIMULATION_CONFIG: {
        "default": {"enable_pydss_solve": True}
    },
    ConfigType.CONTROLLER_CONFIG: [
        {
            "controller_type": ControllerType.PV_CONTROLLER.value,
            "name": "volt_var_upgrade",
            "filename": DEFAULT_CONTROLLER_CONFIG_FILE
        }
    ]
}


class UpgradeConfiguration(PyDssConfigurationBase):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._pydss_inputs = self.get_default_pydss_config()

        # Customize pydss config
        if "enable_pydss_solve" in kwargs:
            self.enable_pydss_solve(kwargs["enable_pydss_solve"])

    @classmethod
    def auto_config(cls, inputs, **kwargs):
        if isinstance(inputs, str):
            inputs = UpgradeInputs(inputs)
        
        config = cls(**kwargs)
        for job in inputs.iter_jobs():
            config.add_job(job)
        
        return config

    def _serialize(self, data):
        data["pydss_inputs"] = self.serialize_pydss_inputs(self._pydss_inputs)

    @staticmethod
    def get_default_pydss_config():
        """Return the default PyDSS configuration.

        Returns
        -------
        dict

        """
        config_types = [ConfigType.SIMULATION_CONFIG, ConfigType.CONTROLLER_CONFIG]
        config = {k: copy.deepcopy(DEFAULT_PYDSS_CONFIG[k]) for k in config_types}
        return config

    def enable_pydss_solve(self, value: bool):
        self._pydss_inputs[ConfigType.SIMULATION_CONFIG]["default"]["enable_pydss_solve"] = value
        if value is True:
            message = "Enable PyDSS solve."
        else:
            message = "Disable PyDSS solve for upgrade simulation."
        logger.info(message)

    def get_pydss_controller_model(self, name):
        controller_config = self._pydss_inputs[ConfigType.CONTROLLER_CONFIG]
        for controller in controller_config:
            if controller["name"] != name:
                continue
            data = load_data(filename= controller["filename"])
            if name not in data:
                continue
            return data[name]
        raise ValueError(f"No controller named '{name}' configured.")

    def create_from_result(self, job, output_dir):
        cls = self.job_execution_class(job.extension)
        return cls.create(job, output=output_dir)
