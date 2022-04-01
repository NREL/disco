import logging
import os

import click
from jade.common import CONFIG_FILE
from jade.loggers import setup_logging
from jade.utils.utils import load_data

from disco.extensions.upgrade_simulation.upgrades.common_functions import (
    get_default_upgrade_params_file,
    get_default_upgrade_cost_database
)
from disco.extensions.upgrade_simulation.upgrade_inputs import UpgradeInputs
from disco.extensions.upgrade_simulation.upgrade_configuration import UpgradeConfiguration

logger = logging.getLogger(__name__)


@click.command()
@click.argument("inputs")
@click.option(
    "-d", "--cost-database",
    type=click.Path(exists=True),
    default=get_default_upgrade_cost_database(),
    show_default=True,
    help="The unit cost database spreadsheet."
)
@click.option(
    "-p", "--params-file",
    type=click.Path(),
    required=False,
    default="upgrade-parameters.toml",
    show_default=True,
    help="Upgrade parameters file."
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
    cost_database,
    params_file,
    config_file,
    verbose=False
):
    """Create JADE configuration for upgrade simulations"""
    level = logging.DEBUG if verbose else logging.INFO
    setup_logging(__name__, None, console_level=level)

    if not os.path.exists(params_file):
        logger.info("Applied default upgrade parameters, %s", params_file)
        params_file = get_default_upgrade_params_file(params_file)

    inputs = UpgradeInputs(inputs)
    job_global_config = load_data(params_file)
    job_global_config["upgrade_cost_database"] = cost_database
    config = UpgradeConfiguration.auto_config(
        inputs=inputs,
        job_global_config=job_global_config
    )
    config.dump(filename=config_file)
    print(f"Created {config_file} for upgrade cost analysis.")
