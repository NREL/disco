import os
from pprint import pprint
from types import SimpleNamespace

import pandas as pd
import ipywidgets as widgets
from IPython.display import display

from disco.postprocess.hosting_capacity import get_hosting_capacity

# Layouts
field_layout = widgets.Layout(width="50%")
comp_layout = widgets.Layout(width="10%")
value_layout = widgets.Layout(width="40%")
textarea_layout = widgets.Layout(width="99.5%", height="200px")

# Options
comparison_options = ["==", "<", "<=", ">", ">="]
bool_options = [False, True]
scenario_options = ["scenario", "pf1", "control_mode"]
node_type_options = ["primaries", "secondaries"]
placement_options = ["close", "far", "random"]

# Namespaces
inputs = SimpleNamespace(
    feeder_head=None,
    feeder_losses=None,
    metadata=None,
    thermal_metrics=None,
    voltage_metrics=None
)

queryset = SimpleNamespace(
    feeder_head=None,
    feeder_losses=None,
    metadata=None,
    thermal_metrics=None,
    voltage_metrics=None
)

hc = SimpleNamespace(
    summary=None,
    overall=None
)

# Load Data
load_tab = widgets.Tab(indent=False)
load_tab.set_title(0, "Load Tables")

input_path = widgets.Text(placeholder="result directory of summary tables", indent=False, layout=widgets.Layout(width="99.5%"))
feeder_head_table_checkbox = widgets.Checkbox(description="Feeder Head Table", value=False, indent=False)
feeder_losses_table_checkbox = widgets.Checkbox(description="Feeder Losses Table", value=False, indent=False)
metadata_table_checkbox = widgets.Checkbox(description="Metadata Table", value=False, indent=False)
thermal_metrics_table_checkbox = widgets.Checkbox(description="Thermal Metrics Table", value=False, indent=False)
voltage_metrics_table_checkbox = widgets.Checkbox(description="Voltage Metrics Table", value=False, indent=False)
load_box = widgets.VBox([
    input_path,
    feeder_head_table_checkbox,
    feeder_losses_table_checkbox,
    metadata_table_checkbox,
    thermal_metrics_table_checkbox,
    voltage_metrics_table_checkbox
])

load_tab.children = [load_box]
load_button = widgets.Button(description="Load Metrics", indent=False)
load_output = widgets.Output(indent=False)

def load_tables(arg):
    """Load metrics tables into memory"""
    load_output.clear_output()
    with load_output:
        if not input_path.value:
            print("Please provide the output directory of metrics tables.")
            return

        if not os.path.exists(input_path.value):
            print(f"Output directory does not exist! '{input_path.value}'")
            return
        
        selected = False
        if feeder_head_table_checkbox.value:
            selected = True
            feeder_head_table = os.path.join(input_path.value, "feeder_head_table.csv")
            inputs.feeder_head = pd.read_csv(feeder_head_table)
        
        if feeder_losses_table_checkbox.value:
            selected = True
            feeder_losses_table = os.path.join(input_path.value, "feeder_losses_table.csv")
            inputs.feeder_losses = pd.read_csv(feeder_losses_table)
        
        if metadata_table_checkbox.value:
            selected = True
            metadata_table = os.path.join(input_path.value, "metadata_table.csv")
            inputs.metadata = pd.read_csv(metadata_table)
        
        if thermal_metrics_table_checkbox.value:
            selected = True
            thermal_metrics_table = os.path.join(input_path.value, "thermal_metrics_table.csv")
            inputs.thermal_metrics = pd.read_csv(thermal_metrics_table)
        
        if voltage_metrics_table_checkbox.value:
            selected = True
            voltage_metrics_table = os.path.join(input_path.value, "voltage_metrics_table.csv")
            inputs.voltage_metrics = pd.read_csv(voltage_metrics_table)

        if selected:
            print("Selected tables loaded, check 'inputs' namespace.")
        else:
            print("No table selected, please select first.")

display(load_tab)
display(load_button, load_output)
load_button.on_click(load_tables)


# Tab
tables_tab = widgets.Tab(indent=False)
titles = ["Feeder Head", "Feeder Losses", "Metadata", "Thermal Metrics", "Voltage Metrics"]
for i, title in enumerate(titles):
    tables_tab.set_title(i, title)


