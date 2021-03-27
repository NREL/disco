"""Defines time series impact analysis model."""

from typing import Optional

from pydantic.fields import Field

from .base import ImpactAnalysisBaseModel


class TimeSeriesAnalysisModel(ImpactAnalysisBaseModel):
    """Data model for time series impact analysis"""
    # Currently unused and just taking up space in config files.
    #include_pv_clipping: Optional[bool] = Field(
    #    title="include_pv_clipping",
    #    default=True,
    #    description="Whether to include PV clipping metrics",
    #)
    #include_pv_curtailment: Optional[bool] = Field(
    #    title="include_pv_curtailment",
    #    default=True,
    #    description="Whether to include PV curtailment metrics",
    #)
    #include_voltage_metrics: Optional[bool] = Field(
    #    title="include_voltage_metrics",
    #    default=True,
    #    description="Whether to include voltage metrics",
    #)
    #include_thermal_metrics: Optional[bool] = Field(
    #    title="include_thermal_metrics",
    #    default=True,
    #    description="Whether to include thermal metrics",
    #)
    #include_feeder_losses: Optional[bool] = Field(
    #    title="include_feeder_losses",
    #    default=True,
    #    description="Whether to include feeder loss metrics",
    #)
    #include_capacitor_state_change_count: Optional[bool] = Field(
    #    title="include_capacitor_state_change_count",
    #    default=True,
    #    description="Whether to include capacitor state change count metrics",
    #)
    #include_reg_control_state_change_count: Optional[bool] = Field(
    #    title="include_reg_control_state_change_count",
    #    default=True,
    #    description="Whether to include regulator state change count metrics",
    #)
    #granularity: Optional[str] = Field(
    #    title="granularity",
    #    default="per_element_per_time_point",
    #    description="Granularity of data to collect",
    #)

    class Config:
        title = "TimeSeriesAnalysisModel"
        anystr_strip_whitespace = True
        validate_assignment = True
