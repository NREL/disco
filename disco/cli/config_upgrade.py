"""
Create Jade configuration for simulation jobs.
"""

import logging
import os
import sys

import click

from jade.common import CONFIG_FILE
from jade.loggers import setup_logging
from jade.jobs.job_post_process import JobPostProcess
from jade.utils.utils import dump_data, load_data

from disco.analysis import GENERIC_COST_DATABASE
from disco.extensions.automated_upgrade_simulation.automated_upgrade_configuration import \
    AutomatedUpgradeConfiguration
from disco.extensions.automated_upgrade_simulation.automated_upgrade_inputs import \
    AutomatedUpgradeInputs
from disco.pydss.pydss_configuration_upgrade import ThermalUpgradeConfiguration, \
    VoltageUpgradeConfiguration


@click.command()
@click.argument("inputs")
@click.option(
    "-s", "--single-upgrade",
    is_flag=True,
    default=False,
    help="Enable single upgrades."
)
@click.option(
    "-S", "--sequential-upgrade",
    is_flag=True,
    default=False,
    help="Enable sequential upgrades."
)
@click.option(
    "-d", "--cost-database",
    type=click.Path(exists=True),
    default=GENERIC_COST_DATABASE,
    show_default=True,
    help="The unit cost database spreadsheet."
)
@click.option(
    "-p", "--params-file",
    type=click.Path(),
    required=False,
    default="upgrade-params.toml",
    show_default=True,
    help="Thermal & Voltage upgrade parameters file."
)
@click.option(
    "--show-params",
    is_flag=True,
    default=False,
    help="Show the default upgrade parameters in file."
)
@click.option(
    "-n", "--nearest-redirect",
    is_flag=True,
    default=False,
    help="Redirect DSS files from nearest lower-order jobs."
)
@click.option(
    "-c", "--config-file",
    type=click.Path(),
    default=CONFIG_FILE,
    show_default=True,
    help="JADE config file to create"
)
@click.option(
    "--verbose",
    is_flag=True,
    default=False,
    help="Enable debug logging."
)
def upgrade(
        inputs,
        single_upgrade,
        sequential_upgrade,
        cost_database,
        params_file,
        show_params,
        nearest_redirect,
        config_file,
        verbose=False
    ):
    """Create JADE configuration for upgrade cost analysis."""
    level = logging.DEBUG if verbose else logging.INFO
    setup_logging(__name__, None, console_level=level)

    if single_upgrade and sequential_upgrade:
        print("--single-upgrade and --sequential-upgrade cannot both be set")
        sys.exit(1)
    
    if show_params:
        single_upgrade = True
    
    if not single_upgrade and not sequential_upgrade:
        print("--single-upgrade or --sequential-upgrade must be set")
        sys.exit(1)

    if not os.path.exists(params_file):
        params = {
            "thermal_upgrade_config": ThermalUpgradeConfiguration().defaults,
            "voltage_upgrade_config": VoltageUpgradeConfiguration().defaults
        }
        dump_data(params, params_file)

    if show_params:
        params = load_data(params_file)

        print_pretty_dict(params["thermal_upgrade_config"], "Thermal Upgrade Config")
        print("")
        print_pretty_dict(params["voltage_upgrade_config"], "Voltage Upgrade Config")
        print(f"\nUpgrade params from '{params_file}'.")
        return

    post_process = JobPostProcess(
        module_name="disco.analysis",
        class_name="UpgradeCostAnalysis",
        data={"unit_cost_data_file": cost_database}
    )
    inputs = AutomatedUpgradeInputs(inputs, sequential_upgrade, nearest_redirect)

    job_global_config = {
        "sequential_upgrade": sequential_upgrade,
        "nearest_redirect": nearest_redirect
    }
    job_global_config.update(load_data(params_file))
    config = AutomatedUpgradeConfiguration.auto_config(
        inputs=inputs,
        job_global_config=job_global_config,
        job_post_process_config=post_process.serialize()
    )

    config.dump(filename=config_file)
    print(f"Created {config_file} for UpgradeCostAnalysis.")


def print_pretty_dict(data, name=None):
    """Print dict data in pretty format"""
    maxlen = max([len(k) for k in data.keys()])
    template = "{:<{width}}   {}\n".format("Parameter", "Value", width=maxlen)
    for k, v in data.items():
        if v is True:
            v = "true"
        elif v is False:
            v = "false"
        template += "{:<{width}} : {}\n".format(k, str(v), width=maxlen)
    pretty_string = template.rstrip()

    print(name)
    print("----------")
    print(pretty_string)
