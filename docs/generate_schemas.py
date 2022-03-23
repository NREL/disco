import sys
from pathlib import Path

import click

from disco.models.upgrade_cost_analysis_generic_model import *


@click.command()
@click.argument("output-dir", callback=lambda _, __, x: Path(x))
def generate_schemas(output_dir):
    output_dir.mkdir(exist_ok=True, parents=True)
    for model in (
        UpgradeCostAnalysisSimulationModel,
        UpgradeSummaryResultsModel,
        # ThermalUpgradeParamsModel,
        # VoltageUpgradeParamsModel,
        # UpgradeCostAnalysisGenericModel,
        # PyDssControllerModels,
        # PvControllerModel,
        # UpgradeResultModel,
        # EquipmentTypeUpgradeCostsModel,
    ):
        filename = output_dir / (model.__name__ + ".json")
        with open(str(filename), "w") as f_out:
            f_out.write(model.schema_json(indent=2))
            print(f"Generated {filename}")


if __name__ == "__main__":
    generate_schemas()
