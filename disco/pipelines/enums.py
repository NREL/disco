import enum

class SimulationType(enum.Enum):
    """DISCO simulation types."""
    SNAPSHOT = "snapshot"
    TIME_SERIES = "time-series"
    UPGRADE = "upgrade"


class AnalysisType(enum.Enum):
    """DISCO analysis types"""
    IMAPCT_ANALYSIS = "impact-analysis"
    HOSTING_CAPACITY = "hosting-capacity"


class TemplateSection(enum.Enum):
    PRESCREEN = "prescreen"
    SIMULATION = "simulation"
    POSTPROCESS = "postprocess"
    MODEL = "model"


class TemplateParams(enum.Enum):
    TRANSFORM_PARAMS = "transform-params"
    CONFIG_PARAMS = "config-params"
    PRESCREEN_PARAMS = "prescreen-params"
    SUMITTER_PARAMS = "submitter-params"
