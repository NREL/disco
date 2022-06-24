import logging

import click
from jade.common import CONFIG_FILE
from jade.loggers import setup_logging
from jade.utils.utils import load_data

from disco.extensions.upgrade_simulation.upgrade_inputs import UpgradeInputs
from disco.extensions.upgrade_simulation.upgrade_configuration import (
    UpgradeConfiguration,
    DEFAULT_UPGRADE_COST_DB_FILE,
    DEFAULT_UPGRADE_PARAMS_FILE
)
from disco.models.upgrade_cost_analysis_generic_input_model import (
    ThermalUpgradeParamsModel,
    VoltageUpgradeParamsModel
)

logger = logging.getLogger(__name__)


@click.command()
@click.argument("inputs")
@click.option(
    "-d", "--cost-database",
    type=click.Path(exists=True),
    default=DEFAULT_UPGRADE_COST_DB_FILE,
    show_default=True,
    help="The unit cost database spreadsheet."
)
@click.option(
    "-p", "--params-file",
    type=click.Path(exists=True),
    required=False,
    default=DEFAULT_UPGRADE_PARAMS_FILE,
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
    setup_logging(__name__, None, console_level=level, packages=["disco"])

    params = load_data(params_file)
    thermal_upgrade_params = ThermalUpgradeParamsModel(**params["thermal_upgrade_params"]).dict()
    voltage_upgrade_params = VoltageUpgradeParamsModel(**params["voltage_upgrade_params"]).dict()
    upgrade_simulation_params = params["upgrade_simulation_params"]

    job_global_config = {
        "upgrade_cost_database": cost_database,
        "thermal_upgrade_params": thermal_upgrade_params,
        "voltage_upgrade_params": voltage_upgrade_params,
        "upgrade_simulation_params": upgrade_simulation_params
    }

    inputs = UpgradeInputs(inputs)
    config = UpgradeConfiguration.auto_config(
        inputs=inputs,
        job_global_config=job_global_config
    )
    config.dump(filename=config_file)
    print(f"Created {config_file} for upgrade cost analysis.")
