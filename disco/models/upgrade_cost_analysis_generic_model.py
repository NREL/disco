import logging
from pathlib import Path
from typing import Any, List, Optional, Set

from pydantic import BaseModel, Field, root_validator

from jade.utils.utils import load_data
from PyDSS.controllers import PvControllerModel
from disco.models.base import BaseAnalysisModel


logger = logging.getLogger(__name__)


class UpgradeParamsBaseModel(BaseModel):
    """Base model for all upgrade cost analysis parameters"""

    class Config:
        title = "UpgradeParamsBaseModel"
        anystr_strip_whitespace = True
        validate_assignment = True
        validate_all = True
        extra = "forbid"
        use_enum_values = False


class ThermalUpgradeParamsModel(UpgradeParamsBaseModel):
    """Thermal Upgrade Parameters for all jobs in a simulation"""

    transformer_upper_limit: float = Field(
        title="transformer_upper_limit",
        description="Transformer upper limit in per unit (example: 1.25)",
    )
    line_upper_limit: float = Field(
        title="line_upper_limit",
        description="Line upper limit in per unit (example: 1.25)",
    )
    line_design_pu: float = Field(
        title="line_design_pu",
        description="Line design in per unit (example: 0.75)",
    )
    transformer_design_pu: float = Field(
        title="transformer_design_pu",
        description="Transformer design in per unit (example: 0.75)",
    )
    voltage_upper_limit: float = Field(
        title="voltage_upper_limit",
        description="Voltage upper limit in per unit (example: 1.05)",
    )
    voltage_lower_limit: float = Field(
        title="voltage_lower_limit",
        description="Voltage lower limit in per unit (example: 0.95)",
    )
    parallel_xfmrs_limit: Optional[int] = Field(
        title="parallel_xfmrs_limit",
        description="Parallel transformer limit",
        default=4
    )
    parallel_lines_limit: Optional[int] = Field(
        title="parallel_lines_limit",
        description="Parallel lines limit",
        default=4
    )
    upgrade_iteration_threshold: Optional[int] = Field(
        title="upgrade_iteration_threshold",
        description="Upgrade iteration threshold",
        default=5
    )
    timepoint_multipliers: Optional[dict] = Field(
        title="timepoint_multipliers",
        description="Dictionary to provide timepoint multipliers",
        default=None
    )
    read_external_catalog: bool = Field(
        title="read_external_catalog",
        description="Flag to determine whether external catalog is to be used (example: False)",
    )
    external_catalog: str = Field(
        title="external_catalog",
        description="Location to external upgrades technical catalog json file",
    )


# TODO DT: document error codes
# document opendss errors specifically

class VoltageUpgradeParamsModel(UpgradeParamsBaseModel):
    """Voltage Upgrade Parameters for all jobs in a simulation"""

    initial_upper_limit: float = Field(
        title="initial_upper_limit",
        description="Initial upper limit",
        default=1.05,
    )
    initial_lower_limit: float = Field(
        title="initial_lower_limit",
        description="Initial lower limit",
        default=0.95,
    )
    final_upper_limit: float = Field(
        title="final_upper_limit",
        description="Final upper limit",
        default=1.05,
    )
    final_lower_limit: float = Field(
        title="final_lower_limit",
        description="Final lower limit",
        default=0.95,
    )
    target_v: float = Field(
        title="target_v",
        description="Target voltage",
        default=1.0,
    )
    nominal_voltage: float = Field(
        title="nominal_voltage",
        description="Nominal voltage",
        default=120.0,
    )
    nominal_pu_voltage: float = Field(
        title="nominal_voltage",
        description="Nominal voltage",
        default=1.0,
    )
    tps_to_test: List[Any] = Field(
        title="tps_to_test",
        description="TPS to test",
        default=[],
    )
    capacitor_sweep_voltage_gap: float = Field(
        title="capacitor_sweep_voltage_gap",
        description="Capacitor swee voltage gap",
        default=1.0,
    )
    reg_control_bands: List[int] = Field(
        title="reg_control_bands",
        description="Regulator control bands",
        default=[1, 2],
    )
    reg_v_delta: float = Field(
        title="reg_v_delta",
        description="Regulator voltage delta",
        default=0.5,
    )
    max_regulators: int = Field(
        title="max_regulators",
        description="Maximum number of regulators",
        default=4,
    )
    place_new_regulators: bool = Field(
        title="place_new_regulators",
        description="Place new regulators",
        default=False,
    )
    use_ltc_placement: bool = Field(
        title="use_ltc_placement",
        description="Use LTC placement",
        default=False,
    )
    timepoint_multipliers: dict = Field(
        title="timepoint_multipliers",
        description="Dictionary containing timepoint multipliers. Format: {'load_multipliers': {'with_pv': [1.2, 1], 'without_pv': [0.3]}}",
        default=None
    )
    capacitor_action_flag: bool = Field(
        title="capacitor_action_flag",
        description="Capacitor action flag",
        default=True
    )
    existing_regulator_sweep_action: bool = Field(
        title="existing_regulator_sweep_action",
        description="Existing regulator sweep action",
        default=True
    )


