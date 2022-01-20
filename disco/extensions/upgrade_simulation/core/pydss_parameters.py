from PyDSS.simulation_input_models import ProjectModel, SimulationSettingsModel
from PyDSS.common import LoggingLevel, SimulationType
from PyDSS.controllers import CircuitElementController, ControllerManager

# from PyDSS.get_snapshot_timepoints import get_snapshot_timepoint
# new_start = get_snapshot_timepoint(SimulationSettingsModel, SnapshotTimePointSelectionMode.DAYTIME_MIN_LOAD)
# new_start = get_snapshot_timepoint(SimulationSettingsModel, SnapshotTimePointSelectionMode.DAYTIME_MIN_LOAD).strftime(DATE_FORMAT)
from .upgrade_parameters import volt_var_model
import logging
import opendssdirect as dss

logger = logging.getLogger(__name__)


def define_initial_pydss_settings(**kwargs):
    settings = ProjectModel(
        max_control_iterations=50,
        error_tolerance=0.0001,
        simulation_type=SimulationType.SNAPSHOT,
    )
    dss.utils.run_command("Set ControlMode={}".format(settings.control_mode.value))
    dss.Solution.MaxControlIterations(settings.max_control_iterations)
    # we dont need to define controller everytime we solve the circuit, unless we're reloading the circuit
    controller = CircuitElementController(
        kwargs["pydss_volt_var_model"]
    )  # Use all elements.
    pydss_controller_manager = ControllerManager.create([controller], settings)
    kwargs.update({"pydss_controller_manager": pydss_controller_manager})
    return kwargs


def pydss_solve_and_check(raise_exception=False, **kwargs):
    logger.debug("Solving circuit using PyDSS controls")
    pydss_pass_flag = kwargs["pydss_controller_manager"].run_controls()
    if not pydss_pass_flag:
        logger.info(f"PyDSS Convergence Error")
        if raise_exception:
            raise Exception("PyDSS solution did not converge")
    return pydss_pass_flag
