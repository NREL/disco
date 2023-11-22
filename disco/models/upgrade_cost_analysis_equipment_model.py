import logging
import numpy as np
from typing import Any
from pathlib import Path
from typing import Optional, List
from pydantic.v1 import BaseModel, Field, validator

from jade.utils.utils import load_data

logger = logging.getLogger(__name__)


class UpgradeParamsBaseModel(BaseModel):
    """Base model for all upgrade cost analysis parameters"""

    class Config:
        title = "UpgradeParamsBaseModel"
        anystr_strip_whitespace = True
        validate_assignment = True
        validate_all = True
        extra = "forbid"
        use_enum_values = False
        arbitrary_types_allowed = True

    @classmethod
    def from_file(cls, filename: Path):
        """Return an instance from a file

        Parameters
        ----------
        filename : Path

        """
        return cls(**load_data(filename))
    

class CommonLineParameters(UpgradeParamsBaseModel):
    """This model contains common line parameters that are used in linecode technical catalog, line technical catalog, line output upgrades. 
    All these fields are directly available from opendss"""
    r1: Any = Field(
        title="r1",
        description="r1",
        determine_upgrade_option=True,
        symmetrical_impedance_property=True,
    )
    x1: Any = Field(
        title="x1",
        description="x1",
        determine_upgrade_option=True,
        symmetrical_impedance_property=True,
    )
    r0: Any = Field(
        title="r0",
        description="r0",
        determine_upgrade_option=True,
        symmetrical_impedance_property=True,
    )
    x0: Any = Field(
        title="x0",
        description="x0",
        determine_upgrade_option=True,
        symmetrical_impedance_property=True,
    )
    C1: Any = Field(
        title="c1",
        description="c1",
        determine_upgrade_option=True,
        symmetrical_impedance_property=True,
    )
    C0: Any = Field(
        title="c0",
        description="c0",
        determine_upgrade_option=True,
        symmetrical_impedance_property=True,
    )
    rmatrix: List[str] = Field(
        title="rmatrix",
        description="rmatrix. If provided, should be a list.",
        determine_upgrade_option=True,
        matrix_impedance_property=True,
    )
    xmatrix: List[str] = Field(
        title="xmatrix",
        description="xmatrix. If provided, should be a list.",
        determine_upgrade_option=True,
        matrix_impedance_property=True,
    )
    cmatrix: List[str] = Field(
        title="cmatrix",
        description="cmatrix. If provided, should be a list.",
        determine_upgrade_option=True,
        matrix_impedance_property=True,
    )
    Rg: float = Field(
        title="Rg",
        description="Rg",
        determine_upgrade_option=True,
        matrix_impedance_property=True,
    )
    Xg: float = Field(
        title="Xg",
        description="Xg",
        determine_upgrade_option=True,
        matrix_impedance_property=True,
    )
    rho: float = Field(
        title="rho",
        description="rho",
        matrix_impedance_property=True,
    )
    B1: Any = Field(
        title="B1",
        description="B1",
        determine_upgrade_option=True,
    )
    B0: Any = Field(
        title="B0",
        description="B0",
        determine_upgrade_option=True,
    )
    normamps: float = Field(
        title="normamps",
        description="normamps",
        determine_upgrade_option=True,
    )
    emergamps: float = Field(
        title="emergamps",
        description="emergamps",
        determine_upgrade_option=True,
    )
    units: str = Field(
        title="units",
        description="units",
        determine_upgrade_option=True,
    )   
    faultrate: Optional[float] = Field(
        title="faultrate",
        description="faultrate",
    )
    pctperm: Optional[float] = Field(
        title="pctperm",
        description="pctperm",
    )
    repair: Optional[float] = Field(
        title="repair",
        description="repair",
    ) 
    Seasons: Optional[Any] = Field(
        title="Seasons",
        description="Seasons",
    )
    Ratings: Optional[Any] = Field(
        title="Ratings",
        description="Ratings",
    ) 
    

class OpenDSSLineParams(CommonLineParameters):

    geometry: Any = Field(
        title="geometry",
        description="geometry",
        determine_upgrade_option=True,
    )
    linecode: Any = Field(
        title="linecode",
        description="If line is defined using linecode, then name of associated line code should be provided here.",
        determine_upgrade_option=True,
    )
    phases: int = Field(
        title="phases",
        description="phases",
        determine_upgrade_option=True,
        deciding_property=True,
    )  
    EarthModel: Any = Field(
        title="EarthModel",
        description="EarthModel",
    )
    cncables: Any = Field(
        title="cncables",
        description="cncables",
    )    
    tscables: Any = Field(
        title="tscables",
        description="tscables",
    )   
    wires: Any = Field(
        title="wires",
        description="wires",
    )
    like: Any = Field(
        title="like",
        description="like",
    )
    basefreq: float = Field(
        title="basefreq",
        description="basefreq",
        determine_upgrade_option=True,
        deciding_property=True,
    )
    Switch: str = Field(
        title="Switch",
        description="Flag that determines whether line is switch or not.",
        determine_upgrade_option=True,
        deciding_property=True,
    )
    spacing: Any = Field(
        title="spacing",
        description="spacing",
        determine_upgrade_option=True,
    )
    
    @validator("Switch")
    def check_switch_property(cls, Switch):
        if Switch not in ("Yes", "No"):
            raise ValueError("Incorrect Switch type.")
        return Switch
    