class UpgradeCostAnalysisGenericModel(BaseAnalysisModel):
    """Parameters for each job in a simulation"""

    name: str = Field(
        title="name",
        description="Unique name identifying the job",
    )
    opendss_model_file: str = Field(
        title="opendss_model_file",
        description="Path to file used load the simulation model files",
    )
    model_type: str = Field(
        title="model_type",
        description="Model type",
        default="UpgradeCostAnalysisGenericModel",
    )
    blocked_by: Set[str] = Field(
        title="blocked_by",
        description="Names of jobs that must finish before this job starts",
        default=set(),
    )
    estimated_run_minutes: Optional[int] = Field(
        title="estimated_run_minutes",
        description="Optionally advises the job execution manager on how long the job will run",
    )


class PyDssControllerModels(UpgradeParamsBaseModel):
    """Defines the settings for PyDSS controllers"""

    pv_controller: Optional[PvControllerModel] = Field(
        title="pv_controller", description="Settings for a PV controller"
    )


class UpgradeCostAnalysisSimulationModel(BaseModel):
    """Defines the jobs in an upgrade cost analysis simulation."""

    class Config:
        title = "UpgradeCostAnalysisSimulationModel"
        anystr_strip_whitespace = True
        validate_assignment = True
        validate_all = True
        extra = "forbid"
        use_enum_values = False

    thermal_upgrade_params: ThermalUpgradeParamsModel = Field(default=ThermalUpgradeParamsModel())
    voltage_upgrade_params: VoltageUpgradeParamsModel = Field(default=VoltageUpgradeParamsModel())
    upgrade_cost_database: str = Field(
        title="upgrade_cost_database",
        description="Database containing costs for each equipment type",
    )
    pydss_controllers: PyDssControllerModels = Field(
        title="pydss_controllers",
        description="Apply these PyDSS controllers to each corresponding element type.",
        default=PyDssControllerModels(),
    )
    enable_pydss_controllers: bool = Field(
        title="enable_pydss_controllers",
        description="Enable PyDSS controllers",
        default=True,
    )
    include_pf1: bool = Field(
        title="include_pf1",
        description="Include PF1 scenario (no controls) if pydss_controllers are defined.",
        default=True,
    )
    jobs: List[UpgradeCostAnalysisGenericModel]

    @root_validator(pre=True)
    def check_job_names(cls, values):
        names = set()
        for job in values["jobs"]:
            if job["name"] in names:
                raise ValueError(f"{job['name']} is duplicated")
            names.add(job["name"])
        return values

    @classmethod
    def from_file(cls, filename: Path):
        """Return an instance of UpgradeCostAnalysisSimulationModel from a file

        Parameters
        ----------
        filename : Path

        """
        return cls(**load_data(filename))

    def has_pydss_controllers(self):
        """Return True if a PyDSS controller is defined.

        Returns
        -------
        bool

        """
        return self.pydss_controllers.pv_controller is not None


