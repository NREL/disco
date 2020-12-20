import logging

import click

from jade.exceptions import InvalidParameter
from jade.utils.utils import load_data
from disco.models.factory import list_model_classes

logger = logging.getLogger(__name__)


@click.group()
def simulation_models():
    """Commands to operate on simulation models"""


def get_model_class(ctx, param, value):
    for cls in list_model_classes():
        if cls.__name__ == value:
            return cls
    raise InvalidParameter(f"invalid model: {value}")


@click.command(name="list")
def list_models():
    """List all simulation models."""
    print("{}".format(" ".join([x.__name__ for x in list_model_classes()])))


@click.command()
@click.argument("model", callback=get_model_class)
def show_example(model):
    """Show an example job definition for a simulation model."""
    print(model.example_json())


@click.command()
@click.argument("model", callback=get_model_class)
def show_schema(model):
    """Show the schema for a simulation model."""
    print(model.schema_json())


@click.command()
@click.argument("filename", type=click.Path(exists=True))
@click.argument("model", callback=get_model_class)
def validate_file(filename, model):
    """Validate the JSON inputs config file."""
    data = load_data(filename)
    if isinstance(data, dict):
        model.validate(data)
    else:
        for item in data:
            model.validate(item)
    print("Success!")


simulation_models.add_command(list_models)
simulation_models.add_command(show_example)
simulation_models.add_command(show_schema)
simulation_models.add_command(validate_file)
