import logging
import os

from jade.utils.utils import load_data

from disco.pydss.common import ConfigType
from disco.extensions.upgrade_simulation.upgrade_inputs import UpgradeInputs
from disco.pydss.pydss_configuration_base import PyDssConfigurationBase

logger = logging.getLogger(__name__)


DEFAULT_UPGRADE_COST_DB_FILE = os.path.join(
    os.path.dirname(__file__),
    "upgrades",
    "Generic_DISCO_cost_database_v2.xlsx"
)

DEFAULT_UPGRADE_PARAMS_FILE = os.path.join(
    os.path.dirname(__file__),
    "upgrades",
    "upgrade_parameters.toml"
)


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
        # this method not in use, simply return an empty dict.
        return {}

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
