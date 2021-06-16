import os
import json
from pathlib import Path
import pickle
import math

import pandas as pd
import sklearn
import numpy as np

from disco.enums import SimulationHierarchy

def generate_estimate_run_minutes(config):
    """ Estimated run minutes.

    """
    def get_num_elem(dss_path,elem_name):
        n = 0
        with open(dss_path) as fp:
            for line in fp: 
                if "new "+elem_name.lower() in line.lower():
                    n += 1
        return n
    
    directory = os.path.dirname(__file__)
    model_file = os.path.join(directory, 'trained_lm_time_prediction.sav')
    trained_model = pickle.load(open(model_file, 'rb'))
    hierarchy = config.get_simulation_hierarchy()
    
    if hierarchy == SimulationHierarchy.SUBSTATION:
        for job in config.iter_jobs():
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
            job.estimated_run_minutes = math.ceil(float(exe_time_pred_s/60)*2.5)          
    else:
        for job in config.iter_jobs():
            deployment_dss = job.model.deployment.deployment_file
            feeder_dir = job.model.deployment.directory
            lines_dss = os.path.join(feeder_dir, "OpenDSS","Lines.dss")
            loads_dss = os.path.join(feeder_dir, "OpenDSS","Loads.dss")
            num_lines = get_num_elem(lines_dss,"Line")
            num_loads = get_num_elem(loads_dss,"load")
            num_pvsystem = get_num_elem(deployment_dss,"pvsystem")
            exe_time_pred_s = trained_model.predict(np.array([num_lines, num_loads, num_pvsystem]).reshape(1,-1)) 
            job.estimated_run_minutes = math.ceil(float(exe_time_pred_s/60)*2.5)        
        
if __name__ == "__main__":
    generate_estimate_run_minutes()