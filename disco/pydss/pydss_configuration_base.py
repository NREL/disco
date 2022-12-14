"""Contains functionality to configure PyDss simulations."""

import copy
import logging
import os

from jade.exceptions import InvalidParameter
from PyDSS.common import ControllerType
from PyDSS.registry import Registry

import disco
from disco.distribution.distribution_configuration import DistributionConfiguration
from disco.enums import AnalysisType, get_enum_from_value, SimulationType
from disco.pydss.common import ConfigType


logger = logging.getLogger(__name__)

DEFAULT_CONTROLLER_CONFIG_FILE = os.path.join(
    os.path.dirname(getattr(disco, "__path__")[0]), "disco", "pydss",
    "config", "pv_controllers.toml"
)

DEFAULT_CONTROLLER_CONFIGS = [
    {
        "controller_type": ControllerType.PV_CONTROLLER.value,
        "name": "volt_var_1",
        "filename": DEFAULT_CONTROLLER_CONFIG_FILE
    },
    {
        "controller_type": ControllerType.PV_CONTROLLER.value,
        "name": "volt_var_ieee_1547_2018_catB",
        "filename": DEFAULT_CONTROLLER_CONFIG_FILE
    },
]

DEFAULT_LOAD_SHAPE_START_TIME = "2021-01-01 00:00:00.0"

DEFAULT_PYDSS_SIMULATION_CONFIG = {
    "project": {
        "start_time": "2021-01-01 00:00:00.0",
        "loadshape_start_time": DEFAULT_LOAD_SHAPE_START_TIME,
        "simulation_duration_min": 1.0,
        "step_resolution_sec": 900.0,
        "max_control_iterations": 50,
        "error_tolerance": 0.0001,
        "max_error_tolerance": 0.01,
        "convergence_error_percent_threshold": 1.0,
        "skip_export_on_convergence_error": True,
        "use_controller_registry": True
    },
    "exports": {
        "export_results": True,
        "export_elements": True,
        "export_element_types": ["Loads", "PVSystems"],  # Make this empty to export all types.
        "export_event_log": True,
        "export_format": "h5",
        "export_compression": True,
        "export_data_tables": False,
        "export_pv_profiles": False,
    },
    "reports": {},
}

DEFAULT_PYDSS_CONFIG = {
    ConfigType.SIMULATION_CONFIG: {
        "default": copy.deepcopy(DEFAULT_PYDSS_SIMULATION_CONFIG),
    },
    ConfigType.CONTROLLER_CONFIG: DEFAULT_CONTROLLER_CONFIGS,
    ConfigType.SCENARIOS: [],
}


def get_default_exports_file(simulation_type: SimulationType, analysis_type: AnalysisType):
    """Return the default exports file

    Parameters
    ----------
    simulation_type: SimulationType
    analysis_type: AnalysisType

    Returns
    -------
    str

    """
    if simulation_type == SimulationType.SNAPSHOT:
        filename = "snapshot-exports.toml"
    elif simulation_type in (SimulationType.QSTS, SimulationType.TIME_SERIES):
        if analysis_type == AnalysisType.COST_BENEFIT:
            filename = "cba-exports.toml"
        else:
            filename = "exports.toml"
    else:
        assert False, f"Exports for {simulation_type} is not supported."

    return os.path.join(
        os.path.dirname(getattr(disco, "__path__")[0]),
        "disco",
        "pydss",
        "config",
        filename
    )


def get_default_reports_file(simulation_type: SimulationType):
    """Return the default report file for the simulation type.

    Parameters
    ----------
    simulation_type : SimulationType

    Returns
    -------
    str

    """
    if simulation_type in (SimulationType.QSTS, SimulationType.TIME_SERIES):
        filename = "time_series_reports.toml"
    elif simulation_type == SimulationType.SNAPSHOT:
        filename = "snapshot_reports.toml"
    else:
        assert False, simulation_type

    return os.path.join(
        os.path.dirname(getattr(disco, "__path__")[0]),
        "disco",
        "extensions",
        "pydss_simulation",
        filename,
    )


