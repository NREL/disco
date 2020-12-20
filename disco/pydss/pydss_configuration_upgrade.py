import logging
import os
from abc import abstractmethod
from collections import UserDict

from jade.utils.utils import load_data, dump_data
from disco.pydss.common import UpgradeType

import disco

logger = logging.getLogger(__name__)

ROOT_DIR = os.path.dirname(getattr(disco, "__path__")[0])

# Thermal Config
DEFAULT_THERMAL_UPGRADE_CONFIG_FILE = os.path.join(
    ROOT_DIR,
    "disco",
    "pydss",
    "config",
    "thermal_upgrade.toml"
)
DEFAULT_THERMAL_UPGRADE_CONFIG = load_data(DEFAULT_THERMAL_UPGRADE_CONFIG_FILE)

# Voltage Config
DEFAULT_VOLTAGE_UPGRADE_CONFIG_FILE = os.path.join(
    ROOT_DIR,
    "disco",
    "pydss",
    "config",
    "voltage_upgrade.toml"
)
DEFAULT_VOLTAGE_UPGRADE_CONFIG = load_data(DEFAULT_VOLTAGE_UPGRADE_CONFIG_FILE)


class UpgradeConfigurationBase(UserDict):
    """
    Represents the configuration options for upgrade simulation in PyDSS.
    """
    def __init__(self, user_data=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if user_data:
            self.update(user_data)
        else:
            self.update(self.defaults)

    def __repr__(self):
        """Formatted configuration strings."""
        maxlen = max([len(k) for k in self.keys()])
        template = "{:<{width}}   {}\n".format("Parameter", "Value", width=maxlen)
        for k, v in self.items():
            template += "{:<{width}} : {}\n".format(k, str(v), width=maxlen)
        template = template.strip()
        return template

    @property
    @abstractmethod
    def defaults(self):
        """The default configuration in dict."""

    @property
    def currents(self):
        """The updated configuration in dict."""
        return self.data

    def dump(self, config_file):
        """Dump current configuration to file."""
        dump_data(self.currents, config_file)


class ThermalUpgradeConfiguration(UpgradeConfigurationBase):
    """
    Represents the configuration options for thermal upgrade simulation in PyDSS.
    """
    DEFAULT_CONFIG = DEFAULT_THERMAL_UPGRADE_CONFIG

    @property
    def defaults(self):
        """The default thermal upgrade configuration in dict"""
        return self.DEFAULT_CONFIG

    def update(self, data):
        """Update configuration with user data.

        Parameters
        ----------
        data : dict
            A dict of paramter-value pairs.
        """
        self.data.update(data)


class VoltageUpgradeConfiguration(UpgradeConfigurationBase):
    """
    Represents the configuration options for voltage upgrade simulation in PyDSS.
    """
    DEFAULT_CONFIG = DEFAULT_VOLTAGE_UPGRADE_CONFIG

    @property
    def defaults(self):
        """The default voltage upgrade configuration in dict."""
        return self.DEFAULT_CONFIG

    def update(self, data):
        """Update configuration with user data.

        Parameters
        ----------
        data : dict
            A dict of paramter-value pairs.
        """
        # Ensure thermal scenario name
        thermal_scenario_name = data.get("thermal_scenario_name", None)
        desired_thermal_scenario_name = UpgradeType.ThermalUpgrade.value

        if thermal_scenario_name and (thermal_scenario_name != desired_thermal_scenario_name):
            logger.warning("Parameter 'Thernal scenario name' could not be overridden!!!")
            data["thermal_scenario_name"] = desired_thermal_scenario_name

        self.data.update(data)
