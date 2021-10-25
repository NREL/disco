import sqlite3

from sqlalchemy import Column, ForeignKey
from sqlalchemy import types
from sqlalchemy.engine import create_engine as _create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker

Base = declarative_base()


class Task(Base):
    __tablename__ = "task"
    id = Column(types.String(length=36), primary_key=True)
    name = Column(types.String(length=128))
    inputs = Column(types.String(length=256))
    output = Column(types.String(length=256))
    image_version = Column(types.String(length=30), nullable=True, default=None)
    disco_version = Column(types.String(length=30), nullable=True, default=None)
    jade_version = Column(types.String(length=30), nullable=True, default=None)
    pydss_version = Column(types.String(length=30), nullable=True, default=None)
    opendssdirect_version = Column(types.String(length=30), nullable=True, default=None)
    opendss_version = Column(types.String(length=30), nullable=True, default=None)
    notes = Column(types.Text, nullable=True, default=None)
    creation_time = Column(types.DateTime)


class Job(Base):
    __tablename__ = "job"
    id = Column(types.String(length=36), primary_key=True)
    task_id = Column(types.String(length=36), ForeignKey("task.id"))
    name = Column(types.String(length=128))
    project_path = Column(types.String(length=256), nullable=True)
    return_code = Column(types.Integer, nullable=True)
    status = Column(types.String(length=20), nullable=True)
    exec_time_s = Column(types.Float, nullable=True)
    completion_time = Column(types.DateTime)


class Scenario(Base):
    __tablename__ = "scenario"
    id = Column(types.String(length=36), primary_key=True)
    job_id = Column(types.String(length=36), ForeignKey("job.id"))
    simulation_type = Column(types.String(length=30))
    name = Column(types.String(length=30))
    start_time = Column(types.DateTime, nullable=True)
    end_time = Column(types.DateTime, nullable=True)


class Report(Base):
    __tablename__ = "report"
    id = Column(types.String(length=36), primary_key=True)
    task_id = Column(types.String(length=36), ForeignKey("task.id"))
    file_name = Column(types.String(length=128))
    file_path = Column(types.String(length=256))
    file_size = Column(types.Integer)
    creation_time = Column(types.DateTime)


class FeederHead(Base):
    __tablename__ = "feeder_head"
    id = Column(types.String(length=36), primary_key=True)
    report_id = Column(types.String(length=36), ForeignKey("report.id"))
    job_id = Column(types.String(length=36), ForeignKey("job.id"), nullable=True)
    name = Column(types.String(length=128))
    substation = Column(types.String(length=128))
    feeder = Column(types.String(length=128))
    placement = Column(types.String(length=10), nullable=True)
    sample = Column(types.Integer, nullable=True)
    penetration_level = Column(types.Integer, nullable=True)
    scenario = Column(types.String(length=128))
    time_point = Column(types.String(length=30), default=None)
    line = Column(types.String(length=128))
    loading = Column(types.Float)
    load_kw = Column(types.Float)
    load_kvar = Column(types.Float)
    reverse_power_flow = Column(types.Boolean)


class FeederLosses(Base):
    __tablename__ = "feeder_losses"
    id = Column(types.String(length=36), primary_key=True)
    report_id = Column(types.String(length=36), ForeignKey("report.id"))
    job_id = Column(types.String(length=36), ForeignKey("job.id"), nullable=True)
    name = Column(types.String(length=128))
    substation = Column(types.String(length=128))
    feeder = Column(types.String(length=128))
    placement = Column(types.String(length=10), nullable=True)
    sample = Column(types.Integer, nullable=True)
    penetration_level = Column(types.Integer, nullable=True)
    scenario = Column(types.String(length=128))
    time_point = Column(types.String(length=30), nullable=True, default=None)
    total_losses_kwh = Column(types.Float)
    line_losses_kwh = Column(types.Float)
    transformer_losses_kwh = Column(types.Float)
    total_load_demand_kwh = Column(types.Float)


class Metadata(Base):
    __tablename__ = "metadata"
    id = Column(types.String(length=36), primary_key=True)
    report_id = Column(types.String(length=36), ForeignKey("report.id"))
    job_id = Column(types.String(length=36), ForeignKey("job.id"), nullable=True)
    name = Column(types.String(length=128))
    substation = Column(types.String(length=128))
    feeder = Column(types.String(length=128))
    placement = Column(types.String(length=10), nullable=True)
    sample = Column(types.Integer, nullable=True)
    penetration_level = Column(types.Integer, nullable=True)
    scenario = Column(types.String(length=128))
    pct_pv_to_load_ratio = Column(types.Float)
    pv_capacity_kw = Column(types.Float)
    load_capacity_kw = Column(types.Float)


class VoltageMetrics(Base):
    __tablename__ = "voltage_metrics"
    id = Column(types.String(length=36), primary_key=True)
    report_id = Column(types.String(length=36), ForeignKey("report.id"))
    job_id = Column(types.String(length=36), ForeignKey("job.id"), nullable=True)
    name = Column(types.String(length=128))
    substation = Column(types.String(length=128))
    feeder = Column(types.String(length=128))
    placement = Column(types.String(length=10), nullable=True)
    sample = Column(types.Integer, nullable=True)
    penetration_level = Column(types.Integer, nullable=True)
    scenario = Column(types.String(length=128))
    time_point = Column(types.String(length=30), nullable=True, default=None)
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


class ThermalMetrics(Base):
    __tablename__ = "thermal_metrics"
    id = Column(types.String(length=36), primary_key=True)
    report_id = Column(types.String(length=36), ForeignKey("report.id"))
    job_id = Column(types.String(length=36), ForeignKey("job.id"), nullable=True)
    name = Column(types.String(length=128))
    substation = Column(types.String(length=128))
    feeder = Column(types.String(length=128))
    placement = Column(types.String(length=10), nullable=True)
    sample = Column(types.Integer, nullable=True)
    penetration_level = Column(types.Integer, nullable=True)
    scenario = Column(types.String(length=128))
    time_point = Column(types.String(length=30), nullable=True, default=None)
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


def create_engine(database):
    engine = _create_engine("sqlite:///" + database)
    return engine


def create_database(database):
    engine = create_engine(database)
    Base.metadata.create_all(engine)
