import logging
import os
from abc import ABC, abstractmethod

from jade.hpc.common import HpcType
from jade.jobs.pipeline_manager import PipelineManager
from jade.models import HpcConfig, LocalHpcConfig
from jade.models.pipeline import PipelineStage
from jade.utils.utils import dump_data, load_data
from disco.pipelines.enums import TemplateSection, TemplateParams
from disco.enums import AnalysisType

logger = logging.getLogger(__name__)


class PipelineTemplate:
    """class for handling pipeline template data"""
    
    def __init__(self, template_file):
        self.template_file = template_file
        self.data = load_data(template_file)
    
    @property
    def task_name(self):
        return self.data["task_name"]

    @property
    def inputs(self):
        return self.data["inputs"]

    @property
    def preconfigured(self):
        return self.data["preconfigured"]

    @property
    def simulation_type(self):
        return self.data["simulation_type"]
    
    @property
    def analysis_type(self):
        return self.data["analysis_type"]

    @property
    def database(self):
        return self.data["database"]

    @property
    def reports(self):
        return self.data.get(TemplateSection.REPORTS.value, {})

    def contains_prescreen(self):
        return TemplateSection.PRESCREEN.value in self.data

    def contains_postprocess(self):
        return TemplateSection.POSTPROCESS.value in self.data

    def update_transform_params(self, data):
        section = TemplateSection.MODEL
        _data = self._keep_null_value(data)
        self.data[section.value][TemplateParams.TRANSFORM_PARAMS.value].update(_data)

    def update_config_params(self, data, section):
        _data = self._keep_null_value(data)
        self.data[section.value][TemplateParams.CONFIG_PARAMS.value].update(_data)

    def update_reports_params(self, data):
        if TemplateSection.REPORTS.value not in self.data:
            self.data[TemplateSection.REPORTS.value] = {}
        _data = self._keep_null_value(data)
        self.data[TemplateSection.REPORTS.value].update(_data)
    
    @staticmethod
    def _keep_null_value(data):
        _data = {}
        for key, value in data.items():
            if value is None:
                _data[key] = "null"
            else:
                _data[key] = value
        return _data

    def get_command_params(self, section, params_type):
        """Return command params in dict"""
        if isinstance(section, TemplateSection):
            section = section.value
        if isinstance(params_type, TemplateParams):
            params_type = params_type.value
        
        if params_type not in self.data[section]:
            raise KeyError(f"Template section '{section}' does not contain '{params_type}'.")
        
        params = self.data[section].get(params_type)
        for param, value in params.items():
            if value == "null":
                params[param] = None
        return params

    def get_transform_params(self, section):
        return self.get_command_params(section, TemplateParams.TRANSFORM_PARAMS)

    def get_prescreen_params(self, section):
        return self.get_command_params(section, TemplateParams.PRESCREEN_PARAMS)

    def get_config_params(self, section):
        return self.get_command_params(section, TemplateParams.CONFIG_PARAMS)

    def get_submitter_params(self, section):
        return self.get_command_params(section, TemplateParams.SUMITTER_PARAMS)

    def get_command_options(self, section, params_type):
        """Return command options in constructed string"""
        if isinstance(section, TemplateSection):
            section = section.value
        if isinstance(params_type, TemplateParams):
            params_type = params_type.value
        
        params = self.data[section][params_type]
        options = self._construct_options_string(params)
        return options
    
    @staticmethod
    def _construct_options_string(params):
        temp = []
        for param, value in params.items():
            if value == "null" or value is False or value is None:
                continue
            dash_param = "--" + param.replace("_", "-")
            if value is True:
                temp.append(dash_param)
            else:
                temp.append(f"{dash_param}={value}")
        options =  " ".join(temp)
        return options
    
    def get_model_transform_output(self):
        if "JADE_PIPELINE_OUTPUT_DIR" in os.environ:
            pipeline_output = os.environ["JADE_PIPELINE_OUTPUT_DIR"]
        else:
            pipeline_output = "$JADE_PIPELINE_OUTPUT_DIR"
        params = self.get_transform_params(TemplateSection.MODEL)
        output = os.path.join(pipeline_output, params["output"])
        return output
    
    def get_transform_options(self, section):
        params = self.get_transform_params(TemplateSection.MODEL)
        params["output"] = os.path.join("$JADE_PIPELINE_OUTPUT_DIR", params["output"])
        options = self._construct_options_string(params)
        return options
    
    def get_config_options(self, section):
        return self.get_command_options(section, TemplateParams.CONFIG_PARAMS)

    def get_submitter_options(self, section):
        return self.get_command_options(section, TemplateParams.SUMITTER_PARAMS)

    def remove_section(self, section):
        if isinstance(section, TemplateSection):
            section = section.value
        
        if section in self.data:
            self.data.pop(section)

    def remove_params(self, section, params_type):
        if isinstance(section, TemplateSection):
            section = section.value
        if isinstance(params_type, TemplateParams):
            params_type = params_type.value
        if section in self.data and params_type in self.data[section]:
            self.data[section].pop(params_type)

    def set_preconfigured_models(self, path):
        self.data[TemplateSection.MODEL.value]["preconfigured_models"] = path