class UpgradeResultModel(UpgradeParamsBaseModel):
    """Defines result parameters for thermal upgrades."""

    name: str = Field(
        title="name",
        description="Job name that produced the result",
    )
    scenario: str = Field(
        title="scenario",
        description="Simulation scenario describing the controls being used",
        default="control_mode",
    )
    stage: str = Field(
        title="stage",
        description="Stage: initial or final",
    )
    upgrade_type: str = Field(
        title="upgrade_type",
        description="Type of upgrade: thermal or voltage",
    )
    simulation_time_s: float = Field(
        title="simulation_time_s",
        description="Simulation time to perform upgrades (seconds)",
    )
    thermal_violations_present: bool = Field(
        title="thermal_violations_present",
        description="Flag indicating whether thermal violations are present",
    )
    voltage_violations_present: bool = Field(
        title="voltage_violations_present",
        description="Flag indicating whether voltage violations are present",
    )
    max_bus_voltage: float = Field(
        title="max_bus_voltage",
        description="Max voltage recorded on any bus",
        units="pu",
    )
    min_bus_voltage: float = Field(
        title="min_bus_voltage",
        description="Max voltage recorded on any bus",
        units="pu",
    )
    num_of_voltage_violation_buses: int = Field(
        title="num_of_voltage_violation_buses",
        description="Number of buses with voltage violations",
    )
    num_of_overvoltage_violation_buses: int = Field(
        title="num_of_overvoltage_violation_buses",
        description="Number of violations with buses above voltage_upper_limit",
    )
    voltage_upper_limit: float = Field(
        title="voltage_upper_limit",
        description="Voltage upper limit",
        units="pu",
    )
    num_of_undervoltage_violation_buses: int = Field(
        title="num_of_undervoltage_violation_buses",
        description="Number of violations with buses below voltage_lower_limit",
    )
    voltage_lower_limit: float = Field(
        title="voltage_lower_limit",
        description="Voltage lower limit",
        units="pu",
    )
    max_line_loading: float = Field(
        title="max_line_loading",
        description="Maximum line loading",
        units="pu",
    )
    max_transformer_loading: float = Field(
        title="max_transformer_loading",
        description="Maximum transformer loading",
        units="pu",
    )
    num_of_line_violations: int = Field(
        title="num_of_line_violations",
        description="Number of lines with violations above line upper limit",
    )
    line_upper_limit: float = Field(
        title="line_upper_limit",
        description="Line upper limit",
        units="pu",
    )
    num_of_transformer_violations: int = Field(
        title="num_of_transformer_violations",
        description="Number of transformers with violations above transformer upper limit",
    )
    transformer_upper_limit: float = Field(
        title="transformer_upper_limit",
        description="Transformer upper limit",
        units="pu",
    )


class EquipmentTypeUpgradeCostsModel(UpgradeParamsBaseModel):
    """Provides costs for upgrading a type of equipment."""

    name: str = Field(
        title="name",
        description="Job name",
    )
    type: str = Field(
        title="type",
        description="Equipment type",
    )
    count: str = Field(
        title="count",
        description="Count upgraded",
    )
    total_cost_usd: float = Field(
        title="total_cost_usd",
        description="Total cost in US dollars",
        units="dollars",
    )


class UpgradeSummaryResultsModel(UpgradeParamsBaseModel):
    """Contains results from all jobs in the simulation."""

    violation_summary: List[UpgradeResultModel] = Field(
        title="upgrade_summary",
        description="Contains thermal or voltage upgrade results for each job",
    )
    upgrade_costs: List[EquipmentTypeUpgradeCostsModel] = Field(
        title="total_upgrade_costs",
        description="Contains upgrade cost information for each jobs",
    )
