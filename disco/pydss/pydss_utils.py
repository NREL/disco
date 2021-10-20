"""Contains PyDSS utility functions"""

import json

from PyDSS.pydss_project import PyDssProject


def detect_convergence_problems(project_path):
    """Detects convergence problems in a PyDSS run.

    Parameters
    ----------
    project_path : str

    Returns
    -------
    list
        list of dicts with keys: 'scenario', 'priority', 'step'

    """
    problems = []
    project = PyDssProject.load_project(project_path)
    project_name = project.simulation_config.project.active_project
    for scenario in project.list_scenario_names():
        log_file = f"Logs/{project_name}__{scenario}__reports.log"
        problems += _detect_convergence_problems(project.fs_interface.read_file(log_file))

    return problems


def _detect_convergence_problems(text):
    problems = []
    for line in text.splitlines():
        data = json.loads(line)
        if data["Report"] == "Convergence":
            problems.append(data)

    return problems
