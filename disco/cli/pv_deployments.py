import json
import logging
import random
import sys
from types import SimpleNamespace

import click

from jade.loggers import setup_logging
from disco.enums import Placement
from disco.sources.base import DEFAULT_PV_DEPLOYMENTS_DIRNAME
from disco.sources.source_tree_1.pv_deployments import (
    DeploymentHierarchy,
    DeploymentCategory,
    PVDataStorage,
    PVDataManager,
    PVDeploymentManager,
    PVConfigManager
)

HIERARCHY_CHOICE = [item.value for item in DeploymentHierarchy]
CATEGORY_CHOICE = [item.value for item in DeploymentCategory]
PLACEMENT_CHOICE = [item.value for item in Placement]

logger = logging.getLogger(__name__)


def create_pv_deployments(input_path: str, hierarchy: str, config: dict):
    """A method for generating pv deployments"""
    hierarchy = DeploymentHierarchy(hierarchy)
    config = SimpleNamespace(**config)
    if not config.placement:
        print(f"'-p' or '--placement' should not be None for this action, choose from {PLACEMENT_CHOICE}")
        sys.exit()
    manager = PVDeploymentManager(input_path, hierarchy, config)
    summary = manager.generate_pv_deployments()
    print(json.dumps(summary, indent=2))


def create_pv_configs(input_path: str, hierarchy: str, config: dict, control_name: str, limit: int):
    """A method for generating pv config JSON files """
    hierarchy = DeploymentHierarchy(hierarchy)
    config = SimpleNamespace(**config)
    if config.placement:
        config.placement = None
        print(f"'-p' or '--placement' option is ignored for this action.")
    
    manager = PVConfigManager(input_path, hierarchy, config)
    config_files = manager.generate_pv_configs(control_name=control_name, limit=limit)
    print(f"PV configs created! Total: {len(config_files)}")


def remove_pv_deployments(input_path: str, hierarchy: str, config: dict):
    """A method for removing deployed pv systems"""
    hierarchy = DeploymentHierarchy(hierarchy)
    config = SimpleNamespace(**config)
    manager = PVDeploymentManager(input_path, hierarchy, config)
    if config.placement:
        placement = Placement(config.placement)
    else:
        placement = config.placement
    result = manager.remove_pv_deployments(placement=placement)
    print(f"=========\nTotal removed deployments: {len(result)}")


def check_pv_deployments(input_path: str, hierarchy: str, config: dict):
    hierarchy = DeploymentHierarchy(hierarchy)
    config = SimpleNamespace(**config)
    manager = PVDeploymentManager(input_path, hierarchy, config)
    if config.placement:
        placement = Placement(config.placement)
    else:
        placement = config.placement
    result = manager.check_pv_deployments(placement=placement)
    print(json.dumps(result.__dict__, indent=2))


def remove_pv_configs(input_path: str, hierarchy: str, config: dict):
    hierarchy = DeploymentHierarchy(hierarchy)
    config = SimpleNamespace(**config)
    manager = PVConfigManager(input_path, hierarchy, config)
    if config.placement:
        placement = Placement(config.placement)
    else:
        placement = config.placement
    config_files = manager.remove_pv_configs(placement=placement)
    print(f"PV configs created! Total: {len(config_files)}")


def check_pv_configs(input_path: str, hierarchy: str, config: dict):
    hierarchy = DeploymentHierarchy(hierarchy)
    config = SimpleNamespace(**config)
    manager = PVConfigManager(input_path, hierarchy, config)
    if config.placement:
        placement = Placement(config.placement)
    else:
        placement = config.placement
    total_missing = manager.check_pv_configs(placement=placement)
    print(json.dumps(total_missing, indent=2))


def list_feeder_paths(input_path: str, hierarchy: str, config: dict):
    hierarchy = DeploymentHierarchy(hierarchy)
    storage = PVDataStorage(input_path, hierarchy, config)
    result = storage.get_feeder_paths()
    for feeder_path in result:
        print(feeder_path)
    print(f"=========\nTotal feeders: {len(result)}")


def redirect_pv_shapes(input_path: str, hierarchy: str, config: dict):
    hierarchy = DeploymentHierarchy(hierarchy)
    config = SimpleNamespace(**config)
    manager = PVDataManager(input_path, hierarchy, config)
    if hierarchy == DeploymentHierarchy.SUBSTATION:
        manager.redirect_substation_pv_shapes()
    elif hierarchy == DeploymentHierarchy.FEEDER:
        manager.redirect_feeder_pv_shapes()
    else:
        raise NotImplementedError(f"{hierarchy=}")


def generate_pv_deployment_jobs(input_path: str, hierarchy: str, config: dict):
    hierarchy = DeploymentHierarchy(hierarchy)
    config = SimpleNamespace(**config)
    
    manager = PVDeploymentManager(input_path, hierarchy, config)
    manager.generate_pv_creation_jobs()
    
    manager = PVConfigManager(input_path, hierarchy, config)
    manager.generate_pv_config_jobs()


