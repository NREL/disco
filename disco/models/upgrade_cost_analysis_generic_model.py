import logging
from pathlib import Path
from typing import List, Optional, Set, Dict

from pydantic import BaseModel, Field, root_validator, validator

from jade.utils.utils import load_data
from PyDSS.controllers import PvControllerModel
from disco.models.base import BaseAnalysisModel

from disco.extensions.upgrade_simulation.upgrade_configuration import DEFAULT_UPGRADE_PARAMS_FILE

logger = logging.getLogger(__name__)

_DEFAULT_UPGRADE_PARAMS = None
_SUPPORTED_UPGRADE_TYPES = ["thermal", "voltage"]


def _get_default_upgrade_params():
    global _DEFAULT_UPGRADE_PARAMS
    if _DEFAULT_UPGRADE_PARAMS is None:
        _DEFAULT_UPGRADE_PARAMS = load_data(DEFAULT_UPGRADE_PARAMS_FILE)
    return _DEFAULT_UPGRADE_PARAMS


def get_default_thermal_upgrade_params():
    return _get_default_upgrade_params()["thermal_upgrade_params"]


def get_default_voltage_upgrade_params():
    return _get_default_upgrade_params()["voltage_upgrade_params"]


class UpgradeParamsBaseModel(BaseModel):
    """Base model for all upgrade cost analysis parameters"""

    class Config:
        title = "UpgradeParamsBaseModel"
        anystr_strip_whitespace = True
        validate_assignment = True
        validate_all = True
        extra = "forbid"
        use_enum_values = False

    @classmethod
    def from_file(cls, filename: Path):
        """Return an instance from a file

        Parameters
        ----------
        filename : Path

        """
        return cls(**load_data(filename))


class ThermalUpgradeParamsModel(UpgradeParamsBaseModel):
    """Thermal Upgrade Parameters for all jobs in a simulation"""

    # Required fields
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
    read_external_catalog: bool = Field(
        title="read_external_catalog",
        description="Flag to determine whether external catalog is to be used (example: False)",
    )
    external_catalog: str = Field(
        title="external_catalog",
        description="Location to external upgrades technical catalog json file",
    )

    # Optional fields
    create_plots: Optional[bool] = Field(
        title="create_plots", description="Flag to enable or disable figure creation", default=True
    )
    parallel_transformer_limit: Optional[int] = Field(
        title="parallel_transformer_limit", description="Parallel transformer limit", default=4
    )
    parallel_lines_limit: Optional[int] = Field(
        title="parallel_lines_limit", description="Parallel lines limit", default=4
    )
    upgrade_iteration_threshold: Optional[int] = Field(
        title="upgrade_iteration_threshold", description="Upgrade iteration threshold", default=5
    )
    timepoint_multipliers: Optional[Dict] = Field(
        title="timepoint_multipliers",
        description='Dictionary to provide timepoint multipliers. example: timepoint_multipliers={"load_multipliers": {"with_pv": [0.1], "without_pv": [0.3]}}',
    )

    @validator("voltage_lower_limit")
    def check_voltage_lower_limits(cls, voltage_lower_limit, values):
        upper = values["voltage_upper_limit"]
        if upper <= voltage_lower_limit:
            raise ValueError(
                f"voltage_upper_limit={upper} must be greater than voltage_lower_limit={voltage_lower_limit}"
            )
        return voltage_lower_limit

    @validator("external_catalog")
    def check_catalog(cls, external_catalog, values):
        if values["read_external_catalog"] and not Path(external_catalog).exists():
            raise ValueError(f"{external_catalog} does not exist")
        return external_catalog

    @validator("timepoint_multipliers")
    def check_timepoint_multipliers(cls, timepoint_multipliers):
        if timepoint_multipliers is None:
            return timepoint_multipliers
        if "load_multipliers" not in timepoint_multipliers:
            raise ValueError("load_multipliers must be defined in timepoint_multipliers")
        if "with_pv" not in timepoint_multipliers and "without_pv" not in timepoint_multipliers:
            raise ValueError(
                "Either 'with_pv' or 'without_pv' must be defined in timepoint_multipliers"
            )
        return timepoint_multipliers


