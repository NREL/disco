"""Runs a automatic upgrade analysis through PyDSS"""
import json
import logging
import os

from PyDSS.pydss_project import PyDssScenario
from jade.common import CONFIG_FILE

from disco.exceptions import PyDssConfigurationException
from disco.extensions.pydss_simulation.pydss_simulation import PyDssSimulation
from disco.pydss.common import ConfigType, UpgradeType, UPGRADE_SCRIPT_MAPPING
from disco.pydss.pydss_configuration_upgrade import (
    ThermalUpgradeConfiguration,
    VoltageUpgradeConfiguration
)
from disco.utils.dss_utils import extract_upgrade_results

logger = logging.getLogger(__name__)


class AutomatedUpgradeSimulation(PyDssSimulation):
    """Execute a automated upgrade process"""

    def __init__(self, pydss_inputs, job_global_config, job, output):
        """Construct a AutomatedUpgradeSimulation."""
        self._thermal_upgrade = UpgradeType.ThermalUpgrade.value
        self._voltage_upgrade = UpgradeType.VoltageUpgrade.value
        self._job_global_config = job_global_config
        super(AutomatedUpgradeSimulation, self).__init__(
            pydss_inputs=pydss_inputs,
            job=job,
            output=output
        )

    def __repr__(self):
        return f"AutomatedUpgradeSimulation: {self._model}"

    @staticmethod
    def generate_command(job, output, config_file, verbose=False):
        command = [
            "jade-internal run automated_upgrade_simulation",
            f"--name={job.name}",
            f"--output={output}",
            f"--config-file={config_file}"
        ]

        if verbose:
            command.append("--verbose")

        return " ".join(command)

    def _get_exports(self):
        return {
            "Log Results": False,
            "Export Elements": False,
        }

    def _get_upgrade_process_infos(self, scenario_name):
        if scenario_name == self._thermal_upgrade:
            return {
                "script": UPGRADE_SCRIPT_MAPPING[UpgradeType.ThermalUpgrade],
                "config_file": self._get_thermal_upgrade_config_file()
            }

        if scenario_name == self._voltage_upgrade:
            return {
                "script": UPGRADE_SCRIPT_MAPPING[UpgradeType.VoltageUpgrade],
                "config_file": self._get_voltage_upgrade_config_file()
            }

        raise PyDssConfigurationException(f"PyDSS does not support {scenario_name} configuration.")

    def _get_thermal_upgrade_config_file(self):
        """Get global thermal upgrade parameters, then overrides using job specific ones."""
        thermal_upgrade_config = ThermalUpgradeConfiguration(
            user_data=self._job_global_config["thermal_upgrade_config"]
        )
        overrides = self._model.upgrade_overrides.thermal_upgrade_overrides.dict()
        if not overrides["upgrade_library_path"]:
            overrides.pop("upgrade_library_path")
        thermal_upgrade_config.update(overrides)
        thermal_upgrade_config["project_data"] = self._model.deployment.project_data

        config_file = os.path.join(self._run_dir, "ThermalUpgrade.toml")
        thermal_upgrade_config.dump(config_file)

        return config_file

    def _get_voltage_upgrade_config_file(self):
        """Get global voltage upgrade parameters, then overrides using job specific ones."""
        voltage_upgrade_config = VoltageUpgradeConfiguration(
            user_data=self._job_global_config["voltage_upgrade_config"]
        )
        voltage_upgrade_config.update(
            self._model.upgrade_overrides.voltage_upgrade_overrides.dict()
        )
        voltage_upgrade_config["project_data"] = self._model.deployment.project_data

        config_file = os.path.join(self._run_dir, "VoltageUpgrade.toml")
        voltage_upgrade_config.dump(config_file)

        return config_file

    def _make_pydss_scenarios(self):
        pydss_scenarios = []
        for x in self._pydss_inputs[ConfigType.SCENARIOS]:
            scenario = PyDssScenario(
                x["name"],
                exports=self._make_pydss_exports(x),
                post_process_infos=[self._get_upgrade_process_infos(x["name"])]
            )
            pydss_scenarios.append(scenario)
        return pydss_scenarios

    def _collect_upgrade_files(self):
        """Collect upgrade files generated from jobs with lower job_order."""
        blocking_jobs = self._get_original_blocking_jobs()
        try:
            logger.info("Collecting upgrade files from %s jobs...", len(blocking_jobs))
            for job_name in blocking_jobs:
                project_path = os.path.join(self._output, job_name, "pydss_project")
                upgrade_results = extract_upgrade_results(project_path)
                self._model.upgrade_paths.extend(upgrade_results.values())
        except Exception:
            logger.exception("Failed to extract upgrade files.")
            raise

    # TODO: This is a temp solution for getting the original blocked_by data.
    # As blocked_by set changes during runtime in JADE, so could not use job.blocked_by direcly.
    def _get_original_blocking_jobs(self):
        """Get the original blocking jobs, i.e. blocked_by, from config file."""
        global_config_file = os.path.join(os.path.dirname(self._output), CONFIG_FILE)
        with open(global_config_file) as f:
            data = json.load(f)
        for job in data["jobs"]:
            if job["name"] == self._model.name:
                return set(job.get("blocked_by", []))
        return set()

    def run(self, verbose=False):
        if self._job_global_config["sequential_upgrade"]:
            self._collect_upgrade_files()
        return super().run(verbose=verbose)
