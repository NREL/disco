from .automated_thermal_upgrades import determine_thermal_upgrades
from .automated_voltage_upgrades import determine_voltage_upgrades
from .upgrade_parameters import PYDSS_PARAMS
from .cost_computation import compute_all_costs
from .loggers import setup_logging
import logging
import os


determine_thermal_upgrades(**PYDSS_PARAMS)
determine_voltage_upgrades(**PYDSS_PARAMS)
compute_all_costs()
