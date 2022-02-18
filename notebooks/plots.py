#!/usr/bin/env python


"""
    Results analysis

"""

import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
import os

import click


# @click.command()
# @click.option('--db', help='db file to read')


# read 

conn = sqlite3.connect("/projects/distcosts3/WenboWang_start/ss2/disco-ss2-hc.sqlite")
df1 = pd.read_sql_query("SELECT name FROM sqlite_master WHERE type = 'table'", conn)

df2 = pd.read_sql_query("PRAGMA table_info(hosting_capacity)", conn)

df_hc = pd.read_sql_query("SELECT * from hosting_capacity Where time_point=='max_pv_load_ratio' and scenario=='pf1' and hc_type=='overall'", conn)


# choose number of feeders 30
df_hc_test = df_hc.iloc[0:30]
fig, ax = plt.subplots(figsize=(8,8))
y_pos = df_hc_test['feeder']
ax.barh(y_pos,df_hc_test['min_hc_pct'],label="no violation",color='limegreen')
ax.barh(y_pos,df_hc_test['max_hc_pct']-df_hc_test['min_hc_pct'],left=df_hc_test['min_hc_pct'],label="some violation",color='gold')
ax.barh(y_pos,200-df_hc_test['max_hc_pct'],left=df_hc_test['max_hc_pct'],label="violation",color='tomato')
ax.set_title("HCA heatmap: pf1")
ax.set_xlabel("Penetration level (%)")
ax.legend(ncol=3)
plt.savefig("hca.png")

# color match: https://www.xcelenergy.com/hosting_capacity_map 


# select a feeder name

feeder_example = df_hc_test['feeder'][1]

df3 = pd.read_sql_query(f"SELECT * from voltage_metrics Where feeder=='{feeder_example}'", conn)

fig, ax = plt.subplots(figsize=(8,8))
ax.scatter(df3[df3['node_type']=='primaries']['penetration_level'],df3[df3['node_type']=='primaries']["max_voltage"],facecolors='none',edgecolors='C0',label="primary")
ax.scatter(df3[df3['node_type']=='secondaries']['penetration_level'],df3[df3['node_type']=='secondaries']["max_voltage"],facecolors='none',edgecolors='C1',label="secondary")
ax.legend()
ax.set_title(feeder_example)
ax.set_xlabel("Penetration level")
ax.set_ylabel("max_voltage (pu)")
fig.savefig("max_voltage_pri_sec.png")


fig, ax = plt.subplots(figsize=(8,8))

ax.scatter(df3[df3['scenario']=='pf1']['penetration_level'],df3[df3['scenario']=='pf1']["max_voltage"],facecolors='none',edgecolors='C0',label="base_case:pf1")
ax.scatter(df3[df3['scenario']=='control_mode']['penetration_level'],df3[df3['scenario']=='control_mode']["max_voltage"],facecolors='none',edgecolors='C1',label="control_mode:volt-var")
ax.legend()
ax.set_title(feeder_example)
ax.set_xlabel("Penetration level")
ax.set_ylabel("max_voltage (pu)")
fig.savefig("max_voltage_base_voltvar.png")

df4 = pd.read_sql_query(f"SELECT * from thermal_metrics Where feeder=='{feeder_example}'", conn)

fig, ax = plt.subplots(figsize=(8,8))

ax.scatter(df4[df4['scenario']=='pf1']['penetration_level'],df4[df4['scenario']=='pf1']["transformer_max_instantaneous_loading_pct"],facecolors='none',edgecolors='C0',label="base_case:pf1",marker='^')
ax.scatter(df4[df4['scenario']=='control_mode']['penetration_level'],df4[df4['scenario']=='control_mode']["transformer_max_instantaneous_loading_pct"],facecolors='none',edgecolors='C1',label="control_mode:volt-var",marker='v')
ax.legend()
ax.set_title(feeder_example)
ax.set_xlabel("Penetration level")
ax.set_ylabel("transformer_max_instantaneous_loading_pct")
fig.savefig("transformer_max_instantaneous_loading_pct.png")


fig, ax = plt.subplots(figsize=(8,8))

ax.scatter(df4[df4['scenario']=='pf1']['penetration_level'],df4[df4['scenario']=='pf1']["transformer_num_time_points_with_instantaneous_violations"],facecolors='none',edgecolors='C0',label="base_case:pf1",marker='^')
ax.scatter(df4[df4['scenario']=='control_mode']['penetration_level'],df4[df4['scenario']=='control_mode']["transformer_num_time_points_with_instantaneous_violations"],facecolors='none',edgecolors='C1',label="control_mode:volt-var",marker='v')
ax.legend()
ax.set_title(feeder_example)
ax.set_xlabel("Penetration level")
ax.set_ylabel("transformer_num_time_points_with_instantaneous_violations")
fig.savefig("transformer_num_time_points_with_instantaneous_violations.png")


print('End')