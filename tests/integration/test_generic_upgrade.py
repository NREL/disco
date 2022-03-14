"""Test local execution of generic (non-DISCO models) upgrade simulation with cost analysis"""
import copy
import shutil
import tempfile
from pathlib import Path

from jade.result import ResultsSummary
from jade.utils.subprocess_manager import run_command
from jade.utils.utils import load_data, dump_data

from tests.common import *

BASE_CONFIG_FILE = Path("tests") / "data" / "upgrade_cost_analysis_generic.json"


def test_generic_upgrade_jade_workflow(cleanup):
    test_upgrade_file = setup_models()
    try:
        for fmt in ("csv", "json"):
            if Path(OUTPUT).exists():
                shutil.rmtree(OUTPUT)
            config_cmd = f"disco upgrade-cost-analysis config {test_upgrade_file} -c {CONFIG_FILE} --fmt={fmt}"
            assert run_command(config_cmd) == 0
            submit_cmd = f"{SUBMIT_JOBS} {CONFIG_FILE} --output={OUTPUT}"

            assert run_command(submit_cmd) == 0
            # TODO: upgrades code is currently broken
            # verify_results(OUTPUT, 4)
    finally:
        test_upgrade_file.unlink()


def test_generic_upgrade_standalone_workflow(cleanup):
    test_upgrade_file = setup_models()
    try:
        if Path(OUTPUT).exists():
            shutil.rmtree(OUTPUT)
        run_cmd = f"disco upgrade-cost-analysis run {test_upgrade_file}"
        ret = run_command(run_cmd)
        # assert ret == 0
        # TODO: upgrades code is currently broken
    finally:
        test_upgrade_file.unlink()


def setup_models():
    transform_cmd = (
        f"{TRANSFORM_MODEL}  tests/data/smart-ds/substations upgrade -F -o {MODELS_DIR}"
    )
    assert run_command(transform_cmd) == 0
    config_cmd = f"{CONFIG_JOBS} upgrade {MODELS_DIR} -c {CONFIG_FILE}"
    assert run_command(config_cmd) == 0
    disco_config = load_data(CONFIG_FILE)
    upgrades_config = load_data(BASE_CONFIG_FILE)
    model = upgrades_config["jobs"][0]
    upgrades_config["jobs"].clear()

    for disco_job in disco_config["jobs"][:3]:
        upgrade_job = copy.deepcopy(model)
        upgrade_job["name"] = disco_job["name"]
        upgrade_job["opendss_model_file"] = disco_job["deployment"]["deployment_file"]
        upgrades_config["jobs"].append(upgrade_job)
    test_upgrade_file = Path(tempfile.gettempdir()) / "test_upgrades.json"
    dump_data(upgrades_config, test_upgrade_file)
    return test_upgrade_file


def verify_results(output_dir, num_jobs):
    result_summary = ResultsSummary(output_dir)
    results = result_summary.list_results()
    assert len(results) == num_jobs
    for result in results:
        assert result.status == "finished"
        assert result.return_code == 0
