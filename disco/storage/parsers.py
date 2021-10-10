import json
import logging
import os
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from datetime import datetime

import pandas as pd
from sqlalchemy import inspect
from dateutil.parser import parse

import jade
import PyDSS
from jade.utils.utils import load_data
from PyDSS.pydss_project import PyDssProject
from PyDSS.pydss_fs_interface import PyDssZipFileInterface
from disco.enums import SimulationType
from disco.storage.db import Task, Job, Report
from disco.storage.outputs import get_simulation_output, get_creation_time
from disco.version import __version__ as __disco_version__


logger = logging.getLogger(__name__)


class ParserBase(ABC):
    """Abstract parser class"""
    
    @abstractmethod
    def parse(self, output):
        """Given output, parse result data from it"""
    
    def _get_uuid(self):
        """Return an random UUID string"""
        return str(uuid.uuid4())


class TaskParser(ParserBase):

    def __init__(self, name, model_inputs=None, notes=None):
        self.name = name
        self.model_inputs = model_inputs
        self.notes = notes

    def parse(self, output):
        if isinstance(output, str):
            output = get_simulation_output(output)
        
        results = load_data(output.result_file)
        logfile = self._get_job0_run_log_file(output, results)
        
        data = {
            "id": self._get_uuid(),
            "name": self.name,
            "inputs": self.model_inputs,
            "output": str(output),
            "image_version": self._get_image_version(),
            "jade_version": results["jade_version"],
            "pydss_version": self._get_disco_version(logfile),
            "disco_version": self._get_pydss_version(logfile),
            "notes": self.notes,
            "date_created": output.creation_time,
        }
        return data

    def _get_task_id(self):
        return self._get_uuid()
    
    def _get_task_inputs(self):
        if not self.model_inputs:
            raise ValueError("Invalid model model_inputs for the simulation task.")
        return self.model_inputs
    
    def _get_image_version(self):
        """Return the version of docker image"""
        # TODO: get image version if applicable
        return ""
    
    def _get_disco_version(self, logfile):
        """Return the version of disco"""
        version = None
        with open(logfile, "r") as f:  
            for line in f.readlines():
                line = line.strip()
                if "disco version" not in line:
                    continue
                version = line.split("=")[1].strip()
                break
        
        if not version:
            version = __disco_version__
        
        return version
    
    def _get_pydss_version(self, logfile):
        """Return the version of PyDSS"""
        version = None
        with open(logfile, "r") as f:  
            for line in f.readlines():
                line = line.strip()
                if "PyDSS version" not in line:
                    continue
                version = line.split("=")[1].strip()
                break
        
        if not version:
            version = __disco_version__
        
        return version

    @staticmethod
    def _get_job0_run_log_file(output, results):
        job_name = results["results"][0]["name"]
        job_dir = output.job_outputs / job_name
        
        log_file = None
        for d in job_dir.iterdir():
            if not str(d.name).startswith("run.log"):
                continue
            log_file = output.job_outputs / job_name / str(d.name)
        return log_file


class ScenarioParser(ParserBase):
    
    SUFFIX_MAPPING = {
        "max_pv_load_ratio": "Max PV to Load Ratio",
        "max_load": "Max Load",
        "daytime_min_load": "Min Daytime Load",
        "pv_minus_load": "Max PV minus Load"
    }
    
    def __init__(self, job):
        self.job = job
    
    def parse(self, simulation):
        scenario_names = self._get_scenario_names()
        simulation_type = self._get_simulation_type(simulation, scenario_names)
        
        scenarios = []
        if simulation_type == SimulationType.SNAPSHOT:
            timepoints = self._get_snapshot_timepoints(simulation, scenario_names)
            for name in scenario_names:
                scenario = {
                    "id": self._get_scenario_id(),
                    "job_id": self.job["id"],
                    "simulation_type": simulation_type.value,
                    "name": name,
                    "start_time": timepoints[name],
                    "end_time": None
                }
                scenarios.append(scenario)

        elif simulation_type == SimulationType.TIME_SERIES:
            for name in scenario_names:
                scenario = {
                    "id": self._get_scenario_id(),
                    "job_id": self.job["id"],
                    "simulation_type": simulation_type.value,
                    "name": name,
                    "start_time": parse(simulation["start_time"]),
                    "end_time": parse(simulation["end_time"])
                }
                scenarios.append(scenario)

        return scenarios
    
    def _get_scenario_id(self):
        return self._get_uuid()

    def _get_scenario_names(self):
        interface = PyDssZipFileInterface(self.job["project_path"])
        scenario_names = interface._list_scenario_names()
        return scenario_names

    def _get_simulation_type(self, simulation, scenario_names):
        """Convert PyDSS simulation type to DISCO type"""
        simulation_type = simulation["simulation_type"]
        
        if simulation_type == "Snapshot":
            return SimulationType.SNAPSHOT

        if simulation_type == "QSTS":
            if len(scenario_names) > 2:
                return SimulationType.SNAPSHOT
            return SimulationType.TIME_SERIES
        
        return None
    
    def _get_snapshot_timepoints(self, simulation, scenario_names):
        timestamps = {}
        if len(scenario_names) > 2:
            interface = PyDssZipFileInterface(self.job["project_path"])
            data = json.loads(interface.read_file("Exports/snapshot_time_points.json"))
            
            for name in scenario_names:
                key = self.SUFFIX_MAPPING[name.split("__")[1]]
                if key in data:
                    timestamps[name] = parse(data[key]["Timepoints"])
                else:
                    timestamps[name] = None
        else:
            for name in scenario_names:
                timestamps[name] = simulation["start_time"]
        return timestamps


