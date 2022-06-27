import enum
import logging
from typing import Any
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


def _extract_specific_model_properties_(model_name, field_type_key, field_type_value):    
    return [field_name  for field_name in model_name.schema().get("properties") if model_name.schema()["properties"][field_name].get(field_type_key) == field_type_value]


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
        arbitrary_types_allowed = True

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
 
    
class TransformerUnitCostModel(UpgradeParamsBaseModel):
    """Contains Transformer Unit Cost Database Model"""
    
    phases: int = Field(
        title="phases",
        description="Number of phases",
    )
    primary_kV: float = Field(
        title="primary_kV",
        description="Transformer primary winding voltage, in kV",
    )
    secondary_kV: float = Field(
        title="secondary_kV",
        description="Transformer secondary winding voltage, in kV",
    )    
    num_windings: int = Field(
        title="num_windings",
        description="Number of windings",
    )
    primary_connection_type: str = Field(
        title="primary_connection_type",
        description="Transformer primary winding connection type. Should be wye or delta",
    )
    secondary_connection_type: str = Field(
        title="secondary_connection_type",
        description="Transformer secondary winding connection type. Should be wye or delta",
    )
    rated_kVA: float = Field(
        title="rated_kVA",
        description="Transformer Rated kVA",
    )
    cost: float = Field(
        title="cost",
        description="Transformer unit cost",
    )
    cost_units: str = Field(
        title="cost_units",
        description="Unit for cost. This should be in USD/unit",
    )
    
    @validator("cost_units")    
    def check_transformer_cost_units(cls, cost_units):
        if cost_units not in ("USD/unit"):
            raise ValueError("Incorrect cost units")
        return cost_units
    
    @validator("primary_connection_type")
    def check_primary_connection(cls, primary_connection_type):
        if primary_connection_type not in ("wye", "delta"):
            raise ValueError("Incorrect transformer primary connection type")
        return primary_connection_type
    
    @validator("secondary_connection_type")
    def check_secondary_connection(cls, secondary_connection_type):
        if secondary_connection_type not in ("wye", "delta"):
            raise ValueError("Incorrect transformer secondary connection type")
        return secondary_connection_type
        

class LineUnitCostModel(UpgradeParamsBaseModel):
    """Contains Line Unit Cost Database Model"""
    
    description: str = Field(
        title="description",
        description="Description of whether this is a new_line or reconductored_line",
    )
    phases: int = Field(
        title="phases",
        description="Number of phases",
    )
    voltage_kV: float = Field(
        title="voltage_kV",
        description="Voltage level in kV",
    )    
    ampere_rating: float = Field(
        title="ampere_rating",
        description="Line rating in amperes",
    )
    line_placement: str = Field(
        title="line_placement",
        description="Placement of line: overhead or underground",
    )
    cost_per_m: float = Field(
        title="cost_per_m",
        description="Cost per meter",
    )
    cost_units: str = Field(
        title="cost_units",
        description="Unit for cost. This should be in USD",
    )
    
    @validator("line_placement")
    def check_line_placement(cls, line_placement):
        if line_placement not in ("underground", "overhead"):
            raise ValueError("Incorrect Line placement type.")
        return line_placement
    
    @validator("cost_units")
    def check_line_cost_units(cls, cost_units):
        if cost_units not in ("USD"):
            raise ValueError("Incorrect cost units")
        return cost_units
    
    @validator("description")
    def check_line_description(cls, description):
        if description not in ("new_line", "reconductored_line"):
            raise ValueError("Incorrect line description")
        return description
    
        
class ControlUnitCostModel(UpgradeParamsBaseModel):
    """Contains Control Changes Cost Database Model"""
    
    type: str = Field(
        title="type",
        description="Type of control setting",
    )
    cost: float = Field(
        title="cost",
        description="Control changes unit cost",
    )
    cost_units: str = Field(
        title="cost_units",
        description="Unit for cost. This should be in USD/unit",
    )
    
    @validator("cost_units")
    def check_control_cost_units(cls, cost_units):
        if cost_units not in ("USD/unit"):
            raise ValueError("Incorrect cost units")
        return cost_units
    
    
