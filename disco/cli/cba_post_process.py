"""Adds PV Curtailment columns to CBA output table."""

import click

import pandas as pd


def add_curtailment_columns(filename, curtailment_tolerance):
    """Add PV Curtailment columns to the file."""
    df = pd.read_csv(filename, index_col="Timestamp", parse_dates=True)
    df["PVSystems__Curtailment__commercial (kWh)"] = 0.0
    df["PVSystems__Curtailment__residential (kWh)"] = 0.0
    columns = ["substation", "feeder", "placement", "sample", "penetration_level"]

    def calc_curtailment(pf1, control_mode):
        """Calculate curtailment."""
        if pf1 == 0:
            return 0

        # We may need to consider using this tolerance in the future.
        # if pf1 < curtailment_tolerance:
        #    return 0
        diff = pf1 - control_mode
        #if diff < 0 and abs(diff) < curtailment_tolerance:
        #    return 0
        return diff / pf1

    for (substation, feeder, placement, sample, penetration_level), tdf in df.groupby(by=columns):
        for customer_type in ("commercial", "residential"):
            for sim_type in ("control_mode", "derms"):
                power_col = f"PVSystems__Powers__{customer_type} (kWh)"
                sim_vals = tdf.query("scenario == @sim_type")[power_col]
                if sim_vals.empty:
                    continue
                pf1 = tdf.query("scenario == 'pf1'")[power_col]
                curtailment = pf1.combine(sim_vals, calc_curtailment)
                cond = lambda x: (
                    (x["substation"] == substation)
                    & (x["feeder"] == feeder)
                    & (x["placement"] == placement)
                    & (x["sample"] == sample)
                    & (x["penetration_level"] == penetration_level)
                    & (x["scenario"] == sim_type)
                )
                df.loc[cond, f"PVSystems__Curtailment__{customer_type} (kWh)"] = curtailment

    df.to_csv(filename)
    print(f"Added PV Curtailment to {filename}")


@click.command()
@click.argument("output_dir")
# This is disabled because we don't know the best tolerance for these customer-type
# aggregations. Leaving it in the code in case we need it in the future.
# @click.option(
#    "-d", "--curtailment-tolerance",
#    default=0.0001,
#    show_default=True,
#    help="Set curtailment to 0 if the diff is less than this value.",
# )
def cba_post_process(output_dir, curtailment_tolerance=0.0001):
    """Perform post-processing of CBA tables."""
    add_curtailment_columns(output_dir, curtailment_tolerance)


if __name__ == "__main__":
    cba_post_process()
