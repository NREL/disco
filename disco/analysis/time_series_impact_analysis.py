"""Defines Time Series Impact Analysis object."""
from disco.analysis import Analysis, Input, Option
from disco.utils.custom_type import CustomType

class TimeSeriesImpactAnalysis(Analysis):
    """Snapshot impact analysis class with default values"""
    INPUTS = [
        Input('analysis_period', CustomType(list), [0, 1])
    ]

    OPTIONS = [
        Option('reports_produced', []),
        Option('severity', 0),
        Option('duration', 0),
        Option('snapshot_impact_only', False),
        Option('pv_curtailment', True),
    ]

    def run(self, config_file):
        """Run time series impact analysis"""