class PyDssConfigurationBase(DistributionConfiguration):
    """Represents the configuration options for a PyDSS simulation."""

    def __init__(self,
                 #add_pmpp_if_missing, # TODO
                 **kwargs):
        """Constructs PyDssConfiguration."""
        super(PyDssConfigurationBase, self).__init__(**kwargs)

        # Kinda hacky, but this enables PyDssConfiguration.deserialize().
        if "pydss_inputs" in kwargs:
            cfg = kwargs["pydss_inputs"]
            self._pydss_inputs = self.deserialize_pydss_inputs(cfg)
        else:
            self._pydss_inputs = self.get_default_pydss_config()

        self._ensure_pydss_controller_registry()

    @property
    def pydss_inputs(self):
        """Get the PyDSS inputs configuration.

        Returns
        -------
        dict

        """
        return copy.deepcopy(self._pydss_inputs)

    def _get_config(self, config_type):
        config = self._pydss_inputs.get(config_type)
        if config is None:
            raise InvalidParameter(f"invalid config_type={config_type}")

        return config

    @staticmethod
    def _ensure_pydss_controller_registry():
        """Ensure DISCO's controllers registered in PyDSS."""
        registry = Registry()
        for item in DEFAULT_CONTROLLER_CONFIGS:
            registered = registry.is_controller_registered(
                controller_type=item["controller_type"],
                name=item["name"]
            )
            if registered:
                continue
            registry.register_controller(
                controller_type=item["controller_type"],
                controller={
                    "name": item["name"],
                    "filename": os.path.abspath(item["filename"])
                }
            )

    def _serialize(self, data):
        data["pydss_inputs"] = self.serialize_pydss_inputs(self._pydss_inputs)

    def get_pydss_config(self, config_type):
        """Return the configuration for the given type.

        Parameters
        ----------
        config_type : ConfigType

        Returns
        -------
        dict

        """
        return copy.deepcopy(self._get_config(config_type))

    def set_pydss_config(self, config_type, config):
        """Set the configuration for the given type.

        Parameters
        ----------
        config_type : ConfigType

        Returns
        -------
        dict

        """
        # This will validate config_type.
        self._get_config(config_type)

        self._pydss_inputs[config_type] = copy.deepcopy(config)
        logger.debug("Set new PyDSS config for %s: %s", config_type, config)

    def add_pydss_controller_config(self, controller_type, name):
        """Add a PyDSS controller to the configuration.

        Parameters
        ----------
        controller_type : str
            The PyDSS controller type
        name : str
            The PyDSS controller name
        """
        controllers = self._pydss_inputs[ConfigType.CONTROLLER_CONFIG]
        for controller in controllers:
            if controller["controller_type"] != controller_type:
                continue
            if controller["name"] == name:
                raise InvalidParameter(f"controller {name} is already stored")

        controller = {
            "controller_type": controller_type,
            "name": name
        }
        self._pydss_inputs[ConfigType.CONTROLLER_CONFIG].append(controller)
        logger.info("Added controller %s", name)

    def remove_pydss_controller_config(self, controller_type, name):
        """Remove a PyDSS controller from the configuration.

        Parameters
        ----------
        controller_type: str
            The PyDSS controller type
        name : str
            The PyDSS controller name

        Raises
        ------
        InvalidParameter
            Raised if name is not stored.

        """
        controllers = self._pydss_inputs[ConfigType.CONTROLLER_CONFIG]
        controller_index = None
        for i, controller in enumerate(controllers):
            if controller["controller_type"] != controller_type:
                continue
            if controller["name"] == name:
                controller_index = i

        if not controller_index:
            raise InvalidParameter(f"{name} is not stored")

        self._pydss_inputs[ConfigType.CONTROLLER_CONFIG].pop(controller_index)
        logger.info("Removed controller %s", name)

    def add_pydss_simulation_config(self, name, simulation):
        """Add a PyDSS simulation config to the configuration.

        Call PyDssConfigurationBase.get_default_pydss_simulation_config() for a
        base simulation.

        Parameters
        ----------
        name : str
        simulation : dict

        """
        self._pydss_inputs[ConfigType.SIMULATION_CONFIG][name] = simulation
        logger.info("Added simulation %s", name)

    def remove_pydss_simulation_config(self, name):
        """Remove a PyDSS simulation config from the configuration.

        Parameters
        ----------
        name : str

        Raises
        ------
        InvalidParameter
            Raised if name is not stored.

        """
        if name not in self._pydss_inputs[ConfigType.SIMULATION_CONFIG]:
            raise InvalidParameter(f"{name} is not stored")

        self._pydss_inputs[ConfigType.SIMULATION_CONFIG].pop(name)
        logger.info("Removed simulation %s", name)

    def get_pydss_simulation_config(self, name):
        """Return the simulation config.

        Parameters
        ----------
        name : str

        Returns
        -------
        dict

        Raises
        ------
        InvalidParameter
            Raised if name is not stored.

        """
        if name not in self._pydss_inputs[ConfigType.SIMULATION_CONFIG]:
            raise InvalidParameter(f"{name} is not stored")

        return self._pydss_inputs[ConfigType.SIMULATION_CONFIG][name]

    @staticmethod
    def serialize_pydss_inputs(inputs):
        """Serializes PyDSS input configuration, replacing enums with values.

        Parameters
        ----------
        inputs : dict

        Returns
        -------
        dict

        """
        return {k.value: v for k, v in inputs.items()}

    @staticmethod
    def deserialize_pydss_inputs(cfg):
        """Deserializes PyDSS input configuration, replacing values with enums.

        Parameters
        ----------
        inputs : dict

        Returns
        -------
        dict

        """
        return {get_enum_from_value(ConfigType, k): v for k, v in cfg.items()}

    @staticmethod
    def get_default_pydss_config():
        """Return the default PyDSS configuration.

        Returns
        -------
        dict

        """
        config = {k: copy.deepcopy(DEFAULT_PYDSS_CONFIG[k]) for k in ConfigType}
        return config

    @staticmethod
    def get_default_pydss_simulation_config():
        """Return the default PyDSS simulation configuration.

        Returns
        -------
        dict

        """
        return copy.deepcopy(DEFAULT_PYDSS_SIMULATION_CONFIG)

    @staticmethod
    def make_default_pydss_scenario(scenario_name, exports=None, post_process_infos=None):
        """Return a default scenario dictionary for a given name.

        Parameters
        ----------
        scenario_name : str

        Returns
        -------
        dict

        """
        return {
            "name": scenario_name,
            "exports": {} if exports is None else exports,
            "post_process_infos": [] if post_process_infos is None else post_process_infos,
        }
