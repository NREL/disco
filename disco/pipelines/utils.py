import os

from jade.utils.utils import load_data
from disco.exceptions import UnknownSourceType
from disco.pipelines.base import PipelineTemplate
from disco.pipelines.enums import SimulationType


SOURCE_MAPPINGS = {
    "SourceTree1Model": "source_tree_1"
}


def get_source_type(source_inputs):
    format_file = os.path.join(source_inputs, "format.toml")
    if not os.path.exists(format_file):
        raise UnknownSourceType("Source inputs does not contain 'format.toml'.")
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
