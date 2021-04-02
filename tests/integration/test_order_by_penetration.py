"""Tests configuration with ordering by penetration level."""


from jade.jobs.job_configuration_factory import create_config_from_file

from jade.utils.subprocess_manager import run_command
from tests.common import *


def test_order_by_penetration(cleanup):
    for option in ("snapshot", "time-series"):
        transform_cmd = f"{TRANSFORM_MODEL} tests/data/smart-ds/substations {option} -F -o {MODELS_DIR}"
        assert run_command(transform_cmd) == 0
        cmd = f"disco config {option} {MODELS_DIR} --order-by-penetration -c {CONFIG_FILE}"
        ret = run_command(cmd)
        assert ret == 0
        config = create_config_from_file(CONFIG_FILE)
        job_mapping = {}
        for job in config.iter_jobs():
            job_mapping[job.name] = job

        for job in config.iter_pydss_simulation_jobs():
            penetration_level = job.model.deployment.project_data.get("penetration_level")
            if penetration_level not in (None, 5):
                blocking_jobs = list(job.get_blocking_jobs())
                assert len(blocking_jobs) == 1
                assert blocking_jobs[0] in job_mapping
                blocking_job = job_mapping[blocking_jobs[0]]
                blocking_pen = blocking_job.model.deployment.project_data.get("penetration_level")
                assert penetration_level > blocking_pen

        cmd = f"disco config {option} {MODELS_DIR} --no-order-by-penetration -c {CONFIG_FILE}"
        ret = run_command(cmd)
        assert ret == 0
        config = create_config_from_file(CONFIG_FILE)
        job_mapping = {}
        for job in config.iter_jobs():
            job_mapping[job.name] = job

        for job in config.iter_pydss_simulation_jobs():
            penetration_level = job.model.deployment.project_data.get("penetration_level")
            if penetration_level is not None:
                assert not job.get_blocking_jobs()
