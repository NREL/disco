import os
import shutil

import pytest

from jade.utils.subprocess_manager import run_command
from jade.utils.utils import load_data, dump_data

# Pre-defined filenames
TEST_TEMPLATE_FILE = "pipeline-test-template.toml"
TEST_PIPELINE_CONFIG_FILE = "pipeline-test.json"
TEST_HPC_CONFIG_FILE = "hpc-test-config.toml"
PRESCREEN_AUTO_CONFIG_TEXT_FILE = "pipeline-prescreen-auto-config.txt"
SIMULATION_AUTO_CONFIG_TEXT_FILE = "pipeline-simulation-auto-config.txt"
POSTPROCESS_AUTO_CONFIG_TEXT_FILE = "pipeline-postprocess-auto-config.txt"
POSTPROCESS_COMMAND_TEXT_FILE = "pipeline-postprocess-command.txt"

# Output filenames/dir after pipeline submit
TRANSFORM_MODEL_LOG_FILE = "transform_model.log"
SIMULATION_CONFIG_FILE = "config.json"
PRESCREEN_CONFIG_FILE = "prescreen-config.json"
FILTERED_CONFIG_FILE = "filtered-config.json"
POSTPROCESS_CONFIG_FILE = "postprocess-config.json"
SNAPSHOT_MODELS_DIR = "snapshot-models"
TIME_SERIES_MODELS_DIR = "time-series-models"
TEST_PIPELINE_OUTPUT = "pipeline-test-output"
TEST_PRECONFIGURED_MODELS = "test-preconfigured-models"

FEEDER_HEAD_TABLE = "feeder_head_table.csv"
FEEDER_LOSSES_TABLE = "feeder_losses_table.csv"
METADATA_TABLE = "metadata_table.csv"
THERMAL_METRICS_TABLE = "thermal_metrics_table.csv"
VOLTAGE_METRICS_TABLE = "voltage_metrics_table.csv"


CONFIG_HPC_COMMAND = (
    f"jade config hpc -a testaccount -p short -t local -w 4:00 "
    f"-c {TEST_HPC_CONFIG_FILE}"
)
MAKE_PIPELINE_CONFIG_COMMAND = (
    f"disco create-pipeline config {TEST_TEMPLATE_FILE} "
    F"-c {TEST_PIPELINE_CONFIG_FILE}"
)


@pytest.fixture
def cleanup():
    """clean up all filenames and dirs generated during tests"""
    def delete_test_results():
        result_files = [
            TEST_TEMPLATE_FILE,
            TEST_PIPELINE_CONFIG_FILE,
            TEST_HPC_CONFIG_FILE,
            PRESCREEN_AUTO_CONFIG_TEXT_FILE,
            SIMULATION_AUTO_CONFIG_TEXT_FILE,
            POSTPROCESS_AUTO_CONFIG_TEXT_FILE,
            POSTPROCESS_COMMAND_TEXT_FILE,
            TRANSFORM_MODEL_LOG_FILE,
            SIMULATION_CONFIG_FILE,
            PRESCREEN_CONFIG_FILE,
            FILTERED_CONFIG_FILE,
            POSTPROCESS_CONFIG_FILE
        ]
        for path in result_files:
            if os.path.exists(path):
                os.remove(path)
        
        result_dirs = [
            SNAPSHOT_MODELS_DIR,
            TIME_SERIES_MODELS_DIR,
            TEST_PIPELINE_OUTPUT,
            TEST_PRECONFIGURED_MODELS
        ]
        for path in result_dirs:
            if os.path.exists(path):
                shutil.rmtree(path)

    delete_test_results()
    yield
    delete_test_results()


def test_source_tree_1_create_snapshot_pipeline_template(smart_ds_substations, cleanup):
    cmd = f"disco create-pipeline template {smart_ds_substations} -t {TEST_TEMPLATE_FILE}"
    ret = ret = run_command(cmd)
    assert ret == 0
    
    assert os.path.exists(TEST_TEMPLATE_FILE)
    data = load_data(TEST_TEMPLATE_FILE)
    
    assert "model" in data
    assert "prescreen" not in data
    assert "simulation" in data
    assert "postprocess" not in data
    
    assert data["inputs"] == smart_ds_substations
    assert data["simulation_type"] == "snapshot"
    assert "analysis_type" not in data
    
    assert "transform-params" in data["model"]
    assert "config-params" in data["simulation"]
    assert "submitter-params" in data["simulation"]


