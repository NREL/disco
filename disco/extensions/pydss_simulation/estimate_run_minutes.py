import os
import json
from pathlib import Path
import pickle
import math

import pandas as pd
import sklearn
import numpy as np

from disco.enums import SimulationHierarchy


# We observed that times were off by a little more than 2x.
FUDGE_FACTOR = 2.5


def generate_estimate_run_minutes(config):
    """Estimated run minutes.

    Parameters
    ----------
    config : PyDssConfiguration

    """
    def get_num_elem(dss_path,elem_name):
        n = 0
        with open(dss_path) as fp:
            for line in fp: 
                if "new "+elem_name.lower() in line.lower():
                    n += 1
        return n

    def compute_estimate(exe_time, scaling_factor):
        val = math.ceil(float(exe_time / 60) * FUDGE_FACTOR) * scaling_factor
        return max(val, 1)
    
    directory = os.path.dirname(__file__)
    model_file = os.path.join(directory, 'trained_lm_time_prediction.sav')
    trained_model = pickle.load(open(model_file, 'rb'))
    hierarchy = config.get_simulation_hierarchy()
    duration = None
    scale_factor = None
    
    for job in config.iter_jobs():
        if duration is None:
            seconds_per_day = 24 * 60 * 60
            duration = (job.model.simulation.end_time - job.model.simulation.start_time).total_seconds() / seconds_per_day
            scale_factor = duration / 365
        if hierarchy == SimulationHierarchy.SUBSTATION:
            deployment_dss = job.model.deployment.deployment_file
            sub_dir = job.model.deployment.directory
            path = Path(sub_dir)
            num_lines = 0
            for lines_dss in path.rglob("Lines.dss"):
                num_lines += get_num_elem(lines_dss,"Line")
            num_loads = 0
            for loads_dss in path.rglob("Loads.dss"):
                num_loads += get_num_elem(loads_dss,"Load")
            num_pvsystem = get_num_elem(deployment_dss,"pvsystem")
            exe_time_pred_s = trained_model.predict(np.array([num_lines, num_loads, num_pvsystem]).reshape(1,-1))
            job.estimated_run_minutes = compute_estimate(exe_time_pred_s, scale_factor)
        elif hierarchy == SimulationHierarchy.FEEDER:
            deployment_dss = job.model.deployment.deployment_file
            feeder_dir = job.model.deployment.directory
            lines_dss = os.path.join(feeder_dir, "OpenDSS","Lines.dss")
            loads_dss = os.path.join(feeder_dir, "OpenDSS","Loads.dss")
            num_lines = get_num_elem(lines_dss,"Line")
            num_loads = get_num_elem(loads_dss,"load")
            num_pvsystem = get_num_elem(deployment_dss,"pvsystem")
            exe_time_pred_s = trained_model.predict(np.array([num_lines, num_loads, num_pvsystem]).reshape(1,-1))
            job.estimated_run_minutes = compute_estimate(exe_time_pred_s, scale_factor)
        else:
            assert False, hierarchy


if __name__ == "__main__":
    generate_estimate_run_minutes()
