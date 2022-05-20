import logging
import shutil
import sys
import time
from collections import namedtuple
from pathlib import Path

import click

from jade.common import CONFIG_FILE, JOBS_OUTPUT_DIR
from jade.extensions.generic_command import GenericCommandConfiguration
from jade.extensions.generic_command import GenericCommandParameters
from jade.loggers import setup_logging
from jade.result import ResultsSummary
from jade.utils.utils import get_cli_string, load_data, dump_data

from disco.common import EXIT_CODE_GOOD, EXIT_CODE_GENERIC_ERROR
from disco.cli.make_upgrade_tables import (
    get_upgrade_summary_table,
    get_total_upgrade_costs_table,
    serialize_table,
)
from disco.exceptions import DiscoBaseException, get_error_code_from_exception
from disco.models.base import OpenDssDeploymentModel
from disco.models.upgrade_cost_analysis_generic_model import (
    UpgradeCostAnalysisSimulationModel,
    UpgradeResultModel,
    EquipmentTypeUpgradeCostsModel,
    UpgradeSummaryResultsModel,
)
from disco.extensions.upgrade_simulation.upgrade_parameters import UpgradeParameters
from disco.extensions.upgrade_simulation.upgrade_simulation import UpgradeSimulation


logger = logging.getLogger(__name__)


JobInfo = namedtuple("JobInfo", ["name"])

AGGREGATION_JOB_NAME = "aggregate-results"


@click.command()
@click.argument("upgrades-config-file", type=click.Path(exists=True))
def check_config(upgrades_config_file):
    """Check that the upgrade cost analysis config file is valid."""
    setup_logging(__name__, None, console_level=logging.INFO, packages=["disco"])
    ret = 0
    try:
        UpgradeCostAnalysisSimulationModel.from_file(upgrades_config_file)
        print(f"UpgradeCostAnalysis config file {upgrades_config_file} is valid")
    except Exception:
        logger.exception("Failed to validate UpgradeCostAnalysis config file")
        ret = 1
    sys.exit(ret)


@click.command()
@click.argument("upgrades-config-file", type=click.Path(exists=True))
@click.option(
    "-c",
    "--config-file",
    type=str,
    default="config.json",
    show_default=True,
    help="JADE config filename",
)
@click.option(
    "--fmt",
    type=click.Choice(["csv", "json"]),
    default="json",
    show_default=True,
    help="Output data format",
)
def config(upgrades_config_file, config_file, fmt):
    """Create a JADE config file from a set of generic inputs."""
    config = UpgradeCostAnalysisSimulationModel.from_file(upgrades_config_file)
    jade_config = GenericCommandConfiguration()
    base_cmd = f"disco upgrade-cost-analysis run {upgrades_config_file} --no-aggregate-results"
    blocking_jobs = set()
    for job in config.jobs:
        cmd = f"{base_cmd} --job-name {job.name}"
        jade_job = GenericCommandParameters(
            command=cmd,
            name=job.name,
            estimated_run_minutes=job.estimated_run_minutes,
            append_output_dir=True,
        )
        jade_config.add_job(jade_job)
        blocking_jobs.add(job.name)

    aggregation_job = GenericCommandParameters(
        command=f"disco upgrade-cost-analysis aggregate-results --fmt {fmt}",
        name=AGGREGATION_JOB_NAME,
        append_output_dir=True,
        blocked_by=blocking_jobs,
    )
    jade_config.add_job(aggregation_job)

    jade_config.dump(config_file)
    print(f"Created JADE configuration file {config_file}")


