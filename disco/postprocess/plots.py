import logging
import os

import pandas as pd
import matplotlib.pyplot as plt 

logger = logging.getLogger(__name__)


def plot_voltage(output_dir, scenario):
    voltage_metrics_table = os.path.join(output_dir, "voltage_metrics_table.csv")
    voltage_metrics = pd.read_csv(voltage_metrics_table)
    feeder_example = voltage_metrics['feeder'].unique()[0]
    voltage_metrics = voltage_metrics[voltage_metrics['feeder']==feeder_example]

    fig, ax = plt.subplots(figsize=(8,8))
    ax.scatter(
        voltage_metrics[voltage_metrics['node_type']=='primaries']['penetration_level'],
        voltage_metrics[voltage_metrics['node_type']=='primaries']["max_voltage"],
        facecolors='none',
        edgecolors='C0',
        label="primary"
    )
    ax.scatter(
        voltage_metrics[voltage_metrics['node_type']=='secondaries']['penetration_level'],
        voltage_metrics[voltage_metrics['node_type']=='secondaries']["max_voltage"],
        facecolors='none',
        edgecolors='C1',
        label="secondary"
    )
    ax.legend()
    ax.set_title(feeder_example)
    ax.set_xlabel("Penetration level")
    ax.set_ylabel("max_voltage (pu)")
    fig.savefig(os.path.join(output_dir,"max_voltage_pri_sec.png"))

    fig, ax = plt.subplots(figsize=(8,8))
    ax.scatter(
        voltage_metrics[voltage_metrics['scenario']=='pf1']['penetration_level'],
        voltage_metrics[voltage_metrics['scenario']=='pf1']["max_voltage"],
        facecolors='none',
        edgecolors='C0',
        label="base_case:pf1"
    )
    ax.scatter(
        voltage_metrics[voltage_metrics['scenario']=='control_mode']['penetration_level'],
        voltage_metrics[voltage_metrics['scenario']=='control_mode']["max_voltage"],
        facecolors='none',
        edgecolors='C1',
        label="control_mode:volt-var"
    )
    ax.legend()
    ax.set_title(feeder_example)
    ax.set_xlabel("Penetration level")
    ax.set_ylabel("max_voltage (pu)")
    fig.savefig(os.path.join(output_dir,"max_voltage_base_voltvar.png"))
    logger.info("Voltage plot created.")


def plot_hc(output_dir, scenario):
    overall_file = os.path.join(output_dir, f"hosting_capacity_overall__{scenario}.json")
    overall = pd.read_json(overall_file)

    _, ax = plt.subplots(figsize=(8,8))
    y_pos = overall['feeder']
    ax.barh(
        y_pos,
        overall['min_hc_pct'],
        label="no violation",
        color='limegreen'
    )
    ax.barh(
        y_pos,
        overall['max_hc_pct']-overall['min_hc_pct'],
        left=overall['min_hc_pct'],
        label="some violation",
        color='gold'
    )
    ax.barh(
        y_pos,
        200-overall['max_hc_pct'],
        left=overall['max_hc_pct'],
        label="violation",
        color='tomato'
    )
    ax.set_title(f"HCA heatmap: {scenario}")
    ax.set_xlabel("Penetration level (%)")
    ax.legend(ncol=3)
    plt.savefig(os.path.join(output_dir,"hca.png"))
    
    logger.info("Hostint capacity plot created.")
