"""This file is auto-generated. Please do not edit it manually."""

from pydantic import BaseModel, Field, root_validator

from opendss_base_model import OpenDssElementBaseModel


class LineCode(OpenDssElementBaseModel):
    """None"""

    nphases: int | None = Field(
        description="""
        Number of phases in the line this line code data represents.  Setting this property reinitializes the line code.  Impedance matrix is reset for default symmetrical component.

        DSS property name: `nphases`, DSS property index: 1.
        """
    )
    r1: float | None = Field(
        description="""
        Positive-sequence Resistance, ohms per unit length. Setting any of R1, R0, X1, X0, C1, C0 forces the program to use the symmetrical component line definition. See also Rmatrix.

        DSS property name: `r1`, DSS property index: 2.
        """
    )
    x1: float | None = Field(
        description="""
        Positive-sequence Reactance, ohms per unit length. Setting any of R1, R0, X1, X0, C1, C0 forces the program to use the symmetrical component line definition. See also Xmatrix

        DSS property name: `x1`, DSS property index: 3.
        """
    )
    r0: float | None = Field(
        description="""
        Zero-sequence Resistance, ohms per unit length. Setting any of R1, R0, X1, X0, C1, C0 forces the program to use the symmetrical component line definition.

        DSS property name: `r0`, DSS property index: 4.
        """
    )
    x0: float | None = Field(
        description="""
        Zero-sequence Reactance, ohms per unit length. Setting any of R1, R0, X1, X0, C1, C0 forces the program to use the symmetrical component line definition.

        DSS property name: `x0`, DSS property index: 5.
        """
    )
    C1: float | None = Field(
        description="""
        Positive-sequence capacitance, nf per unit length. Setting any of R1, R0, X1, X0, C1, C0 forces the program to use the symmetrical component line definition. See also Cmatrix and B1.

        DSS property name: `C1`, DSS property index: 6.
        """
    )
    C0: float | None = Field(
        description="""
        Zero-sequence capacitance, nf per unit length. Setting any of R1, R0, X1, X0, C1, C0 forces the program to use the symmetrical component line definition. See also B0.

        DSS property name: `C0`, DSS property index: 7.
        """
    )
    units: str | None = Field(
        description="""
        One of (ohms per ...) {none|mi|km|kft|m|me|ft|in|cm}.  Default is none; assumes units agree with length unitsgiven in Line object

        DSS property name: `units`, DSS property index: 8.
        """
    )
    rmatrix: list | None = Field(
        description="""
        Resistance matrix, lower triangle, ohms per unit length. Order of the matrix is the number of phases. May be used to specify the impedance of any line configuration.  For balanced line models, you may use the standard symmetrical component data definition instead.

        DSS property name: `rmatrix`, DSS property index: 9.
        """
    )
    xmatrix: list | None = Field(
        description="""
        Reactance matrix, lower triangle, ohms per unit length. Order of the matrix is the number of phases. May be used to specify the impedance of any line configuration.  For balanced line models, you may use the standard symmetrical component data definition instead.

        DSS property name: `xmatrix`, DSS property index: 10.
        """
    )
    cmatrix: list | None = Field(
        description="""
        Nodal Capacitance matrix, lower triangle, nf per unit length.Order of the matrix is the number of phases. May be used to specify the shunt capacitance of any line configuration.  For balanced line models, you may use the standard symmetrical component data definition instead.

        DSS property name: `cmatrix`, DSS property index: 11.
        """
    )
    baseFreq: float | None = Field(
        description="""
        Frequency at which impedances are specified.

        DSS property name: `baseFreq`, DSS property index: 12.
        """
    )
    normamps: float | None = Field(
        description="""
        Normal ampere limit on line.  This is the so-called Planning Limit. It may also be the value above which load will have to be dropped in a contingency.  Usually about 75% - 80% of the emergency (one-hour) rating.

        DSS property name: `normamps`, DSS property index: 13.
        """
    )
    emergamps: float | None = Field(
        description="""
        Emergency ampere limit on line (usually one-hour rating).

        DSS property name: `emergamps`, DSS property index: 14.
        """
    )
    faultrate: float | None = Field(
        description="""
        Number of faults per unit length per year.

        DSS property name: `faultrate`, DSS property index: 15.
        """
    )
    pctperm: float | None = Field(
        description="""
        Percentage of the faults that become permanent.

        DSS property name: `pctperm`, DSS property index: 16.
        """
    )
    repair: float | None = Field(
        description="""
        Hours to repair.

        DSS property name: `repair`, DSS property index: 17.
        """
    )
    Rg: float | None = Field(
        description="""
        Carson earth return resistance per unit length used to compute impedance values at base frequency.  For making better frequency adjustments. Default is 0.01805 = 60 Hz value in ohms per kft (matches default line impedances). This value is required for harmonic solutions if you wish to adjust the earth return impedances for frequency. If not, set both Rg and Xg = 0.

        DSS property name: `Rg`, DSS property index: 19.
        """
    )
    Xg: float | None = Field(
        description="""
        Carson earth return reactance per unit length used to compute impedance values at base frequency.  For making better frequency adjustments. Default value is 0.155081 = 60 Hz value in ohms per kft (matches default line impedances). This value is required for harmonic solutions if you wish to adjust the earth return impedances for frequency. If not, set both Rg and Xg = 0.

        DSS property name: `Xg`, DSS property index: 20.
        """
    )
    rho: float | None = Field(
        description="""
        Default=100 meter ohms.  Earth resitivity used to compute earth correction factor.

        DSS property name: `rho`, DSS property index: 21.
        """
    )
    neutral: int | None = Field(
        description="""
        Designates which conductor is the "neutral" conductor that will be eliminated by Kron reduction. Default is the last conductor (nphases value). After Kron reduction is set to 0. Subsequent issuing of Kron=Yes will not do anything until this property is set to a legal value. Applies only to LineCodes defined by R, X, and C matrix.

        DSS property name: `neutral`, DSS property index: 22.
        """
    )
    B1: float | None = Field(
        description="""
        Alternate way to specify C1. MicroS per unit length

        DSS property name: `B1`, DSS property index: 23.
        """
    )
    B0: float | None = Field(
        description="""
        Alternate way to specify C0. MicroS per unit length

        DSS property name: `B0`, DSS property index: 24.
        """
    )
    Seasons: int | None = Field(
        description="""
        Defines the number of ratings to be defined for the wire, to be used only when defining seasonal ratings using the "Ratings" property.

        DSS property name: `Seasons`, DSS property index: 25.
        """
    )
    Ratings: list | None = Field(
        description="""
        An array of ratings to be used when the seasonal ratings flag is True. It can be used to insert
        multiple ratings to change during a QSTS simulation to evaluate different ratings in lines.

        DSS property name: `Ratings`, DSS property index: 26.
        """
    )
    linetype: str | None = Field(
        alias="LineType",
        description="""
        Code designating the type of line.
        One of: OH, UG, UG_TS, UG_CN, SWT_LDBRK, SWT_FUSE, SWT_SECT, SWT_REC, SWT_DISC, SWT_BRK, SWT_ELBOW, BUSBAR

        OpenDSS currently does not use this internally. For whatever purpose the user defines. Default is OH.

        DSS property name: `LineType`, DSS property index: 27.
        """,
    )

    @root_validator(pre=True)
    def drop_fields(cls, values):
        """Removes undesired fields."""
        values.pop("Kron", None)
        return values


class LoadShape(OpenDssElementBaseModel):
    """None"""

    npts: int | None = Field(
        description="""
        Max number of points to expect in load shape vectors. This gets reset to the number of multiplier values found (in files only) if less than specified.

        DSS property name: `npts`, DSS property index: 1.
        """
    )
    interval: float | None = Field(
        description="""
        Time interval for fixed interval data, hrs. Default = 1. If Interval = 0 then time data (in hours) may be at either regular or  irregular intervals and time value must be specified using either the Hour property or input files. Then values are interpolated when Interval=0, but not for fixed interval data.

        See also "sinterval" and "minterval".

        DSS property name: `interval`, DSS property index: 2.
        """
    )
    hour: list | None = Field(
        description="""
        Array of hour values. Only necessary to define for variable interval data (Interval=0). If you set Interval>0 to denote fixed interval data, DO NOT USE THIS PROPERTY. You can also use the syntax:
        hour = (file=filename)     !for text file one value per line
        hour = (dblfile=filename)  !for packed file of doubles
        hour = (sngfile=filename)  !for packed file of singles

        DSS property name: `hour`, DSS property index: 4.
        """
    )
    mean: float | None = Field(
        description="""
        Mean of the active power multipliers.  This is computed on demand the first time a value is needed.  However, you may set it to another value independently. Used for Monte Carlo load simulations.

        DSS property name: `mean`, DSS property index: 5.
        """
    )
    stddev: float | None = Field(
        description="""
        Standard deviation of active power multipliers.  This is computed on demand the first time a value is needed.  However, you may set it to another value independently.Is overwritten if you subsequently read in a curve

        Used for Monte Carlo load simulations.

        DSS property name: `stddev`, DSS property index: 6.
        """
    )
    csvfile: str | None = Field(
        description="""
        Switch input of active power load curve data to a CSV text file containing (hour, mult) points, or simply (mult) values for fixed time interval data, one per line. NOTE: This action may reset the number of points to a lower value.

        DSS property name: `csvfile`, DSS property index: 7.
        """
    )
    sngfile: str | None = Field(
        description="""
        Switch input of active power load curve data to a binary file of singles containing (hour, mult) points, or simply (mult) values for fixed time interval data, packed one after another. NOTE: This action may reset the number of points to a lower value.

        DSS property name: `sngfile`, DSS property index: 8.
        """
    )
    dblfile: str | None = Field(
        description="""
        Switch input of active power load curve data to a binary file of doubles containing (hour, mult) points, or simply (mult) values for fixed time interval data, packed one after another. NOTE: This action may reset the number of points to a lower value.

        DSS property name: `dblfile`, DSS property index: 9.
        """
    )
    qmult: list | None = Field(
        description="""
        Array of multiplier values for reactive power (Q).  You can also use the syntax:
        qmult = (file=filename)     !for text file one value per line
        qmult = (dblfile=filename)  !for packed file of doubles
        qmult = (sngfile=filename)  !for packed file of singles
        qmult = (file=MyCSVFile.csv, col=4, header=yes)  !for multicolumn CSV files

        DSS property name: `qmult`, DSS property index: 11.
        """
    )
    UseActual: bool | None = Field(
        description="""
        {Yes | No* | True | False*} If true, signifies to Load, Generator, Vsource, or other objects to use the return value as the actual kW, kvar, kV, or other value rather than a multiplier. Nominally for AMI Load data but may be used for other functions.

        DSS property name: `UseActual`, DSS property index: 12.
        """
    )
    Pmax: float | None = Field(
        description="""
        kW value at the time of max power. Is automatically set upon reading in a loadshape. Use this property to override the value automatically computed or to retrieve the value computed.

        DSS property name: `Pmax`, DSS property index: 13.
        """
    )
    Qmax: float | None = Field(
        description="""
        kvar value at the time of max kW power. Is automatically set upon reading in a loadshape. Use this property to override the value automatically computed or to retrieve the value computed.

        DSS property name: `Qmax`, DSS property index: 14.
        """
    )
    sinterval: float | None = Field(
        description="""
        Specify fixed interval in SECONDS. Alternate way to specify Interval property.

        DSS property name: `sinterval`, DSS property index: 15.
        """
    )
    minterval: float | None = Field(
        description="""
        Specify fixed interval in MINUTES. Alternate way to specify Interval property.

        DSS property name: `minterval`, DSS property index: 16.
        """
    )
    Pbase: float | None = Field(
        description="""
        Base P value for normalization. Default is zero, meaning the peak will be used.

        DSS property name: `Pbase`, DSS property index: 17.
        """
    )
    Qbase: float | None = Field(
        description="""
        Base Q value for normalization. Default is zero, meaning the peak will be used.

        DSS property name: `Qbase`, DSS property index: 18.
        """
    )
    Pmult: list | None = Field(
        description="""
        Synonym for "mult".

        DSS property name: `Pmult`, DSS property index: 19.
        """
    )
    PQCSVFile: str | None = Field(
        description="""
        Switch input to a CSV text file containing (active, reactive) power (P, Q) multiplier pairs, one per row.
        If the interval=0, there should be 3 items on each line: (hour, Pmult, Qmult)

        DSS property name: `PQCSVFile`, DSS property index: 20.
        """
    )
    MemoryMapping: bool | None = Field(
        description="""
        {Yes | No* | True | False*} Enables the memory mapping functionality for dealing with large amounts of load shapes.
        By defaul is False. Use it to accelerate the model loading when the containing a large number of load shapes.

        DSS property name: `MemoryMapping`, DSS property index: 21.
        """
    )
    Interpolation: str | None = Field(
        description="""
        {AVG* | EDGE} Defines the interpolation method used for connecting distant dots within the load shape.

        By defaul is AVG (average), which will return a multiplier for missing intervals based on the closest multiplier in time.
        EDGE interpolation keeps the last known value for missing intervals until the next defined multiplier arrives.

        DSS property name: `Interpolation`, DSS property index: 22.
        """
    )

    @root_validator(pre=True)
    def drop_fields(cls, values):
        """Removes undesired fields."""
        values.pop("action", None)
        values.pop("mult", None)
        return values


class TShape(OpenDssElementBaseModel):
    """None"""

    npts: int | None = Field(
        description="""
        Max number of points to expect in temperature shape vectors. This gets reset to the number of Temperature values found if less than specified.

        DSS property name: `npts`, DSS property index: 1.
        """
    )
    interval: float | None = Field(
        description="""
        Time interval for fixed interval data, hrs. Default = 1. If Interval = 0 then time data (in hours) may be at irregular intervals and time value must be specified using either the Hour property or input files. Then values are interpolated when Interval=0, but not for fixed interval data.

        See also "sinterval" and "minterval".

        DSS property name: `interval`, DSS property index: 2.
        """
    )
    temp: list | None = Field(
        description="""
        Array of temperature values.  Units should be compatible with the object using the data. You can also use the syntax:
        Temp = (file=filename)     !for text file one value per line
        Temp = (dblfile=filename)  !for packed file of doubles
        Temp = (sngfile=filename)  !for packed file of singles

        Note: this property will reset Npts if the  number of values in the files are fewer.

        DSS property name: `temp`, DSS property index: 3.
        """
    )
    hour: list | None = Field(
        description="""
        Array of hour values. Only necessary to define this property for variable interval data. If the data are fixed interval, do not use this property. You can also use the syntax:
        hour = (file=filename)     !for text file one value per line
        hour = (dblfile=filename)  !for packed file of doubles
        hour = (sngfile=filename)  !for packed file of singles

        DSS property name: `hour`, DSS property index: 4.
        """
    )
    mean: float | None = Field(
        description="""
        Mean of the temperature curve values.  This is computed on demand the first time a value is needed.  However, you may set it to another value independently. Used for Monte Carlo load simulations.

        DSS property name: `mean`, DSS property index: 5.
        """
    )
    stddev: float | None = Field(
        description="""
        Standard deviation of the temperatures.  This is computed on demand the first time a value is needed.  However, you may set it to another value independently.Is overwritten if you subsequently read in a curve

        Used for Monte Carlo load simulations.

        DSS property name: `stddev`, DSS property index: 6.
        """
    )
    csvfile: str | None = Field(
        description="""
        Switch input of  temperature curve data to a csv file containing (hour, Temp) points, or simply (Temp) values for fixed time interval data, one per line. NOTE: This action may reset the number of points to a lower value.

        DSS property name: `csvfile`, DSS property index: 7.
        """
    )
    sngfile: str | None = Field(
        description="""
        Switch input of  temperature curve data to a binary file of singles containing (hour, Temp) points, or simply (Temp) values for fixed time interval data, packed one after another. NOTE: This action may reset the number of points to a lower value.

        DSS property name: `sngfile`, DSS property index: 8.
        """
    )
    dblfile: str | None = Field(
        description="""
        Switch input of  temperature curve data to a binary file of doubles containing (hour, Temp) points, or simply (Temp) values for fixed time interval data, packed one after another. NOTE: This action may reset the number of points to a lower value.

        DSS property name: `dblfile`, DSS property index: 9.
        """
    )
    sinterval: float | None = Field(
        description="""
        Specify fixed interval in SECONDS. Alternate way to specify Interval property.

        DSS property name: `sinterval`, DSS property index: 10.
        """
    )
    minterval: float | None = Field(
        description="""
        Specify fixed interval in MINUTES. Alternate way to specify Interval property.

        DSS property name: `minterval`, DSS property index: 11.
        """
    )

    @root_validator(pre=True)
    def drop_fields(cls, values):
        """Removes undesired fields."""
        return values


class PriceShape(OpenDssElementBaseModel):
    """None"""

    npts: int | None = Field(
        description="""
        Max number of points to expect in price shape vectors. This gets reset to the number of Price values found if less than specified.

        DSS property name: `npts`, DSS property index: 1.
        """
    )
    interval: float | None = Field(
        description="""
        Time interval for fixed interval data, hrs. Default = 1. If Interval = 0 then time data (in hours) may be at irregular intervals and time value must be specified using either the Hour property or input files. Then values are interpolated when Interval=0, but not for fixed interval data.

        See also "sinterval" and "minterval".

        DSS property name: `interval`, DSS property index: 2.
        """
    )
    price: list | None = Field(
        description="""
        Array of Price values.  Units should be compatible with the object using the data. You can also use the syntax:
        Price = (file=filename)     !for text file one value per line
        Price = (dblfile=filename)  !for packed file of doubles
        Price = (sngfile=filename)  !for packed file of singles

        Note: this property will reset Npts if the  number of values in the files are fewer.

        DSS property name: `price`, DSS property index: 3.
        """
    )
    hour: list | None = Field(
        description="""
        Array of hour values. Only necessary to define this property for variable interval data. If the data are fixed interval, do not use this property. You can also use the syntax:
        hour = (file=filename)     !for text file one value per line
        hour = (dblfile=filename)  !for packed file of doubles
        hour = (sngfile=filename)  !for packed file of singles

        DSS property name: `hour`, DSS property index: 4.
        """
    )
    mean: float | None = Field(
        description="""
        Mean of the Price curve values.  This is computed on demand the first time a value is needed.  However, you may set it to another value independently. Used for Monte Carlo load simulations.

        DSS property name: `mean`, DSS property index: 5.
        """
    )
    stddev: float | None = Field(
        description="""
        Standard deviation of the Prices.  This is computed on demand the first time a value is needed.  However, you may set it to another value independently.Is overwritten if you subsequently read in a curve

        Used for Monte Carlo load simulations.

        DSS property name: `stddev`, DSS property index: 6.
        """
    )
    csvfile: str | None = Field(
        description="""
        Switch input of  Price curve data to a csv file containing (hour, Price) points, or simply (Price) values for fixed time interval data, one per line. NOTE: This action may reset the number of points to a lower value.

        DSS property name: `csvfile`, DSS property index: 7.
        """
    )
    sngfile: str | None = Field(
        description="""
        Switch input of  Price curve data to a binary file of singles containing (hour, Price) points, or simply (Price) values for fixed time interval data, packed one after another. NOTE: This action may reset the number of points to a lower value.

        DSS property name: `sngfile`, DSS property index: 8.
        """
    )
    dblfile: str | None = Field(
        description="""
        Switch input of  Price curve data to a binary file of doubles containing (hour, Price) points, or simply (Price) values for fixed time interval data, packed one after another. NOTE: This action may reset the number of points to a lower value.

        DSS property name: `dblfile`, DSS property index: 9.
        """
    )
    sinterval: float | None = Field(
        description="""
        Specify fixed interval in SECONDS. Alternate way to specify Interval property.

        DSS property name: `sinterval`, DSS property index: 10.
        """
    )
    minterval: float | None = Field(
        description="""
        Specify fixed interval in MINUTES. Alternate way to specify Interval property.

        DSS property name: `minterval`, DSS property index: 11.
        """
    )

    @root_validator(pre=True)
    def drop_fields(cls, values):
        """Removes undesired fields."""
        return values


class XYcurve(OpenDssElementBaseModel):
    """None"""

    npts: int | None = Field(
        description="""
        Max number of points to expect in curve. This could get reset to the actual number of points defined if less than specified.

        DSS property name: `npts`, DSS property index: 1.
        """
    )
    Yarray: list | None = Field(
        description="""
        Alternate way to enter Y values. Enter an array of Y values corresponding to the X values.  You can also use the syntax:
        Yarray = (file=filename)     !for text file one value per line
        Yarray = (dblfile=filename)  !for packed file of doubles
        Yarray = (sngfile=filename)  !for packed file of singles

        Note: this property will reset Npts to a smaller value if the  number of values in the files are fewer.

        DSS property name: `Yarray`, DSS property index: 3.
        """
    )
    Xarray: list | None = Field(
        description="""
        Alternate way to enter X values. Enter an array of X values corresponding to the Y values.  You can also use the syntax:
        Xarray = (file=filename)     !for text file one value per line
        Xarray = (dblfile=filename)  !for packed file of doubles
        Xarray = (sngfile=filename)  !for packed file of singles

        Note: this property will reset Npts to a smaller value if the  number of values in the files are fewer.

        DSS property name: `Xarray`, DSS property index: 4.
        """
    )
    csvfile: str | None = Field(
        description="""
        Switch input of  X-Y curve data to a CSV file containing X, Y points one per line. NOTE: This action may reset the number of points to a lower value.

        DSS property name: `csvfile`, DSS property index: 5.
        """
    )
    sngfile: str | None = Field(
        description="""
        Switch input of  X-Y curve data to a binary file of SINGLES containing X, Y points packed one after another. NOTE: This action may reset the number of points to a lower value.

        DSS property name: `sngfile`, DSS property index: 6.
        """
    )
    dblfile: str | None = Field(
        description="""
        Switch input of  X-Y  curve data to a binary file of DOUBLES containing X, Y points packed one after another. NOTE: This action may reset the number of points to a lower value.

        DSS property name: `dblfile`, DSS property index: 7.
        """
    )
    x: float | None = Field(
        description="""
        Enter a value and then retrieve the interpolated Y value from the Y property. On input shifted then scaled to original curve. Scaled then shifted on output.

        DSS property name: `x`, DSS property index: 8.
        """
    )
    y: float | None = Field(
        description="""
        Enter a value and then retrieve the interpolated X value from the X property. On input shifted then scaled to original curve. Scaled then shifted on output.

        DSS property name: `y`, DSS property index: 9.
        """
    )
    Xshift: float | None = Field(
        description="""
        Shift X property values (in/out) by this amount of offset. Default = 0. Does not change original definition of arrays.

        DSS property name: `Xshift`, DSS property index: 10.
        """
    )
    Yshift: float | None = Field(
        description="""
        Shift Y property values (in/out) by this amount of offset. Default = 0. Does not change original definition of arrays.

        DSS property name: `Yshift`, DSS property index: 11.
        """
    )
    Xscale: float | None = Field(
        description="""
        Scale X property values (in/out) by this factor. Default = 1.0. Does not change original definition of arrays.

        DSS property name: `Xscale`, DSS property index: 12.
        """
    )
    Yscale: float | None = Field(
        description="""
        Scale Y property values (in/out) by this factor. Default = 1.0. Does not change original definition of arrays.

        DSS property name: `Yscale`, DSS property index: 13.
        """
    )

    @root_validator(pre=True)
    def drop_fields(cls, values):
        """Removes undesired fields."""
        return values


class GrowthShape(OpenDssElementBaseModel):
    """None"""

    npts: int | None = Field(
        description="""
        Number of points to expect in subsequent vector.

        DSS property name: `npts`, DSS property index: 1.
        """
    )
    year: list | None = Field(
        description="""
        Array of year values, or a text file spec, corresponding to the multipliers. Enter only those years where the growth changes. May be any integer sequence -- just so it is consistent. See help on Mult.

        DSS property name: `year`, DSS property index: 2.
        """
    )
    mult: list | None = Field(
        description="""
        Array of growth multiplier values, or a text file spec, corresponding to the year values. Enter the multiplier by which you would multiply the previous year's load to get the present year's.

        Examples:

          Year = [1, 2, 5]   Mult=[1.05, 1.025, 1.02].
          Year= (File=years.txt) Mult= (file=mults.txt).

        Text files contain one value per line.

        DSS property name: `mult`, DSS property index: 3.
        """
    )
    csvfile: str | None = Field(
        description="""
        Switch input of growth curve data to a csv file containing (year, mult) points, one per line.

        DSS property name: `csvfile`, DSS property index: 4.
        """
    )
    sngfile: str | None = Field(
        description="""
        Switch input of growth curve data to a binary file of singles containing (year, mult) points, packed one after another.

        DSS property name: `sngfile`, DSS property index: 5.
        """
    )
    dblfile: str | None = Field(
        description="""
        Switch input of growth curve data to a binary file of doubles containing (year, mult) points, packed one after another.

        DSS property name: `dblfile`, DSS property index: 6.
        """
    )

    @root_validator(pre=True)
    def drop_fields(cls, values):
        """Removes undesired fields."""
        return values


class TCC_Curve(OpenDssElementBaseModel):
    """None"""

    npts: int | None = Field(
        description="""
        Number of points to expect in time-current arrays.

        DSS property name: `npts`, DSS property index: 1.
        """
    )
    C_array: list | None = Field(
        description="""
        Array of current (or voltage) values corresponding to time values (see help on T_Array).

        DSS property name: `C_array`, DSS property index: 2.
        """
    )
    T_array: list | None = Field(
        description="""
        Array of time values in sec. Typical array syntax:
        t_array = (1, 2, 3, 4, ...)

        Can also substitute a file designation:
        t_array =  (file=filename)

        The specified file has one value per line.

        DSS property name: `T_array`, DSS property index: 3.
        """
    )

    @root_validator(pre=True)
    def drop_fields(cls, values):
        """Removes undesired fields."""
        return values


class Spectrum(OpenDssElementBaseModel):
    """None"""

    NumHarm: int | None = Field(
        description="""
        Number of frequencies in this spectrum. (See CSVFile)

        DSS property name: `NumHarm`, DSS property index: 1.
        """
    )
    harmonic: list | None = Field(
        description="""
        Array of harmonic values. You can also use the syntax
        harmonic = (file=filename)     !for text file one value per line
        harmonic = (dblfile=filename)  !for packed file of doubles
        harmonic = (sngfile=filename)  !for packed file of singles

        DSS property name: `harmonic`, DSS property index: 2.
        """
    )
    pctmag: list | None = Field(
        alias="%mag",
        description="""
        Array of magnitude values, assumed to be in PERCENT. You can also use the syntax
        %mag = (file=filename)     !for text file one value per line
        %mag = (dblfile=filename)  !for packed file of doubles
        %mag = (sngfile=filename)  !for packed file of singles

        DSS property name: `%mag`, DSS property index: 3.
        """,
    )
    angle: list | None = Field(
        description="""
        Array of phase angle values, degrees.You can also use the syntax
        angle = (file=filename)     !for text file one value per line
        angle = (dblfile=filename)  !for packed file of doubles
        angle = (sngfile=filename)  !for packed file of singles

        DSS property name: `angle`, DSS property index: 4.
        """
    )
    CSVFile: str | None = Field(
        description="""
        File of spectrum points with (harmonic, magnitude-percent, angle-degrees) values, one set of 3 per line, in CSV format. If fewer than NUMHARM frequencies found in the file, NUMHARM is set to the smaller value.

        DSS property name: `CSVFile`, DSS property index: 5.
        """
    )

    @root_validator(pre=True)
    def drop_fields(cls, values):
        """Removes undesired fields."""
        return values


class WireData(OpenDssElementBaseModel):
    """None"""

    Rdc: float | None = Field(
        description="""
        dc Resistance, ohms per unit length (see Runits). Defaults to Rac/1.02 if not specified.

        DSS property name: `Rdc`, DSS property index: 1.
        """
    )
    Rac: float | None = Field(
        description="""
        Resistance at 60 Hz per unit length. Defaults to 1.02*Rdc if not specified.

        DSS property name: `Rac`, DSS property index: 2.
        """
    )
    Runits: str | None = Field(
        description="""
        Length units for resistance: ohms per {mi|kft|km|m|Ft|in|cm|mm} Default=none.

        DSS property name: `Runits`, DSS property index: 3.
        """
    )
    GMRac: float | None = Field(
        description="""
        GMR at 60 Hz. Defaults to .7788*radius if not specified.

        DSS property name: `GMRac`, DSS property index: 4.
        """
    )
    GMRunits: str | None = Field(
        description="""
        Units for GMR: {mi|kft|km|m|Ft|in|cm|mm} Default=none.

        DSS property name: `GMRunits`, DSS property index: 5.
        """
    )
    radius: float | None = Field(
        description="""
        Outside radius of conductor. Defaults to GMR/0.7788 if not specified.

        DSS property name: `radius`, DSS property index: 6.
        """
    )
    radunits: str | None = Field(
        description="""
        Units for outside radius: {mi|kft|km|m|Ft|in|cm|mm} Default=none.

        DSS property name: `radunits`, DSS property index: 7.
        """
    )
    normamps: float | None = Field(
        description="""
        Normal ampacity, amperes. Defaults to Emergency amps/1.5 if not specified.

        DSS property name: `normamps`, DSS property index: 8.
        """
    )
    emergamps: float | None = Field(
        description="""
        Emergency ampacity, amperes. Defaults to 1.5 * Normal Amps if not specified.

        DSS property name: `emergamps`, DSS property index: 9.
        """
    )
    diam: float | None = Field(
        description="""
        Diameter; Alternative method for entering radius.

        DSS property name: `diam`, DSS property index: 10.
        """
    )
    Seasons: int | None = Field(
        description="""
        Defines the number of ratings to be defined for the wire, to be used only when defining seasonal ratings using the "Ratings" property.

        DSS property name: `Seasons`, DSS property index: 11.
        """
    )
    Ratings: list | None = Field(
        description="""
        An array of ratings to be used when the seasonal ratings flag is True. It can be used to insert
        multiple ratings to change during a QSTS simulation to evaluate different ratings in lines.

        DSS property name: `Ratings`, DSS property index: 12.
        """
    )
    Capradius: float | None = Field(
        description="""
        Equivalent conductor radius for capacitance calcs. Specify this for bundled conductors. Defaults to same value as radius. Define Diam or Radius property first.

        DSS property name: `Capradius`, DSS property index: 13.
        """
    )

    @root_validator(pre=True)
    def drop_fields(cls, values):
        """Removes undesired fields."""
        return values


class CNData(OpenDssElementBaseModel):
    """None"""

    k: int | None = Field(
        description="""
        Number of concentric neutral strands; default is 2

        DSS property name: `k`, DSS property index: 1.
        """
    )
    DiaStrand: float | None = Field(
        description="""
        Diameter of a concentric neutral strand; same units as core conductor radius; no default.

        DSS property name: `DiaStrand`, DSS property index: 2.
        """
    )
    GmrStrand: float | None = Field(
        description="""
        Geometric mean radius of a concentric neutral strand; same units as core conductor GMR; defaults to 0.7788 * CN strand radius.

        DSS property name: `GmrStrand`, DSS property index: 3.
        """
    )
    Rstrand: float | None = Field(
        description="""
        AC resistance of a concentric neutral strand; same units as core conductor resistance; no default.

        DSS property name: `Rstrand`, DSS property index: 4.
        """
    )
    EpsR: float | None = Field(
        description="""
        Insulation layer relative permittivity; default is 2.3.

        DSS property name: `EpsR`, DSS property index: 5.
        """
    )
    InsLayer: float | None = Field(
        description="""
        Insulation layer thickness; same units as radius; no default. With DiaIns, establishes inner radius for capacitance calculation.

        DSS property name: `InsLayer`, DSS property index: 6.
        """
    )
    DiaIns: float | None = Field(
        description="""
        Diameter over insulation layer; same units as radius; no default. Establishes outer radius for capacitance calculation.

        DSS property name: `DiaIns`, DSS property index: 7.
        """
    )
    DiaCable: float | None = Field(
        description="""
        Diameter over cable; same units as radius; no default.

        DSS property name: `DiaCable`, DSS property index: 8.
        """
    )
    Rdc: float | None = Field(
        description="""
        dc Resistance, ohms per unit length (see Runits). Defaults to Rac/1.02 if not specified.

        DSS property name: `Rdc`, DSS property index: 9.
        """
    )
    Rac: float | None = Field(
        description="""
        Resistance at 60 Hz per unit length. Defaults to 1.02*Rdc if not specified.

        DSS property name: `Rac`, DSS property index: 10.
        """
    )
    Runits: str | None = Field(
        description="""
        Length units for resistance: ohms per {mi|kft|km|m|Ft|in|cm|mm} Default=none.

        DSS property name: `Runits`, DSS property index: 11.
        """
    )
    GMRac: float | None = Field(
        description="""
        GMR at 60 Hz. Defaults to .7788*radius if not specified.

        DSS property name: `GMRac`, DSS property index: 12.
        """
    )
    GMRunits: str | None = Field(
        description="""
        Units for GMR: {mi|kft|km|m|Ft|in|cm|mm} Default=none.

        DSS property name: `GMRunits`, DSS property index: 13.
        """
    )
    radius: float | None = Field(
        description="""
        Outside radius of conductor. Defaults to GMR/0.7788 if not specified.

        DSS property name: `radius`, DSS property index: 14.
        """
    )
    radunits: str | None = Field(
        description="""
        Units for outside radius: {mi|kft|km|m|Ft|in|cm|mm} Default=none.

        DSS property name: `radunits`, DSS property index: 15.
        """
    )
    normamps: float | None = Field(
        description="""
        Normal ampacity, amperes. Defaults to Emergency amps/1.5 if not specified.

        DSS property name: `normamps`, DSS property index: 16.
        """
    )
    emergamps: float | None = Field(
        description="""
        Emergency ampacity, amperes. Defaults to 1.5 * Normal Amps if not specified.

        DSS property name: `emergamps`, DSS property index: 17.
        """
    )
    diam: float | None = Field(
        description="""
        Diameter; Alternative method for entering radius.

        DSS property name: `diam`, DSS property index: 18.
        """
    )
    Seasons: int | None = Field(
        description="""
        Defines the number of ratings to be defined for the wire, to be used only when defining seasonal ratings using the "Ratings" property.

        DSS property name: `Seasons`, DSS property index: 19.
        """
    )
    Ratings: list | None = Field(
        description="""
        An array of ratings to be used when the seasonal ratings flag is True. It can be used to insert
        multiple ratings to change during a QSTS simulation to evaluate different ratings in lines.

        DSS property name: `Ratings`, DSS property index: 20.
        """
    )
    Capradius: float | None = Field(
        description="""
        Equivalent conductor radius for capacitance calcs. Specify this for bundled conductors. Defaults to same value as radius. Define Diam or Radius property first.

        DSS property name: `Capradius`, DSS property index: 21.
        """
    )

    @root_validator(pre=True)
    def drop_fields(cls, values):
        """Removes undesired fields."""
        return values


class TSData(OpenDssElementBaseModel):
    """None"""

    DiaShield: float | None = Field(
        description="""
        Diameter over tape shield; same units as radius; no default.

        DSS property name: `DiaShield`, DSS property index: 1.
        """
    )
    TapeLayer: float | None = Field(
        description="""
        Tape shield thickness; same units as radius; no default.

        DSS property name: `TapeLayer`, DSS property index: 2.
        """
    )
    TapeLap: float | None = Field(
        description="""
        Tape Lap in percent; default 20.0

        DSS property name: `TapeLap`, DSS property index: 3.
        """
    )
    EpsR: float | None = Field(
        description="""
        Insulation layer relative permittivity; default is 2.3.

        DSS property name: `EpsR`, DSS property index: 4.
        """
    )
    InsLayer: float | None = Field(
        description="""
        Insulation layer thickness; same units as radius; no default. With DiaIns, establishes inner radius for capacitance calculation.

        DSS property name: `InsLayer`, DSS property index: 5.
        """
    )
    DiaIns: float | None = Field(
        description="""
        Diameter over insulation layer; same units as radius; no default. Establishes outer radius for capacitance calculation.

        DSS property name: `DiaIns`, DSS property index: 6.
        """
    )
    DiaCable: float | None = Field(
        description="""
        Diameter over cable; same units as radius; no default.

        DSS property name: `DiaCable`, DSS property index: 7.
        """
    )
    Rdc: float | None = Field(
        description="""
        dc Resistance, ohms per unit length (see Runits). Defaults to Rac/1.02 if not specified.

        DSS property name: `Rdc`, DSS property index: 8.
        """
    )
    Rac: float | None = Field(
        description="""
        Resistance at 60 Hz per unit length. Defaults to 1.02*Rdc if not specified.

        DSS property name: `Rac`, DSS property index: 9.
        """
    )
    Runits: str | None = Field(
        description="""
        Length units for resistance: ohms per {mi|kft|km|m|Ft|in|cm|mm} Default=none.

        DSS property name: `Runits`, DSS property index: 10.
        """
    )
    GMRac: float | None = Field(
        description="""
        GMR at 60 Hz. Defaults to .7788*radius if not specified.

        DSS property name: `GMRac`, DSS property index: 11.
        """
    )
    GMRunits: str | None = Field(
        description="""
        Units for GMR: {mi|kft|km|m|Ft|in|cm|mm} Default=none.

        DSS property name: `GMRunits`, DSS property index: 12.
        """
    )
    radius: float | None = Field(
        description="""
        Outside radius of conductor. Defaults to GMR/0.7788 if not specified.

        DSS property name: `radius`, DSS property index: 13.
        """
    )
    radunits: str | None = Field(
        description="""
        Units for outside radius: {mi|kft|km|m|Ft|in|cm|mm} Default=none.

        DSS property name: `radunits`, DSS property index: 14.
        """
    )
    normamps: float | None = Field(
        description="""
        Normal ampacity, amperes. Defaults to Emergency amps/1.5 if not specified.

        DSS property name: `normamps`, DSS property index: 15.
        """
    )
    emergamps: float | None = Field(
        description="""
        Emergency ampacity, amperes. Defaults to 1.5 * Normal Amps if not specified.

        DSS property name: `emergamps`, DSS property index: 16.
        """
    )
    diam: float | None = Field(
        description="""
        Diameter; Alternative method for entering radius.

        DSS property name: `diam`, DSS property index: 17.
        """
    )
    Seasons: int | None = Field(
        description="""
        Defines the number of ratings to be defined for the wire, to be used only when defining seasonal ratings using the "Ratings" property.

        DSS property name: `Seasons`, DSS property index: 18.
        """
    )
    Ratings: list | None = Field(
        description="""
        An array of ratings to be used when the seasonal ratings flag is True. It can be used to insert
        multiple ratings to change during a QSTS simulation to evaluate different ratings in lines.

        DSS property name: `Ratings`, DSS property index: 19.
        """
    )
    Capradius: float | None = Field(
        description="""
        Equivalent conductor radius for capacitance calcs. Specify this for bundled conductors. Defaults to same value as radius. Define Diam or Radius property first.

        DSS property name: `Capradius`, DSS property index: 20.
        """
    )

    @root_validator(pre=True)
    def drop_fields(cls, values):
        """Removes undesired fields."""
        return values


