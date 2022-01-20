"""
This script creates technical parameter catalogue for transformers, lines, regulators, reg-controls, capacitors
"""
import shutil
import click
import os

from .common_functions import (
    get_cn_data,
    get_wire_data,
    get_all_line_info,
    get_all_transformer_info,
    get_capacitor_info,
    get_regcontrol_info,
    get_line_geometry,
    get_line_code,
    determine_available_line_upgrades,
    determine_available_xfmr_upgrades,
    run_selective_master_dss,
)


@click.command()
@click.option(
    "-o",
    "--output-folder",
    required=True,
    help="output folder path",
)
@click.option(
    "-f",
    "--feeder-path",
    required=True,
    help="feeder path",
)
@click.option(
    "--delete-existing",
    type=click.Choice(("true", "false"), case_sensitive=False),
    default="false",
    show_default=True,
    help="Whether to delete the existing outputs directory",
)
def prepare_technical_catalogue(output_folder, feeder_path, delete_existing):
    if (delete_existing.lower() == "true") and os.path.exists(output_folder):
        shutil.rmtree(output_folder)
    os.makedirs(os.path.join(output_folder, "line_upgrade_options"), exist_ok=True)
    os.makedirs(os.path.join(output_folder, "xfmr_upgrade_options"), exist_ok=True)
    os.makedirs(os.path.join(output_folder, "all_lines"), exist_ok=True)
    os.makedirs(os.path.join(output_folder, "all_xfmrs"), exist_ok=True)
    os.makedirs(os.path.join(output_folder, "regcontrols"), exist_ok=True)
    os.makedirs(os.path.join(output_folder, "capacitors"), exist_ok=True)
    os.makedirs(os.path.join(output_folder, "line_geometry"), exist_ok=True)
    os.makedirs(os.path.join(output_folder, "line_code"), exist_ok=True)
    os.makedirs(os.path.join(output_folder, "wire_data"), exist_ok=True)
    os.makedirs(os.path.join(output_folder, "cn_data"), exist_ok=True)

    prefix = "feeder_name1"
    master_filename = "Master.dss"
    master_path = os.path.join(feeder_path, master_filename)
    # reload_dss_circuit(dss_file_list=[master_path], commands_list=None)
    run_selective_master_dss(master_filepath=master_path)

    all_lines_df = get_all_line_info(compute_loading=False)
    all_xfmrs_df = get_all_transformer_info(compute_loading=False)
    line_upgrade_options = determine_available_line_upgrades(all_lines_df)
    xfmr_upgrade_options = determine_available_xfmr_upgrades(all_xfmrs_df)

    line_upgrade_options.to_csv(
        os.path.join(
            output_folder, "line_upgrade_options", f"{prefix}_line_upgrade_options.csv"
        )
    )
    xfmr_upgrade_options.to_csv(
        os.path.join(
            output_folder, "xfmr_upgrade_options", f"{prefix}_xfmr_upgrade_options.csv"
        )
    )
    all_lines_df.to_csv(
        os.path.join(output_folder, "all_lines", f"{prefix}_all_lines.csv")
    )
    all_xfmrs_df.to_csv(
        os.path.join(output_folder, "all_xfmrs", f"{prefix}_all_xfmrs.csv")
    )
    get_regcontrol_info().to_csv(
        os.path.join(output_folder, "regcontrols", f"{prefix}_regcontrols.csv")
    )
    get_capacitor_info().to_csv(
        os.path.join(output_folder, "capacitors", f"{prefix}_capacitors.csv")
    )
    get_line_geometry().to_csv(
        os.path.join(output_folder, "line_geometry", f"{prefix}_line_geometry.csv")
    )
    get_line_code().to_csv(
        os.path.join(output_folder, "line_code", f"{prefix}_line_code.csv")
    )
    get_wire_data().to_csv(
        os.path.join(output_folder, "wire_data", f"{prefix}_wire_data.csv")
    )
    get_cn_data().to_csv(
        os.path.join(output_folder, "cn_data", f"{prefix}_cn_data.csv")
    )


if __name__ == "__main__":
    prepare_technical_catalogue()
