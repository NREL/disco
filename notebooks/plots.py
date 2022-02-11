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