class LineSpacing(OpenDssElementBaseModel):
    """None"""

    nconds: int | None = Field(
        description="""
        Number of wires in this geometry. Default is 3. Triggers memory allocations. Define first!

        DSS property name: `nconds`, DSS property index: 1.
        """
    )
    nphases: int | None = Field(
        description="""
        Number of retained phase conductors. If less than the number of wires, list the retained phase coordinates first.

        DSS property name: `nphases`, DSS property index: 2.
        """
    )
    x: list | None = Field(
        description="""
        Array of wire X coordinates.

        DSS property name: `x`, DSS property index: 3.
        """
    )
    h: list | None = Field(
        description="""
        Array of wire Heights.

        DSS property name: `h`, DSS property index: 4.
        """
    )
    units: str | None = Field(
        description="""
        Units for x and h: {mi|kft|km|m|Ft|in|cm } Initial default is "ft", but defaults to last unit defined

        DSS property name: `units`, DSS property index: 5.
        """
    )

    @root_validator(pre=True)
    def drop_fields(cls, values):
        """Removes undesired fields."""
        return values


class LineGeometry(OpenDssElementBaseModel):
    """None"""

    nconds: int | None = Field(
        description="""
        Number of conductors in this geometry. Default is 3. Triggers memory allocations. Define first!

        DSS property name: `nconds`, DSS property index: 1.
        """
    )
    nphases: int | None = Field(
        description="""
        Number of phases. Default =3; All other conductors are considered neutrals and might be reduced out.

        DSS property name: `nphases`, DSS property index: 2.
        """
    )
    wire: list | None = Field(
        description="""
        Code from WireData. MUST BE PREVIOUSLY DEFINED. no default.
        Specifies use of Overhead Line parameter calculation,
        Unless Tape Shield cable previously assigned to phases, and this wire is a neutral.

        DSS property name: `wire`, DSS property index: 4.
        """
    )
    x: list | None = Field(
        description="""
        x coordinate.

        DSS property name: `x`, DSS property index: 5.
        """
    )
    h: list | None = Field(
        description="""
        Height of conductor.

        DSS property name: `h`, DSS property index: 6.
        """
    )
    units: str | None = Field(
        description="""
        Units for x and h: {mi|kft|km|m|Ft|in|cm } Initial default is "ft", but defaults to last unit defined

        DSS property name: `units`, DSS property index: 7.
        """
    )
    normamps: float | None = Field(
        description="""
        Normal ampacity, amperes for the line. Defaults to first conductor if not specified.

        DSS property name: `normamps`, DSS property index: 8.
        """
    )
    emergamps: float | None = Field(
        description="""
        Emergency ampacity, amperes. Defaults to first conductor if not specified.

        DSS property name: `emergamps`, DSS property index: 9.
        """
    )
    reduce: bool | None = Field(
        description="""
        {Yes | No} Default = no. Reduce to Nphases (Kron Reduction). Reduce out neutrals.

        DSS property name: `reduce`, DSS property index: 10.
        """
    )
    spacing: str | None = Field(
        description="""
        Reference to a LineSpacing for use in a line constants calculation.
        Alternative to x, h, and units. MUST BE PREVIOUSLY DEFINED.
        Must match "nconds" as previously defined for this geometry.
        Must be used in conjunction with the Wires property.

        DSS property name: `spacing`, DSS property index: 11.
        """
    )
    Seasons: int | None = Field(
        description="""
        Defines the number of ratings to be defined for the wire, to be used only when defining seasonal ratings using the "Ratings" property. Defaults to first conductor if not specified.

        DSS property name: `Seasons`, DSS property index: 17.
        """
    )
    Ratings: list | None = Field(
        description="""
        An array of ratings to be used when the seasonal ratings flag is True. It can be used to insert
        multiple ratings to change during a QSTS simulation to evaluate different ratings in lines.Defaults to first conductor if not specified.

        DSS property name: `Ratings`, DSS property index: 18.
        """
    )
    linetype: str | None = Field(
        description="""
        Code designating the type of line.
        One of: OH, UG, UG_TS, UG_CN, SWT_LDBRK, SWT_FUSE, SWT_SECT, SWT_REC, SWT_DISC, SWT_BRK, SWT_ELBOW, BUSBAR

        OpenDSS currently does not use this internally. For whatever purpose the user defines. Default is OH.

        DSS property name: `LineType`, DSS property index: 19.
        """
    )

    @root_validator(pre=True)
    def drop_fields(cls, values):
        """Removes undesired fields."""
        return values


class XfmrCode(OpenDssElementBaseModel):
    """None"""

    phases: int | None = Field(
        description="""
        Number of phases this transformer. Default is 3.

        DSS property name: `phases`, DSS property index: 1.
        """
    )
    windings: int | None = Field(
        description="""
        Number of windings, this transformers. (Also is the number of terminals) Default is 2. This property triggers memory allocation for the Transformer and will cause other properties to revert to default values.

        DSS property name: `windings`, DSS property index: 2.
        """
    )
    pctR: list | None = Field(
        alias="%r",
        description="""
        Percent resistance this winding.  (half of total for a 2-winding).

        DSS property name: `%R`, DSS property index: 8.
        """,
    )
    Rneut: list | None = Field(
        description="""
        Default = -1. Neutral resistance of wye (star)-connected winding in actual ohms.If entered as a negative value, the neutral is assumed to be open, or floating.

        DSS property name: `Rneut`, DSS property index: 9.
        """
    )
    Xneut: list | None = Field(
        description="""
        Neutral reactance of wye(star)-connected winding in actual ohms.  May be + or -.

        DSS property name: `Xneut`, DSS property index: 10.
        """
    )
    conns: list | None = Field(
        description="""
        Use this to specify all the Winding connections at once using an array. Example:

        New Transformer.T1 buses="Hibus, lowbus"
        ~ conns=(delta, wye)

        DSS property name: `conns`, DSS property index: 11.
        """
    )
    kVs: list | None = Field(
        description="""
        Use this to specify the kV ratings of all windings at once using an array. Example:

        New Transformer.T1 buses="Hibus, lowbus"
        ~ conns=(delta, wye)
        ~ kvs=(115, 12.47)

        See kV= property for voltage rules.

        DSS property name: `kVs`, DSS property index: 12.
        """
    )
    kVAs: list | None = Field(
        description="""
        Use this to specify the kVA ratings of all windings at once using an array.

        DSS property name: `kVAs`, DSS property index: 13.
        """
    )
    taps: list | None = Field(
        description="""
        Use this to specify the normal p.u. tap of all windings at once using an array.

        DSS property name: `taps`, DSS property index: 14.
        """
    )
    Xhl: float | None = Field(
        description="""
        Use this to specify the percent reactance, H-L (winding 1 to winding 2).  Use for 2- or 3-winding transformers. On the kva base of winding 1.

        DSS property name: `Xhl`, DSS property index: 15.
        """
    )
    Xht: float | None = Field(
        description="""
        Use this to specify the percent reactance, H-T (winding 1 to winding 3).  Use for 3-winding transformers only. On the kVA base of winding 1.

        DSS property name: `Xht`, DSS property index: 16.
        """
    )
    Xlt: float | None = Field(
        description="""
        Use this to specify the percent reactance, L-T (winding 2 to winding 3).  Use for 3-winding transformers only. On the kVA base of winding 1.

        DSS property name: `Xlt`, DSS property index: 17.
        """
    )
    Xscarray: list | None = Field(
        description="""
        Use this to specify the percent reactance between all pairs of windings as an array. All values are on the kVA base of winding 1.  The order of the values is as follows:

        (x12 13 14... 23 24.. 34 ..)

        There will be n(n-1)/2 values, where n=number of windings.

        DSS property name: `Xscarray`, DSS property index: 18.
        """
    )
    thermal: float | None = Field(
        description="""
        Thermal time constant of the transformer in hours.  Typically about 2.

        DSS property name: `thermal`, DSS property index: 19.
        """
    )
    n: float | None = Field(
        description="""
        n Exponent for thermal properties in IEEE C57.  Typically 0.8.

        DSS property name: `n`, DSS property index: 20.
        """
    )
    m: float | None = Field(
        description="""
        m Exponent for thermal properties in IEEE C57.  Typically 0.9 - 1.0

        DSS property name: `m`, DSS property index: 21.
        """
    )
    flrise: float | None = Field(
        description="""
        Temperature rise, deg C, for full load.  Default is 65.

        DSS property name: `flrise`, DSS property index: 22.
        """
    )
    hsrise: float | None = Field(
        description="""
        Hot spot temperature rise, deg C.  Default is 15.

        DSS property name: `hsrise`, DSS property index: 23.
        """
    )
    pctloadloss: float | None = Field(
        alias="%loadloss",
        description="""
        Percent load loss at full load. The %R of the High and Low windings (1 and 2) are adjusted to agree at rated kVA loading.

        DSS property name: `%loadloss`, DSS property index: 24.
        """,
    )
    pctnoloadloss: float | None = Field(
        alias="%noloadloss",
        description="""
        Percent no load losses at rated excitatation voltage. Default is 0. Converts to a resistance in parallel with the magnetizing impedance in each winding.

        DSS property name: `%noloadloss`, DSS property index: 25.
        """,
    )
    normhkVA: float | None = Field(
        description="""
        Normal maximum kVA rating of H winding (winding 1).  Usually 100% - 110% ofmaximum nameplate rating, depending on load shape. Defaults to 110% of kVA rating of Winding 1.

        DSS property name: `normhkVA`, DSS property index: 26.
        """
    )
    emerghkVA: float | None = Field(
        description="""
        Emergency (contingency)  kVA rating of H winding (winding 1).  Usually 140% - 150% ofmaximum nameplate rating, depending on load shape. Defaults to 150% of kVA rating of Winding 1.

        DSS property name: `emerghkVA`, DSS property index: 27.
        """
    )
    MaxTap: list | None = Field(
        description="""
        Max per unit tap for the active winding.  Default is 1.10

        DSS property name: `MaxTap`, DSS property index: 28.
        """
    )
    MinTap: list | None = Field(
        description="""
        Min per unit tap for the active winding.  Default is 0.90

        DSS property name: `MinTap`, DSS property index: 29.
        """
    )
    NumTaps: list | None = Field(
        description="""
        Total number of taps between min and max tap.  Default is 32.

        DSS property name: `NumTaps`, DSS property index: 30.
        """
    )
    pctimag: float | None = Field(
        alias="%imag",
        description="""
        Percent magnetizing current. Default=0.0. Magnetizing branch is in parallel with windings in each phase. Also, see "ppm_antifloat".

        DSS property name: `%imag`, DSS property index: 31.
        """,
    )
    ppm_antifloat: float | None = Field(
        description="""
        Default=1 ppm.  Parts per million of transformer winding VA rating connected to ground to protect against accidentally floating a winding without a reference. If positive then the effect is adding a very large reactance to ground.  If negative, then a capacitor.

        DSS property name: `ppm_antifloat`, DSS property index: 32.
        """
    )
    pctRs: list | None = Field(
        alias="%rs",
        description="""
        Use this property to specify all the winding %resistances using an array. Example:

        New Transformer.T1 buses="Hibus, lowbus" ~ %Rs=(0.2  0.3)

        DSS property name: `%Rs`, DSS property index: 33.
        """,
    )
    X12: float | None = Field(
        description="""
        Alternative to XHL for specifying the percent reactance from winding 1 to winding 2.  Use for 2- or 3-winding transformers. Percent on the kVA base of winding 1.

        DSS property name: `X12`, DSS property index: 34.
        """
    )
    X13: float | None = Field(
        description="""
        Alternative to XHT for specifying the percent reactance from winding 1 to winding 3.  Use for 3-winding transformers only. Percent on the kVA base of winding 1.

        DSS property name: `X13`, DSS property index: 35.
        """
    )
    X23: float | None = Field(
        description="""
        Alternative to XLT for specifying the percent reactance from winding 2 to winding 3.Use for 3-winding transformers only. Percent on the kVA base of winding 1.

        DSS property name: `X23`, DSS property index: 36.
        """
    )
    RdcOhms: list | None = Field(
        description="""
        Winding dc resistance in OHMS. Useful for GIC analysis. From transformer test report. Defaults to 85% of %R property

        DSS property name: `RdcOhms`, DSS property index: 37.
        """
    )
    Seasons: int | None = Field(
        description="""
        Defines the number of ratings to be defined for the transfomer, to be used only when defining seasonal ratings using the "Ratings" property.

        DSS property name: `Seasons`, DSS property index: 38.
        """
    )
    Ratings: list | None = Field(
        description="""
        An array of ratings to be used when the seasonal ratings flag is True. It can be used to insert
        multiple ratings to change during a QSTS simulation to evaluate different ratings in transformers.

        DSS property name: `Ratings`, DSS property index: 39.
        """
    )

    @root_validator(pre=True)
    def drop_fields(cls, values):
        """Removes undesired fields."""
        return values


class Line(OpenDssElementBaseModel):
    """None"""

    bus1: str | None = Field(
        description="""
        Name of bus to which first terminal is connected.
        Example:
        bus1=busname   (assumes all terminals connected in normal phase order)
        bus1=busname.3.1.2.0 (specify terminal to node connections explicitly)

        DSS property name: `bus1`, DSS property index: 1.
        """
    )
    bus2: str | None = Field(
        description="""
        Name of bus to which 2nd terminal is connected.

        DSS property name: `bus2`, DSS property index: 2.
        """
    )
    linecode: str | None = Field(
        description="""
        Name of linecode object describing line impedances.
        If you use a line code, you do not need to specify the impedances here. The line code must have been PREVIOUSLY defined. The values specified last will prevail over those specified earlier (left-to-right sequence of properties).  You can subsequently change the number of phases if symmetrical component quantities are specified.If no line code or impedance data are specified, the line object defaults to 336 MCM ACSR on 4 ft spacing.

        DSS property name: `linecode`, DSS property index: 3.
        """
    )
    length: float | None = Field(
        description="""
        Length of line. Default is 1.0. If units do not match the impedance data, specify "units" property.

        DSS property name: `length`, DSS property index: 4.
        """
    )
    phases: int | None = Field(
        description="""
        Number of phases, this line.

        DSS property name: `phases`, DSS property index: 5.
        """
    )
    r1: float | None = Field(
        description="""
        Positive-sequence Resistance, ohms per unit length. Setting any of R1, R0, X1, X0, C1, C0 forces the program to use the symmetrical component line definition. See also Rmatrix.

        DSS property name: `r1`, DSS property index: 6.
        """
    )
    x1: float | None = Field(
        description="""
        Positive-sequence Reactance, ohms per unit length. Setting any of R1, R0, X1, X0, C1, C0 forces the program to use the symmetrical component line definition.  See also Xmatrix

        DSS property name: `x1`, DSS property index: 7.
        """
    )
    r0: float | None = Field(
        description="""
        Zero-sequence Resistance, ohms per unit length. Setting any of R1, R0, X1, X0, C1, C0 forces the program to use the symmetrical component line definition.

        DSS property name: `r0`, DSS property index: 8.
        """
    )
    x0: float | None = Field(
        description="""
        Zero-sequence Reactance, ohms per unit length. Setting any of R1, R0, X1, X0, C1, C0 forces the program to use the symmetrical component line definition.

        DSS property name: `x0`, DSS property index: 9.
        """
    )
    C1: float | None = Field(
        description="""
        Positive-sequence capacitance, nf per unit length.  Setting any of R1, R0, X1, X0, C1, C0 forces the program to use the symmetrical component line definition. See also Cmatrix and B1.

        DSS property name: `C1`, DSS property index: 10.
        """
    )
    C0: float | None = Field(
        description="""
        Zero-sequence capacitance, nf per unit length. Setting any of R1, R0, X1, X0, C1, C0 forces the program to use the symmetrical component line definition.See also B0.

        DSS property name: `C0`, DSS property index: 11.
        """
    )
    rmatrix: list | None = Field(
        description="""
        Resistance matrix, lower triangle, ohms per unit length. Order of the matrix is the number of phases. May be used to specify the impedance of any line configuration. Using any of Rmatrix, Xmatrix, Cmatrix forces program to use the matrix values for line impedance definition. For balanced line models, you may use the standard symmetrical component data definition instead.

        DSS property name: `rmatrix`, DSS property index: 12.
        """
    )
    xmatrix: list | None = Field(
        description="""
        Reactance matrix, lower triangle, ohms per unit length. Order of the matrix is the number of phases. May be used to specify the impedance of any line configuration. Using any of Rmatrix, Xmatrix, Cmatrix forces program to use the matrix values for line impedance definition.  For balanced line models, you may use the standard symmetrical component data definition instead.

        DSS property name: `xmatrix`, DSS property index: 13.
        """
    )
    cmatrix: list | None = Field(
        description="""
        Nodal Capacitance matrix, lower triangle, nf per unit length.Order of the matrix is the number of phases. May be used to specify the shunt capacitance of any line configuration. Using any of Rmatrix, Xmatrix, Cmatrix forces program to use the matrix values for line impedance definition.  For balanced line models, you may use the standard symmetrical component data definition instead.

        DSS property name: `cmatrix`, DSS property index: 14.
        """
    )
    Switch: bool | None = Field(
        description="""
        {y/n | T/F}  Default= no/false.  Designates this line as a switch for graphics and algorithmic purposes.
        SIDE EFFECT: Sets r1 = 1.0; x1 = 1.0; r0 = 1.0; x0 = 1.0; c1 = 1.1 ; c0 = 1.0;  length = 0.001; You must reset if you want something different.

        DSS property name: `Switch`, DSS property index: 15.
        """
    )
    Rg: float | None = Field(
        description="""
        Carson earth return resistance per unit length used to compute impedance values at base frequency. Default is 0.01805 = 60 Hz value in ohms per kft (matches default line impedances). This value is required for harmonic solutions if you wish to adjust the earth return impedances for frequency. If not, set both Rg and Xg = 0.

        DSS property name: `Rg`, DSS property index: 16.
        """
    )
    Xg: float | None = Field(
        description="""
        Carson earth return reactance per unit length used to compute impedance values at base frequency.  For making better frequency adjustments. Default is 0.155081 = 60 Hz value in ohms per kft (matches default line impedances). This value is required for harmonic solutions if you wish to adjust the earth return impedances for frequency. If not, set both Rg and Xg = 0.

        DSS property name: `Xg`, DSS property index: 17.
        """
    )
    rho: float | None = Field(
        description="""
        Default=100 meter ohms.  Earth resitivity used to compute earth correction factor. Overrides Line geometry definition if specified.

        DSS property name: `rho`, DSS property index: 18.
        """
    )
    geometry: str | None = Field(
        description="""
        Geometry code for LineGeometry Object. Supercedes any previous definition of line impedance. Line constants are computed for each frequency change or rho change. CAUTION: may alter number of phases. You cannot subsequently change the number of phases unless you change how the line impedance is defined.

        DSS property name: `geometry`, DSS property index: 19.
        """
    )
    units: str | None = Field(
        description="""
        Length Units = {none | mi|kft|km|m|Ft|in|cm } Default is None - assumes length units match impedance units.

        DSS property name: `units`, DSS property index: 20.
        """
    )
    spacing: str | None = Field(
        description="""
        Reference to a LineSpacing for use in a line constants calculation.
        Must be used in conjunction with the Wires property.
        Specify this before the wires property.

        DSS property name: `spacing`, DSS property index: 21.
        """
    )
    wires: list | None = Field(
        description="""
        Array of WireData names for use in an overhead line constants calculation.
        Must be used in conjunction with the Spacing property.
        Specify the Spacing first, and "ncond" wires.
        May also be used to specify bare neutrals with cables, using "ncond-nphase" wires.

        DSS property name: `wires`, DSS property index: 22.
        """
    )
    earthmodel: str | None = Field(
        alias="EarthModel",
        description="""
        One of {Carson | FullCarson | Deri}. Default is the global value established with the Set EarthModel command. See the Options Help on EarthModel option. This is used to override the global value for this line. This option applies only when the "geometry" property is used.

        DSS property name: `EarthModel`, DSS property index: 23.
        """,
    )
    B1: float | None = Field(
        description="""
        Alternate way to specify C1. MicroS per unit length

        DSS property name: `B1`, DSS property index: 26.
        """
    )
    B0: float | None = Field(
        description="""
        Alternate way to specify C0. MicroS per unit length

        DSS property name: `B0`, DSS property index: 27.
        """
    )
    Seasons: int | None = Field(
        description="""
        Defines the number of ratings to be defined for the wire, to be used only when defining seasonal ratings using the "Ratings" property.

        DSS property name: `Seasons`, DSS property index: 28.
        """
    )
    Ratings: list | None = Field(
        description="""
        An array of ratings to be used when the seasonal ratings flag is True. It can be used to insert
        multiple ratings to change during a QSTS simulation to evaluate different ratings in lines.

        DSS property name: `Ratings`, DSS property index: 29.
        """
    )
    linetype: str | None = Field(
        alias="LineType",
        description="""
        Code designating the type of line.
        One of: OH, UG, UG_TS, UG_CN, SWT_LDBRK, SWT_FUSE, SWT_SECT, SWT_REC, SWT_DISC, SWT_BRK, SWT_ELBOW, BUSBAR

        OpenDSS currently does not use this internally. For whatever purpose the user defines. Default is OH.

        DSS property name: `LineType`, DSS property index: 30.
        """,
    )
    normamps: float | None = Field(
        description="""
        Normal rated current.

        DSS property name: `normamps`, DSS property index: 31.
        """
    )
    emergamps: float | None = Field(
        description="""
        Maximum or emerg current.

        DSS property name: `emergamps`, DSS property index: 32.
        """
    )
    faultrate: float | None = Field(
        description="""
        Failure rate PER UNIT LENGTH per year. Length must be same units as LENGTH property. Default is 0.1 fault per unit length per year.

        DSS property name: `faultrate`, DSS property index: 33.
        """
    )
    pctperm: float | None = Field(
        description="""
        Percent of failures that become permanent. Default is 20.

        DSS property name: `pctperm`, DSS property index: 34.
        """
    )
    repair: float | None = Field(
        description="""
        Hours to repair. Default is 3 hr.

        DSS property name: `repair`, DSS property index: 35.
        """
    )
    basefreq: float | None = Field(
        description="""
        Base Frequency for ratings.

        DSS property name: `basefreq`, DSS property index: 36.
        """
    )
    enabled: bool | None = Field(
        description="""
        {Yes|No or True|False} Indicates whether this element is enabled.

        DSS property name: `enabled`, DSS property index: 37.
        """
    )

    @root_validator(pre=True)
    def drop_fields(cls, values):
        """Removes undesired fields."""
        return values


class Vsource(OpenDssElementBaseModel):
    """None"""

    bus1: str | None = Field(
        description="""
        Name of bus to which the main terminal (1) is connected.
        bus1=busname
        bus1=busname.1.2.3

        The VSOURCE object is a two-terminal voltage source (thevenin equivalent). Bus2 defaults to Bus1 with all phases connected to ground (node 0) unless previously specified. This is a Yg connection. If you want something different, define the Bus2 property ezplicitly.

        DSS property name: `bus1`, DSS property index: 1.
        """
    )
    basekv: float | None = Field(
        description="""
        Base Source kV, usually phase-phase (L-L) unless you are making a positive-sequence model or 1-phase modelin which case, it will be phase-neutral (L-N) kV.

        DSS property name: `basekv`, DSS property index: 2.
        """
    )
    pu: float | None = Field(
        description="""
        Per unit of the base voltage that the source is actually operating at.
        "pu=1.05"

        DSS property name: `pu`, DSS property index: 3.
        """
    )
    angle: float | None = Field(
        description="""
        Phase angle in degrees of first phase: e.g.,Angle=10.3

        DSS property name: `angle`, DSS property index: 4.
        """
    )
    frequency: float | None = Field(
        description="""
        Source frequency.  Defaults to system default base frequency.

        DSS property name: `frequency`, DSS property index: 5.
        """
    )
    phases: int | None = Field(
        description="""
        Number of phases.  Defaults to 3.

        DSS property name: `phases`, DSS property index: 6.
        """
    )
    MVAsc3: float | None = Field(
        description="""
        MVA Short circuit, 3-phase fault. Default = 2000. Z1 is determined by squaring the base kv and dividing by this value. For single-phase source, this value is not used.

        DSS property name: `MVAsc3`, DSS property index: 7.
        """
    )
    MVAsc1: float | None = Field(
        description="""
        MVA Short Circuit, 1-phase fault. Default = 2100. The "single-phase impedance", Zs, is determined by squaring the base kV and dividing by this value. Then Z0 is determined by Z0 = 3Zs - 2Z1.  For 1-phase sources, Zs is used directly. Use X0R0 to define X/R ratio for 1-phase source.

        DSS property name: `MVAsc1`, DSS property index: 8.
        """
    )
    x1r1: float | None = Field(
        description="""
        Positive-sequence  X/R ratio. Default = 4.

        DSS property name: `x1r1`, DSS property index: 9.
        """
    )
    x0r0: float | None = Field(
        description="""
        Zero-sequence X/R ratio.Default = 3.

        DSS property name: `x0r0`, DSS property index: 10.
        """
    )
    Isc3: float | None = Field(
        description="""
        Alternate method of defining the source impedance.
        3-phase short circuit current, amps.  Default is 10000.

        DSS property name: `Isc3`, DSS property index: 11.
        """
    )
    Isc1: float | None = Field(
        description="""
        Alternate method of defining the source impedance.
        single-phase short circuit current, amps.  Default is 10500.

        DSS property name: `Isc1`, DSS property index: 12.
        """
    )
    R1: float | None = Field(
        description="""
        Alternate method of defining the source impedance.
        Positive-sequence resistance, ohms.  Default is 1.65.

        DSS property name: `R1`, DSS property index: 13.
        """
    )
    X1: float | None = Field(
        description="""
        Alternate method of defining the source impedance.
        Positive-sequence reactance, ohms.  Default is 6.6.

        DSS property name: `X1`, DSS property index: 14.
        """
    )
    R0: float | None = Field(
        description="""
        Alternate method of defining the source impedance.
        Zero-sequence resistance, ohms.  Default is 1.9.

        DSS property name: `R0`, DSS property index: 15.
        """
    )
    X0: float | None = Field(
        description="""
        Alternate method of defining the source impedance.
        Zero-sequence reactance, ohms.  Default is 5.7.

        DSS property name: `X0`, DSS property index: 16.
        """
    )
    scantype: str | None = Field(
        description="""
        {pos*| zero | none} Maintain specified sequence for harmonic solution. Default is positive sequence. Otherwise, angle between phases rotates with harmonic.

        DSS property name: `ScanType`, DSS property index: 17.
        """
    )
    Sequence: str | None = Field(
        description="""
        {pos*| neg | zero} Set the phase angles for the specified symmetrical component sequence for non-harmonic solution modes. Default is positive sequence.

        DSS property name: `Sequence`, DSS property index: 18.
        """
    )
    bus2: str | None = Field(
        description="""
        Name of bus to which 2nd terminal is connected.
        bus2=busname
        bus2=busname.1.2.3

        Default is Bus1.0.0.0 (grounded wye connection)

        DSS property name: `bus2`, DSS property index: 19.
        """
    )
    Z2: complex | None = Field(
        description="""
        Negative-sequence equivalent source impedance, ohms, as a 2-element array representing a complex number. Example:

        Z2=[1, 2]  ! represents 1 + j2

        Used to define the impedance matrix of the VSOURCE if Z1 is also specified.

        Note: Z2 defaults to Z1 if it is not specifically defined. If Z2 is not equal to Z1, the impedance matrix is asymmetrical.

        DSS property name: `Z2`, DSS property index: 22.
        """
    )
    puZ1: complex | None = Field(
        description="""
        2-element array: e.g., [1  2]. An alternate way to specify Z1. See Z1 property. Per-unit positive-sequence impedance on base of Vsource BasekV and BaseMVA.

        DSS property name: `puZ1`, DSS property index: 23.
        """
    )
    puZ0: complex | None = Field(
        description="""
        2-element array: e.g., [1  2]. An alternate way to specify Z0. See Z0 property. Per-unit zero-sequence impedance on base of Vsource BasekV and BaseMVA.

        DSS property name: `puZ0`, DSS property index: 24.
        """
    )
    puZ2: complex | None = Field(
        description="""
        2-element array: e.g., [1  2]. An alternate way to specify Z2. See Z2 property. Per-unit negative-sequence impedance on base of Vsource BasekV and BaseMVA.

        DSS property name: `puZ2`, DSS property index: 25.
        """
    )
    baseMVA: float | None = Field(
        description="""
        Default value is 100. Base used to convert values specifiied with puZ1, puZ0, and puZ2 properties to ohms on kV base specified by BasekV property.

        DSS property name: `baseMVA`, DSS property index: 26.
        """
    )
    Yearly: str | None = Field(
        description="""
        LOADSHAPE object to use for the per-unit voltage for YEARLY-mode simulations. Set the Mult property of the LOADSHAPE to the pu curve. Qmult is not used. If UseActual=Yes then the Mult curve should be actual L-N kV.

        Must be previously defined as a LOADSHAPE object.

        Is set to the Daily load shape when Daily is defined.  The daily load shape is repeated in this case. Set to NONE to reset to no loadahape for Yearly mode. The default is no variation.

        DSS property name: `Yearly`, DSS property index: 27.
        """
    )
    Daily: str | None = Field(
        description="""
        LOADSHAPE object to use for the per-unit voltage for DAILY-mode simulations. Set the Mult property of the LOADSHAPE to the pu curve. Qmult is not used. If UseActual=Yes then the Mult curve should be actual L-N kV.

        Must be previously defined as a LOADSHAPE object.

        Sets Yearly curve if it is not already defined.   Set to NONE to reset to no loadahape for Yearly mode. The default is no variation.

        DSS property name: `Daily`, DSS property index: 28.
        """
    )
    Duty: str | None = Field(
        description="""
        LOADSHAPE object to use for the per-unit voltage for DUTYCYCLE-mode simulations. Set the Mult property of the LOADSHAPE to the pu curve. Qmult is not used. If UseActual=Yes then the Mult curve should be actual L-N kV.

        Must be previously defined as a LOADSHAPE object.

        Defaults to Daily load shape when Daily is defined.   Set to NONE to reset to no loadahape for Yearly mode. The default is no variation.

        DSS property name: `Duty`, DSS property index: 29.
        """
    )
    Model: str | None = Field(
        description="""
        {Thevenin* | Ideal}  Specifies whether the Vsource is to be considered a Thevenin short circuit model or a quasi-ideal voltage source. If Thevenin, the Vsource uses the impedances defined for all calculations. If "Ideal", the model uses a small impedance on the diagonal of the impedance matrix for the fundamental base frequency power flow only. Then switches to actual Thevenin model for other frequencies.

        DSS property name: `Model`, DSS property index: 30.
        """
    )
    puZideal: complex | None = Field(
        description="""
        2-element array: e.g., [1  2]. The pu impedance to use for the quasi-ideal voltage source model. Should be a very small impedances. Default is [1e-6, 0.001]. Per-unit impedance on base of Vsource BasekV and BaseMVA. If too small, solution may not work. Be sure to check the voltage values and powers.

        DSS property name: `puZideal`, DSS property index: 31.
        """
    )
    spectrum: str | None = Field(
        description="""
        Name of harmonic spectrum for this source.  Default is "defaultvsource", which is defined when the DSS starts.

        DSS property name: `spectrum`, DSS property index: 32.
        """
    )
    basefreq: float | None = Field(
        description="""
        Base Frequency for ratings.

        DSS property name: `basefreq`, DSS property index: 33.
        """
    )
    enabled: bool | None = Field(
        description="""
        {Yes|No or True|False} Indicates whether this element is enabled.

        DSS property name: `enabled`, DSS property index: 34.
        """
    )

    @root_validator(pre=True)
    def drop_fields(cls, values):
        """Removes undesired fields."""
        return values


class Isource(OpenDssElementBaseModel):
    """None"""

    bus1: str | None = Field(
        description="""
        Name of bus to which source is connected.
        bus1=busname
        bus1=busname.1.2.3

        DSS property name: `bus1`, DSS property index: 1.
        """
    )
    amps: float | None = Field(
        description="""
        Magnitude of current source, each phase, in Amps.

        DSS property name: `amps`, DSS property index: 2.
        """
    )
    angle: float | None = Field(
        description="""
        Phase angle in degrees of first phase: e.g.,Angle=10.3.
        Phase shift between phases is assumed 120 degrees when number of phases <= 3

        DSS property name: `angle`, DSS property index: 3.
        """
    )
    frequency: float | None = Field(
        description="""
        Source frequency.  Defaults to  circuit fundamental frequency.

        DSS property name: `frequency`, DSS property index: 4.
        """
    )
    phases: int | None = Field(
        description="""
        Number of phases.  Defaults to 3. For 3 or less, phase shift is 120 degrees.

        DSS property name: `phases`, DSS property index: 5.
        """
    )
    scantype: str | None = Field(
        description="""
        {pos*| zero | none} Maintain specified sequence for harmonic solution. Default is positive sequence. Otherwise, angle between phases rotates with harmonic.

        DSS property name: `scantype`, DSS property index: 6.
        """
    )
    sequence: str | None = Field(
        description="""
        {pos*| neg | zero} Set the phase angles for the specified symmetrical component sequence for non-harmonic solution modes. Default is positive sequence.

        DSS property name: `sequence`, DSS property index: 7.
        """
    )
    Yearly: str | None = Field(
        description="""
        LOADSHAPE object to use for the per-unit current for YEARLY-mode simulations. Set the Mult property of the LOADSHAPE to the pu curve. Qmult is not used. If UseActual=Yes then the Mult curve should be actual Amp.

        Must be previously defined as a LOADSHAPE object.

        Is set to the Daily load shape when Daily is defined.  The daily load shape is repeated in this case. Set to NONE to reset to no loadahape for Yearly mode. The default is no variation.

        DSS property name: `Yearly`, DSS property index: 8.
        """
    )
    Daily: str | None = Field(
        description="""
        LOADSHAPE object to use for the per-unit current for DAILY-mode simulations. Set the Mult property of the LOADSHAPE to the pu curve. Qmult is not used. If UseActual=Yes then the Mult curve should be actual A.

        Must be previously defined as a LOADSHAPE object.

        Sets Yearly curve if it is not already defined.   Set to NONE to reset to no loadahape for Yearly mode. The default is no variation.

        DSS property name: `Daily`, DSS property index: 9.
        """
    )
    Duty: str | None = Field(
        description="""
        LOADSHAPE object to use for the per-unit current for DUTYCYCLE-mode simulations. Set the Mult property of the LOADSHAPE to the pu curve. Qmult is not used. If UseActual=Yes then the Mult curve should be actual A.

        Must be previously defined as a LOADSHAPE object.

        Defaults to Daily load shape when Daily is defined.   Set to NONE to reset to no loadahape for Yearly mode. The default is no variation.

        DSS property name: `Duty`, DSS property index: 10.
        """
    )
    Bus2: str | None = Field(
        description="""
        Name of bus to which 2nd terminal is connected.
        bus2=busname
        bus2=busname.1.2.3

        Default is Bus1.0.0.0 (grounded-wye connection)

        DSS property name: `Bus2`, DSS property index: 11.
        """
    )
    spectrum: str | None = Field(
        description="""
        Harmonic spectrum assumed for this source.  Default is "default".

        DSS property name: `spectrum`, DSS property index: 12.
        """
    )
    basefreq: float | None = Field(
        description="""
        Base Frequency for ratings.

        DSS property name: `basefreq`, DSS property index: 13.
        """
    )
    enabled: bool | None = Field(
        description="""
        {Yes|No or True|False} Indicates whether this element is enabled.

        DSS property name: `enabled`, DSS property index: 14.
        """
    )

    @root_validator(pre=True)
    def drop_fields(cls, values):
        """Removes undesired fields."""
        return values


