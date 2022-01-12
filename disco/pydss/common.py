"""Common definitions for PyDSS-based simulations."""

import enum
import logging


from PyDSS.reports.pv_reports import PF1_SCENARIO, CONTROL_MODE_SCENARIO

logger = logging.getLogger(__name__)


SCENARIO_NAME_DELIMITER = "__"
SIMULATION_POSTPROCESS = "post_process"
TIME_SERIES_SCENARIOS = [CONTROL_MODE_SCENARIO, PF1_SCENARIO]
SNAPSHOT_SCENARIO = "scenario"


class ConfigType(enum.Enum):
    """Possible values for PyDSS config options"""
    SIMULATION_CONFIG = "Simulation"
    CONTROLLER_CONFIG = "PvControllers"
    SCENARIOS = "Scenarios"