def restore_feeder_data(input_path: str, hierarchy: str, config: dict):
    hierarchy = DeploymentHierarchy(hierarchy)
    config = SimpleNamespace(**config)
    manager = PVDataManager(input_path, hierarchy, config)
    manager.restore_feeder_data()


def transform_feeder_loads(input_path: str, hierarchy: str, config: dict):
    hierarchy = DeploymentHierarchy(hierarchy)
    config = SimpleNamespace(**config)
    manager = PVDataManager(input_path, hierarchy, config)
    manager.transform_feeder_loads()


ACTION_MAPPING = {
    "redirect-pvshapes": redirect_pv_shapes,
    "transform-loads": transform_feeder_loads,
    "generate-jobs": generate_pv_deployment_jobs,
    "restore-feeders": restore_feeder_data,
    
    "create-pv": create_pv_deployments,
    "create-configs": create_pv_configs,
    
    "remove-pv": remove_pv_deployments,
    "check-pv": check_pv_deployments,
    "remove-configs": remove_pv_configs,
    "check-configs": check_pv_configs,
    "list-feeders": list_feeder_paths
}

@click.group()
def pv_deployments():
    """Generate PV deployments from raw OpenDSS models"""


@click.command()
@click.argument("input_path")
@click.option(
    "-a", "--action",
    type=click.Choice(list(ACTION_MAPPING.keys()), case_sensitive=False),
    required=True,
    help="Choose the action related to pv deployments"
)
@click.option(
    "-c", "--control-name",
    type=click.STRING,
    default="volt_var_ieee_1547_2018_catB",
    show_default=True,
    help="Choose the control name to assign to pv configs in the action create-configs."
)
@click.option(
    "-h", "--hierarchy",
    type=click.Choice(HIERARCHY_CHOICE, case_sensitive=False),
    required=True,
    help="Choose the deployment hierarchy."
)
@click.option(
    "-l", "--kw-limit",
    type=click.FLOAT,
    default=5,
    show_default=True,
    help="Capacity threshold to use for assigning the value of --control-name. The action "
    "create-configs will only assign a control if a PV's capacity is greater than this value in "
    "kW.",
)
@click.option(
    "-p", "--placement",
    type=click.Choice(PLACEMENT_CHOICE, case_sensitive=False),
    required=False,
    default=None,
    show_default=True,
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
    "-n", "--sample-number",
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
# TODO: Jianli, this code option causes an exception with the command below.
# The option is not used, so I'm commenting it out.
#@click.option(
#    "-P", "--percent-shares",
#    default=[100, 0],
#    show_default=True,
#    help="The share pair - [share of residential PVs, share of utility scale PVs]"
#)
@click.option(
    "-x", "--pv-size-pdf",
    type=click.INT,
    default=None,
    show_default=True,
    help="The PV size pdf value"
)
@click.option(
    "--pv-upscale/--no-pv-upscale",
    is_flag=True,
    default=True,
    show_default=True,
    help="Upscale PV in deployments."
)
@click.option(
    "-o", "--pv-deployments-dirname",
    type=click.STRING,
    default=DEFAULT_PV_DEPLOYMENTS_DIRNAME,
    show_default=True,
    help="Output directory name of PV deployments"
)
@click.option(
    "-r", "--random-seed",
    type=click.IntRange(1, 1000000, clamp=True),
    default=random.randint(1, 1000000),
    help="Set an initial integer seed for making PV deployments reproducible"
)
@click.option(
    "--verbose",
    type=click.BOOL,
    is_flag=True,
    default=False,
    show_default=True,
    help="Enable to show overbose information."
)
def source_tree_1(
    input_path,
    action,
    control_name,
    hierarchy,
    kw_limit,
    placement,
    category,
    master_filename,
    min_penetration,
    max_penetration,
    penetration_step,
    sample_number,
    proximity_step,
    #percent_shares,
    pv_size_pdf,
    pv_upscale,
    pv_deployments_dirname,
    random_seed,
    verbose
):
    """Generate PV deployments for source tree 1."""
    level = logging.DEBUG if verbose else logging.INFO
    setup_logging("pv_deployments", None, console_level=level, packages=["disco"])
    
    if action == "create-pv":
        logger.info("Set integer %s as initial random seed for PV deployments.", random_seed)
    
    if action == "create-configs":
        logger.info("Set integer %s as initial random seed for PV configs.", random_seed)
    
    config = {
        "placement": placement,
        "category": category,
        "master_filename": master_filename,
        "pv_upscale": pv_upscale,
        "min_penetration": min_penetration,
        "max_penetration": max_penetration,
        "penetration_step": penetration_step,
        "sample_number": sample_number,
        "proximity_step": proximity_step,
        "percent_shares": [100, 0],
        "pv_size_pdf": pv_size_pdf,
        "pv_deployments_dirname": pv_deployments_dirname,
        "random_seed": random_seed
    }
    action_function = ACTION_MAPPING[action]
    args = [input_path, hierarchy, config]
    if action == "create-configs":
        args.append(control_name)
        args.append(kw_limit)
    action_function(*args)


pv_deployments.add_command(source_tree_1)
