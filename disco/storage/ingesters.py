import json
import os
import pathlib
from abc import ABC, abstractmethod

from disco.storage.db import (
    Task,
    Scenario,
    Job,
    Report,
    FeederHead,
    FeederLosses,
    Metadata,
    ThermalMetrics,
    VoltageMetrics,
    create_session
)
from disco.storage.exceptions import IngestionError


class IngesterBase(ABC):
    """Abstract ingester class"""
    
    data_class = None
    
    def __init__(self, database, batch_size):
        self.database = database
        self.batch_size = batch_size
        self.session = create_session(database)

    @abstractmethod
    def ingest(self, data):
        """Ingest data into database via sqlalchemy"""
    
    def _perfrom_ingestion(self, data):
        """
        Parameters
        ----------
        data: dict
        """
        if not self.data_class:
            raise IngestionError("No data_class was set for this ingestion.")
        self.session.add(self.data_class(**data))
        self.session.commit()
    
    def _perform_batch_ingestion(self, data):
        """
        Parameters
        ----------
        data: list[dict]
        """
        for i in range(0, len(data), self.batch_size):
            batch = data[i: i+self.batch_size]
            self.session.add_all(batch)
            self.session.commit()


class TaskIngester(IngesterBase):
    """Class used for ingesting parsed task into database"""
    
    data_class = Task

    def ingest(self, task):
        """Ingest task data into task table in database"""
        self._perfrom_ingestion(data=task)
        index = {task["name"]: task["id"]}
        return index


class ScenarioIngester(IngesterBase):
    """Class used for ingesting parsed scenarios into database"""
    
    data_class = Scenario
    
    def ingest(self, scenarios):
        """Ingest a list of scenarios into scenario table in database"""
        objects = [self.data_class(**data) for data in scenarios]
        self._perform_batch_ingestion(data=objects)
        indexes = {self._generate_identifier(item): item["id"] for item in scenarios}
        return indexes
    
    @staticmethod
    def _generate_identifier(item):
        fields = ["job_id", "simulation_type", "name"]
        values = [item[k] for k in fields]
        return " | ".join(values)


class JobIngester(IngesterBase):
    """Class used for ingesting parsed jobs into database"""
    
    data_class = Job
    
    def ingest(self, jobs):
        """Ingest a list of jobs into job table in database"""
        objects = [self.data_class(**data) for data in jobs]
        self._perform_batch_ingestion(data=objects)
        indexes = {job["name"]: job["id"] for job in jobs}
        return indexes


class ReportIngester(IngesterBase):
    """Class used for ingesting parsed reports into database"""
    
    data_class = Report

    def ingest(self, reports):
        """Ingest parsed reports into report table in database"""
        objects = [self.data_class(**report) for report in reports]
        self._perform_batch_ingestion(data=objects)
        indexes = {report["file_name"]: report["id"] for report in reports}
        return indexes


class TableIngesterMixin:
    """Mixin class for handling report table ingestion"""

    def ingest(self, data):
        objects = [self.data_class(**item) for item in data]
        self._perform_batch_ingestion(data=objects)
        indexes = {self._generate_identifier(item): item["id"] for item in data}
        return indexes

    @staticmethod
    def _generate_identifier(item):
        fields = [
            "name",
            "substation",
            "feeder",
            "placement",
            "sample",
            "penetration_level",
            "scenario",
            "time_point"
        ]
        values = [item[k] for k in fields]
        return " | ".join(values)


class FeederHeadIngester(TableIngesterMixin, IngesterBase):
    """Class used for ingesting feeder head data into database"""
    
    data_class = FeederHead


class FeederLossesIngester(TableIngesterMixin, IngesterBase):
    """Class used for ingesting feeder losses data into database"""
    
    data_class = FeederLosses


class MetadataIngester(TableIngesterMixin, IngesterBase):
    """Class used for ingesting metadata into database"""
    
    data_class = Metadata
    
    @staticmethod
    def _generate_identifier(item):
        fields = [
            "name",
            "substation",
            "feeder",
            "placement",
            "sample",
            "penetration_level",
            "scenario"
        ]
        values = [item[k] for k in fields]
        return " | ".join(values)


class ThermalMetricsIngester(TableIngesterMixin, IngesterBase):
    """Class used for ingesting thermal metrics into database"""
    
    data_class = ThermalMetrics
    

