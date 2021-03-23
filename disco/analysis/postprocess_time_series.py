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
from disco.extensions.pydss_simulation.pydss_configuration import PyDssConfiguration
from disco.distribution.deployment_parameters import DeploymentParameters
from PyDSS.pydss_project import PyDssProject
from PyDSS.pydss_results import PyDssResults
from PyDSS.node_voltage_metrics import SimulationVoltageMetricsModel, VoltageMetricsModel


def combine_metrics(project_path):
    summary_dict = dict()

    #if os.path.exists(project_path):
    pydss_project = PyDssProject.load_project(project_path)

    voltage_metrics = SimulationVoltageMetricsModel(
        **json.loads(
            pydss_project.fs_interface.read_file(
                os.path.join("Reports", "voltage_metrics.json")
            )
        )
    )
    assert "control_mode" in voltage_metrics.scenarios

    thermal_metrics = json.loads(
        pydss_project.fs_interface.read_file(
            os.path.join("Reports", "thermal_metrics.json")
        )
    )
    
    voltage_summary = voltage_metrics.scenarios["control_mode"].summary
    summary_dict.update(voltage_summary.dict())
    summary_dict.update(thermal_metrics['summary'])
    return summary_dict

def get_absolute_changes(df, property_name, base_case='base_case'):
    to_exclude = [
        'total_num_time_points',
        'total_simulation_duration',
        'num_nodes_always_inside_ansi_a',
        'PV_capacity_kW',
        'load_capacity_kW',
        'pct_pv_to_load_ratio',
        'feeder'
    ]
    if property_name not in to_exclude:
        df[f"absolute_change_in_{property_name}"] = (
            df.loc[:, property_name] - df.loc[base_case, property_name]
        )
    return df

def aggregate_deployments(job_outputs_path, tolerance=0.05):
    config_file = os.path.join(os.path.dirname(job_outputs_path), CONFIG_FILE)
    config = PyDssConfiguration.deserialize(config_file)

    summary_dfs = []
    for feeder in config.list_feeders():
        all_summaries_dict = dict()
        base_case = config.get_base_case_job(feeder)
        
        for job in config.iter_feeder_jobs(feeder):
            project_path = os.path.join(
                job_outputs_path, job.name, "pydss_project",
            )
            total_pv = get_total_pv_kilowatts(project_path)
            total_load = get_total_load_kilowatts(project_path)
            penetration = 100 * total_pv / max(total_load, 1e-3)
            all_summaries_dict[job.name] = {
                'feeder': feeder,
                'PV_capacity_kW': total_pv,
                'load_capacity_kW': total_load,
                'pct_pv_to_load_ratio': penetration
            }
            
            all_summaries_dict[job.name].update(combine_metrics(project_path))
            

        summary_df = pd.DataFrame.from_dict(all_summaries_dict, 'index')
        if not summary_df.empty:
            for property_name in summary_df.columns:
                summary_df = get_absolute_changes(summary_df, property_name, base_case.name)
            summary_df = assess_deployments(summary_df, tolerance)
            summary_df.to_csv(os.path.join(job_outputs_path, f'impact_summary_{feeder}.csv'))
            summary_dfs.append(summary_df)

    return summary_dfs

def assess_deployments(df, tolerance):
    key = 'absolute_change_in_'
    change_cols = [(c, c.split(key)[1]) for c in df.columns if key in c]
    for cols in change_cols:
        change_col = cols[0]
        flag_col = f"pass_{cols[1]}"
        df.loc[:, flag_col] = df[change_col] <= tolerance * df[cols[1]]
    pass_flags = [c for c in df.columns if c.startswith('pass')]
    df['pass_flag'] = df[pass_flags[0]] # initialization
    for col in pass_flags[1:]:
        df['pass_flag'] = np.logical_and(df['pass_flag'], df[col])

    return df

#------------------------------------------


def get_total_pv_kilowatts(job_path):
    results = PyDssResults(job_path)
    scenario = results.scenarios[0]
    df = scenario.read_element_info_file(f'Exports/{scenario.name}/PVSystemsInfo.csv')
    if not df.Name.isnull().all():
        return df['Pmpp'].sum()
    else:
        return 0

def get_total_load_kilowatts(job_path):
    results = PyDssResults(job_path)
    scenario = results.scenarios[0]
    df = scenario.read_element_info_file(f'Exports/{scenario.name}/LoadsInfo.csv')
    
    return df['kW'].sum()
    
    
def compute_hosting_capacity(dfs, job_outputs_path):
    hc_dict = {}
    for df in dfs:
        feeder = df['feeder'].values[0]
        
        hc_dict[feeder] = {
            'max_hc_pct': None, 
            'max_hc_kW': None,
            'min_hc_pct': None, 
            'min_hc_kW': None
        }
        
        hc_set = []
        size_set = []
        if df.pass_flag.any():
            pass_df = df.loc[df.pass_flag==True, :]
            
            hc_dict[feeder]['max_hc_pct'] = pass_df.pct_pv_to_load_ratio.max()
            hc_dict[feeder]['max_hc_kW'] = pass_df.PV_capacity_kW.max()
            
            passing_pentrations = list(pass_df.pct_pv_to_load_ratio)
            for pct in passing_pentrations:
                if df.loc[df.pct_pv_to_load_ratio <= pct, 'pass_flag'].all():
                    hc_set.append(pct)
                    size_set.append(df.loc[df.pct_pv_to_load_ratio == pct, 'PV_capacity_kW'][0])
            if hc_set:
                hc_dict[feeder]['min_hc_pct'] = max(hc_set)
                hc_dict[feeder]['min_hc_kW'] = max(size_set)   
    hc_df = pd.DataFrame.from_dict(hc_dict, 'index')
    hc_df.to_csv(os.path.join(job_outputs_path, 'hosting_capacity.csv'))
