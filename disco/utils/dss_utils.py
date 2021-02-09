"""Contains OpenDSS utility functions."""

import logging
import os
import re

from filelock import SoftFileLock
from PyDSS.pydss_project import PyDssProject

from disco.pydss.common import UpgradeType


logger = logging.getLogger(__name__)


def read_capacitor_changes(event_log):
    """Read the capacitor state changes from an OpenDSS event log.

    Parameters
    ----------
    event_log : str
        Path to event log

    Returns
    -------
    dict
        Maps capacitor names to count of state changes.

    """
    capacitor_changes = {}
    regex = re.compile(r"(Capacitor\.\w+)")

    data = read_event_log(event_log)
    for row in data:
        match = regex.search(row["Element"])
        if match:
            name = match.group(1)
            if name not in capacitor_changes:
                capacitor_changes[name] = 0
            action = row["Action"].replace("*", "")
            if action in ("OPENED", "CLOSED", "STEP UP"):
                capacitor_changes[name] += 1

    return capacitor_changes


def read_event_log(filename):
    """Return OpenDSS event log information.

    Parameters
    ----------
    filename : str
        path to event log file.


    Returns
    -------
    list
        list of dictionaries (one dict for each row in the file)

    """
    data = []

    with open(filename) as f_in:
        for line in f_in:
            tokens = [x.strip() for x in line.split(",")]
            row = {}
            for token in tokens:
                name_and_value = [x.strip() for x in token.split("=")]
                name = name_and_value[0]
                value = name_and_value[1]
                row[name] = value
            data.append(row)

    return data


def extract_upgrade_results(project_path, file_ext=".dss"):
    """Extract given file path from project.zip created by PyDSS.

    Parameters
    ----------
    project_path : str
        The path to the pydss_project path.
    file_path : str
        Relative file path within project.zip.
    file_type: str
        The extension of upgrade files, choices: .dss | .json
    """
    if file_ext == ".dss":
        upgrades_result = _extract_upgrade_dss_files(project_path)
    elif file_ext == ".json":
        upgrades_result = _extract_upgrade_json_files(project_path)
    else:
        upgrades_result = {"thermal": None, "voltage": None}
    return upgrades_result


def _extract_upgrade_dss_files(project_path):
    """Extract .dss upgrades files from pydss_project."""
    upgrade_results = {}

    lock_file = os.path.join(project_path, "project__upgrades.dss.lock")
    with SoftFileLock(lock_file=lock_file):
        thermal_upgrade_file = os.path.join(project_path, "thermal_upgrades.dss")
        voltage_upgrade_file = os.path.join(project_path, "voltage_upgrades.dss")

        # Return if upgrade dss file exists.
        if os.path.exists(thermal_upgrade_file):
            upgrade_results["thermal"] = thermal_upgrade_file
        if os.path.exists(voltage_upgrade_file):
            upgrade_results["voltage"] = voltage_upgrade_file

        if len(upgrade_results) == 2:
            return upgrade_results

        # Extract if upgrade dss files not exist
        if not os.path.exists(os.path.join(project_path, "project.zip")):
            return upgrade_results

        pydss_project = PyDssProject.load_project(project_path)
        if "thermal" not in upgrade_results:
            text = pydss_project.fs_interface.read_file(os.path.join(
                "Scenarios",
                UpgradeType.ThermalUpgrade.value,
                "PostProcess",
                "thermal_upgrades.dss"
            ))
            open(thermal_upgrade_file, "w").write(text)
            upgrade_results["thermal"] = thermal_upgrade_file

        if "voltage" not in upgrade_results:
            text = pydss_project.fs_interface.read_file(os.path.join(
                "Scenarios",
                UpgradeType.VoltageUpgrade.value,
                "PostProcess",
                "voltage_upgrades.dss"
            ))
            open(voltage_upgrade_file, "w").write(text)
            upgrade_results["voltage"] = voltage_upgrade_file

    return upgrade_results


def _extract_upgrade_json_files(project_path):
    """Extract .json upgrades files from pydss_project."""
    upgrade_results = {}
    thermal_upgrade_file = os.path.join(project_path, "Processed_thermal_upgrades.json")
    voltage_upgrade_file = os.path.join(project_path, "Processed_voltage_upgrades.json")

    pydss_project = PyDssProject.load_project(project_path)
    if "thermal" not in upgrade_results:
        text = pydss_project.fs_interface.read_file(os.path.join(
            "Scenarios",
            UpgradeType.ThermalUpgrade.value,
            "PostProcess",
            "Processed_thermal_upgrades.json"
        ))
        with open(thermal_upgrade_file, "w") as f:
            f.write(text)
        upgrade_results["thermal"] = thermal_upgrade_file

    if "voltage" not in upgrade_results:
        text = pydss_project.fs_interface.read_file(os.path.join(
            "Scenarios",
            UpgradeType.VoltageUpgrade.value,
            "PostProcess",
            "Processed_voltage_upgrades.json"
        ))
        with open(voltage_upgrade_file, "w") as f:
            f.write(text)
        upgrade_results["voltage"] = voltage_upgrade_file

    return upgrade_results
