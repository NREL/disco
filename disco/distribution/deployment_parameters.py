"""Defines deployment parameters for auto-generated scenarios."""

from collections import namedtuple
import logging

from jade.jobs.job_parameters_interface import JobParametersInterface
from disco.models.factory import make_model
from disco.models.base import ImpactAnalysisBaseModel


logger = logging.getLogger(__name__)


class DeploymentParameters(JobParametersInterface):
    """Represents deployment parameters for auto-generated scenarios."""

    parameters_type = namedtuple("DeploymentKeys", "name")
    DEFAULT_STEP_RESOLUTION = 900

    def __init__(self, data):
        self._model = make_model(data)

    def __repr__(self):
        return self.name

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

    @property
    def name(self):
        return self._model.name

    @property
    def feeder(self):
        """Return the job's feeder."""
        return self._model.deployment.feeder

    def serialize(self):
        """Serialize deployment into a dictionary."""
        return self._model.dict()

    @classmethod
    def deserialize(cls, data):
        return cls(data)

    def add_blocking_job(self, name):
        self._model.blocked_by.add(name)

    def add_blocking_jobs(self, names):
        self._model.blocked_by.update(names)

    def get_blocking_jobs(self):
        return self._model.blocked_by

    def remove_blocking_job(self, name):
        self._model.blocked_by.remove(name)
