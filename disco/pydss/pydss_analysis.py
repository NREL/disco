"""Analysis of PyDSS simulations."""

import logging
import math
import os
import re

import pandas as pd

from jade.exceptions import InvalidParameter, InvalidConfiguration
from jade.jobs.job_analysis import JobAnalysis
from jade.utils.utils import load_data
from PyDSS.pydss_results import PyDssResults
from disco.sources.gem.make_element_bus_mapping import get_bus_to_element, \
    REGION_BUS_MAPPING_FILENAME


logger = logging.getLogger(__name__)


class PyDssAnalysis(JobAnalysis):
    """Performs analysis of PyDSS simulations."""

    def read_results(self, simulation):
        """Return all results dataframes for a simulation.

        Parameters
        ----------
        simulation : str | PyDssSimulationBase

        Returns
        -------
        dict
            class name : PyDssResult instance

        """
        if isinstance(simulation, str):
            simulation = self.get_simulation(simulation)

        return PyDssResults(simulation.pydss_project_path)


class PyDssScenarioAnalysis:
    """Performs analysis on one PyDSS scenario results."""

    _REGEX_PHASE_ANY_TERMINAL_1 = re.compile(rf"[ABCN]1")

    def __init__(self, job, results, scenario_name=None):
        self._job = job
        self._feeder = job.model.deployment.feeder
        if not results.scenarios:
            raise InvalidParameter("there are no scenarios in the results")

        if scenario_name is None:
            self._scenario = results.scenarios[0]
        else:
            self._scenario = results.get_scenario(scenario_name)

    def get_pu_bus_voltage_magnitudes(self):
        """Return per-unit voltage magnitudes for each bus.

        Returns
        -------
        dict
            Maps bus name to list of voltages.

        """
        voltages = {}
        for name in self._scenario.list_element_names("Buses", "puVmagAngle"):
            df = self._scenario.get_dataframe(
                "Buses",
                "puVmagAngle",
                name,
                phase_terminal=self._REGEX_PHASE_ANY_TERMINAL_1,
                mag_ang="mag",
            )
            voltages[name] = [row.mean() for _, row in df.iterrows()]

        return voltages

    def get_line_loading_percentages(self, fmt="dataframe"):
        """Return line loading values as percents for all lines.

        Parameters
        ----------
        fmt : str
            Controls output format. Must be 'dataframe' or 'json'."

        Returns
        -------
        dict
            Maps line name to loading percentages.

        """
        if fmt.lower() not in ("dataframe", "json"):
            raise InvalidParameter("fmt must be 'dataframe' or 'json'")

        loadings = {}
        columns = ["Line Loading (%)"]

        for name in self._scenario.list_element_names("Lines", "Currents"):
            df = self._scenario.get_dataframe(
                "Lines",
                "Currents",
                name,
                phase_terminal=self._REGEX_PHASE_ANY_TERMINAL_1
            )
            normal_amps = self._scenario.get_dataframe(
                "Lines",
                "NormalAmps",
                name,
            )
            values = []
            for i, row in df.iterrows():
                val = max(row.apply(lambda x: math.sqrt(x.real**2 + x.imag**2)))
                normal_amps_val = normal_amps.loc[i][normal_amps.columns[0]]
                values.append(val / normal_amps_val * 100)

            df = pd.DataFrame(values, index=df.index, columns=columns)
            if fmt == "json":
                loadings[name] = df.to_json(orient="records")
            else:
                loadings[name] = df

        return loadings

    def get_transformer_loading_percentages(self, fmt="dataframe"):
        """Return transformer loading values as percents for all transformers.

        Parameters
        ----------
        fmt : str
            Controls output format. Must be 'dataframe' or 'json'."

        Returns
        -------
        dict
            Maps transformer name to loading percentages pd.DataFrame.

        """
        if fmt.lower() not in ("dataframe", "json"):
            raise InvalidParameter("fmt must be 'dataframe' or 'json'")

        #transformers = self._scenario.read_element_info_file("Transformers")
        #transformers_phase_info = self._scenario.read_element_info_file("TransformersPhase")

        loadings = {}
        columns = ["Transformer Loading (%)"]
        for name in self._scenario.list_element_names("Transformers", "Currents"):
            #short_name = name.replace("Transformer.", "")
            df = self._scenario.get_dataframe(
                "Transformers",
                "Currents",
                name,
                phase_terminal=self._REGEX_PHASE_ANY_TERMINAL_1
            )
            normal_amps = self._scenario.get_dataframe(
                "Transformers",
                "NormalAmps",
                name,
            )

            # TODO: this needs some minor correction

            #transformer = transformers.query(f"Name == '{short_name}'").iloc[0]
            #transformer_phase = transformers_phase_info.query(f"Transformer == '{name}'").iloc[0]
            #num_windings = transformer["NumWindings"]
            #high_side_connection = transformer_phase["HighSideConnection"]
            #num_phases = len(df.columns)
            #if num_phases == 3 and high_side_connection == "wye":
            #    phase = 4
            #elif num_phases == 3 and high_side_connection == "delta":
            #    phase = 3
            #else:
            #    phase = num_phases

            values = []
            for i, row in df.iterrows():
                val = max(row.apply(lambda x: math.sqrt(x.real**2 + x.imag**2)))
                normal_amps_val = normal_amps.loc[i][normal_amps.columns[0]]
                values.append(val / normal_amps_val * 100)

            df = pd.DataFrame(values, index=df.index, columns=columns)
            if fmt == "json":
                loadings[name] = df.to_json(orient="records")
            else:
                loadings[name] = df

        return loadings

    def get_kw_at_bus_mapping(self):
        """Return a mapping of bus to PV system and load kW values.

        Requires that the script make_element_bus_mapping.py has been run on this feeder.

        Returns
        -------
        dict
            Key is bus name. Value is a list of dicts containing element info
            and kW values.

            Example: {"123456": [{"type": "pv_systems", "name": "pv_1234", "kW", 1.3}]}

        """
        input_directory = self._job.model.deployment.directory
        bus_mapping_file = os.path.join(
            input_directory, REGION_BUS_MAPPING_FILENAME
        )
        if not os.path.exists(bus_mapping_file):
            raise InvalidConfiguration(
                f"{bus_mapping_file} does not exist. Has make_element_bus_mapping.py been run?"
            )

        summary = load_data(bus_mapping_file)
        if self._feeder not in summary:
            raise InvalidConfiguration(
                f"{bus_mapping_file} does not contain feeder={self._feeder}"
            )

        feeder_file = summary[self._feeder]
        feeder_mapping = load_data(feeder_file)

        bus_to_elems = {}
        get_bus_to_element(bus_to_elems, feeder_mapping, "pv_systems")
        get_bus_to_element(bus_to_elems, feeder_mapping, "loads")

        pv_systems = self._scenario.read_element_info_file("PVSystems")
        loads = self._scenario.read_element_info_file("Loads")
        for elements in bus_to_elems.values():
            to_delete = []
            for i, element in enumerate(elements):
                src = pv_systems if element["type"] == "pv_systems" else loads
                df = src[src["Name"] == element["name"]]
                if len(df) == 0:
                    # The data may include other PV systems.
                    to_delete.append(i)
                    continue
                element["kW"] = df["kW"].values[0]
            for i in reversed(to_delete):
                elements.pop(i)

        return bus_to_elems
