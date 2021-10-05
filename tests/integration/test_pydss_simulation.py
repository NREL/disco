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


def test_pydss_simulation(cleanup):
    num_jobs = 18
    transform_cmd = f"{TRANSFORM_MODEL} tests/data/smart-ds/substations snapshot -F -o {MODELS_DIR}"
    config_cmd = f"{CONFIG_JOBS} snapshot {MODELS_DIR} -c {CONFIG_FILE}"
    submit_cmd = f"{SUBMIT_JOBS} {CONFIG_FILE} --output={OUTPUT} -p 1"

    assert run_command(transform_cmd) == 0
    assert run_command(config_cmd) == 0
    assert run_command(submit_cmd) == 0
    verify_results(OUTPUT, num_jobs)
    config = PyDssConfiguration.deserialize(CONFIG_FILE)

    analysis = PyDssAnalysis(OUTPUT, config)
    result = analysis.list_results()[0]
    pydss_results = analysis.read_results(result.name)
    assert len(pydss_results.scenarios) == 1
    scenario = pydss_results.scenarios[0]
    lines = scenario.list_element_names("Lines", "Currents")
    df = scenario.get_dataframe("Lines", "Currents", lines[0])
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 1

    element_info_files = scenario.list_element_info_files()
    assert element_info_files
    loads = scenario.read_element_info_file("Loads")
    assert isinstance(loads, pd.DataFrame)
    assert len(loads) > 0

    # TODO: the test circuit doesn't current produce anything
    capacitor_changes = scenario.read_capacitor_changes()
    #assert capacitor_changes

    event_log = scenario.read_event_log()
    #assert event_log


def verify_results(output_dir, num_jobs):
    result_summary = ResultsSummary(output_dir)
    results = result_summary.list_results()
    assert len(results) == num_jobs
    for result in results:
        assert result.status == "finished"
        assert result.return_code == 0


def test_recalculate_kva(cleanup):
    transform_cmd = f"{TRANSFORM_MODEL} tests/data/smart-ds/substations snapshot -F -o {MODELS_DIR}"
    assert run_command(transform_cmd) == 0

    inputs = PyDssInputs(MODELS_DIR)
    key = inputs.list_keys()[0]
    config = PyDssConfiguration()
    job = inputs.get_job(key)
    config.add_job(job)

    simulation = PyDssSimulation.create(config.pydss_inputs,
                                        job,
                                        output="output")

    assert simulation._model.deployment.dc_ac_ratio == 1.15
    assert simulation._model.deployment.kva_to_kw_rating == 1.0
    irradiance_scaling_factor = 100

    # pctPmpp = irradiance_scaling_factor/DC-AC ratio
    # kVA = (Pmpp/DC-AC ratio)*(kVA_to_kW rating)

    for add_pct_pmpp in (True, False):
        simulation._add_pct_pmpp = add_pct_pmpp
        pmpp = 54.440229732964184
        line = "New PVSystem.pv_123456 bus1=123456_xfmr.1.2 phases=2 " \
            "kV=0.20784609690826525 kVA=59.884252706260604 " \
            f"Pmpp={pmpp} conn=wye irradiance=1 yearly=test"
        pct_pmpp = irradiance_scaling_factor / 1.15
        kva = pmpp / simulation._model.deployment.dc_ac_ratio * \
            simulation._model.deployment.kva_to_kw_rating
        expected = "New PVSystem.pv_123456 bus1=123456_xfmr.1.2 " \
            f"phases=2 kV=0.20784609690826525 kVA={kva} " \
            f"Pmpp={pmpp} conn=wye irradiance=1 yearly=test"

        if add_pct_pmpp:
            expected += f" pctPmpp={pct_pmpp}"

        actual = simulation._recalculate_kva(line)

        assert actual == expected + "\n"

        # Add pctPmpp as an existing bad value and ensure it gets fixed.
        line = "New PVSystem.pv_123456 bus1=123456_xfmr.1.2 phases=2 " \
            "kV=0.20784609690826525 kVA=59.884252706260604 " \
            f"Pmpp={pmpp} pctPmpp=99999 conn=wye irradiance=1 " \
            "yearly=test"

        expected = "New PVSystem.pv_123456 bus1=123456_xfmr.1.2 " \
            f"phases=2 kV=0.20784609690826525 kVA={kva} " \
            f"Pmpp={pmpp} pctPmpp={pct_pmpp} conn=wye irradiance=1 " \
            "yearly=test"

        actual = simulation._recalculate_kva(line)

        assert actual == expected + "\n"
