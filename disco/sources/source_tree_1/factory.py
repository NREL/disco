"""This module contains factory methods related to source_tree_1"""
from types import SimpleNamespace

from .pv_deployments import (
    DeploymentHierarchy,
    RegionPVDeploymentGenerator,
    SubstationPVDeploymentGenerator,
    FeederPVDeploymentGenerator
)

PV_DEPLOYMENT_GENERATOR_MAPPING = {
    DeploymentHierarchy.REGION: RegionPVDeploymentGenerator,
    DeploymentHierarchy.SUBSTATION: SubstationPVDeploymentGenerator,
    DeploymentHierarchy.FEEDER: FeederPVDeploymentGenerator
}

def generate_pv_deployments(input_path: str, hierarchy: str, config: dict):
    """A factory method for generating pv deployments
    
    Parameters
    ----------
    input_path: str, the input path of raw data.
    hierarchy: str, a hierarchy type - region, substation, or feeder.
    config: dict, the configuration for PV deployment.
    
    Returns
    ------
    summary: dict
        The summary of PV deployments.
    """
    hierarchy = DeploymentHierarchy(hierarchy)
    generator_class = PV_DEPLOYMENT_GENERATOR_MAPPING[hierarchy]
    config = SimpleNamespace(**config)
    generator = generator_class(input_path, config)
    summary = generator.generate_pv_deployments()
    return summary


def list_feeder_paths(input_path: str, hierarchy: str):
    """
    A factory method for getting feeder paths
    """
    hierarchy = DeploymentHierarchy(hierarchy)
    generator_class = PV_DEPLOYMENT_GENERATOR_MAPPING[hierarchy]
    generator = generator_class(input_path, config=None)
    feeder_paths = generator.get_feeder_paths()
    return feeder_paths