def test_source_tree_1_create_snapshot_pipeline_template__impact_analysis(smart_ds_substations, cleanup):
    cmd = f"disco create-pipeline template {smart_ds_substations} --impact-analysis -t {TEST_TEMPLATE_FILE}"
    ret = ret = run_command(cmd)
    assert ret == 0
    
    assert os.path.exists(TEST_TEMPLATE_FILE)
    data = load_data(TEST_TEMPLATE_FILE)
    
    assert "model" in data
    assert "prescreen" not in data
    assert "simulation" in data
    assert "postprocess" in data
    
    assert data["inputs"] == smart_ds_substations
    assert data["simulation_type"] == "snapshot"
    assert data["analysis_type"] == "impact-analysis"
    
    assert "transform-params" in data["model"]
    
    assert "config-params" in data["simulation"]
    assert "submitter-params" in data["simulation"]
    
    assert "config-params" in data["postprocess"]
    assert "submitter-params" in data["postprocess"]


def test_source_tree_1_create_snapshot_pipeline_template__prescreen(smart_ds_substations, cleanup):
    cmd = f"disco create-pipeline template {smart_ds_substations} --prescreen -t {TEST_TEMPLATE_FILE}"
    ret = run_command(cmd)
    assert ret == 0
    
    assert os.path.exists(TEST_TEMPLATE_FILE)
    data = load_data(TEST_TEMPLATE_FILE)
    assert "prescreen" not in data


def test_source_tree_1_create_snapshot_pipeline_template__preconfigured_models(smart_ds_substations, cleanup):
    cmd1 = f"disco transform-model {smart_ds_substations} snapshot -o {TEST_PRECONFIGURED_MODELS}"
    ret = run_command(cmd1)
    assert ret == 0
    assert os.path.exists(TEST_PRECONFIGURED_MODELS)
    
    cmd = (
        f"disco create-pipeline template {TEST_PRECONFIGURED_MODELS} "
        f"--preconfigured -t {TEST_TEMPLATE_FILE}"
    )
    ret = run_command(cmd)
    assert ret == 0
    
    assert os.path.exists(TEST_TEMPLATE_FILE)
    data = load_data(TEST_TEMPLATE_FILE)
    assert "model" not in data
    assert data["preconfigured"] == True


def test_source_tree_1_config_snapshot_pipeline(smart_ds_substations, cleanup):
    cmd1 = f"disco create-pipeline template {smart_ds_substations} -t {TEST_TEMPLATE_FILE}"
    ret = run_command(cmd1)
    assert ret == 0
    ret = run_command(CONFIG_HPC_COMMAND)
    assert ret == 0
    
    assert os.path.exists(TEST_TEMPLATE_FILE)
    data = load_data(TEST_TEMPLATE_FILE)
    data["simulation"]["submitter-params"]["hpc_config"] = TEST_HPC_CONFIG_FILE
    dump_data(data, TEST_TEMPLATE_FILE)
    
    ret = run_command(MAKE_PIPELINE_CONFIG_COMMAND)
    assert ret == 0
    
    assert os.path.exists(TEST_HPC_CONFIG_FILE)
    assert os.path.exists(TEST_PIPELINE_CONFIG_FILE)
    assert not os.path.exists(PRESCREEN_AUTO_CONFIG_TEXT_FILE)
    assert os.path.exists(SIMULATION_AUTO_CONFIG_TEXT_FILE)
    assert not os.path.exists(POSTPROCESS_AUTO_CONFIG_TEXT_FILE)
    
    pipeline_data = load_data(TEST_PIPELINE_CONFIG_FILE)
    assert len(pipeline_data["stages"]) == 1


