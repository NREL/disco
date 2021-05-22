import os
import sys

from jade.utils.utils import load_data
from disco.exceptions import UnknownSourceType
from disco.pipelines.base import PipelineTemplate
from disco.pipelines.enums import SimulationType, TemplateSection
from disco.sources.base import FORMAT_FILENAME


SOURCE_MAPPINGS = {
    "SourceTree1Model": "source_tree_1"
}


def get_source_type(source_inputs):
    format_file = os.path.join(source_inputs, FORMAT_FILENAME)
    if not os.path.exists(format_file):
        raise UnknownSourceType(f"Source inputs does not contain '{FORMAT_FILENAME}'.")
    data = load_data(format_file)
    source_type = data["type"]
    if source_type not in SOURCE_MAPPINGS:
        raise UnknownSourceType(f"Source type '{source_type}' does not support.")
    return source_type


def get_default_pipeline_template(source_type, simulation_type):
    """Return the default pipeline template file"""
    source = SOURCE_MAPPINGS[source_type]
    if isinstance(simulation_type, SimulationType):
        simulation_type = simulation_type.value
    filename = f"{simulation_type}-default-template.toml"
    template_file = os.path.join(os.path.dirname(__file__), source, filename)
    template = PipelineTemplate(template_file)
    return template


def check_hpc_config(template_file):
    template = PipelineTemplate(template_file)
    for section in TemplateSection:
        try:
            submitter_params = template.get_submitter_params(section)
        except KeyError:
            continue
        
        hpc_config_file = submitter_params.get("hpc_config", None)
        if not hpc_config_file or not os.path.exists(hpc_config_file):
            print(f"{hpc_config_file} does not exist, please run 'jade config hpc' to create.")
            sys.exit(1)


def ensure_jade_pipeline_output_dir(text):
    """Replace JADE_PIPELINE_OUTPUT_DIR by using its value."""
    if "JADE_PIPELINE_OUTPUT_DIR" not in text:
        return text
    if "JADE_PIPELINE_OUTPUT_DIR" not in os.environ:
        raise KeyError(f"Environment variable JADE_PIPELINE_OUTPUT_DIR not found.")
    return text.replace("$JADE_PIPELINE_OUTPUT_DIR", os.environ["JADE_PIPELINE_OUTPUT_DIR"])
