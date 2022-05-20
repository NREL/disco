from disco.exceptions import (
    EXCEPTIONS_TO_ERROR_CODES,
    OpenDssCompileError,
    OpenDssConvergenceError,
    PyDssConvergenceError,
    PyDssConvergenceErrorCountExceeded,
    PyDssConvergenceMaxError,
    is_convergence_error,
    get_error_code_from_exception,
) 


def test_error_code_values():
    required_keys = {"description", "error_code"}
    for val in EXCEPTIONS_TO_ERROR_CODES.values():
        val.pop("corrective_action", None)
        assert not required_keys.symmetric_difference(val)

    assert len(EXCEPTIONS_TO_ERROR_CODES) == len(
        {x["error_code"] for x in EXCEPTIONS_TO_ERROR_CODES.values()}
    )

    
def test_convergence_errors():
    assert not is_convergence_error(get_error_code_from_exception(OpenDssCompileError))
    assert is_convergence_error(get_error_code_from_exception(OpenDssConvergenceError))
    assert is_convergence_error(get_error_code_from_exception(PyDssConvergenceError))
    assert is_convergence_error(get_error_code_from_exception(PyDssConvergenceErrorCountExceeded))
    assert is_convergence_error(get_error_code_from_exception(PyDssConvergenceMaxError))
