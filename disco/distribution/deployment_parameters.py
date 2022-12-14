"""Defines deployment parameters for auto-generated scenarios."""

from collections import namedtuple
import logging

from jade.jobs.job_parameters_interface import JobParametersInterface
from jade.common import DEFAULT_SUBMISSION_GROUP
from disco.models.factory import make_model
from disco.models.base import ImpactAnalysisBaseModel
from disco.models.snapshot_impact_analysis_model import SnapshotImpactAnalysisModel
from disco.models.time_series_analysis_model import TimeSeriesAnalysisModel
from disco.models.upgrade_cost_analysis_model import UpgradeCostAnalysisModel

logger = logging.getLogger(__name__)


class DeploymentParameters(JobParametersInterface):
    """Represents deployment parameters for auto-generated scenarios."""

    parameters_type = namedtuple("DeploymentKeys", "name")
    DEFAULT_STEP_RESOLUTION = 900
    _EXTENSIONS = {
        SnapshotImpactAnalysisModel: "pydss_simulation",
        TimeSeriesAnalysisModel: "pydss_simulation",
        UpgradeCostAnalysisModel: "upgrade_simulation"
    }

    def __init__(self, estimated_run_minutes=None, **kwargs):
        self._estimated_run_minutes = estimated_run_minutes
        self._model = make_model(kwargs)
        self._submission_group = DEFAULT_SUBMISSION_GROUP

    def __repr__(self):
        return self.name

    @property
    def estimated_run_minutes(self):
        return self._estimated_run_minutes

    @estimated_run_minutes.setter
    def estimated_run_minutes(self, val):
        self._estimated_run_minutes = val

    @staticmethod
    def list_extensions():
        # this may need to be extended to all JobParametersInterface classes
        return list(DeploymentParameters._EXTENSIONS)

    @property
    def extension(self):
        return self._EXTENSIONS[type(self._model)]

    @property
    def model(self):
        """Return the input data model for the job."""
        return self._model

    @property
    def base_case(self):
        """Return the base case or None."""
        if isinstance(self._model, ImpactAnalysisBaseModel):
            return self._model.base_case
        return None

    def has_pydss_controllers(self):
        """Return True if pydss controllers are present."""
        if self._model.deployment.pydss_controllers is None:
            return False
        if isinstance(self._model.deployment.pydss_controllers, list):
            return bool(self._model.deployment.pydss_controllers)
        return True

    @property
    def name(self):
        return self._model.name

    @property
    def feeder(self):
        """Return the job's feeder."""
        return self._model.deployment.feeder

    def serialize(self):
        """Serialize deployment into a dictionary."""
        data = self._model.dict()
        data["extension"] = self.extension
        data["estimated_run_minutes"] = self.estimated_run_minutes
        return data

    @classmethod
    def deserialize(cls, data):
        return cls(**data)

    def add_blocking_job(self, name):
        self._model.blocked_by.add(name)

    def add_blocking_jobs(self, names):
        self._model.blocked_by.update(names)

    def get_blocking_jobs(self):
        return self._model.blocked_by

    def remove_blocking_job(self, name):
        self._model.blocked_by.remove(name)

    def set_blocking_jobs(self, blocking_jobs):
        self._model.blocked_by = blocking_jobs

    @property
    def cancel_on_blocking_job_failure(self):
        return True

    @property
    def submission_group(self):
        return self._submission_group

    @submission_group.setter
    def submission_group(self, group):
        self._submission_group = group
