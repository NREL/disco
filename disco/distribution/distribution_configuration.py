"""Base functionality for distribution configurations."""

import logging

from jade.jobs.job_configuration import JobConfiguration
from jade.jobs.job_container_by_key import JobContainerByKey
from jade.utils.utils import load_data


logger = logging.getLogger(__name__)


class DistributionConfiguration(JobConfiguration):
    """Represents the configuration options for a distribution simulation."""

    def __init__(self,
                 inputs,
                 job_parameters_class,
                 extension_name,
                 **kwargs):
        """Constructs DistributionConfiguration.

        Parameters
        ----------
        inputs : str | JobInputsInterface
            path to inputs directory or JobInputsInterface object

        """
        super(DistributionConfiguration, self).__init__(inputs,
                                                        JobContainerByKey(),
                                                        job_parameters_class,
                                                        extension_name,
                                                        **kwargs)

    @classmethod
    def deserialize(cls, filename_or_data, do_not_deserialize_jobs=False):
        if isinstance(filename_or_data, str):
            data = load_data(filename_or_data)
        else:
            data = filename_or_data
        inputs = data.pop("inputs_directory")
        data["do_not_deserialize_jobs"] = do_not_deserialize_jobs
        return cls(inputs, **data)

    @property
    def base_directory(self):
        """Return the base directory for the inputs."""
        if isinstance(self.inputs, str):
            return self.inputs
        return self.inputs.base_directory

    def create_job_key(self, *args):
        """Create a job key from parameters."""
        return self._job_parameters_class.create_job_key(*args)
