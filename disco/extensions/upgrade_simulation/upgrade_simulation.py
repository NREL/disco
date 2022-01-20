

from .core.automated_thermal_upgrades import determine_thermal_upgrades
from .core.automated_voltage_upgrades import determine_voltage_upgrades
from .core.upgrade_parameters import PYDSS_PARAMS
from .core.cost_computation import compute_all_costs


class UpgradeSimulation:
    
    def __init__(self, job, job_global_config):
        self.job = job
        self.job_global_config = job_global_config

    @staticmethod
    def generate_command(job, output, config_file, verbose=False):
        """
        Parameters
        ----------
        job: UpgradeParameters
            The instance of upgradeParameters
        output: str
            The output directory of jobs, e.g output/job-outputs
        config_file: str
            The path of config file during runtime
        verbose: bool
            Enable verbose logging if True
        """
        command = [
            "jade-internal run upgrade_simulation",
            f"--name={job.name}",
            f"--output={output}",
            f"--config-file={config_file}"
        ]

        if verbose:
            command.append("--verbose")
        
        return " ".join(command)

    def run(self, verbose=False):
        determine_thermal_upgrades(**PYDSS_PARAMS)
        determine_voltage_upgrades(**PYDSS_PARAMS)
        compute_all_costs()


if __name__ == "__main__":
    upgrade = UpgradeSimulation()
    upgrade.run()
