"""Base functionality for distribution configurations."""

import logging

from jade.jobs.job_configuration import JobConfiguration
from jade.utils.utils import load_data


logger = logging.getLogger(__name__)


class DistributionConfiguration(JobConfiguration):
    """Represents the configuration options for a distribution simulation."""

    @classmethod
    def deserialize(cls, filename_or_data, do_not_deserialize_jobs=False):
        if isinstance(filename_or_data, str):
            data = load_data(filename_or_data)
        else:
            data = filename_or_data
        data["do_not_deserialize_jobs"] = do_not_deserialize_jobs
        return cls(**data)
