import logging
import os
from pathlib import Path

import click


from jade.extensions.generic_command.generic_command_configuration import (
    GenericCommandConfiguration,
)
from jade.extensions.generic_command.generic_command_parameters import (
    GenericCommandParameters,
)
from jade.jobs.job_configuration_factory import create_config_from_file
from jade.loggers import setup_logging
from jade.utils.utils import load_data

from disco.pydss.prescreen_pv_penetration_levels import (
    create_job_key,
    run_prescreen,
    JobKey,
    PRESCREEN_JOBS_OUTPUT,
)


logger = logging.getLogger(__name__)


@click.group()
@click.argument("config_file")
@click.pass_context
def prescreen_pv_penetration_levels(ctx, config_file):
    """Prescreen jobs to find the highest passing PV penetration level for each sample."""
    ctx.obj = create_config_from_file(config_file)


@click.command()
@click.option(
    "-c",
    "--config-file",
    default="prescreen_config.json",
    show_default=True,
    help="Destination config file",
)
@click.pass_context
@click.pass_obj
def create(config, ctx, config_file):
    """Create prescreen jobs from a JADE config file."""
    jobs = set()
    for job in config.iter_pydss_simulation_jobs():
        if not job.model.is_base_case:
            jobs.add(create_job_key(job))

    src_config_file = ctx.parent.params["config_file"]
    dst_config = GenericCommandConfiguration()
    for key in jobs:
        cmd = (
            f"disco prescreen-pv-penetration-levels {src_config_file} run "
            f"--substation={key.substation} --feeder={key.feeder} --placement={key.placement} "
            f"--sample={key.sample}"
        )
        job = GenericCommandParameters(command=cmd, append_output_dir=True)
        dst_config.add_job(job)

    dst_config.dump(config_file)
    print(f"Wrote jobs to {config_file}")


@click.command()
@click.option(
    "-s",
    "--substation",
    required=True,
)
@click.option(
    "-f",
    "--feeder",
    default="None",
    required=False,
)
@click.option(
    "-p",
    "--placement",
    required=True,
)
@click.option(
    "-d",
    "--sample",
    required=True,
    type=int,
)
@click.option(
    "-o",
    "--jade-runtime-output",
    default="output",
    help="output directory",
)
@click.option(
    "--verbose",
    default=False,
    is_flag=True,
    show_default=True,
    help="Enable debug logging",
)
@click.pass_context
@click.pass_obj
def run(config, ctx, substation, feeder, placement, sample, jade_runtime_output, verbose):
    """Run a bisect on the penetration levels for a sample."""
    prescreen_jobs_output = Path(jade_runtime_output) / PRESCREEN_JOBS_OUTPUT
    os.makedirs(prescreen_jobs_output, exist_ok=True)
    filename = os.path.join(
        prescreen_jobs_output,
        "__".join((substation, feeder, placement, str(sample))) + ".log",
    )
    level = logging.DEBUG if verbose else logging.INFO
    setup_logging("disco", filename, console_level=logging.WARNING, packages=["disco"])

    src_config_file = ctx.parent.params["config_file"]
    run_prescreen(
        config,
        src_config_file,
        substation,
        feeder,
        placement,
        sample,
        prescreen_jobs_output,
    )


@click.command()
@click.argument("output_dir")
@click.option(
    "-c",
    "--config-file",
    default="filtered_config.json",
    help="config file with only prescreened jobs",
)
@click.pass_context
@click.pass_obj
def filter_config(config, ctx, config_file, output_dir):
    """Filter the source config file with the prescreening results."""
    os.makedirs(output_dir, exist_ok=True)
    filename = Path(output_dir) / "filter_prescreened_jobs.log"
    setup_logging("disco", filename, console_level=logging.WARNING, packages=["disco"])
    src_config_file = ctx.parent.params["config_file"]
    prescreen_jobs_output = Path(output_dir) / PRESCREEN_JOBS_OUTPUT
    highest_passing_levels = {}
    for filename in prescreen_jobs_output.glob("*.toml"):
        data = load_data(filename)
        key = JobKey(
            substation=data["substation"],
            feeder=data["feeder"],
            placement=data["placement"],
            sample=data["sample"],
        )
        highest_passing_levels[key] = data["highest_passing_penetration_level"]

    jobs_to_remove = []
    for job in config.iter_pydss_simulation_jobs(exclude_base_case=True):
        key = create_job_key(job)
        highest_passing_level = highest_passing_levels.get(key)
        if highest_passing_level is None:
            logger.warning("Skipping job %s because there is no passing penetration level", key)
            jobs_to_remove.append(job)
        elif job.model.deployment.project_data["penetration_level"] > highest_passing_level:
            jobs_to_remove.append(job)

    for job in jobs_to_remove:
        config.remove_job(job)

    config.dump(config_file)
    num = len(jobs_to_remove)
    logger.info(
        "Created %s by filtering %s job(s) that were expected to fail from %s.",
        config_file,
        num,
        src_config_file,
    )


prescreen_pv_penetration_levels.add_command(create)
prescreen_pv_penetration_levels.add_command(run)
prescreen_pv_penetration_levels.add_command(filter_config)
