"""Integration test for Snapshot Impact Analysis."""

import os
import subprocess

from jade.result import ResultsSummary
from jade.utils.subprocess_manager import run_command
from jade.utils.utils import load_data

from disco.extensions.pydss_simulation.pydss_configuration import PyDssConfiguration
import disco
from tests.common import *


POST_PROCESS_RESULT = "snapshot-impact-analysis-batch-post-process.csv"
DISCO_PATH = disco.__path__[0]


def test_snapshot_impact_analysis(cleanup):
    """For each job, gather outputs and generate desired output CSV files."""
    base = os.path.join(DISCO_PATH, "extensions", "pydss_simulation")
    config_file = PIPELINE_CONFIG
    transform_cmd = f"{TRANSFORM_MODEL} tests/data/smart-ds/substations snapshot-impact-analysis -F -o {MODELS_DIR}"
    create_sim_config = f"disco config snapshot-impact-analysis {MODELS_DIR} -c config-stage1.json"
    create_merge_config = os.path.join(base, "create_merge_feeders_results.py")
    pipeline_cmd = f"jade pipeline create \"{create_sim_config}\" {create_merge_config} -c {config_file}"
    submit_cmd = f"jade pipeline submit {config_file} -o {OUTPUT}"

    assert run_command(transform_cmd) == 0
    subprocess.check_call(pipeline_cmd, shell=True)
    # something gets broken with quotes
    #assert run_command(pipeline_cmd) == 0

    # check result
    data = load_data(config_file)
    assert len(data["stages"]) == 2

    assert run_command(submit_cmd) == 0

    # Verify Results
    stage1_output_path = os.path.join(OUTPUT, 'output-stage1')
    result_summary = ResultsSummary(stage1_output_path)
    results = result_summary.list_results()

    assert len(results) == 4
    for result in results:
        assert result.status == "finished"
        assert result.return_code == 0

    stage1_config_file = os.path.join(stage1_output_path, 'config.json')
    config = PyDssConfiguration.deserialize(stage1_config_file)

    # Verify Post-process Results
    for feeder in config.list_feeders():
        post_process_result = os.path.join(OUTPUT, 'output-stage2', JOB_OUTPUTS,
                                           f"{feeder}-{POST_PROCESS_RESULT}")
        assert os.path.exists(post_process_result)
