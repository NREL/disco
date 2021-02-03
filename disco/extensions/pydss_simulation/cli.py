"""CLI to run a scenario."""

import importlib
import logging
import os
import sys

import click

from jade.common import CONFIG_FILE, OUTPUT_DIR
from disco.extensions.pydss_simulation.pydss_configuration import PyDssConfiguration
from jade.jobs.job_configuration_factory import create_config_from_file
from jade.exceptions import InvalidExtension
from disco.extensions.pydss_simulation.pydss_simulation import PyDssSimulation
from jade.utils.utils import get_cli_string


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

    print(get_cli_string())

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
