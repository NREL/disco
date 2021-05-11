"""Tests local execution of a snapshot simulation."""

import copy
import glob
from pathlib import Path

from jade.result import ResultsSummary
from jade.utils.subprocess_manager import run_command
from jade.utils.utils import load_data, dump_data

from disco.pydss.prescreen_pv_penetration_levels import PRESCREEN_JOBS_OUTPUT
from tests.common import *


def test_prescreen_pv_penetration_levels(cleanup):
    num_jobs = 8
    src_data = "tests/data/smart-ds/substations"
    test_fail = {
        "substation": "p1uhs23_1247",
        "feeder": "p1udt21301",
        "placement": "close",
        "sample": 2,
    }
    for hierarchy in ("feeder", "substation"):
        transform_cmd = f"{TRANSFORM_MODEL} {src_data} time-series -F -o {MODELS_DIR} --hierarchy={hierarchy} --force"
        config_cmd = f"{CONFIG_JOBS} time-series {MODELS_DIR} -c {CONFIG_FILE}"
        prescreen_cmd = f"{PRESCREEN_JOBS} {CONFIG_FILE} create -c {PRESCREEN_CONFIG_FILE}"
        submit_cmd = f"{SUBMIT_JOBS} {PRESCREEN_CONFIG_FILE} --output={OUTPUT} --force"
        filter_cmd = f"{PRESCREEN_JOBS} {CONFIG_FILE} filter-config -c {PRESCREEN_FINAL_CONFIG_FILE} {OUTPUT}"

        assert run_command(transform_cmd) == 0
        assert run_command(config_cmd) == 0
        assert run_command(prescreen_cmd) == 0
        assert run_command(submit_cmd) == 0
        verify_results(OUTPUT, num_jobs)

        # All of these test jobs pass. Inject one failure.
        data = copy.deepcopy(test_fail)
        if hierarchy == "substation":
            data["feeder"] = "None"
        base_name = "__".join((str(x) for x in data.values())) + ".toml"
        filename = Path(OUTPUT) / PRESCREEN_JOBS_OUTPUT / base_name

        results = load_data(filename)
        assert results["highest_passing_penetration_level"] == 15
        results["highest_passing_penetration_level"] = 5
        dump_data(results, filename)
        orig_num_jobs = len(load_data(CONFIG_FILE)["jobs"])
        assert run_command(filter_cmd) == 0
        new_num_jobs = len(load_data(PRESCREEN_FINAL_CONFIG_FILE)["jobs"])
        assert new_num_jobs == orig_num_jobs - 1


def verify_results(output_dir, num_jobs):
    result_summary = ResultsSummary(output_dir)
    results = result_summary.list_results()
    assert len(results) == num_jobs
    for result in results:
        assert result.status == "finished"
        assert result.return_code == 0

    levels_path = f"{output_dir}/{PRESCREEN_JOBS_OUTPUT}/*.toml"
    files = glob.glob(levels_path)
    assert len(files) == num_jobs
    for filename in files:
        data = load_data(filename)
        assert data["highest_passing_penetration_level"] == 15
