import logging
import click

from jade.common import CONFIG_FILE
from jade.loggers import setup_logging
from disco.postprocess.config import GENERIC_COST_DATABASE

from disco.extensions.upgrade_simulation.upgrade_inputs import UpgradeInputs
from disco.extensions.upgrade_simulation.upgrade_configuration import UpgradeConfiguration


@click.command()
@click.argument("inputs")
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
def upgrade(inputs, cost_database, params_file, config_file, verbose=False):
    """Create JADE configuration for upgrade simulations"""
    level = logging.DEBUG if verbose else logging.INFO
    setup_logging(__name__, None, console_level=level)

    inputs = UpgradeInputs(inputs)
    config = UpgradeConfiguration.auto_config(inputs=inputs)
    config.dump(filename=config_file)
    print(f"Created {config_file} for upgrade simulation and analysis")
