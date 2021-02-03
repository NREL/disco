"""Defines Time Series Impact Analysis object."""
from disco.analysis import Analysis, Input, Option
from disco.utils.custom_type import CustomType


class TimeSeriesImpactAnalysis(Analysis):
    """Snapshot impact analysis class with default values"""
    INPUTS = [
        Input('over_voltage', CustomType(float), 1.05),
        Input('under_voltage', CustomType(float), 0.95),
        Input('over_voltage_conservative', CustomType(float), 1.05833),
        Input('under_voltage_conservative', CustomType(float), 0.91667),
        Input('line_overload_1', CustomType('percent'), 100),
        Input('line_overload_2', CustomType('percent'), 100),
        Input('transformer_overload_1', CustomType('percent'), 100),
        Input('transformer_overload_2', CustomType('percent'), 100),
    ]

    def run(self, output, **kwargs):
        """Run time series impact analysis"""
