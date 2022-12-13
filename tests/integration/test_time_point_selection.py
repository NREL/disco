import math
import subprocess
from pathlib import Path

import opendssdirect as dss

from disco.preprocess.select_timepoints2 import (
    CriticalCondition,
    DemandCategory,
    GenerationCategory,
    main,
)


MASTER_FILE = (
    Path("tests")
    / "data"
    / "generic-models"
    / "p1uhs23_1247"
    / "p1udt21301"
    / "PVDeployments"
    / "p1uhs23_1247__p1udt21301__random__2__15.dss"
)


def test_time_point_selection(tmp_path):
    categories = {
        "demand": [DemandCategory.LOAD],
        "generation": [GenerationCategory.PV_SYSTEM],
    }
    critical_conditions = [CriticalCondition.MAX_DEMAND, CriticalCondition.MAX_NET_GENERATION]
    (
        bus_data,
        profile_data,
        ag_series,
        head_time_indices,
        critical_time_indices,
        compression_rate,
    ) = main(
        MASTER_FILE,
        categories=categories,
        critical_conditions=critical_conditions,
        destination_dir=tmp_path,
    )
    dss.Text.Command(f"Clear")
    dss.Text.Command(f"Redirect {MASTER_FILE}")
    before = get_pmult_data()

    new_master = tmp_path / "new_model" / "Master.dss"
    assert new_master.exists()
    dss.Text.Command(f"Clear")
    dss.Text.Command(f"Redirect {new_master}")
    after = get_pmult_data()
    assert sorted(before.keys()) == sorted(after.keys())

    count = 0
    for name in before:
        for i, main_index in enumerate(critical_time_indices):
            num_decimals = 2
            val1 = round(before[name][main_index], num_decimals)
            val2 = round(after[name][i], num_decimals)
            assert math.isclose(
                val1, val2
            ), f"Mismatch for LoadShape {name} at time_point={main_index} before={val1} after={val2}"
            count += 1


def get_pmult_data():
    flag = dss.LoadShape.First()
    load_shapes = {}
    while flag > 0:
        name = dss.LoadShape.Name()
        if name != "default":
            assert name not in load_shapes, name
            load_shapes[name] = dss.LoadShape.PMult()
        flag = dss.LoadShape.Next()

    return load_shapes


def test_time_point_selection_cli(tmp_path):
    cmd = [
        "disco",
        "select-time-points",
        str(MASTER_FILE),
        "-d",
        "load",
        "-g",
        "pv_system",
        "-c",
        CriticalCondition.MAX_DEMAND.value,
        "-c",
        CriticalCondition.MIN_DEMAND.value,
        "-c",
        CriticalCondition.MAX_DEMAND.value,
        "-c",
        CriticalCondition.MAX_NET_GENERATION.value,
        "-o",
        str(tmp_path / "output"),
    ]
    subprocess.run(cmd, check=True)
