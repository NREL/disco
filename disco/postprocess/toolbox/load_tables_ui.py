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
        
        if feeder_head_table_checkbox.value:
            feeder_head_table = os.path.join(input_path.value, "feeder_head_table.csv")
            inputs.feeder_head = pd.read_csv(feeder_head_table)
            print("Feeder head table loaded.")
        
        if feeder_losses_table_checkbox.value:
            feeder_losses_table = os.path.join(input_path.value, "feeder_losses_table.csv")
            inputs.feeder_losses = pd.read_csv(feeder_losses_table)
            print("Feeder losses table loaded.")
        
        if metadata_table_checkbox.value:
            metadata_table = os.path.join(input_path.value, "metadata_table.csv")
            inputs.metadata = pd.read_csv(metadata_table)
            print("Metadata table loaded.")
        
        if thermal_metrics_table_checkbox.value:
            thermal_metrics_table = os.path.join(input_path.value, "thermal_metrics_table.csv")
            inputs.thermal_metrics = pd.read_csv(thermal_metrics_table)
            print("Thermal metrics table loaded.")
        
        if voltage_metrics_table_checkbox.value:
            voltage_metrics_table = os.path.join(input_path.value, "voltage_metrics_table.csv")
            inputs.voltage_metrics = pd.read_csv(voltage_metrics_table)
            print("Voltage metrics table loaded.")

display(load_tab)
display(load_button, load_output)
load_button.on_click(load_tables)