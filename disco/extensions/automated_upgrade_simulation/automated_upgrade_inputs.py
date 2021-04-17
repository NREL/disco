"""Impements functionality for automatic upgrade inputs"""
import itertools
import logging
import os
from copy import copy

from jade.utils.utils import load_data

from disco.distribution.distribution_inputs import DistributionInputs
from disco.extensions.automated_upgrade_simulation.automated_upgrade_parameters import \
    AutomatedUpgradeParameters

logger = logging.getLogger(__name__)


class AutomatedUpgradeInputs(DistributionInputs):
    """Implements functionality for automated upgrade inputs"""

    def __init__(
        self,
        base_directory,
        sequential_upgrade=False,
        nearest_redirect=False
    ):
        """
        Initialize automated upgrade inputs.

        Parameters
        ----------
        base_directory : str
            The base directory of configuration.
        sequential_upgrade : bool
            Sequential upgrade enabled, default False.
        nearest_redirect : bool
            Redirect DSS files from nearest lower jobs.
        """
        self.sequential_upgrade = sequential_upgrade
        self.nearest_redirect = nearest_redirect
        super().__init__(base_directory)

    def _parse_config_files(self):
        logger.info("Parsing configured job parameters...")
        filename = os.path.join(self._base, self._CONFIG_FILE)
        data = load_data(filename)
        if self.sequential_upgrade:
            parameters = self._parse_parameters_with_blocking_jobs(data)
        else:
            parameters = self._parse_parameters(data)
        self._parameters = parameters
        logger.info("Parsing done.")

    @staticmethod
    def _create_data_groups(data):
        """Sort data based on feeder, and user specified job_order"""
        if len(list(filter(lambda x: x["job_order"] is None, data))) > 0:
            raise ValueError(
                "Invalid 'job_order' value - None, should be int or float."
            )
        keyfunc = lambda x: (x['deployment']["feeder"], x["job_order"])
        data = sorted(data, key=keyfunc)
        groups = itertools.groupby(data, key=keyfunc)
        return groups

    def _parse_parameters_with_blocking_jobs(self, data):
        """
        Parse jobs with blocked_by attributes,
        The blockers are jobs with lower job_order.
        """
        parameters = {}
        groups = self._create_data_groups(data)

        marker = None
        blocking_jobs = set()
        lower_order_job_names = set()
        for (feeder, job_order), group_data in groups:
            if marker is None:
                marker = feeder

            elif marker != feeder:
                blocking_jobs = set()
                lower_order_job_names = set()

            if self.nearest_redirect:
                lower_order_job_names = set()
            for job_data in group_data:
                job = AutomatedUpgradeParameters(**job_data)
                job.add_blocking_jobs(blocking_jobs)
                assert job.name not in parameters
                parameters[job.name] = job
                lower_order_job_names.add(job.name)

            if marker != feeder:
                marker = None

            blocking_jobs = copy(lower_order_job_names)

        return parameters

    def _parse_parameters(self, data):
        """Parse jobs without blocked_by attribute."""
        parameters = {}
        for job_data in data:
            job = AutomatedUpgradeParameters(**job_data)
            assert job.name not in parameters
            parameters[job.name] = job
        return parameters
