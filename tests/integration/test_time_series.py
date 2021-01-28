"""Tests local execution of a snapshot simulation."""


import os
import shutil

import pandas as pd
import pytest

from jade.result import ResultsSummary
from jade.utils.subprocess_manager import run_command
from disco.extensions.pydss_simulation.pydss_configuration import PyDssConfiguration
from disco.extensions.pydss_simulation.pydss_inputs import PyDssInputs
from disco.extensions.pydss_simulation.pydss_simulation import PyDssSimulation
from disco.pydss.pydss_analysis import PyDssAnalysis
from tests.common import *


def test_time_series_basic(cleanup):
    os.environ["FAKE_HPC_CLUSTER"] = "True"
    num_jobs = 5
    transform_cmd = f"{TRANSFORM_MODEL} tests/data/smart-ds/substations time-series -F -o {MODELS_DIR}"
    config_cmd = f"{CONFIG_JOBS} time-series {MODELS_DIR} -c {CONFIG_FILE}"
    submit_cmd = f"{SUBMIT_JOBS} {CONFIG_FILE} --output={OUTPUT} -p 1"

    assert run_command(transform_cmd) == 0
    assert run_command(config_cmd) == 0
    assert run_command(submit_cmd) == 0
    verify_results(OUTPUT, num_jobs)

    config = PyDssConfiguration.deserialize(CONFIG_FILE)
    jobs = config.list_jobs()
    for job in jobs:
        assert not job.get_blocking_jobs()
    assert not config.list_user_data_keys()

    analysis = PyDssAnalysis(OUTPUT, config)
    result = analysis.list_results()[0]
    pydss_results = analysis.read_results(result.name)
    assert len(pydss_results.scenarios) == 2


def test_time_series_hosting_capacity(cleanup):
    os.environ["FAKE_HPC_CLUSTER"] = "True"
    num_jobs = 7
    transform_cmd = f"{TRANSFORM_MODEL} tests/data/smart-ds/substations time-series -F -o {MODELS_DIR}"
    config_cmd = f"{CONFIG_JOBS} time-series --hosting-capacity {MODELS_DIR} -c {CONFIG_FILE}"
    submit_cmd = f"{SUBMIT_JOBS} {CONFIG_FILE} --output={OUTPUT} -p 1"

    assert run_command(transform_cmd) == 0
    assert run_command(config_cmd) == 0
    assert run_command(submit_cmd) == 0
    verify_results(OUTPUT, num_jobs)

    config = PyDssConfiguration.deserialize(CONFIG_FILE)
    assert config.list_user_data_keys()
    jobs = config.list_jobs()
    for job in jobs[:5]:
        assert not job.get_blocking_jobs()
    assert len(jobs[5].get_blocking_jobs()) == 5
    assert len(jobs[6].get_blocking_jobs()) == 1

    analysis = PyDssAnalysis(OUTPUT, config)
    result = analysis.list_results()[0]
    pydss_results = analysis.read_results(result.name)
    assert len(pydss_results.scenarios) == 2


def test_time_series_impact_analysis(cleanup):
    os.environ["FAKE_HPC_CLUSTER"] = "True"
    num_jobs = 6
    transform_cmd = f"{TRANSFORM_MODEL} tests/data/smart-ds/substations time-series -F -o {MODELS_DIR}"
    config_cmd = f"{CONFIG_JOBS} time-series --impact-analysis {MODELS_DIR} -c {CONFIG_FILE}"
    submit_cmd = f"{SUBMIT_JOBS} {CONFIG_FILE} --output={OUTPUT} -p 1"

    assert run_command(transform_cmd) == 0
    assert run_command(config_cmd) == 0
    assert run_command(submit_cmd) == 0
    verify_results(OUTPUT, num_jobs)

    config = PyDssConfiguration.deserialize(CONFIG_FILE)
    assert config.list_user_data_keys()
    jobs = config.list_jobs()
    for job in jobs[:5]:
        assert not job.get_blocking_jobs()
    assert len(jobs[5].get_blocking_jobs()) == 5

    analysis = PyDssAnalysis(OUTPUT, config)
    result = analysis.list_results()[0]
    pydss_results = analysis.read_results(result.name)
    assert len(pydss_results.scenarios) == 2


def verify_results(output_dir, num_jobs):
    result_summary = ResultsSummary(output_dir)
    results = result_summary.list_results()
    assert len(results) == num_jobs
    for result in results:
        assert result.status == "finished"
        assert result.return_code == 0
