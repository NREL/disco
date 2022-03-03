# -*- coding: utf-8 -*-
"""
Created on Thu May 27 01:28:38 2021

@author: senam
"""

import os
import pandas as pd


METRIC_MAP = {
    "thermal": {
        "submetrics": [
            "line_max_instantaneous_loading",
            "line_max_moving_average_loading",
            "line_num_time_points_with_instantaneous_violations",
            "line_num_time_points_with_moving_average_violations",
            "transformer_max_instantaneous_loading",
            "transformer_max_moving_average_loading",
            "transformer_num_time_points_with_instantaneous_violations",
            "transformer_num_time_points_with_moving_average_violations",
        ]
    },
    "voltage": {
        "node_type": ["primaries", "secondaries"],
        "submetrics": [
            "min_voltage",
            "max_voltage",
            "num_nodes_any_outside_ansi_b",
            "num_time_points_with_ansi_b_violations",
        ],
    }
}


def build_queries(columns, thresholds, metric_class, on="all"):
    """Build queries for filtering metrics dataframes"""
    queries = []
    if on == "all":
        on = METRIC_MAP[metric_class]["submetrics"]
    metrics = [m for m in on if m in columns]
    for metric in metrics:
        if "min" in metric:
            comparison = ">="
        else:
            comparison = "<="
        query = f"{metric} {comparison} {thresholds[metric_class][metric]}"
        queries.append(query)
    return queries


def synthesize_voltage(results_df):
    """ Reduce voltage metrics table to one time-point like table
    where for each metric, only the worst metric value of all time-points
    is recorded
    """
    filter_cols = ["name",
                   "substation",
                   "feeder",
                   "placement",
                   "sample",
                   "penetration_level",
                   "scenario",
                   "node_type"]

    df = results_df.groupby(filter_cols)[["min_voltage"]].min().reset_index()
    df2 = results_df.groupby(filter_cols)[["max_voltage"]].max().reset_index()
    df = df.merge(df2, how="left", on=filter_cols)
    df3 = (
        results_df.groupby(filter_cols)[
            [
                "num_nodes_any_outside_ansi_b",
                "num_time_points_with_ansi_b_violations"
                ]
        ]
        .max()
        .reset_index()
    )

    df = df.merge(df3, how="left", on=filter_cols)

    return df

def synthesize_thermal(results_df):
    """ Reduce thermal metrics table to one time-point like table
    where for each metric, only the worst metric value of all time-points
    is recorded
    """

    filter_cols = ["name",
                   "substation",
                   "feeder",
                   "placement",
                   "sample",
                   "penetration_level",
                   "scenario"]
    df = (
        results_df.groupby(filter_cols)[
            [
                c for c in results_df.columns if (c not in filter_cols) and (c != "time_point")
                ]
        ]
        .max()
        .reset_index()
    )
    return df

def synthesize(metrics_df, metadata_df, metric_class):
    """ For snapshot hosting capacity analysis,
    reduce metrics and metadata tables to one time-point like tables
    where for each metric, only the worst metric value of all time-points
    is recorded
    """

    """the presence of 'time_point' in the dataframe
    indicates that we are dealing with a snapshot case"""
    if 'time_point' in metrics_df.columns:
        if metric_class == 'voltage':
            metrics_df = synthesize_voltage(metrics_df)
        if metric_class == 'thermal':
            metrics_df = synthesize_thermal(metrics_df)

    return metrics_df, metadata_df


def compute_hc_per_metric_class(
    result_path,
    thresholds,
    metric_class,
    scenario,
    node_types,
    on,
    hc_summary,
):
    """
    Given the metric class, compute its hosting capacity

    Parameters
    ----------
    result_path: str, the output directory of metrics summary tables
    thresholds: dict, the mapping of metric thresholds
    metric_class: str, the metric class, 'voltage' or 'thermal'
    node_types: list, the node types in voltage scenario
    on: list | str, the list of metrics of interest
        example: on = ['min_voltage', 'max_voltage']
    hc_summary: dict

    """
    metric_table = f"{metric_class}_metrics_table.csv"
    metric_df = pd.read_csv(os.path.join(result_path, metric_table))
    metric_df = metric_df[metric_df.scenario == scenario]
    meta_df = pd.read_csv(os.path.join(result_path, "metadata_table.csv"))

    metric_df, meta_df = synthesize(metric_df, meta_df, metric_class)

    if set(metric_df.feeder) == {'None'} or set(meta_df.feeder) == {'None'}:
        meta_df.feeder = meta_df.substation
        metric_df.feeder = metric_df.substation

    if metric_class == "voltage" and len(node_types) == 1:
        metric_df = metric_df[metric_df.node_types == node_types[0]]

    queries = build_queries(metric_df.columns, thresholds, metric_class, on=on)
    query_phrase = " & ".join(queries)

    metric_df = metric_df.mask(metric_df.eq("None")).dropna()
    metric_df.penetration_level = metric_df.penetration_level.astype("float")
    if query_phrase:
        hc_summary = get_hosting_capacity(
            meta_df, metric_df, query_phrase, metric_class, hc_summary
        )
    return hc_summary, query_phrase


