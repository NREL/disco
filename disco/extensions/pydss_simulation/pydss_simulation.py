"""Runs a simulation through PyDSS."""

import fileinput
import logging
import os
import re
import shutil
from pathlib import Path

from jade.common import OUTPUT_DIR
from jade.utils.utils import modify_file, interpret_datetime
from PyDSS.common import DATE_FORMAT

from disco.enums import SimulationType
from disco.pydss.common import ConfigType
from disco.pydss.pydss_simulation_base import PyDssSimulationBase


logger = logging.getLogger(__name__)

DEFAULTS = {
    "output": OUTPUT_DIR,
}


class PyDssSimulation(PyDssSimulationBase):
    """Runs a PyDss simulation."""

    SIMULATION_TYPE_TO_PYDSS_TYPE = {
        SimulationType.SNAPSHOT: "Snapshot",
        SimulationType.QSTS: "QSTS",
        SimulationType.TIME_SERIES: "QSTS",
    }

    def __init__(self, pydss_inputs, job, output=DEFAULTS["output"]):
        """Constructs a PyDssSimulation.

        Raises
        ------
        InvalidParameter
            Raised if any parameter is invalid.

        """
        super(PyDssSimulation, self).__init__(
            pydss_inputs,
            job,
            output
        )

    def __repr__(self):
        return f"Simulation: {self._model}"

    @classmethod
    def create(cls, pydss_inputs, job, output):
        logger.debug("params=%s", job)
        sim = cls(pydss_inputs, job, output=output)
        return sim

    @staticmethod
    def generate_command(job, output, config_file, verbose=False):
        command = [
            "jade-internal run pydss_simulation",
            f"--name={job.name}",
            f"--output={output}",
            f"--config-file={config_file}",
        ]

        if verbose:
            command.append("--verbose")

        return " ".join(command)

    def _get_scenario_names(self):
        return [x["name"] for x in self._pydss_inputs[ConfigType.SCENARIOS]]

    def _get_deployment_input_path(self):
        return os.path.join(
            self._dss_dir,
            self._get_deployment_input_filename(),
        )

    @staticmethod
    def _get_deployment_input_filename():
        return "deployment.dss"

    @staticmethod
    def _is_dss_file_path_absolute():
        return False

    def _modify_open_dss_parameters(self):
        deployment_filename = self._get_deployment_input_path()
        shutil.copyfile(self._model.deployment.deployment_file,
                        deployment_filename)
        modify_file(deployment_filename, self._recalculate_kva)
        logger.info("Modified kVA in %s", deployment_filename)

        modify_file(deployment_filename, self.fix_redirects, Path(deployment_filename))
        logger.info("Modified redirect path in %s", deployment_filename)

    @staticmethod
    def _minutes_from_midnight(timetuple):
        return timetuple.tm_hour * 60 + timetuple.tm_min

    def _modify_pydss_simulation_params(self, config):
        start_time = self._model.simulation.start_time
        end_time = self._model.simulation.end_time
        if start_time is not None:
            config["start_time"] = start_time.strftime(DATE_FORMAT)

        match = self._REGEX_YEAR.search(config["start_time"])
        assert match, config["start_time"]
        start_time_year = int(match.group(1))
        self._make_years_match(start_time_year, config, "loadshape_start_time")

        if end_time is not None:
            config["simulation_duration_min"] = (end_time - start_time).total_seconds() / 60

        if self._model.simulation.step_resolution is not None:
            config["step_resolution_sec"] = self._model.simulation.step_resolution

        config["simulation_type"] = self.SIMULATION_TYPE_TO_PYDSS_TYPE[self._model.simulation.simulation_type]

    def _recalculate_kva(self, line, *args, **kwargs):
        """Adjust kVA for dc_ac_ratio and kva_to_kw_rating."""
        values = []
        pmpp = None
        old_pct_pmpp = None
        pct_pmpp_index = None
        old_kva = None
        kva_index = None

        # Extract the kVA token, recalculate it, then add it back.
        for i, token in enumerate(line.split()):
            val_pair = token.split("=")
            if len(val_pair) == 2:
                if val_pair[0].lower() == "pmpp":
                    pmpp = float(val_pair[1])
                elif val_pair[0].lower() == "%pmpp":
                    old_pct_pmpp = float(val_pair[1])
                    pct_pmpp_index = i
                elif val_pair[0].lower() == "kva":
                    old_kva = float(val_pair[1])
                    kva_index = i
            values.append(token)

        if pmpp is None or old_kva is None:
            # No change required.
            return line

        dc_ac_ratio = self._model.deployment.dc_ac_ratio
        kva_to_kw_rating = self._model.deployment.kva_to_kw_rating

        if dc_ac_ratio is None or kva_to_kw_rating is None:
            assert dc_ac_ratio is None
            assert kva_to_kw_rating is None
            # No change required.
            return line

        kva = kva_to_kw_rating * pmpp / dc_ac_ratio
        values[kva_index] = f"kVA={kva}"
        logger.debug("old kVA = %s, new kVA = %s", old_kva, kva)

        if old_pct_pmpp is not None or self._add_pct_pmpp:
            pct_pmpp = self._irradiance_scaling_factor / dc_ac_ratio
            token = f"%Pmpp={pct_pmpp}"
            if pct_pmpp_index is None:
                values.append(token)
                logger.debug("Added pct_pmpp = %s", pct_pmpp)
            else:
                values[pct_pmpp_index] = token
                logger.debug("old pct_pmpp = %s, new pct_pmpp = %s",
                             old_pct_pmpp, pct_pmpp)

        return " ".join(values) + "\n"

    def fix_redirects(self, line, deployment_filename, **kwargs):
        """Fix the paths to a redirect file."""
        regex = re.compile(r"^([Rr]edirect\s+)(.*)")
        match = regex.search(line)
        if match is None:
            return line

        # The deployment file is now farther away from the base files.
        # This will change Redirect ../OpenDSS/Master.dss
        # to something like
        # Redirect ../../../../../model-inputs/X/OpenDSS/Master.dss

        base_path = Path(".")
        assert len(deployment_filename.parts) >= 2
        parts = [".."] * (len(deployment_filename.parts) - 1)
        parts.append(self._model.deployment.directory)
        base_path = Path(parts[0])
        for part in parts[1:]:
            base_path /= part

        path = Path(match.group(2))
        parts = [x for x in path.parts if str(x) != ".."]
        new_path = base_path
        for parent in parts:
            new_path /= parent
        new_line = match.group(1) + str(new_path)
        return new_line
