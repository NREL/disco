"""CLI commands for transforming source data"""

import logging
import os
import sys

import click

from jade.loggers import setup_logging
from jade.utils.utils import get_cli_string
from disco.sources.factory import list_subcommands, make_source_model


logger = logging.getLogger(__name__)


class TransformCli(click.MultiCommand):
    """Custom CLI to dynamically detect subcommands from an input argument."""

    def __init__(self, *args, **kwargs):
        super(TransformCli, self).__init__(*args, **kwargs)
        self.input_path = None
        self.source_type = None

    def list_commands(self, ctx):
        self.check_input_path()
        return self.source_type.list_transform_subcommands()

    def get_command(self, ctx, name):
        self.check_input_path()
        if name in ("-h", "--help"):
            self.show_subcommand_help_and_exit()

        if name not in self.list_commands(ctx):
            raise click.BadArgumentUsage(f"{name} is not a valid command")
        return self.source_type.get_transform_subcommand(name)

    def check_input_path(self):
        if self.source_type is None:
            show_help_and_exit()

    def show_subcommand_help_and_exit(self):
        commands = self.source_type.list_transform_subcommands()
        input_path = self.input_path
        print("\nAvailable analysis types: {}\n".format(" ".join(commands)))
        print("For additional help run one of the following:")
        for cmd in commands:
            print(f"    disco transform-model {input_path} {cmd} --help")
        sys.exit(0)


def input_path_cb(ctx, param, value):
    ctx.command.input_path = value
    ctx.command.source_type = make_source_model(value)
    return value


def show_help_and_exit():
    print(
        "Transforms source data specified by INPUT_PATH into DISCO models.\n"
        "Subcommands are dependent on the source data type.\n"
    )
    print("Usage: disco transform-model [OPTIONS] INPUT_PATH COMMAND [ARGS]...")
    print("\ninput_path must be specified to determine available commands\n")
    print("Examples:\n")
    print("disco transform-model ~/source-data --help")
    print("disco transform-model ~/source-data snapshot --help")
    print(
        "disco transform-model ~/source-data snapshot --output snapshot-models"
    )
    sys.exit(0)


@click.command(cls=TransformCli)
@click.argument("input_path", callback=input_path_cb)
def transform_model(input_path):
    """Transform input data into a DISCO model"""
    setup_logging("disco", "transform_model.log", mode="a", packages=["disco"])
    logger.info(get_cli_string())
