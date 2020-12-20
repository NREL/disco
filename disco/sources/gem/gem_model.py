"""Model for GEM feeder input data.
The model can be transformed into DISCO OpenDSS model with PV deployments.
"""

import logging
import os
import shutil

from disco.sources.base import BaseOpenDssModel
from .factory import read_config_data


logger = logging.getLogger(__name__)


class GemModel(BaseOpenDssModel):
    """GEM Feeder Model Inputs Class"""

    @property
    def substation(self):
        return None

    @classmethod
    def transform(cls, input_file, output_path, simulation_model,
                  include_pv_systems=True):
        """Transform GEM input data to a DISCO data model.

        Parameters
        ----------
        input_file : str
        output_path : str

        """
        if os.path.exists(output_path):
            shutil.rmtree(output_path)
        os.makedirs(output_path)
        read_config_data(input_file).generate_output_data(
            output_path, include_pv_systems, simulation_model)
