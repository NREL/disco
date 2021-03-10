import json
import logging

import click

from jade.loggers import setup_logging
from disco.enums import Placement
from disco.sources.source_tree_1.factory import generate_pv_deployments, list_feeder_paths, assign_pv_profiles
from disco.sources.source_tree_1.pv_deployments import DeploymentHierarchy, DeploymentCategory

HIERARCHY_CHOICE = [item.value for item in DeploymentHierarchy]
CATEGORY_CHOICE = [item.value for item in DeploymentCategory]
PLACEMENT_CHOICE = [item.value for item in Placement]


@click.group()
def pv_deployments():
    """Generate PV deployments from raw OpenDSS models"""


@click.group()
def source_tree_1():
    """Generate PV deployments from raw OpenDSS models"""


@click.command()
@click.argument("input_path")
@click.option(
    "-h", "--hierarchy",
    type=click.Choice(HIERARCHY_CHOICE, case_sensitive=False),
    required=True,
    help="Choose the deployment hierarchy."
)
@click.option(
    "-p", "--placement",
    type=click.Choice(PLACEMENT_CHOICE, case_sensitive=False),
    required=True,
    help="Choose the placement type"
)
@click.option(
    "-c", "--category",
    type=click.Choice(CATEGORY_CHOICE, case_sensitive=False),
    default=DeploymentCategory.SMALL.value,
    show_default=True,
    help="The PV size pdf value"
)
@click.option(
    "-f", "--master-filename",
    type=click.STRING,
    required=False,
    default="Master.dss",
    show_default=True,
    help="The filename of master dss"
)
@click.option(
    "-u", "--pv-upscale",
    is_flag=True,
    default=True,
    show_default=True,
    help="Upscale PV in deployments."
)
@click.option(
  "-m", "--min-penetration",
    type=click.INT,
    default=5,
    show_default=True,
    help="The minimum level of PV penetration."
)
@click.option(
    "-M", "--max-penetration",
    type=click.INT,
    default=200,
    show_default=True,
    help="The maximum level of PV penetration."
)
@click.option(
   "-s", "--penetration-step",
    type=click.INT,
    default=5,
    show_default=5,
    help="The step of penetration level."
)
@click.option(
    "-n", "--deployment-number",
    type=click.INT,
    default=10,
    show_default=True,
    help="The number of deployments"
)
@click.option(
    "-S", "--proximity-step",
    type=click.INT,
    default=10,
    show_default=True,
    help="The proximity step in PV deployments."
)
@click.option(
    "-P", "--percent-shares",
    default=[100, 0],
    show_default=True,
    help="The share pair - [share of residential PVs, share of utility scale PVs]"
)
@click.option(
    "-x", "--pv-size-pdf",
    type=click.INT,
    default=None,
    show_default=True,
    help="The PV size pdf value"
)
@click.option(
    "-v", "--verbose",
    type=click.BOOL,
    is_flag=True,
    default=False,
    show_default=True,
    help="Enable to show overbose information."
)
def deploy_pv(
    input_path,
    hierarchy,
    placement,
    category,
    master_filename,
    pv_upscale,
    min_penetration,
    max_penetration,
    penetration_step,
    deployment_number,
    proximity_step,
    percent_shares,
    pv_size_pdf,
    verbose
):
    """Generate PV deployments for source tree 1."""
    level = logging.DEBUG if verbose else logging.INFO
    setup_logging("pv_deployments", None, console_level=level)
    config = {
        "placement": placement,
        "category": category,
        "master_filename": master_filename,
        "pv_upscale": pv_upscale,
        "min_penetration": min_penetration,
        "max_penetration": max_penetration,
        "penetration_step": penetration_step,
        "deployment_number": deployment_number,
        "proximity_step": proximity_step,
        "percent_shares": [100, 0],
        "pv_size_pdf": pv_size_pdf
    }
    summary = generate_pv_deployments(
        input_path=input_path,
        hierarchy=hierarchy,
        config=config
    )
    print(json.dumps(summary, indent=2))


@click.command()
@click.argument("input_path")
@click.option(
    "-h", "--hierarchy",
    type=click.Choice(HIERARCHY_CHOICE, case_sensitive=False),
    required=True,
    help="Choose the deployment hierarchy."
)
@click.option(
    "-o", "--output-file",
    type=click.STRING,
    required=False,
    default=None,
    help="Text file for feeder paths output."
)
@click.option(
    "-v", "--verbose",
    type=click.BOOL,
    is_flag=True,
    default=False,
    show_default=True,
    help="Enable to show overbose information."
)
def list_feeders(
    input_path,
    hierarchy,
    output_file,
    verbose
):
    """List feeder paths for source tree 1."""
    level = logging.DEBUG if verbose else logging.INFO
    setup_logging("pv_deployments", None, console_level=level)
    feeder_paths = list_feeder_paths(input_path, hierarchy)
    if output_file:
        with open(output_file, "w") as f:
            data = "\n".join(feeder_paths)
            f.write(data)
        print(f"Total feeders: {len(feeder_paths)}. Output file - {output_file}." )
        return

    for feeder_path in feeder_paths:
        print(feeder_path)
    print(f"=========\nTotal feeders: {len(feeder_paths)}")


@click.command()
@click.argument("input_path")
@click.option(
    "-h", "--hierarchy",
    type=click.Choice(HIERARCHY_CHOICE, case_sensitive=False),
    required=True,
    help="Choose the deployment hierarchy."
)
@click.option(
    "-p", "--placement",
    type=click.Choice(PLACEMENT_CHOICE, case_sensitive=False),
    required=True,
    help="Choose the placement type"
)
@click.option(
    "-c", "--category",
    type=click.Choice(CATEGORY_CHOICE, case_sensitive=False),
    default=DeploymentCategory.SMALL.value,
    show_default=True,
    help="The PV size pdf value"
)
@click.option(
    "-v", "--verbose",
    type=click.BOOL,
    is_flag=True,
    default=False,
    show_default=True,
    help="Enable to show overbose information."
)
def assign_profile(input_path, hierarchy, placement, category, verbose):
    """Assign PV profiles based on PV deployments"""
    level = logging.DEBUG if verbose else logging.INFO
    setup_logging("pv_deployments", None, console_level=level)
    config_paths = assign_pv_profiles(input_path, hierarchy, placement, category)
    print(f"PV configs created! Total: {len(config_paths)}")


source_tree_1.add_command(deploy_pv)
source_tree_1.add_command(list_feeders)
source_tree_1.add_command(assign_profile)
pv_deployments.add_command(source_tree_1)
