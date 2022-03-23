<<<<<<< HEAD
import sqlite3

=======
>>>>>>> origin/main
from sqlalchemy import Column, ForeignKey
from sqlalchemy import types
from sqlalchemy.engine import create_engine as _create_engine
from sqlalchemy.ext.declarative import declarative_base
<<<<<<< HEAD
from sqlalchemy.orm import relationship, sessionmaker
=======
from sqlalchemy.orm import relationship
>>>>>>> origin/main

Base = declarative_base()


class Task(Base):
    __tablename__ = "task"
    id = Column(types.String(length=36), primary_key=True)
<<<<<<< HEAD
    name = Column(types.String(length=128))
    inputs = Column(types.String(length=256))
    output = Column(types.String(length=256))
=======
    name = Column(types.String(length=256))
    inputs = Column(types.Text())
    output = Column(types.Text())
>>>>>>> origin/main
    image_version = Column(types.String(length=30), nullable=True, default=None)
    disco_version = Column(types.String(length=30), nullable=True, default=None)
    jade_version = Column(types.String(length=30), nullable=True, default=None)
    pydss_version = Column(types.String(length=30), nullable=True, default=None)
    opendssdirect_version = Column(types.String(length=30), nullable=True, default=None)
<<<<<<< HEAD
    opendss_version = Column(types.String(length=30), nullable=True, default=None)
=======
    opendss_version = Column(types.Text(), nullable=True, default=None)
>>>>>>> origin/main
    notes = Column(types.Text, nullable=True, default=None)
    creation_time = Column(types.DateTime)


class Job(Base):
    __tablename__ = "job"
    id = Column(types.String(length=36), primary_key=True)
    task_id = Column(types.String(length=36), ForeignKey("task.id"))
<<<<<<< HEAD
    name = Column(types.String(length=128))
    project_path = Column(types.String(length=256), nullable=True)
=======
    name = Column(types.String(length=256))
    project_path = Column(types.Text(), nullable=True)
>>>>>>> origin/main
    return_code = Column(types.Integer, nullable=True)
    status = Column(types.String(length=20), nullable=True)
    exec_time_s = Column(types.Float, nullable=True)
    completion_time = Column(types.DateTime)
<<<<<<< HEAD
=======
    task = relationship("Task", primaryjoin="Job.task_id == Task.id")
>>>>>>> origin/main


class Scenario(Base):
    __tablename__ = "scenario"
    id = Column(types.String(length=36), primary_key=True)
    job_id = Column(types.String(length=36), ForeignKey("job.id"))
    simulation_type = Column(types.String(length=30))
    name = Column(types.String(length=30))
    start_time = Column(types.DateTime, nullable=True)
    end_time = Column(types.DateTime, nullable=True)
<<<<<<< HEAD
=======
    job = relationship("Job", primaryjoin="Scenario.job_id == Job.id")
>>>>>>> origin/main


class SnapshotTimePoints(Base):
    __tablename__ = "snapshot_time_points"
    id = Column(types.String(length=36), primary_key=True)
    job_id = Column(types.String(length=36), ForeignKey("job.id"))
<<<<<<< HEAD
    max_pv_load_ratio = Column(types.DateTime, nullable=True)
    max_load = Column(types.DateTime, nullable=True)
    daytime_min_load = Column(types.DateTime, nullable=True)
    pv_minus_load = Column(types.DateTime, nullable=True)
=======
    max_pv_load_ratio = Column(types.DateTime)
    max_load = Column(types.DateTime)
    daytime_min_load = Column(types.DateTime)
    pv_minus_load = Column(types.DateTime)
    job = relationship("Job", primaryjoin="SnapshotTimePoints.job_id == Job.id")
>>>>>>> origin/main


class Report(Base):
    __tablename__ = "report"
    id = Column(types.String(length=36), primary_key=True)
    task_id = Column(types.String(length=36), ForeignKey("task.id"))
<<<<<<< HEAD
    file_name = Column(types.String(length=128))
    file_path = Column(types.String(length=256))
    file_size = Column(types.Integer)
    creation_time = Column(types.DateTime)
=======
    file_name = Column(types.String(length=256))
    file_path = Column(types.Text())
    file_size = Column(types.Integer)
    creation_time = Column(types.DateTime)
    task = relationship("Task", primaryjoin="Report.task_id == Task.id")
>>>>>>> origin/main


class FeederHead(Base):
    __tablename__ = "feeder_head"
    id = Column(types.String(length=36), primary_key=True)
    report_id = Column(types.String(length=36), ForeignKey("report.id"))
    job_id = Column(types.String(length=36), ForeignKey("job.id"), nullable=True)
