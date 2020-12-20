
from jade.exceptions import InvalidParameter
from disco.enums import AnalysisType
from disco.models.snapshot_impact_analysis_model import SnapshotImpactAnalysisModel
from disco.models.time_series_impact_analysis_model import TimeSeriesImpactAnalysisModel
from disco.models.upgrade_cost_analysis_model import UpgradeCostAnalysisModel

_MAPPING = {
    AnalysisType.SnapshotImpactAnalysis: SnapshotImpactAnalysisModel,
    AnalysisType.TimeSeriesImpactAnalysis: TimeSeriesImpactAnalysisModel,
    AnalysisType.UpgradeCostAnalysis: UpgradeCostAnalysisModel
}

_MAPPING_BY_NAME = {
    "SnapshotImpactAnalysisModel": SnapshotImpactAnalysisModel,
    "TimeSeriesImpactAnalysisModel": TimeSeriesImpactAnalysisModel,
    "UpgradeCostAnalysisModel": UpgradeCostAnalysisModel
}


def get_model_class_by_analysis_type(analysis_type):
    """Return the model class for an analysis_type.

    Parameters
    ----------
    analysis_type : AnalysisType

    Returns
    -------
    class
        Will be a subtype of DiscoBaseModel

    """
    if analysis_type not in _MAPPING:
        raise InvalidParameter(f"no mapping for {analysis_type}")
    return _MAPPING[analysis_type]


def get_model_class_by_name(name):
    """Return the model class for a name.

    Parameters
    ----------
    name : str

    Returns
    -------
    class
        Will be a subtype of DiscoBaseModel

    """
    if name not in _MAPPING_BY_NAME:
        raise InvalidParameter(f"no mapping for {name}")
    return _MAPPING_BY_NAME[name]


def make_model(data):
    """Make a model from serialized data.

    Parameters
    ----------
    data : dict

    Returns
    -------
    class
        Will be a subtype of DiscoBaseModel

    """
    model_class = get_model_class_by_name(data["model_type"])
    return model_class.validate(data)


def list_model_classes():
    """Return all simulation input models.

    Returns
    -------
    list
        list of model classes

    """
    # TODO: do this dynamically, accounting for abstract types.
    return [
        SnapshotImpactAnalysisModel,
        TimeSeriesImpactAnalysisModel,
        UpgradeCostAnalysisModel,
    ]