# Feeder head table
feeder_head_columns = {
    "name": str,
    "substation": str,
    "feeder": str,
    "placement": str,
    "sample": int,
    "penetration_level": int,
    "scenario": str,
    "FeederHeadLine": str,
    "FeederHeadLoading": float,
    "FeederHeadLoadKW": float,
    "FeederHeadLoadKVar": float,
    "ReversePowerFlow": bool
}
feeder_head_hboxes = []
for column, data_type in feeder_head_columns.items():
    checkbox = widgets.Checkbox(description=column, value=False, indent=False, layout=field_layout)
    comparison = widgets.Dropdown(options=comparison_options, layout=comp_layout)
    if data_type is int:
        value = widgets.IntText(layout=value_layout)
    elif data_type is float:
        value = widgets.FloatText(layout=value_layout)
    elif data_type is bool:
        value = widgets.Dropdown(options=bool_options, layout=value_layout)
    elif checkbox.description == "scenario":
        value = widgets.Dropdown(options=scenario_options, layout=value_layout)
    elif checkbox.description == "placement":
        value = widgets.Dropdown(options=placement_options, layout=value_layout)
    else:
        value = widgets.Text(layout=value_layout)
    box = widgets.HBox([checkbox, comparison, value])
    feeder_head_hboxes.append(box)
feeder_head_textarea = widgets.Textarea(indent=False, placeholder="Query String", layout=textarea_layout)
feeder_head_hboxes.append(feeder_head_textarea)
feeder_head_vbox = widgets.VBox(feeder_head_hboxes)


# Feeder losses table
feeder_losses_columns = {
    "name": str,
    "substation": str,
    "feeder": str,
    "placement": str,
    "sample": int,
    "penetration_level": int,
    "scenario": str,
    "total_losses_kwh": float,
    "line_losses_kwh": float,
    "transformer_losses_kwh": float,
    "total_load_demand_kwh": float
}
feeder_losses_hboxes = []
for column, data_type in feeder_losses_columns.items():
    checkbox = widgets.Checkbox(description=column, value=False, indent=False, layout=field_layout)
    comparison = widgets.Dropdown(options=comparison_options, layout=comp_layout)
    if data_type is int:
        value = widgets.IntText(layout=value_layout)
    elif data_type is float:
        value = widgets.FloatText(layout=value_layout)
    elif data_type is bool:
        value = widgets.Dropdown(options=bool_options, layout=value_layout)
    elif checkbox.description == "scenario":
        value = widgets.Dropdown(options=scenario_options, layout=value_layout)
    elif checkbox.description == "placement":
        value = widgets.Dropdown(options=placement_options, layout=value_layout)
    else:
        value = widgets.Text(layout=value_layout)
    box = widgets.HBox([checkbox, comparison, value])
    feeder_losses_hboxes.append(box)
feeder_losses_textarea = widgets.Textarea(indent=False, placeholder="Query String", layout=textarea_layout)
feeder_losses_hboxes.append(feeder_losses_textarea)
feeder_losses_vbox = widgets.VBox(feeder_losses_hboxes)


# Metadata Table
metadata_columns = {
    "name": str,
    "substation": str,
    "feeder": str,
    "placement": str,
    "sample": int,
    "penetration_level": int,
    "scenario": str,
    "pct_pv_to_load_ratio": float,
    "pv_capacity_kw": float,
    "load_capacity_kw": float,
}
metadata_hboxes = []
for column, data_type in metadata_columns.items():
    checkbox = widgets.Checkbox(description=column, value=False, indent=False, layout=field_layout)
    comparison = widgets.Dropdown(options=comparison_options, layout=comp_layout)
    if data_type is int:
        value = widgets.IntText(layout=value_layout)
    elif data_type is float:
        value = widgets.FloatText(layout=value_layout)
    elif data_type is bool:
        value = widgets.Dropdown(options=bool_options, layout=value_layout)
    elif checkbox.description == "scenario":
        value = widgets.Dropdown(options=scenario_options, layout=value_layout)
    elif checkbox.description == "placement":
        value = widgets.Dropdown(options=placement_options, layout=value_layout)
    else:
        value = widgets.Text(layout=value_layout)
    box = widgets.HBox([checkbox, comparison, value])
    metadata_hboxes.append(box)
metadata_textarea = widgets.Textarea(indent=False, placeholder="Query String", layout=textarea_layout)
metadata_hboxes.append(metadata_textarea)
metadata_vbox = widgets.VBox(metadata_hboxes)


