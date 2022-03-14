import json
from pathlib import Path

import pytest

from jade.utils.utils import load_data, dump_data
from disco.models.upgrade_cost_analysis_generic_model import UpgradeCostAnalysisSimulationModel


def test_model_load():
    config_file = Path("tests") / "data" / "upgrade_cost_analysis_generic.json"
    model = UpgradeCostAnalysisSimulationModel.from_file(config_file)
    assert model.has_pydss_controllers()


def test_invalid_model_load():
    config_file = Path("tests") / "data" / "upgrade_cost_analysis_generic.json"
    config = load_data(config_file)
    config["jobs"].append(config["jobs"][0])
    with pytest.raises(ValueError):
        UpgradeCostAnalysisSimulationModel(**config)


def test_generate_schema():
    schema = json.loads(UpgradeCostAnalysisSimulationModel.schema_json(indent=2))
    assert schema["title"] == "UpgradeCostAnalysisSimulationModel"
