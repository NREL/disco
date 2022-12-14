# -*- coding: utf-8 -*-
"""
Created on Thu May 27 01:28:38 2021

@author: senam
"""

import os
import pandas as pd
import numpy as np

PENETRATION_STEP = 5
METRIC_MAP = {
    "thermal": {
        "submetrics": [
            "line_max_instantaneous_loading_pct",
            "line_max_moving_average_loading_pct",
            "line_num_time_points_with_instantaneous_violations",
            "line_num_time_points_with_moving_average_violations",
            "transformer_max_instantaneous_loading_pct",
            "transformer_max_moving_average_loading_pct",
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
    ]

    df = results_df.groupby(filter_cols)[["min_voltage"]].min().reset_index()
    df2 = results_df.groupby(filter_cols)[["max_voltage"]].max().reset_index()
    df = df.merge(df2, how="left", on=filter_cols)
    df3 = (
        results_df.groupby(filter_cols)[
            [
                "num_nodes_any_outside_ansi_b",
                "num_time_points_with_ansi_b_violations",
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
    """Reduce metrics and metadata tables to one time-point like tables
    where for each metric, only the worst metric value of all time-points
    is recorded
    """
    if metric_class == 'voltage':
        # Both snapshot and time-series have primaries + secondaries.
        # Snapshot also has several time points.
        metrics_df = synthesize_voltage(metrics_df)

    # the presence of 'time_point' in the dataframe
    # indicates that we are dealing with a snapshot case"""
    elif metric_class == 'thermal' and 'time_point' in metrics_df.columns:
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
    metric_df = pd.read_csv(
        os.path.join(result_path, metric_table),
        dtype={"sample": np.float64, "penetration_level": np.float64, "placement": str},
    )
    metric_df = metric_df.dropna(axis="index", subset=["sample", "penetration_level"])
    metric_df = metric_df[metric_df.scenario == scenario]
    meta_df = pd.read_csv(
        os.path.join(result_path, "metadata_table.csv"),
        dtype={"sample": np.float64, "penetration_level": np.float64, "placement": str},
    )
    meta_df = meta_df.dropna(axis="index", subset=["sample", "penetration_level"])

    if metric_class == "voltage" and len(node_types) == 1:
        metric_df = metric_df[metric_df.node_type == node_types[0]]

    metric_df, meta_df = synthesize(metric_df, meta_df, metric_class)

    queries = build_queries(metric_df.columns, thresholds, metric_class, on=on)
    query_phrase = " & ".join(queries)

    metric_df.penetration_level = metric_df.penetration_level.astype("float")
    if query_phrase:
        hc_summary = get_hosting_capacity(
            meta_df, metric_df, query_phrase, metric_class, hc_summary
        )

    if metric_class == "thermal":
        if (metric_df.transformer_instantaneous_threshold.isna().any() or 
            metric_df.transformer_instantaneous_threshold.isnull().any()):
            queries = [q for q in queries if 'transformer' not in q]
            noxfmr_metric_df = metric_df.loc[metric_df.transformer_instantaneous_threshold.isna(), :]
            noxfmr_query_phrase = " & ".join(queries)
            if noxfmr_query_phrase:
                hc_summary = get_hosting_capacity(
                    meta_df, noxfmr_metric_df, noxfmr_query_phrase, metric_class, hc_summary
                )
    
    return hc_summary, query_phrase


def get_hosting_capacity(meta_df, metric_df, query_phrase, metric_class, hc_summary):
    """Return the hosting capacity summary

    violation_starting_penetration: the lowest penetration level at which the analysis revealed a violation
    candidate_cba_samples: list of all deployments or samples that have violations at the lowest penetration level
    violation_frequency_by_sample: the ratio between the number of scenarios yielding violations and the total number of scenarios investigated in a given deployment sample
    recommended_cba_sample: the sample with the highest violation frequency, recommended for further cost benefit analysis or upgrade

    """
    
    cba_samples = set(metric_df['sample'])
    violation_starting_penetration = 0
    violation_frequency_by_sample = {}

    for feeder, temp_df in metric_df.groupby(by="feeder"):
        if not feeder in hc_summary.keys():
            hc_summary[feeder] = dict()
        temp_pass = temp_df.query(query_phrase)
        temp_fail = temp_df.query(f"~({query_phrase})")
        violation_frequency_by_sample = {d:len(temp_fail.query('sample == @d'))/len(temp_df.query('sample == @d')) for d in temp_df['sample'].unique()}
        recommended_cba_sample = max(violation_frequency_by_sample, key=violation_frequency_by_sample.get)
        fail_penetration_levels = set(temp_fail.penetration_level.values)
        pass_penetration_levels = set(temp_pass.penetration_level.values)
        if fail_penetration_levels:
            violation_starting_penetration = min(fail_penetration_levels)
            cba_samples = set(temp_fail.loc[temp_fail.penetration_level==violation_starting_penetration, 'sample'])
        else:
            violation_starting_penetration = None
            cba_samples = set()
        temp_min_values = pass_penetration_levels.difference(fail_penetration_levels)
        if len(temp_pass) == 0:
            # min_hc = min(temp_fail.penetration_level.values)
            min_hc = 0 # This is supposed to be the PV penetration level of the base case if it passed, 0 otherwise
            max_hc = 0 # This is supposed to be the PV penetration level of the base case if it passed, 0 otherwise
        elif len(temp_fail) == 0:
            min_hc = max(pass_penetration_levels)
            max_hc = max(pass_penetration_levels)
        else:
            max_hc = max(pass_penetration_levels)
            if temp_min_values:
                min_hc = max(temp_min_values)
            else:
                min_hc = 0

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
        th_sample = dic['thermal']['recommended_cba_sample']
        th_samples = dic['thermal']['candidate_cba_samples']
        v_sample = dic['voltage']['recommended_cba_sample']
        v_samples = dic['voltage']['candidate_cba_samples']
        cba_rec_pen = list(np.arange(
		    hc_overall[feeder]['min_hc_pct'] + PENETRATION_STEP, 
            hc_overall[feeder]['max_hc_pct'] + PENETRATION_STEP, 
            PENETRATION_STEP)
		)
        if th_sample in v_samples:
            hc_overall[feeder]['cba_recommendation'] = [
			    {'sample': th_sample, 'penetrations': cba_rec_pen}
			]
        elif v_sample in th_samples:
            hc_overall[feeder]['cba_recommendation'] = [
			    {'sample':v_sample, 'penetrations':cba_rec_pen}
			]
        else:
            v_cba_rec_pen = list(np.arange(
			    dic['voltage']['min_hc_pct'] + PENETRATION_STEP, 
                dic['voltage']['max_hc_pct'] + PENETRATION_STEP, 
                PENETRATION_STEP
            ))
            th_cba_rec_pen = list(np.arange(
			    dic['thermal']['min_hc_pct'] + PENETRATION_STEP, 
                dic['thermal']['max_hc_pct'] + PENETRATION_STEP, 
                PENETRATION_STEP
            ))
            hc_overall[feeder]['cba_recommendation'] = [
                {'sample': v_sample, 'penetrations': v_cba_rec_pen},
                {'sample': th_sample, 'penetrations': th_cba_rec_pen}
            ]

    return hc_summary, hc_overall, query_list
