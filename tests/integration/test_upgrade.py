"""Integration test for Upgrade Cost Anlaysis"""

import os

from jade.result import ResultsSummary
from jade.utils.subprocess_manager import run_command
from jade.utils.utils import load_data

from disco.analysis import GENERIC_COST_DATABASE
from disco.extensions.automated_upgrade_simulation.automated_upgrade_configuration import (
    AutomatedUpgradeConfiguration
)
from tests.common import *

RESULT_FILES = [
    "detailed_line_upgrade_costs.csv",
    "detailed_transformer_costs.csv",
    "summary_of_upgrade_costs.csv"
]


def test_upgrade_cost_analysis(cleanup):
    """Should create post_process results of upgrade cost analysis"""
    # transform-model
    tranform_cmd = (
        f"{TRANSFORM_MODEL} tests/data/smart-ds/substations/ "
        f"upgrade -F -o {MODELS_DIR}"
    )
    assert run_command(tranform_cmd) == 0

    # config simulation
    disco_config_cmd = (
        f"disco config upgrade --sequential-upgrade "
        f"-d {GENERIC_COST_DATABASE} "
        f"-c {CONFIG_FILE} "
        f"-p {UPGRADE_PARAMS} "
        f"{MODELS_DIR}"
    )
    assert run_command(disco_config_cmd) == 0

    # check blocked_by
    config = AutomatedUpgradeConfiguration.deserialize(CONFIG_FILE)
    for job in config.iter_jobs():
        if job.model.job_order == 5:
            assert len(job.model.blocked_by) == 0
        if job.model.job_order == 10:
            assert len(job.model.blocked_by) == 2

    # submit jobs
    submit_cmd = f"{SUBMIT_JOBS} {CONFIG_FILE} -o {OUTPUT}"
    assert run_command(submit_cmd) == 0

    # verify results
    result_summary = ResultsSummary(OUTPUT)
    results = result_summary.list_results()
    assert len(results) == 16

    for result in results:
        assert result.status == "finished"
        assert result.return_code == 0

    # verify post-process results
    job_outputs = os.path.join(OUTPUT, "job-outputs")
    for job_name in os.listdir(job_outputs):
        post_process = os.path.join(job_outputs, job_name, "post_process")
        result_files = os.listdir(post_process)
        assert len(result_files) == 3
        assert set(result_files) == set(RESULT_FILES)
