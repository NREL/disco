import abc
import json
from collections import defaultdict
from datetime import datetime
from enum import Enum
from typing import List, Optional, Union, Set

from pydantic.class_validators import validator, root_validator
from pydantic.fields import Field
from pydantic.main import BaseModel
from pydantic.types import DirectoryPath, FilePath

from jade.utils.utils import ExtendedJSONEncoder, standardize_timestamp
from PyDSS.common import ControllerType
from PyDSS.registry import Registry

from disco.enums import SimulationType
from disco.models.utils import SchemaDict
from disco.pydss.pydss_configuration_base import DEFAULT_CONTROLLER_CONFIGS


DISCO_CONTROLLER_NAMES = [
    controller["name"]
    for controller in DEFAULT_CONTROLLER_CONFIGS
]

registered_pydss_controllers = defaultdict(set)


class DiscoBaseModel(BaseModel):
    """Base input model for DISCO types."""

    @classmethod
    def schema_json(
        cls,
        #model_type: str = "SnapshotImpactAnalysisModel",
        by_alias: bool = True,
        indent: int = 2,
    ) -> str:
        data = cls.schema(by_alias=by_alias)
        return json.dumps(data, indent=indent, cls=ExtendedJSONEncoder)

    @classmethod
    def example(
        cls,
        in_list: bool = True,
    ) -> dict:
        """Create an data example for an inputs model"""
        data = {}
        schema_dict = SchemaDict(super().schema())
        for field in cls.__fields__.values():
            if field.name == "model_type":
                field_value = cls.__name__
            else:
                field_value = field.get_default()

            if field_value is None:
                field_value = field.field_info.extra.get("example_value", None)

            is_enum = False
            if isinstance(field_value, Enum):
                field_value = field_value.value
                is_enum = True

            definition = getattr(field.type_, "__name__", None)
            if definition and (definition in schema_dict.definitions) and (not is_enum):
                field_value = field.type_.example(False)

            data[field.alias] = field_value

        if in_list:
            data = [data]

        return data

    @classmethod
    def example_json(cls, indent: int = 2) -> str:
        """Create a JSON example for an inputs model."""
        return json.dumps(cls.example(), indent=indent)


class PyDSSControllerModel(DiscoBaseModel):
    """PV Controller on deployment"""

    controller_type: ControllerType = Field(
        #alias="type",
        title="controller_type",
        description="The controller type defined in PyDSS.",
        example_value="PvController"
    )
    name: str = Field(
        title="name",
        description="The name of the controller",
        max_length=120,
        example_value="ctrl-name"
    )
    targets: Optional[Union[FilePath, List[FilePath]]] = Field(
        title="targets",
        default=None,
        description="The PV system files that need to apply controller."
    )

    class Config:
        title = "PyDSSControllerModel"
        anystr_strip_whitespace = True
        validate_assignment = True

    @root_validator(pre=True)
    def validate_pydss_controller_registration(cls, values: dict) -> dict:
        controller_type = ControllerType(values["controller_type"])
        name = values["name"]

        if name in registered_pydss_controllers[controller_type]:
            return values

        pydss_registry = Registry()
        registered = pydss_registry.is_controller_registered(
            controller_type=controller_type.value,
            name=name
        )
        if (name not in DISCO_CONTROLLER_NAMES) and not registered:
            raise ValueError("Invalid controller name.")

        registered_pydss_controllers[controller_type].add(name)
        return values


