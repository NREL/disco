#!/usr/bin/env python

import os
import re
import shutil
import sys
from pathlib import Path

import click


BASE_DIR = "/datasets/SMART-DS"
# Examples:
#   P32U
#   P4R
REGEX_REGION_NAME = re.compile(r"^P\d+[RU]$")


@click.argument("output-dir")
@click.option(
    "-v", "--version",
    type=str,
    required=True,
    help="dataset version",
)
@click.option(
    "-y", "--year",
    type=str,
    required=True,
    help="dataset year",
)
@click.option(
    "-c", "--city",
    type=str,
    required=True,
    help="dataset city",
)
@click.option(
    "-f", "--force",
    is_flag=True,
    default=False,
    help="overwrite output-dir if it exists",
)
@click.command()
def copy_dataset(output_dir, version, year, city, force):
    """Copy a SMART-DS from the Eagle source directory to a destination directory."""
    output_dir = Path(output_dir)
    base_path = Path(BASE_DIR) / version / year / city
    if not base_path.exists():
        print(f"{base_path} does not exist")
        sys.exit(1)

    dst_path = output_dir / version / year / city
    if dst_path.exists():
        if force:
            shutil.rmtree(dst_path)
        else:
            print(f"{dst_path} already exists. Delete it or set --force.")
            sys.exit(1)
    os.makedirs(dst_path)

    for name in os.listdir(base_path):
        if REGEX_REGION_NAME.search(name) is not None:
            src_region_path = base_path / name / "scenarios" / "base_timeseries" / "opendss"
            dst_region_path = dst_path / name / "scenarios" / "base_timeseries" / "opendss"

            shutil.copytree(src_region_path, dst_region_path)
            print(f"Copied {src_region_path} to {dst_region_path}")



if __name__ == "__main__":
    copy_dataset()
