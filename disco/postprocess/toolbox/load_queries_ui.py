
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
            outputs.feeder_head = inputs.feeder_head.query(feeder_head_query_string)

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
            outputs.thermal_metrics = inputs.thermal_metrics.query(thermal_metrics_query_string)

    if voltage_metrics_table_checkbox.value and inputs.voltage_metrics is not None:
        voltage_metrics_query_string = build_query_string(voltage_metrics_hboxes, voltage_metrics_columns)
        if voltage_metrics_query_string:
            outputs.voltage_metrics = inputs.voltage_metrics.query(voltage_metrics_query_string)
    
    query_output.clear_output()
    with query_output:
        print("Query done! Check the 'outputs' variable.")

tables_tab.children = [feeder_head_vbox, feeder_losses_vbox, metadata_vbox, thermal_metrics_vbox, voltage_metrics_vbox]
display(tables_tab)

build_button = widgets.Button(description="Build Query", indent=False)
query_button = widgets.Button(description="Run Query", indent=False)
build_button.on_click(build_queries)
query_button.on_click(query_tables)
display(widgets.HBox([build_button, query_button]))
display(query_output)