class VRegUnitCostModel(TransformerUnitCostModel):
    """Contains Voltage Regulator Cost Database Model"""
    
    type: str = Field(
        title="type",
        description="This should be 'Add new voltage regulator transformer'.",
    )
    

class MiscUnitCostModel(UpgradeParamsBaseModel):
    """Contains Miscellaneous Cost Database Model"""
    
    description: str = Field(
        title="description",
        description="Description of whether this is a fixed cost to add or replace transformer. "
        "These are optional, and will be used if provided.",
    )
    total_cost: float = Field(
        title="total_cost",
        description="total_cost",
    )
    cost_units: str = Field(
        title="cost_units",
        description="Unit for cost. This should be in USD/unit",
    )
    
    @validator("cost_units")
    def check_misc_cost_units(cls, cost_units):
        if cost_units not in ("USD/unit"):
            raise ValueError("Incorrect cost units")
        return cost_units
    
    @validator("description")
    def check_misc_description(cls, description):
        if description not in ("Replace transformer (fixed cost)", "Add new transformer (fixed cost)"):
            raise ValueError("Incorrect Miscellaneous Description")
        return description
    

class UpgradeCostDatabaseModel(UpgradeParamsBaseModel):
    """Contains Upgrades Unit Cost Database needed for cost analysis"""
    
    transformers: List[TransformerUnitCostModel] = Field(
        title="transformers",
        description="This consists of all transformer unit costs",
        default=[]
    )
    lines: List[LineUnitCostModel] = Field(
        title="lines",
        description="This consists of all line unit costs",
        default=[]
    )
    control_changes: List[ControlUnitCostModel] = Field(
        title="control_changes",
        description="This consists of all control changes unit costs",
        default=[]
    )
    voltage_regulators: List[VRegUnitCostModel] = Field(
        title="voltage_regulators",
        description="This consists of all voltage regulator unit costs",
        default=[]
    )
    misc: List[MiscUnitCostModel] = Field(
        title="misc",
        description="This consists of all miscellaneous unit costs",
        default=[]
    )


class upgrade_cost_types(enum.Enum):
    """Possible values for upgrade costs"""
    TRANSFORMER = "Transformer"
    LINE = "Line"


class CommonLineParameters(UpgradeParamsBaseModel):
    """This model contains common line parameters that are used in linecode technical catalog, line technical catalog, line output upgrades. 
    All these fields are directly available from opendss"""
    r1: Any = Field(
        title="r1",
        description="r1",
        determine_upgrade_option=True,
    )
    x1: Any = Field(
        title="x1",
        description="x1",
        determine_upgrade_option=True,
    )
    r0: Any = Field(
        title="r0",
        description="r0",
        determine_upgrade_option=True,
    )
    x0: Any = Field(
        title="x0",
        description="x0",
        determine_upgrade_option=True,
    )
    C1: Any = Field(
        title="c1",
        description="c1",
        determine_upgrade_option=True,
    )
    C0: Any = Field(
        title="c0",
        description="c0",
        determine_upgrade_option=True,
    )
    rmatrix: Any = Field(
        title="rmatrix",
        description="rmatrix. If provided, should be a list.",
        determine_upgrade_option=True,
    )
    xmatrix: Any = Field(
        title="xmatrix",
        description="xmatrix. If provided, should be a list.",
        determine_upgrade_option=True,
    )
    cmatrix: Any = Field(
        title="cmatrix",
        description="cmatrix. If provided, should be a list.",
        determine_upgrade_option=True,
    )
    Rg: float = Field(
        title="Rg",
        description="Rg",
        determine_upgrade_option=True,
    )
    Xg: float = Field(
        title="Xg",
        description="Xg",
        determine_upgrade_option=True,
    )
    rho: float = Field(
        title="rho",
        description="rho",
        determine_upgrade_option=True,
    )
    B1: Any = Field(
        title="B1",
        description="B1",
        determine_upgrade_option=True,
    )
    B0: Any = Field(
        title="B0",
        description="B0",
        determine_upgrade_option=True,
    )
    normamps: float = Field(
        title="normamps",
        description="normamps",
        determine_upgrade_option=True,
    )
    emergamps: float = Field(
        title="emergamps",
        description="emergamps",
        determine_upgrade_option=True,
    )
    units: str = Field(
        title="units",
        description="units",
        determine_upgrade_option=True,
    )   
    faultrate: Optional[float] = Field(
        title="faultrate",
        description="faultrate",
    )
    pctperm: Optional[float] = Field(
        title="pctperm",
        description="pctperm",
    )
    repair: Optional[float] = Field(
        title="repair",
        description="repair",
    ) 
    Seasons: Optional[Any] = Field(
        title="Seasons",
        description="Seasons",
    )
    Ratings: Optional[Any] = Field(
        title="Ratings",
        description="Ratings",
    ) 


