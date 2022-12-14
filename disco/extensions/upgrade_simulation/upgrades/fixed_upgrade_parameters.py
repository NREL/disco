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
