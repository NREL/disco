#!/usr/bin/env python

"""Creates JADE configuration for stage 1 of pydss_simulation pipeline."""

import logging
import sys

from jade.utils.subprocess_manager import run_command

logger = logging.getLogger(__name__)

def main():
    model_inputs = './model-inputs'
    job_post_process_file = 'snapshot-post-process-config.toml'

    # Create job post process config
    job_post_process_cmd = f"disco generate-analysis -t SnapshotImpactAnalysis \
                            --output-file {job_post_process_file}"

    # add overrides from args
    for arg in sys.argv[1:]:
        job_post_process_cmd += f" -o {arg}"

    ret = run_command(job_post_process_cmd)

    if ret != 0:
        logger.error("Error running job post-process config creation.")
        sys.exit(ret)

    # Generate pydss simulation config
    pydss_auto_config_cmd = f"jade auto-config pydss_simulation {model_inputs} \
                            -p {job_post_process_file} \
                            -c config-stage1.json"

    ret = run_command(pydss_auto_config_cmd)

    if ret != 0:
        logger.error("Error running pydss_simulation auto-config.")

    sys.exit(ret)

if __name__ == "__main__":
    main()