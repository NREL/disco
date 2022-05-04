"""Tests local execution of a snapshot simulation."""


import os
import shutil

import pandas as pd
import pytest
import toml

from jade.result import ResultsSummary
from jade.utils.subprocess_manager import check_run_command, run_command
from jade.utils.utils import load_data
from disco.enums import SimulationHierarchy
from disco.extensions.pydss_simulation.pydss_configuration import PyDssConfiguration
from disco.extensions.pydss_simulation.pydss_inputs import PyDssInputs
from disco.extensions.pydss_simulation.pydss_simulation import PyDssSimulation
from disco.pydss.pydss_analysis import PyDssAnalysis
from tests.common import *


def test_time_series_basic(cleanup):
    num_jobs = 18
    transform_cmd = f"{TRANSFORM_MODEL} tests/data/smart-ds/substations time-series -F -o {MODELS_DIR}"
    config_cmd = f"{CONFIG_JOBS} time-series {MODELS_DIR} -c {CONFIG_FILE}"
    submit_cmd = f"{SUBMIT_JOBS} {CONFIG_FILE} --output={OUTPUT}"

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


def test_time_series_at_substation(cleanup):
    num_jobs = 18
    transform_cmd = f"{TRANSFORM_MODEL} tests/data/smart-ds/substations time-series -c -F -o {MODELS_DIR} --hierarchy=substation"
    config_cmd = f"{CONFIG_JOBS} time-series {MODELS_DIR} -c {CONFIG_FILE}"
    submit_cmd = f"{SUBMIT_JOBS} {CONFIG_FILE} --output={OUTPUT}"

    assert run_command(transform_cmd) == 0
    assert run_command(config_cmd) == 0
    assert run_command(submit_cmd) == 0
    verify_results(OUTPUT, num_jobs)

    config = PyDssConfiguration.deserialize(CONFIG_FILE)
    jobs = config.list_jobs()
    for job in jobs:
        assert not job.get_blocking_jobs()
    assert not config.list_user_data_keys()
    assert config.get_simulation_hierarchy() == SimulationHierarchy.SUBSTATION

    analysis = PyDssAnalysis(OUTPUT, config)
    result = analysis.list_results()[0]
    pydss_results = analysis.read_results(result.name)
    assert len(pydss_results.scenarios) == 2
    # TODO: configuring at the substation doesn't work with hosting capacity calculations.
    # That is in process of being changed, so we'll delay this test.


def test_time_series_impact_analysis(cleanup):
    num_jobs = 18
    transform_cmd = f"{TRANSFORM_MODEL} tests/data/smart-ds/substations time-series -F -o {MODELS_DIR}"
    config_cmd = f"{CONFIG_JOBS} time-series {MODELS_DIR} -c {CONFIG_FILE}"
    submit_cmd = f"{SUBMIT_JOBS} {CONFIG_FILE} --output={OUTPUT}"

    assert run_command(transform_cmd) == 0
    assert run_command(config_cmd) == 0
    assert run_command(submit_cmd) == 0
    verify_results(OUTPUT, num_jobs)

    config = PyDssConfiguration.deserialize(CONFIG_FILE)
    assert not config.list_user_data_keys()
    jobs = config.list_jobs()
    assert len(jobs) == num_jobs
    assert config.get_simulation_hierarchy() == SimulationHierarchy.FEEDER

    analysis = PyDssAnalysis(OUTPUT, config)
    result = analysis.list_results()[0]
    pydss_results = analysis.read_results(result.name)
    assert len(pydss_results.scenarios) == 2
    
    # Verify Post-process & Results
    postprocess_cmd = f"disco make-summary-tables {OUTPUT}"
    assert run_command(postprocess_cmd) == 0
    for filename in POSTPROCESS_RESULTS:
        summary_table = os.path.join(OUTPUT, filename)
        assert os.path.exists(summary_table)
    
    # TODO: Test impact analysis function after code integrated.


