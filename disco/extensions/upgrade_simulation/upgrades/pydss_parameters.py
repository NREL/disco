import logging
import opendssdirect as dss

from PyDSS.simulation_input_models import ProjectModel
from PyDSS.common import SimulationType
from PyDSS.controllers import CircuitElementController, ControllerManager

from disco.exceptions import PyDssConvergenceError


logger = logging.getLogger(__name__)


def define_initial_pydss_settings(pydss_volt_var_model):
    settings = ProjectModel(
        max_control_iterations=50,
        error_tolerance=0.0001,
        simulation_type=SimulationType.SNAPSHOT,
    )
    dss.Text.Command("Set ControlMode={}".format(settings.control_mode.value))
    dss.Solution.MaxControlIterations(settings.max_control_iterations)
    # we dont need to define controller everytime we solve the circuit, unless we're reloading the circuit
    controller = CircuitElementController(pydss_volt_var_model)  # Use all elements.
    pydss_controller_manager = ControllerManager.create([controller], settings)
    return pydss_controller_manager


def pydss_solve_and_check(pydss_controller_manager, raise_exception=False):
    logger.debug("Solving circuit using PyDSS controls")
    pydss_pass_flag = pydss_controller_manager.run_controls()
    if not pydss_pass_flag:
        logger.info(f"PyDSS Convergence Error")
        if raise_exception:
            raise PyDssConvergenceError("PyDSS solution did not converge")
    return pydss_pass_flag