<<<<<<< HEAD
    name = Column(types.String(length=128))
    substation = Column(types.String(length=128))
    feeder = Column(types.String(length=128))
    placement = Column(types.String(length=10), nullable=True)
    sample = Column(types.Integer, nullable=True)
    penetration_level = Column(types.Integer, nullable=True)
=======
    name = Column(types.String(length=256))
    substation = Column(types.String(length=256))
    feeder = Column(types.String(length=256))
    placement = Column(types.String(length=30), nullable=True)
    sample = Column(types.Float, nullable=True)
    penetration_level = Column(types.Float, nullable=True)
>>>>>>> origin/main
    scenario = Column(types.String(length=128))
    line = Column(types.String(length=128))
    loading = Column(types.Float)
    load_kw = Column(types.Float)
    load_kvar = Column(types.Float)
    reverse_power_flow = Column(types.Boolean)
<<<<<<< HEAD
=======
    job = relationship("Job", primaryjoin="FeederHead.job_id == Job.id")
    report = relationship("Report", primaryjoin="FeederHead.report_id == Report.id")
>>>>>>> origin/main


class FeederLosses(Base):
    __tablename__ = "feeder_losses"
    id = Column(types.String(length=36), primary_key=True)
    report_id = Column(types.String(length=36), ForeignKey("report.id"))
    job_id = Column(types.String(length=36), ForeignKey("job.id"), nullable=True)
<<<<<<< HEAD
    name = Column(types.String(length=128))
    substation = Column(types.String(length=128))
    feeder = Column(types.String(length=128))
    placement = Column(types.String(length=10), nullable=True)
    sample = Column(types.Integer, nullable=True)
    penetration_level = Column(types.Integer, nullable=True)
=======
    name = Column(types.String(length=256))
    substation = Column(types.String(length=256))
    feeder = Column(types.String(length=256))
    placement = Column(types.String(length=30), nullable=True)
    sample = Column(types.Float, nullable=True)
    penetration_level = Column(types.Float, nullable=True)
>>>>>>> origin/main
    scenario = Column(types.String(length=128))
    total_losses_kwh = Column(types.Float)
    line_losses_kwh = Column(types.Float)
    transformer_losses_kwh = Column(types.Float)
    total_load_demand_kwh = Column(types.Float)
<<<<<<< HEAD
=======
    job = relationship("Job", primaryjoin="FeederLosses.job_id == Job.id")
    report = relationship("Report", primaryjoin="FeederLosses.report_id == Report.id")
>>>>>>> origin/main


class Metadata(Base):
    __tablename__ = "metadata"
    id = Column(types.String(length=36), primary_key=True)
    report_id = Column(types.String(length=36), ForeignKey("report.id"))
    job_id = Column(types.String(length=36), ForeignKey("job.id"), nullable=True)
<<<<<<< HEAD
    name = Column(types.String(length=128))
    substation = Column(types.String(length=128))
    feeder = Column(types.String(length=128))
    placement = Column(types.String(length=10), nullable=True)
    sample = Column(types.Integer, nullable=True)
    penetration_level = Column(types.Integer, nullable=True)
=======
    name = Column(types.String(length=256))
    substation = Column(types.String(length=256))
    feeder = Column(types.String(length=256))
    placement = Column(types.String(length=30), nullable=True)
    sample = Column(types.Float, nullable=True)
    penetration_level = Column(types.Float, nullable=True)
>>>>>>> origin/main
    scenario = Column(types.String(length=128))
    pct_pv_to_load_ratio = Column(types.Float)
    pv_capacity_kw = Column(types.Float)
    load_capacity_kw = Column(types.Float)
<<<<<<< HEAD
=======
    job = relationship("Job", primaryjoin="Metadata.job_id == Job.id")
    report = relationship("Report", primaryjoin="Metadata.report_id == Report.id")
>>>>>>> origin/main


class VoltageMetrics(Base):
    __tablename__ = "voltage_metrics"
    id = Column(types.String(length=36), primary_key=True)
    report_id = Column(types.String(length=36), ForeignKey("report.id"))
    job_id = Column(types.String(length=36), ForeignKey("job.id"), nullable=True)
<<<<<<< HEAD
    name = Column(types.String(length=128))
    substation = Column(types.String(length=128))
    feeder = Column(types.String(length=128))
    placement = Column(types.String(length=10), nullable=True)
    sample = Column(types.Integer, nullable=True)
    penetration_level = Column(types.Integer, nullable=True)
=======
    name = Column(types.String(length=256))
    substation = Column(types.String(length=256))
    feeder = Column(types.String(length=256))
    placement = Column(types.String(length=30), nullable=True)
    sample = Column(types.Float, nullable=True)
    penetration_level = Column(types.Float, nullable=True)
