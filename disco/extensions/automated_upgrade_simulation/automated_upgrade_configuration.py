"""Contains functionality to configure automatic upgrade analysis"""

from disco.pydss.common import UpgradeType, ConfigType
from disco.pydss.pydss_configuration_base import PyDssConfigurationBase
from disco.extensions.automated_upgrade_simulation.automated_upgrade_inputs import \
    AutomatedUpgradeInputs
from disco.extensions.automated_upgrade_simulation.automated_upgrade_parameters import \
    AutomatedUpgradeParameters


class AutomatedUpgradeConfiguration(PyDssConfigurationBase):
    """Represents the configuration options for automatic upgrade analysis"""

    def __init__(self, **kwargs):
        """Construct automatic upgrade configuration"""
        super(AutomatedUpgradeConfiguration, self).__init__(**kwargs)

    @classmethod
    def auto_config(cls, inputs, simulation_config=None, scenarios=None, **kwargs):
        """Create a configuration from all available inputs."""
        if isinstance(inputs, str):
            inputs = AutomatedUpgradeInputs(inputs)
        config = cls(**kwargs)
        for job in inputs.iter_jobs():
            config.add_job(job)

        if simulation_config is None:
            simulation_config = config.get_default_pydss_simulation_config()
        config.set_pydss_config(ConfigType.SIMULATION_CONFIG, simulation_config)

        if scenarios is None:
            scenarios = [
                cls.make_default_pydss_scenario(upgrade_type.value)
                for upgrade_type in UpgradeType
            ]
        config.set_pydss_config(ConfigType.SCENARIOS, scenarios)

        return config

    def create_from_result(self, job, output_dir):
        cls = self.job_execution_class(job.extension)
        return cls.create(job, output=output_dir)
