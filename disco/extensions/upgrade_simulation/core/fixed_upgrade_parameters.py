from .upgrade_parameters import *

thermal_upgrades_dss_filename = "thermal_upgrades.dss"
voltage_upgrades_dss_filename = "voltage_upgrades.dss"
output_csv_line_upgrades_filename = "Line upgrades.csv"
output_csv_xfmr_upgrades_filename = "Transformer upgrades.csv"
output_csv_voltage_upgrades_filename = "Voltage upgrades.csv"

# fixed thermal upgrade parameters
thermal_upgrade_iteration_threshold = (
    5  # max limit to the number of iterations for the thermal upgrades algorithm
)
max_acceptable_transformer_overload_pu = 3.5  # in per unit
max_acceptable_line_overload_pu = 3.5  # in per unit
PARALLEL_LINES_LIMIT = 4
PARALLEL_XFMRS_LIMIT = 4
ignore_switch = True  # should switches be considered while determining line loading

# fixed voltage upgrade parameters
correct_PT_ratio = True

# default capacitor bank settings
default_capacitor_settings = {}
default_capacitor_settings["capON"] = round(
    (
        voltage_config["nominal_voltage"]
        - voltage_config["capacitor_sweep_voltage_gap"] / 2
    ),
    1,
)
default_capacitor_settings["capOFF"] = round(
    (
        voltage_config["nominal_voltage"]
        + voltage_config["capacitor_sweep_voltage_gap"] / 2
    ),
    1,
)
default_capacitor_settings["capONdelay"] = 0
default_capacitor_settings["capOFFdelay"] = 0
default_capacitor_settings["capdeadtime"] = 0
default_capacitor_settings["PTphase"] = "AVG"
default_capacitor_settings["cap_control"] = "voltage"
default_capacitor_settings["terminal"] = 1
plot_violations_counter = 0

# default regulator settings
default_regcontrol_settings = {}
default_regcontrol_settings["conn"] = "wye"
default_regcontrol_settings["delay"] = 15  # in seconds
default_regcontrol_settings["band"] = 2  # deadband in volts
default_regcontrol_settings["properties_to_be_defined"] = [
    "winding",
    "ptratio",
    "band",
    "vreg",
    "delay",
]

max_regs = voltage_config["max_regulators"]

# default Substation LTC settings
default_subltc_settings = {}
default_subltc_settings["vreg"] = 1.03 * voltage_config["nominal_voltage"]
default_subltc_settings["winding"] = 2
default_subltc_settings["delay"] = 45  # in seconds
default_subltc_settings["band"] = 2  # deadband in volts
default_subltc_settings["properties_to_be_defined"] = [
    "winding",
    "ptratio",
    "band",
    "vreg",
    "delay",
]

# voltage upgrade action flags - to determine if a particular action is to be done or not
capacitor_action_flag = True
existing_regulator_sweep_action = True
