# -*- coding: utf-8 -*-
"""
Created on Fri Nov 25 07:43:46 2022

@author: ksedzro
"""

import os
import numpy as np
import pandas as pd
import time



def get_parameter(line, parameter_name, func=None):
    if func!=None:
        val = func(line.split(f'{parameter_name}=')[1].split(' ')[0])
        
    else:
        val = line.split(f'{parameter_name}=')[1].split(' ')[0]
        if '\n' in val:
            val = val.strip('\n')
    
    return val
    

def collect_category(file_path, bus_data, category='demand'):
    """
    file_path can be:
        loads.dss path 
        EVloads.dss path 
        PVsystems.dss path
    category must be 'demand' or 'generation'
        if file_path points to loads or EV loads, category must be 'demand'
        if file_path points to PV systems or DERs, category must be 'generation'
    """
    assert category in ['demand', 'generation']
    with open(file_path, 'r') as lr:
        lines = lr.readlines()
        
    for line in lines:
        if line.lower().startswith('new'):
            line = line.lower()
            size = 0
            profile_name = ''
            bus = get_parameter(line, 'bus1')
            #bus = line.split('bus1=')[1].split(' ')[0]
            if '.' in bus:
                bus = bus.split('.')[0]
            if not bus in bus_data.keys():
                bus_data[bus] = {'bus':bus, 'demand':[], 'generation':[]}
            
            if 'kw=' in line:
                size = get_parameter(line, 'kw', float)
                # load_size = float(line.split('kw=')[1].split(' ')[0])
            elif 'kva=' in line:
                size = get_parameter(line, 'kva', float)
                # load_size = float(line.split('kva=')[1].split(' ')[0])
            elif 'pmpp=' in line:
                size = get_parameter(line, 'pmpp', float)
            if 'yearly' in line:
                profile_name =  get_parameter(line, 'yearly')
            elif 'daily' in line:
                profile_name =  get_parameter(line, 'daily')
             
            bus_data[bus][category].append([size, profile_name])   
    
    return bus_data

def collect_profiles(profile_files):
    """
    This function builds a dictionary called profile_data.
    The profile_data collects for each timeseries profile:
        the name
        the path to the actual CV profile data file
        the numpy array of the profile timeseries data
    It also builds and stores a new destination path where new reduced profile timeseries will be written
    INPUT:
        profile_files: a list of paths pointing to .dss profile files such as LoadShapes.dss, PVshapes.dss, etc.
    OUTPUT:
        proile_data: a dictionary (see description above)
    """
    profile_data = {}
    for file_path in profile_files:
        base_path, _ = os.path.split(file_path)
        with open(file_path, 'r') as lr:
            lines = lr.readlines()
        for line in lines:
            if line.lower().startswith('new'):
                line = line.lower()
                profile_name = line.split('loadshape.')[1].split(' ')[0]
                rel_path = line.split('file=')[1].split(')')[0]
                profile_path = os.path.join(base_path, rel_path)
                with open(profile_path) as pr:
                    profile_array = np.loadtxt(pr, delimiter=",")
                folder, filename = os.path.split(profile_path)
                copy_dir = folder+'-new'
                if not os.path.exists(copy_dir):
                    os.mkdir(copy_dir)
                new_profile_path = os.path.join(copy_dir, filename)
                profile_data[profile_name] = {'profile_name': profile_name,
                                              'profile_path': profile_path,
                                              'new_profile_path': new_profile_path,
                                              'time_series': profile_array
                                              }
                
    return profile_data
            
