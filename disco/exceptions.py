"""Exceptions raised by DISCO"""

from jade.exceptions import JadeBaseException


class DiscoBaseException(JadeBaseException):
    """All DISCO exceptions should derive from this."""


class AnalysisRunException(DiscoBaseException):
    """Raise when Analysis post-process run failed."""


class AnalysisConfigurationException(DiscoBaseException):
    """Raise when Analysis configuration is not valid."""


class UpgradeCostAnalysisRunException(AnalysisRunException):
    """Raise when UpgradeCostAnalysis run failed."""


class PyDssException(DiscoBaseException):
    """Raise when PyDSS-related operations failed"""


class PyDssConfigurationException(PyDssException):
    """Raise when failed to configure PyDSS."""


class PyDssJobException(DiscoBaseException):
    """Raise when PyDSS related job operations failed"""

class UnknownSourceType(DiscoBaseException):
    """Raise when failed to parse the source format"""
