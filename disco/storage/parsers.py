import logging
import uuid
from abc import ABC, abstractmethod
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime
from functools import partial
from pathlib import Path

import pandas as pd
from dateutil.parser import parse

from jade.utils.utils import load_data
from opendssdirect._version import __version__ as __opendssdirect_version__
from PyDSS import __version__ as __pydss_version__
from PyDSS.common import SnapshotTimePointSelectionMode
from disco.pydss.common import SNAPSHOT_SCENARIO, TIME_SERIES_SCENARIOS, SCENARIO_NAME_DELIMITER
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
        logger.info("Parsing data - 'task'...")
        
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


class JobParser(ParserBase):
    """Parse jobs data from output"""
    
    def __init__(self, task):
        self.task = task

    def parse(self, output):
        """Parse jobs data from output"""
        logger.info("Parsing data - 'jobs'...")
        
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


class PyDssScenarioParser(ParserBase):
    
    def __init__(self, jobs):
        self.jobs = jobs  # Parsed jobs wiht uuid
    
    def _get_scenario_id(self):
        return self._get_uuid()

    def parse(self, config_file, snapshot_time_points_table):
        logger.info("Parsing data - 'scenarios'...")
        
        if snapshot_time_points_table.exists():
            return self._parse_scenarios_from_snapshot_time_points(snapshot_time_points_table)
        
        return self._parse_scenarios_from_config_file(config_file)
    
    def _parse_scenarios_from_snapshot_time_points(self, snapshot_time_points_table):
        df = None
        try:
            df = pd.read_csv(snapshot_time_points_table)
        except pd.errors.EmptyDataError:
            pass
        if df is None or df.empty:
            time_points = {}
        else:
            time_points = {item["name"]: item for item in df.to_dict(orient="records")}
        
        scenarios = []
        for job in self.jobs:
            if job["name"] not in time_points:
                continue
            tp = time_points[job["name"]]
            for scenario_name in TIME_SERIES_SCENARIOS:
                for mode in SnapshotTimePointSelectionMode:
                    if mode == SnapshotTimePointSelectionMode.NONE:
                        continue
                    _scenario_name = f"{scenario_name}{SCENARIO_NAME_DELIMITER}{mode.value}"
                    scenarios.append({
                        "id": self._get_scenario_id(),
                        "job_id": job["id"],
                        "simulation_type": "snapshot",
                        "name": _scenario_name,
                        "start_time": tp.get(mode.value),
                        "end_time": None
                    })
        return scenarios
    
    def _parse_scenarios_from_config_file(self, config_file):
        config = load_data(config_file)
        simulations = {item["name"]: item["simulation"] for item in config["jobs"]}
        simulation_type = config["jobs"][0]["simulation"]["simulation_type"].lower()
        
        scenarios = []
        if simulation_type == "snapshot":
            for job in self.jobs:
                simulation = simulations[job["name"]]
                scenario = {
                    "id": self._get_scenario_id(),
                    "job_id": job["id"],
                    "simulation_type": "snapshot",
                    "name": SNAPSHOT_SCENARIO,
                    "start_time": parse(simulation["start_time"]),
                    "end_time": None
                }
                scenarios.append(scenario)
            return scenarios
        
        if simulation_type == "qsts":
            for job in self.jobs:
                simulation = simulations[job["name"]]
                job_scenarios = [
                    {
                        "id": self._get_scenario_id(),
                        "job_id": job["id"],
                        "simulation_type": "time-series",
                        "name": scenario_name,
                        "start_time": parse(simulation["start_time"]),
                        "end_time": parse(simulation["end_time"])
                    }
                    for scenario_name in TIME_SERIES_SCENARIOS
                ]
                scenarios.extend(job_scenarios)
            return scenarios
        
        raise ValueError(
            f"The simulation_type '{simulation_type}' for storage is not supported currently."
        )


class DermsScenaioParser(ParserBase):
    
    def __init__(self, jobs):
        self.jobs = jobs
    
    def _get_scenario_id(self):
        return self._get_uuid()

    def parse(self, derms_info_file):
        logger.info("Parsing data - 'scenarios'...")
        
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


class ReportParser(ParserBase):

    def __init__(self, task):
        self.task = task

    def parse(self, output):
        """Parse reports information from output"""
        logger.info("Parsing data - 'reports'...")
        
        reports = {}
        if output.snapshot_time_points_table.exists():
            table_names = output.table_names
        else:
            table_names = output.table_names[:-1]
        report_files = [output.output / table_name for table_name in table_names]
        
        for report_file in report_files:
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
        """Parse feeder head data from output report file"""
        logger.info("Parsing data - 'feeder_head'...")
        df = pd.read_csv(output.feeder_head_table)
        data = df.rename(columns=self.field_mappings).to_dict(orient="records")
        data = self._set_record_index(data)
        return data


class FeederLossesParser(ParserBase, TableParserMixin):

    def __init__(self, report, jobs):
        self.report = report
        self.jobs = jobs
    
    def parse(self, output):
        """Parse feeder losses data from output report file"""
        logger.info("Parsing data - 'feeder_losses'...")
        df = pd.read_csv(output.feeder_losses_table)
        data = df.to_dict(orient="records")
        data = self._set_record_index(data)
        return data


class MetadataParser(ParserBase, TableParserMixin):

    def __init__(self, report, jobs):
        self.report = report
        self.jobs = jobs
    
    def parse(self, output):
        """Parse metadata data from output report file"""
        logger.info("Parsing data - 'metadata'...")
        df = pd.read_csv(output.metadata_table)
        data = df.to_dict(orient="records")
        data = self._set_record_index(data)
        return data


