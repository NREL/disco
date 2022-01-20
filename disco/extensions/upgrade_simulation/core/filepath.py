from .fixed_upgrade_parameters import *

os.makedirs(output_folder, exist_ok=True)

thermal_upgrades_folder = os.path.join(output_folder, "ThermalUpgrades")
voltage_upgrades_folder = os.path.join(output_folder, "VoltageUpgrades")
metadata_folder = os.path.join(output_folder, "Metadata")
os.makedirs(thermal_upgrades_folder, exist_ok=True)
os.makedirs(voltage_upgrades_folder, exist_ok=True)
os.makedirs(metadata_folder, exist_ok=True)

# upgrades output filepaths
thermal_upgrades_dss_filepath = os.path.join(
    thermal_upgrades_folder, thermal_upgrades_dss_filename
)
voltage_upgrades_dss_filepath = os.path.join(
    voltage_upgrades_folder, voltage_upgrades_dss_filename
)
output_csv_line_upgrades_filepath = os.path.join(
    thermal_upgrades_folder, output_csv_line_upgrades_filename
)
output_csv_xfmr_upgrades_filepath = os.path.join(
    thermal_upgrades_folder, output_csv_xfmr_upgrades_filename
)
output_csv_voltage_upgrades_filepath = os.path.join(
    voltage_upgrades_folder, output_csv_voltage_upgrades_filename
)
thermal_summary_file = os.path.join(thermal_upgrades_folder, "Thermal_Summary.csv")
voltage_summary_file = os.path.join(voltage_upgrades_folder, "Voltage_Summary.csv")
line_upgrade_options_file = os.path.join(
    thermal_upgrades_folder, "line_upgrade_options.csv"
)
xfmr_upgrade_options_file = os.path.join(
    thermal_upgrades_folder, "xfmr_upgrade_options.csv"
)

# defining log filepaths
thermal_upgrades_log_folder = thermal_upgrades_folder
voltage_upgrades_log_folder = voltage_upgrades_folder
thermal_upgrades_log_filepath = os.path.join(
    thermal_upgrades_log_folder, "ThermalUpgrades.log"
)
voltage_upgrades_log_filepath = os.path.join(
    voltage_upgrades_log_folder, "VoltageUpgrades.log"
)
os.makedirs(thermal_upgrades_log_folder, exist_ok=True)
os.makedirs(voltage_upgrades_log_folder, exist_ok=True)
