"""Test local execution of upgrade simulation with cost analysis"""
import os

from jade.jobs.job_configuration_factory import create_config_from_file
from jade.result import ResultsSummary
from jade.utils.subprocess_manager import run_command

from tests.common import *

def test_upgrade(cleanup):
    transform_cmd = f"{TRANSFORM_MODEL}  tests/data/smart-ds/substations upgrade -x -F -o {MODELS_DIR}"
    config_cmd = f"{CONFIG_JOBS} upgrade {MODELS_DIR} -c {CONFIG_FILE}"
    submit_cmd = f"{SUBMIT_JOBS} {CONFIG_FILE} --output={OUTPUT}"

    # Run simulation
    assert run_command(transform_cmd) == 0
    assert run_command(config_cmd) == 0
    assert run_command(submit_cmd) == 0
    verify_results(OUTPUT, 16)

    config = create_config_from_file(CONFIG_FILE)
    for job in config.iter_jobs():
        print(job)

    # Run postprocess for aggregration
    postprocess_cmd = f"disco-internal make-upgrade-tables {OUTPUT}"
    assert run_command(postprocess_cmd) == 0
    for name in [TOTAL_UPGRADE_COSTS, UPGRADE_SUMMARY]:
        filename = os.path.join(OUTPUT, name)
        assert os.path.exists(filename)


def verify_results(output_dir, num_jobs):
    result_summary = ResultsSummary(output_dir)
    results = result_summary.list_results()
    assert len(results) == num_jobs
    for result in results:
        assert result.status == "finished"
        assert result.return_code == 0
