import logging
import os
import shutil
import stat
import sys

import click

from jade.loggers import setup_logging
from jade.models import SingularityParams
from jade.utils.utils import dump_data, load_data

from disco.enums import SimulationType
from disco.pipelines.base import TemplateSection, TemplateParams, PipelineTemplate
from disco.pipelines.enums import AnalysisType
from disco.pipelines.factory import PipelineCreatorFactory
from disco.pipelines.utils import get_default_pipeline_template, check_hpc_config
from disco.pydss.pydss_configuration_base import get_default_reports_file, get_default_exports_file
from disco.sources.factory import make_source_model


logger = logging.getLogger(__name__)

SIMULATION_TYPE_CHOICE = [SimulationType.SNAPSHOT.value, SimulationType.TIME_SERIES.value]


@click.group()
def create_pipeline():
    """Create JADE pipeline for DISCO analysis"""


@click.command()
@click.argument("inputs")
@click.option(
    "-P", "--preconfigured",
    type=click.BOOL,
    is_flag=True,
    default=False,
    show_default=True,
    help="Whether inputs models are preconfigured"
)
@click.option(
    "-s", "--simulation-type",
    type=click.Choice(SIMULATION_TYPE_CHOICE, case_sensitive=True),
    default=SimulationType.SNAPSHOT.value,
    show_default=True,
    help="Choose a DISCO simulation type"
)
@click.option(
    "--with-loadshape/--no-with-loadshape",
    type=click.BOOL,
    is_flag=True,
    default=None,
    help="Indicate if loadshape file used for Snapshot simulation."
)
@click.option(
    "--auto-select-time-points/--no-auto-select-time-points",
    is_flag=True,
    default=True,
    show_default=True,
    help="Automatically select the time point based on max PV-load ratio for snapshot "
         "simulations. Only applicable if --with-loadshape.",
)
@click.option(
    "-d", "--auto-select-time-points-search-duration-days",
    default=365,
    show_default=True,
    help="Search duration in days. Only applicable with --auto-select-time-points.",
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
    "-c", "--cost-benefit",
    is_flag=True,
    default=False,
    show_default=True,
    help="Enable cost benefit computations"
)
@click.option(
    "-p", "--prescreen",
    type=click.BOOL,
    is_flag=True,
    default=False,
    show_default=True,
    help="Enable PV penetration level prescreening"
)
@click.option(
    "-t", "--template-file",
    type=click.STRING,
    required=False,
    default="pipeline-template.toml",
    show_default=True,
    help="Output pipeline template file"
)
@click.option(
    "-r",
    "--reports-filename",
    default=None,
    type=click.STRING,
    help="PyDSS report options. If None, use the default for the simulation type.",
)
@click.option(
    "-S",
    "--enable-singularity",
    is_flag=True,
    default=False,
    show_default=True,
    help="Add Singularity parameters and set the config to run in a container.",
)
@click.option(
    "-C",
    "--container",
    type=click.Path(exists=True),
    help="Path to container",
)
def template(
    inputs,
    preconfigured,
    simulation_type,
    with_loadshape,
    auto_select_time_points,
    auto_select_time_points_search_duration_days,
    impact_analysis,
    hosting_capacity,
    cost_benefit,
    prescreen,
    template_file,
    reports_filename,
    enable_singularity,
    container,
):
    """Create pipeline template file"""
    if hosting_capacity and impact_analysis:
        print("--impact-analysis and --hosting-capacity cannot both be enabled.")
        sys.exit(1)
    
    template = get_default_pipeline_template(simulation_type=simulation_type)
    template.data["inputs"] = inputs

    # model transformation
    if preconfigured:
        template.data["preconfigured"] = True
        template.remove_section(TemplateSection.MODEL)
    else:
        source_model = make_source_model(inputs)
        transform_defaults = source_model.get_transform_defaults()
        template.update_transform_params(transform_defaults)
    
    simulation_type = SimulationType(simulation_type)
    config_params = template.get_config_params(TemplateSection.SIMULATION)
    
    # snapshot special cases
    if simulation_type == SimulationType.SNAPSHOT:
        if prescreen:
            print("-p or --prescreen option has no effect on 'snapshot' pipeline, ignored!")
        
        if cost_benefit:
            print("-c or --cost-benefit option has no effect on 'snapshot' pipeline, ignored!")

        if with_loadshape is None:
            print("--with-loadshape option is required for Snapshot simulation.")
            sys.exit(1)

        config_params["with_loadshape"] = with_loadshape
        config_params["auto_select_time_points"] = auto_select_time_points
        config_params["auto_select_time_points_search_duration_days"] = \
            auto_select_time_points_search_duration_days
    
        template.update_config_params(config_params, TemplateSection.SIMULATION)

    # time-series special cases
    if simulation_type == SimulationType.TIME_SERIES:
        if prescreen:
            template.remove_params(TemplateSection.SIMULATION, TemplateParams.CONFIG_PARAMS)
        else:
            template.remove_section(TemplateSection.PRESCREEN)
        
        if cost_benefit:
            if config_params["exports_filename"] is None:
                exports_filename = get_default_exports_file(SimulationType.TIME_SERIES)
                config_params["exports_filename"] = exports_filename
                template.update_config_params(config_params, TemplateSection.SIMULATION)
    
    if reports_filename is None:
        reports_filename = get_default_reports_file(simulation_type)
    template.update_reports_params(load_data(reports_filename))

    if impact_analysis:
        template.data["analysis_type"] = AnalysisType.IMAPCT_ANALYSIS.value
    elif hosting_capacity:
        template.data["analysis_type"] = AnalysisType.HOSTING_CAPACITY.value
    elif cost_benefit and simulation_type == SimulationType.TIME_SERIES:
        template.data["analysis_type"] = AnalysisType.COST_BENEFIT.value
    else:
        template.remove_section(TemplateSection.POSTPROCESS)
    
    if enable_singularity:
        singularity_params = SingularityParams(enabled=True, container=container)
        for section in template.data.values():
            if isinstance(section, dict) and "submitter-params" in section:
                section["submitter-params"]["singularity_params"] = singularity_params.dict()

    dump_data(template.data, filename=template_file)
    print(f"Pipeline template file created - {template_file}")


@click.command()
@click.argument("template-file")
@click.option(
    "-c", "--config-file",
    type=click.STRING,
    default="pipeline.json",
    show_default=True,
    help="Pipeline config file"
)
def config(template_file, config_file):
    """Create pipeline config file"""
    check_hpc_config(template_file)
    pipeline_creator = PipelineCreatorFactory.create(template_file=template_file)
    pipeline_creator.create_pipeline(config_file)
    print(f"Pipeline config file created - {config_file}")


create_pipeline.add_command(template)
create_pipeline.add_command(config)
