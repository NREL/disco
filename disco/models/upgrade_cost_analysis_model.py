"""Data model for Upgrade Cost Analysis"""

from datetime import datetime
from typing import List, Optional, Union

from pydantic.fields import Field
from pydantic.types import DirectoryPath, FilePath

from .base import (
    DiscoBaseModel,
    OpenDssDeploymentModel,
    SimulationModel,
    BaseAnalysisModel
)


class ThermalUpgradeOverridesModel(DiscoBaseModel):
    """Thermal Upgrade Override Parameters"""

    line_loading_limit: Optional[float] = Field(
        title="line_loading_limit",
        default=1.0,
        description=(
            "Line loading threshold above which violations are counted, "
            "1=100% of rated line capacity"
        ),
        ge=0.0,
        unit="1",
    )
    dt_loading_limit: Optional[float] = Field(
        title="dt_loading_limit",
        default=1.0,
        description=(
            "Xfmr loading threshold above which violations are counted, "
            "1=100% of rated xfmr capacity"
        ),
        ge=0.0,
        unit="1",
    )
    line_safety_margin: Optional[float] = Field(
        title="line_safety_margin",
        default=1.5,
        description=(
            "All upgraded lines will have this buffer, 1.5 means loading of "
            "upgraded lines would be (line loading limit)/(line_safety_margin) "
            "say 1/1.5 = 66.67%"
        ),
        ge=0.0,
        unit=1,
    )
    xfmr_safety_margin: Optional[float] = Field(
        title="xfmr_safety_margin",
        default=1.5,
        description=(
            "All upgraded xfmr will have this buffer, 1.5 means loading of "
            "upgraded xfmrs would be (xfmr loading limit)/(xfmr_safety_margin) "
            "say 1/1.5 = 66.67%"
        ),
        ge=0.0,
        unit=1,
    )
    nominal_voltage: Optional[int] = Field(
        title="nominal_voltage",
        default=120,
        description="Feeder nominal voltage almost always 120V for US feeders",
    )
    max_iterations: Optional[int] = Field(
        title="max_iterations",
        default=20,
        description="Max thermal upgrade iterations",
    )
    create_upgrade_plots: Optional[bool] = Field(
        title="create_upgrade_plots",
        default=False,
        description=(
            "Use 'true' if output plots such as initial and final loading "
            "comparisons are required, only use if bus coordiantes are available."
        ),
    )
    tps_to_test: Optional[Union[List[float], List[datetime]]] = Field(
        title="tps_to_test",
        default=[0.2, 1.8, 0.1, 0.9],
        description=(
            "Load multipliers for determining upgrades, "
            "(min load no PV, max load no PV, min load rated PV, max load rated PV)"
        ),
    )
    create_upgrades_library: Optional[bool] = Field(
        title="create_upgrades_library",
        default=True,
        description=(
            "Use only if external upgrades library is not available, "
            "will create upgrades library from the feeder model itself."
        ),
    )
    upgrade_library_path: Optional[DirectoryPath] = Field(
        title="upgrade_library_path",
        default="",
        description=(
            "Specify path to upgrades library, library should be created "
            "in a particular format using script in postprocess scripts folder."
        ),
    )

    class Config:
        title = "Themal Upgrade Overrides"
        validate_assignment = True


class VoltageUpgradeOverridesModel(DiscoBaseModel):
    """Voltage Upgrade Override Parameters"""

    target_v: Optional[float] = Field(
        title="target_v",
        default=1,
        description=(
            "p.u. value around which control set points are chosen, "
            "only experienced users should change this parameter."
        ),
    )
    initial_voltage_upper_limit: Optional[float] = Field(
        title="initial_voltage_upper_limit",
        default=1.0583,
        description="The initial voltage upper threshold p.u."
    )
    initial_voltage_lower_limit: Optional[float] = Field(
        title="initial_voltage_lower_limit",
        default=0.9167,
        description="The initial voltage lower threshold p.u."
    )
    final_voltage_upper_limit: Optional[float] = Field(
        title="final_voltage_upper_limit",
        default=1.05,
        description="The final voltage upper threshold p.u."
    )
    final_voltage_lower_limit: Optional[float] = Field(
        title="final_voltage_lower_limit",
        default=0.95,
        description="The final voltage lower threshold p.u."
    )
    nominal_voltage: Optional[int] = Field(
        title="nominal_voltage",
        default=120,
        description="Almost always 120 for US feeders.",
    )
    nominal_pu_voltage: Optional[int] = Field(
        alias="nominal pu voltage",
        default=1,
        description="Almost always 1 only experienced users may edit it.",
    )
    tps_to_test: Optional[Union[List[float], List[datetime]]] = Field(
        title="tps_to_test",
        default=[0.2, 1.3, 0.1, 0.9],
        description=(
            "Load multipliers for determining upgrades, "
            "(min load no PV, max load no PV, min load rated PV, max load rated PV)"
        ),
    )
    create_topology_plots: Optional[bool] = Field(
        title="create_topology_plots",
        default=False,
        description=(
            "Use 'true' if output plots such as initial and final loading "
            "comparisons are required, only use if bus coordiantes are available."
        ),
    )
    cap_sweep_voltage_gap: Optional[float] = Field(
        title="cap_sweep_voltage_gap",
        default=1,
        description=(
            "Difference between cap ON and OFF voltages, 1 means set points "
            "sweep would start from 119.5-120.5, 119-121 and so on until "
            "voltage thresholds are reached."
        ),
    )
    reg_control_bands: Optional[List[int]] = Field(
        title="reg_control_bands",
        default=[1, 2],
        description="Define the band property in regcontrol object in OpenDSS.",
    )
    reg_v_delta: Optional[float] = Field(
        title="reg_v_delta",
        default=0.5,
        description=(
            "RReg control 'vreg' property sweep step, 0.5 means set points "
            "tested would be 114, 114.5...,126 for ANSI A thresholds."
        ),
    )
    max_regulators: Optional[int] = Field(
        title="max_regulators",
        default=4,
        discription="Maximum regulators to be placed in a feeder.",
        example=4,
    )
    use_ltc_placement: Optional[bool] = Field(
        title="use_ltc_placement",
        default=True,
        description="Whether or not substation LTC has to be added.",
    )

    class Config:
        title = "VoltageUpgradwOverridesModel"
        validate_assignment = True


class UpgradeOverridesModel(DiscoBaseModel):
    """Upgrade Override Parameters"""

    thermal_upgrade_overrides: ThermalUpgradeOverridesModel = Field(
        title="thermal_upgrade_overrides",
        default={},
        description="Override default thermal upgrade parameter values.",
    )
    voltage_upgrade_overrides: VoltageUpgradeOverridesModel = Field(
        title="voltage_upgrade_overrides",
        default={},
        description="To override default voltage upgrade parameter values.",
    )

    class Config:
        title = "UpgradeOverridesModel"
        validate_assignment = True


class UpgradeCostAnalysisModel(BaseAnalysisModel):
    """A data model for ensuring inputs configuration of simulation jobs."""
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
    upgrade_paths: Optional[List[FilePath]] = Field(
        title="upgrade_paths",
        default=[],
        description="A list of .dss files used for upgrade.",
    )
    upgrade_overrides: Optional[UpgradeOverridesModel] = Field(
        title="upgrade_overrides",
        default={},
        description="Override default thermal/voltage upgrade parameters.",
    )

    class Config:
        title = "UpgradeCostAnalysisModel"
        anystr_strip_whitespace = True
        validate_assignment = True
