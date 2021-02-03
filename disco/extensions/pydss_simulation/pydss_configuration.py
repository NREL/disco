"""Contains functionality to configure PyDss simulations."""

import logging
from collections import defaultdict

from jade.exceptions import InvalidParameter
from jade.extensions.generic_command.generic_command_parameters import GenericCommandParameters
from jade.utils.utils import load_data

from disco.distribution.deployment_parameters import DeploymentParameters
from disco.enums import SimulationType
from disco.exceptions import PyDssJobException
from disco.pydss.pydss_configuration_base import PyDssConfigurationBase
from disco.pydss.common import ConfigType
from disco.extensions.pydss_simulation.pydss_inputs import PyDssInputs


logger = logging.getLogger(__name__)


class PyDssConfiguration(PyDssConfigurationBase):
    """Represents the configuration options for a PyDSS simulation."""

    def __init__(self, **kwargs):
        """Constructs PyDssConfiguration."""
        super(PyDssConfiguration, self).__init__(**kwargs)
        self._scenario_names = []

    def add_hosting_capacity_job(self, simulation_type, impact_analysis_jobs):
        """Add post-processing jobs for hosting capacity.

        Parameters
        ----------
        simulation_type : SimulationType
        impact_analysis_jobs : list
            Names of impact analysis jobs

        """
        if simulation_type == SimulationType.SNAPSHOT:
            command = "compute-snapshot-hosting-capacity"
        elif simulation_type == SimulationType.QSTS:
            command = "compute-time-series-hosting-capacity"
        else:
            assert False, simulation_type

        cmd = f"disco-internal {command}"
        job = GenericCommandParameters(
            command=cmd,
            job_id=command,
            blocked_by=impact_analysis_jobs,
            append_output_dir=True,
        )
        self.add_job(job)

    def add_impact_analysis_jobs(self, simulation_type):
        """Add post-processing jobs for impact analysis.

        Parameters
        ----------
        simulation_type : SimulationType

        Returns
        -------
        list
            Names of impact analysis jobs

        """
        if simulation_type == SimulationType.SNAPSHOT:
            command = "compute-snapshot-impact-analysis"
        elif simulation_type == SimulationType.QSTS:
            command = "compute-time-series-impact-analysis"
        else:
            assert False, simulation_type

        feeders = defaultdict(list)
        for job in self.iter_jobs():
            feeders[job.model.deployment.feeder].append(job.name)

        job_names = []
        for feeder, blocking_jobs in feeders.items():
            cmd = f"disco-internal {command} {feeder}"
            name = f"{feeder}-{command}"
            job = GenericCommandParameters(
                command=cmd,
                job_id=name,
                blocked_by=blocking_jobs,
                append_output_dir=True,
            )
            self.add_job(job)
            job_names.append(name)

        return job_names

    @classmethod
    def auto_config(cls, inputs, simulation_config=None, scenarios=None, **kwargs):
        """Create a configuration from all available inputs."""
        if isinstance(inputs, str):
            inputs = PyDssInputs(inputs)
        config = cls(**kwargs)
        for job in inputs.iter_jobs():
            config.add_job(job)

        if simulation_config is None:
            simulation_config = config.get_default_pydss_simulation_config()
        config.set_pydss_config(ConfigType.SIMULATION_CONFIG, simulation_config)

        if scenarios is None:
            scenarios = [PyDssConfiguration.make_default_pydss_scenario("scenario")]
        config.set_pydss_config(ConfigType.SCENARIOS, scenarios)

        config.apply_job_order()
        return config

    def apply_job_order(self):
        """Assign blocked_by field in each job."""
        base_cases = {}
        # This requires that base case jobs be listed first for a feeder.
        for job in self.iter_jobs():
            base_case = job.base_case
            if base_case is None:
                continue

            base_case_index = f"{job.feeder}-{base_case}"
            if job.name == base_case:
                assert base_case_index not in base_cases
                base_cases[base_case_index] = job.name
            elif base_case_index in base_cases:
                job.add_blocking_job(base_cases[base_case_index])

    def create_from_result(self, job, output_dir):
        cls = self.job_execution_class(job.extension)
        return cls.create(self.pydss_inputs, job, output=output_dir)

    def list_feeders(self):
        """Return a list of unique feeders in the config.

        Returns
        -------
        list

        """
        feeders = set()
        for job in self.iter_jobs():
            if job.extension in DeploymentParameters.list_extensions():
                feeders.add(job.feeder)

        return list(feeders)

    def get_feeder_jobs(self, feeder):
        """Return a generator of jobs for feeders in the config.

        Parameters
        ----------
        feeder : str
            Return jobs with this feeder.

        Yields
        ------
        DeploymentParameters

        """
        for job in self.iter_jobs():
            if job.feeder == feeder:
                yield job

    def get_feeder_job(self, feeder, deployment):
        """Return job by deployment

        Parameters
        ----------
        feeder : str
        deployment : str

        Returns
        -------
        DeploymentParameters

        Raises
        ------
        PyDssJobException

        """
        for job in self.get_feeder_jobs(feeder):
            if job.name == deployment:
                return job

        raise PyDssJobException(f"No Job with deployment name {deployment} in feeder {feeder}")
