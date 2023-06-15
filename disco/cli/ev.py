import logging
import os
import shutil
import sys
from pathlib import Path

import click

from jade.loggers import setup_logging
from jade.utils.utils import get_cli_string
from disco.ev.feeder_EV_HC import run


logger = logging.getLogger(__name__)


@click.group()
def ev():
    """Run electic vehicle simulations."""


@click.command()
@click.argument("master_file", type=click.Path(exists=True), callback=lambda *x: Path(x[2]))
@click.option(
    "-c", "--num-cpus", type=int, help="Number of CPUs to use, default is all."
)
@click.option(
    "-l", "--lower-voltage-limit", default=0.95, show_default=True, type=float, help="Lower voltage limit (P.U.)"
)
@click.option(
    "-u", "--upper-voltage-limit", default=1.05, show_default=True, type=float, help="Upper voltage limit (P.U.)"
)
@click.option(
    "-v",
    "--kw-step-voltage-violation",
    default=10.0,
    type=float,
    show_default=True,
    help="kW step value for detecting a voltage violation",
)
@click.option(
    "-t",
    "--kw-step-thermal-violation",
    default=10.0,
    type=float,
    show_default=True,
    help="kW step value for detecting a thermal violation",
)
@click.option(
    "-e",
    "--extra-percentage-for-existing-overloads",
    default=2.0,
    type=float,
    show_default=True,
    help="Considers extra percentage for already overloaded elements",
)
@click.option(
    "-T",
    "--thermal-loading-limit",
    default=100.0,
    type=float,
    show_default=True,
    help="Limit for thermal overloads",
)
@click.option(
    "--thermal-tolerance",
    type=float,
    help="Tolerance to use when finding lowest thermal violations. Uses --kw-step-thermal-violation by default",
)
@click.option(
    "--voltage-tolerance",
    type=float,
    help="Tolerance to use when finding lowest voltage violations. Uses --kw-step-voltage-violation by default",
)
@click.option(
    "--export-circuit-elements/--no-export-circuit-elements",
    default=False,
    show_default=True,
    help="Export rated values for all circuit elements",
)
# TODO: not implemented
# @click.option(
#    "--plot-heatmap/--no-plot-heatmap",
#    default=False,
#    show_default=True,
#    help="Plot heatmap for hosting capacity",
# )
@click.option(
    "-o",
    "--output",
    default="output",
    show_default=True,
    callback=lambda *x: Path(x[2]),
    help="Output directory",
)
@click.option(
    "--overwrite",
    is_flag=True,
    default=False,
    show_default=True,
    help="Overwrite output directory if it already exists.",
)
@click.option(
    "--verbose",
    is_flag=True,
    default=False,
    help="Enable debug logging",
)
def hosting_capacity(
    master_file: Path,
    num_cpus: int | None,
    lower_voltage_limit: float,
    upper_voltage_limit: float,
    kw_step_voltage_violation: float,
    kw_step_thermal_violation: float,
    extra_percentage_for_existing_overloads: float,
    thermal_loading_limit: float,
    voltage_tolerance: float,
    thermal_tolerance: float,
    export_circuit_elements: bool,
    # plot_heatmap: bool,
    output: Path,
    overwrite: bool,
    verbose: bool,
):
    """Compute hosting capacity for a feeder."""
    if output.exists():
        if overwrite:
            shutil.rmtree(output)
        else:
            print(
                f"{output} already exists. Choose a different path or pass --overwrite.",
                file=sys.stderr,
            )
            sys.exit(1)
    output.mkdir()
    thermal_tolerance = thermal_tolerance or kw_step_thermal_violation
    voltage_tolerance = voltage_tolerance or kw_step_voltage_violation

    level = logging.DEBUG if verbose else logging.INFO
    filename = output / "ev_hosting_capacity.log"
    logger = setup_logging(
        "disco", filename, console_level=level, file_level=level, packages=["disco"]
    )
    logger.info(get_cli_string())

    run(
        master_file=master_file,
        lower_voltage_limit=lower_voltage_limit,
        upper_voltage_limit=upper_voltage_limit,
        kw_step_voltage_violation=kw_step_voltage_violation,
        voltage_tolerance=voltage_tolerance,
        kw_step_thermal_violation=kw_step_thermal_violation,
        thermal_tolerance=thermal_tolerance,
        extra_percentage_for_existing_overloads=extra_percentage_for_existing_overloads,
        thermal_loading_limit=thermal_loading_limit,
        export_circuit_elements=export_circuit_elements,
        output_dir=output,
        num_cpus=num_cpus,
    )


ev.add_command(hosting_capacity)
