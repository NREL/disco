import logging
import os
import shutil
import stat
import sys

import click

from jade.loggers import setup_logging
from jade.utils.utils import dump_data, load_data

from disco.pipelines.base import TemplateSection, TemplateParams, PipelineTemplate
from disco.pipelines.enums import SimulationType, AnalysisType
from disco.pipelines.factory import PipelineCreatorFactory
from disco.pipelines.utils import get_source_type, get_default_pipeline_template


logger = logging.getLogger(__name__)

SIMULATION_TYPE_CHOICE = [SimulationType.SNAPSHOT.value, SimulationType.TIME_SERIES.value]


@click.group()
def create_pipeline():
    """Create JADE pipeline for DISCO analysis"""


@click.command()
@click.argument("inputs")
@click.option(
    "-s", "--simulation-type",
    type=click.Choice(SIMULATION_TYPE_CHOICE, case_sensitive=True),
    default=SimulationType.SNAPSHOT.value,
    show_default=True,
    help="Choose a DISCO simulation type"
)
@click.option(
    "-i", "--impact-analysis",
    is_flag=True,
    default=False,
    show_default=True,
    help="Enable impact analysis computations",
)
@click.option(
    "-h", "--hosting-capacity",
    is_flag=True,
    default=False,
    show_default=True,
    help="Enable hosting capacity computations",
)
@click.option(
    "-p", "--prescreen",
    type=click.BOOL,
    is_flag=True,
    default=False,
    show_default=True,
    help="Enable pv penetration level prescreening"
)
@click.option(
    "-t", "--template-file",
    type=click.STRING,
    required=False,
    default="pipeline-template.toml",
    show_default=True,
    help="Output pipeline template file"
)
def template(inputs, simulation_type, impact_analysis, hosting_capacity, prescreen, template_file):
    """Create pipeline template file"""
    if hosting_capacity and impact_analysis:
        print("--impact-analysis and --hosting-capacity cannot both be enabled.")
        sys.exit(1)

    source_type = get_source_type(source_inputs=inputs)
    template = get_default_pipeline_template(source_type, simulation_type=simulation_type)
    template.data["inputs"] = inputs
    
    if impact_analysis:
        template.data["analysis_type"] = AnalysisType.IMAPCT_ANALYSIS.value
    elif hosting_capacity:
        template.data["analysis_type"] = AnalysisType.HOSTING_CAPACITY.value
    else:
        template.remove_section(TemplateSection.POSTPROCESS)
    
    if SimulationType(simulation_type) == SimulationType.SNAPSHOT:
        if prescreen:
            print("-p or --prescreen option has no effect on 'snapshot' pipeline, ignored!")
    
    if SimulationType(simulation_type) == SimulationType.TIME_SERIES:
        if prescreen:
            template.remove_params(TemplateSection.SIMULATION, TemplateParams.CONFIG_PARAMS)
        else:
            template.remove_section(TemplateSection.PRESCREEN)
    
    dump_data(template.data, filename=template_file)
    print(f"Pipeline template file created - {template_file}")


@click.command()
@click.argument("template")
@click.option(
    "-c", "--config-file",
    type=click.STRING,
    default="pipeline.json",
    show_default=True,
    help="Pipeline config file"
)
def config(template, config_file):
    """Create pipeline config file"""
    pipeline_creator = PipelineCreatorFactory.create(template_file=template)
    pipeline_creator.create_pipeline(config_file)
    print(f"Pipeline config file created - {config_file}")


create_pipeline.add_command(template)
create_pipeline.add_command(config)