>>>>>>> origin/main
    scenario = Column(types.String(length=128))
    node_type = Column(types.String(length=10))
    num_nodes_any_outside_ansi_b = Column(types.Integer)
    num_time_points_with_ansi_b_violations = Column(types.Integer)
    voltage_duration_between_ansi_a_and_b_minutes = Column(types.Integer)
    max_per_node_voltage_duration_outside_ansi_a_minutes = Column(types.Integer)
    moving_average_voltage_duration_outside_ansi_a_minutes = Column(types.Integer)
    num_nodes_always_inside_ansi_a = Column(types.Integer)
    num_nodes_any_outside_ansi_a_always_inside_ansi_b = Column(types.Integer)
    min_voltage = Column(types.Float)
    max_voltage = Column(types.Float)
<<<<<<< HEAD
=======
    job = relationship("Job", primaryjoin="VoltageMetrics.job_id == Job.id")
    report = relationship("Report", primaryjoin="VoltageMetrics.report_id == Report.id")
>>>>>>> origin/main


class ThermalMetrics(Base):
    __tablename__ = "thermal_metrics"
    id = Column(types.String(length=36), primary_key=True)
    report_id = Column(types.String(length=36), ForeignKey("report.id"))
    job_id = Column(types.String(length=36), ForeignKey("job.id"), nullable=True)
<<<<<<< HEAD
    name = Column(types.String(length=128))
    substation = Column(types.String(length=128))
    feeder = Column(types.String(length=128))
    placement = Column(types.String(length=10), nullable=True)
    sample = Column(types.Integer, nullable=True)
    penetration_level = Column(types.Integer, nullable=True)
=======
    name = Column(types.String(length=256))
    substation = Column(types.String(length=256))
    feeder = Column(types.String(length=256))
    placement = Column(types.String(length=30), nullable=True)
    sample = Column(types.Float, nullable=True)
    penetration_level = Column(types.Float, nullable=True)
>>>>>>> origin/main
    scenario = Column(types.String(length=128))
    line_max_instantaneous_loading_pct = Column(types.Float)
    line_max_moving_average_loading_pct = Column(types.Float)
    line_window_size_hours = Column(types.Integer)
    line_num_time_points_with_instantaneous_violations = Column(types.Integer)
    line_num_time_points_with_moving_average_violations = Column(types.Integer)
    line_instantaneous_threshold = Column(types.Float)
    line_moving_average_threshold = Column(types.Float)
    transformer_max_instantaneous_loading_pct = Column(types.Float)
    transformer_max_moving_average_loading_pct = Column(types.Float)
    transformer_window_size_hours = Column(types.Integer)
    transformer_num_time_points_with_instantaneous_violations = Column(types.Integer)
    transformer_num_time_points_with_moving_average_violations = Column(types.Integer)
    transformer_instantaneous_threshold = Column(types.Integer)
    transformer_moving_average_threshold = Column(types.Integer)
<<<<<<< HEAD
=======
    job = relationship("Job", primaryjoin="ThermalMetrics.job_id == Job.id")
    report = relationship("Report", primaryjoin="ThermalMetrics.report_id == Report.id")
>>>>>>> origin/main


class HostingCapacity(Base):
    __tablename__ = "hosting_capacity"
    id = Column(types.String(length=36), primary_key=True)
    task_id = Column(types.String(length=36), ForeignKey("task.id"))
    hc_type = Column(types.String(length=20))
    metric_type = Column(types.String(length=20))
<<<<<<< HEAD
    feeder = Column(types.String(length=128))
    scenario = Column(types.String(length=128))
=======
    feeder = Column(types.String(length=256))
    scenario = Column(types.String(length=256))
>>>>>>> origin/main
    time_point = Column(types.String(length=60), nullable=True, default=None)
    min_hc_pct = Column(types.Float)
    max_hc_pct = Column(types.Float)
    min_hc_kw = Column(types.Float)
    max_hc_kw = Column(types.Float)
<<<<<<< HEAD
=======
    task = relationship("Task", primaryjoin="HostingCapacity.task_id == Task.id")


class PvDistances(Base):
    __tablename__ = "pv_distances"
    job_name = Column(types.String(length=256), primary_key=True)
    substation = Column(types.String(length=256))
    feeder = Column(types.String(length=256))
    placement = Column(types.String(length=256), nullable=True)
    sample = Column(types.Integer, nullable=True)
    penetration_level = Column(types.Integer, nullable=True)
    weighted_average_pv_distance = Column(types.Float)
    option = Column(types.String(length=128))
>>>>>>> origin/main


def create_engine(database):
    engine = _create_engine("sqlite:///" + database)
    return engine


def create_database(database):
    engine = create_engine(database)
    Base.metadata.create_all(engine)
