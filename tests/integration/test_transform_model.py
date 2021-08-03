"""Tests local execution of a snapshot simulation."""

from pathlib import Path

from jade.utils.subprocess_manager import check_run_command
from tests.common import *


def test_transform_no_copy_load_shape_data(cleanup):
    transform_cmd = f"{TRANSFORM_MODEL} tests/data/smart-ds/substations time-series -F -o {MODELS_DIR}"
    check_run_command(transform_cmd) == 0
    load_shape_data_files = list(Path(MODELS_DIR).rglob("*.csv"))
    assert not load_shape_data_files


def test_transform_copy_load_shape_data(cleanup):
    transform_cmd = f"{TRANSFORM_MODEL} tests/data/smart-ds/substations time-series -F -o {MODELS_DIR} -c"
    check_run_command(transform_cmd) == 0
    load_shape_data_files = list(Path(MODELS_DIR).rglob("*.csv"))
    assert load_shape_data_files
