"""Contains PyDSS utility functions"""

import re

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
    project_name = project.simulation_config["Project"]["Active Project"]
    for scenario in project.list_scenario_names():
        log_file = "Logs/pydss.log"
        problems += _detect_convergence_problems(
            scenario, project.fs_interface.read_file(log_file)
        )

    return problems


def _detect_convergence_problems(scenario, text):
    problems = []
    regex = re.compile(r"WARNING.*Control Loop (?P<priority>\d+) no convergence @ (?P<step>\d+)")
    for line in text.splitlines():
        if "no convergence" in line:
            match = regex.search(line)
            assert match
            priority = int(match.groupdict()["priority"])
            step = int(match.groupdict()["step"])
            problems.append({
                "scenario": scenario,
                "priority": priority,
                "step": step,
            })

    return problems