def test_source_tree_1_config_snapshot_pipeline__impact_analysis(smart_ds_substations, cleanup):
    cmd1 = (
        f"disco create-pipeline template {smart_ds_substations} "
        f"--impact-analysis -t {TEST_TEMPLATE_FILE}"
    )
    ret = run_command(cmd1)
    assert ret == 0
    ret = run_command(CONFIG_HPC_COMMAND)
    assert ret == 0
    
    assert os.path.exists(TEST_TEMPLATE_FILE)
    data = load_data(TEST_TEMPLATE_FILE)
    data["simulation"]["submitter-params"]["hpc_config"] = TEST_HPC_CONFIG_FILE
    data["postprocess"]["submitter-params"]["hpc_config"] = TEST_HPC_CONFIG_FILE
    dump_data(data, TEST_TEMPLATE_FILE)
    
    ret = run_command(MAKE_PIPELINE_CONFIG_COMMAND)
    assert ret == 0
    
    assert os.path.exists(TEST_HPC_CONFIG_FILE)
    assert os.path.exists(TEST_TEMPLATE_FILE)
    assert os.path.exists(TEST_PIPELINE_CONFIG_FILE)
    assert not os.path.exists(PRESCREEN_AUTO_CONFIG_TEXT_FILE)
    assert os.path.exists(SIMULATION_AUTO_CONFIG_TEXT_FILE)
    assert os.path.exists(POSTPROCESS_AUTO_CONFIG_TEXT_FILE)
    assert os.path.exists(POSTPROCESS_COMMAND_TEXT_FILE)

    pipeline_data = load_data(TEST_PIPELINE_CONFIG_FILE)
    assert len(pipeline_data["stages"]) == 2


def test_source_tree_1_create_time_series_pipeline_template(smart_ds_substations, cleanup):
    cmd = (
        f"disco create-pipeline template {smart_ds_substations} -s time-series "
        f"-t {TEST_TEMPLATE_FILE}"
    )
    ret = run_command(cmd)
    assert ret == 0
    
    assert os.path.exists(TEST_TEMPLATE_FILE)
    data = load_data(TEST_TEMPLATE_FILE)
    
    assert "model" in data
    assert "prescreen" not in data
    assert "simulation" in data
    assert "postprocess" not in data
    
    assert data["inputs"] == smart_ds_substations
    assert data["simulation_type"] == "time-series"
    assert "analysis_type" not in data
    
    assert "transform-params" in data["model"]
    assert "config-params" in data["simulation"]
    assert "submitter-params" in data["simulation"]


def test_source_tree_1_create_time_series_pipeline_template__impact_analysis(smart_ds_substations, cleanup):
    cmd = (
        f"disco create-pipeline template {smart_ds_substations} -s time-series "
        f"--impact-analysis -t {TEST_TEMPLATE_FILE}"
    )
    ret = run_command(cmd)
    assert ret == 0
    
    assert os.path.exists(TEST_TEMPLATE_FILE)
    data = load_data(TEST_TEMPLATE_FILE)
    
    assert "model" in data
    assert "prescreen" not in data
    assert "simulation" in data
    assert "postprocess" in data
    
    assert data["inputs"] == smart_ds_substations
    assert data["simulation_type"] == "time-series"
    assert data["analysis_type"] == "impact-analysis"
    
    assert "transform-params" in data["model"]
    
    assert "config-params" in data["simulation"]
    assert "submitter-params" in data["simulation"]
    
    assert "config-params" in data["postprocess"]
    assert "submitter-params" in data["postprocess"]


def test_source_tree_1_create_time_series_pipeline_template__prescreen(smart_ds_substations, cleanup):
    cmd = (
        f"disco create-pipeline template {smart_ds_substations} -s time-series "
        f"--prescreen -t {TEST_TEMPLATE_FILE}"
    )
    ret = run_command(cmd)
    assert ret == 0
    
    assert os.path.exists(TEST_TEMPLATE_FILE)
    data = load_data(TEST_TEMPLATE_FILE)
    
    assert "model" in data
    assert "prescreen" in data
    assert "simulation" in data
    assert "postprocess" not in data
    
    assert data["inputs"] == smart_ds_substations
    assert data["simulation_type"] == "time-series"
    assert "analysis_type" not in data
    
    assert "transform-params" in data["model"]
    
    assert "config-params" in data["prescreen"]
    assert "prescreen-params" in data["prescreen"]
    assert "submitter-params" in data["prescreen"]
    
    assert "config-params" not in data["simulation"]
    assert "submitter-params" in data["simulation"]


