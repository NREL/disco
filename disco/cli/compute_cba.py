import logging
import sys
import time
from pathlib import Path

import click
import pandas as pd
import numpy as np

from jade.loggers import setup_logging
import disco


LOGGER_NAME = "CBA"
logger = logging.getLogger(LOGGER_NAME)

COMM_LOAD = "Loads__Powers__commercial (kWh)"
RES_LOAD = "Loads__Powers__residential (kWh)"
PVCOMM_OUT = "PVSystems__Powers__commercial (kWh)"
PVRES_OUT = "PVSystems__Powers__residential (kWh)"
SUB_POWER = "Circuits__TotalPower (kWh)"
SUB_LOSS = "Circuits__Losses (kWh)"
PVCOMM_CURT = "PVSystems__Curtailment__commercial (kWh)"
PVRES_CURT = "PVSystems__Curtailment__residential (kWh)"
CR1 = "Commercial power ($)"
CR2 = "Residential power ($)"
CR3 = "Commercial PV ($)"
CR4 = "Residential PV ($)"
CR5 = "Substation power ($)"
CR6 = "Substation losses ($)"
CR7 = "Commercial curtailment ($)"
CR8 = "Residential curtailment ($)"

COL_LIST = [
    COMM_LOAD,
    RES_LOAD,
    PVCOMM_OUT,
    PVRES_OUT,
    SUB_POWER,
    SUB_LOSS,
    PVCOMM_CURT,
    PVRES_CURT,
]
LABEL_COLUMNS = [
    "scenario",
    "name",
    "substation",
    "feeder",
    "placement",
    "sample",
    "penetration_level",
]
COSTS_PER_HOUR_FILE = Path(disco.__path__[0]) / "analysis" / "cba_costs_per_hour.csv"


def run(powers_file: Path, costs_file: Path, output_file: Path, skipna: bool):
    """Compute cost summaries."""
    start = time.time()
    powers_df = pd.read_csv(
        powers_file,
        dtype={"sample": np.float64, "penetration_level": np.float64, "placement": str},
    )
    costs_df = pd.read_csv(costs_file)
    raw_costs = []

    for (name, scenario), df in powers_df.groupby(by=["name", "scenario"]):
        if len(df) != 8760:
            raise Exception(f"Length of DataFrame is not 8760: {name}/{scenario}: {len(df)}")

        cost_list = []
        for col in LABEL_COLUMNS:
            unique_vals = df[col].unique()
            if len(unique_vals) != 1:
                raise Exception(f"Column does not have one unique value: {col}: {unique_vals}")
            cost_list.append(df[col].values[0])
        for col in COL_LIST:
            null_count = df[col].isnull().sum()
            if null_count > 0:
                logger.warning("Column %s has %s null values. skipna=%s", col, null_count, skipna)
            result = (df[col] * costs_df[col].values).sum(skipna=skipna)
            cost_list.append(result)
        raw_costs.append(cost_list)

    columns = LABEL_COLUMNS + [CR1, CR2, CR3, CR4, CR5, CR6, CR7, CR8]
    results_df = pd.DataFrame(raw_costs, columns=columns)
    results_df.to_csv(output_file, index=False)
    logger.info(f"Created %s. Duration = %s seconds", output_file, time.time() - start)


@click.command()
@click.argument("powers-file", type=click.Path(exists=True))
@click.option(
    "-c",
    "--costs-file",
    type=click.Path(exists=True),
    default=COSTS_PER_HOUR_FILE,
    show_default=True,
    help="Path to file containing hourly cost information",
)
@click.option(
    "-o",
    "--output-file",
    type=click.Path(),
    default="cba_results.csv",
    show_default=True,
    help="Output file for results",
    callback=lambda _, __, z: Path(z),
)
@click.option(
    "--skipna/--no-skipna",
    is_flag=True,
    default=False,
    show_default=True,
    help="Skip null values when summing costs.",
)
@click.option(
    "-f",
    "--force",
    is_flag=True,
    default=False,
    show_default=True,
    help="Overwrite output file if it already exists.",
)
@click.option(
    "--verbose", is_flag=True, default=False, show_default=True, help="Enable verbose logging"
)
def compute_cba(powers_file, costs_file, output_file, skipna, force, verbose):
    """Compute Cost Benefit Analysis metrics."""
    level = logging.DEBUG if verbose else logging.INFO
    setup_logging(LOGGER_NAME, None, console_level=level, packages=["disco"])
    if output_file.exists() and not force:
        logger.error(
            "%s already exists. Pass --force to overwrite or choose a custom name.", output_file
        )
        sys.exit(1)
    run(powers_file, costs_file, output_file, skipna)