class OpenDssDeploymentModel(DiscoBaseModel):
    """PV Deployment on Feeder"""

    is_standalone: bool = Field(
        title="is_standalone",
        description="Set to True if the models are not to be modified by DISCO.",
        default=False,
    )
    deployment_file: str = Field(
        title="deployment_file",
        description="The path to the PV deployment file.",
        max_length=150,
        example_value="model-inputs/J1/PVDeployments/deployment_001.dss",
    )
    substation: str = Field(
        default=None,
        title="substation",
        description="The substation name.",
        max_length=120,
        example_value="substation_name",
    )
    feeder: str = Field(
        title="feeder",
        description="The feeder name in string.",
        max_length=120,
        example_value="J1",
    )
    dc_ac_ratio: float = Field(
        default=None,
        title="dc_ac_ratio",
        description=(
            "Factor representing the ratio between the PV plant's kW "
            "dc rating and its inverter's kW ac rating"
        ),
        gt=0.0,
        example_value=1.15,
    )
    directory: Optional[DirectoryPath] = Field(
        title="directory",
        default="model-inputs",
        description="The directory of OpenDSS models.",
    )
    kva_to_kw_rating: float = Field(
        default=None,
        title="kva_to_kw_rating",
        description=(
            "Factor representing the ratio between the inverter's input kW "
            "and output kVA ratings"
        ),
        gt=0.0,
        example_value=1.0,
    )
    project_data: dict = Field(
        title="project_data",
        default={},
        description=(
            "Opaque data, unused by DISCO, that will be forwarded through "
            "the stack for use in analysis/post-processing scripts."
        )
    )
    pydss_controllers: Union[PyDSSControllerModel, List[PyDSSControllerModel]] = Field(
        title="pydss_controllers",
        default=None,
        description="One or multiple controllers"
    )

    class Config:
        title = "OpenDssDeploymentModel"
        anystr_strip_whitespace = True
        validate_assignment = True


class SimulationModel(DiscoBaseModel):
    """DISCO Simulation Configurations"""

    start_time: datetime = Field(
        title="start_time",
        description="The start datetime of simulation.",
        example_value="2014-06-17T15:00:00.000",
    )
    end_time: datetime = Field(
        title="end_time",
        description="The end datetime of simulation.",
        example_value="2014-06-17T15:00:00.000",
    )
    step_resolution: int = Field(
        title="step_resolution",
        description="The step resolution of simulation in seconds.",
        ge=1,
        default=900
    )
    simulation_type: SimulationType = Field(
        title="simulation_type",
        default=SimulationType.SNAPSHOT,
        description="The simulation type supported in DISCO."
    )

    class Config:
        title = "SimulationModel"
        validate_assignment = True

    @validator("start_time", pre=True)
    def validate_start_time(cls, value: Union[str, datetime]) -> str:
        try:
            return standardize_timestamp(value)
        except ValueError:
            raise

    @validator("end_time", pre=True)
    def validate_end_time(cls, value: Union[str, datetime]) -> str:
        try:
            return standardize_timestamp(value)
        except ValueError:
            raise

    @root_validator(pre=True)
    def check_start_end_time(cls, values):
        """Validate start/end time for Snapshot simulation."""
        simulation_type = SimulationType(values.get("simulation_type"))
        is_snapshot = simulation_type == SimulationType.SNAPSHOT
        if not is_snapshot:
            return values

        start_time, end_time = values.get("start_time"), values.get("end_time")
        if is_snapshot and start_time != end_time:
            raise ValueError(
                "Invalid 'start_time' and 'end_time' values on "
                "Snapshot simulation, they should be same."
            )
        return values


class BaseAnalysisModel(DiscoBaseModel):
    """Base input model for DISCO simulation types."""
    model_type: Optional[str] = Field(
        title="model_type",
        description="model type.",
        max_length=255,
        default="BaseAnalysisModel"
    )
    name: str = Field(
        title="name",
        description="A unique name for this simulation job.",
        max_length=255,
        example_value="J1_123_Sim_456",
    )
    model_type: Optional[str] = Field(
        title="model_type",
        description="model type.",
        max_length=255
    )
    blocked_by: Optional[Set[str]] = Field(
        title="blocked_by",
        default=set(),
        description="A set of simulation job names that blocks currrent job.",
    )
    job_order: Optional[Union[int, float]] = Field(
        title="job_order",
        default=None,
        ge=0.0,
        description="The execution order of the simulation job.",
    )


class ImpactAnalysisBaseModel(BaseAnalysisModel, abc.ABC):
    """A base model for impact analysis types."""

    base_case: Optional[str] = Field(
        title="base_case",
        description="The base simulation job which has no added PV.",
        max_length=255,
    )
    is_base_case: Optional[bool] = Field(
        title="is_base_case",
        description="Whether this job is a base case",
        default=False,
    )
    deployment: OpenDssDeploymentModel = Field(
        title="deployment",
        description="PV deployment on feeder",
    )
    simulation: SimulationModel = Field(
        title="simulation",
        description="Simulation parameters with PV deployment",
    )

    class Config:
        title = "ImpactAnalysisBaseModel"
        anystr_strip_whitespace = True
        validate_assignment = True
