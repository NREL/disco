"""Common definitions and functionality for tests"""


CONFIG_FILE = "test-config.json"
PRESCREEN_CONFIG_FILE = "test-prescreen-config.json"
PRESCREEN_FINAL_CONFIG_FILE = "test-prescreen-final-config.json"
CONFIG_JOBS = "disco config"
JOB_OUTPUTS = "job-outputs"
MODELS_DIR = "test-disco-models"
OUTPUT = "test-output"
PIPELINE_CONFIG = "test-pipeline.toml"
POST_PROCESS_OUTPUT_FILE = "post-process.toml"
PRESCREEN_JOBS = "disco prescreen-pv-penetration-levels"
SUBMIT_JOBS = "jade submit-jobs --local"
TRANSFORM_MODEL = "disco transform-model"
TRANSFORM_MODEL_LOG = "transform_model.log"
POSTPROCESS_RESULTS = [
    "feeder_head_table.csv",
    "feeder_losses_table.csv",
    "metadata_table.csv",
    "thermal_metrics_table.csv",
    "voltage_metrics_table.csv"
]
UPGRADE_SUMMARY = "upgrade_summary.json"


def find_non_base_case_job(jobs):
    """Return a job that is not a base case."""
    for job in jobs:
        if job.model.base_case is not None:
            assert not job.model.is_base_case
            return job
    raise Exception("Did not find a non-base-case job")