def test_source_tree_1_create_time_series_pipeline_template__prescreen__impact_analysis(smart_ds_substations, cleanup):
    cmd = (
        f"disco create-pipeline template {smart_ds_substations} -s time-series "
        f"--prescreen --impact-analysis -t {TEST_TEMPLATE_FILE}"
    )
    ret = run_command(cmd)
    assert ret == 0
    
    assert os.path.exists(TEST_TEMPLATE_FILE)
    data = load_data(TEST_TEMPLATE_FILE)
    
    assert "model" in data
    assert "prescreen" in data
    assert "simulation" in data
    assert "postprocess" in data
    
    assert data["inputs"] == smart_ds_substations
    assert data["simulation_type"] == "time-series"
    assert data["analysis_type"] == "impact-analysis"
    
    assert "transform-params" in data["model"]
    
    assert "config-params" in data["prescreen"]
    assert "prescreen-params" in data["prescreen"]
    assert "submitter-params" in data["prescreen"]
    
    assert "config-params" not in data["simulation"]
    assert "submitter-params" in data["simulation"]
    
    assert "config-params" in data["postprocess"]
    assert "submitter-params" in data["postprocess"]


def test_source_tree_1_config_time_series_pipeline(smart_ds_substations, cleanup):
    cmd1 = (
        f"disco create-pipeline template {smart_ds_substations} -s time-series "
        f"-t {TEST_TEMPLATE_FILE}"
    )
    ret = run_command(cmd1)
    assert ret == 0
    ret = run_command(CONFIG_HPC_COMMAND)
    assert ret == 0
    
    assert os.path.exists(TEST_TEMPLATE_FILE)
    data = load_data(TEST_TEMPLATE_FILE)
    data["simulation"]["submitter-params"]["hpc_config"] = TEST_HPC_CONFIG_FILE
    dump_data(data, TEST_TEMPLATE_FILE)
    
    ret = run_command(MAKE_PIPELINE_CONFIG_COMMAND)
    
    assert os.path.exists(TEST_HPC_CONFIG_FILE)
    assert os.path.exists(TEST_PIPELINE_CONFIG_FILE)
    assert not os.path.exists(PRESCREEN_AUTO_CONFIG_TEXT_FILE)
    assert os.path.exists(SIMULATION_AUTO_CONFIG_TEXT_FILE)
    assert not os.path.exists(POSTPROCESS_AUTO_CONFIG_TEXT_FILE)
    
    pipeline_data = load_data(TEST_PIPELINE_CONFIG_FILE)
    assert len(pipeline_data["stages"]) == 1


def test_source_tree_1_config_time_series_pipeline__prescreen(smart_ds_substations, cleanup):
    cmd1 = (
        f"disco create-pipeline template {smart_ds_substations} -s time-series "
        f"--prescreen -t {TEST_TEMPLATE_FILE}"
    )
    ret = run_command(cmd1)
    assert ret == 0
    ret = run_command(CONFIG_HPC_COMMAND)
    assert ret == 0
    
    assert os.path.exists(TEST_TEMPLATE_FILE)
    data = load_data(TEST_TEMPLATE_FILE)
    data["prescreen"]["submitter-params"]["hpc_config"] = TEST_HPC_CONFIG_FILE
    data["simulation"]["submitter-params"]["hpc_config"] = TEST_HPC_CONFIG_FILE
    dump_data(data, TEST_TEMPLATE_FILE)
    
    ret = run_command(MAKE_PIPELINE_CONFIG_COMMAND)
    assert ret == 0
    
    assert os.path.exists(TEST_HPC_CONFIG_FILE)
    assert os.path.exists(TEST_PIPELINE_CONFIG_FILE)
    assert os.path.exists(PRESCREEN_AUTO_CONFIG_TEXT_FILE)
    assert os.path.exists(SIMULATION_AUTO_CONFIG_TEXT_FILE)
    assert not os.path.exists(POSTPROCESS_AUTO_CONFIG_TEXT_FILE)
    
    pipeline_data = load_data(TEST_PIPELINE_CONFIG_FILE)
    assert len(pipeline_data["stages"]) == 2


