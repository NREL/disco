import os
import sys

from disco.enums import SimulationType
from disco.pipelines.base import PipelineTemplate
from disco.pipelines.enums import TemplateSection
from disco.sources.base import FORMAT_FILENAME


def get_default_pipeline_template(simulation_type):
    """Return the default pipeline template file"""
    if isinstance(simulation_type, SimulationType):
        simulation_type = simulation_type.value
    filename = f"{simulation_type}-default-template.toml"
    template_file = os.path.join(os.path.dirname(__file__), "template", filename)
    template = PipelineTemplate(template_file)
    return template


def check_hpc_config(template_file):
    template = PipelineTemplate(template_file)
    for section in TemplateSection:
        try:
            submitter_params = template.get_submitter_params(section)
        except KeyError:
            continue
        
        hpc_config =  submitter_params.get("hpc_config")
        if isinstance(hpc_config, dict) and hpc_config["hpc_type"] == "local":
            return

        assert isinstance(hpc_config, str)
        hpc_config_file = hpc_config
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
