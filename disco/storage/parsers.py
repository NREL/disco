import json
import logging
import os
import pathlib
import uuid
import zipfile
from abc import ABC, abstractmethod
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime
from functools import partial

import pandas as pd
from sqlalchemy import inspect
from dateutil.parser import parse

import jade
from jade.utils.utils import load_data
from dss.v7 import DSS_GR
from opendssdirect._version import __version__ as __opendssdirect_version__
from PyDSS import __version__ as __pydss_version__
from PyDSS.pydss_project import PyDssProject
from disco.enums import SimulationType
from disco.storage.db import Task, Job, Report
from disco.storage.outputs import get_simulation_output, get_creation_time, OutputType
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
        
        data = {
            "id": self._get_uuid(),
            "name": self.name,
            "inputs": self.model_inputs,
            "output": str(output),
            "image_version": self._get_image_version(),
            "notes": self.notes,
            "creation_time": output.creation_time,
        }
        package_versions = self._get_package_versions(output)
        data.update(package_versions)
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
    
    def _get_package_versions(self, output):
        results = load_data(output.result_file)
        package_versions = {
            "disco_version": None,
            "pydss_version": None,
            "jade_version": results["jade_version"],
            "opendssdirect_version": None,
            "opendss_version": None
        }
        
        if output.output_type == OutputType.DERMS:
            data = load_data(output.derms_info_file)
            package_versions["opendssdirect_version"] = data["opendssdirect_version"]
            package_versions["opendss_version"] = \
                self._extract_opendss_svn_number(data["opendss_version"])
        else:
            logfile = self._get_job0_run_log_file(output, results)
            with open(logfile, "r") as f:
                lines = f.readlines()
            
            for line in lines:
                line = line.strip()
                if "disco version" in line:
                    package_versions["disco_version"] = line.split("=")[1].strip()
                if "PyDSS version" in line:
                    package_versions["pydss_version"] = line.split("=")[1].strip()
                if "OpenDSSDirect version" in line:
                    package_versions["opendssdirect_version"] = line.split("=")[1].strip()
                if "OpendDSS version" in line:
                    package_versions["opendss_version"] = \
                        self._extract_opendss_svn_number(line.split("=")[1].strip())
        return package_versions
    
    @staticmethod
    def _extract_opendss_svn_number(value):
        return value.split("OpenDSS SVN ")[1][:4]
    
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


class PyDssScenarioParser(ParserBase):
    
    SUFFIX_MAPPING = {
        "max_pv_load_ratio": "Max PV to Load Ratio",
        "max_load": "Max Load",
        "daytime_min_load": "Min Daytime Load",
        "pv_minus_load": "Max PV minus Load"
    }
    
    def __init__(self, jobs):
        self.jobs = jobs  # Parsed jobs wiht uuid
    
    def parse(self, config_file):
        config = load_data(config_file)
        mapping = {job["name"]: job for job in self.jobs}
        
        jobs = [mapping[item["name"]] for item in config["jobs"]]
        simulations = [item["simulation"] for item in config["jobs"]]
        with ProcessPoolExecutor() as executor:
            results = executor.map(self._parse_job_scenarios, jobs, simulations)
        
        scenarios = [scenario for sublist in results for scenario in sublist]
        return scenarios
    
    def _parse_job_scenarios(self, job, simulation):
        scenario_names = self._get_scenario_names(job)
        simulation_type = self._get_simulation_type(simulation, scenario_names)
        
        scenarios = []
        if simulation_type == SimulationType.SNAPSHOT:
            timepoints = self._get_snapshot_timepoints(job, simulation, scenario_names)
            for name in scenario_names:
                scenario = {
                    "id": self._get_scenario_id(),
                    "job_id": job["id"],
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
                    "job_id": job["id"],
                    "simulation_type": simulation_type.value,
                    "name": name,
                    "start_time": parse(simulation["start_time"]),
                    "end_time": parse(simulation["end_time"])
                }
                scenarios.append(scenario)
        return scenarios
    
    def _get_scenario_id(self):
        return self._get_uuid()

    @staticmethod
    def _get_scenario_names(job):
        # TODO: use PyDSS file interface to read scenaio names
        # Currently, the interface raise error when check scenarios on some jobs
        store_file = pathlib.Path(job["project_path"]) / "store.h5"
        if not os.path.exists(store_file):
            return []

        scenario_names = []
        with pd.HDFStore(store_file, "r") as store:
            for (path, subgroups, _) in store.walk():
                if path == "/Exports":
                    scenario_names = subgroups
                    break
        
        if scenario_names:
            scenario_names.sort()
        
        return scenario_names

    def _get_simulation_type(self, simulation, scenario_names):
        """Convert PyDSS simulation type to DISCO type"""
        simulation_type = simulation["simulation_type"]
        
        if simulation_type.lower() == "snapshot":
            return SimulationType.SNAPSHOT

        if simulation_type.lower() == "qsts":
            if len(scenario_names) > 2:
                return SimulationType.SNAPSHOT
            return SimulationType.TIME_SERIES
        return None
    
    def _get_snapshot_timepoints(self, job, simulation, scenario_names):
        timestamps = {}
        if len(scenario_names) > 2:
            project = pathlib.Path(job["project_path"]) / "project.zip"
            try:
                with zipfile.ZipFile(project, "r") as zf:
                    data = json.loads(zf.read("Exports/snapshot_time_points.json"))
            except KeyError:
                data = {}
            
            for name in scenario_names:
                key = self.SUFFIX_MAPPING[name.split("__")[1]]
                if key in data:
                    timestamps[name] = parse(data[key]["Timepoints"])
                else:
                    timestamps[name] = None
        else:
            for name in scenario_names:
                timestamps[name] = parse(simulation["start_time"])
        return timestamps


