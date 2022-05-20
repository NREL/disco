"""Exceptions raised by DISCO"""

from jade.exceptions import JadeBaseException


class DiscoBaseException(JadeBaseException):
    """All DISCO exceptions should derive from this."""


class AnalysisRunException(DiscoBaseException):
    """Raise when Analysis post-process run failed."""


class AnalysisConfigurationException(DiscoBaseException):
    """Raise when the configuration is not valid."""


class ExceededParallelLinesLimit(DiscoBaseException):
    """Raise when an upgrade simulation exceeds the limit for parallel lines"""


class ExceededParallelTransformersLimit(DiscoBaseException):
    """Raise when an upgrade simulation exceeds the limit for parallel transformers"""


class UpgradesInvalidViolationIncrease(DiscoBaseException):
    """Raise when violations increase unexpectedly"""


class OpenDssCompileError(DiscoBaseException):
    """Raise when OpenDSS fails to compile a model"""


class OpenDssConvergenceError(DiscoBaseException):
    """Raise when OpenDSS fails to converge"""


class PyDssConvergenceError(DiscoBaseException):
    """Raise when PyDSS fails to converge"""


class PyDssConvergenceErrorCountExceeded(DiscoBaseException):
    """Raise when PyDSS exceeds its threshold for error counts"""


class PyDssConvergenceMaxError(DiscoBaseException):
    """Raise when PyDSS exceeds its max tolerance error threshold"""


class UpgradesExternalCatalogRequired(DiscoBaseException):
    """Raise when an upgrade simulation needs an external catalog"""


class UpgradesExternalCatalogMissingObjectDefinition(DiscoBaseException):
    """Raise when an upgrade external catalog is missing an equipment type"""


class InvalidOpenDssElementError(DiscoBaseException):
    """Raise when an OpenDSS element has unexpected properties"""


EXCEPTIONS_TO_ERROR_CODES = {
    
    AnalysisConfigurationException: {
        "description": "The input configuration is invalid.",
        "error_code": 114,
    },
    ExceededParallelLinesLimit: {
        "description": "An Upgrades simulation exceeded the limit for parallel lines.",
        "corrective_action": "If not already done, enable ThermalUpgradeParamsModel.read_external_catalog"
        "and provide an external catalog. Or, increase ThermalUpgradeParamsModel.parallel_lines_limit to allow more parallel equipment to"
        "be placed to resolve thermal violations.",
        "error_code": 115,
    },
    ExceededParallelTransformersLimit: {
        "description": "An Upgrades simulation exceeded the limit for parallel transformers.",
        "corrective_action": "If not already done, enable ThermalUpgradeParamsModel.read_external_catalog"
        "and provide an external catalog. Or, increase ThermalUpgradeParamsModel.parallel_transformers_limit to allow more parallel equipment to"
        "be placed to resolve thermal violations.",
        "error_code": 116,
    },
    InvalidOpenDssElementError: {
        "description": "An OpenDSS element has unexpected properties.",
        "corrective_action": "Check the error message and fix the OpenDSS element definitions.",
        "error_code": 117,
    },
    OpenDssCompileError: {
        "description": "OpenDSS failed to compile a model.",
        "corrective_action": "Check the error message and fix the OpenDSS model definitions.",
        "error_code": 118,
    },
    OpenDssConvergenceError: {
        "description": "OpenDSS failed to converge.",
        "corrective_action": "Check the OpenDSS model. Also, refer to the OpenDSS manual to vary settings for convergence.",
        "error_code": 119,
    },
    PyDssConvergenceError: {
        "description": "PyDSS failed to find a solution in its external controls.",
        "error_code": 120,
    },
    PyDssConvergenceErrorCountExceeded: {
        "description": "PyDSS external controls exceeded the threshold for error counts.",
        "error_code": 121,
    },
    PyDssConvergenceMaxError: {
        "description": "PyDSS external controls exceeded the max tolerance error threshold.",
        "error_code": 122,
    },
    UpgradesExternalCatalogRequired: {
        "description": "An Upgrades simulation requires an external catalog for thermal upgrades in order to add or "
        "upgrade a component.",
        "corrective_action": "Provide an external catalog or disable ThermalUpgradeParamsModel.read_external_catalog.",
        "error_code": 123,
    },
    UpgradesExternalCatalogMissingObjectDefinition: {
        "description": "The Upgrades external catalog does not define a required object.",
        "corrective_action": "Ensure the external catalog defines all required objects. Refer to "
        "the error message for specific details.",
        "error_code": 124,
    },
    UpgradesInvalidViolationIncrease: {
        "description": "An Upgrades simulation detected an invalid increase in violations.",
        "corrective_action": "This could happen in cases when lines or transformers are extremely overloaded. Check and "
        "modify OpenDSS model for such instances.",
        "error_code": 125,
    },
}


def get_error_code_from_exception(exception_class):
    """Return the error code for a disco exception."""
    if not issubclass(exception_class, DiscoBaseException):
        raise Exception(f"exception={exception_class} is not handled")

    if exception_class in EXCEPTIONS_TO_ERROR_CODES:
        return EXCEPTIONS_TO_ERROR_CODES[exception_class]["error_code"]

    # Return a generic error code for any exceptions that we don't specifically want to map.
    return 1


def is_convergence_error(error_code):
    """Return True if the error code indicates a convergence error."""
    return error_code in {119, 120, 121, 122}