class ExtraLineParams(BaseModel):
    line_definition_type: str = Field(
        title="line_definition_type",
        description="This indicates if the line is defined by using linecodes or line geometry. Possible values are linecode, geometry or line_definition."
                    "This is a computed field, not a direct OpenDSS object property",
        determine_upgrade_option=True,
    )
    kV: float = Field(
        title="kV",
        description="Line-to-Neutral kV. This is not a direct OpenDSS object property.",
        determine_upgrade_option=True,
        deciding_property=True,
    )
    h: float = Field(
        title="h",
        description="h. This is not a direct opendss line property, and is added as a new field. A value is available if line is defined as a line geometry.",
        determine_upgrade_option=True,
    )
    line_placement: str = Field(
        title="line_placement",
        description="line_placement. This is a new field, not a direct OpenDSS object property.",
        determine_upgrade_option=True,
        deciding_property=True,
    )
    
    @validator("line_definition_type")
    def check_line_definition_type(cls, line_definition_type):
        if line_definition_type not in ("linecode", "geometry", "line_definition"):
            raise ValueError(f"Incorrect Line definition type: {line_definition_type}. Acceptable values: linecode, geometry or line_definition.")
        return line_definition_type
    
    @validator("line_placement")
    def check_line_placement(cls, line_placement):
        if line_placement not in ("underground", "overhead"):
            raise ValueError(f"Incorrect Line placement type: {line_placement}. Acceptable values: overhead, underground.")
        return line_placement


