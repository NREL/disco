"""
Goal is to take the PyDSS hd5 store the compute hosting capacity analysis
"""

# python standard imports
from pathlib import Path
import os
import json
import copy
import logging
from textwrap import indent

# python third-party imports
import numpy as np

# python internal imports
from PyDSS.pydss_results import PyDssResults
from jade.common import CONFIG_FILE, JOBS_OUTPUT_DIR
from jade.jobs.job_configuration_factory import create_config_from_file
from jade.jobs.results_aggregator import ResultsAggregator
from jade.utils.utils import dump_data, load_data
from jade.loggers import setup_logging


# setup logger
logger = logging.getLogger(__name__)


def compute_hosting_capacity_for_pydss(
    output_dir: str,
    output_json: str = "./hosting-capacity-from-pydss-results.json",
    threshold_voltage: float = 1.05,
    threshold_overloading: float = 100.0,
):

    setup_logging(__name__, None, console_level=logging.INFO, packages=["disco"])

    output_path = Path(output_dir)
    orig = Path(os.getcwd())
    try:
        os.chdir(output_path.parent)
        _compute_hosting_capacity_for_pydss(
            output_path, output_json, threshold_voltage, threshold_overloading
        )
    finally:
        os.chdir(orig)


def _compute_hosting_capacity_for_pydss(
    output_path, output_json: str, threshold_voltage: float, threshold_overloading
):

    """Parse all the jobs in JADE output directory and compute hosting capacity for each
    feeders by scenario and by time step taking pydss results"""

    config = create_config_from_file(output_path / CONFIG_FILE)
    jobs = []
    results = ResultsAggregator.list_results(output_path)
    result_lookup = {x.name: x for x in results}
    for job in config.iter_pydss_simulation_jobs():
        if job.name not in result_lookup:
            logger.info("Skip missing job %s", job.name)
            continue
        if result_lookup[job.name].return_code != 0:
            logger.info("Skip failed job %s", job.name)
            continue
        if job.model.is_base_case:
            continue
        jobs.append(job)

    # Container for storing max voltage and overloadings
    violation_container = []

    # Loop through all the jobs
    for job in jobs:

        job_path = output_path / JOBS_OUTPUT_DIR / job.name / "pydss_project"
        results = PyDssResults(job_path)

        substation = job.model.deployment.substation
        sample = job.model.deployment.project_data.get("sample", "-1")
        placement = job.model.deployment.project_data.get("placement", "-1")
        pen_level = job.model.deployment.project_data.get("penetration_level", "-1")

        for scenario in results.scenarios:

            df_buses = scenario.get_full_dataframe("Circuits", "AllBusMagPu")
            df_loadings = scenario.get_full_dataframe("CktElement", "ExportLoadingsMetric")

            violations = []
            max_thermal_dict = df_loadings.max(axis=1).to_dict()
            for key, value in df_buses.max(axis=1).to_dict().items():

                violations.append(
                    {
                        "timestamp": key.strftime("%Y-%m-%d %H:%M:%S"),
                        "max_voltage": value,
                        "penetration_level": float(pen_level),
                        "max_loading": max_thermal_dict[key],
                    }
                )

            violation_container.append(
                {
                    "substation": substation,
                    "scenario": scenario._name,
                    "placement_sample": str(placement) + "__" + str(sample),
                    "violations": violations,
                }
            )

    hosting_capacity_result = []
    substations = set(map(lambda x: x["substation"], violation_container))

    for substation in substations:

        substation_violations = [
            el for el in violation_container if el["substation"] == substation
        ]

        scenarios = set(map(lambda x: x["scenario"], substation_violations))
        for scenario in scenarios:

            scenario_violations = [
                el["violations"] for el in substation_violations if el["scenario"] == scenario
            ]

            timestamps = set(map(lambda x: x["timestamp"], scenario_violations[0]))

            for timestamp in timestamps:

                timestamp_violations = [
                    el
                    for sub_array in scenario_violations
                    for el in sub_array
                    if el["timestamp"] == timestamp
                ]

                max_voltages = np.array([el["max_voltage"] for el in timestamp_violations])
                max_loadings = np.array([el["max_loading"] for el in timestamp_violations])
                pen_levels = np.array([el["penetration_level"] for el in timestamp_violations])

                v_hc = (
                    np.max(pen_levels[max_voltages < threshold_voltage])
                    if len(pen_levels[max_voltages < threshold_voltage])
                    else None
                )

                t_hc = (
                    np.max(pen_levels[max_loadings < threshold_overloading])
                    if len(pen_levels[max_loadings < threshold_overloading])
                    else None
                )

                vt_hc = (
                    min(filter(lambda x: x is not None, [v_hc, t_hc]))
                    if any([v_hc, t_hc])
                    else None
                )

                hosting_capacity_result.append(
                    {
                        "substation": substation,
                        "scenario": scenario,
                        "timestamp": timestamp,
                        "hosting_capacity": {
                            "overvoltage_hc": v_hc,
                            "thermal_hc": t_hc,
                            "overvoltage_thermal_hc": vt_hc,
                        },
                    }
                )

    dump_data({"hc_result": hosting_capacity_result}, output_json, indent=2)
    logger.info(f"Written file named {output_json}")


if __name__ == "__main__":
    pass
