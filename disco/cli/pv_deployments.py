import json
import click

from disco.enums import Placement
from disco.sources.source_tree_1.factory import generate_pv_deployments
from disco.sources.source_tree_1.pv_deployments import DeploymentHierarchy, ScenarioCategory

HIERARCHY_CHOICE = [item.value for item in DeploymentHierarchy]
CATEGORY_CHOICE = [item.value for item in ScenarioCategory]
PLACEMENT_CHOICE = [item.value for item in Placement]


@click.group()
def pv_deployments():
    """Generate PV deployments from raw OpenDSS models"""


@click.command()
@click.argument("input_path")
@click.option(
    "--hierarchy",
    type=click.Choice(HIERARCHY_CHOICE, case_sensitive=False),
    required=True,
    help="Choose the deployment hierarchy."
)
@click.option(
    "--placement",
    type=click.Choice(PLACEMENT_CHOICE, case_sensitive=False),
    required=True,
    help="Choose the placement type"
)
@click.option(
    "--pv-upscale",
    is_flag=True,
    default=True,
    show_default=True,
    help="Upscale PV in deployments."
)
@click.option(
  "--min-penetration",
    type=click.INT,
    default=5,
    show_default=True,
    help="The minimum level of PV penetration."
)
@click.option(
    "--max-penetration",
    type=click.INT,
    default=200,
    show_default=True,
    help="The maximum level of PV penetration."
)
@click.option(
    "--penetration-step",
    type=click.INT,
    default=5,
    show_default=5,
    help="The step of penetration level."
)
@click.option(
    "--deployment-number",
    type=click.INT,
    default=10,
    show_default=True,
    help="The number of deployments"
)
@click.option(
    "--proximity-step",
    type=click.INT,
    default=10,
    show_default=True,
    help="The proximity step in PV deployments."
)
@click.option(
    "--pv-size-pdf",
    type=click.INT,
    default=None,
    show_default=True,
    help="The PV size pdf value"
)
@click.option(
    "--category",
    type=click.Choice(CATEGORY_CHOICE, case_sensitive=False),
    default="small",
    show_default=True,
    help="The PV size pdf value"
)
@click.option(
    "--percent-shares",
    default=[100, 0],
    show_default=True,
    help="The share pair - [share of residential PVs, share of utility scale PVs]"
)
@click.option(
    "-o", "--output-path",
    type=click.Path(),
    default=None,
    required=False,
    help="PV deployments output path."
)
@click.option(
    "-v", "--verbose",
    type=click.BOOL,
    is_flag=True,
    default=False,
    show_default=True,
    help="Enable to show overbose information."
)
def source_tree_1(
    input_path,
    hierarchy,
    placement,
    pv_upscale,
    min_penetration,
    max_penetration,
    penetration_step,
    deployment_number,
    proximity_step,
    pv_size_pdf,
    category,
    percent_shares,
    output_path,
    verbose
):
    """Generate PV deployments for source tree 1."""
    deployment_config = {
        "pv_upscale": pv_upscale,
        "min_penetration": min_penetration,
        "max_penetration": max_penetration,
        "penetration_step": penetration_step,
        "deployment_number": deployment_number,
        "proximity_step": proximity_step,
        "pv_size_pdf": pv_size_pdf,
        "category": category,
        "percent_shares": [100, 0]
    }
    summary, output_path = generate_pv_deployments(
        input_path=input_path,
        hierarchy=hierarchy,
        config=deployment_config,
        output_path=output_path,
        verbose=verbose
    )
    print("PV deployments are generated in {}".format(output_path))
    print(json.dumps(summary, indent=2))


pv_deployments.add_command(source_tree_1)
