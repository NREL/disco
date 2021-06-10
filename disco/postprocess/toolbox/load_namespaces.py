import os
from pprint import pprint
from types import SimpleNamespace

import pandas as pd
import ipywidgets as widgets
from IPython.display import display

# Layouts
field_layout = widgets.Layout(width="50%")
comp_layout = widgets.Layout(width="10%")
value_layout = widgets.Layout(width="40%")
textarea_layout = widgets.Layout(width="99.5%", height="300px")

# Options
comparison_options = ["==", "<", "<=", ">", ">="]
bool_options = [False, True]
scenario_options = ["scenario", "pf1", "control_mode"]
node_type_options = ["primaries", "secondaries"]
placement_options = ["close", "far", "random"]


# Tables
inputs = SimpleNamespace(
    feeder_head=None,
    feeder_losses=None,
    metadata=None,
    thermal_metrics=None,
    voltage_metrics=None
)

outputs = SimpleNamespace(
    feeder_head=None,
    feeder_losses=None,
    metadata=None,
    thermal_metrics=None,
    voltage_metrics=None
)
print("inputs:")
pprint(inputs)
print()
print("outputs:")
pprint(outputs)