class JobParser(ParserBase):
    """Parse both job and scenario data from output"""
    
    def __init__(self, task):
        self.task = task

    def parse(self, output):
        """Parse jobs data from output"""
        if isinstance(output, str):
            output = get_simulation_output(output)
        
        config = load_data(output.config_file)
        jobs, scenarios = [], []
        for item in config["jobs"]:
            job_dir = output.job_outputs / item["name"]
            job = {
                "id": self._get_job_id(),
                "task_id": self.task["id"],
                "name": item["name"],
                "project_path": self._get_project_path_dir(job_dir),
                "date_created": self._get_creation_time(job_dir)
            }
            jobs.append(job)
            
            # Parse scenarios from job
            scenario_parser = ScenarioParser(job)
            job_scenarios = scenario_parser.parse(item["simulation"])
            scenarios.extend(job_scenarios)
        return jobs, scenarios

    def _get_job_id(self):
        return self._get_uuid()

    def _get_project_path_dir(self, job_dir):
        return str(job_dir / "pydss_project")
    
    def _get_creation_time(self, job_dir):
        timestamp = get_creation_time(job_dir)
        return datetime.fromtimestamp(timestamp)


class ReportParser(ParserBase):

    def __init__(self, task):
        self.task = task

    def parse(self, output):
        """Parse reports information from output"""
        reports = {}
        for report_file in output.report_files:
            report = {
                "id": self._get_report_id(),
                "task_id": self.task["id"],
                "file_name": report_file.name,
                "file_path": str(report_file),
                "file_size": report_file.stat().st_size,
                "date_created": self._get_creation_time(report_file),
            }
            key = report_file.name.split("_table")[0]
            reports[key] = report
        return reports
    
    def _get_report_id(self):
        return self._get_uuid()
    
    def _get_creation_time(self, report_file):
        timestamp = get_creation_time(report_file)
        return datetime.fromtimestamp(timestamp)


class TableParserMixin:

    def _set_record_index(self, data):
        """
        Parameters
        ----------
        data: list[dict], A list of records in dict.
        """
        indexed_data = []
        job_indexes = {job["name"]: job["id"] for job in self.jobs}
        for item in data:
            item.update({
                "id": self._get_uuid(),
                "report_id": self.report["id"],
                "job_id": job_indexes[item["name"]]
            })
            indexed_data.append(item)
        return indexed_data
    
    @staticmethod
    def _replace_none(df):
        df.loc[df["placement"] == "None", "placement"] = None
        df.loc[df["sample"] == "None", "sample"] = None
        df.loc[df["penetration_level"] == "None", "penetration_level"] = None
        return df


class FeederHeadParser(ParserBase, TableParserMixin):

    field_mappings = {
        "FeederHeadLine": "line",
        "FeederHeadLoading": "loading",
        "FeederHeadLoadKW": "load_kw",
        "FeederHeadLoadKVar": "load_kvar",
        "ReversePowerFlow": "reverse_power_flow"
    }

    def __init__(self, report, jobs):
        self.report = report
        self.jobs = jobs
    
    def parse(self, output):
        """Prase feeder head data from output report file"""
        df = pd.read_csv(output.feeder_head_table)
        df = self._replace_none(df)
        data = df.rename(columns=self.field_mappings).to_dict(orient="records")
        data = self._set_record_index(data)
        return data