# Thermal metrics table
thermal_metrics_columns = {
    "name": str,
    "substation": str,
    "feeder": str,
    "placement": str,
    "sample": int,
    "penetration_level": int,
    "scenario": str,
    "line_max_instantaneous_loading_pct": float,
    "line_max_moving_average_loading_pct": float,
    "line_window_size_hours": int,
    "line_num_time_points_with_instantaneous_violations": int,
    "line_num_time_points_with_moving_average_violations": int,
    "line_instantaneous_threshold": float,
    "line_moving_average_threshold": float,
    "transformer_max_instantaneous_loading_pct": float,
    "transformer_max_moving_average_loading_pct": float,
    "transformer_window_size_hours": int,
    "transformer_num_time_points_with_instantaneous_violations": int,
    "transformer_num_time_points_with_moving_average_violations": int,
    "transformer_instantaneous_threshold": float,
    "transformer_moving_average_threshold": float
}
thermal_metrics_hboxes = []
for column, data_type in thermal_metrics_columns.items():
    checkbox = widgets.Checkbox(description=column, value=False, indent=False, layout=field_layout)
    comparison = widgets.Dropdown(options=comparison_options, layout=comp_layout)
    if data_type is int:
        value = widgets.IntText(layout=value_layout)
    elif data_type is float:
        value = widgets.FloatText(layout=value_layout)
    elif data_type is bool:
        value = widgets.Dropdown(options=bool_options, layout=value_layout)
    elif checkbox.description == "scenario":
        value = widgets.Dropdown(options=scenario_options, layout=value_layout)
    elif checkbox.description == "placement":
        value = widgets.Dropdown(options=placement_options, layout=value_layout)
    else:
        value = widgets.Text(layout=value_layout)
    box = widgets.HBox([checkbox, comparison, value])
    thermal_metrics_hboxes.append(box)
thermal_metrics_textarea = widgets.Textarea(indent=False, placeholder="Query String", layout=textarea_layout)
thermal_metrics_hboxes.append(thermal_metrics_textarea)
thermal_metrics_vbox = widgets.VBox(thermal_metrics_hboxes)


# Voltage metrics table
voltage_metrics_columns = {
    "name": str,
    "substation": str,
    "feeder": str,
    "placement": str,
    "sample": int,
    "penetration_level": int,
    "scenario": str,
    "node_type": str,
    "num_nodes_any_outside_ansi_b": int,
    "num_time_points_with_ansi_b_violations": int,
    "min_voltage": float,
    "max_voltage": float
}
voltage_metrics_hboxes = []
for column, data_type in voltage_metrics_columns.items():
    checkbox = widgets.Checkbox(description=column, value=False, indent=False, layout=field_layout)
    comparison = widgets.Dropdown(options=comparison_options, layout=comp_layout)
    if data_type is int:
        value = widgets.IntText(layout=value_layout)
    elif data_type is float:
        value = widgets.FloatText(layout=value_layout)
    elif data_type is bool:
        value = widgets.Dropdown(options=bool_options, layout=value_layout)
    elif checkbox.description == "node_type":
        value = widgets.Dropdown(options=node_type_options, layout=value_layout)
    elif checkbox.description == "scenario":
        value = widgets.Dropdown(options=scenario_options, layout=value_layout)
    elif checkbox.description == "placement":
        value = widgets.Dropdown(options=placement_options, layout=value_layout)
    else:
        value = widgets.Text(layout=value_layout)
    box = widgets.HBox([checkbox, comparison, value])
    voltage_metrics_hboxes.append(box)
voltage_metrics_textarea = widgets.Textarea(indent=False, placeholder="Query String", layout=textarea_layout)
voltage_metrics_hboxes.append(voltage_metrics_textarea)
voltage_metrics_vbox = widgets.VBox(voltage_metrics_hboxes)


# Query
query_output = widgets.Output(index=False)

def build_query_string(hboxes, columns):
    query_string = ""
    for hbox in hboxes:
        
        if isinstance(hbox, widgets.Textarea):
            continue
        
        checkbox = hbox.children[0]
        if not checkbox.value:
            continue
        
        comparision = hbox.children[1]
        raw_value, value_type = hbox.children[2], columns[checkbox.description]
        if value_type is str:
            value = [v.strip() for v in raw_value.value.split(",")]
        else:
            value = raw_value.value
        
        if not query_string:
            query_string = f"{checkbox.description}{comparision.value}{value}"
        else:
            query_string += f" & {checkbox.description}{comparision.value}{value}"
    
    return query_string


