"""Tests execution of a generic power flow simulations."""

from pathlib import Path

from jade.common import JOBS_OUTPUT_DIR
from jade.utils.subprocess_manager import check_run_command
from jade.utils.utils import load_data
from PyDSS.pydss_results import PyDssResults

from tests.common import *


EXPORTS = """
[Loads.Powers]
store_values_type = "all"

[PVSystems.Powers]
store_values_type = "all"

[Circuits.TotalPower]
store_values_type = "all"

[Circuits.LineLosses]
store_values_type = "all"

[Circuits.Losses]
store_values_type = "all"

[Lines.Currents]
store_values_type = "all"

[Lines.Losses]
store_values_type = "all"

[Lines.Powers]
store_values_type = "all"
"""


def test_generic_snapshot(cleanup):
    num_jobs = 2
    exports_filename = Path("test_exports.toml")
    exports_filename.write_text(EXPORTS)
    config_cmd = (
        f"disco config-generic-models snapshot tests/data/snapshot_generic.json "
        f"-c {CONFIG_FILE} "
        "--store-per-element-data "
        "--with-loadshape "
        "--auto-select-time-points-search-duration-days 1 "
        f"--exports-filename={exports_filename}"
    )
    submit_cmd = f"{SUBMIT_JOBS} {CONFIG_FILE} --output={OUTPUT}"

    try:
        check_run_command(config_cmd)
        config = load_data(CONFIG_FILE)
        assert len(config["jobs"]) == num_jobs
        check_run_command(submit_cmd)
    finally:
        exports_filename.unlink()

    job_names = [x["name"] for x in config["jobs"]]
    for name in job_names:
        results = PyDssResults(Path(OUTPUT) / JOBS_OUTPUT_DIR / name / "pydss_project")
        assert len(results.scenarios) == 8


def test_generic_time_series(cleanup):
    num_jobs = 2
    exports_filename = Path("test_exports.toml")
    exports_filename.write_text(EXPORTS)
    config_cmd = (
        f"disco config-generic-models time-series tests/data/time_series_generic.json "
        f"-c {CONFIG_FILE} "
        "--thermal-metrics=true "
        "--voltage-metrics=true "
        "--store-per-element-data "
        "--store-all-time-points "
        "--export-data-tables "
        f"--exports-filename={exports_filename}"
    )
    submit_cmd = f"{SUBMIT_JOBS} {CONFIG_FILE} --output={OUTPUT}"

    try:
        check_run_command(config_cmd) == 0
        config = load_data(CONFIG_FILE)
        assert len(config["jobs"]) == num_jobs
        check_run_command(submit_cmd) == 0
    finally:
        exports_filename.unlink()

    job_names = [x["name"] for x in config["jobs"]]
    for name in job_names:
        results = PyDssResults(Path(OUTPUT) / JOBS_OUTPUT_DIR / name / "pydss_project")
        assert len(results.scenarios) == 2
        for scenario in results.scenarios:
            df = scenario.get_full_dataframe("PVSystems", "Powers")
            assert len(df) == 96 
            # This should be present because of thermal metrics.
            df = scenario.get_full_dataframe("CktElement", "ExportLoadingsMetric")
            assert len(df) == 96 
            # This should be present because of voltage metrics.
            df = scenario.get_full_dataframe("Buses", "puVmagAngle")
            assert len(df) == 96 

    check_run_command(f"disco make-summary-tables {OUTPUT}")
    thermal_metrics_file = Path(OUTPUT) / "thermal_metrics_table.csv"
    voltage_metrics_file = Path(OUTPUT) / "voltage_metrics_table.csv"
    assert thermal_metrics_file.exists()
    assert voltage_metrics_file.exists()
