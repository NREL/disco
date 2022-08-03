
import os
import shutil
import pytest


from tests.common import *


@pytest.fixture
def cleanup():
    def delete_files():
        for path in (
            PIPELINE_CONFIG,
            CONFIG_FILE,
            PRESCREEN_CONFIG_FILE,
            PRESCREEN_FINAL_CONFIG_FILE,
            TRANSFORM_MODEL_LOG,
            UPGRADE_SUMMARY
        ):
            if os.path.exists(path):
                os.remove(path)
        for path in (OUTPUT, MODELS_DIR):
            if os.path.exists(path):
                shutil.rmtree(path)

    delete_files()
    yield
    delete_files()


@pytest.fixture
def test_data_dir():
    """The path to the directory that contains the fixture data"""
    return os.path.join(os.path.dirname(__file__), "data")


@pytest.fixture
def smart_ds_substations():
    """The path to the tests data - smart-ds substations"""
    return os.path.join(
        os.path.dirname(__file__), "data", "smart-ds", "substations"
    )
