"""Enums for the disco package."""

import enum
import re

import toml


class Status(enum.Enum):
    """Return status."""
    GOOD = 0
    ERROR = 1


# Directories use these values.
DCAC_MAPPING = {
    -1: "None",
    0.8: "DCAC0.8",
    1.15: "DCAC1.15",
}


class Scale(enum.Enum):
    """Possible values for scale"""
    SMALL = "small"
    LARGE = "large"


# Directories use these values.
SCALE_MAPPING = {
    Scale.SMALL: "SmallScale",
    Scale.LARGE: "LargeScale",
}


def get_scale_from_value(value):
    """Gets the enum for the given value.

    Returns
    -------
    Scale

    """
    for key, val in SCALE_MAPPING.items():
        if val == value:
            return key
    raise Exception("Unknown value: {}".format(value))


class Placement(enum.Enum):
    """Possible values for placement"""
    RANDOM = "random"
    CLOSE = "close"
    FAR = "far"


# TODO: we cannot support having placement values with upper and lower case.
# need to change all directories where this is the case.


def get_placement_from_value(value):
    """Gets the enum for the given value.

    Note: this performs a case-insensitive search because some input
    directories are inconsistent.

    Returns
    -------
    Placement

    """
    for placement in Placement:
        if placement.value == value.lower():
            return placement
    raise Exception("Unknown value: {}".format(value))


class Mode(enum.Enum):
    """Possible values for computational sequencing mode"""
    PARALLEL = "parallel"
    SEQUENTIAL = "sequential"


class SimulationHierarchy(enum.Enum):
    SUBSTATION = "substation"
    FEEDER = "feeder"


class SimulationOutputs(enum.Enum):
    """Defines the possible simulation output types."""
    LINE_LOADINGS = "line_loadings"
    LINE_LOSSES = "line_losses"
    NODAL_VOLTAGES = "nodal_voltages"
    PV_OUTPUTS = "pv_outputs"
    TOTAL_CIRCUIT_POWER = "total_circuit_power"
    TOTAL_LOSSES = "total_losses"
    TRANSFORMER_LOADINGS = "transformer_loadings"


class SimulationType(enum.Enum):
    """Defines the possible simulation types."""
    SNAPSHOT = "snapshot"
    QSTS = "QSTS"
    TIME_SERIES = "time-series"  # This should be duplicate with QSTS.
    UPGRADE = "upgrade"


class AnalysisModelType(enum.Enum):
    """Represents the type of model used for each analysis type."""
    # ImpactAnalysis is improperly used here. Leaving for backwards compatibility.
    # The same data model is used for time-series impact analysis and hosting capacity analysis.
    SnapshotImpactAnalysis = "SnapshotImpactAnalysis"
    TimeSeriesImpactAnalysis = "TimeSeriesImpactAnalysis"
    UpgradeCostAnalysis = "UpgradeCostAnalysis"


class AnalysisType(enum.Enum):
    """DISCO user analysis types"""
    IMPACT_ANALYSIS = "impact-analysis"
    HOSTING_CAPACITY = "hosting-capacity"
    COST_BENEFIT = "cost-benefit"
    UPGRADE_ANALYSIS = "upgrade-analysis"
    NONE = "none"


class LoadMultiplierType(enum.Enum):
    """Multiplier types"""
    ORIGINAL = "original"
    UNIFORM = "uniform"


ANALYSIS_MODEL_TYPES = [t.value for t in AnalysisModelType]


PUBLIC_ENUMS = {
    "AnalysisModelType": AnalysisModelType,
    "Mode": Mode,
    "Placement": Placement,
    "Scale": Scale,
    "SimulationOutputs": SimulationOutputs,
    "SimulationType": SimulationType,
}


_REGEX_ENUM = re.compile(r"^(\w+)\.(\w+)$")


def get_enum_from_str(string):
    """Converts a enum that's been written as a string back to an enum.

    Parameters
    ----------
    string : str
        string to convert

    Returns
    -------
    tuple
        converted, converted enum or original

    """
    converted = False
    match = _REGEX_ENUM.search(string)
    if match and match.group(1) in PUBLIC_ENUMS:
        obj = getattr(PUBLIC_ENUMS[match.group(1)], match.group(2))
        converted = True
    else:
        obj = string

    return converted, obj


def get_enum_from_value(cls, value):
    """Gets the enum for the given value."""
    for enum_ in cls:
        if enum_.value == value:
            return enum_
    raise Exception("Unknown value: {} {}".format(cls, value))


class EnumEncoder(toml.TomlEncoder):
    """Custom encoder for enums."""
    def __init__(self, _dict=dict, preserve=False):
        super(EnumEncoder, self).__init__(_dict, preserve)
        self.dump_funcs[enum.Enum] = EnumEncoder.dump_enum

    @staticmethod
    def dump_enum(val):
        """Return the enum value converted to string."""
        return str(val.value)
