import os
import logging
from .upgrade_parameters import output_folder

log_console_level = logging.DEBUG
log_file_level = logging.DEBUG

cost_database_filepath = r"C:\Users\SABRAHAM\Desktop\NREL\current_projects\SETO_distcost\AutomatedUpgrades\Generic_DISCO_cost_database_v2.xlsx"

cost_output_folder = os.path.join(output_folder, "UpgradeCosts")
os.makedirs(cost_output_folder, exist_ok=True)

# log filepaths
voltage_upgrades_log_folder = os.path.join(cost_output_folder, "Logs")
cost_upgrades_log_filepath = os.path.join(
    voltage_upgrades_log_folder, "UpgradeCosts.log"
)
os.makedirs(voltage_upgrades_log_folder, exist_ok=True)

# output filepaths
thermal_cost_output_filepath = os.path.join(
    cost_output_folder, "thermal_upgrade_costs.csv"
)
voltage_cost_output_filepath = os.path.join(
    cost_output_folder, "voltage_upgrade_costs.csv"
)
total_cost_output_filepath = os.path.join(cost_output_folder, "total_upgrade_costs.csv")
