#!/usr/bin/env python

"""Creates JADE configuration for stage 2 of pydss_simulation pipeline."""

import os
import sys

from jade.utils.subprocess_manager import run_command
from jade.utils.utils import load_data


def main():
    pydss_folder = os.path.dirname(os.path.realpath(__file__))
    status = load_data(os.environ["JADE_PIPELINE_STATUS_FILE"])
    cur_stage = status["stages"][-1]
    cur_stage_output = cur_stage["output_directory"]
    previous_stage = status["stages"][-2]
    previous_stage_output = previous_stage["output_directory"]
    script = os.path.join(pydss_folder, "merge_feeders_results.py")

    commands_file = "merge_feeders_commands.txt"
    with open(commands_file, "w") as f_out:
        cmd = f"python {script} run {previous_stage_output} {cur_stage_output}"
        f_out.write(cmd + "\n")

    cmd = f"jade config create {commands_file} -c config-stage2.json"
    try:
        ret = run_command(cmd)
    finally:
        os.remove(commands_file)
    sys.exit(ret)


if __name__ == "__main__":
    main()
