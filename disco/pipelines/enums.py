import enum


class AnalysisType(enum.Enum):
    """DISCO analysis types"""
    IMAPCT_ANALYSIS = "impact-analysis"
    HOSTING_CAPACITY = "hosting-capacity"
    COST_BENEFIT = "cost-benefit"


class TemplateSection(enum.Enum):
    PRESCREEN = "prescreen"
    SIMULATION = "simulation"
    POSTPROCESS = "postprocess"
    MODEL = "model"
    REPORTS = "reports"


class TemplateParams(enum.Enum):
    TRANSFORM_PARAMS = "transform-params"
    CONFIG_PARAMS = "config-params"
    PRESCREEN_PARAMS = "prescreen-params"
    SUMITTER_PARAMS = "submitter-params"
