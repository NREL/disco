import json
from disco.postprocess.hosting_capacity import get_hosting_capacity

def compute_thermal_hc(hc_summary):
    metric_df = outputs.thermal_metrics
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
    metric_df = outputs.voltage_metrics
    if metric_df is None:
        return
    metric_df = metric_df.mask(metric_df.eq("None")).dropna()
    metric_df.penetration_level = metric_df.penetration_level.astype("float")

    query_phrase = voltage_metrics_textarea.value
    if query_phrase:
        hc_summary = get_hosting_capacity(
            inputs.metadata, metric_df, query_phrase, "voltage", hc_summary
        )


def compute_hc():
    hc_summary = {}
    compute_thermal_hc(hc_summary)
    compute_voltage_hc(hc_summary)
    print(json.dumps(hc_summary, indent=2))


if __name__ == '__main__':
    compute_hc()
