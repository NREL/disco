"""Defines snapshot impact analysis data model"""

from typing import Optional

from pydantic.fields import Field

from .base import ImpactAnalysisBaseModel


class SnapshotImpactAnalysisModel(ImpactAnalysisBaseModel):
    """Data model for snapshot impact analysis"""
    include_voltage_deviation: Optional[bool] = Field(
        title="include_voltage_deviation",
        default=False,
        description="Whether include voltage deviation or not",
    )

    class Config:
        title = "SnapshotImpactAnalysisModel"
        anystr_strip_whitespace = True
        validate_assignment = True
