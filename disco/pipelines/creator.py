import logging
import os

from PyDSS.common import SnapshotTimePointSelectionMode
from PyDSS.reports.pv_reports import PF1_SCENARIO, CONTROL_MODE_SCENARIO

import disco
from disco.pipelines.enums import AnalysisType, TemplateSection
from disco.pipelines.base import PipelineCreatorBase
from disco.pydss.common import TIME_SERIES_SCENARIOS
from disco.pydss.pydss_configuration_base import get_default_exports_file
from jade.models.pipeline import PipelineConfig
from jade.utils.utils import dump_data

logger = logging.getLogger(__name__)


EXPORTS_FILENAME = get_default_exports_file()


class SnapshotPipelineCreator(PipelineCreatorBase):

    def create_pipeline(self, config_file):
        """Make snapshot pipeline config file"""
        stages = [self.make_simulation_stage()]
        if self.template.contains_postprocess():
            stages.append(self.make_postprocess_stage())

        config = PipelineConfig(stages=stages, stage_num=1)
        with open(config_file, "w") as f:
            f.write(config.json(indent=2))
        logger.info("Created pipeline config file - %s", config_file)

    def make_model_transform_command(self):
        options = self.template.get_transform_options(TemplateSection.MODEL)
        command = f"disco transform-model {self.template.inputs} snapshot {options}"
        logger.info("Make command - '%s'", command)
        return command

    def make_disco_config_command(self, section):
        if self.template.preconfigured:
            model_inputs = self.template.inputs
        else:
            model_inputs = self.template.get_model_transform_output()
        options = self.template.get_config_options(section)
        reports_filename = "generated_snapshot_reports.toml"
        dump_data(self.template.reports, reports_filename)
        command = (
            f"disco config snapshot {model_inputs} "
            f"--reports-filename={reports_filename} --exports-filename={EXPORTS_FILENAME} {options}"
        )
        return command

    def make_prescreen_create_command(self):
        pass

    def make_prescreen_filter_command(self):
        pass

    def make_postprocess_command(self):
        commands = []
        impact_analysis = self.template.analysis_type == AnalysisType.IMAPCT_ANALYSIS.value
        hosting_capacity = self.template.analysis_type == AnalysisType.HOSTING_CAPACITY.value
        if impact_analysis or hosting_capacity:
            inputs = os.path.join("$JADE_PIPELINE_OUTPUT_DIR", f"output-stage{self.stage_num-1}")
            commands.append(f"disco-internal make-summary-tables {inputs}")
            if hosting_capacity:
                config_params = self.template.get_config_params(TemplateSection.SIMULATION)
                with_loadshape = config_params["with_loadshape"]
                auto_select_time_points = config_params["auto_select_time_points"]
                pf1 = config_params["pf1"]
                base_cmd = f"disco-internal compute-hosting-capacity {inputs}"
                if with_loadshape:
                    scenarios = [CONTROL_MODE_SCENARIO]
                    if pf1:
                        scenarios.append(PF1_SCENARIO)
                    if auto_select_time_points:
                        for scenario in scenarios:
                            for mode in SnapshotTimePointSelectionMode:
                                if mode != SnapshotTimePointSelectionMode.NONE:
                                    commands.append(f"{base_cmd} --scenario={scenario} --time-point={mode.value}")
                    else:
                        for scenario in scenarios:
                            commands.append(f"{base_cmd} --scenario={scenario}")
                else:
                    commands.append(f"{base_cmd} --scenario=scenario")
        return "\n".join(commands)


class TimeSeriesPipelineCreator(PipelineCreatorBase):
    """Time-series pipeline creator class"""

    def create_pipeline(self, config_file):
        """Make time-series pipeline config file"""
        stages = []
        if self.template.contains_prescreen():
            stages.append(self.make_prescreen_stage())
        stages.append(self.make_simulation_stage())
        if self.template.contains_postprocess():
            stages.append(self.make_postprocess_stage())

        config = PipelineConfig(stages=stages, stage_num=1)
        with open(config_file, "w") as f:
            f.write(config.json(indent=2))
        logger.info("Created pipeline config file - %s", config_file)

    def make_model_transform_command(self):
        options = self.template.get_transform_options(TemplateSection.MODEL)
        command = f"disco transform-model {self.template.inputs} time-series {options}"
        logger.info("Make command - '%s'", command)
        return command

    def make_disco_config_command(self, section):
        if self.template.preconfigured:
            model_inputs = self.template.inputs
        else:
            model_inputs = self.template.get_model_transform_output()
        options = self.template.get_config_options(section)
        reports_filename = "generated_time_series_reports.toml"
        dump_data(self.template.reports, reports_filename)
        command = (
            f"disco config time-series {model_inputs} "
            f"--reports-filename={reports_filename} {options}"
        )
        logger.info("Make command - '%s'", command)
        return command

    def make_prescreen_create_command(self):
        config_params = self.template.get_config_params(TemplateSection.PRESCREEN)
        config_file = config_params["config_file"]
        prescreen_params = self.template.get_prescreen_params(TemplateSection.PRESCREEN)
        command = (
            f"disco prescreen-pv-penetration-levels {config_file} "
            f"create --config-file={prescreen_params['prescreen_config_file']}"
        )
        logger.info("Make command - '%s'", command)
        return command

    def make_prescreen_filter_command(self):
        config_params = self.template.get_config_params(TemplateSection.PRESCREEN)
        config_file = config_params["config_file"]

        prescreen_params = self.template.get_prescreen_params(TemplateSection.PRESCREEN)
        prescreen_output = os.path.join("$JADE_PIPELINE_OUTPUT_DIR", f"output-stage{self.stage_num-1}")
        command = (
            f"disco prescreen-pv-penetration-levels {config_file} "
            f"filter-config {prescreen_output} "
            f"--config-file={prescreen_params['filtered_config_file']}"
        )
        logger.info("Make command - '%s'", command)
        return command

    def make_postprocess_command(self):
        command = ""
        impact_analysis = self.template.analysis_type == AnalysisType.IMAPCT_ANALYSIS.value
        hosting_capacity = self.template.analysis_type == AnalysisType.HOSTING_CAPACITY.value
        if impact_analysis or hosting_capacity:
            inputs = os.path.join("$JADE_PIPELINE_OUTPUT_DIR", f"output-stage{self.stage_num-1}")
            command += f"disco-internal make-summary-tables {inputs}"
            if hosting_capacity:
                for scenario in TIME_SERIES_SCENARIOS:
                    command += f"\ndisco-internal compute-hosting-capacity {inputs} --scenario={scenario}"
        return command
