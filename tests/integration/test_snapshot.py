"""Integration test for Snapshot Impact Analysis."""

import os
import subprocess

from jade.result import ResultsSummary
from jade.utils.subprocess_manager import run_command
from jade.utils.utils import dump_data, load_data

import disco
from disco.enums import SimulationType
from disco.pydss.common import ConfigType
from disco.pydss.pydss_analysis import PyDssAnalysis
from disco.extensions.pydss_simulation.pydss_configuration import PyDssConfiguration
from tests.common import *

DISCO_PATH = disco.__path__[0]


def test_snapshot_basic(cleanup):
    base = os.path.join(DISCO_PATH, "extensions", "pydss_simulation")
    config_file = CONFIG_FILE
    transform_cmd = f"{TRANSFORM_MODEL} tests/data/smart-ds/substations snapshot -c -F -o {MODELS_DIR}"
    config_cmd = f"{CONFIG_JOBS} snapshot {MODELS_DIR} -c {CONFIG_FILE}"
    submit_cmd = f"{SUBMIT_JOBS} {config_file} -o {OUTPUT}"

    assert run_command(transform_cmd) == 0
    assert run_command(config_cmd) == 0
    assert run_command(submit_cmd) == 0

    config = PyDssConfiguration.deserialize(CONFIG_FILE)
    jobs = config.list_jobs()
    for job in jobs:
        assert not job.get_blocking_jobs()
    assert not config.list_user_data_keys()

    analysis = PyDssAnalysis(OUTPUT, config)
    results = analysis.list_results()
    assert len(results) == 18
    result = results[0]
    pydss_results = analysis.read_results(result.name)
    assert len(pydss_results.scenarios) == 1


def test_snapshot_basic_with_loadshape_no_pf1(cleanup):
    base = os.path.join(DISCO_PATH, "extensions", "pydss_simulation")
    config_file = CONFIG_FILE
    transform_cmd = f"{TRANSFORM_MODEL} tests/data/smart-ds/substations snapshot -F -o {MODELS_DIR}"
    config_cmd = f"{CONFIG_JOBS} snapshot {MODELS_DIR} --with-loadshape --no-pf1 -c {CONFIG_FILE}"
    submit_cmd = f"{SUBMIT_JOBS} {config_file} -o {OUTPUT}"

    assert run_command(transform_cmd) == 0
    assert run_command(config_cmd) == 0
    assert run_command(submit_cmd) == 0

    config = PyDssConfiguration.deserialize(CONFIG_FILE)
    jobs = config.list_jobs()
    for job in jobs:
        assert job.model.simulation.simulation_type == SimulationType.QSTS
        timedelta = (job.model.simulation.end_time - job.model.simulation.start_time).total_seconds()
        assert timedelta == job.model.simulation.step_resolution
        assert not job.get_blocking_jobs()
    assert not config.list_user_data_keys()
    for scenario in config._pydss_inputs[ConfigType.SCENARIOS]:
        assert not scenario["exports"]

    analysis = PyDssAnalysis(OUTPUT, config)
    results = analysis.list_results()
    assert len(results) == 18
    result = results[0]
    pydss_results = analysis.read_results(result.name)
    assert len(pydss_results.scenarios) == 1
    assert pydss_results.scenarios[0].name == "control_mode"


def test_snapshot_impact_analysis(cleanup):
    """For each job, gather outputs and generate desired output CSV files."""
    base = os.path.join(DISCO_PATH, "extensions", "pydss_simulation")
    config_file = CONFIG_FILE
    transform_cmd = f"{TRANSFORM_MODEL} tests/data/smart-ds/substations snapshot -F -o {MODELS_DIR}"
    config_cmd = f"{CONFIG_JOBS} snapshot {MODELS_DIR} -c {CONFIG_FILE}"
    submit_cmd = f"{SUBMIT_JOBS} {config_file} -o {OUTPUT}"

    assert run_command(transform_cmd) == 0
    assert run_command(config_cmd) == 0
    assert run_command(submit_cmd) == 0

    config = PyDssConfiguration.deserialize(CONFIG_FILE)
    jobs = config.list_jobs()
    assert len(jobs) == 18
    assert not config.list_user_data_keys()

    # Verify Post-process & Results
    postprocess_cmd = f"disco-internal make-summary-tables {OUTPUT}"
    assert run_command(postprocess_cmd) == 0
    for filename in POSTPROCESS_RESULTS:
        summary_table = os.path.join(OUTPUT, filename)
        assert os.path.exists(summary_table)
    
    # TODO: Test impact analysis function after code integrated.


def test_snapshot_hosting_capacity(cleanup):
    """For each job, gather outputs and generate desired output CSV files."""
    base = os.path.join(DISCO_PATH, "extensions", "pydss_simulation")
    config_file = CONFIG_FILE
    transform_cmd = f"{TRANSFORM_MODEL} tests/data/smart-ds/substations snapshot -F -o {MODELS_DIR}"
    config_cmd = f"{CONFIG_JOBS} snapshot {MODELS_DIR} -c {CONFIG_FILE}"
    submit_cmd = f"{SUBMIT_JOBS} {config_file} -o {OUTPUT} -p1"

    assert run_command(transform_cmd) == 0
    assert run_command(config_cmd) == 0
    assert run_command(submit_cmd) == 0

    config = PyDssConfiguration.deserialize(CONFIG_FILE)
    jobs = config.list_jobs()
    assert len(jobs) == 18
    assert not config.list_user_data_keys()

    # Verify Post-process & Results
    postprocess_cmd = f"disco-internal make-summary-tables {OUTPUT}"
    assert run_command(postprocess_cmd) == 0
    for filename in POSTPROCESS_RESULTS:
        summary_table = os.path.join(OUTPUT, filename)
        assert os.path.exists(summary_table)
    
    # TODO: Test hosting capacity function when code integrated.
