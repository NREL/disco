MAX_ACCEPTABLE_TRANSFORMER_OVERLOAD_PU = 3.5  # in per unit
MAX_ACCEPTABLE_LINE_OVERLOAD_PU = 3.5  # in per unit

# fixed voltage upgrade parameters
correct_PT_ratio = True

PLOT_VIOLATIONS_COUNTER = 0

PARALLEL_XFMRS_LIMIT = 4
PARALLEL_LINES_LIMIT = 4
THERMAL_UPGRADE_ITERATION_THRESHOLD = 5

# voltage upgrade action flags - to determine if a particular action is to be done or not
CAPACITOR_ACTION_FLAG = True
EXISTING_REGULATOR_SWEEP_ACTION = True

# default capacitor bank settings
DEFAULT_CAPACITOR_SETTINGS = {
    "capONdelay": 0,
    "capOFFdelay": 0,
    "capdeadtime": 0,
    "PTphase": "AVG",
    "cap_control": "voltage",
    "terminal": 1,
    "capON": None,  # Customize during voltage upgrades
    "capOFF": None  # Customize during voltage upgrades
}

# default Substation LTC settings
DEFAULT_SUBLTC_SETTINGS = {
    "winding": 2,
    "delay": 45,  # in seconds
    "band": 2,  # deadband in volts
    "properties_to_be_defined": [
        "winding",
        "ptratio",
        "band",
        "vreg",
        "delay",
    ],
    "vreg": None # Customize during voltage upgrades
}

# default regulator settings
DEFAULT_REGCONTROL_SETTINGS = {}
DEFAULT_REGCONTROL_SETTINGS["conn"] = "wye"
DEFAULT_REGCONTROL_SETTINGS["delay"] = 15  # in seconds
DEFAULT_REGCONTROL_SETTINGS["band"] = 2  # deadband in volts
DEFAULT_REGCONTROL_SETTINGS["properties_to_be_defined"] = [
    "winding",
    "ptratio",
    "band",
    "vreg",
    "delay",
]

# max_regs = voltage_config["max_regulators"]

create_topology_plots = False