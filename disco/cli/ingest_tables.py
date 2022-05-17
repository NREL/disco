import logging
import os

import click

from jade.loggers import setup_logging
from disco.pipelines.utils import ensure_jade_pipeline_output_dir
from disco.storage.db import create_database
from disco.storage.core import StoragePipeline


@click.command()
@click.argument("output")
@click.option(
    "-t", "--task-name",
    type=click.STRING,
    required=True,
    help="Name of the DISCO simulation/analysis task"
)
@click.option(
    "-m", "--model-inputs",
    type=click.Path(),
    required=True,
    help="Model inputs of the DISCO simulation/analysis task"
)
@click.option(
    "-n", "--notes",
    type=click.STRING,
    default=None,
    help="Notes about this DISCO simulation/analysis task"
)
@click.option(
    "-d", "--database",
    type=click.Path(),
    default="disco.sqlite",
    help="The path of new or existing SQLite database"
)
@click.option(
    "-v", "--verbose",
    is_flag=True,
    default=False,
    help="Enable debug logging"
)
def ingest_tables(
    output,
    task_name,
    model_inputs, 
    notes,
    database,
    verbose
):
    """Ingest DISCO simulation/analysis reports into SQLite database"""
    level = logging.DEBUG if verbose else logging.INFO
    logger = setup_logging(__name__, None, console_level=level, packages=["disco"])

    output = ensure_jade_pipeline_output_dir(output)
    database = ensure_jade_pipeline_output_dir(database)
    
    db_created = False
    if not os.path.exists(database):
        create_database(database)
        db_created = True
    
    try:
        data = {
            "output": os.path.abspath(output),
            "task_name": task_name,
            "model_inputs": os.path.abspath(model_inputs),
            "notes": notes or "",
            "database": database
        }
        pipeline = StoragePipeline(database=database)
        pipeline.run(data=data)
    except Exception as e:
        if db_created:
            os.remove(database)
        else:
            # TODO: rollback if any error
            pass
        raise e