class VCCS(OpenDssElementBaseModel):
    """None"""

    bus1: str | None = Field(
        description="""
        Name of bus to which source is connected.
        bus1=busname
        bus1=busname.1.2.3

        DSS property name: `bus1`, DSS property index: 1.
        """
    )
    phases: int | None = Field(
        description="""
        Number of phases.  Defaults to 1.

        DSS property name: `phases`, DSS property index: 2.
        """
    )
    prated: float | None = Field(
        description="""
        Total rated power, in Watts.

        DSS property name: `prated`, DSS property index: 3.
        """
    )
    vrated: float | None = Field(
        description="""
        Rated line-to-line voltage, in Volts

        DSS property name: `vrated`, DSS property index: 4.
        """
    )
    ppct: float | None = Field(
        description="""
        Steady-state operating output, in percent of rated.

        DSS property name: `ppct`, DSS property index: 5.
        """
    )
    bp1: str | None = Field(
        description="""
        XYCurve defining the input piece-wise linear block.

        DSS property name: `bp1`, DSS property index: 6.
        """
    )
    bp2: str | None = Field(
        description="""
        XYCurve defining the output piece-wise linear block.

        DSS property name: `bp2`, DSS property index: 7.
        """
    )
    filter: str | None = Field(
        description="""
        XYCurve defining the digital filter coefficients (x numerator, y denominator).

        DSS property name: `filter`, DSS property index: 8.
        """
    )
    fsample: float | None = Field(
        description="""
        Sample frequency [Hz} for the digital filter.

        DSS property name: `fsample`, DSS property index: 9.
        """
    )
    rmsmode: bool | None = Field(
        description="""
        True if only Hz is used to represent a phase-locked loop (PLL), ignoring the BP1, BP2 and time-domain transformations. Default is no.

        DSS property name: `rmsmode`, DSS property index: 10.
        """
    )
    imaxpu: float | None = Field(
        description="""
        Maximum output current in per-unit of rated; defaults to 1.1

        DSS property name: `imaxpu`, DSS property index: 11.
        """
    )
    vrmstau: float | None = Field(
        description="""
        Time constant in sensing Vrms for the PLL; defaults to 0.0015

        DSS property name: `vrmstau`, DSS property index: 12.
        """
    )
    irmstau: float | None = Field(
        description="""
        Time constant in producing Irms from the PLL; defaults to 0.0015

        DSS property name: `irmstau`, DSS property index: 13.
        """
    )
    spectrum: str | None = Field(
        description="""
        Harmonic spectrum assumed for this source.  Default is "default".

        DSS property name: `spectrum`, DSS property index: 14.
        """
    )
    basefreq: float | None = Field(
        description="""
        Base Frequency for ratings.

        DSS property name: `basefreq`, DSS property index: 15.
        """
    )
    enabled: bool | None = Field(
        description="""
        {Yes|No or True|False} Indicates whether this element is enabled.

        DSS property name: `enabled`, DSS property index: 16.
        """
    )

    @root_validator(pre=True)
    def drop_fields(cls, values):
        """Removes undesired fields."""
        return values


class Load(OpenDssElementBaseModel):
    """None"""

    phases: int | None = Field(
        description="""
        Number of Phases, this load.  Load is evenly divided among phases.

        DSS property name: `phases`, DSS property index: 1.
        """
    )
    bus1: str | None = Field(
        description="""
        Bus to which the load is connected.  May include specific node specification.

        DSS property name: `bus1`, DSS property index: 2.
        """
    )
    kV: float | None = Field(
        description="""
        Nominal rated (1.0 per unit) voltage, kV, for load. For 2- and 3-phase loads, specify phase-phase kV. Otherwise, specify actual kV across each branch of the load. If wye (star), specify phase-neutral kV. If delta or phase-phase connected, specify phase-phase kV.

        DSS property name: `kV`, DSS property index: 3.
        """
    )
    kW: float | None = Field(
        description="""
        Total base kW for the load.  Normally, you would enter the maximum kW for the load for the first year and allow it to be adjusted by the load shapes, growth shapes, and global load multiplier.

        Legal ways to define base load:
        kW, PF
        kW, kvar
        kVA, PF
        XFKVA * Allocationfactor, PF
        kWh/(kWhdays*24) * Cfactor, PF

        DSS property name: `kW`, DSS property index: 4.
        """
    )
    pf: float | None = Field(
        description="""
        Load power factor.  Enter negative for leading powerfactor (when kW and kvar have opposite signs.)

        DSS property name: `pf`, DSS property index: 5.
        """
    )
    model: str | None = Field(
        description="""
        Integer code for the model to use for load variation with voltage. Valid values are:

        1:Standard constant P+jQ load. (Default)
        2:Constant impedance load.
        3:Const P, Quadratic Q (like a motor).
        4:Nominal Linear P, Quadratic Q (feeder mix). Use this with CVRfactor.
        5:Constant Current Magnitude
        6:Const P, Fixed Q
        7:Const P, Fixed Impedance Q
        8:ZIPV (7 values)

        For Types 6 and 7, only the P is modified by load multipliers.

        DSS property name: `model`, DSS property index: 6.
        """
    )
    yearly: str | None = Field(
        description="""
        LOADSHAPE object to use for yearly simulations.  Must be previously defined as a Loadshape object. Is set to the Daily load shape  when Daily is defined.  The daily load shape is repeated in this case. Set Status=Fixed to ignore Loadshape designation. Set to NONE to reset to no loadahape. The default is no variation.

        DSS property name: `yearly`, DSS property index: 7.
        """
    )
    daily: str | None = Field(
        description="""
        LOADSHAPE object to use for daily simulations.  Must be previously defined as a Loadshape object of 24 hrs, typically. Set Status=Fixed to ignore Loadshape designation. Set to NONE to reset to no loadahape. Default is no variation (constant) if not defined. Side effect: Sets Yearly load shape if not already defined.

        DSS property name: `daily`, DSS property index: 8.
        """
    )
    duty: str | None = Field(
        description="""
        LOADSHAPE object to use for duty cycle simulations.  Must be previously defined as a Loadshape object.  Typically would have time intervals less than 1 hr. Designate the number of points to solve using the Set Number=xxxx command. If there are fewer points in the actual shape, the shape is assumed to repeat.Set to NONE to reset to no loadahape. Set Status=Fixed to ignore Loadshape designation.  Defaults to Daily curve If not specified.

        DSS property name: `duty`, DSS property index: 9.
        """
    )
    growth: str | None = Field(
        description="""
        Characteristic  to use for growth factors by years.  Must be previously defined as a Growthshape object. Defaults to circuit default growth factor (see Set Growth command).

        DSS property name: `growth`, DSS property index: 10.
        """
    )
    conn: str | None = Field(
        description="""
        ={wye or LN | delta or LL}.  Default is wye.

        DSS property name: `conn`, DSS property index: 11.
        """
    )
    kvar: float | None = Field(
        description="""
        Specify the base kvar for specifying load as kW & kvar.  Assumes kW has been already defined.  Alternative to specifying the power factor.  Side effect:  the power factor and kVA is altered to agree.

        DSS property name: `kvar`, DSS property index: 12.
        """
    )
    Rneut: float | None = Field(
        description="""
        Default is -1. Neutral resistance of wye (star)-connected load in actual ohms. If entered as a negative value, the neutral can be open, or floating, or it can be connected to node 0 (ground), which is the usual default. If >=0 be sure to explicitly specify the node connection for the neutral, or last, conductor. Otherwise, the neutral impedance will be shorted to ground.

        DSS property name: `Rneut`, DSS property index: 13.
        """
    )
    Xneut: float | None = Field(
        description="""
        Neutral reactance of wye(star)-connected load in actual ohms.  May be + or -.

        DSS property name: `Xneut`, DSS property index: 14.
        """
    )
    status: str | None = Field(
        description="""
        ={Variable | Fixed | Exempt}.  Default is variable. If Fixed, no load multipliers apply;  however, growth multipliers do apply.  All multipliers apply to Variable loads.  Exempt loads are not modified by the global load multiplier, such as in load duration curves, etc.  Daily multipliers do apply, so setting this property to Exempt is a good way to represent industrial load that stays the same day-after-day for the period study.

        DSS property name: `status`, DSS property index: 15.
        """
    )
    cls: int | None = Field(
        alias="class",
        description="""
        An arbitrary integer number representing the class of load so that load values may be segregated by load value. Default is 1; not used internally.

        DSS property name: `class`, DSS property index: 16.
        """,
    )
    Vminpu: float | None = Field(
        description="""
        Default = 0.95.  Minimum per unit voltage for which the MODEL is assumed to apply. Lower end of normal voltage range.Below this value, the load model reverts to a constant impedance model that matches the model at the transition voltage. See also "Vlowpu" which causes the model to match Model=2 below the transition voltage.

        DSS property name: `Vminpu`, DSS property index: 17.
        """
    )
    Vmaxpu: float | None = Field(
        description="""
        Default = 1.05.  Maximum per unit voltage for which the MODEL is assumed to apply. Above this value, the load model reverts to a constant impedance model.

        DSS property name: `Vmaxpu`, DSS property index: 18.
        """
    )
    Vminnorm: float | None = Field(
        description="""
        Minimum per unit voltage for load EEN evaluations, Normal limit.  Default = 0, which defaults to system "vminnorm" property (see Set Command under Executive).  If this property is specified, it ALWAYS overrides the system specification. This allows you to have different criteria for different loads. Set to zero to revert to the default system value.

        DSS property name: `Vminnorm`, DSS property index: 19.
        """
    )
    Vminemerg: float | None = Field(
        description="""
        Minimum per unit voltage for load UE evaluations, Emergency limit.  Default = 0, which defaults to system "vminemerg" property (see Set Command under Executive).  If this property is specified, it ALWAYS overrides the system specification. This allows you to have different criteria for different loads. Set to zero to revert to the default system value.

        DSS property name: `Vminemerg`, DSS property index: 20.
        """
    )
    xfkVA: float | None = Field(
        description="""
        Default = 0.0.  Rated kVA of service transformer for allocating loads based on connected kVA at a bus. Side effect:  kW, PF, and kvar are modified. See help on kVA.

        DSS property name: `xfkVA`, DSS property index: 21.
        """
    )
    allocationfactor: float | None = Field(
        description="""
        Default = 0.5.  Allocation factor for allocating loads based on connected kVA at a bus. Side effect:  kW, PF, and kvar are modified by multiplying this factor times the XFKVA (if > 0).

        DSS property name: `allocationfactor`, DSS property index: 22.
        """
    )
    kVA: float | None = Field(
        description="""
        Specify base Load in kVA (and power factor)

        Legal ways to define base load:
        kW, PF
        kW, kvar
        kVA, PF
        XFKVA * Allocationfactor, PF
        kWh/(kWhdays*24) * Cfactor, PF

        DSS property name: `kVA`, DSS property index: 23.
        """
    )
    pctmean: float | None = Field(
        alias="%mean",
        description="""
        Percent mean value for load to use for monte carlo studies if no loadshape is assigned to this load. Default is 50.

        DSS property name: `%mean`, DSS property index: 24.
        """,
    )
    pctstddev: float | None = Field(
        alias="%stddev",
        description="""
        Percent Std deviation value for load to use for monte carlo studies if no loadshape is assigned to this load. Default is 10.

        DSS property name: `%stddev`, DSS property index: 25.
        """,
    )
    CVRwatts: float | None = Field(
        description="""
        Percent reduction in active power (watts) per 1% reduction in voltage from 100% rated. Default=1.
         Typical values range from 0.4 to 0.8. Applies to Model=4 only.
         Intended to represent conservation voltage reduction or voltage optimization measures.

        DSS property name: `CVRwatts`, DSS property index: 26.
        """
    )
    CVRvars: float | None = Field(
        description="""
        Percent reduction in reactive power (vars) per 1% reduction in voltage from 100% rated. Default=2.
         Typical values range from 2 to 3. Applies to Model=4 only.
         Intended to represent conservation voltage reduction or voltage optimization measures.

        DSS property name: `CVRvars`, DSS property index: 27.
        """
    )
    kwh: float | None = Field(
        description="""
        kWh billed for this period. Default is 0. See help on kVA and Cfactor and kWhDays.

        DSS property name: `kwh`, DSS property index: 28.
        """
    )
    kwhdays: float | None = Field(
        description="""
        Length of kWh billing period in days (24 hr days). Default is 30. Average demand is computed using this value.

        DSS property name: `kwhdays`, DSS property index: 29.
        """
    )
    Cfactor: float | None = Field(
        description="""
        Factor relating average kW to peak kW. Default is 4.0. See kWh and kWhdays. See kVA.

        DSS property name: `Cfactor`, DSS property index: 30.
        """
    )
    CVRcurve: str | None = Field(
        description="""
        Default is NONE. Curve describing both watt and var factors as a function of time. Refers to a LoadShape object with both Mult and Qmult defined. Define a Loadshape to agree with yearly or daily curve according to the type of analysis being done. If NONE, the CVRwatts and CVRvars factors are used and assumed constant.

        DSS property name: `CVRcurve`, DSS property index: 31.
        """
    )
    NumCust: int | None = Field(
        description="""
        Number of customers, this load. Default is 1.

        DSS property name: `NumCust`, DSS property index: 32.
        """
    )
    ZIPV: list | None = Field(
        description="""
        Array of 7 coefficients:

         First 3 are ZIP weighting factors for real power (should sum to 1)
         Next 3 are ZIP weighting factors for reactive power (should sum to 1)
         Last 1 is cut-off voltage in p.u. of base kV; load is 0 below this cut-off
         No defaults; all coefficients must be specified if using model=8.

        DSS property name: `ZIPV`, DSS property index: 33.
        """
    )
    pctSeriesRL: float | None = Field(
        alias="%SeriesRL",
        description="""
        Percent of load that is series R-L for Harmonic studies. Default is 50. Remainder is assumed to be parallel R and L. This can have a significant impact on the amount of damping observed in Harmonics solutions.

        DSS property name: `%SeriesRL`, DSS property index: 34.
        """,
    )
    RelWeight: float | None = Field(
        description="""
        Relative weighting factor for reliability calcs. Default = 1. Used to designate high priority loads such as hospitals, etc.

        Is multiplied by number of customers and load kW during reliability calcs.

        DSS property name: `RelWeight`, DSS property index: 35.
        """
    )
    Vlowpu: float | None = Field(
        description="""
        Default = 0.50.  Per unit voltage at which the model switches to same as constant Z model (model=2). This allows more consistent convergence at very low voltaes due to opening switches or solving for fault situations.

        DSS property name: `Vlowpu`, DSS property index: 36.
        """
    )
    puXharm: float | None = Field(
        description="""
        Special reactance, pu (based on kVA, kV properties), for the series impedance branch in the load model for HARMONICS analysis. Generally used to represent motor load blocked rotor reactance. If not specified (that is, set =0, the default value), the series branch is computed from the percentage of the nominal load at fundamental frequency specified by the %SERIESRL property.

        Applies to load model in HARMONICS mode only.

        A typical value would be approximately 0.20 pu based on kVA * %SeriesRL / 100.0.

        DSS property name: `puXharm`, DSS property index: 37.
        """
    )
    XRharm: float | None = Field(
        description="""
        X/R ratio of the special harmonics mode reactance specified by the puXHARM property at fundamental frequency. Default is 6.

        DSS property name: `XRharm`, DSS property index: 38.
        """
    )
    spectrum: str | None = Field(
        description="""
        Name of harmonic current spectrum for this load.  Default is "defaultload", which is defined when the DSS starts.

        DSS property name: `spectrum`, DSS property index: 39.
        """
    )
    basefreq: float | None = Field(
        description="""
        Base Frequency for ratings.

        DSS property name: `basefreq`, DSS property index: 40.
        """
    )
    enabled: bool | None = Field(
        description="""
        {Yes|No or True|False} Indicates whether this element is enabled.

        DSS property name: `enabled`, DSS property index: 41.
        """
    )

    @root_validator(pre=True)
    def drop_fields(cls, values):
        """Removes undesired fields."""
        return values


class Transformer(OpenDssElementBaseModel):
    """None"""

    phases: int | None = Field(
        description="""
        Number of phases this transformer. Default is 3.

        DSS property name: `phases`, DSS property index: 1.
        """
    )
    windings: int | None = Field(
        description="""
        Number of windings, this transformers. (Also is the number of terminals) Default is 2. This property triggers memory allocation for the Transformer and will cause other properties to revert to default values.

        DSS property name: `windings`, DSS property index: 2.
        """
    )
    pctR: list | None = Field(
        alias="%R",
        description="""
        Percent resistance this winding.  (half of total for a 2-winding).

        DSS property name: `%R`, DSS property index: 9.
        """,
    )
    Rneut: list | None = Field(
        description="""
        Default = -1. Neutral resistance of wye (star)-connected winding in actual ohms. If entered as a negative value, the neutral is assumed to be open, or floating. To solidly ground the neutral, connect the neutral conductor to Node 0 in the Bus property spec for this winding. For example: Bus=MyBusName.1.2.3.0, which is generally the default connection.

        DSS property name: `Rneut`, DSS property index: 10.
        """
    )
    Xneut: list | None = Field(
        description="""
        Neutral reactance of wye(star)-connected winding in actual ohms.  May be + or -.

        DSS property name: `Xneut`, DSS property index: 11.
        """
    )
    buses: list | None = Field(
        description="""
        Use this to specify all the bus connections at once using an array. Example:

        New Transformer.T1 buses="Hibus, lowbus"

        DSS property name: `buses`, DSS property index: 12.
        """
    )
    conns: list | None = Field(
        description="""
        Use this to specify all the Winding connections at once using an array. Example:

        New Transformer.T1 buses="Hibus, lowbus" ~ conns=(delta, wye)

        DSS property name: `conns`, DSS property index: 13.
        """
    )
    kVs: list | None = Field(
        description="""
        Use this to specify the kV ratings of all windings at once using an array. Example:

        New Transformer.T1 buses="Hibus, lowbus"
        ~ conns=(delta, wye)
        ~ kvs=(115, 12.47)

        See kV= property for voltage rules.

        DSS property name: `kVs`, DSS property index: 14.
        """
    )
    kVAs: list | None = Field(
        description="""
        Use this to specify the kVA ratings of all windings at once using an array.

        DSS property name: `kVAs`, DSS property index: 15.
        """
    )
    taps: list | None = Field(
        description="""
        Use this to specify the p.u. tap of all windings at once using an array.

        DSS property name: `taps`, DSS property index: 16.
        """
    )
    XHL: float | None = Field(
        description="""
        Use this to specify the percent reactance, H-L (winding 1 to winding 2).  Use for 2- or 3-winding transformers. On the kVA base of winding 1. See also X12.

        DSS property name: `XHL`, DSS property index: 17.
        """
    )
    XHT: float | None = Field(
        description="""
        Use this to specify the percent reactance, H-T (winding 1 to winding 3).  Use for 3-winding transformers only. On the kVA base of winding 1. See also X13.

        DSS property name: `XHT`, DSS property index: 18.
        """
    )
    XLT: float | None = Field(
        description="""
        Use this to specify the percent reactance, L-T (winding 2 to winding 3).  Use for 3-winding transformers only. On the kVA base of winding 1.  See also X23.

        DSS property name: `XLT`, DSS property index: 19.
        """
    )
    Xscarray: list | None = Field(
        description="""
        Use this to specify the percent reactance between all pairs of windings as an array. All values are on the kVA base of winding 1.  The order of the values is as follows:

        (x12 13 14... 23 24.. 34 ..)

        There will be n(n-1)/2 values, where n=number of windings.

        DSS property name: `Xscarray`, DSS property index: 20.
        """
    )
    thermal: float | None = Field(
        description="""
        Thermal time constant of the transformer in hours.  Typically about 2.

        DSS property name: `thermal`, DSS property index: 21.
        """
    )
    n: float | None = Field(
        description="""
        n Exponent for thermal properties in IEEE C57.  Typically 0.8.

        DSS property name: `n`, DSS property index: 22.
        """
    )
    m: float | None = Field(
        description="""
        m Exponent for thermal properties in IEEE C57.  Typically 0.9 - 1.0

        DSS property name: `m`, DSS property index: 23.
        """
    )
    flrise: float | None = Field(
        description="""
        Temperature rise, deg C, for full load.  Default is 65.

        DSS property name: `flrise`, DSS property index: 24.
        """
    )
    hsrise: float | None = Field(
        description="""
        Hot spot temperature rise, deg C.  Default is 15.

        DSS property name: `hsrise`, DSS property index: 25.
        """
    )
    pctloadloss: float | None = Field(
        alias="%loadloss",
        description="""
        Percent load loss at full load. The %R of the High and Low windings (1 and 2) are adjusted to agree at rated kVA loading.

        DSS property name: `%loadloss`, DSS property index: 26.
        """,
    )
    pctnoloadloss: float | None = Field(
        alias="%noloadloss",
        description="""
        Percent no load losses at rated excitatation voltage. Default is 0. Converts to a resistance in parallel with the magnetizing impedance in each winding.

        DSS property name: `%noloadloss`, DSS property index: 27.
        """,
    )
    normhkVA: float | None = Field(
        description="""
        Normal maximum kVA rating of H winding (winding 1).  Usually 100% - 110% ofmaximum nameplate rating, depending on load shape. Defaults to 110% of kVA rating of Winding 1.

        DSS property name: `normhkVA`, DSS property index: 28.
        """
    )
    emerghkVA: float | None = Field(
        description="""
        Emergency (contingency)  kVA rating of H winding (winding 1).  Usually 140% - 150% ofmaximum nameplate rating, depending on load shape. Defaults to 150% of kVA rating of Winding 1.

        DSS property name: `emerghkVA`, DSS property index: 29.
        """
    )
    sub: bool | None = Field(
        description="""
        ={Yes|No}  Designates whether this transformer is to be considered a substation.Default is No.

        DSS property name: `sub`, DSS property index: 30.
        """
    )
    MaxTap: list | None = Field(
        description="""
        Max per unit tap for the active winding.  Default is 1.10

        DSS property name: `MaxTap`, DSS property index: 31.
        """
    )
    MinTap: list | None = Field(
        description="""
        Min per unit tap for the active winding.  Default is 0.90

        DSS property name: `MinTap`, DSS property index: 32.
        """
    )
    NumTaps: list | None = Field(
        description="""
        Total number of taps between min and max tap.  Default is 32 (16 raise and 16 lower taps about the neutral position). The neutral position is not counted.

        DSS property name: `NumTaps`, DSS property index: 33.
        """
    )
    subname: str | None = Field(
        description="""
        Substation Name. Optional. Default is null. If specified, printed on plots

        DSS property name: `subname`, DSS property index: 34.
        """
    )
    pctimag: float | None = Field(
        alias="%imag",
        description="""
        Percent magnetizing current. Default=0.0. Magnetizing branch is in parallel with windings in each phase. Also, see "ppm_antifloat".

        DSS property name: `%imag`, DSS property index: 35.
        """,
    )
    ppm_antifloat: float | None = Field(
        description="""
        Default=1 ppm.  Parts per million of transformer winding VA rating connected to ground to protect against accidentally floating a winding without a reference. If positive then the effect is adding a very large reactance to ground.  If negative, then a capacitor.

        DSS property name: `ppm_antifloat`, DSS property index: 36.
        """
    )
    pctRs: list | None = Field(
        alias="%Rs",
        description="""
        Use this property to specify all the winding %resistances using an array. Example:

        New Transformer.T1 buses="Hibus, lowbus" ~ %Rs=(0.2  0.3)

        DSS property name: `%Rs`, DSS property index: 37.
        """,
    )
    bank: str | None = Field(
        description="""
        Name of the bank this transformer is part of, for CIM, MultiSpeak, and other interfaces.

        DSS property name: `bank`, DSS property index: 38.
        """
    )
    xfmrcode: str | None = Field(
        alias="XfmrCode",
        description="""
        Name of a library entry for transformer properties. The named XfmrCode must already be defined.

        DSS property name: `XfmrCode`, DSS property index: 39.
        """,
    )
    XRConst: bool | None = Field(
        description="""
        ={Yes|No} Default is NO. Signifies whether or not the X/R is assumed contant for harmonic studies.

        DSS property name: `XRConst`, DSS property index: 40.
        """
    )
    X12: float | None = Field(
        description="""
        Alternative to XHL for specifying the percent reactance from winding 1 to winding 2.  Use for 2- or 3-winding transformers. Percent on the kVA base of winding 1.

        DSS property name: `X12`, DSS property index: 41.
        """
    )
    X13: float | None = Field(
        description="""
        Alternative to XHT for specifying the percent reactance from winding 1 to winding 3.  Use for 3-winding transformers only. Percent on the kVA base of winding 1.

        DSS property name: `X13`, DSS property index: 42.
        """
    )
    X23: float | None = Field(
        description="""
        Alternative to XLT for specifying the percent reactance from winding 2 to winding 3.Use for 3-winding transformers only. Percent on the kVA base of winding 1.

        DSS property name: `X23`, DSS property index: 43.
        """
    )
    LeadLag: str | None = Field(
        description="""
        {Lead | Lag (default) | ANSI (default) | Euro } Designation in mixed Delta-wye connections the relationship between HV to LV winding. Default is ANSI 30 deg lag, e.g., Dy1 of Yd1 vector group. To get typical European Dy11 connection, specify either "lead" or "Euro"

        DSS property name: `LeadLag`, DSS property index: 44.
        """
    )
    WdgCurrents: str | None = Field(
        description="""
        (Read only) Makes winding currents available via return on query (? Transformer.TX.WdgCurrents). Order: Phase 1, Wdg 1, Wdg 2, ..., Phase 2 ...

        DSS property name: `WdgCurrents`, DSS property index: 45.
        """
    )
    Core: str | None = Field(
        description="""
        {Shell*|5-leg|3-Leg|1-phase|core-1-phase|4-leg} Core Type. Used for GIC analysis

        DSS property name: `Core`, DSS property index: 46.
        """
    )
    RdcOhms: list | None = Field(
        description="""
        Winding dc resistance in OHMS. Useful for GIC analysis. From transformer test report. Defaults to 85% of %R property

        DSS property name: `RdcOhms`, DSS property index: 47.
        """
    )
    Seasons: int | None = Field(
        description="""
        Defines the number of ratings to be defined for the transfomer, to be used only when defining seasonal ratings using the "Ratings" property.

        DSS property name: `Seasons`, DSS property index: 48.
        """
    )
    Ratings: list | None = Field(
        description="""
        An array of ratings to be used when the seasonal ratings flag is True. It can be used to insert
        multiple ratings to change during a QSTS simulation to evaluate different ratings in transformers. Is given in kVA

        DSS property name: `Ratings`, DSS property index: 49.
        """
    )
    normamps: float | None = Field(
        description="""
        Normal rated current.

        DSS property name: `normamps`, DSS property index: 50.
        """
    )
    emergamps: float | None = Field(
        description="""
        Maximum or emerg current.

        DSS property name: `emergamps`, DSS property index: 51.
        """
    )
    faultrate: float | None = Field(
        description="""
        Failure rate per year.

        DSS property name: `faultrate`, DSS property index: 52.
        """
    )
    pctperm: float | None = Field(
        description="""
        Percent of failures that become permanent.

        DSS property name: `pctperm`, DSS property index: 53.
        """
    )
    repair: float | None = Field(
        description="""
        Hours to repair.

        DSS property name: `repair`, DSS property index: 54.
        """
    )
    basefreq: float | None = Field(
        description="""
        Base Frequency for ratings.

        DSS property name: `basefreq`, DSS property index: 55.
        """
    )
    enabled: bool | None = Field(
        description="""
        {Yes|No or True|False} Indicates whether this element is enabled.

        DSS property name: `enabled`, DSS property index: 56.
        """
    )

    @root_validator(pre=True)
    def drop_fields(cls, values):
        """Removes undesired fields."""
        values.pop("bus", None)
        values.pop("conn", None)
        values.pop("kV", None)
        values.pop("kVA", None)
        values.pop("tap", None)
        return values


class Capacitor(OpenDssElementBaseModel):
    """None"""

    bus1: str | None = Field(
        description="""
        Name of first bus of 2-terminal capacitor. Examples:
        bus1=busname
        bus1=busname.1.2.3

        If only one bus specified, Bus2 will default to this bus, Node 0, and the capacitor will be a Yg shunt bank.

        DSS property name: `bus1`, DSS property index: 1.
        """
    )
    bus2: str | None = Field(
        description="""
        Name of 2nd bus. Defaults to all phases connected to first bus, node 0, (Shunt Wye Connection) except when Bus2 explicitly specified.

        Not necessary to specify for delta (LL) connection.

        DSS property name: `bus2`, DSS property index: 2.
        """
    )
    phases: int | None = Field(
        description="""
        Number of phases.

        DSS property name: `phases`, DSS property index: 3.
        """
    )
    kvar: list | None = Field(
        description="""
        Total kvar, if one step, or ARRAY of kvar ratings for each step.  Evenly divided among phases. See rules for NUMSTEPS.

        DSS property name: `kvar`, DSS property index: 4.
        """
    )
    kv: float | None = Field(
        description="""
        For 2, 3-phase, kV phase-phase. Otherwise specify actual can rating.

        DSS property name: `kv`, DSS property index: 5.
        """
    )
    conn: str | None = Field(
        description="""
        ={wye | delta |LN |LL}  Default is wye, which is equivalent to LN

        DSS property name: `conn`, DSS property index: 6.
        """
    )
    cmatrix: list | None = Field(
        description="""
        Nodal cap. matrix, lower triangle, microfarads, of the following form:

        cmatrix="c11 | -c21 c22 | -c31 -c32 c33"

        All steps are assumed the same if this property is used.

        DSS property name: `cmatrix`, DSS property index: 7.
        """
    )
    cuf: list | None = Field(
        description="""
        ARRAY of Capacitance, each phase, for each step, microfarads.
        See Rules for NumSteps.

        DSS property name: `cuf`, DSS property index: 8.
        """
    )
    R: list | None = Field(
        description="""
        ARRAY of series resistance in each phase (line), ohms. Default is 0.0

        DSS property name: `R`, DSS property index: 9.
        """
    )
    XL: list | None = Field(
        description="""
        ARRAY of series inductive reactance(s) in each phase (line) for filter, ohms at base frequency. Use this OR "h" property to define filter. Default is 0.0.

        DSS property name: `XL`, DSS property index: 10.
        """
    )
    Harm: list | None = Field(
        description="""
        ARRAY of harmonics to which each step is tuned. Zero is interpreted as meaning zero reactance (no filter). Default is zero.

        DSS property name: `Harm`, DSS property index: 11.
        """
    )
    Numsteps: int | None = Field(
        description="""
        Number of steps in this capacitor bank. Default = 1. Forces reallocation of the capacitance, reactor, and states array.  Rules: If this property was previously =1, the value in the kvar property is divided equally among the steps. The kvar property does not need to be reset if that is accurate.  If the Cuf or Cmatrix property was used previously, all steps are set to the value of the first step. The states property is set to all steps on. All filter steps are set to the same harmonic. If this property was previously >1, the arrays are reallocated, but no values are altered. You must SUBSEQUENTLY assign all array properties.

        DSS property name: `Numsteps`, DSS property index: 12.
        """
    )
    states: list | None = Field(
        description="""
        ARRAY of integers {1|0} states representing the state of each step (on|off). Defaults to 1 when reallocated (on). Capcontrol will modify this array as it turns steps on or off.

        DSS property name: `states`, DSS property index: 13.
        """
    )
    normamps: float | None = Field(
        description="""
        Normal rated current.

        DSS property name: `normamps`, DSS property index: 14.
        """
    )
    emergamps: float | None = Field(
        description="""
        Maximum or emerg current.

        DSS property name: `emergamps`, DSS property index: 15.
        """
    )
    faultrate: float | None = Field(
        description="""
        Failure rate per year.

        DSS property name: `faultrate`, DSS property index: 16.
        """
    )
    pctperm: float | None = Field(
        description="""
        Percent of failures that become permanent.

        DSS property name: `pctperm`, DSS property index: 17.
        """
    )
    repair: float | None = Field(
        description="""
        Hours to repair.

        DSS property name: `repair`, DSS property index: 18.
        """
    )
    basefreq: float | None = Field(
        description="""
        Base Frequency for ratings.

        DSS property name: `basefreq`, DSS property index: 19.
        """
    )
    enabled: bool | None = Field(
        description="""
        {Yes|No or True|False} Indicates whether this element is enabled.

        DSS property name: `enabled`, DSS property index: 20.
        """
    )

    @root_validator(pre=True)
    def drop_fields(cls, values):
        """Removes undesired fields."""
        return values


class Reactor(OpenDssElementBaseModel):
    """None"""

    bus1: str | None = Field(
        description="""
        Name of first bus. Examples:
        bus1=busname
        bus1=busname.1.2.3

        Bus2 property will default to this bus, node 0, unless previously specified. Only Bus1 need be specified for a Yg shunt reactor.

        DSS property name: `bus1`, DSS property index: 1.
        """
    )
    bus2: str | None = Field(
        description="""
        Name of 2nd bus. Defaults to all phases connected to first bus, node 0, (Shunt Wye Connection) except when Bus2 is specifically defined.

        Not necessary to specify for delta (LL) connection

        DSS property name: `bus2`, DSS property index: 2.
        """
    )
    phases: int | None = Field(
        description="""
        Number of phases.

        DSS property name: `phases`, DSS property index: 3.
        """
    )
    kvar: float | None = Field(
        description="""
        Total kvar, all phases.  Evenly divided among phases. Only determines X. Specify R separately

        DSS property name: `kvar`, DSS property index: 4.
        """
    )
    kv: float | None = Field(
        description="""
        For 2, 3-phase, kV phase-phase. Otherwise specify actual coil rating.

        DSS property name: `kv`, DSS property index: 5.
        """
    )
    conn: str | None = Field(
        description="""
        ={wye | delta |LN |LL}  Default is wye, which is equivalent to LN. If Delta, then only one terminal.

        DSS property name: `conn`, DSS property index: 6.
        """
    )
    Rmatrix: list | None = Field(
        description="""
        Resistance matrix, lower triangle, ohms at base frequency. Order of the matrix is the number of phases. Mutually exclusive to specifying parameters by kvar or X.

        DSS property name: `Rmatrix`, DSS property index: 7.
        """
    )
    Xmatrix: list | None = Field(
        description="""
        Reactance matrix, lower triangle, ohms at base frequency. Order of the matrix is the number of phases. Mutually exclusive to specifying parameters by kvar or X.

        DSS property name: `Xmatrix`, DSS property index: 8.
        """
    )
    Parallel: bool | None = Field(
        description="""
        {Yes | No}  Default=No. Indicates whether Rmatrix and Xmatrix are to be considered in parallel. Default is series. For other models, specify R and Rp.

        DSS property name: `Parallel`, DSS property index: 9.
        """
    )
    R: float | None = Field(
        description="""
        Resistance (in series with reactance), each phase, ohms. This property applies to REACTOR specified by either kvar or X. See also help on Z.

        DSS property name: `R`, DSS property index: 10.
        """
    )
    X: float | None = Field(
        description="""
        Reactance, each phase, ohms at base frequency. See also help on Z and LmH properties.

        DSS property name: `X`, DSS property index: 11.
        """
    )
    Rp: float | None = Field(
        description="""
        Resistance in parallel with R and X (the entire branch). Assumed infinite if not specified.

        DSS property name: `Rp`, DSS property index: 12.
        """
    )
    Z1: complex | None = Field(
        description="""
        Positive-sequence impedance, ohms, as a 2-element array representing a complex number. Example:

        Z1=[1, 2]  ! represents 1 + j2

        If defined, Z1, Z2, and Z0 are used to define the impedance matrix of the REACTOR. Z1 MUST BE DEFINED TO USE THIS OPTION FOR DEFINING THE MATRIX.

        Side Effect: Sets Z2 and Z0 to same values unless they were previously defined.

        DSS property name: `Z1`, DSS property index: 13.
        """
    )
    Z2: complex | None = Field(
        description="""
        Negative-sequence impedance, ohms, as a 2-element array representing a complex number. Example:

        Z2=[1, 2]  ! represents 1 + j2

        Used to define the impedance matrix of the REACTOR if Z1 is also specified.

        Note: Z2 defaults to Z1 if it is not specifically defined. If Z2 is not equal to Z1, the impedance matrix is asymmetrical.

        DSS property name: `Z2`, DSS property index: 14.
        """
    )
    Z0: complex | None = Field(
        description="""
        Zer0-sequence impedance, ohms, as a 2-element array representing a complex number. Example:

        Z0=[3, 4]  ! represents 3 + j4

        Used to define the impedance matrix of the REACTOR if Z1 is also specified.

        Note: Z0 defaults to Z1 if it is not specifically defined.

        DSS property name: `Z0`, DSS property index: 15.
        """
    )
    RCurve: str | None = Field(
        description="""
        Name of XYCurve object, previously defined, describing per-unit variation of phase resistance, R, vs. frequency. Applies to resistance specified by R or Z property. If actual values are not known, R often increases by approximately the square root of frequency.

        DSS property name: `RCurve`, DSS property index: 17.
        """
    )
    LCurve: str | None = Field(
        description="""
        Name of XYCurve object, previously defined, describing per-unit variation of phase inductance, L=X/w, vs. frequency. Applies to reactance specified by X, LmH, Z, or kvar property.L generally decreases somewhat with frequency above the base frequency, approaching a limit at a few kHz.

        DSS property name: `LCurve`, DSS property index: 18.
        """
    )
    LmH: float | None = Field(
        description="""
        Inductance, mH. Alternate way to define the reactance, X, property.

        DSS property name: `LmH`, DSS property index: 19.
        """
    )
    normamps: float | None = Field(
        description="""
        Normal rated current.

        DSS property name: `normamps`, DSS property index: 20.
        """
    )
    emergamps: float | None = Field(
        description="""
        Maximum or emerg current.

        DSS property name: `emergamps`, DSS property index: 21.
        """
    )
    faultrate: float | None = Field(
        description="""
        Failure rate per year.

        DSS property name: `faultrate`, DSS property index: 22.
        """
    )
    pctperm: float | None = Field(
        description="""
        Percent of failures that become permanent.

        DSS property name: `pctperm`, DSS property index: 23.
        """
    )
    repair: float | None = Field(
        description="""
        Hours to repair.

        DSS property name: `repair`, DSS property index: 24.
        """
    )
    basefreq: float | None = Field(
        description="""
        Base Frequency for ratings.

        DSS property name: `basefreq`, DSS property index: 25.
        """
    )
    enabled: bool | None = Field(
        description="""
        {Yes|No or True|False} Indicates whether this element is enabled.

        DSS property name: `enabled`, DSS property index: 26.
        """
    )

    @root_validator(pre=True)
    def drop_fields(cls, values):
        """Removes undesired fields."""
        return values


