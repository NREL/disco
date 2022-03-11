"""CLI to run a scenario."""
import logging

import opendssdirect as dss
from opendssdirect._version import __version__ as opendssdirect_version
from PyDSS import __version__ as pydss_version
from jade.jobs.job_configuration_factory import create_config_from_file
from disco.extensions.pydss_simulation.pydss_configuration import PyDssConfiguration
from disco.extensions.pydss_simulation.pydss_simulation import PyDssSimulation
from disco.version import __version__ as disco_version

logger = logging.getLogger(__name__)
DEFAULT_EXTENSION = "jade"


def auto_config(inputs, **kwargs):
    """
    Create a configuration file for PyDssSimulation.

    Parameters
    ----------
    inputs: str
        the path to directory containing PyDssSimulation data.

    """
    return PyDssConfiguration.auto_config(inputs, **kwargs)


def run(config_file, name, output, output_format, verbose):
    """Runs a PyDSS auto-generated scenario."""
    config = create_config_from_file(config_file, do_not_deserialize_jobs=True)
    job = config.get_job(name)

    logger.info("disco version = %s", disco_version)
    logger.info("PyDSS version = %s", pydss_version)
    logger.info("OpenDSSDirect version = %s", opendssdirect_version)
    logger.info("OpenDSS version = %s", dss.Basic.Version())

    simulation = PyDssSimulation.create(config.pydss_inputs,
                                        job,
                                        output=output)
    try:
        ret = simulation.run(verbose=verbose)
        return ret
    except Exception:
        logger.exception("unexpected exception in run pydss_simulation job=%s",
                         job.name)
        raise