class CommonTransformerParameters(UpgradeParamsBaseModel):
    """This model contains common transformer parameters which are inherited by transformer catalog, and transformer upgrade output."""
    phases: int = Field(
        title="phases",
        description="phases",
        determine_upgrade_option=True,
        deciding_property=True,
    )
    windings: int = Field(
        title="windings",
        description="windings",
        determine_upgrade_option=True,
    )
    wdg: int = Field(
        title="wdg",
        description="wdg",
        determine_upgrade_option=True,
        deciding_property=True,
    )
    conn: str = Field(
        title="conn",
        description="conn",
        determine_upgrade_option=True,
        deciding_property=True,
    )
    kV: float = Field(
        title="kV",
        description="kV",
        determine_upgrade_option=True,
        deciding_property=True,
    )
    kVA: float = Field(
        title="kVA",
        description="kVA",
        determine_upgrade_option=True,
    )
    tap: float = Field(
        title="tap",
        description="tap",
        determine_upgrade_option=True,
    )
    pctR: float = Field(
        title="pctR",
        description="pctR",
        alias="%R",
        determine_upgrade_option=True,
    )
    Rneut: float = Field(
        title="Rneut",
        description="Rneut",
        determine_upgrade_option=True,
    )
    Xneut: float = Field(
        title="Xneut",
        description="Xneut",
        determine_upgrade_option=True,
    )
    conns: List[str] = Field(
        title="conns",
        description="conns. This needs to be passed as a list.",
        determine_upgrade_option=True,
        deciding_property=True,
    )
    kVs: List[float] = Field(
        title="kVs",
        description="kVs. This needs to be passed as a list.",
        determine_upgrade_option=True,
        deciding_property=True,
    )   
    kVAs: List[float] = Field(
        title="kVAs",
        description="kVAs. This needs to be passed as a list.",
        determine_upgrade_option=True,
    )
    taps: List[float] = Field(
        title="taps",
        description="taps. This needs to be passed as a list.",
        determine_upgrade_option=True,
    )
    XHL: float = Field(
        title="XHL",
        description="XHL",
        determine_upgrade_option=True,
    )
    XHT: float = Field(
        title="XHT",
        description="XHT",
        determine_upgrade_option=True,
    )
    XLT: float = Field(
        title="XLT",
        description="XLT",
        determine_upgrade_option=True,
    )
    Xscarray: List[float] = Field(
        title="Xscarray",
        description="Xscarray",
        determine_upgrade_option=True,
    )
    thermal: Any = Field(
        title="thermal",
        description="thermal",
        determine_upgrade_option=True,
        write_property=True,
    )
    n: float = Field(
        title="n",
        description="n",
        determine_upgrade_option=True,
        write_property=True,
    )
    m: float = Field(
        title="m",
        description="m",
        determine_upgrade_option=True,
        write_property=True,
    )
    flrise: float = Field(
        title="flrise",
        description="flrise",
        determine_upgrade_option=True,
        write_property=True,
    )
    hsrise: float = Field(
        title="hsrise",
        description="hsrise",
        determine_upgrade_option=True,
        write_property=True,
    ) 
    pctloadloss: float = Field(
        title="%loadloss",
        description="%loadloss",
        alias="%loadloss",
        determine_upgrade_option=True,
        write_property=True,
    )
    pctnoloadloss: float = Field(
        title="%noloadloss",
        description="%noloadloss",
        alias="%noloadloss",
        determine_upgrade_option=True,
        write_property=True,
    )
    normhkVA: float = Field(
        title="normhkVA",
        description="normhkVA",
        determine_upgrade_option=True,
        write_property=True,
    ) 
    emerghkVA: float = Field(
        title="emerghkVA",
        description="emerghkVA",
        determine_upgrade_option=True,
        write_property=True,
    )
    sub: str = Field(
        title="sub",
        description="sub",
        determine_upgrade_option=True,
    )
    MaxTap: float = Field(
        title="MaxTap",
        description="MaxTap",
        determine_upgrade_option=True,
    ) 
    MinTap: float = Field(
        title="MinTap",
        description="MinTap",
        determine_upgrade_option=True,
    )
    NumTaps: float = Field(
        title="NumTaps",
        description="NumTaps",
        determine_upgrade_option=True,
        write_property=True,
    )
    subname: Any = Field(
        title="subname",
        description="subname",
        determine_upgrade_option=True,
    ) 
    pctimag: float = Field(
        title="%imag",
        description="%imag",
        alias="%imag",
        determine_upgrade_option=True,
        write_property=True,
    )
    ppm_antifloat: float = Field(
        title="ppm_antifloat",
        description="ppm_antifloat",
        determine_upgrade_option=True,
        write_property=True,
    )
    pctRs: List[float] = Field(
        title="%Rs",
        description="%Rs. If present, should be a list.",
        alias="%Rs",
        determine_upgrade_option=True,
    ) 
    bank: Any = Field(
        title="bank",
        description="bank",
        determine_upgrade_option=True,
    )
    XfmrCode: Any = Field(
        title="XfmrCode",
        description="XfmrCode",
        determine_upgrade_option=True,
    )
    XRConst: Any = Field(
        title="XRConst",
        description="XRConst",
        determine_upgrade_option=True,
        write_property=True,
    ) 
    X12: float = Field(
        title="X12",
        description="X12",
        determine_upgrade_option=True,
    )
    X13: float = Field(
        title="X13",
        description="X13",
        determine_upgrade_option=True,
    )
    X23: float = Field(
        title="X23",
        description="X23",
        determine_upgrade_option=True,
    ) 
    LeadLag: Any = Field(
        title="LeadLag",
        description="LeadLag",
        determine_upgrade_option=True,
        deciding_property=True,
        write_property=True,
    )
    Core: Any = Field(
        title="Core",
        description="Core",
        determine_upgrade_option=True,
        write_property=True,
    )
    RdcOhms: float = Field(
        title="RdcOhms",
        description="RdcOhms",
        determine_upgrade_option=True,
    )
    normamps: float = Field(
        title="normamps",
        description="normamps",
        determine_upgrade_option=True,
    )
    emergamps: float = Field(
        title="emergamps",
        description="emergamps",
        determine_upgrade_option=True,
    )
    faultrate: float = Field(
        title="faultrate",
        description="faultrate",
        determine_upgrade_option=True,
        write_property=True,
    )  
    pctperm: float = Field(
        title="pctperm",
        description="pctperm",
        determine_upgrade_option=True,
    )  
    basefreq: float = Field(
        title="basefreq",
        description="basefreq",
        determine_upgrade_option=True,
        deciding_property=True,
    )  
    repair: Optional[float] = Field(
        title="repair",
        description="repair",
    )
    Seasons: Optional[Any] = Field(
        title="Seasons",
        description="Seasons",
    )
    Ratings: Optional[Any] = Field(
        title="Ratings",
        description="Ratings",
    )

    
class ExtraTransformerParams(BaseModel):
    amp_limit_per_phase: float = Field(
        title="amp_limit_per_phase",
        description="amp_limit_per_phase. This is a new field, not a direct OpenDSS object property.",
        determine_upgrade_option=True,
    )