class CapControl(OpenDssElementBaseModel):
    """None"""

    element: str | None = Field(
        description="""
        Full object name of the circuit element, typically a line or transformer, to which the capacitor control's PT and/or CT are connected.There is no default; must be specified.

        DSS property name: `element`, DSS property index: 1.
        """
    )
    terminal: int | None = Field(
        description="""
        Number of the terminal of the circuit element to which the CapControl is connected. 1 or 2, typically.  Default is 1.

        DSS property name: `terminal`, DSS property index: 2.
        """
    )
    capacitor: str | None = Field(
        description="""
        Name of Capacitor element which the CapControl controls. No Default; Must be specified.Do not specify the full object name; "Capacitor" is assumed for the object class.  Example:

        Capacitor=cap1

        DSS property name: `capacitor`, DSS property index: 3.
        """
    )
    type: str | None = Field(
        description="""
        {Current | Voltage | kvar | PF | Time | Follow} Control type.  Specify the ONsetting and OFFsetting appropriately with the type of control. (See help for ONsetting)

        DSS property name: `type`, DSS property index: 4.
        """
    )
    PTratio: float | None = Field(
        description="""
        Ratio of the PT that converts the monitored voltage to the control voltage. Default is 60.  If the capacitor is Wye, the 1st phase line-to-neutral voltage is monitored.  Else, the line-to-line voltage (1st - 2nd phase) is monitored.

        DSS property name: `PTratio`, DSS property index: 5.
        """
    )
    CTratio: float | None = Field(
        description="""
        Ratio of the CT from line amps to control ampere setting for current and kvar control types.

        DSS property name: `CTratio`, DSS property index: 6.
        """
    )
    ONsetting: float | None = Field(
        description="""
        Value at which the control arms to switch the capacitor ON (or ratchet up a step).

        Type of Control:

        Current: Line Amps / CTratio
        Voltage: Line-Neutral (or Line-Line for delta) Volts / PTratio
        kvar:    Total kvar, all phases (3-phase for pos seq model). This is directional.
        PF:      Power Factor, Total power in monitored terminal. Negative for Leading.
        Time:    Hrs from Midnight as a floating point number (decimal). 7:30am would be entered as 7.5.
        Follow:  Follows a loadshape (ControlSignal) to determine when to turn ON/OFF the capacitor. If the value is different than 0 the capacitor will connect to the grid, otherwise, it will be disconnected.

        DSS property name: `ONsetting`, DSS property index: 7.
        """
    )
    OFFsetting: float | None = Field(
        description="""
        Value at which the control arms to switch the capacitor OFF. (See help for ONsetting)For Time control, is OK to have Off time the next day ( < On time)

        DSS property name: `OFFsetting`, DSS property index: 8.
        """
    )
    Delay: float | None = Field(
        description="""
        Time delay, in seconds, from when the control is armed before it sends out the switching command to turn ON.  The control may reset before the action actually occurs. This is used to determine which capacity control will act first. Default is 15.  You may specify any floating point number to achieve a model of whatever condition is necessary.

        DSS property name: `Delay`, DSS property index: 9.
        """
    )
    VoltOverride: bool | None = Field(
        description="""
        {Yes | No}  Default is No.  Switch to indicate whether VOLTAGE OVERRIDE is to be considered. Vmax and Vmin must be set to reasonable values if this property is Yes.

        DSS property name: `VoltOverride`, DSS property index: 10.
        """
    )
    Vmax: float | None = Field(
        description="""
        Maximum voltage, in volts.  If the voltage across the capacitor divided by the PTRATIO is greater than this voltage, the capacitor will switch OFF regardless of other control settings. Default is 126 (goes with a PT ratio of 60 for 12.47 kV system).

        DSS property name: `Vmax`, DSS property index: 11.
        """
    )
    Vmin: float | None = Field(
        description="""
        Minimum voltage, in volts.  If the voltage across the capacitor divided by the PTRATIO is less than this voltage, the capacitor will switch ON regardless of other control settings. Default is 115 (goes with a PT ratio of 60 for 12.47 kV system).

        DSS property name: `Vmin`, DSS property index: 12.
        """
    )
    DelayOFF: float | None = Field(
        description="""
        Time delay, in seconds, for control to turn OFF when present state is ON. Default is 15.

        DSS property name: `DelayOFF`, DSS property index: 13.
        """
    )
    DeadTime: float | None = Field(
        description="""
        Dead time after capacitor is turned OFF before it can be turned back ON. Default is 300 sec.

        DSS property name: `DeadTime`, DSS property index: 14.
        """
    )
    CTPhase: str | None = Field(
        description="""
        Number of the phase being monitored for CURRENT control or one of {AVG | MAX | MIN} for all phases. Default=1. If delta or L-L connection, enter the first or the two phases being monitored [1-2, 2-3, 3-1]. Must be less than the number of phases. Does not apply to kvar control which uses all phases by default.

        DSS property name: `CTPhase`, DSS property index: 15.
        """
    )
    PTPhase: str | None = Field(
        description="""
        Number of the phase being monitored for VOLTAGE control or one of {AVG | MAX | MIN} for all phases. Default=1. If delta or L-L connection, enter the first or the two phases being monitored [1-2, 2-3, 3-1]. Must be less than the number of phases. Does not apply to kvar control which uses all phases by default.

        DSS property name: `PTPhase`, DSS property index: 16.
        """
    )
    VBus: str | None = Field(
        description="""
        Name of bus to use for voltage override function. Default is bus at monitored terminal. Sometimes it is useful to monitor a bus in another location to emulate various DMS control algorithms.

        DSS property name: `VBus`, DSS property index: 17.
        """
    )
    EventLog: bool | None = Field(
        description="""
        {Yes/True* | No/False} Default is YES for CapControl. Log control actions to Eventlog.

        DSS property name: `EventLog`, DSS property index: 18.
        """
    )
    UserModel: str | None = Field(
        description="""
        Name of DLL containing user-written CapControl model, overriding the default model.  Set to "none" to negate previous setting.

        DSS property name: `UserModel`, DSS property index: 19.
        """
    )
    UserData: str | None = Field(
        description="""
        String (in quotes or parentheses if necessary) that gets passed to the user-written CapControl model Edit function for defining the data required for that model.

        DSS property name: `UserData`, DSS property index: 20.
        """
    )
    pctMinkvar: float | None = Field(
        description="""
        For PF control option, min percent of total bank kvar at which control will close capacitor switch. Default = 50.

        DSS property name: `pctMinkvar`, DSS property index: 21.
        """
    )
    ControlSignal: str | None = Field(
        description="""
        Load shape used for controlling the connection/disconnection of the capacitor to the grid, when the load shape is DIFFERENT than ZERO (0) the capacitor will be ON and conencted to the grid. Otherwise, if the load shape value is EQUAL to ZERO (0) the capacitor bank will be OFF and disconnected from the grid.

        DSS property name: `ControlSignal`, DSS property index: 23.
        """
    )
    basefreq: float | None = Field(
        description="""
        Base Frequency for ratings.

        DSS property name: `basefreq`, DSS property index: 24.
        """
    )
    enabled: bool | None = Field(
        description="""
        {Yes|No or True|False} Indicates whether this element is enabled.

        DSS property name: `enabled`, DSS property index: 25.
        """
    )

    @root_validator(pre=True)
    def drop_fields(cls, values):
        """Removes undesired fields."""
        return values


class Fault(OpenDssElementBaseModel):
    """None"""

    bus1: str | None = Field(
        description="""
        Name of first bus. Examples:

        bus1=busname
        bus1=busname.1.2.3

        Bus2 automatically defaults to busname.0,0,0 unless it was previously defined.

        DSS property name: `bus1`, DSS property index: 1.
        """
    )
    bus2: str | None = Field(
        description="""
        Name of 2nd bus of the 2-terminal Fault object. Defaults to all phases connected to first bus, node 0, if not specified. (Shunt Wye Connection to ground reference)

        That is, the Fault defaults to a ground fault unless otherwise specified.

        DSS property name: `bus2`, DSS property index: 2.
        """
    )
    phases: int | None = Field(
        description="""
        Number of Phases. Default is 1.

        DSS property name: `phases`, DSS property index: 3.
        """
    )
    r: float | None = Field(
        description="""
        Resistance, each phase, ohms. Default is 0.0001. Assumed to be Mean value if gaussian random mode.Max value if uniform mode.  A Fault is actually a series resistance that defaults to a wye connection to ground on the second terminal.  You may reconnect the 2nd terminal to achieve whatever connection.  Use the Gmatrix property to specify an arbitrary conductance matrix.

        DSS property name: `r`, DSS property index: 4.
        """
    )
    pctstddev: float | None = Field(
        alias="%stddev",
        description="""
        Percent standard deviation in resistance to assume for Monte Carlo fault (MF) solution mode for GAUSSIAN distribution. Default is 0 (no variation from mean).

        DSS property name: `%stddev`, DSS property index: 5.
        """,
    )
    Gmatrix: list | None = Field(
        description="""
        Use this to specify a nodal conductance (G) matrix to represent some arbitrary resistance network. Specify in lower triangle form as usual for DSS matrices.

        DSS property name: `Gmatrix`, DSS property index: 6.
        """
    )
    ONtime: float | None = Field(
        description="""
        Time (sec) at which the fault is established for time varying simulations. Default is 0.0 (on at the beginning of the simulation)

        DSS property name: `ONtime`, DSS property index: 7.
        """
    )
    temporary: bool | None = Field(
        description="""
        {Yes | No} Default is No.  Designate whether the fault is temporary.  For Time-varying simulations, the fault will be removed if the current through the fault drops below the MINAMPS criteria.

        DSS property name: `temporary`, DSS property index: 8.
        """
    )
    MinAmps: float | None = Field(
        description="""
        Minimum amps that can sustain a temporary fault. Default is 5.

        DSS property name: `MinAmps`, DSS property index: 9.
        """
    )
    normamps: float | None = Field(
        description="""
        Normal rated current.

        DSS property name: `normamps`, DSS property index: 10.
        """
    )
    emergamps: float | None = Field(
        description="""
        Maximum or emerg current.

        DSS property name: `emergamps`, DSS property index: 11.
        """
    )
    faultrate: float | None = Field(
        description="""
        Failure rate per year.

        DSS property name: `faultrate`, DSS property index: 12.
        """
    )
    pctperm: float | None = Field(
        description="""
        Percent of failures that become permanent.

        DSS property name: `pctperm`, DSS property index: 13.
        """
    )
    repair: float | None = Field(
        description="""
        Hours to repair.

        DSS property name: `repair`, DSS property index: 14.
        """
    )
    basefreq: float | None = Field(
        description="""
        Base Frequency for ratings.

        DSS property name: `basefreq`, DSS property index: 15.
        """
    )
    enabled: bool | None = Field(
        description="""
        {Yes|No or True|False} Indicates whether this element is enabled.

        DSS property name: `enabled`, DSS property index: 16.
        """
    )

    @root_validator(pre=True)
    def drop_fields(cls, values):
        """Removes undesired fields."""
        return values


class DynamicExp(OpenDssElementBaseModel):
    """None"""

    NVariables: int | None = Field(
        description="""
        (Int) Number of state variables to be considered in the differential equation.

        DSS property name: `NVariables`, DSS property index: 1.
        """
    )
    VarNames: list | None = Field(
        description="""
        ([String]) Array of strings with the names of the state variables.

        DSS property name: `VarNames`, DSS property index: 2.
        """
    )
    var: str | None = Field(
        description="""
        (String) Activates the state variable using the given name.

        DSS property name: `var`, DSS property index: 3.
        """
    )
    VarIdx: int | None = Field(
        description="""
        (Int) read-only, returns the index of the active state variable.

        DSS property name: `VarIdx`, DSS property index: 4.
        """
    )
    Expression: str | None = Field(
        description="""
        It is the differential expression using OpenDSS RPN syntax. The expression must be contained within brackets in case of having multiple equations, for example:

        expression="[w dt = 1 M / (P_m D*w - P_e -) *]"

        DSS property name: `Expression`, DSS property index: 5.
        """
    )
    Domain: str | None = Field(
        description="""
        It is the domain for which the equation is defined, it can be one of [time*, dq]. By deafult, dynamic epxressions are defined in the time domain.

        DSS property name: `Domain`, DSS property index: 6.
        """
    )

    @root_validator(pre=True)
    def drop_fields(cls, values):
        """Removes undesired fields."""
        return values


class Generator(OpenDssElementBaseModel):
    """None"""

    phases: int | None = Field(
        description="""
        Number of Phases, this Generator.  Power is evenly divided among phases.

        DSS property name: `phases`, DSS property index: 1.
        """
    )
    bus1: str | None = Field(
        description="""
        Bus to which the Generator is connected.  May include specific node specification.

        DSS property name: `bus1`, DSS property index: 2.
        """
    )
    kv: float | None = Field(
        description="""
        Nominal rated (1.0 per unit) voltage, kV, for Generator. For 2- and 3-phase Generators, specify phase-phase kV. Otherwise, for phases=1 or phases>3, specify actual kV across each branch of the Generator. If wye (star), specify phase-neutral kV. If delta or phase-phase connected, specify phase-phase kV.

        DSS property name: `kv`, DSS property index: 3.
        """
    )
    kW: float | None = Field(
        description="""
        Total base kW for the Generator.  A positive value denotes power coming OUT of the element,
        which is the opposite of a load. This value is modified depending on the dispatch mode. Unaffected by the global load multiplier and growth curves. If you want there to be more generation, you must add more generators or change this value.

        DSS property name: `kW`, DSS property index: 4.
        """
    )
    pf: float | None = Field(
        description="""
        Generator power factor. Default is 0.80. Enter negative for leading powerfactor (when kW and kvar have opposite signs.)
        A positive power factor for a generator signifies that the generator produces vars
        as is typical for a synchronous generator.  Induction machines would be
        specified with a negative power factor.

        DSS property name: `pf`, DSS property index: 5.
        """
    )
    kvar: float | None = Field(
        description="""
        Specify the base kvar.  Alternative to specifying the power factor.  Side effect:  the power factor value is altered to agree based on present value of kW.

        DSS property name: `kvar`, DSS property index: 6.
        """
    )
    model: int | None = Field(
        description="""
        Integer code for the model to use for generation variation with voltage. Valid values are:

        1:Generator injects a constant kW at specified power factor.
        2:Generator is modeled as a constant admittance.
        3:Const kW, constant kV.  Somewhat like a conventional transmission power flow P-V generator.
        4:Const kW, Fixed Q (Q never varies)
        5:Const kW, Fixed Q(as a constant reactance)
        6:Compute load injection from User-written Model.(see usage of Xd, Xdp)
        7:Constant kW, kvar, but current-limited below Vminpu. Approximates a simple inverter. See also Balanced.

        DSS property name: `model`, DSS property index: 7.
        """
    )
    Vminpu: float | None = Field(
        description="""
        Default = 0.90.  Minimum per unit voltage for which the Model is assumed to apply. Below this value, the load model reverts to a constant impedance model. For model 7, the current is limited to the value computed for constant power at Vminpu.

        DSS property name: `Vminpu`, DSS property index: 8.
        """
    )
    Vmaxpu: float | None = Field(
        description="""
        Default = 1.10.  Maximum per unit voltage for which the Model is assumed to apply. Above this value, the load model reverts to a constant impedance model.

        DSS property name: `Vmaxpu`, DSS property index: 9.
        """
    )
    yearly: str | None = Field(
        description="""
        Dispatch shape to use for yearly simulations.  Must be previously defined as a Loadshape object. If this is not specified, a constant value is assumed (no variation). If the generator is assumed to be ON continuously, specify Status=FIXED, or designate a curve that is 1.0 per unit at all times. Set to NONE to reset to no loadahape. Nominally for 8760 simulations.  If there are fewer points in the designated shape than the number of points in the solution, the curve is repeated.

        DSS property name: `yearly`, DSS property index: 10.
        """
    )
    daily: str | None = Field(
        description="""
        Dispatch shape to use for daily simulations.  Must be previously defined as a Loadshape object of 24 hrs, typically.  If generator is assumed to be ON continuously, specify Status=FIXED, or designate a Loadshape objectthat is 1.0 perunit for all hours. Set to NONE to reset to no loadahape.

        DSS property name: `daily`, DSS property index: 11.
        """
    )
    duty: str | None = Field(
        description="""
        Load shape to use for duty cycle dispatch simulations such as for wind generation. Must be previously defined as a Loadshape object. Typically would have time intervals less than 1 hr -- perhaps, in seconds. Set Status=Fixed to ignore Loadshape designation. Set to NONE to reset to no loadahape. Designate the number of points to solve using the Set Number=xxxx command. If there are fewer points in the actual shape, the shape is assumed to repeat.

        DSS property name: `duty`, DSS property index: 12.
        """
    )
    dispmode: str | None = Field(
        description="""
        {Default* | Loadlevel | Price } Default = Default. Dispatch mode. In default mode, gen is either always on or follows dispatch curve as specified. Otherwise, the gen comes on when either the global default load level (Loadshape "default") or the price level exceeds the dispatch value.

        DSS property name: `dispmode`, DSS property index: 13.
        """
    )
    dispvalue: float | None = Field(
        description="""
        Dispatch value.
        If = 0.0 (default) then Generator follow dispatch curves, if any.
        If > 0  then Generator is ON only when either the price signal (in Price dispatch mode) exceeds this value or the active circuit load multiplier * "default" loadshape value * the default yearly growth factor exceeds this value.  Then the generator follows dispatch curves (duty, daily, or yearly), if any (see also Status).

        DSS property name: `dispvalue`, DSS property index: 14.
        """
    )
    conn: str | None = Field(
        description="""
        ={wye|LN|delta|LL}.  Default is wye.

        DSS property name: `conn`, DSS property index: 15.
        """
    )
    status: str | None = Field(
        description="""
        ={Fixed | Variable*}.  If Fixed, then dispatch multipliers do not apply. The generator is alway at full power when it is ON.  Default is Variable  (follows curves).

        DSS property name: `status`, DSS property index: 16.
        """
    )
    cls: int | None = Field(
        alias="class",
        description="""
        An arbitrary integer number representing the class of Generator so that Generator values may be segregated by class.

        DSS property name: `class`, DSS property index: 17.
        """,
    )
    Vpu: float | None = Field(
        description="""
        Per Unit voltage set point for Model = 3  (typical power flow model).  Default is 1.0.

        DSS property name: `Vpu`, DSS property index: 18.
        """
    )
    maxkvar: float | None = Field(
        description="""
        Maximum kvar limit for Model = 3.  Defaults to twice the specified load kvar.  Always reset this if you change PF or kvar properties.

        DSS property name: `maxkvar`, DSS property index: 19.
        """
    )
    minkvar: float | None = Field(
        description="""
        Minimum kvar limit for Model = 3. Enter a negative number if generator can absorb vars. Defaults to negative of Maxkvar.  Always reset this if you change PF or kvar properties.

        DSS property name: `minkvar`, DSS property index: 20.
        """
    )
    pvfactor: float | None = Field(
        description="""
        Deceleration factor for P-V generator model (Model=3).  Default is 0.1. If the circuit converges easily, you may want to use a higher number such as 1.0. Use a lower number if solution diverges. Use Debugtrace=yes to create a file that will trace the convergence of a generator model.

        DSS property name: `pvfactor`, DSS property index: 21.
        """
    )
    forceon: bool | None = Field(
        description="""
        {Yes | No}  Forces generator ON despite requirements of other dispatch modes. Stays ON until this property is set to NO, or an internal algorithm cancels the forced ON state.

        DSS property name: `forceon`, DSS property index: 22.
        """
    )
    kVA: float | None = Field(
        description="""
        kVA rating of electrical machine. Defaults to 1.2* kW if not specified. Applied to machine or inverter definition for Dynamics mode solutions.

        DSS property name: `kVA`, DSS property index: 23.
        """
    )
    Xd: float | None = Field(
        description="""
        Per unit synchronous reactance of machine. Presently used only for Thevinen impedance for power flow calcs of user models (model=6). Typically use a value 0.4 to 1.0. Default is 1.0

        DSS property name: `Xd`, DSS property index: 25.
        """
    )
    Xdp: float | None = Field(
        description="""
        Per unit transient reactance of the machine.  Used for Dynamics mode and Fault studies.  Default is 0.27.For user models, this value is used for the Thevinen/Norton impedance for Dynamics Mode.

        DSS property name: `Xdp`, DSS property index: 26.
        """
    )
    Xdpp: float | None = Field(
        description="""
        Per unit subtransient reactance of the machine.  Used for Harmonics. Default is 0.20.

        DSS property name: `Xdpp`, DSS property index: 27.
        """
    )
    H: float | None = Field(
        description="""
        Per unit mass constant of the machine.  MW-sec/MVA.  Default is 1.0.

        DSS property name: `H`, DSS property index: 28.
        """
    )
    D: float | None = Field(
        description="""
        Damping constant.  Usual range is 0 to 4. Default is 1.0.  Adjust to get damping

        DSS property name: `D`, DSS property index: 29.
        """
    )
    UserModel: str | None = Field(
        description="""
        Name of DLL containing user-written model, which computes the terminal currents for Dynamics studies, overriding the default model.  Set to "none" to negate previous setting.

        DSS property name: `UserModel`, DSS property index: 30.
        """
    )
    UserData: str | None = Field(
        description="""
        String (in quotes or parentheses) that gets passed to user-written model for defining the data required for that model.

        DSS property name: `UserData`, DSS property index: 31.
        """
    )
    ShaftModel: str | None = Field(
        description="""
        Name of user-written DLL containing a Shaft model, which models the prime mover and determines the power on the shaft for Dynamics studies. Models additional mass elements other than the single-mass model in the DSS default model. Set to "none" to negate previous setting.

        DSS property name: `ShaftModel`, DSS property index: 32.
        """
    )
    ShaftData: str | None = Field(
        description="""
        String (in quotes or parentheses) that gets passed to user-written shaft dynamic model for defining the data for that model.

        DSS property name: `ShaftData`, DSS property index: 33.
        """
    )
    DutyStart: float | None = Field(
        description="""
        Starting time offset [hours] into the duty cycle shape for this generator, defaults to 0

        DSS property name: `DutyStart`, DSS property index: 34.
        """
    )
    debugtrace: bool | None = Field(
        description="""
        {Yes | No }  Default is no.  Turn this on to capture the progress of the generator model for each iteration.  Creates a separate file for each generator named "GEN_name.csv".

        DSS property name: `debugtrace`, DSS property index: 35.
        """
    )
    Balanced: bool | None = Field(
        description="""
        {Yes | No*} Default is No.  For Model=7, force balanced current only for 3-phase generators. Force zero- and negative-sequence to zero.

        DSS property name: `Balanced`, DSS property index: 36.
        """
    )
    XRdp: float | None = Field(
        description="""
        Default is 20. X/R ratio for Xdp property for FaultStudy and Dynamic modes.

        DSS property name: `XRdp`, DSS property index: 37.
        """
    )
    UseFuel: bool | None = Field(
        description="""
        {Yes | *No}. Activates the use of fuel for the operation of the generator. When the fuel level reaches the reserve level, the generator stops until it gets refueled. By default, the generator is connected to a continuous fuel supply, Use this mode to mimic dependency on fuel level for different generation technologies.

        DSS property name: `UseFuel`, DSS property index: 38.
        """
    )
    FuelkWh: float | None = Field(
        description="""
        {*0}Is the nominal level of fuel for the generator (kWh). It only applies if UseFuel = Yes/True

        DSS property name: `FuelkWh`, DSS property index: 39.
        """
    )
    pctFuel: float | None = Field(
        alias="%fuel",
        description="""
        It is a number between 0 and 100 representing the current amount of fuel avaiable in percentage of FuelkWh. It only applies if UseFuel = Yes/True

        DSS property name: `%Fuel`, DSS property index: 40.
        """,
    )
    pctReserve: float | None = Field(
        alias="%reserve",
        description="""
        It is a number between 0 and 100 representing the reserve level in percentage of FuelkWh. It only applies if UseFuel = Yes/True

        DSS property name: `%Reserve`, DSS property index: 41.
        """,
    )
    DynamicEq: str | None = Field(
        description="""
        The name of the dynamic equation (DynamicExp) that will be used for defining the dynamic behavior of the generator. if not defined, the generator dynamics will follow the built-in dynamic equation.

        DSS property name: `DynamicEq`, DSS property index: 43.
        """
    )
    DynOut: str | None = Field(
        description="""
        The name of the variables within the Dynamic equation that will be used to govern the generator dynamics.This generator model requires 2 outputs from the dynamic equation:

        1. Shaft speed (velocity) relative to synchronous speed.
        2. Shaft, or power, angle (relative to synchronous reference frame).

        The output variables need to be defined in tha strict order.

        DSS property name: `DynOut`, DSS property index: 44.
        """
    )
    spectrum: str | None = Field(
        description="""
        Name of harmonic voltage or current spectrum for this generator. Voltage behind Xd" for machine - default. Current injection for inverter. Default value is "default", which is defined when the DSS starts.

        DSS property name: `spectrum`, DSS property index: 45.
        """
    )
    basefreq: float | None = Field(
        description="""
        Base Frequency for ratings.

        DSS property name: `basefreq`, DSS property index: 46.
        """
    )
    enabled: bool | None = Field(
        description="""
        {Yes|No or True|False} Indicates whether this element is enabled.

        DSS property name: `enabled`, DSS property index: 47.
        """
    )

    @root_validator(pre=True)
    def drop_fields(cls, values):
        """Removes undesired fields."""
        return values


class GenDispatcher(OpenDssElementBaseModel):
    """None"""

    Element: str | None = Field(
        description="""
        Full object name of the circuit element, typically a line or transformer, which the control is monitoring. There is no default; must be specified.

        DSS property name: `Element`, DSS property index: 1.
        """
    )
    Terminal: int | None = Field(
        description="""
        Number of the terminal of the circuit element to which the GenDispatcher control is connected. 1 or 2, typically.  Default is 1. Make sure you have the direction on the power matching the sign of kWLimit.

        DSS property name: `Terminal`, DSS property index: 2.
        """
    )
    kWLimit: float | None = Field(
        description="""
        kW Limit for the monitored element. The generators are dispatched to hold the power in band.

        DSS property name: `kWLimit`, DSS property index: 3.
        """
    )
    kWBand: float | None = Field(
        description="""
        Bandwidth (kW) of the dead band around the target limit.No dispatch changes are attempted if the power in the monitored terminal stays within this band.

        DSS property name: `kWBand`, DSS property index: 4.
        """
    )
    kvarlimit: float | None = Field(
        description="""
        Max kvar to be delivered through the element.  Uses same dead band as kW.

        DSS property name: `kvarlimit`, DSS property index: 5.
        """
    )
    GenList: list | None = Field(
        description="""
        Array list of generators to be dispatched.  If not specified, all generators in the circuit are assumed dispatchable.

        DSS property name: `GenList`, DSS property index: 6.
        """
    )
    Weights: list | None = Field(
        description="""
        GenDispatcher.Weights

        DSS property name: `Weights`, DSS property index: 7.
        """
    )
    basefreq: float | None = Field(
        description="""
        Base Frequency for ratings.

        DSS property name: `basefreq`, DSS property index: 8.
        """
    )
    enabled: bool | None = Field(
        description="""
        {Yes|No or True|False} Indicates whether this element is enabled.

        DSS property name: `enabled`, DSS property index: 9.
        """
    )

    @root_validator(pre=True)
    def drop_fields(cls, values):
        """Removes undesired fields."""
        return values


class Storage(OpenDssElementBaseModel):
    """None"""

    phases: int | None = Field(
        description="""
        Number of Phases, this Storage element.  Power is evenly divided among phases.

        DSS property name: `phases`, DSS property index: 1.
        """
    )
    bus1: str | None = Field(
        description="""
        Bus to which the Storage element is connected.  May include specific node specification.

        DSS property name: `bus1`, DSS property index: 2.
        """
    )
    kv: float | None = Field(
        description="""
        Nominal rated (1.0 per unit) voltage, kV, for Storage element. For 2- and 3-phase Storage elements, specify phase-phase kV. Otherwise, specify actual kV across each branch of the Storage element.

        If wye (star), specify phase-neutral kV.

        If delta or phase-phase connected, specify phase-phase kV.

        DSS property name: `kv`, DSS property index: 3.
        """
    )
    conn: str | None = Field(
        description="""
        ={wye|LN|delta|LL}.  Default is wye.

        DSS property name: `conn`, DSS property index: 4.
        """
    )
    kW: float | None = Field(
        description="""
        Get/set the requested kW value. Final kW is subjected to the inverter ratings. A positive value denotes power coming OUT of the element, which is the opposite of a Load element. A negative value indicates the Storage element is in Charging state. This value is modified internally depending on the dispatch mode.

        DSS property name: `kW`, DSS property index: 5.
        """
    )
    kvar: float | None = Field(
        description="""
        Get/set the requested kvar value. Final kvar is subjected to the inverter ratings. Sets inverter to operate in constant kvar mode.

        DSS property name: `kvar`, DSS property index: 6.
        """
    )
    pf: float | None = Field(
        description="""
        Get/set the requested PF value. Final PF is subjected to the inverter ratings. Sets inverter to operate in constant PF mode. Nominally, the power factor for discharging (acting as a generator). Default is 1.0.

        Enter negative for leading power factor (when kW and kvar have opposite signs.)

        A positive power factor signifies kw and kvar at the same direction.

        DSS property name: `pf`, DSS property index: 7.
        """
    )
    kVA: float | None = Field(
        description="""
        Indicates the inverter nameplate capability (in kVA). Used as the base for Dynamics mode and Harmonics mode values.

        DSS property name: `kVA`, DSS property index: 8.
        """
    )
    pctCutin: float | None = Field(
        alias="%cutin",
        description="""
        Cut-in power as a percentage of inverter kVA rating. It is the minimum DC power necessary to turn the inverter ON when it is OFF. Must be greater than or equal to %CutOut. Defaults to 2 for PVSystems and 0 for Storage elements which means that the inverter state will be always ON for this element.

        DSS property name: `%Cutin`, DSS property index: 9.
        """,
    )
    pctCutout: float | None = Field(
        alias="%cutout",
        description="""
        Cut-out power as a percentage of inverter kVA rating. It is the minimum DC power necessary to keep the inverter ON. Must be less than or equal to %CutIn. Defaults to 0, which means that, once ON, the inverter state will be always ON for this element.

        DSS property name: `%Cutout`, DSS property index: 10.
        """,
    )
    EffCurve: str | None = Field(
        description="""
        An XYCurve object, previously defined, that describes the PER UNIT efficiency vs PER UNIT of rated kVA for the inverter. Power at the AC side of the inverter is discounted by the multiplier obtained from this curve.

        DSS property name: `EffCurve`, DSS property index: 11.
        """
    )
    VarFollowInverter: bool | None = Field(
        description="""
        Boolean variable (Yes|No) or (True|False). Defaults to False, which indicates that the reactive power generation/absorption does not respect the inverter status.When set to True, the reactive power generation/absorption will cease when the inverter status is off, due to DC kW dropping below %CutOut.  The reactive power generation/absorption will begin again when the DC kW is above %CutIn.  When set to False, the Storage will generate/absorb reactive power regardless of the status of the inverter.

        DSS property name: `VarFollowInverter`, DSS property index: 12.
        """
    )
    kvarMax: float | None = Field(
        description="""
        Indicates the maximum reactive power GENERATION (un-signed numerical variable in kvar) for the inverter. Defaults to kVA rating of the inverter.

        DSS property name: `kvarMax`, DSS property index: 13.
        """
    )
    kvarMaxAbs: float | None = Field(
        description="""
        Indicates the maximum reactive power ABSORPTION (un-signed numerical variable in kvar) for the inverter. Defaults to kvarMax.

        DSS property name: `kvarMaxAbs`, DSS property index: 14.
        """
    )
    WattPriority: bool | None = Field(
        description="""
        {Yes/No*/True/False} Set inverter to watt priority instead of the default var priority.

        DSS property name: `WattPriority`, DSS property index: 15.
        """
    )
    PFPriority: bool | None = Field(
        description="""
        If set to true, priority is given to power factor and WattPriority is neglected. It works only if operating in either constant PF or constant kvar modes. Defaults to False.

        DSS property name: `PFPriority`, DSS property index: 16.
        """
    )
    pctPminNoVars: float | None = Field(
        alias="%pminnovars",
        description="""
        Minimum active power as percentage of kWrated under which there is no vars production/absorption. Defaults to 0 (disabled).

        DSS property name: `%PminNoVars`, DSS property index: 17.
        """,
    )
    pctPminkvarMax: float | None = Field(
        alias="%pminkvarmax",
        description="""
        Minimum active power as percentage of kWrated that allows the inverter to produce/absorb reactive power up to its maximum reactive power, which can be either kvarMax or kvarMaxAbs, depending on the current operation quadrant. Defaults to 0 (disabled).

        DSS property name: `%PminkvarMax`, DSS property index: 18.
        """,
    )
    kWrated: float | None = Field(
        description="""
        kW rating of power output. Base for Loadshapes when DispMode=Follow. Sets kVA property if it has not been specified yet. Defaults to 25.

        DSS property name: `kWrated`, DSS property index: 19.
        """
    )
    pctkWrated: float | None = Field(
        alias="%kwrated",
        description="""
        Upper limit on active power as a percentage of kWrated. Defaults to 100 (disabled).

        DSS property name: `%kWrated`, DSS property index: 20.
        """,
    )
    kWhrated: float | None = Field(
        description="""
        Rated Storage capacity in kWh. Default is 50.

        DSS property name: `kWhrated`, DSS property index: 21.
        """
    )
    kWhstored: float | None = Field(
        description="""
        Present amount of energy stored, kWh. Default is same as kWhrated.

        DSS property name: `kWhstored`, DSS property index: 22.
        """
    )
    pctstored: float | None = Field(
        alias="%stored",
        description="""
        Present amount of energy stored, % of rated kWh. Default is 100.

        DSS property name: `%stored`, DSS property index: 23.
        """,
    )
    pctreserve: float | None = Field(
        alias="%reserve",
        description="""
        Percentage of rated kWh Storage capacity to be held in reserve for normal operation. Default = 20.
        This is treated as the minimum energy discharge level unless there is an emergency. For emergency operation set this property lower. Cannot be less than zero.

        DSS property name: `%reserve`, DSS property index: 24.
        """,
    )
    State: str | None = Field(
        description="""
        {IDLING | CHARGING | DISCHARGING}  Get/Set present operational state. In DISCHARGING mode, the Storage element acts as a generator and the kW property is positive. The element continues discharging at the scheduled output power level until the Storage reaches the reserve value. Then the state reverts to IDLING. In the CHARGING state, the Storage element behaves like a Load and the kW property is negative. The element continues to charge until the max Storage kWh is reached and then switches to IDLING state. In IDLING state, the element draws the idling losses plus the associated inverter losses.

        DSS property name: `State`, DSS property index: 25.
        """
    )
    pctDischarge: float | None = Field(
        alias="%discharge",
        description="""
        Discharge rate (output power) in percentage of rated kW. Default = 100.

        DSS property name: `%Discharge`, DSS property index: 26.
        """,
    )
    pctCharge: float | None = Field(
        alias="%charge",
        description="""
        Charging rate (input power) in percentage of rated kW. Default = 100.

        DSS property name: `%Charge`, DSS property index: 27.
        """,
    )
    pctEffCharge: float | None = Field(
        alias="%effcharge",
        description="""
        Percentage efficiency for CHARGING the Storage element. Default = 90.

        DSS property name: `%EffCharge`, DSS property index: 28.
        """,
    )
    pctEffDischarge: float | None = Field(
        alias="%effdischarge",
        description="""
        Percentage efficiency for DISCHARGING the Storage element. Default = 90.

        DSS property name: `%EffDischarge`, DSS property index: 29.
        """,
    )
    pctIdlingkW: float | None = Field(
        alias="%idlingkw",
        description="""
        Percentage of rated kW consumed by idling losses. Default = 1.

        DSS property name: `%IdlingkW`, DSS property index: 30.
        """,
    )
    pctR: float | None = Field(
        alias="%r",
        description="""
        Equivalent percentage internal resistance, ohms. Default is 0. Placed in series with internal voltage source for harmonics and dynamics modes. Use a combination of %IdlingkW, %EffCharge and %EffDischarge to account for losses in power flow modes.

        DSS property name: `%R`, DSS property index: 32.
        """,
    )
    pctX: float | None = Field(
        alias="%x",
        description="""
        Equivalent percentage internal reactance, ohms. Default is 50%. Placed in series with internal voltage source for harmonics and dynamics modes. (Limits fault current to 2 pu.

        DSS property name: `%X`, DSS property index: 33.
        """,
    )
    model: int | None = Field(
        description="""
        Integer code (default=1) for the model to be used for power output variation with voltage. Valid values are:

        1:Storage element injects/absorbs a CONSTANT power.
        2:Storage element is modeled as a CONSTANT IMPEDANCE.
        3:Compute load injection from User-written Model.

        DSS property name: `model`, DSS property index: 34.
        """
    )
    Vminpu: float | None = Field(
        description="""
        Default = 0.90.  Minimum per unit voltage for which the Model is assumed to apply. Below this value, the load model reverts to a constant impedance model.

        DSS property name: `Vminpu`, DSS property index: 35.
        """
    )
    Vmaxpu: float | None = Field(
        description="""
        Default = 1.10.  Maximum per unit voltage for which the Model is assumed to apply. Above this value, the load model reverts to a constant impedance model.

        DSS property name: `Vmaxpu`, DSS property index: 36.
        """
    )
    Balanced: bool | None = Field(
        description="""
        {Yes | No*} Default is No. Force balanced current only for 3-phase Storage. Forces zero- and negative-sequence to zero.

        DSS property name: `Balanced`, DSS property index: 37.
        """
    )
    LimitCurrent: bool | None = Field(
        description="""
        Limits current magnitude to Vminpu value for both 1-phase and 3-phase Storage similar to Generator Model 7. For 3-phase, limits the positive-sequence current but not the negative-sequence.

        DSS property name: `LimitCurrent`, DSS property index: 38.
        """
    )
    yearly: str | None = Field(
        description="""
        Dispatch shape to use for yearly simulations.  Must be previously defined as a Loadshape object. If this is not specified, the Daily dispatch shape, if any, is repeated during Yearly solution modes. In the default dispatch mode, the Storage element uses this loadshape to trigger State changes.

        DSS property name: `yearly`, DSS property index: 39.
        """
    )
    daily: str | None = Field(
        description="""
        Dispatch shape to use for daily simulations.  Must be previously defined as a Loadshape object of 24 hrs, typically.  In the default dispatch mode, the Storage element uses this loadshape to trigger State changes.

        DSS property name: `daily`, DSS property index: 40.
        """
    )
    duty: str | None = Field(
        description="""
        Load shape to use for duty cycle dispatch simulations such as for solar ramp rate studies. Must be previously defined as a Loadshape object.

        Typically would have time intervals of 1-5 seconds.

        Designate the number of points to solve using the Set Number=xxxx command. If there are fewer points in the actual shape, the shape is assumed to repeat.

        DSS property name: `duty`, DSS property index: 41.
        """
    )
    DispMode: str | None = Field(
        description="""
        {DEFAULT | FOLLOW | EXTERNAL | LOADLEVEL | PRICE } Default = "DEFAULT". Dispatch mode.

        In DEFAULT mode, Storage element state is triggered to discharge or charge at the specified rate by the loadshape curve corresponding to the solution mode.

        In FOLLOW mode the kW output of the Storage element follows the active loadshape multiplier until Storage is either exhausted or full. The element discharges for positive values and charges for negative values.  The loadshape is based on rated kW.

        In EXTERNAL mode, Storage element state is controlled by an external Storagecontroller. This mode is automatically set if this Storage element is included in the element list of a StorageController element.

        For the other two dispatch modes, the Storage element state is controlled by either the global default Loadlevel value or the price level.

        DSS property name: `DispMode`, DSS property index: 42.
        """
    )
    DischargeTrigger: float | None = Field(
        description="""
        Dispatch trigger value for discharging the Storage.
        If = 0.0 the Storage element state is changed by the State command or by a StorageController object.
        If <> 0  the Storage element state is set to DISCHARGING when this trigger level is EXCEEDED by either the specified Loadshape curve value or the price signal or global Loadlevel value, depending on dispatch mode. See State property.

        DSS property name: `DischargeTrigger`, DSS property index: 43.
        """
    )
    ChargeTrigger: float | None = Field(
        description="""
        Dispatch trigger value for charging the Storage.

        If = 0.0 the Storage element state is changed by the State command or StorageController object.

        If <> 0  the Storage element state is set to CHARGING when this trigger level is GREATER than either the specified Loadshape curve value or the price signal or global Loadlevel value, depending on dispatch mode. See State property.

        DSS property name: `ChargeTrigger`, DSS property index: 44.
        """
    )
    TimeChargeTrig: float | None = Field(
        description="""
        Time of day in fractional hours (0230 = 2.5) at which Storage element will automatically go into charge state. Default is 2.0.  Enter a negative time value to disable this feature.

        DSS property name: `TimeChargeTrig`, DSS property index: 45.
        """
    )
    cls: int | None = Field(
        alias="class",
        description="""
        An arbitrary integer number representing the class of Storage element so that Storage values may be segregated by class.

        DSS property name: `class`, DSS property index: 46.
        """,
    )
    DynaDLL: str | None = Field(
        description="""
        Name of DLL containing user-written dynamics model, which computes the terminal currents for Dynamics-mode simulations, overriding the default model.  Set to "none" to negate previous setting. This DLL has a simpler interface than the UserModel DLL and is only used for Dynamics mode.

        DSS property name: `DynaDLL`, DSS property index: 47.
        """
    )
    DynaData: str | None = Field(
        description="""
        String (in quotes or parentheses if necessary) that gets passed to the user-written dynamics model Edit function for defining the data required for that model.

        DSS property name: `DynaData`, DSS property index: 48.
        """
    )
    UserModel: str | None = Field(
        description="""
        Name of DLL containing user-written model, which computes the terminal currents for both power flow and dynamics, overriding the default model.  Set to "none" to negate previous setting.

        DSS property name: `UserModel`, DSS property index: 49.
        """
    )
    UserData: str | None = Field(
        description="""
        String (in quotes or parentheses) that gets passed to user-written model for defining the data required for that model.

        DSS property name: `UserData`, DSS property index: 50.
        """
    )
    debugtrace: bool | None = Field(
        description="""
        {Yes | No }  Default is no.  Turn this on to capture the progress of the Storage model for each iteration.  Creates a separate file for each Storage element named "Storage_name.csv".

        DSS property name: `debugtrace`, DSS property index: 51.
        """
    )
    kVDC: float | None = Field(
        description="""
        Indicates the rated voltage (kV) at the input of the inverter while the storage is discharging. The value is normally greater or equal to the kV base of the Storage device. It is used for dynamics simulation ONLY.

        DSS property name: `kVDC`, DSS property index: 52.
        """
    )
    Kp: float | None = Field(
        description="""
        It is the proportional gain for the PI controller within the inverter. Use it to modify the controller response in dynamics simulation mode.

        DSS property name: `Kp`, DSS property index: 53.
        """
    )
    PITol: float | None = Field(
        description="""
        It is the tolerance (%) for the closed loop controller of the inverter. For dynamics simulation mode.

        DSS property name: `PITol`, DSS property index: 54.
        """
    )
    SafeVoltage: float | None = Field(
        description="""
        Indicates the voltage level (%) respect to the base voltage level for which the Inverter will operate. If this threshold is violated, the Inverter will enter safe mode (OFF). For dynamic simulation. By default is 80%.

        DSS property name: `SafeVoltage`, DSS property index: 55.
        """
    )
    SafeMode: bool | None = Field(
        description="""
        (Read only) Indicates whether the inverter entered (Yes) or not (No) into Safe Mode.

        DSS property name: `SafeMode`, DSS property index: 56.
        """
    )
    DynamicEq: str | None = Field(
        description="""
        The name of the dynamic equation (DynamicExp) that will be used for defining the dynamic behavior of the generator. If not defined, the generator dynamics will follow the built-in dynamic equation.

        DSS property name: `DynamicEq`, DSS property index: 57.
        """
    )
    DynOut: str | None = Field(
        description="""
        The name of the variables within the Dynamic equation that will be used to govern the Storage dynamics. This Storage model requires 1 output from the dynamic equation:

            1. Current.

        The output variables need to be defined in the same order.

        DSS property name: `DynOut`, DSS property index: 58.
        """
    )
    ControlMode: str | None = Field(
        description="""
        Defines the control mode for the inverter. It can be one of {GFM | GFL*}. By default it is GFL (Grid Following Inverter). Use GFM (Grid Forming Inverter) for energizing islanded microgrids, but, if the device is conencted to the grid, it is highly recommended to use GFL.

        GFM control mode disables any control action set by the InvControl device.

        DSS property name: `ControlMode`, DSS property index: 59.
        """
    )
    spectrum: str | None = Field(
        description="""
        Name of harmonic voltage or current spectrum for this Storage element. Current injection is assumed for inverter. Default value is "default", which is defined when the DSS starts.

        DSS property name: `spectrum`, DSS property index: 60.
        """
    )
    basefreq: float | None = Field(
        description="""
        Base Frequency for ratings.

        DSS property name: `basefreq`, DSS property index: 61.
        """
    )
    enabled: bool | None = Field(
        description="""
        {Yes|No or True|False} Indicates whether this element is enabled.

        DSS property name: `enabled`, DSS property index: 62.
        """
    )

    @root_validator(pre=True)
    def drop_fields(cls, values):
        """Removes undesired fields."""
        return values


