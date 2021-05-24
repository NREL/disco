from jade.utils.utils import load_data
from disco.pipelines.base import PipelineTemplate
from disco.pipelines.enums import SimulationType
from disco.pipelines.source_tree_1.pipeline_creator import TimeSeriesPipelineCreator
from disco.sources.factory import make_source_model
from disco.sources.source_tree_1.source_tree_1_model import SourceTree1Model


SOURCE_MAPPINGS = {
    SourceTree1Model: "source_tree_1"
}


PIPELINE_CREATOR_MAPPING = {
    SimulationType.SNAPSHOT: "SnapshotPipelineCreator",
    SimulationType.TIME_SERIES: "TimeSeriesPipelineCreator"
}


class PipelineCreatorFactory:
    """Factory class for getting pipeline creator"""
    
    @classmethod
    def create(cls, template_file):
        """Create pipeline creator"""
        template = PipelineTemplate(template_file)
        
        inputs = template.data["inputs"]
        source = SOURCE_MAPPINGS[make_source_model(inputs)]
        
        simulation_type = SimulationType(template.data["simulation_type"])
        class_name = PIPELINE_CREATOR_MAPPING[simulation_type]
        
        pipeline_creator_class = getattr(__import__(
            name=f"disco.pipelines.{source}",
            fromlist=[class_name]
        ), class_name)
        pipeline_creator = pipeline_creator_class(template_file)
        return pipeline_creator