class ThermalMetricsParser(ParserBase, TableParserMixin):

    def __init__(self, report, jobs):
        self.report = report
        self.jobs = jobs
    
    def parse(self, output):
        """Parse thermal metrics data from output report file"""
        logger.info("Parsing data - 'thermal_metrics'...")
        df = pd.read_csv(output.thermal_metrics_table)
        data = df.to_dict(orient="records")
        data = self._set_record_index(data)
        return data


class VoltageMetricsParser(ParserBase, TableParserMixin):

    def __init__(self, report, jobs):
        self.report = report
        self.jobs = jobs
    
    def parse(self, output):
        """Parse voltage metrics data from output report file"""
        logger.info("Parsing data - 'voltage_metrics'...")
        df = pd.read_csv(output.voltage_metrics_table)
        data = df.to_dict(orient="records")
        data = self._set_record_index(data)
        return data


class SnapshotTimePointsParser(ParserBase, TableParserMixin):
    
    def __init__(self, report, jobs):
        self.report = report
        self.jobs = jobs
    
    def parse(self, output):
        """Parse time points data for snapshot simulation"""
        logger.info("Parsing data - 'snapshot_time_points'...")
        try:
            df = pd.read_csv(output.snapshot_time_points_table)
            data = df.to_dict(orient="records")
        except pd.errors.EmptyDataError:
            data = {}
        data = self._set_record_index(data)
        return data


class HostingCapacityParser(ParserBase):

    def __init__(self, task):
        self.task = task
    
    def _get_hc_id(self):
        return self._get_uuid()
    
    def parse(self, output):
        logger.info("Parsing data - 'hosting_capacity'...")
        
        data = []
        for result_file in output.hosting_capacity_results:
            results = self._parse_result(result_file)
            data.extend(list(results))
        return data

    def _parse_result(self, hosting_capacity_filename):
        items = hosting_capacity_filename.name.split(".")[0].split(SCENARIO_NAME_DELIMITER)
        hc_type = "summary_by_metric" if "summary" in items[0] else "overall"
        scenario = items[1]
        time_point = None if len(items) != 3 else items[2]
        
        result = load_data(hosting_capacity_filename)
        if hc_type == "summary_by_metric":
            data = [
                {
                    "id": self._get_hc_id(),
                    "task_id": self.task["id"],
                    "hc_type": hc_type,
                    "metric_type": metric_type,
                    "feeder": feeder,
                    "scenario": scenario,
                    "time_point": time_point,
                    "min_hc_pct": value["min_hc_pct"],
                    "max_hc_pct": value["max_hc_pct"],
                    "min_hc_kw": value["min_hc_kw"],
                    "max_hc_kw": value["max_hc_kw"]
                }
                for feeder, values in result.items()
                for metric_type, value in values.items()
            ]
        elif hc_type == "overall":
            data = [
                {
                    "id": self._get_hc_id(),
                    "task_id": self.task["id"],
                    "hc_type": hc_type,
                    "metric_type": None,
                    "feeder": feeder,
                    "scenario": scenario,
                    "time_point": time_point,
                    "min_hc_pct": value["min_hc_pct"],
                    "max_hc_pct": value["max_hc_pct"],
                    "min_hc_kw": value["min_hc_kw"],
                    "max_hc_kw": value["max_hc_kw"]
                }
                for feeder, value in result.items()
            ]
        return data


class PvDistancesParser(ParserBase, TableParserMixin):

    def parse(self, model_inputs):
        """Parse PV distances data from output report file"""
        logger.info("Parsing data - 'pv_distances'...")
        path = Path(model_inputs) / "weighted_average_pv_distances.csv"
        if path.exists():
            df = pd.read_csv(path)
            data = df.to_dict(orient="records")
        else:
            data = {}
        return data


class OutputParser(ParserBase):

    def __init__(self, task_name, model_inputs=None, notes=None):
        self.task_name = task_name
        self.model_inputs = model_inputs
        self.notes = notes

    def parse(self, output):
        """Parse task, jobs, and reports data from output"""
        logger.info("Parsing results from output directory...")
        
        result = {}
        
        task = self.parse_task(output=output)
        result["task"] = task
        
        jobs = self.parse_jobs(task=task, output=output)
        scenarios = self.parse_scenarios(jobs=jobs, output=output)
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
        
        if output.snapshot_time_points_table.exists():
            snapshot_time_points = self.parse_snapshot_time_points(
                report=reports["snapshot_time_points"],
                jobs=jobs,
                output=output
            )
            result["snapshot_time_points"] = snapshot_time_points
        
        hosting_capacity = self.parse_hosting_capacity(
            task=task,
            output=output
        )
        result["hosting_capacity"] = hosting_capacity
        pv_distances = self.parse_pv_distances(self.model_inputs)
        if pv_distances:
            result["pv_distances"] = self.parse_pv_distances(self.model_inputs)
        
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
            scenarios = parser.parse(output.config_file, output.snapshot_time_points_table)
        return scenarios

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

    def parse_snapshot_time_points(self, report, jobs, output):
        parser = SnapshotTimePointsParser(report=report, jobs=jobs)
        time_points = parser.parse(output)
        return time_points

    def parse_hosting_capacity(self, task, output):
        parser = HostingCapacityParser(task=task)
        hosting_capacity = parser.parse(output=output)
        return hosting_capacity

    def parse_pv_distances(self, model_inputs):
        return PvDistancesParser().parse(model_inputs)