class StorageController(OpenDssElementBaseModel):
    """None"""

    Element: str | None = Field(
        description="""
        Full object name of the circuit element, typically a line or transformer, which the control is monitoring. There is no default; Must be specified.

        DSS property name: `Element`, DSS property index: 1.
        """
    )
    Terminal: int | None = Field(
        description="""
        Number of the terminal of the circuit element to which the StorageController control is connected. 1 or 2, typically.  Default is 1. Make sure to select the proper direction on the power for the respective dispatch mode.

        DSS property name: `Terminal`, DSS property index: 2.
        """
    )
    MonPhase: str | None = Field(
        description="""
        Number of the phase being monitored or one of {AVG | MAX | MIN} for all phases. Default=MAX. Must be less than the number of phases. Used in PeakShave, Follow, Support and I-PeakShave discharging modes and in PeakShaveLow, I-PeakShaveLow charging modes. For modes based on active power measurements, the value used by the control is the monitored one multiplied by the number of phases of the monitored element.

        DSS property name: `MonPhase`, DSS property index: 3.
        """
    )
    kWTarget: float | None = Field(
        description="""
        kW/kamps target for Discharging. The Storage element fleet is dispatched to try to hold the power/current in band at least until the Storage is depleted. The selection of power or current depends on the Discharge mode (PeakShave->kW, I-PeakShave->kamps).

        DSS property name: `kWTarget`, DSS property index: 4.
        """
    )
    kWTargetLow: float | None = Field(
        description="""
        kW/kamps target for Charging. The Storage element fleet is dispatched to try to hold the power/current in band at least until the Storage is fully charged. The selection of power or current depends on the charge mode (PeakShavelow->kW, I-PeakShavelow->kamps).

        DSS property name: `kWTargetLow`, DSS property index: 5.
        """
    )
    pctkWBand: float | None = Field(
        alias="%kwband",
        description="""
        Bandwidth (% of Target kW/kamps) of the dead band around the kW/kamps target value. Default is 2% (+/-1%).No dispatch changes are attempted if the power in the monitored terminal stays within this band.

        DSS property name: `%kWBand`, DSS property index: 6.
        """,
    )
    kWBand: float | None = Field(
        description="""
        Alternative way of specifying the bandwidth. (kW/kamps) of the dead band around the kW/kamps target value. Default is 2% of kWTarget (+/-1%).No dispatch changes are attempted if the power in the monitored terminal stays within this band.

        DSS property name: `kWBand`, DSS property index: 7.
        """
    )
    pctkWBandLow: float | None = Field(
        alias="%kwbandlow",
        description="""
        Bandwidth (% of kWTargetLow) of the dead band around the kW/kamps low target value. Default is 2% (+/-1%).No charging is attempted if the power in the monitored terminal stays within this band.

        DSS property name: `%kWBandLow`, DSS property index: 8.
        """,
    )
    kWBandLow: float | None = Field(
        description="""
        Alternative way of specifying the bandwidth. (kW/kamps) of the dead band around the kW/kamps low target value. Default is 2% of kWTargetLow (+/-1%).No charging is attempted if the power in the monitored terminal stays within this band.

        DSS property name: `kWBandLow`, DSS property index: 9.
        """
    )
    ElementList: list | None = Field(
        description="""
        Array list of Storage elements to be controlled.  If not specified, all Storage elements in the circuit not presently dispatched by another controller are assumed dispatched by this controller.

        DSS property name: `ElementList`, DSS property index: 10.
        """
    )
    Weights: list | None = Field(
        description="""
        Array of proportional weights corresponding to each Storage element in the ElementList. The needed kW or kvar to get back to center band is dispatched to each Storage element according to these weights. Default is to set all weights to 1.0.

        DSS property name: `Weights`, DSS property index: 11.
        """
    )
    ModeDischarge: str | None = Field(
        description="""
        {PeakShave* | Follow | Support | Loadshape | Time | Schedule | I-PeakShave} Mode of operation for the DISCHARGE FUNCTION of this controller.

        In PeakShave mode (Default), the control attempts to discharge Storage to keep power in the monitored element below the kWTarget.

        In Follow mode, the control is triggered by time and resets the kWTarget value to the present monitored element power. It then attempts to discharge Storage to keep power in the monitored element below the new kWTarget. See TimeDischargeTrigger.

        In Support mode, the control operates oppositely of PeakShave mode: Storage is discharged to keep kW power output up near the target.

        In Loadshape mode, both charging and discharging precisely follows the per unit loadshape. Storage is discharged when the loadshape value is positive.

        In Time mode, the Storage discharge is turned on at the specified %RatekW at the specified discharge trigger time in fractional hours.

        In Schedule mode, the Tup, TFlat, and Tdn properties specify the up ramp duration, flat duration, and down ramp duration for the schedule. The schedule start time is set by TimeDischargeTrigger and the rate of discharge for the flat part is determined by %RatekW.

        In I-PeakShave mode, the control attempts to discharge Storage to keep current in the monitored element below the target given in k-amps (thousands of amps), when this control mode is active, the property kWTarget will be expressed in k-amps.

        DSS property name: `ModeDischarge`, DSS property index: 12.
        """
    )
    ModeCharge: str | None = Field(
        description="""
        {Loadshape | Time* | PeakShaveLow | I-PeakShaveLow} Mode of operation for the CHARGE FUNCTION of this controller.

        In Loadshape mode, both charging and discharging precisely follows the per unit loadshape. Storage is charged when the loadshape value is negative.

        In Time mode, the Storage charging FUNCTION is triggered at the specified %RateCharge at the specified charge trigger time in fractional hours.

        In PeakShaveLow mode, the charging operation will charge the Storage fleet when the power at amonitored element is below a specified KW target (kWTarget_low). The Storage will charge as much power as necessary to keep the power within the deadband around kWTarget_low.

        In I-PeakShaveLow mode, the charging operation will charge the Storage fleet when the current (Amps) at amonitored element is below a specified amps target (kWTarget_low). The Storage will charge as much power as necessary to keep the amps within the deadband around kWTarget_low. When this control mode is active, the property kWTarget_low will be expressed in k-amps and all the other parameters will be adjusted to match the amps (current) control criteria.

        DSS property name: `ModeCharge`, DSS property index: 13.
        """
    )
    TimeDischargeTrigger: float | None = Field(
        description="""
        Default time of day (hr) for initiating Discharging of the fleet. During Follow or Time mode discharging is triggered at a fixed time each day at this hour. If Follow mode, Storage will be discharged to attempt to hold the load at or below the power level at the time of triggering. In Time mode, the discharge is based on the %RatekW property value. Set this to a negative value to ignore. Default is 12.0 for Follow mode; otherwise it is -1 (ignored).

        DSS property name: `TimeDischargeTrigger`, DSS property index: 14.
        """
    )
    TimeChargeTrigger: float | None = Field(
        description="""
        Default time of day (hr) for initiating charging in Time control mode. Set this to a negative value to ignore. Default is 2.0.  (0200).When this value is >0 the Storage fleet is set to charging at this time regardless of other control criteria to make sure Storage is topped off for the next discharge cycle.

        DSS property name: `TimeChargeTrigger`, DSS property index: 15.
        """
    )
    pctRatekW: float | None = Field(
        alias="%ratekw",
        description="""
        Sets the kW discharge rate in % of rated capacity for each element of the fleet. Applies to TIME control mode, SCHEDULE mode, or anytime discharging is triggered by time.

        DSS property name: `%RatekW`, DSS property index: 16.
        """,
    )
    pctRateCharge: float | None = Field(
        alias="%ratecharge",
        description="""
        Sets the kW charging rate in % of rated capacity for each element of the fleet. Applies to TIME control mode and anytime charging mode is entered due to a time trigger.

        DSS property name: `%RateCharge`, DSS property index: 17.
        """,
    )
    pctReserve: float | None = Field(
        alias="%reserve",
        description="""
        Use this property to change the % reserve for each Storage element under control of this controller. This might be used, for example, to allow deeper discharges of Storage or in case of emergency operation to use the remainder of the Storage element.

        DSS property name: `%Reserve`, DSS property index: 18.
        """,
    )
    kWhTotal: float | None = Field(
        description="""
        (Read only). Total rated kWh energy Storage capacity of Storage elements controlled by this controller.

        DSS property name: `kWhTotal`, DSS property index: 19.
        """
    )
    kWTotal: float | None = Field(
        description="""
        (Read only). Total rated kW power capacity of Storage elements controlled by this controller.

        DSS property name: `kWTotal`, DSS property index: 20.
        """
    )
    kWhActual: float | None = Field(
        description="""
        (Read only). Actual kWh stored of all controlled Storage elements.

        DSS property name: `kWhActual`, DSS property index: 21.
        """
    )
    kWActual: float | None = Field(
        description="""
        (Read only). Actual kW output of all controlled Storage elements.

        DSS property name: `kWActual`, DSS property index: 22.
        """
    )
    kWneed: float | None = Field(
        description="""
        (Read only). KW needed to meet target.

        DSS property name: `kWneed`, DSS property index: 23.
        """
    )
    Yearly: str | None = Field(
        description="""
        Dispatch loadshape object, If any, for Yearly solution Mode.

        DSS property name: `Yearly`, DSS property index: 24.
        """
    )
    Daily: str | None = Field(
        description="""
        Dispatch loadshape object, If any, for Daily solution mode.

        DSS property name: `Daily`, DSS property index: 25.
        """
    )
    Duty: str | None = Field(
        description="""
        Dispatch loadshape object, If any, for Dutycycle solution mode.

        DSS property name: `Duty`, DSS property index: 26.
        """
    )
    EventLog: bool | None = Field(
        description="""
        {Yes/True | No/False} Default is No. Log control actions to Eventlog.

        DSS property name: `EventLog`, DSS property index: 27.
        """
    )
    InhibitTime: int | None = Field(
        description="""
        Hours (integer) to inhibit Discharging after going into Charge mode. Default is 5.

        DSS property name: `InhibitTime`, DSS property index: 28.
        """
    )
    Tup: float | None = Field(
        description="""
        Duration, hrs, of upramp part for SCHEDULE mode. Default is 0.25.

        DSS property name: `Tup`, DSS property index: 29.
        """
    )
    TFlat: float | None = Field(
        description="""
        Duration, hrs, of flat part for SCHEDULE mode. Default is 2.0.

        DSS property name: `TFlat`, DSS property index: 30.
        """
    )
    Tdn: float | None = Field(
        description="""
        Duration, hrs, of downramp part for SCHEDULE mode. Default is 0.25.

        DSS property name: `Tdn`, DSS property index: 31.
        """
    )
    kWThreshold: float | None = Field(
        description="""
        Threshold, kW, for Follow mode. kW has to be above this value for the Storage element to be dispatched on. Defaults to 75% of the kWTarget value. Must reset this property after setting kWTarget if you want a different value.

        DSS property name: `kWThreshold`, DSS property index: 32.
        """
    )
    DispFactor: float | None = Field(
        description="""
        Defaults to 1 (disabled). Set to any value between 0 and 1 to enable this parameter.

        Use this parameter to reduce the amount of power requested by the controller in each control iteration. It can be useful when maximum control iterations are exceeded due to numerical instability such as fleet being set to charging and idling in subsequent control iterations (check the Eventlog).

        DSS property name: `DispFactor`, DSS property index: 33.
        """
    )
    ResetLevel: float | None = Field(
        description="""
        The level of charge required for allowing the storage to discharge again after reaching the reserve storage level. After reaching this level, the storage control  will not allow the storage device to discharge, forcing the storage to charge. Once the storage reaches thislevel, the storage will be able to discharge again. This value is a number between 0.2 and 1

        DSS property name: `ResetLevel`, DSS property index: 34.
        """
    )
    Seasons: int | None = Field(
        description="""
        With this property the user can specify the number of targets to be used by the controller using the list given at "SeasonTargets"/"SeasonTargetsLow", which can be used to dynamically adjust the storage controller during a QSTS simulation. The default value is 1. This property needs to be defined before defining SeasonTargets/SeasonTargetsLow.

        DSS property name: `Seasons`, DSS property index: 35.
        """
    )
    SeasonTargets: list | None = Field(
        description="""
        An array of doubles specifying the targets to be used during a QSTS simulation. These targets will take effect only if SeasonRating=true. The number of targets cannot exceed the number of seasons defined at the SeasonSignal.The difference between the targets defined at SeasonTargets and SeasonTargetsLow is that SeasonTargets applies to discharging modes, while SeasonTargetsLow applies to charging modes.

        DSS property name: `SeasonTargets`, DSS property index: 36.
        """
    )
    SeasonTargetsLow: list | None = Field(
        description="""
        An array of doubles specifying the targets to be used during a QSTS simulation. These targets will take effect only if SeasonRating=true. The number of targets cannot exceed the number of seasons defined at the SeasonSignal.The difference between the targets defined at SeasonTargets and SeasonTargetsLow is that SeasonTargets applies to discharging modes, while SeasonTargetsLow applies to charging modes.

        DSS property name: `SeasonTargetsLow`, DSS property index: 37.
        """
    )
    basefreq: float | None = Field(
        description="""
        Base Frequency for ratings.

        DSS property name: `basefreq`, DSS property index: 38.
        """
    )
    enabled: bool | None = Field(
        description="""
        {Yes|No or True|False} Indicates whether this element is enabled.

        DSS property name: `enabled`, DSS property index: 39.
        """
    )

    @root_validator(pre=True)
    def drop_fields(cls, values):
        """Removes undesired fields."""
        return values


class Relay(OpenDssElementBaseModel):
    """None"""

    MonitoredObj: str | None = Field(
        description="""
        Full object name of the circuit element, typically a line, transformer, load, or generator, to which the relay's PT and/or CT are connected. This is the "monitored" element. There is no default; must be specified.

        DSS property name: `MonitoredObj`, DSS property index: 1.
        """
    )
    MonitoredTerm: int | None = Field(
        description="""
        Number of the terminal of the circuit element to which the Relay is connected. 1 or 2, typically.  Default is 1.

        DSS property name: `MonitoredTerm`, DSS property index: 2.
        """
    )
    SwitchedObj: str | None = Field(
        description="""
        Name of circuit element switch that the Relay controls. Specify the full object name.Defaults to the same as the Monitored element. This is the "controlled" element.

        DSS property name: `SwitchedObj`, DSS property index: 3.
        """
    )
    SwitchedTerm: int | None = Field(
        description="""
        Number of the terminal of the controlled element in which the switch is controlled by the Relay. 1 or 2, typically.  Default is 1.

        DSS property name: `SwitchedTerm`, DSS property index: 4.
        """
    )
    type: str | None = Field(
        description="""
        One of a legal relay type:
          Current
          Voltage
          Reversepower
          46 (neg seq current)
          47 (neg seq voltage)
          Generic (generic over/under relay)
          Distance
          TD21
          DOC (directional overcurrent)

        Default is overcurrent relay (Current) Specify the curve and pickup settings appropriate for each type. Generic relays monitor PC Element Control variables and trip on out of over/under range in definite time.

        DSS property name: `type`, DSS property index: 5.
        """
    )
    Phasecurve: str | None = Field(
        description="""
        Name of the TCC Curve object that determines the phase trip.  Must have been previously defined as a TCC_Curve object. Default is none (ignored). For overcurrent relay, multiplying the current values in the curve by the "phasetrip" value gives the actual current.

        DSS property name: `Phasecurve`, DSS property index: 6.
        """
    )
    Groundcurve: str | None = Field(
        description="""
        Name of the TCC Curve object that determines the ground trip.  Must have been previously defined as a TCC_Curve object. Default is none (ignored).For overcurrent relay, multiplying the current values in the curve by the "groundtrip" valuw gives the actual current.

        DSS property name: `Groundcurve`, DSS property index: 7.
        """
    )
    PhaseTrip: float | None = Field(
        description="""
        Multiplier or actual phase amps for the phase TCC curve.  Defaults to 1.0.

        DSS property name: `PhaseTrip`, DSS property index: 8.
        """
    )
    GroundTrip: float | None = Field(
        description="""
        Multiplier or actual ground amps (3I0) for the ground TCC curve.  Defaults to 1.0.

        DSS property name: `GroundTrip`, DSS property index: 9.
        """
    )
    TDPhase: float | None = Field(
        description="""
        Time dial for Phase trip curve. Multiplier on time axis of specified curve. Default=1.0.

        DSS property name: `TDPhase`, DSS property index: 10.
        """
    )
    TDGround: float | None = Field(
        description="""
        Time dial for Ground trip curve. Multiplier on time axis of specified curve. Default=1.0.

        DSS property name: `TDGround`, DSS property index: 11.
        """
    )
    PhaseInst: float | None = Field(
        description="""
        Actual  amps (Current relay) or kW (reverse power relay) for instantaneous phase trip which is assumed to happen in 0.01 sec + Delay Time. Default is 0.0, which signifies no inst trip. Use this value for specifying the Reverse Power threshold (kW) for reverse power relays.

        DSS property name: `PhaseInst`, DSS property index: 12.
        """
    )
    GroundInst: float | None = Field(
        description="""
        Actual  amps for instantaneous ground trip which is assumed to happen in 0.01 sec + Delay Time.Default is 0.0, which signifies no inst trip.

        DSS property name: `GroundInst`, DSS property index: 13.
        """
    )
    Reset: float | None = Field(
        description="""
        Reset time in sec for relay.  Default is 15. If this much time passes between the last pickup event, and the relay has not locked out, the operation counter resets.

        DSS property name: `Reset`, DSS property index: 14.
        """
    )
    Shots: int | None = Field(
        description="""
        Number of shots to lockout.  Default is 4. This is one more than the number of reclose intervals.

        DSS property name: `Shots`, DSS property index: 15.
        """
    )
    RecloseIntervals: list | None = Field(
        description="""
        Array of reclose intervals. If none, specify "NONE". Default for overcurrent relay is (0.5, 2.0, 2.0) seconds. Default for a voltage relay is (5.0). In a voltage relay, this is  seconds after restoration of voltage that the reclose occurs. Reverse power relay is one shot to lockout, so this is ignored.  A locked out relay must be closed manually (set action=close).

        DSS property name: `RecloseIntervals`, DSS property index: 16.
        """
    )
    Delay: float | None = Field(
        description="""
        Trip time delay (sec) for DEFINITE TIME relays. Default is 0.0 for current, voltage and DOC relays. If >0 then this value is used instead of curves. Used by Generic, RevPower, 46 and 47 relays. Defaults to 0.1 s for these relays.

        DSS property name: `Delay`, DSS property index: 17.
        """
    )
    Overvoltcurve: str | None = Field(
        description="""
        TCC Curve object to use for overvoltage relay.  Curve is assumed to be defined with per unit voltage values. Voltage base should be defined for the relay. Default is none (ignored).

        DSS property name: `Overvoltcurve`, DSS property index: 18.
        """
    )
    Undervoltcurve: str | None = Field(
        description="""
        TCC Curve object to use for undervoltage relay.  Curve is assumed to be defined with per unit voltage values. Voltage base should be defined for the relay. Default is none (ignored).

        DSS property name: `Undervoltcurve`, DSS property index: 19.
        """
    )
    kvbase: float | None = Field(
        description="""
        Voltage base (kV) for the relay. Specify line-line for 3 phase devices); line-neutral for 1-phase devices.  Relay assumes the number of phases of the monitored element.  Default is 0.0, which results in assuming the voltage values in the "TCC" curve are specified in actual line-to-neutral volts.

        DSS property name: `kvbase`, DSS property index: 20.
        """
    )
    pctPickup47: float | None = Field(
        alias="47%pickup",
        description="""
        Percent voltage pickup for 47 relay (Neg seq voltage). Default is 2. Specify also base voltage (kvbase) and delay time value.

        DSS property name: `47%Pickup`, DSS property index: 21.
        """,
    )
    BaseAmps46: float | None = Field(
        alias="46baseamps",
        description="""
        Base current, Amps, for 46 relay (neg seq current).  Used for establishing pickup and per unit I-squared-t.

        DSS property name: `46BaseAmps`, DSS property index: 22.
        """,
    )
    pctPickup46: float | None = Field(
        alias="46%pickup",
        description="""
        Percent pickup current for 46 relay (neg seq current).  Default is 20.0.   When current exceeds this value * BaseAmps, I-squared-t calc starts.

        DSS property name: `46%Pickup`, DSS property index: 23.
        """,
    )
    isqt46: float | None = Field(
        alias="46isqt",
        description="""
        Negative Sequence I-squared-t trip value for 46 relay (neg seq current).  Default is 1 (trips in 1 sec for 1 per unit neg seq current).  Should be 1 to 99.

        DSS property name: `46isqt`, DSS property index: 24.
        """,
    )
    Variable: str | None = Field(
        description="""
        Name of variable in PC Elements being monitored.  Only applies to Generic relay.

        DSS property name: `Variable`, DSS property index: 25.
        """
    )
    overtrip: float | None = Field(
        description="""
        Trip setting (high value) for Generic relay variable.  Relay trips in definite time if value of variable exceeds this value.

        DSS property name: `overtrip`, DSS property index: 26.
        """
    )
    undertrip: float | None = Field(
        description="""
        Trip setting (low value) for Generic relay variable.  Relay trips in definite time if value of variable is less than this value.

        DSS property name: `undertrip`, DSS property index: 27.
        """
    )
    Breakertime: float | None = Field(
        description="""
        Fixed delay time (sec) added to relay time. Default is 0.0. Designed to represent breaker time or some other delay after a trip decision is made.Use Delay property for setting a fixed trip time delay.Added to trip time of current and voltage relays. Could use in combination with inst trip value to obtain a definite time overcurrent relay.

        DSS property name: `Breakertime`, DSS property index: 28.
        """
    )
    action: str | None = Field(
        description="""
        DEPRECATED. See "State" property

        DSS property name: `action`, DSS property index: 29.
        """
    )
    Z1mag: float | None = Field(
        description="""
        Positive sequence reach impedance in primary ohms for Distance and TD21 functions. Default=0.7

        DSS property name: `Z1mag`, DSS property index: 30.
        """
    )
    Z1ang: float | None = Field(
        description="""
        Positive sequence reach impedance angle in degrees for Distance and TD21 functions. Default=64.0

        DSS property name: `Z1ang`, DSS property index: 31.
        """
    )
    Z0mag: float | None = Field(
        description="""
        Zero sequence reach impedance in primary ohms for Distance and TD21 functions. Default=2.1

        DSS property name: `Z0mag`, DSS property index: 32.
        """
    )
    Z0ang: float | None = Field(
        description="""
        Zero sequence reach impedance angle in degrees for Distance and TD21 functions. Default=68.0

        DSS property name: `Z0ang`, DSS property index: 33.
        """
    )
    Mphase: float | None = Field(
        description="""
        Phase reach multiplier in per-unit for Distance and TD21 functions. Default=0.7

        DSS property name: `Mphase`, DSS property index: 34.
        """
    )
    Mground: float | None = Field(
        description="""
        Ground reach multiplier in per-unit for Distance and TD21 functions. Default=0.7

        DSS property name: `Mground`, DSS property index: 35.
        """
    )
    EventLog: bool | None = Field(
        description="""
        {Yes/True* | No/False} Default is Yes for Relay. Write trips, reclose and reset events to EventLog.

        DSS property name: `EventLog`, DSS property index: 36.
        """
    )
    DebugTrace: bool | None = Field(
        description="""
        {Yes/True* | No/False} Default is No for Relay. Write extra details to Eventlog.

        DSS property name: `DebugTrace`, DSS property index: 37.
        """
    )
    DistReverse: bool | None = Field(
        description="""
        {Yes/True* | No/False} Default is No; reverse direction for distance and td21 types.

        DSS property name: `DistReverse`, DSS property index: 38.
        """
    )
    Normal: str | None = Field(
        description="""
        {Open | Closed} Normal state of the relay. The relay reverts to this state for reset, change of mode, etc. Defaults to "State" if not specifically declared.

        DSS property name: `Normal`, DSS property index: 39.
        """
    )
    State: str | None = Field(
        description="""
        {Open | Closed} Actual state of the relay. Upon setting, immediately forces state of the relay, overriding the Relay control. Simulates manual control on relay. Defaults to Closed. "Open" causes the controlled element to open and lock out. "Closed" causes the controlled element to close and the relay to reset to its first operation.

        DSS property name: `State`, DSS property index: 40.
        """
    )
    DOC_TiltAngleLow: float | None = Field(
        description="""
        Tilt angle for low-current trip line. Default is 90.

        DSS property name: `DOC_TiltAngleLow`, DSS property index: 41.
        """
    )
    DOC_TiltAngleHigh: float | None = Field(
        description="""
        Tilt angle for high-current trip line. Default is 90.

        DSS property name: `DOC_TiltAngleHigh`, DSS property index: 42.
        """
    )
    DOC_TripSettingLow: float | None = Field(
        description="""
        Resistive trip setting for low-current line. Default is 0.

        DSS property name: `DOC_TripSettingLow`, DSS property index: 43.
        """
    )
    DOC_TripSettingHigh: float | None = Field(
        description="""
        Resistive trip setting for high-current line.  Default is -1 (deactivated). To activate, set a positive value. Must be greater than "DOC_TripSettingLow".

        DSS property name: `DOC_TripSettingHigh`, DSS property index: 44.
        """
    )
    DOC_TripSettingMag: float | None = Field(
        description="""
        Trip setting for current magnitude (defines a circle in the relay characteristics). Default is -1 (deactivated). To activate, set a positive value.

        DSS property name: `DOC_TripSettingMag`, DSS property index: 45.
        """
    )
    DOC_DelayInner: float | None = Field(
        description="""
        Trip time delay (sec) for operation in inner region for DOC relay, defined when "DOC_TripSettingMag" or "DOC_TripSettingHigh" are activate. Default is -1.0 (deactivated), meaning that the relay characteristic is insensitive in the inner region (no trip). Set to 0 for instantaneous trip and >0 for a definite time delay. If "DOC_PhaseCurveInner" is specified, time delay from curve is utilized instead.

        DSS property name: `DOC_DelayInner`, DSS property index: 46.
        """
    )
    DOC_PhaseCurveInner: float | None = Field(
        description="""
        Name of the TCC Curve object that determines the phase trip for operation in inner region for DOC relay. Must have been previously defined as a TCC_Curve object. Default is none (ignored). Multiplying the current values in the curve by the "DOC_PhaseTripInner" value gives the actual current.

        DSS property name: `DOC_PhaseCurveInner`, DSS property index: 47.
        """
    )
    DOC_PhaseTripInner: float | None = Field(
        description="""
        Multiplier for the "DOC_PhaseCurveInner" TCC curve.  Defaults to 1.0.

        DSS property name: `DOC_PhaseTripInner`, DSS property index: 48.
        """
    )
    DOC_TDPhaseInner: str | None = Field(
        description="""
        Time dial for "DOC_PhaseCurveInner" TCC curve. Multiplier on time axis of specified curve. Default=1.0.

        DSS property name: `DOC_TDPhaseInner`, DSS property index: 49.
        """
    )
    DOC_P1Blocking: bool | None = Field(
        description="""
        {Yes/True* | No/False} Blocking element that impedes relay from tripping if balanced net three-phase active power is in the forward direction (i.e., flowing into the monitored terminal). For a delayed trip, if at any given time the reverse power flow condition stops, the tripping is reset. Default=True.

        DSS property name: `DOC_P1Blocking`, DSS property index: 50.
        """
    )
    basefreq: float | None = Field(
        description="""
        Base Frequency for ratings.

        DSS property name: `basefreq`, DSS property index: 51.
        """
    )
    enabled: bool | None = Field(
        description="""
        {Yes|No or True|False} Indicates whether this element is enabled.

        DSS property name: `enabled`, DSS property index: 52.
        """
    )

    @root_validator(pre=True)
    def drop_fields(cls, values):
        """Removes undesired fields."""
        return values


