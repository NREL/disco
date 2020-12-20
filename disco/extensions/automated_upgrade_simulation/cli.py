"""
Command line functions.
"""
import logging
import os

from jade.jobs.job_configuration_factory import create_config_from_file
from jade.utils.utils import get_cli_string

from disco.extensions.automated_upgrade_simulation.automated_upgrade_configuration import \
    AutomatedUpgradeConfiguration
from disco.extensions.automated_upgrade_simulation.automated_upgrade_inputs import \
    AutomatedUpgradeInputs
from disco.extensions.automated_upgrade_simulation.automated_upgrade_simulation import \
    AutomatedUpgradeSimulation

logger = logging.getLogger(__name__)


def auto_config(inputs, **kwargs):
    """Create a configuration file for automatic upgrade analysis

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

    # TODO: update JADE to support job_global_config
    job_global_config = kwargs["job_global_config"]
    inputs = AutomatedUpgradeInputs(
        inputs,
        job_global_config["sequential_upgrade"],
        job_global_config["nearest_redirect"]
    )
    config = AutomatedUpgradeConfiguration(inputs=inputs, **kwargs)
    for job in config.inputs.iter_jobs():
        config.add_job(job)

    return config


def run(config_file, name, output, output_format, verbose):
    """Run automated upgrade simulation through command line"""
    os.makedirs(output, exist_ok=True)

    config = create_config_from_file(config_file, do_not_deserialize_jobs=True)
    job = config.get_job(name)

    print(get_cli_string())
    simulation = AutomatedUpgradeSimulation(
        pydss_inputs=config.get_job_inputs(),
        job_global_config=config.job_global_config,
        job=job,
        output=output
    )
    try:
        ret = simulation.run(verbose=verbose)
        return ret
    except Exception:
        logger.exception("Unexcepted error in automatic upgrade analysis job=%s", job)
        raise