@click.command()
@click.argument("config_file", type=click.Path(exists=True))
@click.option(
    "--aggregate-results/--no-aggregate-results",
    default=True,
    show_default=True,
    help="Aggregate results from all jobs in config_file.",
)
@click.option(
    "-j",
    "--job-name",
    type=str,
    help="If set, only run the job matching this name. Otherwise, run all jobs in config_file.",
)
@click.option(
    "-o",
    "--jade-runtime-output",
    default="output",
    help="Output directory",
    callback=lambda _, __, x: Path(x),
)
@click.option(
    "--fmt",
    type=click.Choice(["csv", "json"]),
    default="json",
    show_default=True,
    help="Output data format. Only applicable if aggregate_results is true.",
)
@click.option(
    "-f",
    "--force",
    is_flag=True,
    default=False,
    show_default=True,
    help="Overwrite output directory if it exists.",
)
@click.option(
    "--verbose", is_flag=True, default=False, show_default=True, help="Enable verbose logging"
)
def run(config_file, aggregate_results, job_name, jade_runtime_output, fmt, force, verbose):
    """Run upgrade cost analysis simulation(s) from a config file."""
    jobs_output_dir = jade_runtime_output / JOBS_OUTPUT_DIR
    jobs_output_dir.mkdir(parents=True, exist_ok=True)
    config = UpgradeCostAnalysisSimulationModel.from_file(config_file)

    if job_name is None:
        jobs = config.jobs
        log_file_dir = jade_runtime_output
        log_filename = "run_upgrade_cost_analysis.log"
    else:
        jobs = []
        for job in config.jobs:
            if job.name == job_name:
                jobs.append(job)
                break
        if not jobs:
            print(f"Job {job_name} is not defined in {config_file}", file=sys.stderr)
            sys.exit(1)
        log_file_dir = jobs_output_dir / job_name
        log_filename = f"run_upgrade_cost_analysis__{job_name}.log"

    for job in jobs:
        _check_job_dir(jobs_output_dir / job.name, force)

    log_file_dir.mkdir(exist_ok=True)
    level = logging.DEBUG if verbose else logging.INFO
    log_file = log_file_dir / log_filename
    setup_logging(__name__, log_file, console_level=level, packages=["disco"])
    logger.info(get_cli_string())

    batch_return_code = EXIT_CODE_GOOD
    all_failed = True
    for job in jobs:
        logger.info("Run upgrades simulation for job %s", job.name)
        start = time.time()
        ret = EXIT_CODE_GOOD
        try:
            run_job(job, config, jobs_output_dir, verbose)
            all_failed = False
        except DiscoBaseException as exc:
            logger.exception("Unexpected DISCO error in upgrade cost analysis job=%s", job.name)
            ret = get_error_code_from_exception(type(exc))
        except Exception:
            logger.exception("Unexpected error in upgrade cost analysis job=%s", job.name)
            ret = EXIT_CODE_GENERIC_ERROR
        logger.info(
            "Completed upgrades simulation for job %s return_code=%s duration=%s seconds",
            job.name,
            ret,
            time.time() - start,
        )
        if ret != EXIT_CODE_GOOD:
            batch_return_code = ret
        _write_job_return_code(jobs_output_dir, job.name, ret)

    if aggregate_results and not all_failed:
        job_names = [x.name for x in jobs]
        _aggregate_results(jade_runtime_output, log_file, job_names, fmt)

    # This will return an error if any job fails. If the user cares about differentiating
    # passes and failures then they should run the jobs through Jade.
    sys.exit(batch_return_code)


def _check_job_dir(job_output_dir, force):
    if job_output_dir.exists():
        if force:
            shutil.rmtree(job_output_dir)
        else:
            print(
                f"{job_output_dir} already exists. Choose a different path or set --force to overwrite.",
                file=sys.stderr,
            )
            sys.exit(1)


def _write_job_return_code(output_dir, job_name, return_code):
    _get_return_code_filename(output_dir, job_name).write_text(f"{return_code}\n")


def _read_job_return_code(output_dir, job_name):
    return int(_get_return_code_filename(output_dir, job_name).read_text().strip())


def _delete_job_return_code_file(output_dir, job_name):
    _get_return_code_filename(output_dir, job_name).unlink()


def _get_return_code_filename(output_dir, job_name):
    return output_dir / job_name / "return_code"


def run_job(job, config, jobs_output_dir, verbose):
    job_output_dir = jobs_output_dir / job.name
    job_output_dir.mkdir(exist_ok=True)
    job = UpgradeParameters(
        model_type="UpgradeCostAnalysisModel",
        name=job.name,
        deployment=OpenDssDeploymentModel(
            deployment_file=job.opendss_model_file,
            feeder="NA",
        ),
    )

    global_config = {
        "thermal_upgrade_params": config.thermal_upgrade_params.dict(),
        "voltage_upgrade_params": config.voltage_upgrade_params.dict(),
        "upgrade_simulation_params": {
            "enable_pydss_controller": config.enable_pydss_controllers,
        },
        "upgrade_cost_database": config.upgrade_cost_database,
        "dc_ac_ratio": config.dc_ac_ratio,
    }
    global_config["upgrade_simulation_params"]["pydss_controller"] = None
    if (config.pydss_controllers.pv_controller is not None) and config.enable_pydss_controllers:
        global_config["upgrade_simulation_params"]["pydss_controller"] = (
            config.pydss_controllers.pv_controller.dict(),
        )

    simulation = UpgradeSimulation(
        job=job,
        job_global_config=global_config,
        output=jobs_output_dir,
    )
    simulation.run(
        dc_ac_ratio=global_config["dc_ac_ratio"],
        enable_pydss_solve=global_config["upgrade_simulation_params"]["enable_pydss_controller"],
        pydss_controller_model=config.pydss_controllers.pv_controller,
        thermal_config=global_config["thermal_upgrade_params"],
        voltage_config=global_config["voltage_upgrade_params"],
        cost_database_filepath=global_config["upgrade_cost_database"],
        verbose=verbose,
    )


