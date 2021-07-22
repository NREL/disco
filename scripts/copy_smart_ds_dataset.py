#!/usr/bin/env python

import os
import re
import shutil
import sys
from pathlib import Path
import struct
import pandas as pd
import csv

import click

from disco.sources.base import FORMAT_FILENAME


BASE_DIR = "/datasets/SMART-DS"
# Examples:
#   P32U
#   P4R
REGEX_REGION_NAME = re.compile(r"^P\d+[RU]$")
FORMAT_FILE_CONTENTS = 'type = "SourceTree1Model"\n'


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
            src_profiles = base_path / name / "profiles"
            dst_profiles = dst_path / name / "profiles"
            shutil.copytree(src_profiles, dst_profiles)
            src_region_path = base_path / name / "scenarios" / "base_timeseries" / "opendss"
            dst_region_path = dst_path / name / "scenarios" / "base_timeseries" / "opendss"
            shutil.copytree(src_region_path, dst_region_path)
            _write_format_file(dst_region_path / FORMAT_FILENAME)
            print(f"Copied {src_region_path} to {dst_region_path}")


def _write_format_file(filename):
    with open(filename, "w") as f_out:
        f_out.write(FORMAT_FILE_CONTENTS)


def convert_to_sng_file(csvfolder):
    """Convert csv files to sng files.

    Parameters
    ----------
    csv files location folder

    """

    path = Path(csvfolder)
    for csvpath in path.rglob("*.csv"):
        header_flag = None
        with open(csvpath) as f:
            reader = csv.reader(f)
            row1 = next(reader)[0]
        if re.match(r'[a-zA-Z]', row1):
            header_flag = 0
        loadshape = pd.read_csv(csvpath, header=header_flag)
        loadshape_list = loadshape.iloc[:, 0].to_list()
        fname = os.path.basename(csvpath).split('.csv')[0] + '.sng'
        with open(path / fname, 'wb') as fout:
            fout.write(struct.pack('%sf' % len(loadshape_list), *loadshape_list))


if __name__ == "__main__":
    copy_dataset()
