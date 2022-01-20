
from disco.extensions.upgrade_simulation.upgrade_inputs import UpgradeInputs
from disco.extensions.upgrade_simulation.upgrade_parameters import UpgradeParameters
from disco.pydss.pydss_configuration_base import PyDssConfigurationBase


class UpgradeConfiguration(PyDssConfigurationBase):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @classmethod
    def auto_config(cls, inputs, **kwargs):
        if isinstance(inputs, str):
            inputs = UpgradeInputs(inputs)
        
        config = cls(**kwargs)
        for job in inputs.iter_jobs():
            config.add_job(job)
        
        return config

    def create_from_result(self, job, output_dir):
        cls = self.job_execution_class(job.extension)
        return cls.create(job, output=output_dir)
