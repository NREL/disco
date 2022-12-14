"""Contains functionality to configure PyDss simulations."""

import logging
from collections import defaultdict

from jade.exceptions import InvalidParameter, InvalidConfiguration
from jade.extensions.generic_command.generic_command_parameters import GenericCommandParameters
from jade.utils.utils import load_data

from PyDSS.common import ControllerType
from PyDSS.reports.pv_reports import CONTROL_MODE_SCENARIO

from disco.distribution.deployment_parameters import DeploymentParameters
from disco.enums import SimulationHierarchy, SimulationType
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
    def auto_config(cls, inputs, simulation_config=None, scenarios=None,
                    order_by_penetration=False, estimated_run_minutes=None,
                    dc_ac_ratio=None, **kwargs):
        """Create a configuration from all available inputs."""
        if isinstance(inputs, str):
            inputs = PyDssInputs(inputs)
        config = cls(**kwargs)
        for job in inputs.iter_jobs():
            job.estimated_run_minutes = estimated_run_minutes
            if dc_ac_ratio is not None:
                job.model.deployment.dc_ac_ratio = dc_ac_ratio
            config.add_job(job)

        if simulation_config is None:
            simulation_config = config.get_default_pydss_simulation_config()
        config.set_pydss_config(ConfigType.SIMULATION_CONFIG, simulation_config)

        if scenarios is None:
            scenarios = [PyDssConfiguration.make_default_pydss_scenario("scenario")]
        config.set_pydss_config(ConfigType.SCENARIOS, scenarios)

        if order_by_penetration:
            config.apply_job_order_by_penetration_level()

        config.check_job_consistency()
        return config

    def apply_job_order_by_penetration_level(self):
        """Assign blocked_by field in each job."""
        keys = set(("placement", "sample", "penetration_level"))
        jobs_to_order = defaultdict(list)
        for job in self.iter_pydss_simulation_jobs():
            if len(keys.intersection(set(job.model.deployment.project_data.keys()))) == 3:
                key = (
                    job.model.deployment.substation,
                    job.model.deployment.feeder,
                    job.model.deployment.project_data["placement"],
                    job.model.deployment.project_data["sample"],
                )
                jobs_to_order[key].append(job)

        # If a job of a lower penetration level fails with a convergence error then
        # all higher jobs are expected to fail. This allows us to cancel those jobs.
        for jobs in jobs_to_order.values():
            if len(jobs) < 2:
                continue
            jobs.sort(key=lambda x: x.model.deployment.project_data["penetration_level"])
            for i, job in enumerate(jobs[1:]):
                # Blocked by the previous job.
                job.add_blocking_job(jobs[i].name)

    def check_job_consistency(self):
        """Check all jobs for consistency.
        
        Raises
        ------
        InvalidConfiguration
            Raised if a rule is violated.

        """
        config_has_pydss_controllers = None
        for job in self.iter_pydss_simulation_jobs(exclude_base_case=True):
            if config_has_pydss_controllers is None:
                config_has_pydss_controllers = job.has_pydss_controllers()
            elif job.has_pydss_controllers() != config_has_pydss_controllers:
                raise InvalidParameter("All jobs must consistently define pydss_controllers.")
        
    def create_from_result(self, job, output_dir):
        cls = self.job_execution_class(job.extension)
        return cls.create(self.pydss_inputs, job, output=output_dir)

    def get_base_case_job(self, feeder):
        """Return the base_case job for the given feeder.

        Parameters
        ----------
        feeder : str

        """
        for job in self.iter_feeder_jobs(feeder):
            if job.model.is_base_case:
                return job

        return InvalidParameter(f"no base case job for feeder={feeder}")

    def get_simulation_hierarchy(self):
        """Return the SimulationHierarchy for the config.

        Returns
        -------
        SimulationHierarchy

        """
        for job in self.iter_pydss_simulation_jobs():
            if not job.model.is_base_case:
                if job.model.deployment.feeder == "None":
                    hierarchy = SimulationHierarchy.SUBSTATION
                else:
                    hierarchy = SimulationHierarchy.FEEDER
                return hierarchy

        raise Exception("Failed to identify SimulationHierarchy")

    def has_pydss_controllers(self):
        """Return True if the jobs have pydss controllers defined."""
        job = next(iter(self.iter_pydss_simulation_jobs(exclude_base_case=True)))
        return job.has_pydss_controllers()

    def iter_feeder_jobs(self, feeder):
        """Return jobs for the given feeder in the config.

        Parameters
        ----------
        feeder : str
            Return jobs with this feeder.

        Yields
        ------
        DeploymentParameters

        """
        for job in self.iter_pydss_simulation_jobs():
            if job.feeder == feeder:
                yield job

    def iter_pydss_simulation_jobs(self, exclude_base_case=False):
        """Return jobs that are pydss_simulation jobs (not post-processing).

        Parameters
        ----------
        exclude_base_case : bool

        Yields
        ------
        DeploymentParameters

        """
        for job in self.iter_jobs():
            if isinstance(job, DeploymentParameters):
                if exclude_base_case and job.model.is_base_case:
                    continue
                yield job

    def list_feeders(self):
        """Return a list of unique feeders in the config.

        Returns
        -------
        list

        """
        return list({x.feeder for x in self.iter_pydss_simulation_jobs()})

    def get_feeder_job(self, feeder, job_name):
        """Return job by name

        Parameters
        ----------
        feeder : str
        job_name : str

        Returns
        -------
        DeploymentParameters

        """
        # TODO: callers should just call this.
        return self.get_job(job_name)

    def update_volt_var_curve(self, volt_var_curve: str):
        """Update the volt-var curve for all jobs configured with PV controls."""
        count = 0
        for job in self.iter_pydss_simulation_jobs(exclude_base_case=True):
            pydss_controllers = job.model.deployment.pydss_controllers
            if pydss_controllers is not None:
                if isinstance(pydss_controllers, list):
                    for controller in pydss_controllers:
                        if controller.controller_type == ControllerType.PV_CONTROLLER:
                            controller.name = volt_var_curve
                            count += 1
                elif pydss_controllers.controller_type == ControllerType.PV_CONTROLLER:
                    pydss_controllers.name = volt_var_curve
                    count += 1

        logger.info("Updated %s jobs with volt-var curve %s", count, volt_var_curve)
