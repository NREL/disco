"""Defines data models for OpenDSS circuit elements"""

import logging

from pydantic import BaseModel, Field, root_validator


logger = logging.getLogger(__name__)


class OpenDssBaseModel(BaseModel):
    """Base data model for all OpenDSS data models"""

    class Config:
        title = "OpenDssBaseModel"
        anystr_strip_whitespace = True
        validate_assignment = True
        validate_all = True
        extra = "forbid"
        use_enum_values = False
        arbitrary_types_allowed = True
        allow_population_by_field_name = True


class OpenDssElementBaseModel(OpenDssBaseModel):
    name: str = Field(description="Name of element")

    @root_validator(pre=True)
    def preprocess(cls, values):
        """Removes undesired fields."""
        for field in ("DSSClass", "like"):
            values.pop(field, None)
        return values

    def new_open_dss_string(self) -> str:
        """Return a string that will create a new OpenDSS element in odd.Text.Command."""
        return _get_new_element_str(self)


def _get_new_element_str(elem) -> str:
    class_name = type(elem).__name__
    match class_name:
        case "Capacitor" | "Line" | "LineCode":
            return _get_new_elem_str_with_matrices(class_name, elem)
        case "Transformer":
            return _get_new_transformer_str(class_name, elem)
        case _:
            return _get_new_default_str(class_name, elem)


def _get_new_prefix(class_name, elem_name):
    return f"New {class_name}.{elem_name}"


def _make_new_element_string(class_name, elem_name, data):
    command = _get_new_prefix(class_name, elem_name)
    fields = [f"{k}={v}" for k, v in data.items() if k != "name"]
    return command + " " + " ".join(fields)


def _get_new_default_str(class_name, elem) -> str:
    data = {}
    for key, val in elem.dict(by_alias=True).items():
        if val is None or (isinstance(val, str) and val.lower() in ("",)):
            continue
        data[key] = val
    return _make_new_element_string(class_name, elem.name, data)


def _get_new_elem_str_with_matrices(class_name, elem) -> str:
    data = {}
    matrix_fields = {"rmatrix", "xmatrix", "cmatrix"}
    for key, val in elem.dict(by_alias=True).items():
        if val is None or (isinstance(val, str) and val == ""):
            continue
        if key in matrix_fields and len(val) == 3:
            data[key] = make_3_elem_matrix_str(val)
        elif key in matrix_fields and len(val) == 6:
            data[key] = make_6_elem_matrix_str(val)
        else:
            data[key] = val
    return _make_new_element_string(class_name, elem.name, data)


def _get_new_transformer_str(class_name, elem) -> str:
    data = {}
    for key, val in elem.dict(by_alias=True).items():
        if val is None or (isinstance(val, str) and val.lower() in ("",)):
            continue
        if key == "WdgCurrents":
            val = f"[{val}]"
        data[key] = val
    return _make_new_element_string(class_name, elem.name, data)


def make_3_elem_matrix_str(m):
    return f"[{m[0]} {m[1]} | {m[2]}]"


def make_6_elem_matrix_str(m):
    return f"[{m[0]} {m[1]} {m[2]} | {m[3]} {m[4]} | {m[5]}]"
