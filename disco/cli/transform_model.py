"""CLI commands for transforming source data"""

import logging
import os
import shutil

import click

from jade.exceptions import InvalidConfiguration, InvalidParameter
from jade.utils.utils import dump_data, load_data
from disco.enums import AnalysisType
from disco.models.factory import get_model_class_by_analysis_type
from disco.sources.factory import make_source_model


TRANSFORM_CONFIG_FILE = "transform_config.toml"

logger = logging.getLogger(__name__)


@click.command()
@click.argument("input_path", type=click.Path(exists=True))
@click.argument("analysis_type")
@click.option(
    "-c", "--config-file",
    help="config file to create",
    default=TRANSFORM_CONFIG_FILE,
    show_default=True,
)
def generate_transform_model_config(input_path, analysis_type, config_file):
    """Generate a transformation input file from defaults."""
    source_type = make_source_model(input_path)
    analysis_type = AnalysisType(analysis_type)
    defaults = source_type.get_default_transformation_selections(analysis_type)
    defaults["source_type"] = source_type.__name__
    defaults["analysis_type"] = analysis_type.value
    defaults["input_path"] = input_path
    dump_data(defaults, config_file)
    print(f"Created {config_file}")


@click.command()
@click.argument("config_file")
@click.option(
    "-o", "--output",
    help="output path",
    default="disco-models",
    show_default=True,
)
@click.option(
    "-f", "--force",
    help="overwrite existing directories",
    is_flag=True,
    default=False,
    show_default=True,
)
def transform_model(config_file, output, force):
    """Transform input data into a DISCO model"""
    if os.path.exists(output):
        if force:
            shutil.rmtree(output)
            os.mkdir(output)
        else:
            raise InvalidParameter(f"output={output} exists. Set --force to overwrite")

    config = load_data(config_file)
    source_type = make_source_model(config["input_path"])
    if source_type.__name__ != config["source_type"]:
        raise InvalidConfiguration(
            f"type mismatch: {source_type.__name__} / config['source_type']"
        )

    analysis_type = AnalysisType(config["analysis_type"])
    simulation_model = get_model_class_by_analysis_type(analysis_type)
    source_type.transform(config, simulation_model, output)
    print(f"Transformed source data {config['input_path']} to {output}")
