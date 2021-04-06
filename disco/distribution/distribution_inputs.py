"""Defines DistributionInputs."""

import enum
import logging
import os

from jade.exceptions import InvalidParameter
from jade.jobs.job_inputs_interface import JobInputsInterface
from jade.utils.utils import load_data
from disco.distribution.deployment_parameters import DeploymentParameters


logger = logging.getLogger(__name__)


class DistributionInputs(JobInputsInterface):
    """Helper class to access Distribution input files."""

    _CONFIG_FILE = "configurations.json"

    def __init__(self, base_directory):
        """Constructs DistributionInputs.

        Parameters
        ----------
        base_directory : str

        """
        self._base = base_directory
        self._parameters = {}

        if not os.path.exists(self._base):
            raise InvalidParameter("inputs directory does not exist: {}"
                                   .format(self._base))

        self._parse_config_files()

    def __repr__(self):
        text = [str(x) for x in self.list_keys()]
        return "\n".join(text)

    def _parse_config_files(self):
        filename = os.path.join(self._base, self._CONFIG_FILE)
        data = load_data(filename)
        for job_data in data:
            job = DeploymentParameters(**job_data)
            assert job.name not in self._parameters
            self._parameters[job.name] = job

    @property
    def base_directory(self):
        return self._base

    def get_job(self, key):
        """Get the job object from a key.

        Parameters
        ----------
        key : namedtuple

        Returns
        -------
        DeploymentParameters

        Raises
        ------
        InvalidParameter
            thrown if the key is not stored

        """
        job = self._parameters.get(key)
        if job is None:
            raise InvalidParameter(f"invalid key {key}")

        return job

    def get_available_parameters(self):
        return self._parameters

    def _get_unique_parameters(self, param):
        assert param != "deployment"
        params = set()
        for item in self._parameters.values():
            val = getattr(item, param)
            if isinstance(val, enum.Enum):
                val = val.value
            params.add(val)

        params = list(params)
        params.sort()
        return params

    def iter_jobs(self):
        """Return an iterator of jobs."""
        return self._parameters.values()

    def list_jobs(self):
        """List the available jobs.

        Returns
        -------
        list
            list of DeploymentParameters

        """
        return list(self._parameters.values())

    def list_feeders(self):
        """List available feeders.

        Returns
        -------
        list
            list of strings

        """
        return self._get_unique_parameters("feeder")

    def list_parameters(self, feeders=None, dc_ac_ratios=None,
                        kva_to_kw_ratings=None, deployment_names=None):
        """List the parameters after applying filters. The filter values can be
        single objects or lists.

        Returns
        -------
        list
            list of DeploymentParameters

        """
        if feeders is not None and not isinstance(feeders, list):
            feeders = [feeders]
        if dc_ac_ratios is not None and not isinstance(dc_ac_ratios, list):
            dc_ac_ratios = [dc_ac_ratios]
        if kva_to_kw_ratings is not None and not isinstance(kva_to_kw_ratings,
                                                            list):
            kva_to_kw_ratings = [kva_to_kw_ratings]
        if deployment_names is not None and not isinstance(deployment_names,
                                                           list):
            deployment_names = [deployment_names]

        parameters = []
        for param in self._parameters.values():
            if feeders is not None and param.feeder not in feeders:
                continue
            if dc_ac_ratios is not None and \
                    param.deployment.dc_ac_ratio not in dc_ac_ratios:
                continue
            if kva_to_kw_ratings is not None and \
                    param.deployment.kva_to_kw_rating not in kva_to_kw_ratings:
                continue
            if deployment_names is not None and \
                    param.deployment.name not in deployment_names:
                continue
            parameters.append(param)

        return parameters

    def list_keys(self):
        """List the available job keys.

        Returns
        -------
        list
            list of namedtuple

        """
        keys = list(self._parameters.keys())
        keys.sort()
        return keys