def test_source_tree_1_config_time_series_pipeline__impact_analysis(smart_ds_substations, cleanup):
    cmd1 = (
        f"disco create-pipeline template {smart_ds_substations} -s time-series "
        f"--impact-analysis -t {TEST_TEMPLATE_FILE}"
    )
    ret = run_command(cmd1)
    assert ret == 0
    ret = run_command(CONFIG_HPC_COMMAND)
    assert ret == 0
    
    assert os.path.exists(TEST_TEMPLATE_FILE)
    data = load_data(TEST_TEMPLATE_FILE)
    data["simulation"]["submitter-params"]["hpc_config"] = TEST_HPC_CONFIG_FILE
    data["postprocess"]["submitter-params"]["hpc_config"] = TEST_HPC_CONFIG_FILE
    dump_data(data, TEST_TEMPLATE_FILE)
    
    ret = run_command(MAKE_PIPELINE_CONFIG_COMMAND)
    assert ret == 0
    
    assert os.path.exists(TEST_HPC_CONFIG_FILE)
    assert os.path.exists(TEST_PIPELINE_CONFIG_FILE)
    assert not os.path.exists(PRESCREEN_AUTO_CONFIG_TEXT_FILE)
    assert os.path.exists(SIMULATION_AUTO_CONFIG_TEXT_FILE)
    assert os.path.exists(POSTPROCESS_AUTO_CONFIG_TEXT_FILE)
    
    pipeline_data = load_data(TEST_PIPELINE_CONFIG_FILE)
    assert len(pipeline_data["stages"]) == 2


def test_source_tree_1_config_time_series_pipeline__prescreen__impact_analysis(smart_ds_substations, cleanup):
    cmd1 = (
        f"disco create-pipeline template {smart_ds_substations} -s time-series "
        f"--impact-analysis --prescreen -t {TEST_TEMPLATE_FILE}"
    )
    ret = run_command(cmd1)
    assert ret == 0
    ret = run_command(CONFIG_HPC_COMMAND)
    assert ret == 0
    
    assert os.path.exists(TEST_TEMPLATE_FILE)
    data = load_data(TEST_TEMPLATE_FILE)
    data["prescreen"]["submitter-params"]["hpc_config"] = TEST_HPC_CONFIG_FILE
    data["simulation"]["submitter-params"]["hpc_config"] = TEST_HPC_CONFIG_FILE
    data["postprocess"]["submitter-params"]["hpc_config"] = TEST_HPC_CONFIG_FILE
    dump_data(data, TEST_TEMPLATE_FILE)
    
    ret = run_command(MAKE_PIPELINE_CONFIG_COMMAND)
    assert ret == 0
    
    assert os.path.exists(TEST_HPC_CONFIG_FILE)
    assert os.path.exists(TEST_PIPELINE_CONFIG_FILE)
    assert os.path.exists(PRESCREEN_AUTO_CONFIG_TEXT_FILE)
    assert os.path.exists(SIMULATION_AUTO_CONFIG_TEXT_FILE)
    assert os.path.exists(POSTPROCESS_AUTO_CONFIG_TEXT_FILE)
    
    pipeline_data = load_data(TEST_PIPELINE_CONFIG_FILE)
    assert len(pipeline_data["stages"]) == 3


