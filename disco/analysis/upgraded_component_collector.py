"""Collects upgraded component information from PyDssSimulation jobs."""

import json
import os

import pandas as pd


class UpgradedComponentCollector:
    """Collects upgraded component information from a PyDssSimulation job."""

    UPGRADES_FILE = "Scenarios/ThermalUpgrade/PostProcess/Processed_upgrades.json"

    def __init__(self, job, job_dir, pydss_results):
        """Constructs UpgradeAnalysis.

        Parameters
        ----------
        job : DeploymentParameters
            PyDssSimulation job
        job_dir : str
            Job output directory
        results : PyDssResults
            Results object for the job's PyDSS project

        """
        self._job = job
        self._job_dir = job_dir
        self._pydss_results = pydss_results

    def get_component_costs(self):
        """Get the new and upgrade line and transformer costs.

        Returns
        -------
        list
            Example output::

                [{'name': 'Transformer.1234,
                  'new_equipment_cost': 0,
                  'upgraded_equipment_cost': 11328.999999999987,
                  'type': 'transformer'}]

        """
        components = []
        line_costs_file = os.path.join(
            self._job_dir,
            "post_process",
            "detailed_line_upgrade_costs.csv",
        )
        t_costs_file = os.path.join(
            self._job_dir,
            "post_process",
            "detailed_transformer_costs.csv",
        )

        components += self._get_component_costs(line_costs_file, "line")
        components += self._get_component_costs(t_costs_file, "transformer")
        return components

    @staticmethod
    def _get_component_costs(filename, component_type):
        components = []
        components_df = pd.read_csv(filename)
        if components_df.empty:
            return components

        components_df.drop("Unnamed: 0", axis=1, inplace=True)
        components_df.columns = [
            "name", "new_equipment_cost", "upgraded_equipment_cost"
        ]
        for _, row in components_df.iterrows():
            data = row.to_dict()
            data["type"] = component_type
            components.append(data)

        return components

    def get_new_and_upgraded_components(self):
        """Get information on new and upgraded lines and transformers.

        Returns
        -------
        dict
            Example output::

                {'upgraded_transformers': [
                    {'transformer': 'Transformer.1234',
                     'original_kva': 37.6,
                     'new_kva': '62.4'},
                    ],
                 'new_transformers': [],
                 'upgraded_lines': [],
                 'new_lines': []}

        """
        data = json.loads(self._pydss_results.read_file(self.UPGRADES_FILE))

        return {
            "upgraded_transformers": self._get_upgraded_transformers(data),
            "new_transformers": self._get_new_transformers(data),
            "upgraded_lines": self._get_upgraded_lines(data),
            "new_lines": self._get_new_lines(data),
        }

    @staticmethod
    def _get_upgraded_transformers(data):
        upgraded_transformers = []
        for transformer, t_data in data.items():
            if not transformer.startswith("Transformer"):
                continue
            info = t_data.get("upgrade")
            if info and len(info) >= 2 and info[0] > 0:
                new_kva = info[1][0]["kva"][0]
                orig_kva = t_data["new"][1]["wdg_kvas"][0]
                upgraded_transformers.append(
                    {
                        "transformer": transformer,
                        "original_kva": orig_kva,
                        "new_kva": new_kva,
                    }
                )

        return upgraded_transformers

    @staticmethod
    def _get_new_transformers(data):
        new_transformers = []
        for transformer, t_data in data.items():
            if not transformer.startswith("Transformer"):
                continue
            info = t_data.get("new")
            new_transformer_count = info[0]
            if new_transformer_count > 0:
                new_transformers.append(
                    {
                        "transformer": transformer,
                        "new_transformer_count": new_transformer_count,
                        "kva": info[1]["wdg_kvs"][0],
                    }
                )

        return new_transformers

    @staticmethod
    def _get_upgraded_lines(data):
        upgraded_lines = []
        for line, l_data in data.items():
            if not line.startswith("Line"):
                continue
            info = l_data.get("upgrade")
            if info and len(info) >= 2 and info[0] > 0:
                new_ampacity = info[1]["ampacity"]
                # TODO: how to get original ampacity? This is a guess.
                # Need  data to confirm.
                orig_ampacity = l_data["new"][1]["Ampacity"]
                upgraded_lines.append(
                    {
                        "line": line,
                        "original_ampacity": orig_ampacity,
                        "new_ampacity": new_ampacity,
                    }
                )

        return upgraded_lines

    @staticmethod
    def _get_new_lines(data):
        new_lines = []
        for line, l_data in data.items():
            if not line.startswith("Line"):
                continue
            info = l_data.get("new")
            new_line_count = info[0]
            if new_line_count > 0:
                new_lines.append(
                    {
                        "line": line,
                        "new_line_count": new_line_count,
                        "ampacity": info[1]["Ampacity"],
                    }
                )

        return new_lines


"""
# Example usage. Need to have data in current directory.

if __name__ == "__main__":
    import pprint
    from disco.extensions.pydss_simulation.pydss_configuration import PyDssConfiguration
    from disco.pydss.pydss_analysis import PyDssAnalysis
    from jade.common import JOBS_OUTPUT_DIR


    config = PyDssConfiguration.deserialize("config.json")
    analysis = PyDssAnalysis("output", config)
    name = "1234__3__1.15__1.0__deployment1.dss"
    job = analysis.get_job(name)
    simulation = analysis.get_simulation(name)
    job_dir = os.path.join("output", JOBS_OUTPUT_DIR, job.name)

    pydss_results = analysis.read_results(simulation)
    ucc = UpgradedComponentCollector(job, job_dir, pydss_results)
    print("Component costs:")
    pprint.pprint(ucc.get_component_costs())
    print("Component costs:")
    pprint.pprint(ucc.get_new_and_upgraded_components())
"""
