# -*- coding: utf-8 -*-
"""
Created on Fri Feb  5 07:46:25 2021

@author: senam
"""
import os
import json
import pandas as pd
import numpy as np

from jade.common import CONFIG_FILE
from PyDSS.pydss_project import PyDssProject
from disco.extensions.pydss_simulation.pydss_configuration import PyDssConfiguration
from disco.distribution.deployment_parameters import DeploymentParameters


def combine_metrics(project_path):
    summary_dict = dict()

    #if os.path.exists(project_path):
    pydss_project = PyDssProject.load_project(project_path)

    voltage_metrics = json.loads(
        pydss_project.fs_interface.read_file(
            os.path.join("Reports", "voltage_metrics.json")
        )
    )

    thermal_metrics = json.loads(
        pydss_project.fs_interface.read_file(
            os.path.join("Reports", "thermal_metrics.json")
        )
    )
    print()
    print(thermal_metrics)
    print()
    summary_dict.update(voltage_metrics['summary'])
    summary_dict.update(thermal_metrics['summary'])
    return summary_dict

def get_absolute_changes(df, property_name, base_case='base_case'):
    to_exclude = [
        'total_num_time_points',
        'total_simulation_duration',
        'num_nodes_always_inside_ansi_a'
    ]
    if property_name not in to_exclude:
        df[f"absolute_change_in_{property_name}"] = (
            df.property_name - df.loc[base_case, property_name]
        )
    return df

def aggregate_deployments(job_outputs_path):
    config_file = os.path.join(os.path.dirname(job_outputs_path), CONFIG_FILE)
    config = PyDssConfiguration.deserialize(config_file)

    summary_dfs = []
    for feeder in config.list_feeders():
        all_summaries_dict = dict()
        base_case = config.get_base_case_job(feeder)
        print(base_case)
        for job in config.iter_feeder_jobs(feeder):
            project_path = os.path.join(
                job_outputs_path, job.name, "pydss_project",
            )
            all_summaries_dict[job.name] = combine_metrics(project_path)

        print(all_summaries_dict)
        summary_df = pd.DataFrame.from_dict(all_summaries_dict, 'index')
        if not summary_df.empty:
            for property_name in summary_df.columns:
                summary_df = get_absolute_changes(summary_df, property_name, base_case.name)
            summary_df = assess_deployments(summary_df)
            summary_dfs.append(summary_df)

    return summary_dfs

def assess_deployments(df):
    key = 'absolute_change_in'
    change_cols = [(c, c.split(key)[1]) for c in df.columns if key in c]
    for cols in change_cols:
        change_col = cols[0]
        flag_col = f"pass_{cols[1]}"
        df.loc[:, flag_col] = df[change_col]<=0
    pass_flags = [c for c in df.columns if c.startswith('pass')]
    df['pass_flag'] = df[pass_flags[0]]
    for col in pass_flags[1:]:
        df['pass_flag'] = np.logical_and(df['pass_flag'], df[col])

    return df
