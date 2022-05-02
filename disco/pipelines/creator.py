import logging
import os

from PyDSS.common import SnapshotTimePointSelectionMode
from PyDSS.reports.pv_reports import PF1_SCENARIO, CONTROL_MODE_SCENARIO

import disco
from disco.enums import SimulationType, AnalysisType
from disco.pipelines.enums import TemplateSection
from disco.pipelines.base import PipelineCreatorBase
from disco.pydss.common import TIME_SERIES_SCENARIOS
from disco.pydss.pydss_configuration_base import get_default_exports_file
from jade.models.pipeline import PipelineConfig
from jade.utils.utils import dump_data

logger = logging.getLogger(__name__)


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
        exports_filename = get_default_exports_file(
            SimulationType.SNAPSHOT,
            AnalysisType(self.template.analysis_type),
        )
        command = (
            f"disco config snapshot {model_inputs} "
            f"--reports-filename={reports_filename} --exports-filename={exports_filename} {options}"
        )
        return command

    def make_prescreen_create_command(self):
        pass

    def make_prescreen_filter_command(self):
        pass

    def make_postprocess_command(self):
        commands = []
        impact_analysis = self.template.analysis_type == AnalysisType.IMPACT_ANALYSIS.value
        hosting_capacity = self.template.analysis_type == AnalysisType.HOSTING_CAPACITY.value
        if impact_analysis or hosting_capacity:
            # Postprocess to make summary tables
            inputs = os.path.join("$JADE_PIPELINE_OUTPUT_DIR", f"output-stage{self.stage_num-1}")
            commands.append(f"disco make-summary-tables {inputs}")
            
            # Postprocess to compute hosting capacity
            if hosting_capacity:
                config_params = self.template.get_config_params(TemplateSection.SIMULATION)
                with_loadshape = config_params["with_loadshape"]
                auto_select_time_points = config_params["auto_select_time_points"]
                pf1 = config_params["pf1"]
                base_cmd = f"disco-internal compute-hosting-capacity {inputs}"
                plot_cmd = f"disco-internal plot {inputs}"
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
                    scenarios = ["scenario"]
            
                # Plot
                for scenario in scenarios:
                    commands.append(f"{plot_cmd} --scenario {scenario}")

            # Postprocess to ingest results into sqlite database
            task_name = self.template.data["task_name"]
            if os.path.isabs(self.template.database):
                database = self.template.database
            else:
                database = os.path.join(inputs, self.template.database)
            model_inputs = self.template.inputs
            commands.append(
                'disco ingest-tables '
                f'--task-name "{task_name}" '
                f'--database {database} '
                f'--model-inputs {model_inputs} '
                f'{inputs}'
            )

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
        if self.template.analysis_type == AnalysisType.COST_BENEFIT.value:
            # These must not be user-configurable and don't go in the template.
            command += " --feeder-losses=false --thermal-metrics=false --voltage-metrics=false"

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
        commands = []
        impact_analysis = self.template.analysis_type == AnalysisType.IMPACT_ANALYSIS.value
        hosting_capacity = self.template.analysis_type == AnalysisType.HOSTING_CAPACITY.value
        if impact_analysis or hosting_capacity:
            inputs = os.path.join("$JADE_PIPELINE_OUTPUT_DIR", f"output-stage{self.stage_num-1}")
            commands.append(f"disco make-summary-tables {inputs}")
            if hosting_capacity:
                for scenario in TIME_SERIES_SCENARIOS:
                    commands.append(f"disco-internal compute-hosting-capacity {inputs} --scenario={scenario}")
                
                for scenario in TIME_SERIES_SCENARIOS:
                    commands.append(f"disco-internal plot {inputs} --scenario={scenario}")
            
            # Postprocess to ingest results into sqlite database
            task_name = self.template.data["task_name"]
            
            if os.path.isabs(self.template.database):
                database = self.template.database
            else:
                database = os.path.join(inputs, self.template.database)
            model_inputs = self.template.inputs
            commands.append(
                'disco ingest-tables '
                f'--task-name "{task_name}" '
                f'--database {database} '
                f'--model-inputs {model_inputs} '
                f'{inputs}'
            )

        elif self.template.analysis_type == AnalysisType.COST_BENEFIT.value:
            inputs = os.path.join("$JADE_PIPELINE_OUTPUT_DIR", f"output-stage{self.stage_num-1}")
            commands.append(f"disco-internal make-cba-tables {inputs}")
        
        return "\n".join(commands)


class UpgradePipelineCreator(PipelineCreatorBase):
    """Upgrade pipeline creator class"""

    def create_pipeline(self, config_file):
        stages = [self.make_simulation_stage()]
        if self.template.contains_postprocess():
            stages.append(self.make_postprocess_stage())
        
        config = PipelineConfig(stages=stages, stage_num=1)
        with open(config_file, "w") as f:
            f.write(config.json(indent=2))
        logger.info("Created pipeline config file - %s", config_file)
    
    def make_model_transform_command(self):
        options = self.template.get_transform_options(TemplateSection.MODEL)
        command = f"disco transform-model {self.template.inputs} upgrade {options}"
        logger.info("Make command - '%s'", command)
        return command
    
    def make_prescreen_create_command(self):
        pass

    def make_prescreen_filter_command(self):
        pass

    def make_disco_config_command(self, section):
        if self.template.preconfigured:
            model_inputs = self.template.inputs
        else:
            model_inputs = self.template.get_model_transform_output()
        
        options = self.template.get_config_options(section)
        command = f"disco config upgrade {model_inputs} {options}"
        logger.info("Make command - '%s'", command)
        return command

    def make_postprocess_command(self):
        inputs = os.path.join("$JADE_PIPELINE_OUTPUT_DIR", f"output-stage{self.stage_num-1}")
        command = f"disco-internal make-upgrade-tables {inputs}"
        return command


class UpgradePipelineCreator(PipelineCreatorBase):
    """Upgrade pipeline creator class"""

    def create_pipeline(self, config_file):
        stages = [self.make_simulation_stage()]
        if self.template.contains_postprocess():
            stages.append(self.make_postprocess_stage())
        
        config = PipelineConfig(stages=stages, stage_num=1)
        with open(config_file, "w") as f:
            f.write(config.json(indent=2))
        logger.info("Created pipeline config file - %s", config_file)
    
    def make_model_transform_command(self):
        options = self.template.get_transform_options(TemplateSection.MODEL)
        command = f"disco transform-model {self.template.inputs} upgrade {options}"
        logger.info("Make command - '%s'", command)
        return command
    
    def make_prescreen_create_command(self):
        pass

    def make_prescreen_filter_command(self):
        pass

    def make_disco_config_command(self, section):
        if self.template.preconfigured:
            model_inputs = self.template.inputs
        else:
            model_inputs = self.template.get_model_transform_output()
        
        options = self.template.get_config_options(section)
        command = f"disco config upgrade {model_inputs} {options}"
        logger.info("Make command - '%s'", command)
        return command

    def make_postprocess_command(self):
        inputs = os.path.join("$JADE_PIPELINE_OUTPUT_DIR", f"output-stage{self.stage_num-1}")
        command = f"disco-internal make-upgrade-tables {inputs}"
        return command
