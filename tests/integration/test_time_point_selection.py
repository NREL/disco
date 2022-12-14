import fileinput
import math
import shutil
import subprocess
from pathlib import Path

import opendssdirect as dss
import pytest

from disco.preprocess.select_timepoints2 import (
    CriticalCondition,
    DemandCategory,
    GenerationCategory,
    InvalidParameter,
    main,
    get_profile,
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
    connected_profiles = get_connected_load_shape_profiles()
    before = get_pmult_data(connected_profiles)

    new_master = tmp_path / "new_model" / "Master.dss"
    assert new_master.exists()
    dss.Text.Command(f"Clear")
    dss.Text.Command(f"Redirect {new_master}")
    after = get_pmult_data(connected_profiles)
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


def test_invalid_master_file(tmp_path):
    bad_file = MASTER_FILE.parent / (MASTER_FILE.name + ".tmp")
    shutil.copyfile(MASTER_FILE, bad_file)
    with fileinput.input(files=[bad_file], inplace=True) as f:
        for line in f:
            if "Solve" in line:
                print("Solve mode=yearly")
            else:
                print(line, end="")

    categories = {
        "demand": [DemandCategory.LOAD],
        "generation": [GenerationCategory.PV_SYSTEM],
    }
    critical_conditions = [CriticalCondition.MAX_DEMAND, CriticalCondition.MAX_NET_GENERATION]
    try:
        with pytest.raises(InvalidParameter):
            main(
                bad_file,
                categories=categories,
                critical_conditions=critical_conditions,
                destination_dir=tmp_path,
                fix_master_file=False,
            )
        main(
            bad_file,
            categories=categories,
            critical_conditions=critical_conditions,
            destination_dir=tmp_path,
            fix_master_file=True,
        )
    finally:
        if bad_file.exists():
            bad_file.unlink()


def get_connected_load_shape_profiles():
    load_shapes = set()
    for cls in (dss.Loads, dss.PVsystems, dss.Storages):
        flag = cls.First()
        while flag > 0:
            profile = get_profile()
            if profile:
                load_shapes.add(profile)
            flag = cls.Next()

    return load_shapes


def get_pmult_data(connected_profiles):
    flag = dss.LoadShape.First()
    load_shapes = {}
    while flag > 0:
        name = dss.LoadShape.Name()
        if name in connected_profiles:
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
