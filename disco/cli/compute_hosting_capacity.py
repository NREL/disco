import os

import click

from jade.utils.utils import load_data, dump_data
from PyDSS.common import SnapshotTimePointSelectionMode
import disco
from disco.postprocess.hosting_capacity import compute_hc


def _handle_snapshot_time_point(_, __, val):
    return SnapshotTimePointSelectionMode(val)


@click.command()
@click.argument("output_dir")
@click.option(
    "--metric-class",
    type=click.Choice(["thermal", "voltage"], case_sensitive=True),
    multiple=True,
    default=("thermal", "voltage"),
    show_default=True,
    help="Choose the metric class"
)
@click.option(
    "--on",
    type=click.STRING,
    default=("all", ),
    multiple=True,
    help="The metric included for query, default 'all'"
)
@click.option(
    "--scenario",
    type=click.Choice(["scenario", "control_mode", "pf1", "derms"], case_sensitive=True),
    default="scenario",
    show_default=True,
    help="Choose the PyDSS scenario"
)
@click.option(
    "--node-type",
    type=click.Choice(["primaries", "secondaries"], case_sensitive=True),
    multiple=True,
    default=("primaries", "secondaries"),
    show_default=True,
    help="Choose the node type."
)
@click.option(
    "--hc-thresholds",
    type=click.Path(),
    default=os.path.join(
        os.path.dirname(getattr(disco, "__path__")[0]),
        "disco",
        "postprocess",
        "config",
        "hc_thresholds.toml",
    ),
    show_default=True,
    help="The thresholds for filtering metrics"
)
@click.option(
    "--time-point",
    type=click.Choice([x.value for x in SnapshotTimePointSelectionMode]),
    default=SnapshotTimePointSelectionMode.NONE.value,
    show_default=True,
    callback=_handle_snapshot_time_point,
    help="Time point selection type. Only applicable to snapshot simulations."
)
def compute_hosting_capacity(output_dir, metric_class, on, scenario, node_type, hc_thresholds, time_point):
    """Compute the hosting capacity"""

    if "JADE_PIPELINE_OUTPUT_DIR" in os.environ and "$JADE_PIPELINE_OUTPUT_DIR" in output_dir:
        pipeline_output = os.environ["JADE_PIPELINE_OUTPUT_DIR"]
        output_dir = output_dir.replace("$JADE_PIPELINE_OUTPUT_DIR", pipeline_output)

    if on == ("all", ):
        on = "all"

    hc_summary, overall_hc, query_list = compute_hc(
        result_path=output_dir,
        thresholds=load_data(hc_thresholds),
        metric_classes=metric_class,
        scenario=scenario,
        on=on,
        node_types=node_type
    )

    print("Query List:", query_list)

    # TODO DISCO-315: handle the time_point value for snapshots.
    suffix = "" if time_point == SnapshotTimePointSelectionMode.NONE else f"__{time_point.value}"
    hc_summary_file = os.path.join(output_dir, f"hosting_capacity_summary__{scenario}{suffix}.json")
    dump_data(hc_summary, hc_summary_file, indent=2)
    print(f"Hosting Capacity Summary data is dumped - {hc_summary_file}")

    overall_hc_file = os.path.join(output_dir, f"hosting_capacity_overall__{scenario}{suffix}.json")
    dump_data(overall_hc, overall_hc_file, indent=2)
    print(f"Hosting Capacity Overall data is dumped - {overall_hc_file}")