@click.command()
@click.option(
    "-o",
    "--jade-runtime-output",
    required=True,
    help="Output directory",
    callback=lambda _, __, x: Path(x),
)
@click.option(
    "--fmt",
    type=click.Choice(["csv", "json"]),
    default="json",
    show_default=True,
    help="Output data format",
)
@click.option(
    "--verbose", is_flag=True, default=False, show_default=True, help="Enable verbose logging"
)
def aggregate_results(jade_runtime_output, fmt, verbose):
    """Aggregate results on a directory of upgrade cost analysis simulations."""
    level = logging.DEBUG if verbose else logging.INFO
    log_file = jade_runtime_output / "upgrade_cost_analysis_aggregation.log"
    setup_logging(__name__, log_file, console_level=level, packages=["disco"])
    logger.info(get_cli_string())
    jade_config_file = jade_runtime_output / CONFIG_FILE
    if not jade_config_file.exists():
        logger.error("aggregate-results is only supported when run through JADE.")
        sys.exit(1)

    job_names = (x["name"] for x in load_data(jade_config_file)["jobs"])
    _aggregate_results(jade_runtime_output, log_file, job_names, fmt)


def _aggregate_results(jade_runtime_output, log_file, job_names, fmt):
    upgrade_summary_table = []
    upgrade_costs_table = []
    job_outputs = []
    jobs_output_dir = jade_runtime_output / JOBS_OUTPUT_DIR
    output_json = {
        "violation_summary": [],
        "upgrade_costs": [],
        "outputs": {"log_file": str(log_file), "jobs": []},
    }

    for name in job_names:
        job_path = jobs_output_dir / name
        job_info = JobInfo(name)
        summary_table = get_upgrade_summary_table(job_path, job_info)
        costs_table = get_total_upgrade_costs_table(job_path, job_info)
        return_code = (
            0 if name == AGGREGATION_JOB_NAME else _read_job_return_code(jobs_output_dir, name)
        )
        outputs = {
            "upgraded_opendss_model_file": str(jobs_output_dir / name / "upgraded_master.dss"),
            "return_code": return_code,
            "feeder_stats": str(jobs_output_dir / name / "feeder_stats.json"),
        }
        output_json["outputs"]["jobs"].append(outputs)
        if name != AGGREGATION_JOB_NAME:
            _delete_job_return_code_file(jobs_output_dir, name)
        if fmt == "csv":
            upgrade_summary_table += summary_table
            upgrade_costs_table += costs_table
        else:
            # It might seem odd to go from dict to model back to dict, but this validates
            # fields and types.
            for result in summary_table:
                upgrade_summary_table.append(UpgradeResultModel(**result).dict())
            for result in costs_table:
                upgrade_costs_table.append(EquipmentTypeUpgradeCostsModel(**result).dict())

    if upgrade_summary_table:
        if fmt == "csv":
            filename = jade_runtime_output / "upgrade_summary.csv"
            serialize_table(upgrade_summary_table, filename)
        else:
            output_json["violation_summary"] += upgrade_summary_table
    else:
        logger.warning("There were no upgrade_summary results.")

    if upgrade_costs_table:
        if fmt == "csv":
            filename = jade_runtime_output / "total_upgrade_costs.csv"
            serialize_table(upgrade_costs_table, filename)
        else:
            output_json["upgrade_costs"] += upgrade_costs_table
    else:
        logger.warning("There were no upgrade_cost results.")

    if fmt == "json":
        filename = jade_runtime_output / "upgrade_summary.json"
        dump_data(UpgradeSummaryResultsModel(**output_json).dict(), filename, indent=2)
        logger.info("Output summary data to %s", filename)


@click.group()
def upgrade_cost_analysis():
    """Commands related to running upgrade cost analysis simulations"""


upgrade_cost_analysis.add_command(check_config)
upgrade_cost_analysis.add_command(config)
upgrade_cost_analysis.add_command(run)
upgrade_cost_analysis.add_command(aggregate_results)
