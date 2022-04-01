import time
import json
import logging
import pandas as pd

from .thermal_upgrade_functions import *
from disco.models.upgrade_cost_analysis_generic_model import UpgradeResultModel

logger = logging.getLogger(__name__)


def determine_thermal_upgrades(
    master_path,
    enable_pydss_solve,
    pydss_volt_var_model,
    thermal_config,
    line_upgrade_options_file,
    xfmr_upgrade_options_file,
    thermal_summary_file,
    thermal_upgrades_dss_filepath,
    output_csv_line_upgrades_filepath,
    output_csv_xfmr_upgrades_filepath,
    ignore_switch=True,
    verbose=False
):
    pydss_params = {
        "enable_pydss_solve": enable_pydss_solve,
        "pydss_volt_var_model": pydss_volt_var_model
    }
    # start upgrades
    pydss_params = reload_dss_circuit(dss_file_list=[master_path], commands_list=None, **pydss_params)

    voltage_upper_limit = thermal_config["voltage_upper_limit"]
    voltage_lower_limit = thermal_config["voltage_lower_limit"]

    orig_lines_df = get_all_line_info(compute_loading=False)
    orig_xfmrs_df = get_all_transformer_info(compute_loading=False)

    if thermal_config["read_external_catalog"]:
        with open(thermal_config["external_catalog"]) as json_file:
            upgrade_technical_catalog = json.load(json_file)
        line_upgrade_options = pd.DataFrame.from_dict(upgrade_technical_catalog['line'])
        xfmr_upgrade_options = pd.DataFrame.from_dict(upgrade_technical_catalog['transformer'])
        # this will remove any duplicates if present
        line_upgrade_options = determine_available_line_upgrades(line_upgrade_options)
        xfmr_upgrade_options = determine_available_xfmr_upgrades(xfmr_upgrade_options)
        # might also need LineCode, WireData, access dictionary when needed
    else:
        line_upgrade_options = determine_available_line_upgrades(orig_lines_df)
        xfmr_upgrade_options = determine_available_xfmr_upgrades(orig_xfmrs_df)
        line_upgrade_options.to_csv(line_upgrade_options_file)
        xfmr_upgrade_options.to_csv(xfmr_upgrade_options_file)

    (
        initial_bus_voltages_df,
        initial_undervoltage_bus_list,
        initial_overvoltage_bus_list,
        initial_buses_with_violations,
    ) = get_bus_voltages(
        upper_limit=voltage_upper_limit, lower_limit=voltage_lower_limit, **pydss_params
    )

    initial_xfmr_loading_df = get_all_transformer_info(
        compute_loading=True, upper_limit=thermal_config["xfmr_upper_limit"]
    )
    initial_line_loading_df = get_all_line_info(
        compute_loading=True,
        upper_limit=thermal_config["line_upper_limit"],
        ignore_switch=ignore_switch,
    )
    initial_overloaded_xfmr_list = list(
        initial_xfmr_loading_df.loc[initial_xfmr_loading_df["status"] == "overloaded"][
            "name"
        ].unique()
    )
    initial_overloaded_line_list = list(
        initial_line_loading_df.loc[initial_line_loading_df["status"] == "overloaded"][
            "name"
        ].unique()
    )
    breakpoint()
    initial_results = UpgradeResultModel(
        name="",
        scenario="",
        stage="Initial",
        upgrade_type="Thermal",
        # upgrade_status = upgrade_status,
        thermal_violations_present=(len(initial_overloaded_xfmr_list) + len(initial_overloaded_line_list)) > 0,
        voltage_violations_present=(len(initial_undervoltage_bus_list) + len(initial_overvoltage_bus_list)) > 0,
        max_voltage_on_any_bus=initial_bus_voltages_df['Max per unit voltage'].max(),
        min_voltage_on_any_bus=initial_bus_voltages_df['Min per unit voltage'].min(),
        num_of_buses_with_voltage_violations=len(initial_undervoltage_bus_list) + len(initial_overvoltage_bus_list),
        num_of_overvoltage_violations_buses_above_voltage_upper_limit=len(initial_overvoltage_bus_list),
        voltage_upper_limit=voltage_upper_limit,
        num_of_undervoltage_violations_buses_below_voltage_lower_limit=len(initial_undervoltage_bus_list),
        voltage_lower_limit=voltage_lower_limit,
        max_line_loading=initial_line_loading_df['max_per_unit_loading'].max(),
        max_xfmr_loading=initial_xfmr_loading_df['max_per_unit_loading'].max(),
        num_of_lines_with_violations_above_line_upper_limit=len(initial_overloaded_line_list),
        line_upper_limit=thermal_config['line_upper_limit'],
        num_of_xfmrs_with_violations_above_xfmr_upper_limit=len(initial_overloaded_xfmr_list),
        xfmr_upper_limit=thermal_config['xfmr_upper_limit']
    )
    temp_results = dict(initial_results)
    # TODO check is this okay to remove keys here.
    temp_results.pop("name")
    temp_results.pop("scenario")
    output_results = [temp_results]
    pd.DataFrame.from_dict(output_results).to_csv(thermal_summary_file, index=False)

    if len(initial_overloaded_xfmr_list) > 0 or len(initial_overloaded_line_list) > 0:
        upgrade_status = "Thermal Upgrades Required"  # status - whether upgrades done or not
    else:
        upgrade_status = "Thermal Upgrades not Required"  # status - whether upgrades done or not
    logger.info(upgrade_status)

    # Mitigate thermal violations
    iteration_counter = 0
    # if number of violations is very high,  limit it to a small number
    max_upgrade_iteration = min(
        thermal_config["upgrade_iteration_threshold"],
        len(initial_overloaded_xfmr_list) + len(initial_overloaded_line_list),
    )
    start = time.time()
    logger.info(
        f"Simulation start time: {start}"
    )
    logger.info(
        f"Limit on number of thermal upgrade iterations: {max_upgrade_iteration}"
    )
    commands_list = []
    line_upgrades_df = pd.DataFrame()
    xfmr_upgrades_df = pd.DataFrame()
    overloaded_line_list = initial_overloaded_line_list
    overloaded_xfmr_list = initial_overloaded_xfmr_list

    while (len(overloaded_line_list) > 0 or len(overloaded_xfmr_list) > 0) and (
        iteration_counter < max_upgrade_iteration
    ):
        prev_num_xfmr_violations = len(overloaded_xfmr_list)
        prev_num_line_violations = len(overloaded_line_list)
        line_loading_df = get_all_line_info(
            compute_loading=True,
            upper_limit=thermal_config["line_upper_limit"],
            ignore_switch=ignore_switch,
        )
        overloaded_line_list = list(
            line_loading_df.loc[line_loading_df["status"] == "overloaded"][
                "name"
            ].unique()
        )
        logger.info("Determined line loadings.")
        logger.info(f"Number of line violations: {len(overloaded_line_list)}")

        if len(overloaded_line_list) > prev_num_line_violations:
            logger.debug(overloaded_line_list)
            logger.info("Write upgrades till this step in debug_upgrades.dss")
            # self.write_dat_file(output_path=os.path.join(self.config["Outputs"], "debug_upgrades.dss"))
            raise Exception(
                f"Line violations increased from {prev_num_line_violations} to {len(overloaded_line_list)} "
                f"during upgrade process"
            )
        if len(overloaded_line_list) > 0:
            line_commands_list, temp_line_upgrades_df = correct_line_violations(
                line_loading_df=line_loading_df,
                line_design_pu=thermal_config["line_design_pu"],
                line_upgrade_options=line_upgrade_options,
                parallel_lines_limit=thermal_config["parallel_lines_limit"],
            )
            logger.info("Corrected line violations.")
            commands_list = commands_list + line_commands_list
            line_upgrades_df = line_upgrades_df.append(temp_line_upgrades_df)

        xfmr_loading_df = get_all_transformer_info(
            compute_loading=True, upper_limit=thermal_config["xfmr_upper_limit"]
        )
        overloaded_xfmr_list = list(
            xfmr_loading_df.loc[xfmr_loading_df["status"] == "overloaded"][
                "name"
            ].unique()
        )
        logger.info("Determined xfmr loadings.")
        logger.info(f"Number of xfmr violations: {len(overloaded_xfmr_list)}")
        if len(overloaded_xfmr_list) > prev_num_xfmr_violations:
            logger.info("Write upgrades till this step in debug_upgrades.dss")
            # self.write_dat_file(output_path=os.path.join(self.config["Outputs"], "debug_upgrades.dss"))
            raise Exception(
                f"Xfmr violations increased from {prev_num_xfmr_violations} to {len(overloaded_xfmr_list)} "
                f"during upgrade process"
            )
        if len(overloaded_xfmr_list) > 0:
            xfmr_commands_list, temp_xfmr_upgrades_df = correct_xfmr_violations(
                xfmr_loading_df=xfmr_loading_df,
                xfmr_design_pu=thermal_config["xfmr_design_pu"],
                xfmr_upgrade_options=xfmr_upgrade_options,
                parallel_xfmrs_limit=thermal_config["parallel_xfmrs_limit"]
            )
            logger.info("Corrected xfmr violations.")
            commands_list = commands_list + xfmr_commands_list
            xfmr_upgrades_df = xfmr_upgrades_df.append(temp_xfmr_upgrades_df)

        # compute loading after upgrades
        xfmr_loading_df = get_all_transformer_info(
            compute_loading=True, upper_limit=thermal_config["xfmr_upper_limit"]
        )
        overloaded_xfmr_list = list(
            xfmr_loading_df.loc[xfmr_loading_df["status"] == "overloaded"][
                "name"
            ].unique()
        )
        line_loading_df = get_all_line_info(
            compute_loading=True,
            upper_limit=thermal_config["line_upper_limit"],
            ignore_switch=ignore_switch,
        )
        overloaded_line_list = list(
            line_loading_df.loc[line_loading_df["status"] == "overloaded"][
                "name"
            ].unique()
        )

        num_violations_curr_itr = len(overloaded_xfmr_list) + len(overloaded_line_list)
        logger.info(
            f"Number of devices with violations after iteration {iteration_counter}: {num_violations_curr_itr}"
        )
        iteration_counter += 1
        if iteration_counter > max_upgrade_iteration:
            logger.info("Max iterations limit reached, quitting")
            break

    write_text_file(
        string_list=commands_list, text_file_path=thermal_upgrades_dss_filepath
    )
    reload_dss_circuit(
        dss_file_list=[master_path, thermal_upgrades_dss_filepath],
        commands_list=None,
        **pydss_params,
    )
    xfmr_loading_df = get_all_transformer_info(
        compute_loading=True, upper_limit=thermal_config["xfmr_upper_limit"]
    )
    line_loading_df = get_all_line_info(
        compute_loading=True,
        upper_limit=thermal_config["line_upper_limit"],
        ignore_switch=ignore_switch,
    )
    (
        bus_voltages_df,
        undervoltage_bus_list,
        overvoltage_bus_list,
        buses_with_violations,
    ) = get_bus_voltages(
        upper_limit=voltage_upper_limit, lower_limit=voltage_lower_limit, **pydss_params
    )
    overloaded_xfmr_list = list(
        xfmr_loading_df.loc[xfmr_loading_df["status"] == "overloaded"]["name"].unique()
    )
    overloaded_line_list = list(
        xfmr_loading_df.loc[line_loading_df["status"] == "overloaded"]["name"].unique()
    )

    final_results = UpgradeResultModel(
        name="",
        scenario="",
        stage="Final",
        upgrade_type="Thermal",
        thermal_violations_present=(len(overloaded_xfmr_list) + len(overloaded_line_list)) > 0,
        voltage_violations_present=(len(undervoltage_bus_list) + len(overvoltage_bus_list)) > 0,
        max_voltage_on_any_bus=bus_voltages_df['Max per unit voltage'].max(),
        min_voltage_on_any_bus=bus_voltages_df['Min per unit voltage'].min(),
        num_of_buses_with_voltage_violations=len(undervoltage_bus_list) + len(overvoltage_bus_list),
        num_of_overvoltage_violations_buses_above_voltage_upper_limit=len(overvoltage_bus_list),
        voltage_upper_limit=voltage_upper_limit,
        num_of_undervoltage_violations_buses_below_voltage_lower_limit=len(undervoltage_bus_list),
        voltage_lower_limit=voltage_lower_limit,
        max_line_loading=line_loading_df['max_per_unit_loading'].max(),
        max_xfmr_loading=xfmr_loading_df['max_per_unit_loading'].max(),
        num_of_lines_with_violations_above_line_upper_limit=len(overloaded_line_list),
        line_upper_limit=thermal_config['line_upper_limit'],
        num_of_xfmrs_with_violations_above_xfmr_upper_limit=len(overloaded_xfmr_list),
        xfmr_upper_limit=thermal_config['xfmr_upper_limit'],
    )
    temp_results = dict(final_results)
    # TODO check is this okay to remove keys here.
    # TODO add scenario based on pydss controller
    temp_results.pop("name")
    temp_results.pop("scenario")
    output_results.append(temp_results)
    pd.DataFrame.from_dict(output_results).to_csv(thermal_summary_file, index=False)
    end = time.time()
    logger.info(
        f"Simulation end time: {end}"
    )
    line_upgrades_df.to_csv(output_csv_line_upgrades_filepath)
    xfmr_upgrades_df.to_csv(output_csv_xfmr_upgrades_filepath)
