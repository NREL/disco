import logging
import sys
from abc import ABC, abstractmethod

from filelock import SoftFileLock

from disco.storage.db import create_engine
from disco.storage.ingesters import OutputIngester, dump_storage_index
from disco.storage.outputs import get_simulation_output
from disco.storage.parsers import OutputParser

logger = logging.getLogger(__name__)


class PipelineStep(ABC):
    """Abstract pipeline step"""
    
    @staticmethod
    def execute(self):
        """Execute the pipeline step"""


class PipelineBase(ABC):
    """Abstract pipeline class"""
    
    def __init__(self, database):
        self.database = database

    @abstractmethod
    def run(self, data):
        """Entry point of running pipeline steps"""


class InitializationStep(PipelineStep):
    """A step for initializing and preparing data required by pipeline"""

    def execute(self, data):
        """Execute this step to initialize pipeline"""
        logger.info("Initializing data pipeline.")
        if not self.validate_task(data):
            task_name = data["task_name"]
            logger.error(f"Task '{task_name}' already exists, please try another --task-name.")
            sys.exit(1)
        return data

    def validate_task(self, data):
        """Return False if task_name already """
        if not data["database"]:
            return True
        
        engine = create_engine(data["database"])
        with engine.connect() as conn:
            queryset = conn.execute("SELECT name FROM task")
            existing_names = set([row[0] for row in queryset])
            if data["task_name"] in existing_names:
                return False
        return True


class OutputParsingStep(PipelineStep):
    """A step for parsing output of DISCO simulation/analysis """

    def __init__(self, output):
        self.output = get_simulation_output(output)
    
    def execute(self, data):
        """Parse desired data from output"""
        parser = OutputParser(
            task_name=data["task_name"],
            model_inputs=data["model_inputs"],
            notes=data["notes"],
        )
        result = parser.parse(output=self.output)
        return result


class ResultIngestionStep(PipelineStep):
    """A step for ingesting parsed result into database"""
    
    def __init__(self, database):
        self.database = database

    def execute(self, data):
        """Ingest parsed data into database"""
        logger.info("Ingesting results into database.")
        lock_file = self.database + ".lock"
        with SoftFileLock(lock_file=lock_file, timeout=3600):
            ingester = OutputIngester(database=self.database)
            indexes = ingester.ingest(data=data)
            return indexes


class FinalizatonStep(PipelineStep):
    """A step for closing pipeline"""
    
    def __init__(self, output):
        self.output = output
    
    def execute(self, data):
        """Store indexes of db storage into JSON file"""
        logger.info("Closing data ingestion pipeline.")
        dump_storage_index(output=self.output, indexes=data)


class StoragePipeline(PipelineBase):
    """Pipeline class for parsing and ingesting DISCO simulation/analysis results"""
    
    def run(self, data):
        """Execute pipeline steps in sequential order"""
        step1 = InitializationStep()
        valid_data = step1.execute(data=data)
        
        step2 = OutputParsingStep(output=data["output"])
        result = step2.execute(data=valid_data)
        
        step3 = ResultIngestionStep(database=data["database"])
        indexes = step3.execute(data=result)
        
        step4 = FinalizatonStep(output=data["output"])
        step4.execute(data=indexes)
        logger.info(f"Done! Tables were ingested into database - {data['database']}")
