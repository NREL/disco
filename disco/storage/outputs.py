import os
import platform
import pathlib
from abc import ABC, abstractmethod
from datetime import datetime

TABLE_NAMES = [
    "feeder_head_table.csv",
    "feeder_losses_table.csv",
    "metadata_table.csv",
    "thermal_metrics_table.csv",
    "voltage_metrics_table.csv"
]


class OutputBase(ABC):
    """Abstract output class for handling JADE output directory"""

    def __init__(self, output: pathlib.Path) -> None:
        self.output = self.validate_output(output)

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
    def report_files(self):
        return [
            self.output / table_name
            for table_name in self.table_names
        ]
    
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
    
    def validate_output(self, output):
        """Check if output containing all desired reports
        
        Parameters
        ----------
        output: pathlib.Path
        """
        report_files = [output / table for table in self.table_names]
        report_exists = [report_file.exists() for report_file in report_files]
        if not all(report_exists):
            raise ValueError(f"The output '{output}' does not contain valid reports.")
        return output


class PipelineSimulationOutput(OutputBase):
    """Output class for handling Jade pipeline output"""
    
    def validate_output(self, output):
        """Return stage output that contains desired reports
        
        Parameters
        ----------
        output: str or pathlib.Path
        """
        for d in output.iterdir():
            if not str(d.name).startswith("output-stage"):
                continue
            report_files = [d / table for table in self.table_names]
            report_exists = [report_file.exists() for report_file in report_files]
            
            if all(report_exists):
                return d
        
        raise ValueError(f"All stage outputs in '{output}' do not contain valid reports.")


def get_creation_time(dir_or_file):
    if platform.system() == "Windows":
        return os.path.getctime(dir_or_file)
    
    stat = os.stat(dir_or_file)
    try:
        return stat.st_birthtime  # For Mac
    except AttributeError:
        # Not easy to get creation time on Linux, use modification time
        return stat.st_mtime


def is_from_pipeline(output):
    """Given an output, check if it's from pipeline or not
    
    Parameters
    ----------
    output: str or pathlib.Path
    """
    for d in output.iterdir():
        if str(d.name).startswith("output-stage"):
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
        raise ValueError(f"Output path does not exist - {output}.")
    
    if is_from_pipeline(output):
        return PipelineSimulationOutput(output)
    
    return SimulationOutput(output)