class DermsScenaioParser(ParserBase):
    
    def __init__(self, jobs):
        self.jobs = jobs
    
    def _get_scenario_id(self):
        return self._get_uuid()

    def parse(self, derms_info_file):
        with ProcessPoolExecutor() as executor:
            results = executor.map(
                partial(self._parse_job_scenario, derms_info_file=derms_info_file),
                self.jobs
            )
        scenarios = list(results)
        return scenarios
    
    def _parse_job_scenario(self, job, derms_info_file):
        data = load_data(derms_info_file)
        scenario = {
            "id": self._get_scenario_id(),
            "job_id": job["id"],
            "simulation_type": "time-series",
            "name": "derms",
            "start_time": data["start_time"],
            "end_time": data["end_time"]
        }
        return scenario


class JobParser(ParserBase):
    """Parse both job and scenario data from output"""
    
    def __init__(self, task):
        self.task = task

    def parse(self, output):
        """Parse jobs data from output"""
        if isinstance(output, str):
            output = get_simulation_output(output)
        
        results = load_data(output.result_file)
        jobs = [
            {
                "id": self._get_job_id(),
                "task_id": self.task["id"],
                "name": item["name"],
                "project_path": self._get_project_path(output.job_outputs / item["name"]),
                "return_code": item["return_code"],
                "status": item["status"],
                "exec_time_s": item["exec_time_s"],
                "completion_time": datetime.fromtimestamp(item["completion_time"])
            }
            for item in results["results"]
        ]
        return jobs

    def _get_job_id(self):
        return self._get_uuid()

    def _get_project_path(self, job_dir):
        return str(job_dir / "pydss_project")


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
                "creation_time": self._get_creation_time(report_file),
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

    def _set_record_index(self, data, reports_only=False):
        """
        Parameters
        ----------
        data: list[dict], A list of records in dict.
        """
        indexed_data = []
        if reports_only:
            for item in data:
                item.update({
                    "id": self._get_uuid(),
                    "report_id": self.report["id"],
                    "job_id": None
                })
                indexed_data.append(item)
        else:
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
    
    def parse(self, output, reports_only=False):
        """Prase feeder head data from output report file"""
        df = pd.read_csv(output.feeder_head_table)
        df = self._replace_none(df)
        data = df.rename(columns=self.field_mappings).to_dict(orient="records")
        data = self._set_record_index(data, reports_only=reports_only)
        return data


class FeederLossesParser(ParserBase, TableParserMixin):

    def __init__(self, report, jobs):
        self.report = report
        self.jobs = jobs
    
    def parse(self, output, reports_only=False):
        """Prase feeder losses data from output report file"""
        df = pd.read_csv(output.feeder_losses_table)
        df = self._replace_none(df)
        data = df.to_dict(orient="records")
        data = self._set_record_index(data, reports_only=reports_only)
        return data


class MetadataParser(ParserBase, TableParserMixin):

    def __init__(self, report, jobs):
        self.report = report
        self.jobs = jobs
    
    def parse(self, output, reports_only=False):
        """Prase metadata data from output report file"""
        df = pd.read_csv(output.metadata_table)
        df = self._replace_none(df)
        data = df.to_dict(orient="records")
        data = self._set_record_index(data, reports_only=reports_only)
        return data