def build_queries(arg):
    if feeder_head_table_checkbox.value:
        feeder_head_query_string = build_query_string(feeder_head_hboxes, feeder_head_columns)
        feeder_head_textarea.value = feeder_head_query_string
    
    if feeder_losses_table_checkbox.value:
        feeder_losses_query_string = build_query_string(feeder_losses_hboxes, feeder_losses_columns)
        feeder_losses_textarea.value = feeder_losses_query_string
    
    if metadata_table_checkbox.value:
        metadata_query_string = build_query_string(metadata_hboxes, metadata_columns)
        metadata_textarea.value = metadata_query_string
    
    if thermal_metrics_table_checkbox.value:
        thermal_metrics_query_string = build_query_string(thermal_metrics_hboxes, thermal_metrics_columns)
        thermal_metrics_textarea.value = thermal_metrics_query_string
    
    if voltage_metrics_table_checkbox.value:
        voltage_metrics_query_string = build_query_string(voltage_metrics_hboxes, voltage_metrics_columns)
        voltage_metrics_textarea.value = voltage_metrics_query_string
    
    query_output.clear_output()
    with query_output:
        print("Query built! Check the query string in text area.")


def query_tables(arg):
    if feeder_head_table_checkbox.value and inputs.feeder_head is not None:
        feeder_head_query_string = build_query_string(feeder_head_hboxes, feeder_head_columns)
        if feeder_head_query_string:
            queryset.feeder_head = inputs.feeder_head.query(feeder_head_query_string)

    if feeder_losses_table_checkbox.value and inputs.feeder_losses is not None:
        feeder_losses_query_string = build_query_string(feeder_losses_hboxes, feeder_losses_columns)
        if feeder_losses_query_string:
            outpus.feeder_losses = inputs.feeder_losses.query(feeder_losses_query_string)

    if metadata_table_checkbox.value and inputs.metadata is not None:
        metadata_query_string = build_query_string(metadata_hboxes, metadata_columns)
        if metadata_query_string:
            outpus.metadata = inputs.metadata.query(metadata_query_string)

    if thermal_metrics_table_checkbox.value and inputs.thermal_metrics is not None:
        thermal_metrics_query_string = build_query_string(thermal_metrics_hboxes, thermal_metrics_columns)
        if thermal_metrics_query_string:
            queryset.thermal_metrics = inputs.thermal_metrics.query(thermal_metrics_query_string)

    if voltage_metrics_table_checkbox.value and inputs.voltage_metrics is not None:
        voltage_metrics_query_string = build_query_string(voltage_metrics_hboxes, voltage_metrics_columns)
        if voltage_metrics_query_string:
            queryset.voltage_metrics = inputs.voltage_metrics.query(voltage_metrics_query_string)
    
    query_output.clear_output()
    with query_output:
        print("Query done! Check the 'queryset' namespace.")


def compute_thermal_hc(hc_summary):
    metric_df = queryset.thermal_metrics
    if metric_df is None:
        return
    metric_df = metric_df.mask(metric_df.eq("None")).dropna()
    metric_df.penetration_level = metric_df.penetration_level.astype("float")

    query_phrase = thermal_metrics_textarea.value
    if query_phrase:
        hc_summary = get_hosting_capacity(
            inputs.metadata, metric_df, query_phrase, "thermal", hc_summary
        )


def compute_voltage_hc(hc_summary):
    metric_df = queryset.voltage_metrics
    if metric_df is None:
        return
    metric_df = metric_df.mask(metric_df.eq("None")).dropna()
    metric_df.penetration_level = metric_df.penetration_level.astype("float")

    query_phrase = voltage_metrics_textarea.value
    if query_phrase:
        hc_summary = get_hosting_capacity(
            inputs.metadata, metric_df, query_phrase, "voltage", hc_summary
        )


def compute_hc(arg):
    query_output.clear_output()
    if not metadata_table_checkbox.value:
        with query_output:
            print("Metadata table has not been loaded, please load first.")
        return
    
    hc_summary = {}
    hc_overall = {}
    compute_thermal_hc(hc_summary)
    compute_voltage_hc(hc_summary)
    
    for feeder, data in hc_summary.items():
        hc_overall[feeder] = {}
        df = pd.DataFrame.from_dict(data, "index")
        for column in df.columns:
            hc_overall[feeder][column] = min(df[column])

    hc.summary = hc_summary
    hc.overall = hc_overall
    
    with query_output:
        print("Compute done! Check the 'hc' namespace.")


# Query UI
tables_tab.children = [feeder_head_vbox, feeder_losses_vbox, metadata_vbox, thermal_metrics_vbox, voltage_metrics_vbox]
display(tables_tab)

build_button = widgets.Button(description="Build Query", indent=False)
query_button = widgets.Button(description="Run Query", indent=False)
compute_button = widgets.Button(description="Compute HC", indent=False)
build_button.on_click(build_queries)
query_button.on_click(query_tables)
compute_button.on_click(compute_hc)
display(widgets.HBox([build_button, query_button, compute_button]))
display(query_output)
