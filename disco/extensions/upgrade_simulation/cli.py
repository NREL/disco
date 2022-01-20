import logging
import os

from jade.jobs.job_configuration_factory import create_config_from_file

from disco.extensions.upgrade_simulation.upgrade_configuration import UpgradeConfiguration
from disco.extensions.upgrade_simulation.upgrade_inputs import UpgradeInputs
from disco.extensions.upgrade_simulation.upgrade_simulation import UpgradeSimulation
from disco.version import __version__ as disco_version

logger = logging.getLogger(__name__)


def auto_config(inputs, **kwargs):
    """Create a configuration file for automated upgrade simulation/analysis.

    Parameters
    ----------
    inputs : str
        The model-inputs path for automated upgrade simulation.
    
    Returns
    -------
    :obj:`JobConfiguration`
        An instance of job configuration.
    """
    if not os.path.exists(inputs):
        raise OSError(f"Inputs path '{inputs}' does not exist.")

    inputs = UpgradeInputs(inputs)
    config = UpgradeConfiguration(inputs=inputs, **kwargs)
    for job in config.inputs.iter_jobs():
        config.add_job(job)

    return config


def run(config_file, name, output, verbose):
    """Run automated upgrade simulation through command line"""
    os.makedirs(output, exist_ok=True)

    config = create_config_from_file(config_file, do_not_deserialize_jobs=True)
    job = config.get_job(name)

    logger.info("disco version = %s", disco_version)

    simulation = UpgradeSimulation(job=job)
    try:
        ret = simulation.run(verbose=verbose)
        return ret
    except Exception:
        logger.exception("Unexcepted error in automatic upgrade analysis job=%s", job)
        raise
