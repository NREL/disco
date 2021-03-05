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

def generate_pv_deployments(input_path: str, hierarchy: str, config: dict, verbose: bool = False):
    """A factory method for generating pv deployments
    
    Parameters
    ----------
    input_path: str, the input path of raw data.
    hierarchy: str, a hierarchy type - region, substation, or feeder.
    config: dict, the configuration for PV deployment.
    verbose: bool, more logging information if enabled, default False.
    
    Returns
    ------
    summary: dict
        The summary of PV deployments.
    """
    hierarchy = DeploymentHierarchy(hierarchy)
    generator_class = PV_DEPLOYMENT_GENERATOR_MAPPING[hierarchy]
    config = SimpleNamespace(**config)
    generator = generator_class(input_path, config, verbose=verbose)
    summary = generator.generate_pv_deployments()
    return summary
