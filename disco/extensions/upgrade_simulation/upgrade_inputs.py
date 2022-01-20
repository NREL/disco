
import os

from jade.utils.utils import load_data
from disco.distribution.distribution_inputs import DistributionInputs
from disco.extensions.upgrade_simulation.upgrade_parameters import UpgradeParameters


class UpgradeInputs(DistributionInputs):
    
    def __init__(self, base_directory):
        super().__init__(base_directory)

    def _parse_config_files(self):
        filename = os.path.join(self._base, self._CONFIG_FILE)
        data = load_data(filename)
        for job_data in data:
            job = UpgradeParameters(**job_data)
            assert job.name not in self._parameters
            self._parameters[job.name] = job