def agregate_series(bus_data, profile_data, critical_conditions):
    ag_series = {}
    critical_time_indices = []
    head_critical_time_indices = []
    for bus, dic in bus_data.items():
        ag_series[bus] = {'critical_time_idx':[],}
        
        if dic['demand']:
            for data in dic['demand']:
                
                if 'demand' in ag_series[bus].keys():
                    ag_series[bus]['demand'] += data[0]*profile_data[data[1]]['time_series']
                else:
                    ag_series[bus]['demand'] = data[0]*profile_data[data[1]]['time_series']
            if 'max_demand' in  critical_conditions:       
                max_demand_idx = np.where(ag_series[bus]['demand'] == np.amax(ag_series[bus]['demand']))[0].tolist()[0]
                ag_series[bus]['critical_time_idx'].append(max_demand_idx)
            if 'min_demand' in  critical_conditions: 
                min_demand_idx = np.where(ag_series[bus]['demand'] == np.amin(ag_series[bus]['demand']))[0].tolist()[0]
                ag_series[bus]['critical_time_idx'].append(min_demand_idx)
                # ag_series[bus]['critical_time_idx'] += [max_demand_idx, min_demand_idx]
           
        if dic['generation']:
            for data in dic['generation']:
                if 'generation' in ag_series[bus].keys():
                    ag_series[bus]['generation'] += data[0]*profile_data[data[1]]['time_series']
                else:
                    ag_series[bus]['generation'] = data[0]*profile_data[data[1]]['time_series']
            if 'max_generation' in  critical_conditions: 
                max_gen_idx = np.where(ag_series[bus]['generation'] == np.amax(ag_series[bus]['generation']))[0].tolist()[0]
                ag_series[bus]['critical_time_idx'].append(max_gen_idx) 
            if 'demand' in ag_series[bus].keys() and 'max_net_generation' in  critical_conditions:
                arr = ag_series[bus]['generation'] - ag_series[bus]['demand']
                max_netgen_idx = np.where(arr == np.amax(arr))[0].tolist()[0]
                ag_series[bus]['critical_time_idx'].append(max_netgen_idx)
                
    total_gen = sum([dic['generation'] for bus, dic in ag_series.items() 
                     if 'generation' in dic.keys()])
    total_dem = sum([dic['demand'] for bus, dic in ag_series.items() 
                     if 'demand' in dic.keys()])
    net_total_gen = total_gen - total_dem
    if 'max_demand' in  critical_conditions: 
        max_demand_idx = np.where(total_dem == np.amax(total_dem))[0].tolist()[0]
        head_critical_time_indices.append(max_demand_idx)
    if 'min_demand' in  critical_conditions:    
        min_demand_idx = np.where(total_dem == np.amin(total_dem))[0].tolist()[0]
        head_critical_time_indices.append(min_demand_idx)
    if 'max_generation' in  critical_conditions:
        max_gen_idx = np.where(total_gen == np.amax(total_gen))[0].tolist()[0]
        head_critical_time_indices.append(max_gen_idx)
    if 'max_net_generation' in  critical_conditions:
        max_netgen_idx = np.where(net_total_gen == np.amax(net_total_gen))[0].tolist()[0]
        head_critical_time_indices.append(max_netgen_idx)
    
    critical_time_indices = [t  for bus, dic in ag_series.items() 
                             for t in dic['critical_time_idx'] 
                             if 'critical_time_idx' in dic.keys()]
    critical_time_indices += head_critical_time_indices
    critical_time_indices = list(set(critical_time_indices))
    critical_time_indices.sort()
    for profile, val in profile_data.items():
        base_len = len(val['time_series'])
        compression_rate = len(critical_time_indices)/base_len
        data = val['time_series'][critical_time_indices]
        pd.DataFrame(data).to_csv(val['new_profile_path'], 
                                  index=False, header=False)
        
    return ag_series, head_critical_time_indices, critical_time_indices, compression_rate
    

def main(category_path_dict, 
         profile_files, 
         critical_conditions=['max_demand', 'min_demand', 'max_generation', 'max_net_generation']):
    """
    INPUT:
        category_path_dict: a dictionary where: 
            the keys are power conversion asset categories: "demand" and "generation"
            the values are a list of paths pointing to the corresponding power conversions assets' .dss files such as "Loads.dss" and "PVSystems.dss" files
            example: category_path_dict = {'demand': [LOAD_PATH, EVLOAD_PATH], 'generation': [PV_PATH]}
        profile_files: a list of paths pointing to shape (profile) files such as "LoadShapes.dss"
    OUTPUT:
        bus_data: 
        profile_data:
        ag_series:
        head_time_indices: list of critical time indices when only feeder-head timeseries are considered 
        critical_time_indices: all critical time indices (individual buses as well as feeder-head considered)
        compression_rate: ratio between the number of critical timepoints and the total number of timepoints in the timeseries
                             
    """
    
    bus_data={}
    for category, file_paths in category_path_dict.items():
        for file_path in file_paths:
            bus_data = collect_category(file_path, bus_data, category=category)
    profile_data = collect_profiles(profile_files)
    ag_series, head_time_indices, critical_time_indices, compression_rate = \
        agregate_series(bus_data, profile_data, critical_conditions)
    return bus_data, profile_data, ag_series, head_time_indices, critical_time_indices, compression_rate
    

if __name__ == "__main__":   
    st = time.time()
    PV_PATH = r"C:\Users\KSEDZRO\Documents\Projects\LA-equity-resilience\data\P12U\sb9_p12uhs3_1247_trans_264--p12udt8475\190\PVSystems.dss"
    LOAD_PATH = r"C:\Users\KSEDZRO\Documents\Projects\LA-equity-resilience\data\P12U\sb9_p12uhs3_1247_trans_264--p12udt8475\Loads.dss"
    LOADSHAPES_PATH = r"C:\Users\KSEDZRO\Documents\Projects\LA-equity-resilience\data\P12U\sb9_p12uhs3_1247_trans_264--p12udt8475\LoadShapes.dss"
    PVSHAPES_PATH = r"C:\Users\KSEDZRO\Documents\Projects\LA-equity-resilience\data\P12U\sb9_p12uhs3_1247_trans_264--p12udt8475\PVShapes.dss"
    category_path_dict = {'demand': [LOAD_PATH], 'generation': [PV_PATH]}
    profile_files = [LOADSHAPES_PATH, PVSHAPES_PATH]
    critical_conditions = ['max_demand', 'max_net_generation']
    
    bus_data, profile_data, ag_series, head_time_indices, critical_time_indices, compression_rate = \
        main(category_path_dict, profile_files, critical_conditions)
    et = time.time()
    elapse_time = et-st
