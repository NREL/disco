import os
import pathlib

import click

from jade.utils.run_command import check_run_command
from disco.pipelines.utils import ensure_jade_pipeline_output_dir


@click.command()
@click.argument("commands-file")
def auto_config(commands_file):
    path = pathlib.Path(commands_file)
    commands = path.read_text().split("\n")
    for cmd in commands:
        cmd = cmd.strip()
        if not cmd:
            continue
        cmd = ensure_jade_pipeline_output_dir(cmd)
        check_run_command(cmd)


if __name__ == "__main__":
    auto_config()
