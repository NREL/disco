import logging
import os

import pandas as pd

logger = logging.getLogger(__name__)


def plot_voltage(output_dir, scenario):
    voltage_metrics_table = os.path.join(output_dir, "voltage_metrics_table.csv")
    voltage_metrics = pd.read_csv(voltage_metrics_table)
    print(voltage_metrics.head())
    logger.info("Voltage plot created.")


def plot_hc(output_dir, scenario):
    overall_pf1_file = os.path.join(output_dir, f"hosting_capacity_overall__{scenario}.json")
    overall_pf1 = pd.read_json(overall_pf1_file)
    print(overall_pf1.head())
    logger.info("Hostint capacity plot created.")