class ThermalMetricsParser(ParserBase, TableParserMixin):

    def __init__(self, report, jobs):
        self.report = report
        self.jobs = jobs
    
    def parse(self, output, reports_only=False):
        """Prase thermal metrics data from output report file"""
        df = pd.read_csv(output.thermal_metrics_table)
        df = self._replace_none(df)
        data = df.to_dict(orient="records")
        data = self._set_record_index(data, reports_only=reports_only)
        return data


class VoltageMetricsParser(ParserBase, TableParserMixin):

    def __init__(self, report, jobs):
        self.report = report
        self.jobs = jobs
    
    def parse(self, output, reports_only=False):
        """Prase voltage metrics data from output report file"""
        df = pd.read_csv(output.voltage_metrics_table)
        df = self._replace_none(df)
        data = df.to_dict(orient="records")
        data = self._set_record_index(data, reports_only=reports_only)
        return data


class OutputParser(ParserBase):

    def __init__(self, task_name, model_inputs=None, notes=None):
        self.task_name = task_name
        self.model_inputs = model_inputs
        self.notes = notes

    def parse(self, output, reports_only=False):
        """Prase task, jobs, and reports data from output"""
        result = {}
        
        task = self.parse_task(output=output)
        result["task"] = task
        
        if reports_only:
            jobs = []
            scenarios = []
        else:
            jobs = self.parse_jobs(task=task, output=output)
            scenarios = self.parse_scenarios(jobs=jobs, output=output)
        
        result["jobs"] = jobs
        result["scenarios"] = scenarios
        
        reports = self.parse_reports(task=task, output=output)
        result["reports"] = reports.values()
        
        feeder_head = self.parse_feeder_head(
            report=reports["feeder_head"],
            jobs=jobs,
            output=output,
            reports_only=reports_only
        )
        result["feeder_head"] = feeder_head
        
        feeder_losses = self.parse_feeder_losses(
            report=reports["feeder_losses"],
            jobs=jobs,
            output=output,
            reports_only=reports_only
        )
        result["feeder_losses"] = feeder_losses
        
        metadata = self.parse_metadata(
            report=reports["metadata"],
            jobs=jobs,
            output=output,
            reports_only=reports_only
        )
        result["metadata"] = metadata
        
        thermal_metrics = self.parse_thermal_metrics(
            report=reports["thermal_metrics"],
            jobs=jobs,
            output=output,
            reports_only=reports_only
        )
        result["thermal_metrics"] = thermal_metrics
        
        voltage_metrics = self.parse_voltage_metrics(
            report=reports["voltage_metrics"],
            jobs=jobs,
            output=output,
            reports_only=reports_only
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
        jobs = parser.parse(output)
        return jobs

    def parse_scenarios(self, jobs, output):
        if output.output_type == OutputType.DERMS:
            parser = DermsScenaioParser(jobs)
            scenarios = parser.parse(output.derms_info_file)
        else:
            parser = PyDssScenarioParser(jobs)
            scenarios = parser.parse(output.config_file)
        return scenarios

    def parse_reports(self, task, output):
        parser = ReportParser(task=task)
        reports = parser.parse(output)
        return reports

    def parse_feeder_head(self, report, jobs, output, reports_only=False):
        parser = FeederHeadParser(report=report, jobs=jobs)
        feeder_head = parser.parse(output, reports_only=reports_only)
        return feeder_head

    def parse_feeder_losses(self, report, jobs, output, reports_only=False):
        parser = FeederLossesParser(report=report, jobs=jobs)
        feeder_losses = parser.parse(output, reports_only=reports_only)
        return feeder_losses

    def parse_metadata(self, report, jobs, output, reports_only=False):
        parser = MetadataParser(report=report, jobs=jobs)
        metadata = parser.parse(output, reports_only=reports_only)
        return metadata
    
    def parse_thermal_metrics(self, report, jobs, output, reports_only=False):
        parser = ThermalMetricsParser(report=report, jobs=jobs)
        thermal_metrics = parser.parse(output, reports_only=reports_only)
        return thermal_metrics

    def parse_voltage_metrics(self, report, jobs, output, reports_only=False):
        parser = VoltageMetricsParser(report=report, jobs=jobs)
        voltage_metrics = parser.parse(output, reports_only=reports_only)
        return voltage_metrics