def test_time_series_hosting_capacity(cleanup):
    num_jobs = 18
    transform_cmd = f"{TRANSFORM_MODEL} tests/data/smart-ds/substations time-series -c -F -o {MODELS_DIR}"
    config_cmd = f"{CONFIG_JOBS} time-series {MODELS_DIR} -c {CONFIG_FILE} -v volt_var_ieee_1547_2018_catB"
    submit_cmd = f"{SUBMIT_JOBS} {CONFIG_FILE} --output={OUTPUT} -p 1"

    assert run_command(transform_cmd) == 0
    assert run_command(config_cmd) == 0
    assert run_command(submit_cmd) == 0
    verify_results(OUTPUT, num_jobs)

    config = PyDssConfiguration.deserialize(CONFIG_FILE)
    assert not config.list_user_data_keys()
    jobs = config.list_jobs()
    assert len(jobs) == num_jobs

    analysis = PyDssAnalysis(OUTPUT, config)
    result = analysis.list_results()[1]
    pydss_results = analysis.read_results(result.name)
    assert len(pydss_results.scenarios) == 2
    
    # Ensure that control_mode scenarios have PV controllers defined and pf1 scenarios do not.
    job = config.get_job(result.name)
    assert not job.model.is_base_case
    assert job.model.deployment.pydss_controllers.name == "volt_var_ieee_1547_2018_catB"
    for scenario in pydss_results.scenarios:
        controller_file = f"Scenarios/{scenario.name}/pyControllerList/PvController.toml"
        if "pf1" in scenario.name:
            with pytest.raises(KeyError):
                # The file should not exist.
                pydss_results.read_file(controller_file)
        else:
            assert "control_mode" in scenario.name
            controller_dict = toml.loads(pydss_results.read_file(controller_file))
            assert controller_dict
            assert list(controller_dict.values())

    # Verify Post-process & Results
    postprocess_cmd = f"disco make-summary-tables {OUTPUT}"
    assert run_command(postprocess_cmd) == 0
    for filename in POSTPROCESS_RESULTS:
        summary_table = os.path.join(OUTPUT, filename)
        assert os.path.exists(summary_table)
    
    # TODO: Test hosting capacity function when code integrated.


def test_time_series_config_options(cleanup):
    transform_cmd = f"{TRANSFORM_MODEL} tests/data/smart-ds/substations time-series -F -o {MODELS_DIR}"
    check_run_command(transform_cmd)
    config_cmd = f"{CONFIG_JOBS} time-series {MODELS_DIR} -c {CONFIG_FILE}"

    check_run_command(config_cmd)
    data = load_data(CONFIG_FILE)
    assert "Simulation range" not in data["pydss_inputs"]["Simulation"]["project"]

    skip_night_cmd = config_cmd + " --skip-night"
    check_run_command(skip_night_cmd)
    data = load_data(CONFIG_FILE)
    assert data["pydss_inputs"]["Simulation"]["project"]["simulation_range"] == {
        "start": "06:00:00",
        "end": "18:00:00",
    }

    feeder_losses_cmd = config_cmd + " --feeder-losses=false"
    check_run_command(feeder_losses_cmd)
    assert not get_report_value(load_data(CONFIG_FILE), "Feeder Losses")

    pv_clipping_cmd = config_cmd + " --pv-clipping=true"
    check_run_command(pv_clipping_cmd)
    assert get_report_value(load_data(CONFIG_FILE), "PV Clipping")

    pv_curtailment_cmd = config_cmd + " --pv-curtailment=true"
    check_run_command(pv_curtailment_cmd)
    assert get_report_value(load_data(CONFIG_FILE), "PV Curtailment")

    thermal_metrics_cmd = config_cmd + " --thermal-metrics=false"
    check_run_command(thermal_metrics_cmd)
    assert not get_report_value(load_data(CONFIG_FILE), "Thermal Metrics")

    voltage_metrics_cmd = config_cmd + " --voltage-metrics=false"
    check_run_command(voltage_metrics_cmd)
    assert not get_report_value(load_data(CONFIG_FILE), "Voltage Metrics")


def get_report_value(data, name):
    for report in data["pydss_inputs"]["Simulation"]["reports"]["types"]:
        if report["name"] == name:
            return report["enabled"]

    assert False, name


def verify_results(output_dir, num_jobs):
    result_summary = ResultsSummary(output_dir)
    results = result_summary.list_results()
    assert len(results) == num_jobs
    for result in results:
        assert result.status == "finished"
        assert result.return_code == 0