class VoltageMetricsIngester(TableIngesterMixin, IngesterBase):
    """Class used for ingesting voltage metrics into database"""
    
    data_class = VoltageMetrics
    
    def _generate_identifier(self, item):
        """Further customize identifier by adding node_type"""
        identifier = super()._generate_identifier(item)
        identifier += f" | {item['node_type']}"
        return identifier


class OutputIngester(IngesterBase):
    """Class used for ingesting all parsed results into SQLite database"""

    def ingest(self, data):
        """Ingest DISCO results into SQLite3 database"""
        indexes = {}   
        indexes["task"] = self._ingest_task(data["task"])
        indexes["jobs"] = self._ingest_jobs(data["jobs"])
        indexes["scenarios"] = self._ingest_scenarios(data["scenarios"])
        indexes["reports"] = self._ingest_reports(data["reports"])
        indexes["feeder_head"] = self._ingest_feeder_head(data["feeder_head"])
        indexes["feeder_losses"] = self._ingest_feeder_losses(data["feeder_losses"])
        indexes["metadata"] = self._ingest_metadata(data["metadata"])
        indexes["thermal_metrics"] = self._ingest_thermal_metrics(data["thermal_metrics"])
        indexes["voltage_metrics"] = self._ingest_voltage_metrics(data["voltage_metrics"])
        return indexes

    def _ingest_task(self, task):
        """Ingest task via TaskIngester
        
        Parameters
        ----------
        task: dict
        """
        ingester = TaskIngester(self.database, self.batch_size)
        index = ingester.ingest(task)
        return index

    def _ingest_jobs(self, jobs):
        """Ingest jobs via JobIngester
        
        Parameters
        ----------
        jobs: list[dict]
        """
        ingester = JobIngester(self.database, self.batch_size)
        indexes = ingester.ingest(jobs)
        return indexes
    
    def _ingest_scenarios(self, scenarios):
        """Ingest scenarios via ScenarioIngester
        
        Parameters
        ----------
        scenarios: list[dict]
        """
        ingester = ScenarioIngester(self.database, self.batch_size)
        indexes = ingester.ingest(scenarios)
        return indexes

    def _ingest_reports(self, reports):
        """Ingest reports via ReportIngester

        Parameters
        ----------
        reports: dict(str=dict)
        """
        ingester = ReportIngester(self.database, self.batch_size)
        indexes = ingester.ingest(reports)
        return indexes
    
    def _ingest_feeder_head(self, feeder_head):
        """Ingest feeder head via FeederHeadIngester
        
        Parameters
        ----------
        feeder_head: list[dict]
        """
        ingester = FeederHeadIngester(self.database, self.batch_size)
        indexes = ingester.ingest(feeder_head)
        return indexes
    
    def _ingest_feeder_losses(self, feeder_losses):
        """Ingest feeder losses via FeederLossesIngester
        
        Parameters
        ----------
        feeder_losses: list[dict]
        """
        ingester = FeederLossesIngester(self.database, self.batch_size)
        indexes = ingester.ingest(feeder_losses)
        return indexes
    
    def _ingest_metadata(self, metadata):
        """Ingest metadata via MetadataIngester
        
        Parameters
        ----------
        metadata: list[dict]
        """
        ingester = MetadataIngester(self.database, self.batch_size)
        indexes = ingester.ingest(metadata)
        return indexes
    
    def _ingest_thermal_metrics(self, thermal_metrics):
        """Ingest thermal metrics via ThermalMetricsIngester
        
        Parameters
        ----------
        thermal_metrics: list[dict]
        """
        ingester = ThermalMetricsIngester(self.database, self.batch_size)
        indexes = ingester.ingest(thermal_metrics)
        return indexes
    
    def _ingest_voltage_metrics(self, voltage_metrics):
        """Ingest voltage metrics via VoltageMetricsIngester
        
        Parameters
        ----------
        voltage_metrics: list[dict]
        """
        ingester = VoltageMetricsIngester(self.database, self.batch_size)
        indexes = ingester.ingest(voltage_metrics)
        return indexes


def dump_storage_index(output, indexes):
    """Dump storage indexes into a JSON file
    
    Parameters
    ----------
    output: str
    indexes: dict(str=dict)
    """
    filename = pathlib.Path(output) / "storage.json"
    with open(filename, "w") as f:
        json.dump(indexes, f, indent=2)
    return filename