def test_source_tree_1_snapshot_pipeline_submit__impact_analysis(smart_ds_substations, cleanup):
    cmd1 = (
        f"disco create-pipeline template {smart_ds_substations} "
        f"--impact-analysis -t {TEST_TEMPLATE_FILE}"
    )
    ret = run_command(cmd1)
    assert ret == 0
    ret = run_command(CONFIG_HPC_COMMAND)
    assert ret == 0
    data = load_data(TEST_TEMPLATE_FILE)
    data["simulation"]["submitter-params"]["hpc_config"] = TEST_HPC_CONFIG_FILE
    data["postprocess"]["submitter-params"]["hpc_config"] = TEST_HPC_CONFIG_FILE
    dump_data(data, TEST_TEMPLATE_FILE)
    ret = run_command(MAKE_PIPELINE_CONFIG_COMMAND)
    
    cmd2 = f"jade pipeline submit {TEST_PIPELINE_CONFIG_FILE} -o {TEST_PIPELINE_OUTPUT}"
    ret = run_command(cmd2)
    assert ret == 0
    assert not os.path.exists("snapshot-models")
    assert os.path.exists(os.path.join(TEST_PIPELINE_OUTPUT, "snapshot-models"))
    
    assert os.path.exists(TEST_PIPELINE_OUTPUT)
    assert os.path.exists(os.path.join(TEST_PIPELINE_OUTPUT, "output-stage1"))
    assert os.path.exists(os.path.join(TEST_PIPELINE_OUTPUT, "output-stage2"))
    
    assert os.path.exists(os.path.join(TEST_PIPELINE_OUTPUT, "output-stage1", FEEDER_HEAD_TABLE))
    assert os.path.exists(os.path.join(TEST_PIPELINE_OUTPUT, "output-stage1", FEEDER_LOSSES_TABLE))
    assert os.path.exists(os.path.join(TEST_PIPELINE_OUTPUT, "output-stage1", METADATA_TABLE))
    assert os.path.exists(os.path.join(TEST_PIPELINE_OUTPUT, "output-stage1", THERMAL_METRICS_TABLE))
    assert os.path.exists(os.path.join(TEST_PIPELINE_OUTPUT, "output-stage1", VOLTAGE_METRICS_TABLE))


def test_source_tree_1_time_series_pipeline_submit__prescreen__impact_analysis(smart_ds_substations, cleanup):
    cmd1 = (
        f"disco create-pipeline template {smart_ds_substations} -s time-series "
        f"--impact-analysis --prescreen -t {TEST_TEMPLATE_FILE}"
    )
    ret = run_command(cmd1)
    assert ret == 0
    ret = run_command(CONFIG_HPC_COMMAND)
    assert ret == 0
    data = load_data(TEST_TEMPLATE_FILE)
    data["prescreen"]["submitter-params"]["hpc_config"] = TEST_HPC_CONFIG_FILE
    data["simulation"]["submitter-params"]["hpc_config"] = TEST_HPC_CONFIG_FILE
    data["postprocess"]["submitter-params"]["hpc_config"] = TEST_HPC_CONFIG_FILE
    dump_data(data, TEST_TEMPLATE_FILE)
    ret = run_command(MAKE_PIPELINE_CONFIG_COMMAND)
    
    cmd2 = f"jade pipeline submit {TEST_PIPELINE_CONFIG_FILE} -o {TEST_PIPELINE_OUTPUT}"
    ret = run_command(cmd2)
    assert not os.path.exists("time-series-models")
    assert os.path.exists(os.path.join(TEST_PIPELINE_OUTPUT, "time-series-models"))
    assert ret == 0
    
    assert os.path.exists(TEST_PIPELINE_OUTPUT)
    assert os.path.exists(os.path.join(TEST_PIPELINE_OUTPUT, "output-stage1"))
    assert os.path.exists(os.path.join(TEST_PIPELINE_OUTPUT, "output-stage2"))
    assert os.path.exists(os.path.join(TEST_PIPELINE_OUTPUT, "output-stage3"))

    assert os.path.exists(os.path.join(TEST_PIPELINE_OUTPUT, "output-stage2", FEEDER_HEAD_TABLE))
    assert os.path.exists(os.path.join(TEST_PIPELINE_OUTPUT, "output-stage2", FEEDER_LOSSES_TABLE))
    assert os.path.exists(os.path.join(TEST_PIPELINE_OUTPUT, "output-stage2", METADATA_TABLE))
    assert os.path.exists(os.path.join(TEST_PIPELINE_OUTPUT, "output-stage2", THERMAL_METRICS_TABLE))
    assert os.path.exists(os.path.join(TEST_PIPELINE_OUTPUT, "output-stage2", VOLTAGE_METRICS_TABLE))