class VoltageUpgradeParamsModel(UpgradeParamsBaseModel):
    """Voltage Upgrade Parameters for all jobs in a simulation"""

    # Required fields
    initial_upper_limit: float = Field(
        title="initial_upper_limit",
        description="Initial upper limit in per unit (example: 1.05)",
    )
    initial_lower_limit: float = Field(
        title="initial_lower_limit",
        description="Initial lower limit in per unit (example: 0.95)",
    )
    final_upper_limit: float = Field(
        title="final_upper_limit",
        description="Final upper limit in per unit (example: 1.05)",
    )
    final_lower_limit: float = Field(
        title="final_lower_limit",
        description="Final lower limit in per unit (example: 0.95)",
    )
    nominal_voltage: float = Field(
        title="nominal_voltage",
        description="Nominal voltage (volts) (example: 120)",
    )

    # Optional fields
    create_plots: Optional[bool] = Field(
        title="create_plots", description="Flag to enable or disable figure creation", default=True
    )
    capacitor_sweep_voltage_gap: float = Field(
        title="capacitor_sweep_voltage_gap",
        description="Capacitor sweep voltage gap (example: 1)",
        default=1.0,
    )
    reg_control_bands: List[int] = Field(
        title="reg_control_bands",
        description="Regulator control bands (example: [1, 2])",
        default=[1, 2],
    )
    reg_v_delta: float = Field(
        title="reg_v_delta",
        description="Regulator voltage delta (example: 0.5)",
        default=0.5,
    )
    max_regulators: int = Field(
        title="max_regulators",
        description="Maximum number of regulators",
        default=4,
    )
    place_new_regulators: bool = Field(
        title="place_new_regulators",
        description="Flag to enable or disable new regulator placement",
        default=False,
    )
    use_ltc_placement: bool = Field(
        title="use_ltc_placement",
        description="Flag to enable or disable substation LTC upgrades module",
        default=False,
    )
    timepoint_multipliers: dict = Field(
        title="timepoint_multipliers",
        description="Dictionary containing timepoint multipliers. Format: {'load_multipliers': {'with_pv': [1.2, 1], 'without_pv': [0.3]}}",
        default=None,
    )
    capacitor_action_flag: bool = Field(
        title="capacitor_action_flag",
        description="Flag to enable or disable capacitor controls settings sweep module",
        default=True,
    )
    existing_regulator_sweep_action: bool = Field(
        title="existing_regulator_sweep_action",
        description="Flag to enable or disable existing regulator controls settings sweep module",
        default=True,
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

    @validator("opendss_model_file")
    def check_model_file(cls, opendss_model_file):
        if not Path(opendss_model_file).exists():
            raise ValueError(f"{opendss_model_file} does not exist")
        return opendss_model_file


class PyDssControllerModels(UpgradeParamsBaseModel):
    """Defines the settings for PyDSS controllers"""

    pv_controller: Optional[PvControllerModel] = Field(
        title="pv_controller", description="Settings for a PV controller"
    )


class UpgradeCostAnalysisSimulationModel(UpgradeParamsBaseModel):
    """Defines the jobs in an upgrade cost analysis simulation."""

    class Config:
        title = "UpgradeCostAnalysisSimulationModel"
        anystr_strip_whitespace = True
        validate_assignment = True
        validate_all = True
        extra = "forbid"
        use_enum_values = False

    thermal_upgrade_params: ThermalUpgradeParamsModel = Field(
        default=ThermalUpgradeParamsModel(**get_default_thermal_upgrade_params())
    )
    voltage_upgrade_params: VoltageUpgradeParamsModel = Field(
        default=VoltageUpgradeParamsModel(**get_default_voltage_upgrade_params())
    )
    upgrade_cost_database: str = Field(
        title="upgrade_cost_database",
        description="Database containing costs for each equipment type",
    )
    calculate_costs: bool = Field(
        title="calculate_costs",
        description="If True, calculate upgrade costs from database.",
        default=True,
    )
    upgrade_order: List[str] = Field(
        description="Order of upgrade algorithm. 'thermal' or 'voltage' can be removed from the "
        "simulation by excluding them from this parameter.",
        default=_SUPPORTED_UPGRADE_TYPES,
    )
    pydss_controllers: PyDssControllerModels = Field(
        title="pydss_controllers",
        description="If enable_pydss_controllers is True, these PyDSS controllers are applied to each corresponding element type.",
        default=PyDssControllerModels(),
    )
    plot_violations: bool = Field(
        title="plot_violations",
        description="If True, create plots of violations before and after simulation.",
        default=True,
    )
    enable_pydss_controllers: bool = Field(
        title="enable_pydss_controllers",
        description="Flag to enable/disable use of PyDSS controllers",
        default=False,
    )
    include_pf1: bool = Field(
        title="include_pf1",
        description="Include PF1 scenario (no controls) if pydss_controllers are defined.",
        default=True,
    )
    dc_ac_ratio: Optional[float] = Field(
        title="dc_ac_ratio", description="Apply DC-AC ratio for PV Systems", default=None
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

    @validator("calculate_costs")
    def check_database(cls, calculate_costs, values):
        if calculate_costs:
            if not Path(values["upgrade_cost_database"]).exists():
                raise ValueError(f"{values['upgrade_cost_database']} does not exist")
        return calculate_costs

    @validator("upgrade_order")
    def check_upgrade_order(cls, upgrade_order):
        diff = set(upgrade_order).difference(_SUPPORTED_UPGRADE_TYPES)
        if diff:
            raise ValueError(f"Unsupported values in upgrade_order: {diff}")
        return upgrade_order

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
        description="Stage of upgrades: initial (before upgrades) or final (after upgrades)",
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
        description="Maximum voltage recorded on any bus",
        units="pu",
    )
    min_bus_voltage: float = Field(
        title="min_bus_voltage",
        description="Minimum voltage recorded on any bus",
        units="pu",
    )
    num_of_voltage_violation_buses: int = Field(
        title="num_of_voltage_violation_buses",
        description="Number of buses with voltage violations",
    )
    num_of_overvoltage_violation_buses: int = Field(
        title="num_of_overvoltage_violation_buses",
        description="Number of buses with voltage above voltage_upper_limit",
    )
    voltage_upper_limit: float = Field(
        title="voltage_upper_limit",
        description="Voltage upper limit, the threshold considered for determining overvoltages",
        units="pu",
    )
    num_of_undervoltage_violation_buses: int = Field(
        title="num_of_undervoltage_violation_buses",
        description="Number of buses with voltage below voltage_lower_limit",
    )
    voltage_lower_limit: float = Field(
        title="voltage_lower_limit",
        description="Voltage lower limit, the threshold considered for determining undervoltages",
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
        description="Number of lines with loading above line upper limit",
    )
    line_upper_limit: float = Field(
        title="line_upper_limit",
        description="Line upper limit, the threshold considered for determining line overloading",
        units="pu",
    )
    num_of_transformer_violations: int = Field(
        title="num_of_transformer_violations",
        description="Number of transformers with loading above transformer upper limit",
    )
    transformer_upper_limit: float = Field(
        title="transformer_upper_limit",
        description="Transformer upper limit, the threshold considered for determining transformer overloading",
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
        description="Count of upgraded equipment",
    )
    total_cost_usd: float = Field(
        title="total_cost_usd",
        description="Total cost in US dollars",
        units="dollars",
    )


class UpgradeJobOutputs(UpgradeParamsBaseModel):
    """Contains outputs from one job."""

    upgraded_opendss_model_file: str = Field(
        title="upgraded_opendss_model_file",
        description="Path to file that will load the upgraded network.",
    )
    feeder_stats: str = Field(
        title="feeder_stats",
        description="Path to file containing feeder metadata and equipment details before and "
        "after upgrades.",
    )
    return_code: int = Field(
        title="return_code",
        description="Return code from process. Zero is success, non-zero is a failure.",
    )


class UpgradeSimulationOutputs(UpgradeParamsBaseModel):
    """Contains outputs from all jobs in the simulation."""

    log_file: str = Field(
        title="log_file",
        description="Path to log file for the simulation.",
    )
    jobs: List[UpgradeJobOutputs] = Field(
        title="jobs",
        description="Outputs for each job in the simulation.",
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
    outputs: UpgradeSimulationOutputs = Field(
        title="outputs",
        description="Outputs for each job in the simulation.",
    )