class PipelineCreatorBase(ABC):
    """A base class for pipeline creator"""

    def __init__(self, template_file):
        self.template_file = template_file
        self.stage_num = 0
    
    @property
    def template(self):
        return PipelineTemplate(self.template_file)
    
    @staticmethod
    def get_auto_config_python_file():
        return os.path.join(os.path.dirname(__file__), "auto_config.py")
    
    def get_prescreen_auto_config_text_file(self):
        return os.path.join(".", "pipeline-prescreen-auto-config.txt")
    
    def get_simulation_auto_config_text_file(self):
        return os.path.join(".", "pipeline-simulation-auto-config.txt")

    def get_postprocess_auto_config_text_file(self):
        return os.path.join(".", "pipeline-postprocess-auto-config.txt")
    
    def get_postprocess_command_text_file(self):
        return os.path.join(".", "pipeline-postprocess-command.txt")
    
    @abstractmethod
    def create_pipeline(self, pipeline_config_file):
        """Create pipeline config file"""
    
    @abstractmethod
    def make_model_transform_command(self):
        """Make disco transform-model command"""
    
    @abstractmethod
    def make_prescreen_create_command(self):
        """Make disco prescreen-pv-penetration-levels command"""
    
    @abstractmethod
    def make_prescreen_filter_command(self):
        """Make disco prescreen-pv-penetration-levels filter-config command"""
    
    @abstractmethod
    def make_disco_config_command(self, section):
        """Make disco config command"""
    
    @abstractmethod
    def make_postprocess_command(self):
        """Make disco make-summary-tables & compute-hosting-capacity command"""
    
    def create_prescreen_auto_config_text_file(self):
        """Create script for generating prescreen config file"""
        temp = []
        if not self.template.preconfigured:
            transform_command = self.make_model_transform_command()
            temp.append(transform_command)
        config_command = self.make_disco_config_command(TemplateSection.PRESCREEN)
        prescreen_command = self.make_prescreen_create_command()
        temp.extend([config_command, prescreen_command])
        auto_config_command = "\n".join(temp)
        
        text_file = self.get_prescreen_auto_config_text_file()
        with open(text_file, "w") as f:
            f.write(auto_config_command)
            f.write("\n")
        return text_file
    
    def create_simulation_auto_config_text_file(self):
        """Create script for generating disco config file"""
        if self.template.contains_prescreen():
            auto_config_command = self.make_prescreen_filter_command()
        else:
            temp = []
            if not self.template.preconfigured:
                temp.append(self.make_model_transform_command())
            temp.append(self.make_disco_config_command(TemplateSection.SIMULATION))
            auto_config_command = "\n".join(temp)
        
        text_file = self.get_simulation_auto_config_text_file()
        with open(text_file, "w") as f:
            f.write(auto_config_command)
            f.write("\n")
        return text_file

    def create_postprocess_auto_config_text_file(self):
        """Create script for generating postprocess config file"""
        command_file = self.create_postprocess_command_text_file()
        options = self.template.get_config_options(TemplateSection.POSTPROCESS)
        auto_config_command = f"jade config create {command_file} {options}"
        
        text_file = self.get_postprocess_auto_config_text_file()
        with open(text_file, "w") as f:
            f.write(auto_config_command)
        return text_file
    
    def create_postprocess_command_text_file(self):
        text_file = "pipeline-postprocess-command.txt"
        command = self.make_postprocess_command()
        with open(text_file, "w") as f:
            f.write(command)
        return text_file

    def make_prescreen_stage(self):
        self.stage_num += 1
        auto_config_text_file = self.create_prescreen_auto_config_text_file()
        submitter_params = self.template.get_submitter_params(TemplateSection.PRESCREEN)
        submitter_params["hpc_config"] = _create_hpc_config(submitter_params)
        
        auto_config_py = self.get_auto_config_python_file()
        auto_config_command = f"python {auto_config_py} {auto_config_text_file}"
        prescreen_params = self.template.get_prescreen_params(TemplateSection.PRESCREEN)
        stage = PipelineStage(
            auto_config_cmd=auto_config_command,
            config_file=prescreen_params["prescreen_config_file"],
            stage_num=self.stage_num,
            submitter_params=submitter_params,
        )
        return stage

    def make_simulation_stage(self):
        self.stage_num += 1
        auto_config_text_file = self.create_simulation_auto_config_text_file()
        submitter_params = self.template.get_submitter_params(TemplateSection.SIMULATION)
        submitter_params["hpc_config"] = _create_hpc_config(submitter_params)
        
        if self.template.contains_prescreen():
            prescreen_params = self.template.get_prescreen_params(TemplateSection.PRESCREEN)
            config_file = prescreen_params["filtered_config_file"]
        else:
            config_params = self.template.get_config_params(TemplateSection.SIMULATION)
            config_file = config_params["config_file"]

        auto_config_py = self.get_auto_config_python_file()
        auto_config_command = f"python {auto_config_py} {auto_config_text_file}"
        stage = PipelineStage(
            auto_config_cmd=auto_config_command,
            config_file=config_file,
            stage_num=self.stage_num,
            submitter_params=submitter_params
        )
        return stage
    
    def make_postprocess_stage(self):
        self.stage_num += 1
        auto_config_text_file = self.create_postprocess_auto_config_text_file()
        submitter_params = self.template.get_submitter_params(TemplateSection.POSTPROCESS)
        submitter_params["hpc_config"] = _create_hpc_config(submitter_params)
        
        auto_config_py = self.get_auto_config_python_file()
        auto_config_command = f"python {auto_config_py} {auto_config_text_file}"
        config_params = self.template.get_config_params(TemplateSection.POSTPROCESS)
        stage = PipelineStage(
            auto_config_cmd=auto_config_command,
            config_file=config_params["config_file"],
            stage_num=self.stage_num,
            submitter_params=submitter_params
        )
        return stage


def _create_hpc_config(submitter_params):
    # TODO: this should be solved in JADE.
    hpc_config = submitter_params["hpc_config"]
    if isinstance(hpc_config, str):
        return HpcConfig(**load_data(hpc_config))

    if submitter_params["hpc_config"]["hpc_type"] == "local":
        return HpcConfig(hpc_type=HpcType.LOCAL, hpc=LocalHpcConfig())

    raise Exception(f"Unknown hpc config: {hpc_config}")
