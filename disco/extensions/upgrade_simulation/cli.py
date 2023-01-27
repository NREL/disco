import logging
import os

from jade.jobs.job_configuration_factory import create_config_from_file
from jade.utils.utils import load_data
from PyDSS.controllers import PvControllerModel

from disco.extensions.upgrade_simulation.upgrade_configuration import UpgradeConfiguration
from disco.extensions.upgrade_simulation.upgrade_inputs import UpgradeInputs
from disco.extensions.upgrade_simulation.upgrade_simulation import UpgradeSimulation
from disco.pydss.pydss_configuration_base import DEFAULT_CONTROLLER_CONFIG_FILE
from disco.version import __version__ as disco_version
from disco.models.upgrade_cost_analysis_generic_input_model import (
    UpgradeCostAnalysisSimulationModel, UpgradeSimulationParamsModel
)

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
        raise FileNotFoundError(f"Inputs path '{inputs}' does not exist.")

    inputs = UpgradeInputs(inputs)
    config = UpgradeConfiguration(inputs=inputs, **kwargs)
    for job in config.inputs.iter_jobs():
        config.add_job(job)

    return config


def run(config_file, name, output, output_format, verbose):
    """Run automated upgrade simulation through command line"""
    os.makedirs(output, exist_ok=True)

    config = create_config_from_file(config_file, do_not_deserialize_jobs=True)
    job = config.get_job(name)

    logger.info("disco version = %s", disco_version)

    simulation = UpgradeSimulation(
        job=job,
        job_global_config=config.job_global_config,
        output=output
    )
    upgrade_simulation_params_config = config.job_global_config["upgrade_simulation_params"]
    try:
        thermal_config = config.job_global_config["thermal_upgrade_params"]
        voltage_config = config.job_global_config["voltage_upgrade_params"]
        cost_database_filepath = config.job_global_config["upgrade_cost_database"]
        upgrade_simulation_params_names = list(UpgradeSimulationParamsModel.schema()["properties"].keys())
        fields = set(upgrade_simulation_params_names) & set(upgrade_simulation_params_config.keys())
        temp = {key: upgrade_simulation_params_config[key] for key in fields}
        upgrade_simulation_params_config = UpgradeSimulationParamsModel(**temp).dict()

        if config.job_global_config["upgrade_simulation_params"]["enable_pydss_controllers"]:
            pv_controllers = load_data(DEFAULT_CONTROLLER_CONFIG_FILE)
            controller_model = PvControllerModel(
                **pv_controllers[config.job_global_config["upgrade_simulation_params"]["pydss_controller_name"]]
            )
            upgrade_simulation_params_config["pydss_controllers"] = controller_model
        else:
           upgrade_simulation_params_config["pydss_controllers"] = None

        ret = simulation.run(
            thermal_config=thermal_config,
            voltage_config=voltage_config,
            upgrade_simulation_params_config=upgrade_simulation_params_config,
            cost_database_filepath=cost_database_filepath,
        )
        return ret
    except Exception:
        logger.exception("Unexcepted error in automatic upgrade analysis job=%s", job)
        raise
