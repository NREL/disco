import click
from disco.postprocess.hosting_capacity_from_pydss import compute_hosting_capacity_for_pydss
from sqlalchemy import over


@click.command()
@click.option(
    "-j",
    "--jade-output-dir",
    help="Ouput directory after running jade runs",
)
@click.option(
    "-o",
    "--output-json",
    default="./hosting-capacity-from-pydss-results.json",
    show_default=True,
    help="Ouput directory after running jade runs",
)
@click.option(
    "-v",
    "--overvoltage-threshold",
    default=1.05,
    show_default=True,
    help="Over voltage threshold value default is 1.05 pu",
)
@click.option(
    "-t",
    "--thermal-threshold",
    default=100.0,
    show_default=True,
    help="Thermal overloading threshold default is 100.0",
)
def hosting_capacity_by_timestep(
    jade_output_dir, output_json, overvoltage_threshold, thermal_threshold
):

    """Compute hosting capacity each time step for all feeders"""
    compute_hosting_capacity_for_pydss(
        jade_output_dir, output_json, overvoltage_threshold, thermal_threshold
    )