class LineCodeCatalogModel(CommonLineParameters):
    """Contains LineCode information needed for thermal upgrade analysis. Most fields can be directly obtained from the opendss models"""
    name: str = Field(
        title="name",
        description="name",
    )
    nphases: int = Field(
        title="nphases",
        description="nphases",
        determine_upgrade_option=True,
    )
    Kron: Optional[Any] = Field(
        title="Kron",
        description="Kron",
        default="N",
        determine_upgrade_option=True,
    )
    neutral: float = Field(
        title="neutral",
        description="neutral",
        determine_upgrade_option=True,
    )
    like: Optional[Any] = Field(
        title="like",
        description="like",
        default=None,
    )
    baseFreq: float = Field(
        title="basefreq",
        description="basefreq",
        determine_upgrade_option=True,
    )
    

class LineCatalogModel(CommonLineParameters):
    """Contains Line information needed for thermal upgrade analysis. Most fields can be directly obtained from the opendss models"""
    name: str = Field(
        title="name",
        description="name. This is not a direct OpenDSS object property.",
    )
    line_definition_type: str = Field(
        title="line_definition_type",
        description="This indicates if the line is defined by using linecodes or line geometry. Possible values are linecode, geometry."
                    "This is a computed field, not a direct OpenDSS object property",
        determine_upgrade_option=True,
    )
    geometry: Any = Field(
        title="geometry",
        description="geometry",
        determine_upgrade_option=True,
    )
    linecode: Any = Field(
        title="linecode",
        description="If line is defined using linecode, then name of associated line code should be provided here.",
        determine_upgrade_option=True,
    )
    phases: int = Field(
        title="phases",
        description="phases",
        determine_upgrade_option=True,
        deciding_property=True,
    )
    kV: float = Field(
        title="kV",
        description="kV. This is not a direct OpenDSS object property.",
        determine_upgrade_option=True,
        deciding_property=True,
    )
    EarthModel: Any = Field(
        title="EarthModel",
        description="EarthModel",
    )
    cncables: Any = Field(
        title="cncables",
        description="cncables",
    )    
    tscables: Any = Field(
        title="tscables",
        description="tscables",
    )   
    wires: Any = Field(
        title="wires",
        description="wires",
    )
    like: Any = Field(
        title="like",
        description="like",
    )
    basefreq: float = Field(
        title="basefreq",
        description="basefreq",
        determine_upgrade_option=True,
        deciding_property=True,
    )
    Switch: bool = Field(
        title="Switch",
        description="Flag that determines whether line is switch or not.",
        determine_upgrade_option=True,
        deciding_property=True,
    )
    spacing: Any = Field(
        title="spacing",
        description="spacing",
        determine_upgrade_option=True,
    )
    h: float = Field(
        title="h",
        description="h. This is not a direct opendss line property, and is added as a new field. A value is available if line is defined as a line geometry.",
        determine_upgrade_option=True,
    )
    line_placement: Any = Field(
        title="line_placement",
        description="line_placement. This is a new field, not a direct OpenDSS object property.",
        determine_upgrade_option=True,
        deciding_property=True,
    )
    
    
