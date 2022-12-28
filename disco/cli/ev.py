import fileinput
import logging
import os
import shutil
import sys
from pathlib import Path

import click

from jade.loggers import setup_logging
from jade.utils.utils import get_cli_string
from disco.ev.feeder_EV_HC import run
from disco import timer_stats_collector


logger = logging.getLogger(__name__)


@click.group()
def ev():
    """Run electic vehicle simulations."""


@click.command()
@click.argument("master_file", type=click.Path(exists=True), callback=lambda *x: Path(x[2]))
@click.option(
    "-l", "--lower-voltage-limit", default=0.95, type=float, help="Lower voltage limit (P.U.)"
)
@click.option(
    "-u", "--upper-voltage-limit", default=1.05, type=float, help="Upper voltage limit (P.U.)"
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
    "--extra-percentages-for-existing-overloads",
    default=(2.0,),
    type=float,
    multiple=True,
    show_default=True,
    help="Considers extra percentages for already overloaded elements",
)
@click.option(
    "-T",
    "--thermal-loading-limits",
    default=(100.0,),
    type=float,
    multiple=True,
    show_default=True,
    help="Limits for thermal overloads",
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
    "-f",
    "--force",
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
    lower_voltage_limit: float,
    upper_voltage_limit: float,
    kw_step_voltage_violation: float,
    kw_step_thermal_violation: float,
    extra_percentages_for_existing_overloads: tuple[float],
    thermal_loading_limits: tuple[float],
    export_circuit_elements: bool,
    # plot_heatmap: bool,
    output: Path,
    force: bool,
    verbose: bool,
):
    """Compute hosting capacity for a feeder."""
    if output.exists():
        if force:
            shutil.rmtree(output)
        else:
            print(
                f"output directory {output} already exists. Choose a different path or pass --force.",
                file=sys.stderr,
            )
            sys.exit(1)
    output.mkdir()

    level = logging.DEBUG if verbose else logging.INFO
    filename = output / "ev_hosting_capacity.log"
    logger = setup_logging(
        "disco", filename, console_level=level, file_level=level, packages=["disco"]
    )
    logger.info(get_cli_string())

    backup_file = master_file.with_suffix(".bk")
    shutil.copyfile(master_file, backup_file)
    with fileinput.input(files=[master_file], inplace=True) as f:
        for line in f:
            if not line.strip().lower().startswith("solve"):
                print(line, end="")
        print("Solve mode=snapshot")

    try:
        shutil.copyfile(master_file, output / "Master.dss")
        run(
            master_file,
            lower_voltage_limit,
            upper_voltage_limit,
            kw_step_voltage_violation,
            kw_step_thermal_violation,
            extra_percentages_for_existing_overloads,
            thermal_loading_limits,
            export_circuit_elements,
            output,
        )
    finally:
        os.rename(backup_file, master_file)
        timer_stats_collector.log_stats(clear=True)


ev.add_command(hosting_capacity)