class FeederLossesParser(ParserBase, TableParserMixin):

    def __init__(self, report, jobs):
        self.report = report
        self.jobs = jobs
    
    def parse(self, output):
        """Prase feeder losses data from output report file"""
        df = pd.read_csv(output.feeder_losses_table)
        df = self._replace_none(df)
        data = df.to_dict(orient="records")
        data = self._set_record_index(data)
        return data


class MetadataParser(ParserBase, TableParserMixin):

    def __init__(self, report, jobs):
        self.report = report
        self.jobs = jobs
    
    def parse(self, output):
        """Prase metadata data from output report file"""
        df = pd.read_csv(output.metadata_table)
        df = self._replace_none(df)
        data = df.to_dict(orient="records")
        data = self._set_record_index(data)
        return data


class ThermalMetricsParser(ParserBase, TableParserMixin):

    def __init__(self, report, jobs):
        self.report = report
        self.jobs = jobs
    
    def parse(self, output):
        """Prase thermal metrics data from output report file"""
        df = pd.read_csv(output.thermal_metrics_table)
        df = self._replace_none(df)
        data = df.to_dict(orient="records")
        data = self._set_record_index(data)
        return data


class VoltageMetricsParser(ParserBase, TableParserMixin):

    def __init__(self, report, jobs):
        self.report = report
        self.jobs = jobs
    
    def parse(self, output):
        """Prase voltage metrics data from output report file"""
        df = pd.read_csv(output.voltage_metrics_table)
        df = self._replace_none(df)
        data = df.to_dict(orient="records")
        data = self._set_record_index(data)
        return data


class OutputParser(ParserBase):

    def __init__(self, task_name, model_inputs=None, notes=None):
        self.task_name = task_name
        self.model_inputs = model_inputs
        self.notes = notes

    def parse(self, output):
        """Prase task, jobs, and reports data from output"""
        result = {}
        
        task = self.parse_task(output=output)
        result["task"] = task
        
        jobs, scenarios = self.parse_jobs(task=task, output=output)
        result["jobs"] = jobs
        result["scenarios"] = scenarios
        
        reports = self.parse_reports(task=task, output=output)
        result["reports"] = reports.values()
        
        feeder_head = self.parse_feeder_head(
            report=reports["feeder_head"],
            jobs=jobs,
            output=output
        )
        result["feeder_head"] = feeder_head
        
        feeder_losses = self.parse_feeder_losses(
            report=reports["feeder_losses"],
            jobs=jobs,
            output=output
        )
        result["feeder_losses"] = feeder_losses
        
        metadata = self.parse_metadata(
            report=reports["metadata"],
            jobs=jobs,
            output=output
        )
        result["metadata"] = metadata
        
        thermal_metrics = self.parse_thermal_metrics(
            report=reports["thermal_metrics"],
            jobs=jobs,
            output=output
        )
        result["thermal_metrics"] = thermal_metrics
        
        voltage_metrics = self.parse_voltage_metrics(
            report=reports["voltage_metrics"],
            jobs=jobs,
            output=output
        )
        result["voltage_metrics"] = voltage_metrics

        return result

    def parse_task(self, output):
        parser = TaskParser(
            name=self.task_name,
            model_inputs=self.model_inputs,
            notes=self.notes
        )
        task = parser.parse(output)
        return task

    def parse_jobs(self, task, output):
        parser = JobParser(task=task)
        jobs, scenarios = parser.parse(output)
        return jobs, scenarios

    def parse_reports(self, task, output):
        parser = ReportParser(task=task)
        reports = parser.parse(output)
        return reports

    def parse_feeder_head(self, report, jobs, output):
        parser = FeederHeadParser(report=report, jobs=jobs)
        feeder_head = parser.parse(output)
        return feeder_head

    def parse_feeder_losses(self, report, jobs, output):
        parser = FeederLossesParser(report=report, jobs=jobs)
        feeder_losses = parser.parse(output)
        return feeder_losses

    def parse_metadata(self, report, jobs, output):
        parser = MetadataParser(report=report, jobs=jobs)
        metadata = parser.parse(output)
        return metadata
    
    def parse_thermal_metrics(self, report, jobs, output):
        parser = ThermalMetricsParser(report=report, jobs=jobs)
        thermal_metrics = parser.parse(output)
        return thermal_metrics

    def parse_voltage_metrics(self, report, jobs, output):
        parser = VoltageMetricsParser(report=report, jobs=jobs)
        voltage_metrics = parser.parse(output)
        return voltage_metrics