class Recloser(OpenDssElementBaseModel):
    """None"""

    MonitoredObj: str | None = Field(
        description="""
        Full object name of the circuit element, typically a line, transformer, load, or generator, to which the Recloser's PT and/or CT are connected. This is the "monitored" element. There is no default; must be specified.

        DSS property name: `MonitoredObj`, DSS property index: 1.
        """
    )
    MonitoredTerm: int | None = Field(
        description="""
        Number of the terminal of the circuit element to which the Recloser is connected. 1 or 2, typically.  Default is 1.

        DSS property name: `MonitoredTerm`, DSS property index: 2.
        """
    )
    SwitchedObj: str | None = Field(
        description="""
        Name of circuit element switch that the Recloser controls. Specify the full object name.Defaults to the same as the Monitored element. This is the "controlled" element.

        DSS property name: `SwitchedObj`, DSS property index: 3.
        """
    )
    SwitchedTerm: int | None = Field(
        description="""
        Number of the terminal of the controlled element in which the switch is controlled by the Recloser. 1 or 2, typically.  Default is 1.

        DSS property name: `SwitchedTerm`, DSS property index: 4.
        """
    )
    NumFast: int | None = Field(
        description="""
        Number of Fast (fuse saving) operations.  Default is 1. (See "Shots")

        DSS property name: `NumFast`, DSS property index: 5.
        """
    )
    PhaseFast: str | None = Field(
        description="""
        Name of the TCC Curve object that determines the Phase Fast trip.  Must have been previously defined as a TCC_Curve object. Default is "A". Multiplying the current values in the curve by the "phasetrip" value gives the actual current.

        DSS property name: `PhaseFast`, DSS property index: 6.
        """
    )
    PhaseDelayed: str | None = Field(
        description="""
        Name of the TCC Curve object that determines the Phase Delayed trip.  Must have been previously defined as a TCC_Curve object. Default is "D".Multiplying the current values in the curve by the "phasetrip" value gives the actual current.

        DSS property name: `PhaseDelayed`, DSS property index: 7.
        """
    )
    GroundFast: str | None = Field(
        description="""
        Name of the TCC Curve object that determines the Ground Fast trip.  Must have been previously defined as a TCC_Curve object. Default is none (ignored). Multiplying the current values in the curve by the "groundtrip" value gives the actual current.

        DSS property name: `GroundFast`, DSS property index: 8.
        """
    )
    GroundDelayed: str | None = Field(
        description="""
        Name of the TCC Curve object that determines the Ground Delayed trip.  Must have been previously defined as a TCC_Curve object. Default is none (ignored).Multiplying the current values in the curve by the "groundtrip" value gives the actual current.

        DSS property name: `GroundDelayed`, DSS property index: 9.
        """
    )
    PhaseTrip: float | None = Field(
        description="""
        Multiplier or actual phase amps for the phase TCC curve.  Defaults to 1.0.

        DSS property name: `PhaseTrip`, DSS property index: 10.
        """
    )
    GroundTrip: float | None = Field(
        description="""
        Multiplier or actual ground amps (3I0) for the ground TCC curve.  Defaults to 1.0.

        DSS property name: `GroundTrip`, DSS property index: 11.
        """
    )
    PhaseInst: float | None = Field(
        description="""
        Actual amps for instantaneous phase trip which is assumed to happen in 0.01 sec + Delay Time. Default is 0.0, which signifies no inst trip.

        DSS property name: `PhaseInst`, DSS property index: 12.
        """
    )
    GroundInst: float | None = Field(
        description="""
        Actual amps for instantaneous ground trip which is assumed to happen in 0.01 sec + Delay Time.Default is 0.0, which signifies no inst trip.

        DSS property name: `GroundInst`, DSS property index: 13.
        """
    )
    Reset: float | None = Field(
        description="""
        Reset time in sec for Recloser.  Default is 15.

        DSS property name: `Reset`, DSS property index: 14.
        """
    )
    Shots: int | None = Field(
        description="""
        Total Number of fast and delayed shots to lockout.  Default is 4. This is one more than the number of reclose intervals.

        DSS property name: `Shots`, DSS property index: 15.
        """
    )
    RecloseIntervals: list | None = Field(
        description="""
        Array of reclose intervals.  Default for Recloser is (0.5, 2.0, 2.0) seconds. A locked out Recloser must be closed manually (action=close).

        DSS property name: `RecloseIntervals`, DSS property index: 16.
        """
    )
    Delay: float | None = Field(
        description="""
        Fixed delay time (sec) added to Recloser trip time. Default is 0.0. Used to represent breaker time or any other delay.

        DSS property name: `Delay`, DSS property index: 17.
        """
    )
    TDPhFast: float | None = Field(
        description="""
        Time dial for Phase Fast trip curve. Multiplier on time axis of specified curve. Default=1.0.

        DSS property name: `TDPhFast`, DSS property index: 19.
        """
    )
    TDGrFast: float | None = Field(
        description="""
        Time dial for Ground Fast trip curve. Multiplier on time axis of specified curve. Default=1.0.

        DSS property name: `TDGrFast`, DSS property index: 20.
        """
    )
    TDPhDelayed: float | None = Field(
        description="""
        Time dial for Phase Delayed trip curve. Multiplier on time axis of specified curve. Default=1.0.

        DSS property name: `TDPhDelayed`, DSS property index: 21.
        """
    )
    TDGrDelayed: float | None = Field(
        description="""
        Time dial for Ground Delayed trip curve. Multiplier on time axis of specified curve. Default=1.0.

        DSS property name: `TDGrDelayed`, DSS property index: 22.
        """
    )
    Normal: str | None = Field(
        description="""
        {Open | Closed} Normal state of the recloser. The recloser reverts to this state for reset, change of mode, etc. Defaults to "State" if not specificallt declared.

        DSS property name: `Normal`, DSS property index: 23.
        """
    )
    State: str | None = Field(
        description="""
        {Open | Closed} Actual state of the recloser. Upon setting, immediately forces state of the recloser, overriding the Recloser control. Simulates manual control on recloser. Defaults to Closed. "Open" causes the controlled element to open and lock out. "Closed" causes the controlled element to close and the recloser to reset to its first operation.

        DSS property name: `State`, DSS property index: 24.
        """
    )
    basefreq: float | None = Field(
        description="""
        Base Frequency for ratings.

        DSS property name: `basefreq`, DSS property index: 25.
        """
    )
    enabled: bool | None = Field(
        description="""
        {Yes|No or True|False} Indicates whether this element is enabled.

        DSS property name: `enabled`, DSS property index: 26.
        """
    )

    @root_validator(pre=True)
    def drop_fields(cls, values):
        """Removes undesired fields."""
        return values


class Fuse(OpenDssElementBaseModel):
    """None"""

    MonitoredObj: str | None = Field(
        description="""
        Full object name of the circuit element, typically a line, transformer, load, or generator, to which the Fuse is connected. This is the "monitored" element. There is no default; must be specified.

        DSS property name: `MonitoredObj`, DSS property index: 1.
        """
    )
    MonitoredTerm: int | None = Field(
        description="""
        Number of the terminal of the circuit element to which the Fuse is connected. 1 or 2, typically.  Default is 1.

        DSS property name: `MonitoredTerm`, DSS property index: 2.
        """
    )
    SwitchedObj: str | None = Field(
        description="""
        Name of circuit element switch that the Fuse controls. Specify the full object name.Defaults to the same as the Monitored element. This is the "controlled" element.

        DSS property name: `SwitchedObj`, DSS property index: 3.
        """
    )
    SwitchedTerm: int | None = Field(
        description="""
        Number of the terminal of the controlled element in which the switch is controlled by the Fuse. 1 or 2, typically.  Default is 1.  Assumes all phases of the element have a fuse of this type.

        DSS property name: `SwitchedTerm`, DSS property index: 4.
        """
    )
    FuseCurve: str | None = Field(
        description="""
        Name of the TCC Curve object that determines the fuse blowing.  Must have been previously defined as a TCC_Curve object. Default is "Tlink". Multiplying the current values in the curve by the "RatedCurrent" value gives the actual current.

        DSS property name: `FuseCurve`, DSS property index: 5.
        """
    )
    RatedCurrent: float | None = Field(
        description="""
        Multiplier or actual phase amps for the phase TCC curve.  Defaults to 1.0.

        DSS property name: `RatedCurrent`, DSS property index: 6.
        """
    )
    Delay: float | None = Field(
        description="""
        Fixed delay time (sec) added to Fuse blowing time determined from the TCC curve. Default is 0.0. Used to represent fuse clearing time or any other delay.

        DSS property name: `Delay`, DSS property index: 7.
        """
    )
    Normal: list | None = Field(
        description="""
        ARRAY of strings {Open | Closed} representing the Normal state of the fuse in each phase of the controlled element. The fuse reverts to this state for reset, change of mode, etc. Defaults to "State" if not specifically declared.

        DSS property name: `Normal`, DSS property index: 9.
        """
    )
    State: list | None = Field(
        description="""
        ARRAY of strings {Open | Closed} representing the Actual state of the fuse in each phase of the controlled element. Upon setting, immediately forces state of fuse(s). Simulates manual control on Fuse. Defaults to Closed for all phases.

        DSS property name: `State`, DSS property index: 10.
        """
    )
    basefreq: float | None = Field(
        description="""
        Base Frequency for ratings.

        DSS property name: `basefreq`, DSS property index: 11.
        """
    )
    enabled: bool | None = Field(
        description="""
        {Yes|No or True|False} Indicates whether this element is enabled.

        DSS property name: `enabled`, DSS property index: 12.
        """
    )

    @root_validator(pre=True)
    def drop_fields(cls, values):
        """Removes undesired fields."""
        return values


class SwtControl(OpenDssElementBaseModel):
    """None"""

    SwitchedObj: str | None = Field(
        description="""
        Name of circuit element switch that the SwtControl operates. Specify the full object class and name.

        DSS property name: `SwitchedObj`, DSS property index: 1.
        """
    )
    SwitchedTerm: int | None = Field(
        description="""
        Terminal number of the controlled element switch. 1 or 2, typically.  Default is 1.

        DSS property name: `SwitchedTerm`, DSS property index: 2.
        """
    )
    Lock: bool | None = Field(
        description="""
        {Yes | No} Delayed action. Sends CTRL_LOCK or CTRL_UNLOCK message to control queue. After delay time, controlled switch is locked in its present open / close state or unlocked. Switch will not respond to either manual (Action) or automatic (APIs) control or internal OpenDSS Reset when locked.

        DSS property name: `Lock`, DSS property index: 4.
        """
    )
    Delay: float | None = Field(
        description="""
        Operating time delay (sec) of the switch. Defaults to 120.

        DSS property name: `Delay`, DSS property index: 5.
        """
    )
    Normal: str | None = Field(
        description="""
        {Open | Closed] Normal state of the switch. If not Locked, the switch reverts to this state for reset, change of mode, etc. Defaults to first Action or State specified if not specifically declared.

        DSS property name: `Normal`, DSS property index: 6.
        """
    )
    State: str | None = Field(
        description="""
        {Open | Closed] Present state of the switch. Upon setting, immediately forces state of switch.

        DSS property name: `State`, DSS property index: 7.
        """
    )
    basefreq: float | None = Field(
        description="""
        Base Frequency for ratings.

        DSS property name: `basefreq`, DSS property index: 9.
        """
    )
    enabled: bool | None = Field(
        description="""
        {Yes|No or True|False} Indicates whether this element is enabled.

        DSS property name: `enabled`, DSS property index: 10.
        """
    )

    @root_validator(pre=True)
    def drop_fields(cls, values):
        """Removes undesired fields."""
        return values


class PVSystem(OpenDssElementBaseModel):
    """None"""

    phases: int | None = Field(
        description="""
        Number of Phases, this PVSystem element.  Power is evenly divided among phases.

        DSS property name: `phases`, DSS property index: 1.
        """
    )
    bus1: str | None = Field(
        description="""
        Bus to which the PVSystem element is connected.  May include specific node specification.

        DSS property name: `bus1`, DSS property index: 2.
        """
    )
    kv: float | None = Field(
        description="""
        Nominal rated (1.0 per unit) voltage, kV, for PVSystem element. For 2- and 3-phase PVSystem elements, specify phase-phase kV. Otherwise, specify actual kV across each branch of the PVSystem element. If 1-phase wye (star or LN), specify phase-neutral kV. If 1-phase delta or phase-phase connected, specify phase-phase kV.

        DSS property name: `kv`, DSS property index: 3.
        """
    )
    irradiance: float | None = Field(
        description="""
        Get/set the present irradiance value in kW/sq-m. Used as base value for shape multipliers. Generally entered as peak value for the time period of interest and the yearly, daily, and duty load shape objects are defined as per unit multipliers (just like Loads/Generators).

        DSS property name: `irradiance`, DSS property index: 4.
        """
    )
    Pmpp: float | None = Field(
        description="""
        Get/set the rated max power of the PV array for 1.0 kW/sq-m irradiance and a user-selected array temperature. The P-TCurve should be defined relative to the selected array temperature.

        DSS property name: `Pmpp`, DSS property index: 5.
        """
    )
    pctPmpp: float | None = Field(
        alias="%Pmpp",
        description="""
        Upper limit on active power as a percentage of Pmpp.

        DSS property name: `%Pmpp`, DSS property index: 6.
        """,
    )
    Temperature: float | None = Field(
        description="""
        Get/set the present Temperature. Used as fixed value corresponding to PTCurve property. A multiplier is obtained from the Pmpp-Temp curve and applied to the nominal Pmpp from the irradiance to determine the net array output.

        DSS property name: `Temperature`, DSS property index: 7.
        """
    )
    pf: float | None = Field(
        description="""
        Nominally, the power factor for the output power. Default is 1.0. Setting this property will cause the inverter to operate in constant power factor mode.Enter negative when kW and kvar have opposite signs.
        A positive power factor signifies that the PVSystem element produces vars
        as is typical for a generator.

        DSS property name: `pf`, DSS property index: 8.
        """
    )
    conn: str | None = Field(
        description="""
        ={wye|LN|delta|LL}.  Default is wye.

        DSS property name: `conn`, DSS property index: 9.
        """
    )
    kvar: float | None = Field(
        description="""
        Get/set the present kvar value.  Setting this property forces the inverter to operate in constant kvar mode.

        DSS property name: `kvar`, DSS property index: 10.
        """
    )
    kVA: float | None = Field(
        description="""
        kVA rating of inverter. Used as the base for Dynamics mode and Harmonics mode values.

        DSS property name: `kVA`, DSS property index: 11.
        """
    )
    pctCutin: float | None = Field(
        alias="%Cutin",
        description="""
        % cut-in power -- % of kVA rating of inverter. When the inverter is OFF, the power from the array must be greater than this for the inverter to turn on.

        DSS property name: `%Cutin`, DSS property index: 12.
        """,
    )
    pctCutout: float | None = Field(
        alias="%Cutout",
        description="""
        % cut-out power -- % of kVA rating of inverter. When the inverter is ON, the inverter turns OFF when the power from the array drops below this value.

        DSS property name: `%Cutout`, DSS property index: 13.
        """,
    )
    EffCurve: str | None = Field(
        description="""
        An XYCurve object, previously defined, that describes the PER UNIT efficiency vs PER UNIT of rated kVA for the inverter. Inverter output power is discounted by the multiplier obtained from this curve.

        DSS property name: `EffCurve`, DSS property index: 14.
        """
    )
    PTCurve: str | None = Field(
        alias="P-TCurve",
        description="""
        An XYCurve object, previously defined, that describes the PV array PER UNIT Pmpp vs Temperature curve. Temperature units must agree with the Temperature property and the Temperature shapes used for simulations. The Pmpp values are specified in per unit of the Pmpp value for 1 kW/sq-m irradiance. The value for the temperature at which Pmpp is defined should be 1.0. The net array power is determined by the irradiance * Pmpp * f(Temperature)

        DSS property name: `P-TCurve`, DSS property index: 15.
        """,
    )
    pctR: float | None = Field(
        alias="%R",
        description="""
        Equivalent percent internal resistance, ohms. Default is 50%. Placed in series with internal voltage source for harmonics and dynamics modes. (Limits fault current to about 2 pu if not current limited -- see LimitCurrent)

        DSS property name: `%R`, DSS property index: 16.
        """,
    )
    pctX: float | None = Field(
        alias="%X",
        description="""
        Equivalent percent internal reactance, ohms. Default is 0%. Placed in series with internal voltage source for harmonics and dynamics modes.

        DSS property name: `%X`, DSS property index: 17.
        """,
    )
    model: int | None = Field(
        description="""
        Integer code (default=1) for the model to use for power output variation with voltage. Valid values are:

        1:PVSystem element injects a CONSTANT kW at specified power factor.
        2:PVSystem element is modeled as a CONSTANT ADMITTANCE.
        3:Compute load injection from User-written Model.

        DSS property name: `model`, DSS property index: 18.
        """
    )
    Vminpu: float | None = Field(
        description="""
        Default = 0.90.  Minimum per unit voltage for which the Model is assumed to apply. Below this value, the load model reverts to a constant impedance model except for Dynamics model. In Dynamics mode, the current magnitude is limited to the value the power flow would compute for this voltage.

        DSS property name: `Vminpu`, DSS property index: 19.
        """
    )
    Vmaxpu: float | None = Field(
        description="""
        Default = 1.10.  Maximum per unit voltage for which the Model is assumed to apply. Above this value, the load model reverts to a constant impedance model.

        DSS property name: `Vmaxpu`, DSS property index: 20.
        """
    )
    Balanced: bool | None = Field(
        description="""
        {Yes | No*} Default is No.  Force balanced current only for 3-phase PVSystems. Forces zero- and negative-sequence to zero.

        DSS property name: `Balanced`, DSS property index: 21.
        """
    )
    LimitCurrent: bool | None = Field(
        description="""
        Limits current magnitude to Vminpu value for both 1-phase and 3-phase PVSystems similar to Generator Model 7. For 3-phase, limits the positive-sequence current but not the negative-sequence.

        DSS property name: `LimitCurrent`, DSS property index: 22.
        """
    )
    yearly: str | None = Field(
        description="""
        Dispatch shape to use for yearly simulations.  Must be previously defined as a Loadshape object. If this is not specified, the Daily dispatch shape, if any, is repeated during Yearly solution modes. In the default dispatch mode, the PVSystem element uses this loadshape to trigger State changes.

        DSS property name: `yearly`, DSS property index: 23.
        """
    )
    daily: str | None = Field(
        description="""
        Dispatch shape to use for daily simulations.  Must be previously defined as a Loadshape object of 24 hrs, typically.  In the default dispatch mode, the PVSystem element uses this loadshape to trigger State changes.

        DSS property name: `daily`, DSS property index: 24.
        """
    )
    duty: str | None = Field(
        description="""
        Load shape to use for duty cycle dispatch simulations such as for solar ramp rate studies. Must be previously defined as a Loadshape object. Typically would have time intervals of 1-5 seconds. Designate the number of points to solve using the Set Number=xxxx command. If there are fewer points in the actual shape, the shape is assumed to repeat.

        DSS property name: `duty`, DSS property index: 25.
        """
    )
    Tyearly: str | None = Field(
        description="""
        Temperature shape to use for yearly simulations.  Must be previously defined as a TShape object. If this is not specified, the Daily dispatch shape, if any, is repeated during Yearly solution modes. The PVSystem element uses this TShape to determine the Pmpp from the Pmpp vs T curve. Units must agree with the Pmpp vs T curve.

        DSS property name: `Tyearly`, DSS property index: 26.
        """
    )
    Tdaily: str | None = Field(
        description="""
        Temperature shape to use for daily simulations.  Must be previously defined as a TShape object of 24 hrs, typically.  The PVSystem element uses this TShape to determine the Pmpp from the Pmpp vs T curve. Units must agree with the Pmpp vs T curve.

        DSS property name: `Tdaily`, DSS property index: 27.
        """
    )
    Tduty: str | None = Field(
        description="""
        Temperature shape to use for duty cycle dispatch simulations such as for solar ramp rate studies. Must be previously defined as a TShape object. Typically would have time intervals of 1-5 seconds. Designate the number of points to solve using the Set Number=xxxx command. If there are fewer points in the actual shape, the shape is assumed to repeat. The PVSystem model uses this TShape to determine the Pmpp from the Pmpp vs T curve. Units must agree with the Pmpp vs T curve.

        DSS property name: `Tduty`, DSS property index: 28.
        """
    )
    cls: int | None = Field(
        alias="class",
        description="""
        An arbitrary integer number representing the class of PVSystem element so that PVSystem values may be segregated by class.

        DSS property name: `class`, DSS property index: 29.
        """,
    )
    UserModel: str | None = Field(
        description="""
        Name of DLL containing user-written model, which computes the terminal currents for Dynamics studies, overriding the default model.  Set to "none" to negate previous setting.

        DSS property name: `UserModel`, DSS property index: 30.
        """
    )
    UserData: str | None = Field(
        description="""
        String (in quotes or parentheses) that gets passed to user-written model for defining the data required for that model.

        DSS property name: `UserData`, DSS property index: 31.
        """
    )
    debugtrace: bool | None = Field(
        description="""
        {Yes | No }  Default is no.  Turn this on to capture the progress of the PVSystem model for each iteration.  Creates a separate file for each PVSystem element named "PVSystem_name.csv".

        DSS property name: `debugtrace`, DSS property index: 32.
        """
    )
    VarFollowInverter: bool | None = Field(
        description="""
        Boolean variable (Yes|No) or (True|False). Defaults to False which indicates that the reactive power generation/absorption does not respect the inverter status.When set to True, the PVSystem reactive power generation/absorption will cease when the inverter status is off, due to panel kW dropping below %Cutout.  The reactive power generation/absorption will begin again when the panel kW is above %Cutin.  When set to False, the PVSystem will generate/absorb reactive power regardless of the status of the inverter.

        DSS property name: `VarFollowInverter`, DSS property index: 33.
        """
    )
    DutyStart: float | None = Field(
        description="""
        Starting time offset [hours] into the duty cycle shape for this PVSystem, defaults to 0

        DSS property name: `DutyStart`, DSS property index: 34.
        """
    )
    WattPriority: bool | None = Field(
        description="""
        {Yes/No*/True/False} Set inverter to watt priority instead of the default var priority

        DSS property name: `WattPriority`, DSS property index: 35.
        """
    )
    PFPriority: bool | None = Field(
        description="""
        {Yes/No*/True/False} Set inverter to operate with PF priority when in constant PF mode. If "Yes", value assigned to "WattPriority" is neglected. If controlled by an InvControl with either Volt-Var or DRC or both functions activated, PF priority is neglected and "WattPriority" is considered. Default = No.

        DSS property name: `PFPriority`, DSS property index: 36.
        """
    )
    pctPminNoVars: float | None = Field(
        alias="%PminNoVars",
        description="""
        Minimum active power as percentage of Pmpp under which there is no vars production/absorption.

        DSS property name: `%PminNoVars`, DSS property index: 37.
        """,
    )
    pctPminkvarMax: float | None = Field(
        alias="%PminkvarMax",
        description="""
        Minimum active power as percentage of Pmpp that allows the inverter to produce/absorb reactive power up to its kvarMax or kvarMaxAbs.

        DSS property name: `%PminkvarMax`, DSS property index: 38.
        """,
    )
    kvarMax: float | None = Field(
        description="""
        Indicates the maximum reactive power GENERATION (un-signed numerical variable in kvar) for the inverter (as an un-signed value). Defaults to kVA rating of the inverter.

        DSS property name: `kvarMax`, DSS property index: 39.
        """
    )
    kvarMaxAbs: float | None = Field(
        description="""
        Indicates the maximum reactive power ABSORPTION (un-signed numerical variable in kvar) for the inverter (as an un-signed value). Defaults to kVA rating of the inverter.

        DSS property name: `kvarMaxAbs`, DSS property index: 40.
        """
    )
    kVDC: float | None = Field(
        description="""
        Indicates the rated voltage (kV) at the input of the inverter at the peak of PV energy production. The value is normally greater or equal to the kV base of the PV system. It is used for dynamics simulation ONLY.

        DSS property name: `kVDC`, DSS property index: 41.
        """
    )
    Kp: float | None = Field(
        description="""
        It is the proportional gain for the PI controller within the inverter. Use it to modify the controller response in dynamics simulation mode.

        DSS property name: `Kp`, DSS property index: 42.
        """
    )
    PITol: float | None = Field(
        description="""
        It is the tolerance (%) for the closed loop controller of the inverter. For dynamics simulation mode.

        DSS property name: `PITol`, DSS property index: 43.
        """
    )
    SafeVoltage: float | None = Field(
        description="""
        Indicates the voltage level (%) respect to the base voltage level for which the Inverter will operate. If this threshold is violated, the Inverter will enter safe mode (OFF). For dynamic simulation. By default is 80%

        DSS property name: `SafeVoltage`, DSS property index: 44.
        """
    )
    SafeMode: bool | None = Field(
        description="""
        (Read only) Indicates whether the inverter entered (Yes) or not (No) into Safe Mode.

        DSS property name: `SafeMode`, DSS property index: 45.
        """
    )
    DynamicEq: str | None = Field(
        description="""
        The name of the dynamic equation (DynamicExp) that will be used for defining the dynamic behavior of the generator. If not defined, the generator dynamics will follow the built-in dynamic equation.

        DSS property name: `DynamicEq`, DSS property index: 46.
        """
    )
    DynOut: str | None = Field(
        description="""
        The name of the variables within the Dynamic equation that will be used to govern the PVSystem dynamics. This PVsystem model requires 1 output from the dynamic equation:

            1. Current.

        The output variables need to be defined in the same order.

        DSS property name: `DynOut`, DSS property index: 47.
        """
    )
    ControlMode: str | None = Field(
        description="""
        Defines the control mode for the inverter. It can be one of {GFM | GFL*}. By default it is GFL (Grid Following Inverter). Use GFM (Grid Forming Inverter) for energizing islanded microgrids, but, if the device is conencted to the grid, it is highly recommended to use GFL.

        GFM control mode disables any control action set by the InvControl device.

        DSS property name: `ControlMode`, DSS property index: 48.
        """
    )
    spectrum: str | None = Field(
        description="""
        Name of harmonic voltage or current spectrum for this PVSystem element. A harmonic voltage source is assumed for the inverter. Default value is "default", which is defined when the DSS starts.

        DSS property name: `spectrum`, DSS property index: 49.
        """
    )
    basefreq: float | None = Field(
        description="""
        Base Frequency for ratings.

        DSS property name: `basefreq`, DSS property index: 50.
        """
    )
    enabled: bool | None = Field(
        description="""
        {Yes|No or True|False} Indicates whether this element is enabled.

        DSS property name: `enabled`, DSS property index: 51.
        """
    )

    @root_validator(pre=True)
    def drop_fields(cls, values):
        """Removes undesired fields."""
        values.pop("AmpLimit", None)
        values.pop("AmpLimitGain", None)
        return values


class UPFC(OpenDssElementBaseModel):
    """None"""

    bus1: str | None = Field(
        description="""
        Name of bus to which the input terminal (1) is connected.
        bus1=busname.1.3
        bus1=busname.1.2.3

        DSS property name: `bus1`, DSS property index: 1.
        """
    )
    bus2: str | None = Field(
        description="""
        Name of bus to which the output terminal (2) is connected.
        bus2=busname.1.2
        bus2=busname.1.2.3

        DSS property name: `bus2`, DSS property index: 2.
        """
    )
    refkV: float | None = Field(
        description="""
        UPFC.refkV

        DSS property name: `refkV`, DSS property index: 3.
        """
    )
    PF: float | None = Field(
        description="""
        UPFC.PF

        DSS property name: `PF`, DSS property index: 4.
        """
    )
    Frequency: float | None = Field(
        description="""
        UPFC.Frequency

        DSS property name: `Frequency`, DSS property index: 5.
        """
    )
    Phases: int | None = Field(
        description="""
        UPFC.Phases

        DSS property name: `Phases`, DSS property index: 6.
        """
    )
    Xs: float | None = Field(
        description="""
        Reactance of the series transformer of the UPFC, ohms (default=0.7540 ... 2 mH)

        DSS property name: `Xs`, DSS property index: 7.
        """
    )
    Tol1: float | None = Field(
        description="""
        Tolerance in pu for the series PI controller
        Tol1=0.02 is the format used to define 2% tolerance (Default=2%)

        DSS property name: `Tol1`, DSS property index: 8.
        """
    )
    Mode: int | None = Field(
        description="""
        Integer used to define the control mode of the UPFC:

        0 = Off,
        1 = Voltage regulator,
        2 = Phase angle regulator,
        3 = Dual mode
        4 = It is a control mode where the user can set two different set points to create a secure GAP, these references must be defined in the parameters RefkV and RefkV2. The only restriction when setting these values is that RefkV must be higher than RefkV2.
        5 = In this mode the user can define the same GAP using two set points as in control mode 4. The only difference between mode 5 and mode 4 is that in mode 5, the UPFC controller performs dual control actions just as in control mode 3

        DSS property name: `Mode`, DSS property index: 9.
        """
    )
    VpqMax: float | None = Field(
        description="""
        Maximum voltage (in volts) delivered by the series voltage source (Default = 24 V)

        DSS property name: `VpqMax`, DSS property index: 10.
        """
    )
    LossCurve: str | None = Field(
        description="""
        Name of the XYCurve for describing the losses behavior as a function of the voltage at the input of the UPFC

        DSS property name: `LossCurve`, DSS property index: 11.
        """
    )
    VHLimit: float | None = Field(
        description="""
        High limit for the voltage at the input of the UPFC, if the voltage is above this value the UPFC turns off. This value is specified in Volts (default 300 V)

        DSS property name: `VHLimit`, DSS property index: 12.
        """
    )
    VLLimit: float | None = Field(
        description="""
        low limit for the voltage at the input of the UPFC, if voltage is below this value the UPFC turns off. This value is specified in Volts (default 125 V)

        DSS property name: `VLLimit`, DSS property index: 13.
        """
    )
    CLimit: float | None = Field(
        description="""
        Current Limit for the UPFC, if the current passing through the UPFC is higher than this value the UPFC turns off. This value is specified in Amps (Default 265 A)

        DSS property name: `CLimit`, DSS property index: 14.
        """
    )
    refkV2: float | None = Field(
        description="""
        UPFC.refkV2

        DSS property name: `refkV2`, DSS property index: 15.
        """
    )
    kvarLimit: float | None = Field(
        description="""
        Maximum amount of reactive power (kvar) that can be absorved by the UPFC (Default = 5)

        DSS property name: `kvarLimit`, DSS property index: 16.
        """
    )
    Element: str | None = Field(
        description="""
        The name of the PD element monitored when operating with reactive power compensation. Normally, it should be the PD element immediately upstream the UPFC. The element must be defined including the class, e.g. Line.myline.

        DSS property name: `Element`, DSS property index: 17.
        """
    )
    spectrum: str | None = Field(
        description="""
        Name of harmonic spectrum for this source.  Default is "defaultUPFC", which is defined when the DSS starts.

        DSS property name: `spectrum`, DSS property index: 18.
        """
    )
    basefreq: float | None = Field(
        description="""
        Base Frequency for ratings.

        DSS property name: `basefreq`, DSS property index: 19.
        """
    )
    enabled: bool | None = Field(
        description="""
        {Yes|No or True|False} Indicates whether this element is enabled.

        DSS property name: `enabled`, DSS property index: 20.
        """
    )

    @root_validator(pre=True)
    def drop_fields(cls, values):
        """Removes undesired fields."""
        return values


class UPFCControl(OpenDssElementBaseModel):
    """None"""

    UPFCList: list | None = Field(
        description="""
        The list of all the UPFC devices to be controlled by this controller, If left empty, this control will apply for all UPFCs in the model.

        DSS property name: `UPFCList`, DSS property index: 1.
        """
    )
    basefreq: float | None = Field(
        description="""
        Base Frequency for ratings.

        DSS property name: `basefreq`, DSS property index: 2.
        """
    )
    enabled: bool | None = Field(
        description="""
        {Yes|No or True|False} Indicates whether this element is enabled.

        DSS property name: `enabled`, DSS property index: 3.
        """
    )

    @root_validator(pre=True)
    def drop_fields(cls, values):
        """Removes undesired fields."""
        return values


class ESPVLControl(OpenDssElementBaseModel):
    """None"""

    Element: str | None = Field(
        description="""
        Full object name of the circuit element, typically a line or transformer, which the control is monitoring. There is no default; must be specified.

        DSS property name: `Element`, DSS property index: 1.
        """
    )
    Terminal: int | None = Field(
        description="""
        Number of the terminal of the circuit element to which the ESPVLControl control is connected. 1 or 2, typically.  Default is 1. Make sure you have the direction on the power matching the sign of kWLimit.

        DSS property name: `Terminal`, DSS property index: 2.
        """
    )
    Type: str | None = Field(
        description="""
        Type of controller.  1= System Controller; 2= Local controller.

        DSS property name: `Type`, DSS property index: 3.
        """
    )
    kWBand: float | None = Field(
        description="""
        Bandwidth (kW) of the dead band around the target limit.No dispatch changes are attempted if the power in the monitored terminal stays within this band.

        DSS property name: `kWBand`, DSS property index: 4.
        """
    )
    kvarlimit: float | None = Field(
        description="""
        Max kvar to be delivered through the element.  Uses same dead band as kW.

        DSS property name: `kvarlimit`, DSS property index: 5.
        """
    )
    LocalControlList: list | None = Field(
        description="""
        Array list of ESPVLControl local controller objects to be dispatched by System Controller. If not specified, all ESPVLControl devices with type=local in the circuit not attached to another controller are assumed to be part of this controller's fleet.

        DSS property name: `LocalControlList`, DSS property index: 6.
        """
    )
    LocalControlWeights: list | None = Field(
        description="""
        Array of proportional weights corresponding to each ESPVLControl local controller in the LocalControlList.

        DSS property name: `LocalControlWeights`, DSS property index: 7.
        """
    )
    PVSystemList: list | None = Field(
        description="""
        Array list of PVSystem objects to be dispatched by a Local Controller.

        DSS property name: `PVSystemList`, DSS property index: 8.
        """
    )
    PVSystemWeights: list | None = Field(
        description="""
        Array of proportional weights corresponding to each PVSystem in the PVSystemList.

        DSS property name: `PVSystemWeights`, DSS property index: 9.
        """
    )
    StorageList: list | None = Field(
        description="""
        Array list of Storage objects to be dispatched by Local Controller.

        DSS property name: `StorageList`, DSS property index: 10.
        """
    )
    StorageWeights: list | None = Field(
        description="""
        Array of proportional weights corresponding to each Storage object in the StorageControlList.

        DSS property name: `StorageWeights`, DSS property index: 11.
        """
    )
    basefreq: float | None = Field(
        description="""
        Base Frequency for ratings.

        DSS property name: `basefreq`, DSS property index: 12.
        """
    )
    enabled: bool | None = Field(
        description="""
        {Yes|No or True|False} Indicates whether this element is enabled.

        DSS property name: `enabled`, DSS property index: 13.
        """
    )

    @root_validator(pre=True)
    def drop_fields(cls, values):
        """Removes undesired fields."""
        return values


class IndMach012(OpenDssElementBaseModel):
    """None"""

    phases: int | None = Field(
        description="""
        Number of Phases, this Induction Machine.

        DSS property name: `phases`, DSS property index: 1.
        """
    )
    bus1: str | None = Field(
        description="""
        Bus to which the Induction Machine is connected.  May include specific node specification.

        DSS property name: `bus1`, DSS property index: 2.
        """
    )
    kv: float | None = Field(
        description="""
        Nominal rated (1.0 per unit) voltage, kV. For 2- and 3-phase machines, specify phase-phase kV. Otherwise, specify actual kV across each branch of the machine. If wye (star), specify phase-neutral kV. If delta or phase-phase connected, specify phase-phase kV.

        DSS property name: `kv`, DSS property index: 3.
        """
    )
    kW: float | None = Field(
        description="""
        Shaft Power, kW, for the Induction Machine.  A positive value denotes power for a load.
        Negative value denotes an induction generator.

        DSS property name: `kW`, DSS property index: 4.
        """
    )
    pf: float | None = Field(
        description="""
        [Read Only] Present power factor for the machine.

        DSS property name: `pf`, DSS property index: 5.
        """
    )
    conn: str | None = Field(
        description="""
        Connection of stator: Delta or Wye. Default is Delta.

        DSS property name: `conn`, DSS property index: 6.
        """
    )
    kVA: float | None = Field(
        description="""
        Rated kVA for the machine.

        DSS property name: `kVA`, DSS property index: 7.
        """
    )
    H: float | None = Field(
        description="""
        Per unit mass constant of the machine.  MW-sec/MVA.  Default is 1.0.

        DSS property name: `H`, DSS property index: 8.
        """
    )
    D: float | None = Field(
        description="""
        Damping constant.  Usual range is 0 to 4. Default is 1.0.  Adjust to get damping in Dynamics mode,

        DSS property name: `D`, DSS property index: 9.
        """
    )
    puRs: float | None = Field(
        description="""
        Per unit stator resistance. Default is 0.0053.

        DSS property name: `puRs`, DSS property index: 10.
        """
    )
    puXs: float | None = Field(
        description="""
        Per unit stator leakage reactance. Default is 0.106.

        DSS property name: `puXs`, DSS property index: 11.
        """
    )
    puRr: float | None = Field(
        description="""
        Per unit rotor  resistance. Default is 0.007.

        DSS property name: `puRr`, DSS property index: 12.
        """
    )
    puXr: float | None = Field(
        description="""
        Per unit rotor leakage reactance. Default is 0.12.

        DSS property name: `puXr`, DSS property index: 13.
        """
    )
    puXm: float | None = Field(
        description="""
        Per unit magnetizing reactance.Default is 4.0.

        DSS property name: `puXm`, DSS property index: 14.
        """
    )
    Slip: float | None = Field(
        description="""
        Initial slip value. Default is 0.007

        DSS property name: `Slip`, DSS property index: 15.
        """
    )
    MaxSlip: float | None = Field(
        description="""
        Max slip value to allow. Default is 0.1. Set this before setting slip.

        DSS property name: `MaxSlip`, DSS property index: 16.
        """
    )
    SlipOption: str | None = Field(
        description="""
        Option for slip model. One of {fixedslip | variableslip*  }

        DSS property name: `SlipOption`, DSS property index: 17.
        """
    )
    Yearly: str | None = Field(
        description="""
        LOADSHAPE object to use for yearly simulations.  Must be previously defined as a Loadshape object. Is set to the Daily load shape  when Daily is defined.  The daily load shape is repeated in this case. Set Status=Fixed to ignore Loadshape designation. Set to NONE to reset to no loadahape. The default is no variation.

        DSS property name: `Yearly`, DSS property index: 18.
        """
    )
    Daily: str | None = Field(
        description="""
        LOADSHAPE object to use for daily simulations.  Must be previously defined as a Loadshape object of 24 hrs, typically. Set Status=Fixed to ignore Loadshape designation. Set to NONE to reset to no loadahape. Default is no variation (constant) if not defined. Side effect: Sets Yearly load shape if not already defined.

        DSS property name: `Daily`, DSS property index: 19.
        """
    )
    Duty: str | None = Field(
        description="""
        LOADSHAPE object to use for duty cycle simulations.  Must be previously defined as a Loadshape object.  Typically would have time intervals less than 1 hr. Designate the number of points to solve using the Set Number=xxxx command. If there are fewer points in the actual shape, the shape is assumed to repeat.Set to NONE to reset to no loadahape. Set Status=Fixed to ignore Loadshape designation.  Defaults to Daily curve If not specified.

        DSS property name: `Duty`, DSS property index: 20.
        """
    )
    Debugtrace: bool | None = Field(
        description="""
        [Yes | No*] Write DebugTrace file.

        DSS property name: `Debugtrace`, DSS property index: 21.
        """
    )
    spectrum: str | None = Field(
        description="""
        Name of harmonic voltage or current spectrum for this IndMach012. Voltage behind Xd" for machine - default. Current injection for inverter. Default value is "default", which is defined when the DSS starts.

        DSS property name: `spectrum`, DSS property index: 22.
        """
    )
    basefreq: float | None = Field(
        description="""
        Base Frequency for ratings.

        DSS property name: `basefreq`, DSS property index: 23.
        """
    )
    enabled: bool | None = Field(
        description="""
        {Yes|No or True|False} Indicates whether this element is enabled.

        DSS property name: `enabled`, DSS property index: 24.
        """
    )

    @root_validator(pre=True)
    def drop_fields(cls, values):
        """Removes undesired fields."""
        return values


