import enum
import logging
from typing import List, Optional, Set, Dict, Any
from pydantic import Field

from disco.models.upgrade_cost_analysis_equipment_model import UpgradeParamsBaseModel, ExtraLineParams, ExtraTransformerParams
from disco.models.upgrade_cost_analysis_generic_input_model import OpenDSSLineModel, OpenDSSTransformerModel

logger = logging.getLogger(__name__)


class UpgradeViolationResultModel(UpgradeParamsBaseModel):
    """Defines result parameters for thermal upgrades."""

    name: str = Field(
        title="name",
        description="Job name",
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
    num_voltage_violation_buses: int = Field(
        title="num_voltage_violation_buses",
        description="Number of buses with voltage violations",
    )
    num_overvoltage_violation_buses: int = Field(
        title="num_overvoltage_violation_buses",
        description="Number of buses with voltage above voltage_upper_limit",
    )
    voltage_upper_limit: float = Field(
        title="voltage_upper_limit",
        description="Voltage upper limit, the threshold considered for determining overvoltages",
        units="pu",
    )
    num_undervoltage_violation_buses: int = Field(
        title="num_undervoltage_violation_buses",
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
    num_line_violations: int = Field(
        title="num_line_violations",
        description="Number of lines with loading above line upper limit",
    )
    line_upper_limit: float = Field(
        title="line_upper_limit",
        description="Line upper limit, the threshold considered for determining line overloading",
        units="pu",
    )
    num_transformer_violations: int = Field(
        title="num_transformer_violations",
        description="Number of transformers with loading above transformer upper limit",
    )
    transformer_upper_limit: float = Field(
        title="transformer_upper_limit",
        description="Transformer upper limit, the threshold considered for determining transformer overloading",
        units="pu",
    )


class TotalUpgradeCostsResultModel(UpgradeParamsBaseModel):
    """Provides total output costs for upgrading a type of equipment."""

    name: str = Field(
        title="name",
        description="Job name",
    )
    type: str = Field(
        title="type",
        description="Equipment type",
    )
    count: int = Field(
        title="count",
        description="Count of upgraded equipment",
    )
    total_cost_usd: float = Field(
        title="total_cost_usd",
        description="Total cost in US dollars",
        units="dollars",
    )
    

class EquipmentTypeUpgradeCostsResultModel(UpgradeParamsBaseModel):
    """Provides output costs and final equipment details for each upgraded asset."""

    name: str = Field(
        title="name",
        description="Job name",
    )
    type: str = Field(
        title="type",
        description="Equipment type",
    )
    count: int = Field(
        title="count",
        description="Count of upgraded equipment",
    )
    total_cost_usd: float = Field(
        title="total_cost_usd",
        description="Total cost in US dollars",
        units="dollars",
    )
    equipment_parameters: Optional[Any] = Field(
        title="equipment_parameters",
        description="Final Equipment parameters",
        units="",
        default={},
    )
    comment: Optional[Any] = Field(
        title="comment",
        description="Other comments",
        units="",
        default="",
    )
    

class AllEquipmentUpgradeCostsResultModel(UpgradeParamsBaseModel):
    """Contains outputs for thermal and voltage costs by individual equipment"""
    voltage: Optional[List[EquipmentTypeUpgradeCostsResultModel]] = Field(
        title="voltage", 
        description="Voltage upgrade costs",
        default=[],  
    )
    thermal: Optional[List[EquipmentTypeUpgradeCostsResultModel]] = Field(
        title="thermal", 
        description="Line and Transformer upgrade costs",  
        default=[],
    )

    
class VoltageUpgradesTechnicalResultModel(UpgradeParamsBaseModel):
    """Model for voltage_upgrades.json. This contains the details on the voltages upgrades made to resolve voltage violations"""
    equipment_type: str = Field(
        title="equipment_type",
        description="Type of upgraded equipment",
    )  
    name: str = Field(
        title="name",
        description="Name of the upgraded equipment",
    )  
    new_controller_added: bool = Field(
        title="new_controller_added",
        description="This flag depicts whether a new controller was added",
    ) 
    controller_settings_modified: bool = Field(
        title="controller_settings_modified",
        description="This flag depicts whether the controller settings were modified",
    ) 
    final_settings: dict = Field(
        title="final_settings",
        description="Final Settings of the equipment",
    ) 
    new_transformer_added: bool = Field(
        title="new_transformer_added",
        description="This flag depicts whether a new transformer was added",
    ) 
    at_substation: bool = Field(
        title="at_substation",
        description="This flag depicts whether the change was made at the Substation",
    ) 
       

class LineUpgradesTechnicalResultModel(OpenDSSLineModel, ExtraLineParams):
    """Line Upgrades Output Details model"""
    equipment_type: str = Field(
         title="equipment_type",
        description="Equipment Type"
    )
    upgrade_type: str = Field(
         title="upgrade_type",
        description="Upgrade Type"
    )
    parameter_type: str = Field(
         title="parameter_type",
        description="Parameter Type"
    )
    action: str = Field(
         title="action",
        description="Action"
    )
    final_equipment_name: str = Field(
         title="final_equipment_name",
        description="final_equipment_name"
    )
    original_equipment_name: str = Field(
         title="original_equipment_name",
        description="original_equipment_name"
    )

    
class TransformerUpgradesTechnicalResultModel(OpenDSSTransformerModel, ExtraTransformerParams):
    """Transformer Upgrades Output Details model"""
    equipment_type: str = Field(
         title="equipment_type",
        description="Equipment Type"
    )
    upgrade_type: str = Field(
         title="upgrade_type",
        description="Upgrade Type"
    )
    parameter_type: str = Field(
         title="parameter_type",
        description="Parameter Type"
    )
    action: str = Field(
         title="action",
        description="Action"
    )
    final_equipment_name: str = Field(
         title="final_equipment_name",
        description="final_equipment_name"
    )
    original_equipment_name: str = Field(
         title="original_equipment_name",
        description="original_equipment_name"
    )

    
class AllUpgradesTechnicalResultModel(UpgradeParamsBaseModel):
    """Contains All Upgrades Output Details. Read in as input for cost computation"""
    line: Optional[List[LineUpgradesTechnicalResultModel]] = Field(
        title="line",
        description="line upgrades output details",
        default=[]
    )
    transformer: Optional[List[TransformerUpgradesTechnicalResultModel]] = Field(
        title="transformer",
        description="transformer upgrades output details",
        default=[]
    )
    voltage: Optional[List[VoltageUpgradesTechnicalResultModel]] = Field(
        title="voltage",
        description="voltage upgrades output details",
        default=[]
    )


class UpgradesCostResultSummaryModel(UpgradeParamsBaseModel):
    """Contains individual equipment output"""
    name: str = Field(
        title="name",
        description="Job name",
    )
    equipment_type: str = Field(
        title="equipment_type",
        description="Type of equipment",
    )
    equipment_name: str = Field(
        title="equipment_name",
        description="Name of equipment",
    )
    status: str = Field(
        title="status",
        description="Status",
    )
    total_cost_usd: float = Field(
        title="total_cost_usd",
        description="Total cost in US dollars",
    )
    parameter1_name: str = Field(
        title="parameter1_name",
        description="Name of parameter1",
    )
    parameter1_original: Any = Field(
        title="parameter1_original",
        description="Original value of parameter1",
    )
    parameter1_upgraded: Any = Field(
        title="parameter1_upgraded",
        description="Upgraded value of parameter1",
    )
    parameter2_name: Optional[str] = Field(
        title="parameter2_name",
        description="Name of parameter2",
        default="",
    )
    parameter2_original: Optional[Any] = Field(
        title="parameter2_original",
        description="Original value of parameter2",
        default=None,
    )
    parameter2_upgraded: Optional[Any] = Field(
        title="parameter2_upgraded",
        description="Upgraded value of parameter2",
        default=None,
    )
    parameter3_name: Optional[str] = Field(
        title="parameter3_name",
        description="Name of parameter3",
        default="",
    )
    parameter3_original: Optional[Any] = Field(
        title="parameter3_original",
        description="Original value of parameter3",
        default=None,
    )
    parameter3_upgraded: Optional[Any] = Field(
        title="parameter3_upgraded",
        description="Upgraded value of parameter3",
        default=None,
    )    


class ResultSummaryModel(UpgradeParamsBaseModel):
    """Contains final results summary"""
    total_cost: str = Field(
        title="equipment_type",
        description="Type of equipment",
    )
    equipment_name: str = Field(
        title="equipment_name",
        description="Name of equipment",
    )

class AllUpgradesCostResultSummaryModel(UpgradeParamsBaseModel):
    """Contains All Equipment output"""
    equipment: List[UpgradesCostResultSummaryModel] = Field(
        title="equipment",
        description="Individual Equipment output details",
        default=[]
    )
    

class ExtendedEnum(enum.Enum):
    @classmethod
    def list_values(cls):
        return list(map(lambda c: c.value, cls))
    

class CapacitorControllerResultType(ExtendedEnum):
    """Possible values for capacitor upgrade type"""
    add_new_cap_controller = "Capacitor controller"
    change_cap_control = "Capacitor controller setting change"
   
 
class VoltageRegulatorResultType(ExtendedEnum):
    """Possible values for voltage regulator upgrade type"""
    add_new_reg_control = "In-line voltage regulator"
    change_reg_control = "In-line voltage regulator control setting change"
    # replace_reg_control = "Replace in-line voltage regulator controller"   # this is not used currently
    add_substation_ltc = "Substation LTC"
    change_ltc_control = "Substation LTC setting change"
    add_new_vreg_transformer = "Transformer for voltage regulator"
    add_new_substation_transformer =  "Substation transformer"


class EquipmentUpgradeStatusModel(ExtendedEnum):
    """Possible values for upgrade status in output summary file"""
    replaced = "replaced"
    new = "new"
    setting_changed = "setting_changed"
    unchanged = "unchanged"


class UpgradeJobOutputModel(UpgradeParamsBaseModel):
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


class UpgradeSimulationOutputModel(UpgradeParamsBaseModel):
    """Contains outputs from all jobs in the simulation."""

    log_file: str = Field(
        title="log_file",
        description="Path to log file for the simulation.",
    )
    jobs: List[UpgradeJobOutputModel] = Field(
        title="jobs",
        description="Outputs for each job in the simulation.",
    )


class JobUpgradeSummaryOutputModel(UpgradeParamsBaseModel):
    """Contains results from all jobs in the simulation."""
    results: List = Field(
        title="results",
        description="Results summary for each job",
    )
    outputs: UpgradeSimulationOutputModel = Field(
        title="outputs",
        description="Outputs for each job in the simulation.",
    )
    violation_summary: List[UpgradeViolationResultModel] = Field(
        title="upgrade_summary",
        description="Contains thermal or voltage upgrade results for each job",
    )
    costs_per_equipment: List[TotalUpgradeCostsResultModel] = Field(
        title="costs_per_equipment",
        description="Contains upgrade cost information for each job by equipment type",
    )    
    equipment: List = Field(
        title="equipment",
        description="Contains equipment information for each job",
    )
