import logging
import os
import platform
import pathlib
from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum

from disco.storage.exceptions import IngestionError

# NOTE: Important table names, please do not change the order.
TABLE_NAMES = [
    "feeder_head_table.csv",
    "feeder_losses_table.csv",
    "metadata_table.csv",
    "thermal_metrics_table.csv",
    "voltage_metrics_table.csv",
    
    # Only apply to snapshot simulaiton 
    # with --auto-select-time-points option enabled
    "snapshot_time_points_table.csv"
]

DERMS_INFO_FILENAME = "derms_simulation_info.json"

logger = logging.getLogger(__name__)


class OutputType(Enum):
    JADE = "jade"
    JADE_PIPELINE = "jade-pipeline"
    DERMS = "derms"


class OutputBase(ABC):
    """Abstract output class for handling JADE output directory"""

    def __init__(self, output: pathlib.Path) -> None:
        self.output = self.validate_output(output)

    @property
    @abstractmethod
    def output_type(self):
        """The output type"""

    @property
    def creation_time(self):
        timestamp = get_creation_time(self.output)
        return datetime.fromtimestamp(timestamp)

    @property
    def config_file(self):
        return self.output / "config.json"

    @property
    def result_file(self):
       return self.output / "results.json"

    @property
    def job_outputs(self):
        return self.output / "job-outputs"
    
    @property
    def table_names(self):
        return TABLE_NAMES
    
    @property
    def feeder_head_table(self):
        return self.output / TABLE_NAMES[0]
    
    @property
    def feeder_losses_table(self):
        return self.output / TABLE_NAMES[1]
    
    @property
    def metadata_table(self):
        return self.output / TABLE_NAMES[2]
    
    @property
    def thermal_metrics_table(self):
        return self.output / TABLE_NAMES[3]
    
    @property
    def voltage_metrics_table(self):
        return self.output / TABLE_NAMES[4]

    @property
    def snapshot_time_points_table(self):
        return self.output / TABLE_NAMES[5]

    @property
    def hosting_capacity_results(self):
        return self.output.glob("hosting_capacity_*.json")

    @property
    def pv_distances(self):
        return self.output / "weighted_average_pv_distances.csv"

    def __str__(self):
        """Return string representation of the output instance"""
        return str(self.output)

    @abstractmethod
    def validate_output(self, output):
        """Given an output, check if it contains desired reports
        
        Parameters
        ----------
        output: pathlib.Path

        Returns
        -------
        str, the valid output directory containing tables.
        """


class SimulationOutput(OutputBase):
    """Output instance class for handling Jade output"""
    
    @property
    def output_type(self):
        return OutputType.JADE
    
    def validate_output(self, output):
        """Check if output containing all desired reports
        
        Parameters
        ----------
        output: pathlib.Path
        """
        report_files = [output / table_name for table_name in self.table_names[:-1]]
        report_exists = [report_file.exists() for report_file in report_files]
        if not all(report_exists):
            raise ValueError(f"The output '{output}' does not contain valid reports.")
        return output


class PipelineSimulationOutput(OutputBase):
    """Output class for handling Jade pipeline output"""
    
    @property
    def output_type(self):
        return OutputType.JADE_PIPELINE
    
    def validate_output(self, output):
        """Return stage output that contains desired reports
        
        Parameters
        ----------
        output: str or pathlib.Path
        """
        for path in output.iterdir():
            if not path.name.startswith("output-stage"):
                continue
            report_files = [path / table_name for table_name in self.table_names[:-1]]
            report_exists = [report_file.exists() for report_file in report_files]
            if all(report_exists):
                return path
        
        raise IngestionError(f"No stage output in '{output}' contain valid reports")


class DermsSimulationOutput(OutputBase):

    @property
    def output_type(self):
        return OutputType.DERMS

    @property
    def result_file(self):
        for path in self.output.iterdir():
            if not path.is_dir():
                continue
            result_file = self.output / path / "results.json"
            if not result_file.exists():
                continue
            return result_file
        raise IngestionError("No JADE results.json file found")

    @property
    def derms_info_file(self):
        return self.output / DERMS_INFO_FILENAME

    def validate_output(self, output):
        report_files = [output / table_name for table_name in self.table_names[:-1]]
        report_exists = [report_file.exists() for report_file in report_files]
        if not all(report_exists):
            raise IngestionError(f"The output '{output}' does not contain valid reports.")
        return output


def get_creation_time(dir_or_file):
    if platform.system() == "Windows":
        return os.path.getctime(dir_or_file)
    
    stat = os.stat(dir_or_file)
    try:
        return stat.st_birthtime  # For FreeBSD, including Mac
    except AttributeError:
        # Not easy to get creation time on Linux, use modification time
        return stat.st_mtime


def is_from_pipeline(output):
    """Given an output, check if it's from pipeline or not
    
    Parameters
    ----------
    output: str or pathlib.Path
    """
    for path in output.iterdir():
        if path.name.startswith("output-stage"):
            return True
    return False


def is_from_derms(output):
    """Given an output, check if it's from DERMS simulation.
    
    Parameters
    ----------
    output: str or pathlib.Path
    """
    if not isinstance(output, pathlib.Path):
        output = pathlib.Path(output)
    
    derms_info_file = output / DERMS_INFO_FILENAME
    if derms_info_file.exists():
        return True
    return False


def get_simulation_output(output):
    """Given an output directory, return an instance of SimulationOutput or PipelineSimulationOutput
    
    Parameters
    ----------
    output: str or pathlib.Path
    """
    if not isinstance(output, pathlib.Path):
        output = pathlib.Path(output)
    
    if not output.exists():
        raise IngestionError(f"Output path does not exist - {output}.")
    
    if is_from_pipeline(output):
        output = PipelineSimulationOutput(output)
    elif is_from_derms(output):
        output = DermsSimulationOutput(output)
    else:
        output = SimulationOutput(output)
    
    logger.info("Simulation report tables are located in '%s'", output.output)
    
    return output