class GICsource(OpenDssElementBaseModel):
    """None"""

    Volts: float | None = Field(
        description="""
        Voltage magnitude, in volts, of the GIC voltage induced across the associated line. When specified, induced voltage is assumed defined by Voltage and Angle properties.

        Specify this value

        OR

        EN, EE, lat1, lon1, lat2, lon2.

        Not both!!  Last one entered will take precedence. Assumed identical in each phase of the Line object.

        DSS property name: `Volts`, DSS property index: 1.
        """
    )
    angle: float | None = Field(
        description="""
        Phase angle in degrees of first phase. Default=0.0.  See Voltage property

        DSS property name: `angle`, DSS property index: 2.
        """
    )
    frequency: float | None = Field(
        description="""
        Source frequency.  Defaults to  0.1 Hz. So GICSource=0 at power frequency.

        DSS property name: `frequency`, DSS property index: 3.
        """
    )
    phases: int | None = Field(
        description="""
        Number of phases.  Defaults to 3. All three phases are assumed in phase (zero sequence)

        DSS property name: `phases`, DSS property index: 4.
        """
    )
    EN: float | None = Field(
        description="""
        Northward Electric field (V/km). If specified, Voltage and Angle are computed from EN, EE, lat and lon values.

        DSS property name: `EN`, DSS property index: 5.
        """
    )
    EE: float | None = Field(
        description="""
        Eastward Electric field (V/km).  If specified, Voltage and Angle are computed from EN, EE, lat and lon values.

        DSS property name: `EE`, DSS property index: 6.
        """
    )
    Lat1: float | None = Field(
        description="""
        Latitude of Bus1 of the line(degrees)

        DSS property name: `Lat1`, DSS property index: 7.
        """
    )
    Lon1: float | None = Field(
        description="""
        Longitude of Bus1 of the line (degrees)

        DSS property name: `Lon1`, DSS property index: 8.
        """
    )
    Lat2: float | None = Field(
        description="""
        Latitude of Bus2 of the line (degrees)

        DSS property name: `Lat2`, DSS property index: 9.
        """
    )
    Lon2: float | None = Field(
        description="""
        Longitude of Bus2 of the line (degrees)

        DSS property name: `Lon2`, DSS property index: 10.
        """
    )
    spectrum: str | None = Field(
        description="""
        Not used.

        DSS property name: `spectrum`, DSS property index: 11.
        """
    )
    basefreq: float | None = Field(
        description="""
        Not used.

        DSS property name: `basefreq`, DSS property index: 12.
        """
    )
    enabled: bool | None = Field(
        description="""
        {Yes|No or True|False} Indicates whether this element is enabled.

        DSS property name: `enabled`, DSS property index: 13.
        """
    )

    @root_validator(pre=True)
    def drop_fields(cls, values):
        """Removes undesired fields."""
        return values


class AutoTrans(OpenDssElementBaseModel):
    """None"""

    phases: int | None = Field(
        description="""
        Number of phases this AutoTrans. Default is 3.

        DSS property name: `phases`, DSS property index: 1.
        """
    )
    windings: int | None = Field(
        description="""
        Number of windings, this AutoTranss. (Also is the number of terminals) Default is 2. This property triggers memory allocation for the AutoTrans and will cause other properties to revert to default values.

        DSS property name: `windings`, DSS property index: 2.
        """
    )
    pctR: list | None = Field(
        alias="%r",
        description="""
        Percent ac resistance this winding.  This value is for the power flow model.Is derived from the full load losses in the transformer test report.

        DSS property name: `%R`, DSS property index: 9.
        """,
    )
    Rdcohms: list | None = Field(
        description="""
        Winding dc resistance in OHMS. Specify this for GIC analysis. From transformer test report (divide by number of phases). Defaults to 85% of %R property (the ac value that includes stray losses).

        DSS property name: `Rdcohms`, DSS property index: 10.
        """
    )
    Core: str | None = Field(
        description="""
        {Shell*|5-leg|3-Leg|1-phase|core-1-phase|4-leg} Core Type. Used for GIC analysis in auxiliary programs. Not used inside OpenDSS.

        DSS property name: `Core`, DSS property index: 11.
        """
    )
    buses: list | None = Field(
        description="""
        Use this to specify all the bus connections at once using an array. Example:

        New AutoTrans.T1 buses=[Hbus, Xbus]

        DSS property name: `buses`, DSS property index: 12.
        """
    )
    conns: list | None = Field(
        description="""
        Use this to specify all the Winding connections at once using an array. Example:

        New AutoTrans.T1 buses=[Hbus, Xbus] ~ conns=(series, wye)

        DSS property name: `conns`, DSS property index: 13.
        """
    )
    kVs: list | None = Field(
        description="""
        Use this to specify the kV ratings of all windings at once using an array. Example:

        New AutoTrans.T1 buses=[Hbus, Xbus]
        ~ conns=(series, wye)
        ~ kvs=(115, 12.47)

        See kV= property for voltage rules.

        DSS property name: `kVs`, DSS property index: 14.
        """
    )
    kVAs: list | None = Field(
        description="""
        Use this to specify the kVA ratings of all windings at once using an array.

        DSS property name: `kVAs`, DSS property index: 15.
        """
    )
    taps: list | None = Field(
        description="""
        Use this to specify the p.u. tap of all windings at once using an array.

        DSS property name: `taps`, DSS property index: 16.
        """
    )
    XHX: float | None = Field(
        description="""
        Use this to specify the percent reactance, H-L (winding 1 to winding 2).  Use for 2- or 3-winding AutoTranss. On the kVA base of winding 1(H-X).

        DSS property name: `XHX`, DSS property index: 17.
        """
    )
    XHT: float | None = Field(
        description="""
        Use this to specify the percent reactance, H-T (winding 1 to winding 3).  Use for 3-winding AutoTranss only. On the kVA base of winding 1(H-X).

        DSS property name: `XHT`, DSS property index: 18.
        """
    )
    XXT: float | None = Field(
        description="""
        Use this to specify the percent reactance, L-T (winding 2 to winding 3).  Use for 3-winding AutoTranss only. On the kVA base of winding 1(H-X).

        DSS property name: `XXT`, DSS property index: 19.
        """
    )
    XSCarray: list | None = Field(
        description="""
        Use this to specify the percent reactance between all pairs of windings as an array. All values are on the kVA base of winding 1.  The order of the values is as follows:

        (x12 13 14... 23 24.. 34 ..)

        There will be n(n-1)/2 values, where n=number of windings.

        DSS property name: `XSCarray`, DSS property index: 20.
        """
    )
    thermal: float | None = Field(
        description="""
        Thermal time constant of the AutoTrans in hours.  Typically about 2.

        DSS property name: `thermal`, DSS property index: 21.
        """
    )
    n: float | None = Field(
        description="""
        n Exponent for thermal properties in IEEE C57.  Typically 0.8.

        DSS property name: `n`, DSS property index: 22.
        """
    )
    m: float | None = Field(
        description="""
        m Exponent for thermal properties in IEEE C57.  Typically 0.9 - 1.0

        DSS property name: `m`, DSS property index: 23.
        """
    )
    flrise: float | None = Field(
        description="""
        Temperature rise, deg C, for full load.  Default is 65.

        DSS property name: `flrise`, DSS property index: 24.
        """
    )
    hsrise: float | None = Field(
        description="""
        Hot spot temperature rise, deg C.  Default is 15.

        DSS property name: `hsrise`, DSS property index: 25.
        """
    )
    pctloadloss: float | None = Field(
        alias="%loadloss",
        description="""
        Percent load loss at full load. The %R of the High and Low windings (1 and 2) are adjusted to agree at rated kVA loading.

        DSS property name: `%loadloss`, DSS property index: 26.
        """,
    )
    pctnoloadloss: float | None = Field(
        alias="%noloadloss",
        description="""
        Percent no load losses at rated excitatation voltage. Default is 0. Converts to a resistance in parallel with the magnetizing impedance in each winding.

        DSS property name: `%noloadloss`, DSS property index: 27.
        """,
    )
    normhkVA: float | None = Field(
        description="""
        Normal maximum kVA rating of H winding (winding 1+2).  Usually 100% - 110% ofmaximum nameplate rating, depending on load shape. Defaults to 110% of kVA rating of Winding 1.

        DSS property name: `normhkVA`, DSS property index: 28.
        """
    )
    emerghkVA: float | None = Field(
        description="""
        Emergency (contingency)  kVA rating of H winding (winding 1+2).  Usually 140% - 150% ofmaximum nameplate rating, depending on load shape. Defaults to 150% of kVA rating of Winding 1.

        DSS property name: `emerghkVA`, DSS property index: 29.
        """
    )
    sub: bool | None = Field(
        description="""
        ={Yes|No}  Designates whether this AutoTrans is to be considered a substation.Default is No.

        DSS property name: `sub`, DSS property index: 30.
        """
    )
    MaxTap: list | None = Field(
        description="""
        Max per unit tap for the active winding.  Default is 1.10

        DSS property name: `MaxTap`, DSS property index: 31.
        """
    )
    MinTap: list | None = Field(
        description="""
        Min per unit tap for the active winding.  Default is 0.90

        DSS property name: `MinTap`, DSS property index: 32.
        """
    )
    NumTaps: list | None = Field(
        description="""
        Total number of taps between min and max tap.  Default is 32 (16 raise and 16 lower taps about the neutral position). The neutral position is not counted.

        DSS property name: `NumTaps`, DSS property index: 33.
        """
    )
    subname: str | None = Field(
        description="""
        Substation Name. Optional. Default is null. If specified, printed on plots

        DSS property name: `subname`, DSS property index: 34.
        """
    )
    pctimag: float | None = Field(
        alias="%imag",
        description="""
        Percent magnetizing current. Default=0.0. Magnetizing branch is in parallel with windings in each phase. Also, see "ppm_antifloat".

        DSS property name: `%imag`, DSS property index: 35.
        """,
    )
    ppm_antifloat: float | None = Field(
        description="""
        Default=1 ppm.  Parts per million of AutoTrans winding VA rating connected to ground to protect against accidentally floating a winding without a reference. If positive then the effect is adding a very large reactance to ground.  If negative, then a capacitor.

        DSS property name: `ppm_antifloat`, DSS property index: 36.
        """
    )
    pctRs: list | None = Field(
        alias="%rs",
        description="""
        Use this property to specify all the winding ac %resistances using an array. Example:

        New AutoTrans.T1 buses=[Hibus, lowbus] ~ %Rs=(0.2  0.3)

        DSS property name: `%Rs`, DSS property index: 37.
        """,
    )
    XRConst: bool | None = Field(
        description="""
        ={Yes|No} Default is NO. Signifies whether or not the X/R is assumed contant for harmonic studies.

        DSS property name: `XRConst`, DSS property index: 38.
        """
    )
    LeadLag: str | None = Field(
        description="""
        {Lead | Lag (default) | ANSI (default) | Euro } Designation in mixed Delta-wye connections the relationship between HV to LV winding. Default is ANSI 30 deg lag, e.g., Dy1 of Yd1 vector group. To get typical European Dy11 connection, specify either "lead" or "Euro"

        DSS property name: `LeadLag`, DSS property index: 39.
        """
    )
    normamps: float | None = Field(
        description="""
        Normal rated current.

        DSS property name: `normamps`, DSS property index: 41.
        """
    )
    emergamps: float | None = Field(
        description="""
        Maximum or emerg current.

        DSS property name: `emergamps`, DSS property index: 42.
        """
    )
    faultrate: float | None = Field(
        description="""
        Failure rate per year.

        DSS property name: `faultrate`, DSS property index: 43.
        """
    )
    pctperm: float | None = Field(
        description="""
        Percent of failures that become permanent.

        DSS property name: `pctperm`, DSS property index: 44.
        """
    )
    repair: float | None = Field(
        description="""
        Hours to repair.

        DSS property name: `repair`, DSS property index: 45.
        """
    )
    basefreq: float | None = Field(
        description="""
        Base Frequency for ratings.

        DSS property name: `basefreq`, DSS property index: 46.
        """
    )
    enabled: bool | None = Field(
        description="""
        {Yes|No or True|False} Indicates whether this element is enabled.

        DSS property name: `enabled`, DSS property index: 47.
        """
    )

    @root_validator(pre=True)
    def drop_fields(cls, values):
        """Removes undesired fields."""
        return values


class RegControl(OpenDssElementBaseModel):
    """None"""

    transformer: str | None = Field(
        description="""
        Name of Transformer or AutoTrans element to which the RegControl is connected. Do not specify the full object name; "Transformer" or "AutoTrans" is assumed for the object class.  Example:

        Transformer=Xfmr1

        DSS property name: `transformer`, DSS property index: 1.
        """
    )
    winding: int | None = Field(
        description="""
        Number of the winding of the transformer element that the RegControl is monitoring. 1 or 2, typically.  Side Effect: Sets TAPWINDING property to the same winding.

        DSS property name: `winding`, DSS property index: 2.
        """
    )
    vreg: float | None = Field(
        description="""
        Voltage regulator setting, in VOLTS, for the winding being controlled.  Multiplying this value times the ptratio should yield the voltage across the WINDING of the controlled transformer. Default is 120.0

        DSS property name: `vreg`, DSS property index: 3.
        """
    )
    band: float | None = Field(
        description="""
        Bandwidth in VOLTS for the controlled bus (see help for ptratio property).  Default is 3.0

        DSS property name: `band`, DSS property index: 4.
        """
    )
    ptratio: float | None = Field(
        description="""
        Ratio of the PT that converts the controlled winding voltage to the regulator control voltage. Default is 60.  If the winding is Wye, the line-to-neutral voltage is used.  Else, the line-to-line voltage is used. SIDE EFFECT: Also sets RemotePTRatio property.

        DSS property name: `ptratio`, DSS property index: 5.
        """
    )
    CTprim: float | None = Field(
        description="""
        Rating, in Amperes, of the primary CT rating for which the line amps convert to control rated amps.The typical default secondary ampere rating is 0.2 Amps (check with manufacturer specs). Current at which the LDC voltages match the R and X settings.

        DSS property name: `CTprim`, DSS property index: 6.
        """
    )
    R: float | None = Field(
        description="""
        R setting on the line drop compensator in the regulator, expressed in VOLTS.

        DSS property name: `R`, DSS property index: 7.
        """
    )
    X: float | None = Field(
        description="""
        X setting on the line drop compensator in the regulator, expressed in VOLTS.

        DSS property name: `X`, DSS property index: 8.
        """
    )
    bus: str | None = Field(
        description="""
        Name of a bus (busname.nodename) in the system to use as the controlled bus instead of the bus to which the transformer winding is connected or the R and X line drop compensator settings.  Do not specify this value if you wish to use the line drop compensator settings.  Default is null string. Assumes the base voltage for this bus is the same as the transformer winding base specified above. Note: This bus (1-phase) WILL BE CREATED by the regulator control upon SOLVE if not defined by some other device. You can specify the node of the bus you wish to sample (defaults to 1). If specified, the RegControl is redefined as a 1-phase device since only one voltage is used.

        DSS property name: `bus`, DSS property index: 9.
        """
    )
    delay: float | None = Field(
        description="""
        Time delay, in seconds, from when the voltage goes out of band to when the tap changing begins. This is used to determine which regulator control will act first. Default is 15.  You may specify any floating point number to achieve a model of whatever condition is necessary.

        DSS property name: `delay`, DSS property index: 10.
        """
    )
    reversible: bool | None = Field(
        description="""
        {Yes |No*} Indicates whether or not the regulator can be switched to regulate in the reverse direction. Default is No.Typically applies only to line regulators and not to LTC on a substation transformer.

        DSS property name: `reversible`, DSS property index: 11.
        """
    )
    revvreg: float | None = Field(
        description="""
        Voltage setting in volts for operation in the reverse direction.

        DSS property name: `revvreg`, DSS property index: 12.
        """
    )
    revband: float | None = Field(
        description="""
        Bandwidth for operating in the reverse direction.

        DSS property name: `revband`, DSS property index: 13.
        """
    )
    revR: float | None = Field(
        description="""
        R line drop compensator setting for reverse direction.

        DSS property name: `revR`, DSS property index: 14.
        """
    )
    revX: float | None = Field(
        description="""
        X line drop compensator setting for reverse direction.

        DSS property name: `revX`, DSS property index: 15.
        """
    )
    tapdelay: float | None = Field(
        description="""
        Delay in sec between tap changes. Default is 2. This is how long it takes between changes after the first change.

        DSS property name: `tapdelay`, DSS property index: 16.
        """
    )
    debugtrace: bool | None = Field(
        description="""
        {Yes | No* }  Default is no.  Turn this on to capture the progress of the regulator model for each control iteration.  Creates a separate file for each RegControl named "REG_name.csv".

        DSS property name: `debugtrace`, DSS property index: 17.
        """
    )
    maxtapchange: int | None = Field(
        description="""
        Maximum allowable tap change per control iteration in STATIC control mode.  Default is 16.

        Set this to 1 to better approximate actual control action.

        Set this to 0 to fix the tap in the current position.

        DSS property name: `maxtapchange`, DSS property index: 18.
        """
    )
    inversetime: bool | None = Field(
        description="""
        {Yes | No* } Default is no.  The time delay is adjusted inversely proportional to the amount the voltage is outside the band down to 10%.

        DSS property name: `inversetime`, DSS property index: 19.
        """
    )
    tapwinding: int | None = Field(
        description="""
        Winding containing the actual taps, if different than the WINDING property. Defaults to the same winding as specified by the WINDING property.

        DSS property name: `tapwinding`, DSS property index: 20.
        """
    )
    vlimit: float | None = Field(
        description="""
        Voltage Limit for bus to which regulated winding is connected (e.g. first customer). Default is 0.0. Set to a value greater then zero to activate this function.

        DSS property name: `vlimit`, DSS property index: 21.
        """
    )
    PTphase: str | None = Field(
        description="""
        For multi-phase transformers, the number of the phase being monitored or one of { MAX | MIN} for all phases. Default=1. Must be less than or equal to the number of phases. Ignored for regulated bus.

        DSS property name: `PTphase`, DSS property index: 22.
        """
    )
    revThreshold: float | None = Field(
        description="""
        kW reverse power threshold for reversing the direction of the regulator. Default is 100.0 kw.

        DSS property name: `revThreshold`, DSS property index: 23.
        """
    )
    revDelay: float | None = Field(
        description="""
        Time Delay in seconds (s) for executing the reversing action once the threshold for reversing has been exceeded. Default is 60 s.

        DSS property name: `revDelay`, DSS property index: 24.
        """
    )
    revNeutral: bool | None = Field(
        description="""
        {Yes | No*} Default is no. Set this to Yes if you want the regulator to go to neutral in the reverse direction or in cogen operation.

        DSS property name: `revNeutral`, DSS property index: 25.
        """
    )
    EventLog: bool | None = Field(
        description="""
        {Yes/True* | No/False} Default is YES for regulator control. Log control actions to Eventlog.

        DSS property name: `EventLog`, DSS property index: 26.
        """
    )
    RemotePTRatio: float | None = Field(
        description="""
        When regulating a bus (the Bus= property is set), the PT ratio required to convert actual voltage at the remote bus to control voltage. Is initialized to PTratio property. Set this property after setting PTratio.

        DSS property name: `RemotePTRatio`, DSS property index: 27.
        """
    )
    TapNum: int | None = Field(
        description="""
        An integer number indicating the tap position that the controlled transformer winding tap position is currently at, or is being set to.  If being set, and the value is outside the range of the transformer min or max tap, then set to the min or max tap position as appropriate. Default is 0

        DSS property name: `TapNum`, DSS property index: 28.
        """
    )
    LDC_Z: float | None = Field(
        description="""
        Z value for Beckwith LDC_Z control option. Volts adjustment at rated control current.

        DSS property name: `LDC_Z`, DSS property index: 30.
        """
    )
    rev_Z: float | None = Field(
        description="""
        Reverse Z value for Beckwith LDC_Z control option.

        DSS property name: `rev_Z`, DSS property index: 31.
        """
    )
    Cogen: bool | None = Field(
        description="""
        {Yes|No*} Default is No. The Cogen feature is activated. Continues looking forward if power reverses, but switches to reverse-mode LDC, vreg and band values.

        DSS property name: `Cogen`, DSS property index: 32.
        """
    )
    basefreq: float | None = Field(
        description="""
        Base Frequency for ratings.

        DSS property name: `basefreq`, DSS property index: 33.
        """
    )
    enabled: bool | None = Field(
        description="""
        {Yes|No or True|False} Indicates whether this element is enabled.

        DSS property name: `enabled`, DSS property index: 34.
        """
    )

    @root_validator(pre=True)
    def drop_fields(cls, values):
        """Removes undesired fields."""
        return values


class InvControl(OpenDssElementBaseModel):
    """None"""

    DERList: list | None = Field(
        description="""
        Array list of PVSystem and/or Storage elements to be controlled. If not specified, all PVSystem and Storage in the circuit are assumed to be controlled by this control.

        No capability of hierarchical control between two controls for a single element is implemented at this time.

        DSS property name: `DERList`, DSS property index: 1.
        """
    )
    Mode: str | None = Field(
        description="""
        Smart inverter function in which the InvControl will control the PC elements specified in DERList, according to the options below:

        Must be one of: {VOLTVAR* | VOLTWATT | DYNAMICREACCURR | WATTPF | WATTVAR | GFM}
        if the user desires to use modes simultaneously, then set the CombiMode property. Setting the Mode to any valid value disables combination mode.

        In volt-var mode (Default). This mode attempts to CONTROL the vars, according to one or two volt-var curves, depending on the monitored voltages, present active power output, and the capabilities of the PVSystem/Storage.

        In volt-watt mode. This mode attempts to LIMIT the watts, according to one defined volt-watt curve, depending on the monitored voltages and the capabilities of the PVSystem/Storage.

        In dynamic reactive current mode. This mode attempts to increasingly counter deviations by CONTROLLING vars, depending on the monitored voltages, present active power output, and the capabilities of the of the PVSystem/Storage.

        In watt-pf mode. This mode attempts to CONTROL the vars, according to a watt-pf curve, depending on the present active power output, and the capabilities of the PVSystem/Storage.

        In watt-var mode. This mode attempts to CONTROL the vars, according to a watt-var curve, depending on the present active power output, and the capabilities of the PVSystem/Storage.

        In GFM mode this control will trigger the GFM control routine for the DERs within the DERList. The GFM actiosn will only take place if the pointed DERs are in GFM mode. The controller parameters are locally setup at the DER.

        DSS property name: `Mode`, DSS property index: 2.
        """
    )
    CombiMode: str | None = Field(
        description="""
        Combination of smart inverter functions in which the InvControl will control the PC elements in DERList, according to the options below:

        Must be a combination of the following: {VV_VW | VV_DRC}. Default is to not set this property, in which case the single control mode in Mode is active.

        In combined VV_VW mode, both volt-var and volt-watt control modes are active simultaneously.  See help individually for volt-var mode and volt-watt mode in Mode property.
        Note that the PVSystem/Storage will attempt to achieve both the volt-watt and volt-var set-points based on the capabilities of the inverter in the PVSystem/Storage (kVA rating, etc), any limits set on maximum active power,

        In combined VV_DRC, both the volt-var and the dynamic reactive current modes are simultaneously active.

        DSS property name: `CombiMode`, DSS property index: 3.
        """
    )
    vvc_curve1: str | None = Field(
        description="""
        Required for VOLTVAR mode.

        Name of the XYCurve object containing the volt-var curve. The positive values of the y-axis of the volt-var curve represent values in pu of the provided base reactive power. The negative values of the y-axis are values in pu of the absorbed base reactive power.
        Provided and absorbed base reactive power values are defined in the RefReactivePower property

        Units for the x-axis are per-unit voltage, which may be in per unit of the rated voltage for the PVSystem/Storage, or may be in per unit of the average voltage at the terminals over a user-defined number of prior solutions.

        DSS property name: `vvc_curve1`, DSS property index: 4.
        """
    )
    hysteresis_offset: float | None = Field(
        description="""
        Required for VOLTVAR mode, and defaults to 0.

        for the times when the terminal voltage is decreasing, this is the off-set in per-unit voltage of a curve whose shape is the same as vvc_curve. It is offset by a certain negative value of per-unit voltage, which is defined by the base quantity for the x-axis of the volt-var curve (see help for voltage_curvex_ref)

        if the PVSystem/Storage terminal voltage has been increasing, and has not changed directions, utilize vvc_curve1 for the volt-var response.

        if the PVSystem/Storage terminal voltage has been increasing and changes directions and begins to decrease, then move from utilizing vvc_curve1 to a volt-var curve of the same shape, but offset by a certain per-unit voltage value.

        Maintain the same per-unit available var output level (unless head-room has changed due to change in active power or kva rating of PVSystem/Storage).  Per-unit var values remain the same for this internally constructed second curve (hysteresis curve).

        if the terminal voltage has been decreasing and changes directions and begins to increase , then move from utilizing the offset curve, back to the vvc_curve1 for volt-var response, but stay at the same per-unit available vars output level.

        DSS property name: `hysteresis_offset`, DSS property index: 5.
        """
    )
    voltage_curvex_ref: str | None = Field(
        description="""
        Required for VOLTVAR and VOLTWATT modes, and defaults to rated.  Possible values are: {rated|avg|ravg}.

        Defines whether the x-axis values (voltage in per unit) for vvc_curve1 and the volt-watt curve corresponds to:

        rated. The rated voltage for the PVSystem/Storage object (1.0 in the volt-var curve equals rated voltage).

        avg. The average terminal voltage recorded over a certain number of prior power-flow solutions.
        with the avg setting, 1.0 per unit on the x-axis of the volt-var curve(s) corresponds to the average voltage.
        from a certain number of prior intervals.  See avgwindowlen parameter.

        ravg. Same as avg, with the exception that the avgerage terminal voltage is divided by the rated voltage.

        DSS property name: `voltage_curvex_ref`, DSS property index: 6.
        """
    )
    avgwindowlen: int | None = Field(
        description="""
        Required for VOLTVAR mode and VOLTWATT mode, and defaults to 0 seconds (0s).

        Sets the length of the averaging window over which the average PVSystem/Storage terminal voltage is calculated.

        Units are indicated by appending s, m, or h to the integer value.

        The averaging window will calculate the average PVSystem/Storage terminal voltage over the specified period of time, up to and including the last power flow solution.

        Note, if the solution stepsize is larger than the window length, then the voltage will be assumed to have been constant over the time-frame specified by the window length.

        DSS property name: `avgwindowlen`, DSS property index: 7.
        """
    )
    voltwatt_curve: str | None = Field(
        description="""
        Required for VOLTWATT mode.

        Name of the XYCurve object containing the volt-watt curve.

        Units for the x-axis are per-unit voltage, which may be in per unit of the rated voltage for the PVSystem/Storage, or may be in per unit of the average voltage at the terminals over a user-defined number of prior solutions.

        Units for the y-axis are either in one of the options described in the VoltwattYAxis property.

        DSS property name: `voltwatt_curve`, DSS property index: 8.
        """
    )
    DbVMin: float | None = Field(
        description="""
        Required for the dynamic reactive current mode (DYNAMICREACCURR), and defaults to 0.95 per-unit voltage (referenced to the PVSystem/Storage object rated voltage or a windowed average value).

        This parameter is the minimum voltage that defines the voltage dead-band within which no reactive power is allowed to be generated.

        DSS property name: `DbVMin`, DSS property index: 9.
        """
    )
    DbVMax: float | None = Field(
        description="""
        Required for the dynamic reactive current mode (DYNAMICREACCURR), and defaults to 1.05 per-unit voltage (referenced to the PVSystem object rated voltage or a windowed average value).

        This parameter is the maximum voltage that defines the voltage dead-band within which no reactive power is allowed to be generated.

        DSS property name: `DbVMax`, DSS property index: 10.
        """
    )
    ArGraLowV: float | None = Field(
        description="""
        Required for the dynamic reactive current mode (DYNAMICREACCURR), and defaults to 0.1

        This is a gradient, expressed in unit-less terms of %/%, to establish the ratio by which percentage capacitive reactive power production is increased as the  percent delta-voltage decreases below DbVMin.

        Percent delta-voltage is defined as the present PVSystem/Storage terminal voltage minus the moving average voltage, expressed as a percentage of the rated voltage for the PVSystem/Storage object.

        Note, the moving average voltage for the dynamic reactive current mode is different than the moving average voltage for the volt-watt and volt-var modes.

        DSS property name: `ArGraLowV`, DSS property index: 11.
        """
    )
    ArGraHiV: float | None = Field(
        description="""
        Required for the dynamic reactive current mode (DYNAMICREACCURR), and defaults to 0.1

        This is a gradient, expressed in unit-less terms of %/%, to establish the ratio by which percentage inductive reactive power production is increased as the  percent delta-voltage decreases above DbVMax.

        Percent delta-voltage is defined as the present PVSystem/Storage terminal voltage minus the moving average voltage, expressed as a percentage of the rated voltage for the PVSystem/Storage object.

        Note, the moving average voltage for the dynamic reactive current mode is different than the mmoving average voltage for the volt-watt and volt-var modes.

        DSS property name: `ArGraHiV`, DSS property index: 12.
        """
    )
    DynReacavgwindowlen: int | None = Field(
        description="""
        Required for the dynamic reactive current mode (DYNAMICREACCURR), and defaults to 1 seconds (1s). do not use a value smaller than 1.0

        Sets the length of the averaging window over which the average PVSystem/Storage terminal voltage is calculated for the dynamic reactive current mode.

        Units are indicated by appending s, m, or h to the integer value.

        Typically this will be a shorter averaging window than the volt-var and volt-watt averaging window.

        The averaging window will calculate the average PVSystem/Storage terminal voltage over the specified period of time, up to and including the last power flow solution.  Note, if the solution stepsize is larger than the window length, then the voltage will be assumed to have been constant over the time-frame specified by the window length.

        DSS property name: `DynReacavgwindowlen`, DSS property index: 13.
        """
    )
    deltaQ_Factor: float | None = Field(
        description="""
        Required for the VOLTVAR and DYNAMICREACCURR modes.  Defaults to -1.0.

        Defining -1.0, OpenDSS takes care internally of delta_Q itself. It tries to improve convergence as well as speed up process

        Sets the maximum change (in per unit) from the prior var output level to the desired var output level during each control iteration.


        if numerical instability is noticed in solutions such as var sign changing from one control iteration to the next and voltages oscillating between two values with some separation, this is an indication of numerical instability (use the EventLog to diagnose).

        if the maximum control iterations are exceeded, and no numerical instability is seen in the EventLog of via monitors, then try increasing the value of this parameter to reduce the number of control iterations needed to achieve the control criteria, and move to the power flow solution.

        When operating the controller using expoenential control model (see CtrlModel), this parameter represents the sampling time gain of the controller, which is used for accelrating the controller response in terms of control iterations required.

        DSS property name: `deltaQ_Factor`, DSS property index: 14.
        """
    )
    VoltageChangeTolerance: float | None = Field(
        description="""
        Defaults to 0.0001 per-unit voltage.  This parameter should only be modified by advanced users of the InvControl.

        Tolerance in pu of the control loop convergence associated to the monitored voltage in pu. This value is compared with the difference of the monitored voltage in pu of the current and previous control iterations of the control loop

        This voltage tolerance value plus the var/watt tolerance value (VarChangeTolerance/ActivePChangeTolerance) determine, together, when to stop control iterations by the InvControl.

        If an InvControl is controlling more than one PVSystem/Storage, each PVSystem/Storage has this quantity calculated independently, and so an individual PVSystem/Storage may reach the tolerance within different numbers of control iterations.

        DSS property name: `VoltageChangeTolerance`, DSS property index: 15.
        """
    )
    VarChangeTolerance: float | None = Field(
        description="""
        Required for VOLTVAR and DYNAMICREACCURR modes.  Defaults to 0.025 per unit of the base provided or absorbed reactive power described in the RefReactivePower property This parameter should only be modified by advanced users of the InvControl.

        Tolerance in pu of the convergence of the control loop associated with reactive power. For the same control iteration, this value is compared to the difference, as an absolute value (without sign), between the desired reactive power value in pu and the output reactive power in pu of the controlled element.

        This reactive power tolerance value plus the voltage tolerance value (VoltageChangeTolerance) determine, together, when to stop control iterations by the InvControl.

        If an InvControl is controlling more than one PVSystem/Storage, each PVSystem/Storage has this quantity calculated independently, and so an individual PVSystem/Storage may reach the tolerance within different numbers of control iterations.

        DSS property name: `VarChangeTolerance`, DSS property index: 16.
        """
    )
    VoltwattYAxis: str | None = Field(
        description="""
        Required for VOLTWATT mode.  Must be one of: {PMPPPU* | PAVAILABLEPU| PCTPMPPPU | KVARATINGPU}.  The default is PMPPPU.

        Units for the y-axis of the volt-watt curve while in volt-watt mode.

        When set to PMPPPU. The y-axis corresponds to the value in pu of Pmpp property of the PVSystem.

        When set to PAVAILABLEPU. The y-axis corresponds to the value in pu of the available active power of the PVSystem.

        When set to PCTPMPPPU. The y-axis corresponds to the value in pu of the power Pmpp multiplied by 1/100 of the %Pmpp property of the PVSystem.

        When set to KVARATINGPU. The y-axis corresponds to the value in pu of the kVA property of the PVSystem.

        DSS property name: `VoltwattYAxis`, DSS property index: 17.
        """
    )
    RateofChangeMode: str | None = Field(
        description="""
        Required for VOLTWATT and VOLTVAR mode.  Must be one of: {INACTIVE* | LPF | RISEFALL }.  The default is INACTIVE.

        Auxiliary option that aims to limit the changes of the desired reactive power and the active power limit between time steps, the alternatives are listed below:

        INACTIVE. It indicates there is no limit on rate of change imposed for either active or reactive power output.

        LPF. A low-pass RC filter is applied to the desired reactive power and/or the active power limit to determine the output power as a function of a time constant defined in the LPFTau property.

        RISEFALL. A rise and fall limit in the change of active and/or reactive power expressed in terms of pu power per second, defined in the RiseFallLimit, is applied to the desired reactive power and/or the active power limit.

        DSS property name: `RateofChangeMode`, DSS property index: 18.
        """
    )
    LPFTau: float | None = Field(
        description="""
        Not required. Defaults to 0 seconds.

        Filter time constant of the LPF option of the RateofChangeMode property. The time constant will cause the low-pass filter to achieve 95% of the target value in 3 time constants.

        DSS property name: `LPFTau`, DSS property index: 19.
        """
    )
    RiseFallLimit: float | None = Field(
        description="""
        Not required.  Defaults to no limit (-1). Must be -1 (no limit) or a positive value.

        Limit in power in pu per second used by the RISEFALL option of the RateofChangeMode property.The base value for this ramp is defined in the RefReactivePower property and/or in VoltwattYAxis.

        DSS property name: `RiseFallLimit`, DSS property index: 20.
        """
    )
    deltaP_Factor: float | None = Field(
        description="""
        Required for the VOLTWATT modes.  Defaults to -1.0.

        Defining -1.0, OpenDSS takes care internally of delta_P itself. It tries to improve convergence as well as speed up process

        Defining between 0.05 and 1.0, it sets the maximum change (in unit of the y-axis) from the prior active power output level to the desired active power output level during each control iteration.


        If numerical instability is noticed in solutions such as active power changing substantially from one control iteration to the next and/or voltages oscillating between two values with some separation, this is an indication of numerical instability (use the EventLog to diagnose).

        If the maximum control iterations are exceeded, and no numerical instability is seen in the EventLog of via monitors, then try increasing the value of this parameter to reduce the number of control iterations needed to achieve the control criteria, and move to the power flow solution.

        DSS property name: `deltaP_Factor`, DSS property index: 21.
        """
    )
    EventLog: bool | None = Field(
        description="""
        {Yes/True | No/False*} Default is NO for InvControl. Log control actions to Eventlog.

        DSS property name: `EventLog`, DSS property index: 22.
        """
    )
    RefReactivePower: str | None = Field(
        description="""
        Required for any mode that has VOLTVAR, DYNAMICREACCURR and WATTVAR. Defaults to VARAVAL.

        Defines the base reactive power for both the provided and absorbed reactive power, according to one of the following options:

        VARAVAL. The base values for the provided and absorbed reactive power are equal to the available reactive power.

        VARMAX: The base values of the provided and absorbed reactive power are equal to the value defined in the kvarMax and kvarMaxAbs properties, respectively.

        DSS property name: `RefReactivePower`, DSS property index: 23.
        """
    )
    ActivePChangeTolerance: float | None = Field(
        description="""
        Required for VOLTWATT. Default is 0.01

        Tolerance in pu of the convergence of the control loop associated with active power. For the same control iteration, this value is compared to the difference between the active power limit in pu resulted from the convergence process and the one resulted from the volt-watt function.

        This reactive power tolerance value plus the voltage tolerance value (VoltageChangeTolerance) determine, together, when to stop control iterations by the InvControl.

        If an InvControl is controlling more than one PVSystem/Storage, each PVSystem/Storage has this quantity calculated independently, and so an individual PVSystem/Storage may reach the tolerance within different numbers of control iterations.

        DSS property name: `ActivePChangeTolerance`, DSS property index: 24.
        """
    )
    monVoltageCalc: str | None = Field(
        description="""
        Number of the phase being monitored or one of {AVG | MAX | MIN} for all phases. Default=AVG.

        DSS property name: `monVoltageCalc`, DSS property index: 25.
        """
    )
    monBus: list | None = Field(
        description="""
        Name of monitored bus used by the voltage-dependente control modes. Default is bus of the controlled PVSystem/Storage or Storage.

        DSS property name: `monBus`, DSS property index: 26.
        """
    )
    MonBusesVbase: list | None = Field(
        description="""
        Array list of rated voltages of the buses and their nodes presented in the monBus property. This list may have different line-to-line and/or line-to-ground voltages.

        DSS property name: `MonBusesVbase`, DSS property index: 27.
        """
    )
    voltwattCH_curve: str | None = Field(
        description="""
        Required for VOLTWATT mode for Storage element in CHARGING state.

        The name of an XYCurve object that describes the variation in active power output (in per unit of maximum active power outut for the Storage).

        Units for the x-axis are per-unit voltage, which may be in per unit of the rated voltage for the Storage, or may be in per unit of the average voltage at the terminals over a user-defined number of prior solutions.

        Units for the y-axis are either in: (1) per unit of maximum active power output capability of the Storage, or (2) maximum available active power output capability (defined by the parameter: VoltwattYAxis), corresponding to the terminal voltage (x-axis value in per unit).

        No default -- must be specified for VOLTWATT mode for Storage element in CHARGING state.

        DSS property name: `voltwattCH_curve`, DSS property index: 28.
        """
    )
    wattpf_curve: str | None = Field(
        description="""
        Required for WATTPF mode.

        Name of the XYCurve object containing the watt-pf curve.
        The positive values of the y-axis are positive power factor values. The negative values of the the y-axis are negative power factor values. When positive, the output reactive power has the same direction of the output active power, and when negative, it has the opposite direction.
        Units for the x-axis are per-unit output active power, and the base active power is the Pmpp for PVSystem and kWrated for Storage.

        The y-axis represents the power factor and the reference is power factor equal to 0.

        For example, if the user wants to define the following XY coordinates: (0, 0.9); (0.2, 0.9); (0.5, -0.9); (1, -0.9).
        Try to plot them considering the y-axis reference equal to unity power factor.

        The user needs to translate this curve into a plot in which the y-axis reference is equal to 0 power factor.It means that two new XY coordinates need to be included, in this case they are: (0.35, 1); (0.35, -1).
        Try to plot them considering the y-axis reference equal to 0 power factor.
        The discontinity in 0.35pu is not a problem since var is zero for either power factor equal to 1 or -1.

        DSS property name: `wattpf_curve`, DSS property index: 29.
        """
    )
    wattvar_curve: str | None = Field(
        description="""
        Required for WATTVAR mode.

        Name of the XYCurve object containing the watt-var curve. The positive values of the y-axis of the watt-var curve represent values in pu of the provided base reactive power. The negative values of the y-axis are values in pu of the absorbed base reactive power.
        Provided and absorbed base reactive power values are defined in the RefReactivePower property.

        Units for the x-axis are per-unit output active power, and the base active power is the Pmpp for PVSystem and kWrated for Storage.

        DSS property name: `wattvar_curve`, DSS property index: 30.
        """
    )
    Vsetpoint: float | None = Field(
        description="""
        Required for Active Voltage Regulation (AVR).

        DSS property name: `Vsetpoint`, DSS property index: 33.
        """
    )
    ControlModel: str | None = Field(
        description="""
        Integer defining the method for moving across the control curve. It can be one of the following:

        0 = Linear mode (default)
        1 = Exponential

        Use this property for better tunning your controller and improve the controller response in terms of control iterations needed to reach the target.
        This property alters the meaning of deltaQ_factor and deltaP_factor properties accroding to its value (Check help). The method can also be combined with the controller tolerance for improving performance.

        DSS property name: `ControlModel`, DSS property index: 34.
        """
    )
    basefreq: float | None = Field(
        description="""
        Base Frequency for ratings.

        DSS property name: `basefreq`, DSS property index: 35.
        """
    )
    enabled: bool | None = Field(
        description="""
        {Yes|No or True|False} Indicates whether this element is enabled.

        DSS property name: `enabled`, DSS property index: 36.
        """
    )

    @root_validator(pre=True)
    def drop_fields(cls, values):
        """Removes undesired fields."""
        return values


