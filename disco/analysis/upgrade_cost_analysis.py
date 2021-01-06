import logging
import os

import pandas as pd

from jade.utils.utils import load_data

from disco.analysis import Analysis, Input
from disco.exceptions import AnalysisRunException
from disco.utils.custom_type import CustomType
from disco.utils.dss_utils import extract_upgrade_results


logger = logging.getLogger(__name__)


class UpgradeCostAnalysis(Analysis):

    INPUTS = [
        Input("unit_cost_data_file", CustomType(str), "generic_cost_database_v1.xlsx")
    ]

    def run(self, output, *args, **kwargs):
        # unit_cost_data_file
        unit_cost_data_file = self.get_input("unit_cost_data_file").current_value

        # relative job paths
        job_output = os.path.join(output, self._job_name)

        # output_path
        post_process_output = os.path.join(job_output, "post_process")
        os.makedirs(post_process_output, exist_ok=True)

        # upgrade files
        project_path = os.path.join(job_output, "pydss_project")
        upgrade_files = extract_upgrade_results(project_path, file_ext=".json")
        thermal_upgrade_file = upgrade_files["thermal"]
        voltage_upgrade_file = upgrade_files["voltage"]
        try:
            # Cost calculation
            thermal_df = self.get_thermal_costs(
                thermal_upgrade_file, unit_cost_data_file, post_process_output
            )

            metadata = load_data(voltage_upgrade_file)
            vreg_df = self.get_vreg_costs(
                voltage_upgrade_file,
                unit_cost_data_file,
                metadata["feederhead_basekV"],
            )
            cap_df = self.get_cap_costs(voltage_upgrade_file, unit_cost_data_file)

            # Cost summary
            total_costs_df = self.get_total_costs(thermal_df, vreg_df, cap_df)

            # Output CSV file
            summary_of_upgrade_costs_file = os.path.join(
                post_process_output, "summary_of_upgrade_costs.csv"
            )
            total_costs_df.to_csv(summary_of_upgrade_costs_file, index=False)
            # total_costs_df.to_feather(output_path + 'summary_of_upgrade_costs.feather')

            self._add_to_results(
                "summary_of_upgrade_costs", summary_of_upgrade_costs_file
            )

        except AnalysisRunException:
            logger.exception("Unexcepted UpgradeCostAnalysis Error.")
            raise

        finally:
            if os.path.exists(thermal_upgrade_file):
                os.remove(thermal_upgrade_file)
            if os.path.exists(voltage_upgrade_file):
                os.remove(voltage_upgrade_file)

    def indiv_line_cost(self, upgrade_df, unit_cost_lines):
        """Function to calculate costs of upgrading each individual line that is overloaded.
        Returns a dataframe with columns containing the line ID's and cost to upgrade.
        """
        # Dictionary used to convert between different length units and meters, which are used for all the calculations.
        # OpenDSS can output results in any of these lengths.
        len_unit_mult = {
            "mi": 1609.34,
            "kft": 0.00328084,
            "km": 0.001,
            "ft": 3.28084,
            "in": 39.3701,
            "cm": 100,
        }

        line_costs_df = pd.DataFrame()
        for k in upgrade_df.keys():
            # print(k)
            if "Line." in k:
                new_line_len = upgrade_df[k]["new"][1][
                    "length"
                ]  # upgraded lines and new lines run along exisiting circuit, so length is the same for both

                if upgrade_df[k]["new"][0] > 0:
                    # print(k)
                    new_line_len_unit = upgrade_df[k]["new"][1]["length_unit"]
                    if new_line_len_unit == "m":
                        new_line_len_m = new_line_len
                    else:
                        new_line_len_m = new_line_len / len_unit_mult[new_line_len_unit]
                    # print('line length is ',new_line_len, new_line_len_unit, 'or', new_line_len_m, 'm')

                    line_count = upgrade_df[k]["new"][
                        0
                    ]  # count of new lines added to address overload. Often 1, but could be > 1 with severe overloads
                    new_line_cost_per_line = new_line_len_m * float(
                        unit_cost_lines[
                            unit_cost_lines["description"] == "new_line"
                        ].cost_per_m
                    )
                    new_line_cost = line_count * new_line_cost_per_line

                elif upgrade_df[k]["new"][0] == 0:
                    new_line_cost = 0
                    new_line_cost_per_line = 0

                elif upgrade_df[k]["new"][0] < 0:
                    logger.error(
                        "Error: number of new lines is negative: %s",
                        upgrade_df[k]["new"][0],
                    )
                    raise AnalysisRunException(
                        "Error: number of new lines is negative: {}".format(
                            upgrade_df[k]["new"][0]
                        )
                    )

                upgraded_line_count = upgrade_df[k]["upgrade"][0]
                upgraded_line_cost = (
                    new_line_cost_per_line * upgraded_line_count
                )  # TODO: update to take ampacities as an option. X data currently does not have sufficient resolution
                dict_k = {
                    "id": [k],
                    "new_equip_cost": [new_line_cost],
                    "upgraded_equip_cost": [upgraded_line_cost],
                }

                df_k = pd.DataFrame.from_dict(dict_k)
                line_costs_df = line_costs_df.append(df_k)

        return line_costs_df

    def get_xfmr_unit_costs(self, kva, unit_cost_xfmrs):
        unit_cost = unit_cost_xfmrs[unit_cost_xfmrs["rated_kva"] == kva].total_cost

        return unit_cost

    def indiv_xfmr_costs(self, upgrade_df, unit_cost_xfmrs):
        """Function to calculate costs of upgrading each individual transformers that is overloaded.
        Returns a dataframe with columns containing the transformer ID's and cost to upgrade.
        """

        xfmr_costs_df = pd.DataFrame()

        rated_kva_list = [float(x) for x in unit_cost_xfmrs["rated_kva"]]

        for k in upgrade_df.keys():
            if "Transformer." in k:
                if (
                    upgrade_df[k]["new"][0] > 0
                ):  # TODO: make functions for getting new equipment and upgraded equipment costs to make cleaner
                    # print(k)
                    new_xfmr_kva = upgrade_df[k]["new"][1]["wdg_kvas"][
                        0
                    ]  # TODO: decide how to handle oh vs ug for GEM
                    new_xfmr_count = upgrade_df[k]["new"][
                        0
                    ]  # count of new transformers added to address overload.

                    if new_xfmr_kva > 5000:  # TODO: update later?
                        new_unit_cost = unit_cost_xfmrs[
                            unit_cost_xfmrs["system"] == "substation"
                        ].install_cost
                    elif not (new_xfmr_kva in rated_kva_list):
                        closest_kva = min(
                            unit_cost_xfmrs["rated_kva"],
                            key=lambda x: abs(x - new_xfmr_kva),
                        )
                        new_unit_cost = unit_cost_xfmrs[
                            unit_cost_xfmrs["rated_kva"] == closest_kva
                        ].install_cost
                    else:
                        new_unit_cost = unit_cost_xfmrs[
                            unit_cost_xfmrs["rated_kva"] == new_xfmr_kva
                        ].install_cost

                    # print(k)
                    # print('new unit cost is:', new_unit_cost)
                    # print('new_xfmr_count is:', new_xfmr_count)
                    # print('new_xfmr_kva is:',new_xfmr_kva)
                    new_xfmr_cost = new_unit_cost * new_xfmr_count
                    new_xfmr_cost = new_xfmr_cost.iloc[0]

                elif upgrade_df[k]["new"][0] == 0:
                    new_xfmr_cost = 0

                elif upgrade_df[k]["new"][0] < 0:
                    logger.exception(
                        "Error: number of new transformers is negative: %s",
                        upgrade_df[k]["new"][0],
                    )
                    raise AnalysisRunException(
                        "Error: number of new transformers is negative: {}".format(
                            upgrade_df[k]["new"][0]
                        )
                    )

                if upgrade_df[k]["upgrade"][0] > 0:
                    # print(upgrade_df[k]['upgrade'][1][0]['kva'][0])

                    upgrade_xfmr_kva = float(upgrade_df[k]["upgrade"][1][0]["kva"][0])
                    upgrade_xfmr_count = upgrade_df[k]["upgrade"][0]

                    if upgrade_xfmr_kva > 5000:  # TODO: update later?
                        upgrade_xfmr_unit_cost = (
                            unit_cost_xfmrs[
                                unit_cost_xfmrs["system"] == "substation"
                            ].install_cost
                            + unit_cost_xfmrs[
                                unit_cost_xfmrs["system"] == "substation"
                            ].remove_cost
                        )
                    elif not (upgrade_xfmr_kva in rated_kva_list):
                        closest_kva = min(
                            unit_cost_xfmrs["rated_kva"],
                            key=lambda x: abs(x - upgrade_xfmr_kva),
                        )
                        upgrade_xfmr_unit_cost = (
                            unit_cost_xfmrs[
                                unit_cost_xfmrs["rated_kva"] == closest_kva
                            ].install_cost
                            + unit_cost_xfmrs[
                                unit_cost_xfmrs["rated_kva"] == closest_kva
                            ].remove_cost
                        )
                    else:
                        upgrade_xfmr_unit_cost = (
                            unit_cost_xfmrs[
                                unit_cost_xfmrs["rated_kva"] == upgrade_xfmr_kva
                            ].install_cost
                            + unit_cost_xfmrs[
                                unit_cost_xfmrs["rated_kva"] == upgrade_xfmr_kva
                            ].remove_cost
                        )
                    upgrade_xfmr_cost = upgrade_xfmr_unit_cost * upgrade_xfmr_count
                    upgrade_xfmr_cost = upgrade_xfmr_cost.iloc[0]

                elif upgrade_df[k]["upgrade"][0] == 0:
                    upgrade_xfmr_cost = 0

                elif upgrade_df[k]["upgrade"][0] < 0:
                    logger.error(
                        "Error: number of upgraded transformers is negative: %s",
                        upgrade_df[k]["upgrade"][0],
                    )
                    raise AnalysisRunException(
                        "Error: number of upgraded transformers is negative: {}".format(
                            upgrade_df[k]["upgrade"][0]
                        )
                    )

                else:
                    upgrade_xfmr_cost = None
                    logger.warning(
                        "Warning: unintentified error. Assigning upgrade_xfmr_cost to None"
                    )

                # print(k)

                dict_k = {
                    "id": [k],
                    "new_equip_cost": [new_xfmr_cost],
                    "upgraded_equip_cost": [upgrade_xfmr_cost],
                }
                df_k = pd.DataFrame.from_dict(dict_k)
                xfmr_costs_df = xfmr_costs_df.append(df_k)

        return xfmr_costs_df

    def get_cap_costs(self, upgrade_file, unit_cost_data_file):
        """
        note we currently are never adding new capacitors to integrate PV. We may want these to
        accomodate new load or EVs. Right now only cap changes are new controllers or control
        setting changes
        """
        # pd.read_json() works if the data looks like {'a': [1,2], 'b': [3,4]}, as the values are indexed.
        # But would fail if just scalar value, like {'a':1, 'b':2}, in this case use typ="series".
        try:
            upgrade_df = pd.read_json(upgrade_file)
        except ValueError:
            upgrade_df = pd.read_json(upgrade_file, typ="series").to_frame("Value")

        if upgrade_df.empty:
            cap_dict = {
                "type": ["new capacitor controller", "capacitor setting changes"],
                "count": [0, 0],
                "total_cost_usd": [0, 0],
            }
            cap_cost_df = pd.DataFrame.from_dict(cap_dict)
            return cap_cost_df

        cap_cols = upgrade_df.columns.str.contains("Capacitor")
        cap_df = upgrade_df[upgrade_df.columns[cap_cols]]

        if cap_df.empty:
            cap_dict = {
                "type": ["new capacitor controller", "capacitor setting changes"],
                "count": [0, 0],
                "total_cost_usd": [0, 0],
            }
            cap_cost_df = pd.DataFrame.from_dict(cap_dict)
            return cap_cost_df

        count_new_cap_controllers = cap_df.loc["New controller added"].sum()
        count_changed_settings = cap_df.loc["Controller settings modified"].sum()

        unit_costs_controls = pd.read_excel(
            unit_cost_data_file, sheet_name="control_changes"
        )
        unit_costs_controls.set_index("type", inplace=True)

        new_controller_unit_cost = unit_costs_controls.loc[
            "replace capacitor controller"
        ].total_cost
        new_setting_unit_cost = unit_costs_controls.loc[
            "voltage regulator or capacitor setting change"
        ].total_cost

        total_new_controller_cost = new_controller_unit_cost * count_new_cap_controllers
        total_new_setting_cost = new_setting_unit_cost * count_changed_settings

        cap_dict = {
            "type": ["new capacitor controller", "capacitor setting changes"],
            "count": [count_new_cap_controllers, count_changed_settings],
            "total_cost_usd": [total_new_controller_cost, total_new_setting_cost],
        }

        cap_cost_df = pd.DataFrame.from_dict(cap_dict)

        return cap_cost_df

    def get_vreg_costs(self, upgrade_file, unit_cost_data_file, voltage_class):
        try:
            upgrade_df = pd.read_json(upgrade_file)
        except ValueError:
            upgrade_df = pd.read_json(upgrade_file, typ="series").to_frame("Value")

        if upgrade_df.empty:
            vreg_dict = {
                "type": [
                    "new substation LTC",
                    "substation LTC setting change",
                    "new line regulators",
                    "replace line regulator controller",
                    "line regulator control setting change",
                ],
                "count": [0, 0, 0, 0, 0],
                "total_cost_usd": [0, 0, 0, 0, 0],
            }
            vreg_cost_df = pd.DataFrame.from_dict(vreg_dict)
            return vreg_cost_df

        vreg_cols = upgrade_df.columns.str.contains("Regctrl")
        vreg_df = upgrade_df[upgrade_df.columns[vreg_cols]]

        if vreg_df.empty:
            vreg_dict = {
                "type": [
                    "new substation LTC",
                    "substation LTC setting change",
                    "new line regulators",
                    "replace line regulator controller",
                    "line regulator control setting change",
                ],
                "count": [0, 0, 0, 0, 0],
                "total_cost_usd": [0, 0, 0, 0, 0],
            }
            vreg_cost_df = pd.DataFrame.from_dict(vreg_dict)
            return vreg_cost_df

        count_new_sub_LTCs = (
            (vreg_df.loc["New transformer added"] == 1)
            & (vreg_df.loc["Substation LTC"] == 1)
        ).sum()

        count_sub_LTC_setting_change = (
            (vreg_df.loc["Controller settings modified"] == 1)
            & (vreg_df.loc["New controller added"] == 0)
            & (vreg_df.loc["Substation LTC"] == 1)
        ).sum()
        # TODO: Check this is correct. I'm assuming all substations have transformers, and this condition
        # just means that a new LTC is added to the substation transformer, not that the whole
        # transformer is replaced.

        count_new_line_regs = (
            (vreg_df.loc["New transformer added"] == 1)
            & (vreg_df.loc["Substation LTC"] == 0)
        ).sum()

        count_new_line_reg_controllers = (
            (vreg_df.loc["New transformer added"] == 0)
            & (vreg_df.loc["New controller added"] == 1)
            & (vreg_df.loc["Substation LTC"] == 0)
        ).sum()

        count_line_reg_setting_changes = (
            (vreg_df.loc["Controller settings modified"] == 1)
            & (vreg_df.loc["New controller added"] == 0)
            & (vreg_df.loc["Substation LTC"] == 0)
        ).sum()

        unit_costs_controls = pd.read_excel(
            unit_cost_data_file, sheet_name="control_changes"
        )
        unit_costs_vreg = pd.read_excel(
            unit_cost_data_file, sheet_name="voltage_regulators"
        )
        unit_costs_controls.set_index("type", inplace=True)
        unit_costs_vreg.set_index("type", inplace=True)

        new_sub_LTC_unit_cost = unit_costs_controls.loc[
            "LTC control replacement"
        ].total_cost
        sub_LTC_settings_change_unit_cost = unit_costs_controls.loc[
            "LTC setpoint change"
        ].total_cost
        new_line_reg_unit_cost = (
            unit_costs_vreg[unit_costs_vreg.voltage_class_kV == voltage_class]
            .loc["new voltage regulator"]
            .total_cost
        )
        new_controller_unit_cost = unit_costs_controls.loc[
            "replace voltage regulator controller"
        ].total_cost
        line_reg_new_setting_unit_cost = unit_costs_controls.loc[
            "voltage regulator or capacitor setting change"
        ].total_cost

        total_new_sub_LTC_costs = count_new_sub_LTCs * new_sub_LTC_unit_cost
        total_sub_LTC_setting_change_costs = (
            count_sub_LTC_setting_change * sub_LTC_settings_change_unit_cost
        )
        total_new_line_reg_costs = count_new_line_regs * new_line_reg_unit_cost
        total_new_line_reg_controller_costs = (
            count_new_line_reg_controllers * new_controller_unit_cost
        )
        total_line_reg_setting_change_costs = (
            count_line_reg_setting_changes * line_reg_new_setting_unit_cost
        )

        vreg_dict = {
            "type": [
                "new substation LTC",
                "substation LTC setting change",
                "new line regulators",
                "replace line regulator controller",
                "line regulator control setting change",
            ],
            "count": [
                count_new_sub_LTCs,
                count_sub_LTC_setting_change,
                count_new_line_regs,
                count_new_line_reg_controllers,
                count_line_reg_setting_changes,
            ],
            "total_cost_usd": [
                total_new_sub_LTC_costs,
                total_sub_LTC_setting_change_costs,
                total_new_line_reg_costs,
                total_new_line_reg_controller_costs,
                total_line_reg_setting_change_costs,
            ],
        }

        vreg_cost_df = pd.DataFrame.from_dict(vreg_dict)

        return vreg_cost_df

    def total_thermal_cost(self, costs_df):  # applies to lines and transformers
        """ Sums the cost of all line upgrades to get the total line upgrade cost in $,
        which is returned as an int.
        """
        if costs_df.empty:
            total_cost = 0
        else:
            total_cost = (
                costs_df["new_equip_cost"].sum() + costs_df["upgraded_equip_cost"].sum()
            )

        # add reconductored line costs
        return total_cost

    def get_thermal_costs(
        self, upgrade_file, unit_cost_data_file, output_path
    ):  # Is for one penetration level/on upgrade file at a time. Upgrade_file is a json file.
        unit_cost_lines = pd.read_excel(
            unit_cost_data_file, sheet_name="lines"
        )  # may want to update path to the unit cost database
        unit_cost_xfmrs = pd.read_excel(
            unit_cost_data_file, sheet_name="transformers"
        )  # may want to update path to the unit cost database
        # no circuit conversion included for now

        try:
            upgrade_df = pd.read_json(upgrade_file)  # merge in two upgrade files
        except ValueError:
            upgrade_df = pd.read_json(upgrade_file, typ="series").to_frame("Value")

        if upgrade_df.empty:
            total_upgrade_dict = {
                "type": ["lines", "transformers"],
                "count": [0, 0],
                "total_cost_usd": [0, 0],
            }
            thermal_df = pd.DataFrame.from_dict(total_upgrade_dict)
            return thermal_df

        line_costs_df = self.indiv_line_cost(upgrade_df, unit_cost_lines)
        line_costs_df.reset_index(inplace=True, drop=True)
        # output the detailed data on line costs

        # Output CSV file
        detailed_line_upgrade_costs_file = os.path.join(
            output_path, "detailed_line_upgrade_costs.csv"
        )
        line_costs_df.to_csv(detailed_line_upgrade_costs_file)
        # line_costs_df.to_feather(output_path + 'detailed_line_upgrade_costs.feather')
        self._add_to_results(
            "detailed_line_upgrade_costs", detailed_line_upgrade_costs_file
        )

        xfmr_costs_df = self.indiv_xfmr_costs(upgrade_df, unit_cost_xfmrs)
        xfmr_costs_df.reset_index(inplace=True, drop=True)

        # Output the detailed data on transformer costs
        detailed_transformer_costs_file = os.path.join(
            output_path, "detailed_transformer_costs.csv"
        )
        xfmr_costs_df.to_csv(detailed_transformer_costs_file)
        # xfmr_costs_df.to_feather(output_path + 'detailed_transformer_costs.feather')
        self._add_to_results(
            "detailed_transformer_costs", detailed_transformer_costs_file
        )

        total_line_cost = self.total_thermal_cost(line_costs_df)
        total_xfmr_cost = self.total_thermal_cost(xfmr_costs_df)

        upgrade_list = ["lines", "transformers"]
        total_cost_list = [total_line_cost, total_xfmr_cost]

        total_upgrade_dict = {
            "type": upgrade_list,
            "count": [len(line_costs_df), len(xfmr_costs_df)],
            "total_cost_usd": total_cost_list,
        }

        thermal_df = pd.DataFrame.from_dict(total_upgrade_dict)

        return thermal_df

    def get_total_costs(self, thermal_df, vreg_df, cap_df):
        total_costs_df = pd.concat([thermal_df, vreg_df, cap_df])
        if total_costs_df.empty:
            total_costs_df = pd.DataFrame(
                [["total", 0, 0]], columns=["type", "count", "total_cost_usd"]
            )
            return total_costs_df

        all_upgrade_costs = total_costs_df["total_cost_usd"].sum()
        all_upgrade_count = total_costs_df["count"].sum()

        totals_row_df = pd.DataFrame(
            [["total", all_upgrade_count, all_upgrade_costs]],
            columns=["type", "count", "total_cost_usd"],
        )
        total_costs_df = total_costs_df.append(totals_row_df)

        return total_costs_df
