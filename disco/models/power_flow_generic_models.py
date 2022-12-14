from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set

from pydantic import BaseModel, Field, root_validator, validator

from jade.utils.utils import load_data

from disco.models.base import BaseAnalysisModel, PyDSSControllerModel


class PowerFlowGenericModel(BaseAnalysisModel):
    """Parameters for each job in a power-flow simulation"""

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
        default="PowerFlowGenericModel",
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
    substation: Optional[str] = Field(
        title="substation",
        description="Substation for the job",
    )
    feeder: Optional[str] = Field(
        title="feeder",
        description="Feeder for the job",
    )
    pydss_controllers: List[PyDSSControllerModel] = Field(
        title="pydss_controllers",
        description="Apply these PyDSS controllers to each corresponding element type. If empty, "
        "use pf1.",
        default=[],
    )
    project_data: Dict = Field(
        title="project_data",
        description="Optional user-defined metadata for the job",
    )


class PowerFlowSimulationBaseModel(BaseModel):
    """Base model for power-flow simulations."""

    class Config:
        title = "PowerFlowSimulationBaseModel"
        anystr_strip_whitespace = True
        validate_assignment = True
        validate_all = True
        extra = "forbid"
        use_enum_values = False

    jobs: List[PowerFlowGenericModel] = Field(
        title="jobs",
        description="Jobs to run as part of the simulation.",
    )
    include_control_mode: bool = Field(
        title="include_control_mode",
        description="Include a control mode (such as volt-var controls) scenario for each job.",
        default=True,
    )
    include_pf1: bool = Field(
        title="include_pf1",
        description="Include a Power Factor 1 scenario for each job.",
        default=True,
    )

    @root_validator(pre=True)
    def check_job_names(cls, values):
        names = set()
        for job in values["jobs"]:
            if job["name"] in names:
                raise ValueError(f"{job['name']} is duplicated")
            names.add(job["name"])
        return values

    @root_validator(pre=False)
    def check_pydss_controllers(cls, values):
        if not values["jobs"]:
            raise ValueError("no jobs are defined")

        num_pydss_controllers = len(values["jobs"][0].pydss_controllers)
        if len(values["jobs"]) > 1:
            for job in values["jobs"][1:]:
                if len(job.pydss_controllers) != num_pydss_controllers:
                    raise ValueError("All jobs must have the same number of pydss_controllers.")
        return values

    @root_validator(pre=False)
    def check_scenarios(cls, values):
        if not values["include_pf1"] and not values["include_control_mode"]:
            raise ValueError(
                "At least one of 'include_pf1' and 'include_control_mode' must be set."
            )
        return values

    @classmethod
    def from_file(cls, filename: Path):
        """Return an instance of UpgradeCostAnalysisSimulationModel from a file

        Parameters
        ----------
        filename : Path

        """
        return cls(**load_data(filename))


class PowerFlowSnapshotSimulationModel(PowerFlowSimulationBaseModel):
    """Defines a snapshot power-flow simulation."""

    model_type: str = Field(default="PowerFlowSnapshotSimulationModel")
    start_time: datetime = Field(
        title="start_time",
        description="Start time of simulation. May be overridden by auto-time-point-selection.",
        default="2020-04-15 14:00:00",
    )

    @validator("model_type")
    def check_model_type(cls, val):
        if val != "PowerFlowSnapshotSimulationModel":
            raise ValueError(
                f"model_type must be 'PowerFlowSnapshotSimulationModel' instead of {val}"
            )
        return val


class PowerFlowTimeSeriesSimulationModel(PowerFlowSimulationBaseModel):
    """Defines a time-series power-flow simulation."""

    model_type: str = Field(default="PowerFlowTimeSeriesSimulationModel")
    start_time: datetime = Field(
        title="start_time",
        description="Start time of simulation.",
        default="2020-01-01 00:00:00",
    )
    end_time: datetime = Field(
        title="end_time",
        description="End time of simulation.",
        default="2020-12-31 23:45:00",
    )
    step_resolution: int = Field(
        title="step_resolution",
        description="Step resolution of simulation in seconds.",
        default=900,
    )

    @validator("model_type")
    def check_model_type(cls, val):
        if val != "PowerFlowTimeSeriesSimulationModel":
            raise ValueError(
                f"model_type must be 'PowerFlowTimeSeriesSimulationModel' instead of {val}"
            )
        return val