class ExpControl(OpenDssElementBaseModel):
    """None"""

    PVSystemList: list | None = Field(
        description="""
        Array list of PVSystems to be controlled.

        If not specified, all PVSystems in the circuit are assumed to be controlled by this ExpControl.

        DSS property name: `PVSystemList`, DSS property index: 1.
        """
    )
    Vreg: float | None = Field(
        description="""
        Per-unit voltage at which reactive power is zero; defaults to 1.0.

        This may dynamically self-adjust when VregTau > 0, limited by VregMin and VregMax.If imput as 0, Vreg will be initialized from a snapshot solution with no inverter Q.The equilibrium point of reactive power is also affected by Qbias

        DSS property name: `Vreg`, DSS property index: 2.
        """
    )
    Slope: float | None = Field(
        description="""
        Per-unit reactive power injection / per-unit voltage deviation from Vreg; defaults to 50.

        Unlike InvControl, base reactive power is constant at the inverter kva rating.

        DSS property name: `Slope`, DSS property index: 3.
        """
    )
    VregTau: float | None = Field(
        description="""
        Time constant for adaptive Vreg. Defaults to 1200 seconds.

        When the control injects or absorbs reactive power due to a voltage deviation from the Q=0 crossing of the volt-var curve, the Q=0 crossing will move toward the actual terminal voltage with this time constant. Over time, the effect is to gradually bring inverter reactive power to zero as the grid voltage changes due to non-solar effects. If zero, then Vreg stays fixed. IEEE1547-2018 requires adjustability from 300s to 5000s

        DSS property name: `VregTau`, DSS property index: 4.
        """
    )
    Qbias: float | None = Field(
        description="""
        Equilibrium per-unit reactive power when V=Vreg; defaults to 0.

        Enter > 0 for lagging (capacitive) bias, < 0 for leading (inductive) bias.

        DSS property name: `Qbias`, DSS property index: 5.
        """
    )
    VregMin: float | None = Field(
        description="""
        Lower limit on adaptive Vreg; defaults to 0.95 per-unit

        DSS property name: `VregMin`, DSS property index: 6.
        """
    )
    VregMax: float | None = Field(
        description="""
        Upper limit on adaptive Vreg; defaults to 1.05 per-unit

        DSS property name: `VregMax`, DSS property index: 7.
        """
    )
    QmaxLead: float | None = Field(
        description="""
        Limit on leading (inductive) reactive power injection, in per-unit of base kva; defaults to 0.44.For Category A inverters per P1547/D7, set this value to 0.25.

        Regardless of QmaxLead, the reactive power injection is still limited by dynamic headroom when actual real power output exceeds 0%

        DSS property name: `QmaxLead`, DSS property index: 8.
        """
    )
    QmaxLag: float | None = Field(
        description="""
        Limit on lagging (capacitive) reactive power injection, in per-unit of base kva; defaults to 0.44.

        For Category A inverters per P1547/D7, set this value to 0.25.Regardless of QmaxLag, the reactive power injection is still limited by dynamic headroom when actual real power output exceeds 0%

        DSS property name: `QmaxLag`, DSS property index: 9.
        """
    )
    EventLog: bool | None = Field(
        description="""
        {Yes/True* | No/False} Default is No for ExpControl. Log control actions to Eventlog.

        DSS property name: `EventLog`, DSS property index: 10.
        """
    )
    DeltaQ_factor: float | None = Field(
        description="""
        Convergence parameter; Defaults to 0.7.

        Sets the maximum change (in per unit) from the prior var output level to the desired var output level during each control iteration. If numerical instability is noticed in solutions such as var sign changing from one control iteration to the next and voltages oscillating between two values with some separation, this is an indication of numerical instability (use the EventLog to diagnose). If the maximum control iterations are exceeded, and no numerical instability is seen in the EventLog of via monitors, then try increasing the value of this parameter to reduce the number of control iterations needed to achieve the control criteria, and move to the power flow solution.

        DSS property name: `DeltaQ_factor`, DSS property index: 11.
        """
    )
    PreferQ: bool | None = Field(
        description="""
        {Yes/True* | No/False} Default is No for ExpControl.

        Curtails real power output as needed to meet the reactive power requirement. IEEE1547-2018 requires Yes, but the default is No for backward compatibility of OpenDSS models.

        DSS property name: `PreferQ`, DSS property index: 12.
        """
    )
    Tresponse: float | None = Field(
        description="""
        Open-loop response time for changes in Q.

        The value of Q reaches 90% of the target change within Tresponse, which corresponds to a low-pass filter having tau = Tresponse / 2.3026. The behavior is similar to LPFTAU in InvControl, but here the response time is input instead of the time constant. IEEE1547-2018 default is 10s for Catagory A and 5s for Category B, adjustable from 1s to 90s for both categories. However, the default is 0 for backward compatibility of OpenDSS models.

        DSS property name: `Tresponse`, DSS property index: 13.
        """
    )
    DERList: list | None = Field(
        description="""
        Alternative to PVSystemList for CIM export and import.

        However, storage is not actually implemented yet. Use fully qualified PVSystem names.

        DSS property name: `DERList`, DSS property index: 14.
        """
    )
    basefreq: float | None = Field(
        description="""
        Base Frequency for ratings.

        DSS property name: `basefreq`, DSS property index: 15.
        """
    )
    enabled: bool | None = Field(
        description="""
        {Yes|No or True|False} Indicates whether this element is enabled.

        DSS property name: `enabled`, DSS property index: 16.
        """
    )

    @root_validator(pre=True)
    def drop_fields(cls, values):
        """Removes undesired fields."""
        return values


class GICLine(OpenDssElementBaseModel):
    """None"""

    bus1: str | None = Field(
        description="""
        Name of bus to which the main terminal (1) is connected.
        bus1=busname
        bus1=busname.1.2.3

        DSS property name: `bus1`, DSS property index: 1.
        """
    )
    bus2: str | None = Field(
        description="""
        Name of bus to which 2nd terminal is connected.
        bus2=busname
        bus2=busname.1.2.3

        No Default; must be specified.

        DSS property name: `bus2`, DSS property index: 2.
        """
    )
    Volts: float | None = Field(
        description="""
        Voltage magnitude, in volts, of the GIC voltage induced across this line. When spedified, voltage source is assumed defined by Voltage and Angle properties.

        Specify this value

        OR

        EN, EE, lat1, lon1, lat2, lon2.

        Not both!!  Last one entered will take precedence. Assumed identical in each phase of the Line object.

        DSS property name: `Volts`, DSS property index: 3.
        """
    )
    Angle: float | None = Field(
        description="""
        Phase angle in degrees of first phase. Default=0.0.  See Voltage property

        DSS property name: `Angle`, DSS property index: 4.
        """
    )
    frequency: float | None = Field(
        description="""
        Source frequency.  Defaults to 0.1 Hz.

        DSS property name: `frequency`, DSS property index: 5.
        """
    )
    phases: int | None = Field(
        description="""
        Number of phases.  Defaults to 3.

        DSS property name: `phases`, DSS property index: 6.
        """
    )
    R: float | None = Field(
        description="""
        Resistance of line, ohms of impedance in series with GIC voltage source.

        DSS property name: `R`, DSS property index: 7.
        """
    )
    X: float | None = Field(
        description="""
        Reactance at base frequency, ohms. Default = 0.0. This value is generally not important for GIC studies but may be used if desired.

        DSS property name: `X`, DSS property index: 8.
        """
    )
    C: float | None = Field(
        description="""
        Value of line blocking capacitance in microfarads. Default = 0.0, implying that there is no line blocking capacitor.

        DSS property name: `C`, DSS property index: 9.
        """
    )
    EN: float | None = Field(
        description="""
        Northward Electric field (V/km). If specified, Voltage and Angle are computed from EN, EE, lat and lon values.

        DSS property name: `EN`, DSS property index: 10.
        """
    )
    EE: float | None = Field(
        description="""
        Eastward Electric field (V/km).  If specified, Voltage and Angle are computed from EN, EE, lat and lon values.

        DSS property name: `EE`, DSS property index: 11.
        """
    )
    Lat1: float | None = Field(
        description="""
        Latitude of Bus1 (degrees)

        DSS property name: `Lat1`, DSS property index: 12.
        """
    )
    Lon1: float | None = Field(
        description="""
        Longitude of Bus1 (degrees)

        DSS property name: `Lon1`, DSS property index: 13.
        """
    )
    Lat2: float | None = Field(
        description="""
        Latitude of Bus2 (degrees)

        DSS property name: `Lat2`, DSS property index: 14.
        """
    )
    Lon2: float | None = Field(
        description="""
        Longitude of Bus2 (degrees)

        DSS property name: `Lon2`, DSS property index: 15.
        """
    )
    spectrum: str | None = Field(
        description="""
        Inherited Property for all PCElements. Name of harmonic spectrum for this source.  Default is "defaultvsource", which is defined when the DSS starts.

        DSS property name: `spectrum`, DSS property index: 16.
        """
    )
    basefreq: float | None = Field(
        description="""
        Inherited Property for all PCElements. Base frequency for specification of reactance value.

        DSS property name: `basefreq`, DSS property index: 17.
        """
    )
    enabled: bool | None = Field(
        description="""
        {Yes|No or True|False} Indicates whether this element is enabled.

        DSS property name: `enabled`, DSS property index: 18.
        """
    )

    @root_validator(pre=True)
    def drop_fields(cls, values):
        """Removes undesired fields."""
        return values


class GICTransformer(OpenDssElementBaseModel):
    """None"""

    BusH: str | None = Field(
        description="""
        Name of High-side(H) bus. Examples:
        BusH=busname
        BusH=busname.1.2.3

        DSS property name: `BusH`, DSS property index: 1.
        """
    )
    BusNH: str | None = Field(
        description="""
        Name of Neutral bus for H, or first, winding. Defaults to all phases connected to H-side bus, node 0, if not specified and transformer type is either GSU or YY. (Shunt Wye Connection to ground reference)For Auto, this is automatically set to the X bus.

        DSS property name: `BusNH`, DSS property index: 2.
        """
    )
    BusX: str | None = Field(
        description="""
        Name of Low-side(X) bus, if type=Auto or YY.

        DSS property name: `BusX`, DSS property index: 3.
        """
    )
    BusNX: str | None = Field(
        description="""
        Name of Neutral bus for X, or Second, winding. Defaults to all phases connected to X-side bus, node 0, if not specified. (Shunt Wye Connection to ground reference)

        DSS property name: `BusNX`, DSS property index: 4.
        """
    )
    phases: int | None = Field(
        description="""
        Number of Phases. Default is 3.

        DSS property name: `phases`, DSS property index: 5.
        """
    )
    Type: str | None = Field(
        description="""
        Type of transformer: {GSU* | Auto | YY}. Default is GSU.

        DSS property name: `Type`, DSS property index: 6.
        """
    )
    R1: float | None = Field(
        description="""
        Resistance, each phase, ohms for H winding, (Series winding, if Auto). Default is 0.0001. If

        DSS property name: `R1`, DSS property index: 7.
        """
    )
    R2: float | None = Field(
        description="""
        Resistance, each phase, ohms for X winding, (Common winding, if Auto). Default is 0.0001.

        DSS property name: `R2`, DSS property index: 8.
        """
    )
    KVLL1: float | None = Field(
        description="""
        Optional. kV LL rating for H winding (winding 1). Default is 500. Required if you are going to export vars for power flow analysis or enter winding resistances in percent.

        DSS property name: `KVLL1`, DSS property index: 9.
        """
    )
    KVLL2: float | None = Field(
        description="""
        Optional. kV LL rating for X winding (winding 2). Default is 138. Required if you are going to export vars for power flow analysis or enter winding resistances in percent..

        DSS property name: `KVLL2`, DSS property index: 10.
        """
    )
    MVA: float | None = Field(
        description="""
        Optional. MVA Rating assumed Transformer. Default is 100. Used for computing vars due to GIC and winding resistances if kV and MVA ratings are specified.

        DSS property name: `MVA`, DSS property index: 11.
        """
    )
    VarCurve: str | None = Field(
        description="""
        Optional. XYCurve object name. Curve is expected as TOTAL pu vars vs pu GIC amps/phase. Vars are in pu of the MVA property. No Default value. Required only if you are going to export vars for power flow analysis. See K property.

        DSS property name: `VarCurve`, DSS property index: 12.
        """
    )
    pctR1: float | None = Field(
        alias="%r1",
        description="""
        Optional. Percent Resistance, each phase, for H winding (1), (Series winding, if Auto). Default is 0.2.

        Alternative way to enter R1 value. It is the actual resistances in ohmns that matter. MVA and kV should be specified.

        DSS property name: `%R1`, DSS property index: 13.
        """,
    )
    pctR2: float | None = Field(
        alias="%r2",
        description="""
        Optional. Percent Resistance, each phase, for X winding (2), (Common winding, if Auto). Default is 0.2.

        Alternative way to enter R2 value. It is the actual resistances in ohms that matter. MVA and kV should be specified.

        DSS property name: `%R2`, DSS property index: 14.
        """,
    )
    K: float | None = Field(
        description="""
        Mvar K factor. Default way to convert GIC Amps in H winding (winding 1) to Mvar. Default is 2.2. Commonly-used simple multiplier for estimating Mvar losses for power flow analysis.

        Mvar = K * kvLL * GIC per phase / 1000

        Mutually exclusive with using the VarCurve property and pu curves.If you specify this (default), VarCurve is ignored.

        DSS property name: `K`, DSS property index: 15.
        """
    )
    normamps: float | None = Field(
        description="""
        Normal rated current.

        DSS property name: `normamps`, DSS property index: 16.
        """
    )
    emergamps: float | None = Field(
        description="""
        Maximum or emerg current.

        DSS property name: `emergamps`, DSS property index: 17.
        """
    )
    faultrate: float | None = Field(
        description="""
        Failure rate per year.

        DSS property name: `faultrate`, DSS property index: 18.
        """
    )
    pctperm: float | None = Field(
        description="""
        Percent of failures that become permanent.

        DSS property name: `pctperm`, DSS property index: 19.
        """
    )
    repair: float | None = Field(
        description="""
        Hours to repair.

        DSS property name: `repair`, DSS property index: 20.
        """
    )
    basefreq: float | None = Field(
        description="""
        Base Frequency for ratings.

        DSS property name: `basefreq`, DSS property index: 21.
        """
    )
    enabled: bool | None = Field(
        description="""
        {Yes|No or True|False} Indicates whether this element is enabled.

        DSS property name: `enabled`, DSS property index: 22.
        """
    )

    @root_validator(pre=True)
    def drop_fields(cls, values):
        """Removes undesired fields."""
        return values


class VSConverter(OpenDssElementBaseModel):
    """None"""

    phases: int | None = Field(
        description="""
        Number of AC plus DC conductors. Default is 4. AC phases numbered before DC conductors.

        DSS property name: `phases`, DSS property index: 1.
        """
    )
    Bus1: str | None = Field(
        description="""
        Name of converter bus, containing both AC and DC conductors. Bus2 is always ground.

        DSS property name: `Bus1`, DSS property index: 2.
        """
    )
    kVac: float | None = Field(
        description="""
        Nominal AC line-neutral voltage in kV. Must be specified > 0.

        DSS property name: `kVac`, DSS property index: 3.
        """
    )
    kVdc: float | None = Field(
        description="""
        Nominal DC voltage in kV. Must be specified > 0.

        DSS property name: `kVdc`, DSS property index: 4.
        """
    )
    kW: float | None = Field(
        description="""
        Nominal converter power in kW. Must be specified > 0.

        DSS property name: `kW`, DSS property index: 5.
        """
    )
    Ndc: int | None = Field(
        description="""
        Number of DC conductors. Default is 1. DC conductors numbered after AC phases.

        DSS property name: `Ndc`, DSS property index: 6.
        """
    )
    Rac: float | None = Field(
        description="""
        AC resistance (ohms) for the converter transformer, plus any series reactors. Default is 0.
        Must be 0 for Vac control mode.

        DSS property name: `Rac`, DSS property index: 7.
        """
    )
    Xac: float | None = Field(
        description="""
        AC reactance (ohms) for the converter transformer, plus any series reactors. Default is 0.
        Must be 0 for Vac control mode. Must be >0 for PacVac, PacQac or VacVdc control mode.

        DSS property name: `Xac`, DSS property index: 8.
        """
    )
    m0: float | None = Field(
        description="""
        Fixed or initial value of the modulation index. Default is 0.5.

        DSS property name: `m0`, DSS property index: 9.
        """
    )
    d0: float | None = Field(
        description="""
        Fixed or initial value of the power angle in degrees. Default is 0.

        DSS property name: `d0`, DSS property index: 10.
        """
    )
    Mmin: float | None = Field(
        description="""
        Minimum value of modulation index. Default is 0.1.

        DSS property name: `Mmin`, DSS property index: 11.
        """
    )
    Mmax: float | None = Field(
        description="""
        Maximum value of modulation index. Default is 0.9.

        DSS property name: `Mmax`, DSS property index: 12.
        """
    )
    Iacmax: float | None = Field(
        description="""
        Maximum value of AC line current, per-unit of nominal. Default is 2.

        DSS property name: `Iacmax`, DSS property index: 13.
        """
    )
    Idcmax: float | None = Field(
        description="""
        Maximum value of DC current, per-unit of nominal. Default is 2.

        DSS property name: `Idcmax`, DSS property index: 14.
        """
    )
    Vacref: float | None = Field(
        description="""
        Reference AC line-to-neutral voltage, RMS Volts. Default is 0.
        Applies to PacVac and VdcVac control modes, influencing m.

        DSS property name: `Vacref`, DSS property index: 15.
        """
    )
    Pacref: float | None = Field(
        description="""
        Reference total AC real power, Watts. Default is 0.
        Applies to PacVac and PacQac control modes, influencing d.

        DSS property name: `Pacref`, DSS property index: 16.
        """
    )
    Qacref: float | None = Field(
        description="""
        Reference total AC reactive power, Vars. Default is 0.
        Applies to PacQac and VdcQac control modes, influencing m.

        DSS property name: `Qacref`, DSS property index: 17.
        """
    )
    Vdcref: float | None = Field(
        description="""
        Reference DC voltage, Volts. Default is 0.
        Applies to VdcVac control mode, influencing d.

        DSS property name: `Vdcref`, DSS property index: 18.
        """
    )
    VscMode: str | None = Field(
        description="""
        Control Mode (Fixed|PacVac|PacQac|VdcVac|VdcQac). Default is Fixed.

        DSS property name: `VscMode`, DSS property index: 19.
        """
    )
    spectrum: str | None = Field(
        description="""
        Name of harmonic spectrum for this device.

        DSS property name: `spectrum`, DSS property index: 20.
        """
    )
    basefreq: float | None = Field(
        description="""
        Base Frequency for ratings.

        DSS property name: `basefreq`, DSS property index: 21.
        """
    )
    enabled: bool | None = Field(
        description="""
        {Yes|No or True|False} Indicates whether this element is enabled.

        DSS property name: `enabled`, DSS property index: 22.
        """
    )

    @root_validator(pre=True)
    def drop_fields(cls, values):
        """Removes undesired fields."""
        return values


class Monitor(OpenDssElementBaseModel):
    """None"""

    element: str | None = Field(
        description="""
        Name (Full Object name) of element to which the monitor is connected.

        DSS property name: `element`, DSS property index: 1.
        """
    )
    terminal: int | None = Field(
        description="""
        Number of the terminal of the circuit element to which the monitor is connected. 1 or 2, typically. For monitoring states, attach monitor to terminal 1.

        DSS property name: `terminal`, DSS property index: 2.
        """
    )
    mode: int | None = Field(
        description="""
        Bitmask integer designating the values the monitor is to capture:
        0 = Voltages and currents at designated terminal
        1 = Powers at designated terminal
        2 = Tap Position (Transformer Device only)
        3 = State Variables (PCElements only)
        4 = Flicker level and severity index (Pst) for voltages. No adders apply.
            Flicker level at simulation time step, Pst at 10-minute time step.
        5 = Solution variables (Iterations, etc).
        Normally, these would be actual phasor quantities from solution.
        6 = Capacitor Switching (Capacitors only)
        7 = Storage state vars (Storage device only)
        8 = All winding currents (Transformer device only)
        9 = Losses, watts and var (of monitored device)
        10 = All Winding voltages (Transformer device only)
        Normally, these would be actual phasor quantities from solution.
        11 = All terminal node voltages and line currents of monitored device
        12 = All terminal node voltages LL and line currents of monitored device
        Combine mode with adders below to achieve other results for terminal quantities:
        +16 = Sequence quantities
        +32 = Magnitude only
        +64 = Positive sequence only or avg of all phases

        Mix adder to obtain desired results. For example:
        Mode=112 will save positive sequence voltage and current magnitudes only
        Mode=48 will save all sequence voltages and currents, but magnitude only.

        DSS property name: `mode`, DSS property index: 3.
        """
    )
    residual: bool | None = Field(
        description="""
        {Yes/True | No/False} Default = No.  Include Residual cbannel (sum of all phases) for voltage and current. Does not apply to sequence quantity modes or power modes.

        DSS property name: `residual`, DSS property index: 5.
        """
    )
    VIPolar: bool | None = Field(
        description="""
        {Yes/True | No/False} Default = YES. Report voltage and current in polar form (Mag/Angle). (default)  Otherwise, it will be real and imaginary.

        DSS property name: `VIPolar`, DSS property index: 6.
        """
    )
    PPolar: bool | None = Field(
        description="""
        {Yes/True | No/False} Default = YES. Report power in Apparent power, S, in polar form (Mag/Angle).(default)  Otherwise, is P and Q

        DSS property name: `PPolar`, DSS property index: 7.
        """
    )
    basefreq: float | None = Field(
        description="""
        Base Frequency for ratings.

        DSS property name: `basefreq`, DSS property index: 8.
        """
    )
    enabled: bool | None = Field(
        description="""
        {Yes|No or True|False} Indicates whether this element is enabled.

        DSS property name: `enabled`, DSS property index: 9.
        """
    )

    @root_validator(pre=True)
    def drop_fields(cls, values):
        """Removes undesired fields."""
        return values


class EnergyMeter(OpenDssElementBaseModel):
    """None"""

    element: str | None = Field(
        description="""
        Name (Full Object name) of element to which the monitor is connected.

        DSS property name: `element`, DSS property index: 1.
        """
    )
    terminal: int | None = Field(
        description="""
        Number of the terminal of the circuit element to which the monitor is connected. 1 or 2, typically.

        DSS property name: `terminal`, DSS property index: 2.
        """
    )
    option: list | None = Field(
        description="""
        Enter a string ARRAY of any combination of the following. Options processed left-to-right:

        (E)xcess : (default) UE/EEN is estimate of energy over capacity
        (T)otal : UE/EEN is total energy after capacity exceeded
        (R)adial : (default) Treats zone as a radial circuit
        (M)esh : Treats zone as meshed network (not radial).
        (C)ombined : (default) Load UE/EEN computed from combination of overload and undervoltage.
        (V)oltage : Load UE/EEN computed based on voltage only.

        Example: option=(E, R)

        DSS property name: `option`, DSS property index: 4.
        """
    )
    kVAnormal: float | None = Field(
        description="""
        Upper limit on kVA load in the zone, Normal configuration. Default is 0.0 (ignored). Overrides limits on individual lines for overload EEN. With "LocalOnly=Yes" option, uses only load in metered branch.

        DSS property name: `kVAnormal`, DSS property index: 5.
        """
    )
    kVAemerg: float | None = Field(
        description="""
        Upper limit on kVA load in the zone, Emergency configuration. Default is 0.0 (ignored). Overrides limits on individual lines for overload UE. With "LocalOnly=Yes" option, uses only load in metered branch.

        DSS property name: `kVAemerg`, DSS property index: 6.
        """
    )
    peakcurrent: list | None = Field(
        description="""
        ARRAY of current magnitudes representing the peak currents measured at this location for the load allocation function.  Default is (400, 400, 400). Enter one current for each phase

        DSS property name: `peakcurrent`, DSS property index: 7.
        """
    )
    Zonelist: list | None = Field(
        description="""
        ARRAY of full element names for this meter's zone.  Default is for meter to find it's own zone. If specified, DSS uses this list instead.  Can access the names in a single-column text file.  Examples:

        zonelist=[line.L1, transformer.T1, Line.L3]
        zonelist=(file=branchlist.txt)

        DSS property name: `Zonelist`, DSS property index: 8.
        """
    )
    LocalOnly: bool | None = Field(
        description="""
        {Yes | No}  Default is NO.  If Yes, meter considers only the monitored element for EEN and UE calcs.  Uses whole zone for losses.

        DSS property name: `LocalOnly`, DSS property index: 9.
        """
    )
    Mask: list | None = Field(
        description="""
        Mask for adding registers whenever all meters are totalized.  Array of floating point numbers representing the multiplier to be used for summing each register from this meter. Default = (1, 1, 1, 1, ... ).  You only have to enter as many as are changed (positional). Useful when two meters monitor same energy, etc.

        DSS property name: `Mask`, DSS property index: 10.
        """
    )
    Losses: bool | None = Field(
        description="""
        {Yes | No}  Default is YES. Compute Zone losses. If NO, then no losses at all are computed.

        DSS property name: `Losses`, DSS property index: 11.
        """
    )
    LineLosses: bool | None = Field(
        description="""
        {Yes | No}  Default is YES. Compute Line losses. If NO, then none of the losses are computed.

        DSS property name: `LineLosses`, DSS property index: 12.
        """
    )
    XfmrLosses: bool | None = Field(
        description="""
        {Yes | No}  Default is YES. Compute Transformer losses. If NO, transformers are ignored in loss calculations.

        DSS property name: `XfmrLosses`, DSS property index: 13.
        """
    )
    SeqLosses: bool | None = Field(
        description="""
        {Yes | No}  Default is YES. Compute Sequence losses in lines and segregate by line mode losses and zero mode losses.

        DSS property name: `SeqLosses`, DSS property index: 14.
        """
    )
    threePhaseLosses: bool | None = Field(
        alias="3phaseLosses",
        description="""
        {Yes | No}  Default is YES. Compute Line losses and segregate by 3-phase and other (1- and 2-phase) line losses.

        DSS property name: `3phaseLosses`, DSS property index: 15.
        """,
    )
    VbaseLosses: bool | None = Field(
        description="""
        {Yes | No}  Default is YES. Compute losses and segregate by voltage base. If NO, then voltage-based tabulation is not reported.

        DSS property name: `VbaseLosses`, DSS property index: 16.
        """
    )
    PhaseVoltageReport: bool | None = Field(
        description="""
        {Yes | No}  Default is NO.  Report min, max, and average phase voltages for the zone and tabulate by voltage base. Demand Intervals must be turned on (Set Demand=true) and voltage bases must be defined for this property to take effect. Result is in a separate report file.

        DSS property name: `PhaseVoltageReport`, DSS property index: 17.
        """
    )
    Int_Rate: float | None = Field(
        description="""
        Average number of annual interruptions for head of the meter zone (source side of zone or feeder).

        DSS property name: `Int_Rate`, DSS property index: 18.
        """
    )
    Int_Duration: float | None = Field(
        description="""
        Average annual duration, in hr, of interruptions for head of the meter zone (source side of zone or feeder).

        DSS property name: `Int_Duration`, DSS property index: 19.
        """
    )
    SAIFI: float | None = Field(
        description="""
        (Read only) Makes SAIFI result available via return on query (? energymeter.myMeter.SAIFI.

        DSS property name: `SAIFI`, DSS property index: 20.
        """
    )
    SAIFIkW: float | None = Field(
        description="""
        (Read only) Makes SAIFIkW result available via return on query (? energymeter.myMeter.SAIFIkW.

        DSS property name: `SAIFIkW`, DSS property index: 21.
        """
    )
    SAIDI: float | None = Field(
        description="""
        (Read only) Makes SAIDI result available via return on query (? energymeter.myMeter.SAIDI.

        DSS property name: `SAIDI`, DSS property index: 22.
        """
    )
    CAIDI: float | None = Field(
        description="""
        (Read only) Makes CAIDI result available via return on query (? energymeter.myMeter.CAIDI.

        DSS property name: `CAIDI`, DSS property index: 23.
        """
    )
    CustInterrupts: float | None = Field(
        description="""
        (Read only) Makes Total Customer Interrupts value result available via return on query (? energymeter.myMeter.CustInterrupts.

        DSS property name: `CustInterrupts`, DSS property index: 24.
        """
    )
    basefreq: float | None = Field(
        description="""
        Base Frequency for ratings.

        DSS property name: `basefreq`, DSS property index: 25.
        """
    )
    enabled: bool | None = Field(
        description="""
        {Yes|No or True|False} Indicates whether this element is enabled.

        DSS property name: `enabled`, DSS property index: 26.
        """
    )

    @root_validator(pre=True)
    def drop_fields(cls, values):
        """Removes undesired fields."""
        values.pop("action", None)
        return values


class Sensor(OpenDssElementBaseModel):
    """None"""

    element: str | None = Field(
        description="""
        Name (Full Object name) of element to which the Sensor is connected.

        DSS property name: `element`, DSS property index: 1.
        """
    )
    terminal: int | None = Field(
        description="""
        Number of the terminal of the circuit element to which the Sensor is connected. 1 or 2, typically. Default is 1.

        DSS property name: `terminal`, DSS property index: 2.
        """
    )
    kvbase: float | None = Field(
        description="""
        Voltage base for the sensor, in kV. If connected to a 2- or 3-phase terminal,
        specify L-L voltage. For 1-phase devices specify L-N or actual 1-phase voltage. Like many other DSS devices, default is 12.47kV.

        DSS property name: `kvbase`, DSS property index: 3.
        """
    )
    clear: bool | None = Field(
        description="""
        { Yes | No }. Clear=Yes clears sensor values. Should be issued before putting in a new set of measurements.

        DSS property name: `clear`, DSS property index: 4.
        """
    )
    kVs: list | None = Field(
        description="""
        Array of Voltages (kV) measured by the voltage sensor. For Delta-connected sensors, Line-Line voltages are expected. For Wye, Line-Neutral are expected.

        DSS property name: `kVs`, DSS property index: 5.
        """
    )
    currents: list | None = Field(
        description="""
        Array of Currents (amps) measured by the current sensor. Specify this or power quantities; not both.

        DSS property name: `currents`, DSS property index: 6.
        """
    )
    kWs: list | None = Field(
        description="""
        Array of Active power (kW) measurements at the sensor. Is converted into Currents along with q=[...]
        Will override any currents=[...] specification.

        DSS property name: `kWs`, DSS property index: 7.
        """
    )
    kvars: list | None = Field(
        description="""
        Array of Reactive power (kvar) measurements at the sensor. Is converted into Currents along with p=[...]

        DSS property name: `kvars`, DSS property index: 8.
        """
    )
    conn: str | None = Field(
        description="""
        Voltage sensor Connection: { wye | delta | LN | LL }.  Default is wye. Applies to voltage measurement only.
        Currents are always assumed to be line currents.
        If wye or LN, voltage is assumed measured line-neutral; otherwise, line-line.

        DSS property name: `conn`, DSS property index: 9.
        """
    )
    Deltadirection: int | None = Field(
        description="""
        {1 or -1}  Default is 1:  1-2, 2-3, 3-1.  For reverse rotation, enter -1. Any positive or negative entry will suffice.

        DSS property name: `Deltadirection`, DSS property index: 10.
        """
    )
    pctError: float | None = Field(
        alias="%error",
        description="""
        Assumed percent error in the measurement. Default is 1.

        DSS property name: `%Error`, DSS property index: 11.
        """,
    )
    Weight: float | None = Field(
        description="""
        Weighting factor: Default is 1.

        DSS property name: `Weight`, DSS property index: 12.
        """
    )
    basefreq: float | None = Field(
        description="""
        Base Frequency for ratings.

        DSS property name: `basefreq`, DSS property index: 13.
        """
    )
    enabled: bool | None = Field(
        description="""
        {Yes|No or True|False} Indicates whether this element is enabled.

        DSS property name: `enabled`, DSS property index: 14.
        """
    )

    @root_validator(pre=True)
    def drop_fields(cls, values):
        """Removes undesired fields."""
        return values
