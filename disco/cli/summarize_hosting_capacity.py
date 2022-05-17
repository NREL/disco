"""Create summary files for hosting capacity results."""

import json
import logging
import re
import shutil
import sys
import time
from pathlib import Path
from tempfile import NamedTemporaryFile

import click
import chevron

from jade.loggers import setup_logging
from jade.utils.subprocess_manager import check_run_command
from jade.utils.utils import get_cli_string, load_data, dump_data

import disco


logger = logging.getLogger("summarize_hc_metrics")

DISCO = Path(disco.__path__[0]).parent
TEMPLATE_FILE = DISCO / "disco" / "postprocess" / "query.mustache"
HOSTING_CAPACITY_THRESHOLDS = DISCO / "disco" / "postprocess" / "config" / "hc_thresholds.toml"

SQLITE3_CMD_TEMPLATE = """
.read {{query_file}}
.headers on
.mode csv
.echo on
.output {{hc_summary_file}}
select * from hc_summary;
.output {{hc_by_sample_file}}
select * from hc_by_sample_kw;
.output {{bad_feeder_file}}
select * from bad_feeders order by feeder;
.output {{bad_feeder_pct_thresholds_file}}
select * from bad_feeders_pct_threshold order by feeder;
.output {{bad_feeder_violations_count_file}}
select * from bad_feeders_violation_count_overall;
"""


def _check_task_pattern(_, __, val):
    if val is None:
        return val
    if not re.search(r"^[\w\% ]+$", val):
        logger.error("Task pattern can only contain alphanumeric characters, spaces, and '%'.")
        sys.exit(1)
    return val


@click.command()
@click.option(
    "-d",
    "--database",
    type=click.Path(exists=True),
    required=True,
    help="Path to simulation results database file",
)
@click.option(
    "-s",
    "--scenario",
    type=click.Choice(["pf1", "control_mode", "derms"], case_sensitive=False),
    required=True,
    help="Scenario name",
)
@click.option(
    "-T",
    "--task-names",
    multiple=True,
    help="Query data with these task names in the database.",
)
@click.option(
    "-t",
    "--task-pattern",
    type=str,
    help="Pattern to match one or more tasks in the database with SQL LIKE. Can only contain "
    "letters, numbers, spaces, underscores, and %. Example: '%Time Series%",
    callback=_check_task_pattern,
)
@click.option(
    "--hc-thresholds",
    type=click.Path(),
    default=HOSTING_CAPACITY_THRESHOLDS,
    show_default=True,
    help="File containing thresholds for filtering metrics",
)
@click.option(
    "--thermal/--no-thermal",
    is_flag=True,
    default=True,
    show_default=True,
    help="Check for thermal violations",
)
@click.option(
    "--voltage/--no-voltage",
    is_flag=True,
    default=True,
    show_default=True,
    help="Check for voltage violations",
)
@click.option(
    "--secondaries/--no-secondaries",
    is_flag=True,
    default=False,
    show_default=True,
    help="Include secondary nodes in voltage checks.",
)
@click.option(
    "-o",
    "--output-directory",
    default="hc_reports",
    show_default=True,
    help="Create report files in this directory. Must not already exist.",
    callback=lambda _, __, x: Path(x),
)
@click.option(
    "-f",
    "--force",
    is_flag=True,
    default=False,
    show_default=True,
    help="Overwrite any pre-existing output files.",
)
@click.option(
    "--verbose", is_flag=True, default=False, show_default=True, help="Enable verbose logging"
)
def summarize_hosting_capacity(
    database,
    scenario,
    task_names,
    task_pattern,
    hc_thresholds,
    thermal,
    voltage,
    secondaries,
    output_directory,
    force,
    verbose,
):
    """Create summary files for hosting capacity results."""
    if output_directory.exists():
        if force:
            shutil.rmtree(output_directory)
        else:
            print(f"{output_directory} already exists. Set --force to overwrite.", file=sys.stderr)
            sys.exit(1)
    output_directory.mkdir()

    level = logging.DEBUG if verbose else logging.INFO
    log_file = output_directory / "summarize_hc_metrics.log"
    setup_logging("summarize_hc_metrics", log_file, console_level=level, file_level=level, packages=["disco"])
    logger.info(get_cli_string())

    if task_pattern is None and not task_names:
        logger.error("One of --task-names or --tast-pattern must be passed")
        sys.exit(1)
    if task_pattern is not None and task_names:
        logger.error("Only one of --task-names and --tast-pattern can be passed")
        sys.exit(1)

    hc_summary_filename = output_directory / "hc_summary.csv"
    hc_by_sample_filename = output_directory / "hc_by_sample.csv"
    bad_feeder_filename = output_directory / "feeders_fail_base_case.csv"
    bad_feeder_pct_thresholds_filename = (
        output_directory / "feeders_pct_thresholds_fail_base_case.csv"
    )
    bad_feeder_violations_count_filename = (
        output_directory / "feeders_fail_base_case_threshold_violation_counts.csv"
    )

    defaults = load_data(hc_thresholds)
    options = {"scenario": scenario}
    if task_names:
        options["task_names"] = " OR ".join((f"task.name = '{x}'" for x in task_names))
    if task_pattern is not None:
        options["task_pattern"] = task_pattern
    if thermal:
        options["thermal"] = defaults["thermal"]
    if voltage:
        options["voltage"] = defaults["voltage"]
        options["voltage"]["secondaries"] = secondaries

    with open(TEMPLATE_FILE, "r") as f_in:
        query = chevron.render(f_in, options)

    with NamedTemporaryFile(mode="w") as f_query:
        f_query.write(query)
        f_query.flush()

        out_file = output_directory / "query.sql"
        shutil.copyfile(f_query.name, out_file)

        with NamedTemporaryFile(mode="w") as f_sqlite3_cmd:
            query_options = {
                "query_file": f_query.name,
                "hc_summary_file": hc_summary_filename,
                "hc_by_sample_file": hc_by_sample_filename,
                "bad_feeder_file": bad_feeder_filename,
                "bad_feeder_pct_thresholds_file": bad_feeder_pct_thresholds_filename,
                "bad_feeder_violations_count_file": bad_feeder_violations_count_filename,
            }
            f_sqlite3_cmd.write(chevron.render(SQLITE3_CMD_TEMPLATE, query_options))
            f_sqlite3_cmd.write("\n")
            f_sqlite3_cmd.flush()

            logger.info(
                "Running SQL queries on %s with thresholds\n%s",
                database,
                json.dumps(options, indent=4),
            )
            dump_data(options, output_directory / "thresholds.json", indent=True)
            start = time.time()
            cmd = f"sqlite3 -init {f_sqlite3_cmd.name} {database} .exit"
            check_run_command(cmd)
            logger.info("Queries complete. Duration = %.2f seconds", time.time() - start)

    for filename in output_directory.iterdir():
        logger.info("Created output file %s", filename)