class CommonTransformerParameters(UpgradeParamsBaseModel):
    """This model contains common transformer parameters which are inherited by transformer catalog, and transformer upgrade output."""
    phases: int = Field(
        title="phases",
        description="phases",
        determine_upgrade_option=True,
        deciding_property=True,
    )
    windings: int = Field(
        title="windings",
        description="windings",
        determine_upgrade_option=True,
    )
    wdg: int = Field(
        title="wdg",
        description="wdg",
        determine_upgrade_option=True,
        deciding_property=True,
    )
    conn: str = Field(
        title="conn",
        description="conn",
        determine_upgrade_option=True,
        deciding_property=True,
    )
    kV: float = Field(
        title="kV",
        description="kV",
        determine_upgrade_option=True,
        deciding_property=True,
    )
    kVA: float = Field(
        title="kVA",
        description="kVA",
        determine_upgrade_option=True,
    )
    tap: float = Field(
        title="tap",
        description="tap",
        determine_upgrade_option=True,
    )
    pctR: float = Field(
        title="pctR",
        description="pctR",
        alias="%R",
        determine_upgrade_option=True,
    )
    Rneut: float = Field(
        title="Rneut",
        description="Rneut",
        determine_upgrade_option=True,
    )
    Xneut: float = Field(
        title="Xneut",
        description="Xneut",
        determine_upgrade_option=True,
    )
    conns: Any = Field(
        title="conns",
        description="conns. This needs to be passed as a list.",
        determine_upgrade_option=True,
        deciding_property=True,
    )
    kVs: Any = Field(
        title="kVs",
        description="kVs. This needs to be passed as a list.",
        determine_upgrade_option=True,
        deciding_property=True,
    )   
    kVAs: Any = Field(
        title="kVAs",
        description="kVAs. This needs to be passed as a list.",
        determine_upgrade_option=True,
    )
    taps: Any = Field(
        title="taps",
        description="taps. This needs to be passed as a list.",
        determine_upgrade_option=True,
    )
    XHL: float = Field(
        title="XHL",
        description="XHL",
        determine_upgrade_option=True,
    )
    XHT: float = Field(
        title="XHT",
        description="XHT",
        determine_upgrade_option=True,
    )
    XLT: float = Field(
        title="XLT",
        description="XLT",
        determine_upgrade_option=True,
    )
    Xscarray: Any = Field(
        title="Xscarray",
        description="Xscarray",
        determine_upgrade_option=True,
    )
    thermal: Any = Field(
        title="thermal",
        description="thermal",
        determine_upgrade_option=True,
        write_property=True,
    )
    n: float = Field(
        title="n",
        description="n",
        determine_upgrade_option=True,
        write_property=True,
    )
    m: float = Field(
        title="m",
        description="m",
        determine_upgrade_option=True,
        write_property=True,
    )
    flrise: float = Field(
        title="flrise",
        description="flrise",
        determine_upgrade_option=True,
        write_property=True,
    )
    hsrise: float = Field(
        title="hsrise",
        description="hsrise",
        determine_upgrade_option=True,
        write_property=True,
    ) 
    pctloadloss: float = Field(
        title="%loadloss",
        description="%loadloss",
        alias="%loadloss",
        determine_upgrade_option=True,
        write_property=True,
    )
    pctnoloadloss: float = Field(
        title="%noloadloss",
        description="%noloadloss",
        alias="%noloadloss",
        determine_upgrade_option=True,
        write_property=True,
    )
    normhkVA: float = Field(
        title="normhkVA",
        description="normhkVA",
        determine_upgrade_option=True,
        write_property=True,
    ) 
    emerghkVA: float = Field(
        title="emerghkVA",
        description="emerghkVA",
        determine_upgrade_option=True,
        write_property=True,
    )
    sub: str = Field(
        title="sub",
        description="sub",
        determine_upgrade_option=True,
    )
    MaxTap: float = Field(
        title="MaxTap",
        description="MaxTap",
        determine_upgrade_option=True,
    ) 
    MinTap: float = Field(
        title="MinTap",
        description="MinTap",
        determine_upgrade_option=True,
    )
    NumTaps: float = Field(
        title="NumTaps",
        description="NumTaps",
        determine_upgrade_option=True,
        write_property=True,
    )
    subname: Any = Field(
        title="subname",
        description="subname",
        determine_upgrade_option=True,
    ) 
    pctimag: float = Field(
        title="%imag",
        description="%imag",
        alias="%imag",
        determine_upgrade_option=True,
        write_property=True,
    )
    ppm_antifloat: float = Field(
        title="ppm_antifloat",
        description="ppm_antifloat",
        determine_upgrade_option=True,
        write_property=True,
    )
    pctRs: Any = Field(
        title="%Rs",
        description="%Rs. If present, should be a list.",
        alias="%Rs",
        determine_upgrade_option=True,
    ) 
    bank: Any = Field(
        title="bank",
        description="bank",
        determine_upgrade_option=True,
    )
    XfmrCode: Any = Field(
        title="XfmrCode",
        description="XfmrCode",
        determine_upgrade_option=True,
    )
    XRConst: Any = Field(
        title="XRConst",
        description="XRConst",
        determine_upgrade_option=True,
        write_property=True,
    ) 
    X12: float = Field(
        title="X12",
        description="X12",
        determine_upgrade_option=True,
    )
    X13: float = Field(
        title="X13",
        description="X13",
        determine_upgrade_option=True,
    )
    X23: float = Field(
        title="X23",
        description="X23",
        determine_upgrade_option=True,
    ) 
    LeadLag: Any = Field(
        title="LeadLag",
        description="LeadLag",
        determine_upgrade_option=True,
        deciding_property=True,
        write_property=True,
    )
    Core: Any = Field(
        title="Core",
        description="Core",
        determine_upgrade_option=True,
        write_property=True,
    )
    RdcOhms: float = Field(
        title="RdcOhms",
        description="RdcOhms",
        determine_upgrade_option=True,
    )  
    normamps: float = Field(
        title="normamps",
        description="normamps",
        determine_upgrade_option=True,
    )
    emergamps: float = Field(
        title="emergamps",
        description="emergamps",
        determine_upgrade_option=True,
    )
    faultrate: float = Field(
        title="faultrate",
        description="faultrate",
        determine_upgrade_option=True,
        write_property=True,
    )  
    pctperm: float = Field(
        title="pctperm",
        description="pctperm",
        determine_upgrade_option=True,
    )  
    basefreq: float = Field(
        title="basefreq",
        description="basefreq",
        determine_upgrade_option=True,
        deciding_property=True,
    )  
    amp_limit_per_phase: float = Field(
        title="amp_limit_per_phase",
        description="amp_limit_per_phase. This is a new field, not a direct OpenDSS object property.",
        determine_upgrade_option=True,
    )


class TransformerCatalogModel(CommonTransformerParameters):
    """Contains Transformer information needed for thermal upgrade analysis. Most fields can be directly obtained from the opendss models"""
    name: str = Field(
        title="name",
        description="name",
    )
    

class UpgradeTechnicalCatalogModel(UpgradeParamsBaseModel):
    """Contains Upgrades Technical Catalog needed for thermal upgrade analysis"""
    line: Optional[List[LineCatalogModel]] = Field(
        title="line",
        description="line catalog",
        default=[]
    )
    transformer: Optional[List[TransformerCatalogModel]] = Field(
        title="transformer",
        description="transformer catalog",
        default=[]
    )
    linecode: Optional[List[LineCodeCatalogModel]] = Field(
        title="linecode",
        description="linecode catalog",
        default=[]
    )
    # TODO not implemented yet. Can be added if lines are defined through linegeometry
    # geometry: Optional[List[LineGeometryCatalogModel]] = Field(
    #     title="linegeometry",
    #     description="linegeometry catalog",
    #     default=[]
    # )