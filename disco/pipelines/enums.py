import enum


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
