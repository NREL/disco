
import copy
import logging

from disco.extensions.pydss_simulation.pydss_configuration import \
    PyDssConfiguration
from disco.extensions.pydss_simulation.pydss_inputs import PyDssInputs
from disco.pydss.common import ConfigType
from jade.utils.utils import load_data


logger = logging.getLogger(__name__)


def auto_config(inputs, **kwargs):
    """Create a configuration from all available inputs."""
    if isinstance(inputs, str):
        inputs = PyDssInputs(inputs)
    config = PyDssConfiguration(inputs, **kwargs)
    for job in config.inputs.iter_jobs():
        config.add_job(job)

    #exports = load_data(exports_filename)
    #config.set_pydss_config(ConfigType.EXPORTS, exports)

    return config
