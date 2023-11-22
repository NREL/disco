from typing import Optional

from pydantic.v1 import Field

from disco.models.base import (
    BaseAnalysisModel,
    DiscoBaseModel,
    OpenDssDeploymentModel,
    SimulationModel
)


class ParameterOverridesModel(DiscoBaseModel):
    # TODO: Add upgrade parameters
    class Config:
        title = "ParameterOverridesModel"
        validate_assignment = True


class UpgradeCostAnalysisModel(BaseAnalysisModel):
    deployment: OpenDssDeploymentModel = Field(
        title="deployment",
        description="PV deployment on feeder",
        default=None,
    )
    simulation: SimulationModel = Field(
        title="simulation",
        description="Simulation parameters with PV deployment",
        default=None,
    )
    parameter_overrides: Optional[ParameterOverridesModel] = Field(
        title="parameter_overrides",
        default={},
        description="Override default upgrade parameters on job level",
    )
    
    class Config:
        title = "UpgradeCostAnalysisModel"
        anystr_strip_whitespace = True
        validate_assignment = True
