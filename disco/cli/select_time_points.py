#!/usr/bin/env python

"""
Down-selects load shape time points in the circuit based on
user-specified critical conditions.
"""

import logging
import shutil
import sys
from pathlib import Path

import click

from jade.loggers import setup_logging
from jade.utils.utils import get_cli_string

from disco.preprocess.select_timepoints2 import (
    CriticalCondition,
    DemandCategory,
    GenerationCategory,
    main,
)


logger = logging.getLogger(__name__)


@click.command()
@click.argument("master_file", type=click.Path(exists=True), callback=lambda *x: Path(x[2]))
@click.option(
    "-c",
    "--critical-conditions",
    type=click.Choice([x.value for x in CriticalCondition]),
    default=tuple(x.value for x in CriticalCondition),
    show_default=True,
    multiple=True,
    callback=lambda *x: tuple(CriticalCondition(y) for y in x[2]),
    help="critical conditions to use for time-point selection",
)
@click.option(
    "-d",
    "--demand-categories",
    type=click.Choice([x.value for x in DemandCategory]),
    default=tuple(x.value for x in DemandCategory),
    show_default=True,
    multiple=True,
    callback=lambda *x: tuple(DemandCategory(y) for y in x[2]),
    help="Demand-based devices to use in time-point selection algorithm",
)
@click.option(
    "-g",
    "--generation-categories",
    type=click.Choice([x.value for x in GenerationCategory]),
    default=tuple(x.value for x in GenerationCategory),
    show_default=True,
    multiple=True,
    callback=lambda *x: tuple(GenerationCategory(y) for y in x[2]),
    help="Generation-based devices to use in time-point selection algorithm",
)
@click.option(
    "-o",
    "--output",
    default="output_time_points",
    callback=lambda *x: Path(x[2]),
    help="Output directory",
)
@click.option(
    "--create-new-circuit/--no-create-new-circuit",
    default=True,
    is_flag=True,
    show_default=True,
    help="Create new circuit with down-selected time points.",
)
@click.option(
    "--check-power-flow/--no-check-power-flow",
    default=True,
    is_flag=True,
    show_default=True,
    help="Run power flow before and after creating new circuit and check output values.",
)
@click.option(
    "--fix-master-file/--no-fix-master-file",
    is_flag=True,
    show_default=True,
    default=False,
    help="Remove commands in the Master.dss file that interfere with time-point selection.",
)
@click.option(
    "-f",
    "--force",
    is_flag=True,
    show_default=True,
    default=False,
    help="Delete output directory if it exists.",
)
@click.option(
    "-v",
    "--verbose",
    is_flag=True,
    show_default=True,
    default=False,
    help="Enabled debug logging.",
)
def select_time_points(
    master_file,
    demand_categories,
    generation_categories,
    critical_conditions,
    output,
    create_new_circuit,
    check_power_flow,
    fix_master_file,
    force,
    verbose,
):
    """Select load shape time points in the circuit based on the specified critical conditions.

    By default, the Master.dss file is not allowed to enable time-series mode. Specify
    --fix-master-file to disable time-series mode and other disallowed parameters.

    """
    if output.exists():
        if force:
            shutil.rmtree(output)
        else:
            print(
                f"Output directory {output} exists. Choose a different path or set --force.",
                file=sys.stderr,
            )
            sys.exit(1)

    output.mkdir()
    level = logging.DEBUG if verbose else logging.INFO
    log_file = output / "disco.log"
    setup_logging("disco", log_file, console_level=level, packages=["disco"])
    logger.info(get_cli_string())
    categories = {"demand": demand_categories, "generation": generation_categories}
    main(
        master_file,
        categories=categories,
        critical_conditions=critical_conditions,
        destination_dir=output,
        create_new_circuit=create_new_circuit,
        fix_master_file=fix_master_file,
        check_power_flow=check_power_flow,
        recreate_profiles=False,
    )
