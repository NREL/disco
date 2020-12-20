"""Common definitions for PyDSS-based simulations."""

import enum
import logging


logger = logging.getLogger(__name__)


SIMULATION_POSTPROCESS = "post_process"


class ConfigType(enum.Enum):
    """Possible values for PyDSS config options"""
    SIMULATION_CONFIG = "Simulation"
    CONTROLLER_CONFIG = "PvControllers"
    SCENARIOS = "Scenarios"


class UpgradeType(enum.Enum):
    """Upgrade types in PyDSS"""
    ThermalUpgrade = "ThermalUpgrade"
    VoltageUpgrade = "VoltageUpgrade"


UPGRADE_SCRIPT_MAPPING = {
    UpgradeType.ThermalUpgrade: "AutomatedThermalUpgrade",
    UpgradeType.VoltageUpgrade: "AutomatedVoltageUpgrade"
}