def get_hosting_capacity(meta_df, metric_df, query_phrase, metric_class, hc_summary):
    """Return the hosting capacity summary
    
    violation_starting_penetration: the lowest penetration level at which the analysis revealed a violation
	candidate_cba_samples: list of all deployments or samples that have violations at the lowest penetration level
    violation_frequency_by_sample: the ratio between the number of scenarios yielding violations and the total number of scenarios investigated in a given deployment sample 
    recommended_cba_sample: the sample with the highest violation frequency, recommended for further cost benefit analysis or upgrade
    	
    """
    pass_df = metric_df.query(query_phrase)
    fail_df = metric_df.query(f"~({query_phrase})")
    feeders = set(metric_df.feeder)
    cba_samples = set(metric_df['sample'])
    violation_starting_penetration = 0
    violation_frequency_by_sample = {}

    for feeder in feeders:
        if not feeder in hc_summary.keys():
            hc_summary[feeder] = dict()
        temp_pass = pass_df[pass_df.feeder == feeder]
        temp_fail = fail_df[fail_df.feeder == feeder]
        temp_df = metric_df[metric_df.feeder == feeder]
        violation_frequency_by_sample = {d:len(temp_fail.query('sample == @d'))/len(temp_df.query('sample == @d')) for d in temp_df['sample'].unique()}
        recommended_cba_sample = max(violation_frequency_by_sample, key=violation_frequency_by_sample.get)
        fail_penetration_levels = set(temp_fail.penetration_level.values)
        pass_penetration_levels = set(temp_pass.penetration_level.values)
        if len(temp_fail) != 0 and len(temp_pass) == 0:
            # min_hc = min(temp_fail.penetration_level.values)
	    min_hc = 0 # This is supposed to be the PV penetration level of the base case if it passed, 0 otherwise

        elif len(temp_fail) != 0 and len(temp_pass) != 0:
            temp_min_values = pass_penetration_levels.difference(fail_penetration_levels)
           
            if temp_min_list:
                min_hc = max(temp_min_values)
                
                violation_starting_penetration = min(fail_penetration_levels)
                cba_samples = set(temp_fail.loc[temp_fail.penetration_level==violation_starting_penetration, 'sample'])
            else:
                min_hc = 0
        else:
            min_hc = max(pass_penetration_levels)

        if len(temp_pass) != 0:
            max_hc = max(pass_penetration_levels)
	    max_hc = 0 # This is supposed to be the PV penetration level of the base case if it passed, 0 otherwise
        else:
            max_hc = min(fail_penetration_levels)

        total_feeder_load = meta_df[meta_df.feeder == feeder][
            "load_capacity_kw"
        ].values[0]
        max_kW = max_hc * total_feeder_load / 100
        min_kW = min_hc * total_feeder_load / 100

        hc_summary[feeder][metric_class] = {
            "min_hc_pct": min_hc,
            "max_hc_pct": max_hc,
            "min_hc_kw": round(min_kW, 0),
            "max_hc_kw": round(max_kW, 0),
            "violation_starting_penetration": violation_starting_penetration,
            "candidate_cba_samples": list(cba_samples),
            "violation_frequency_by_sample": violation_frequency_by_sample,
            "recommended_cba_sample": recommended_cba_sample,
        }
    return hc_summary


def compute_hc(
    result_path,
    thresholds,
    metric_classes,
    scenario,
    node_types,
    on="all",
):
    """
    Compute hosting capacity

    Parameters
    ----------
    result_path: str, the output directory of metrics summary tables
    thresholds: dict, the mapping of metric thresholds
    metric_classes: list, the list of metric class
    node_types: list, the node types in voltage scenario
    on: list | str, the list of metrics of interest
        example: on = ['min_voltage', 'max_voltage']

    Returns
    -------
    dict: hc_summary
    dict: hc_overall
    list: query strings
    """
    query_list = []
    hc_summary = {}
    hc_overall = {}
    for metric_class in metric_classes:
        hc_summary, query_phrase = compute_hc_per_metric_class(
            result_path,
            thresholds,
            metric_class,
            scenario,
            node_types,
            on,
            hc_summary,
        )
        query_list.append(query_phrase)
    for feeder, dic in hc_summary.items():
        hc_overall[feeder] = {}
        df = pd.DataFrame.from_dict(dic, "index")
        for column in df.columns:
            if 'hc' in column:
                hc_overall[feeder][column] = min(df[column])

    return hc_summary, hc_overall, query_list
