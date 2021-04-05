"""Defines Snapshot Impact Analysis object."""

import os
import logging
import math
import re

import numpy as np
from pandas import DataFrame

from jade.common import JOBS_OUTPUT_DIR
from jade.jobs.results_aggregator import ResultsAggregator
from jade.utils.timing_utils import track_timing, TimerStatsCollector, Timer
from jade.utils.utils import dump_data

from PyDSS.pydss_results import PyDssResults, PyDssScenarioResults
from disco.analysis import Analysis, Input
from disco.exceptions import AnalysisRunException
from disco.extensions.pydss_simulation.pydss_configuration import PyDssConfiguration
from disco.utils.custom_type import CustomType


logger = logging.getLogger(__name__)


# TODO: remove once we have debugged the performance issues
TIMER_STATS = TimerStatsCollector()


class SnapshotImpactAnalysis(Analysis):
    """Snapshot impact analysis class with default values"""
    # Values are overridden by impact_analysis_inputs.toml in our workflow.
    INPUTS = [
        Input('over_voltage', CustomType(float), 1.05),
        Input('under_voltage', CustomType(float), 0.95),
        Input('over_voltage_conservative', CustomType(float), 1.05833),
        Input('under_voltage_conservative', CustomType(float), 0.91667),
        Input('line_overload_1', CustomType('percent'), 100),
        Input('line_overload_2', CustomType('percent'), 150),
        Input('transformer_overload_1', CustomType('percent'), 100),
        Input('transformer_overload_2', CustomType('percent'), 150),
    ]

    def __init__(self, feeder, *args, **kwargs):
        self._include_voltage_deviation = False
        super(SnapshotImpactAnalysis, self).__init__(*args, **kwargs)
        self._feeder = feeder
        TIMER_STATS.clear()

    def run(self, output, **kwargs):
        """Run snapshot impact analysis

        Parameters
        ----------
        output : directory containing job outputs

        """
        base_config = os.path.join(output, 'config.json')
        config = PyDssConfiguration.deserialize(base_config)
        results = ResultsAggregator.list_results(output)
        result_lookup = {x.name: x for x in results}
        jobs_output = os.path.join(output, JOBS_OUTPUT_DIR)

        for job in config.iter_feeder_jobs(self._feeder):
            if result_lookup[job.name].return_code != 0:
                logger.info("Skip failed job %s", job.name)
                continue
            self._run_job(config, job, jobs_output)

        TIMER_STATS.log_stats(clear=True)

    @track_timing(TIMER_STATS)
    def _run_job(self, config, job, output):
        simulation = config.create_from_result(job, output)
        results = PyDssResults(simulation.pydss_project_path)
        scenario = results.scenarios[0]

        # get base scenario, if there is one
        base_scenario = None
        self._include_voltage_deviation = job.model.include_voltage_deviation

        if self._include_voltage_deviation:
            base_case = job.model.base_case

            if base_case is None:
                # TODO: ideally, these should bubble upwards and be caught and logged
                # in one place (job-run)
                logger.error(
                    "Error: include-voltage-deviation flag enabled with no base case given: %s",
                    job.name
                )
                raise AnalysisRunException(
                    "Error: include-voltage-deviation flag enabled with no base case given: {}".format(
                        job.name,
                    )
                )

            if base_case != self._job_name:
                base_job = config.get_feeder_job(job.model.deployment.feeder, base_case)
                base_simulation = config.create_from_result(base_job, output)
                base_results = PyDssResults(base_simulation.pydss_project_path)
                base_scenario = base_results.scenarios[0]

        voltage_violations = self._run_voltage_violations(scenario, base_scenario)
        line_loading = self._run_line_loading(scenario)
        transformer_loading = self._run_transformer_loading(scenario)

        results = self._get_violations_for_job(job, voltage_violations, line_loading,
                                               transformer_loading)

        self._add_to_results('violations', results)

        # output to csv
        result_df = DataFrame(columns=results.keys())
        result_df.loc[0] = results

        filename = os.path.join(
            output,
            job.name,
            "snapshot-impact-analysis-job-post-process.csv",
        )

        result_df.to_csv(filename, index=False)

        try:
            data = scenario.read_feeder_head_info()
            filename = os.path.join(output, job.name, "FeederHeadInfo.json")
            dump_data(data, filename)
        except Exception:
            # This is expected if the version of PyDSS is wrong.
            logger.exception("read_feeder_head_info failed")
            raise

    @track_timing(TIMER_STATS)
    def _run_voltage_violations(self, scenario, base_scenario):
        """Run voltage violations from hosting capacity analysis

        Parameters
        ----------
        scenario : ValuesByPropertyAcrossElementsResults

        """
        # just one terminal, all phases
        bus_voltages = self._normalize_dataframe_values(scenario, 'Buses', 'puVmagAngle', 1,
                                                        mag_ang='mag')
        vmin, vmax, uv1, ov1, uv_count1, ov_count1, uv2, ov2, uv_count2, ov_count2 = \
            _check_voltage_violations(
                # TODO dynamically grab all phases, 1 terminal
                bus_voltages['Value'],
                self.get_input('over_voltage').current_value,
                self.get_input('under_voltage').current_value,
                self.get_input('over_voltage_conservative').current_value,
                self.get_input('under_voltage_conservative').current_value
            )

        total_pv_kw = None
        total_pv_pmpp = None
        total_load_kw = _get_total_load_kw(scenario.read_element_info_file('Loads'))
        pv_to_load_ratio = None

        if 'PVSystems' in scenario.list_element_classes():
            total_pv_kw = _get_total_pv_kw(scenario.read_element_info_file('PVSystems'))
            total_pv_pmpp = _get_total_pv_pmpp(scenario.get_full_dataframe('PVSystems', 'Pmpp'))
            pv_to_load_ratio = round(100 * total_pv_pmpp / max(0.00001, total_load_kw), 2)

        self.VIOLATION_FLAG_NAMES = {
            'uv1_flag': 'undervoltage_flag(limit={})'.format(self.get_input('under_voltage').current_value),
            'ov1_flag': 'overvoltage_flag(limit={})'.format(self.get_input('over_voltage').current_value),
            'uv2_flag': 'undervoltage_flag(limit={})'.format(self.get_input('under_voltage_conservative').current_value),
            'ov2_flag': 'overvoltage_flag(limit={})'.format(self.get_input('over_voltage_conservative').current_value),
            'lo1_flag': 'line_overloading_flag(limit={})'.format(self.get_input('line_overload_1').current_value),
            'lo2_flag': 'line_overloading_flag(limit={})'.format(self.get_input('line_overload_2').current_value),
            'to1_flag': 'xfmr_overloading_flag(limit={})'.format(self.get_input('transformer_overload_1').current_value),
            'to2_flag': 'xfmr_overloading_flag(limit={})'.format(self.get_input('transformer_overload_2').current_value),
        }

        self.VIOLATION_COUNT_NAMES = {
            'uv1_count': 'undervoltage_count(limit={})'.format(self.get_input('under_voltage').current_value),
            'uv2_count': 'undervoltage_count(limit={})'.format(self.get_input('under_voltage_conservative').current_value),
            'ov1_count': 'overvoltage_count(limit={})'.format(self.get_input('over_voltage').current_value),
            'ov2_count': 'overvoltage_count(limit={})'.format(self.get_input('over_voltage_conservative').current_value),
            'lo1_count': 'line_overloading_count(limit={})'.format(self.get_input('line_overload_1').current_value),
            'lo2_count': 'line_overloading_count(limit={})'.format(self.get_input('line_overload_2').current_value),
            'to1_count': 'xfmr_overloading_count(limit={})'.format(self.get_input('transformer_overload_1').current_value),
            'to2_count': 'xfmr_overloading_count(limit={})'.format(self.get_input('transformer_overload_2').current_value),
        }

        violations = {
            'pv_kw': total_pv_kw,
            'pv_pmpp': total_pv_pmpp,
            'peak_load': total_load_kw,
            'pv_to_load_ratio': pv_to_load_ratio,
            'min_voltage': vmin,
            'max_voltage': vmax,
            self.VIOLATION_FLAG_NAMES['uv1_flag']: uv1,
            self.VIOLATION_FLAG_NAMES['ov1_flag']: ov1,
            self.VIOLATION_FLAG_NAMES['uv2_flag']: uv2,
            self.VIOLATION_FLAG_NAMES['ov2_flag']: ov2,
            self.VIOLATION_COUNT_NAMES['uv1_count']: uv_count1,
            self.VIOLATION_COUNT_NAMES['ov1_count']: ov_count1,
            self.VIOLATION_COUNT_NAMES['uv2_count']: uv_count2,
            self.VIOLATION_COUNT_NAMES['ov2_count']: ov_count2,
        }

        # ensure that deviation indices are set (base scenarios)
        if self._include_voltage_deviation:
            violations['max_voltage_deviation'] = None
            violations['voltage_deviation_flag'] = None
            violations['voltage_deviation_count'] = None

        if base_scenario is not None:
            # TODO: If this will be used then we need to only get this once.
            base_voltages = self._normalize_dataframe_values(base_scenario, 'Buses', 'puVmagAngle',
                                                             1, mag_ang='mag')
            voltage_deviation, voltage_deviation_flag, voltage_deviation_count = _compare_voltages(
                base_voltages['Value'],
                bus_voltages['Value']
            )

            violations['max_voltage_deviation'] = voltage_deviation
            violations['voltage_deviation_flag'] = voltage_deviation_flag
            violations['voltage_deviation_count'] = voltage_deviation_count

        return violations

    @track_timing(TIMER_STATS)
    def _run_line_loading(self, scenario):
        """Run line loading from hosting capacity analysis

        Parameters
        ----------
        scenario : ValuesByPropertyAcrossElementsResults

        """
        # just one terminal, all phases

        lines_currents_dataframe = self._normalize_dataframe_values(scenario, "Lines", "Currents",
                                                                    1, convert=True)

        _, max_line_loading, lo1, lv_count1, lo2, lv_count2 = \
            _get_line_loading(
                lines_currents_dataframe,
                scenario.get_full_dataframe("Lines", "NormalAmps"),
                self._job_name,
                self.get_input('line_overload_1').current_value,
                self.get_input('line_overload_2').current_value
            )
        line_loading = {
            # 'line_loadings': line_loadings,
            'max_line_loading': max_line_loading,
            self.VIOLATION_FLAG_NAMES['lo1_flag']: lo1,
            self.VIOLATION_FLAG_NAMES['lo2_flag']: lo2,
            self.VIOLATION_COUNT_NAMES['lo1_count']: lv_count1,
            self.VIOLATION_COUNT_NAMES['lo2_count']: lv_count2,
        }

        return line_loading

    @track_timing(TIMER_STATS)
    def _run_transformer_loading(self, scenario):
        """Run transformer from hosting capacity analysis

        Parameters
        ----------
        scenario : ValuesByPropertyAcrossElementsResults

        """
        transformers_df = scenario.read_element_info_file("Transformers")
        transformers_phase_info_df = scenario.read_element_info_file("TransformersPhase")
        transformers_currents_df = self._normalize_dataframe_values(scenario, "Transformers",
                                                                    "Currents", 1, convert=True)
        transformers_normal_amps_df = scenario.get_full_dataframe("Transformers", "NormalAmps")

        _, max_xfmr_loading, to1, tv_count1, to2, tv_count2 = \
            _get_transformer_loading(
                transformers_df,
                transformers_phase_info_df,
                transformers_currents_df,
                transformers_normal_amps_df,
                self.get_input('transformer_overload_1').current_value,
                self.get_input('transformer_overload_2').current_value
            )

        transformer_loading = {
            # 'xfmr_loading_s': xfmr_loading_s,
            'max_xfmr_loading': max_xfmr_loading,
            self.VIOLATION_FLAG_NAMES['to1_flag']: to1,
            self.VIOLATION_FLAG_NAMES['to2_flag']: to2,
            self.VIOLATION_COUNT_NAMES['to1_count']: tv_count1,
            self.VIOLATION_COUNT_NAMES['to2_count']: tv_count2,
        }

        return transformer_loading

    @track_timing(TIMER_STATS)
    def _normalize_dataframe_values(self, scenario, class_name, property_name, terminal=None,
                                    convert=False, **kwargs):
        """Normalize dataframe columns to row values

        Parameters
        ----------
        scenario : ValuesByPropertyAcrossElementsResults
        class_name : str
        property_name : str
        terminal : int
        convert : bool
            (optional) convert values to Magnitude
        **kwargs : dict
            any extra named parameters (mag_ang, etc) to be passed to get_full_dataframe

        Returns
        -------
        results_dataframe : DataFrame

        """
        results_list = list()
        phase_terminal = None
        if terminal is not None:
            phase_terminal = re.compile(rf"[ABCN]{terminal}")

        df = scenario.get_full_dataframe(class_name, property_name, phase_terminal=phase_terminal,
                                         **kwargs)
        for column in df.columns:
            name = PyDssScenarioResults.get_name_from_column(column)
            value = df[column].values.item()
            result = {'Name': name, 'PhaseTerminal': column, 'Value': value}

            if convert:
                complex_number = complex(value)
                result['Value'] = math.sqrt(complex_number.real**2 + complex_number.imag**2)

            results_list.append(result)

        columns = ['Name', 'PhaseTerminal', 'Value']
        return DataFrame(results_list, columns=columns)

    @track_timing(TIMER_STATS)
    def _get_violations_for_job(self, job, voltage, line, transformer):
        """Returns results expected in output csv file

        Parameters
        ----------
        job : Job
        voltage : dict
            voltage violations
        line : dict
            line load
        transformer : dict
            transformer load

        Returns
        ------
        dict

        """
        result = {}

        project_data = job.model.deployment.project_data

        # Job Information
        result['feeder'] = job.model.deployment.feeder
        result['deployment'] = job.model.deployment.deployment_file
        result['placement'] = project_data.get("placement")
        result['sample'] = project_data.get("sample")
        result['penetration'] = project_data.get("penetration")

        # Voltage Violations
        result.update(voltage)

        # Line Loading
        result.update(line)

        # Transformer Loading
        result.update(transformer)

        self.VIOLATION_COMBINATIONS = {
            '{}L_{}T_{}OV_{}UV_pass_flag'.format(
                self.get_input('line_overload_1').current_value,
                self.get_input('transformer_overload_1').current_value,
                self.get_input('over_voltage').current_value,
                self.get_input('under_voltage').current_value,
               ): ['to1_flag', 'lo1_flag', 'uv1_flag', 'ov1_flag'],

            '{}L_{}T_{}OV_{}UV_pass_flag'.format(
                self.get_input('line_overload_2').current_value,
                self.get_input('transformer_overload_1').current_value,
                self.get_input('over_voltage').current_value,
                self.get_input('under_voltage').current_value,
            ): ['to2_flag', 'lo1_flag', 'uv1_flag', 'ov1_flag'],

            '{}L_{}T_{}OV_{}UV_pass_flag'.format(
                self.get_input('line_overload_1').current_value,
                self.get_input('transformer_overload_2').current_value,
                self.get_input('over_voltage').current_value,
                self.get_input('under_voltage').current_value,
            ): ['to1_flag', 'lo2_flag', 'uv1_flag', 'ov1_flag'],

            '{}L_{}T_{}OV_{}UV_pass_flag'.format(
                self.get_input('line_overload_2').current_value,
                self.get_input('transformer_overload_2').current_value,
                self.get_input('over_voltage').current_value,
                self.get_input('under_voltage').current_value,
            ): ['to2_flag', 'lo2_flag', 'uv1_flag', 'ov1_flag'],

            '{}L_{}T_{}OV_{}UV_pass_flag'.format(
                self.get_input('line_overload_1').current_value,
                self.get_input('transformer_overload_1').current_value,
                self.get_input('over_voltage_conservative').current_value,
                self.get_input('under_voltage_conservative').current_value,
            ): ['to1_flag', 'lo1_flag', 'uv2_flag', 'ov2_flag'],

            '{}L_{}T_{}OV_{}UV_pass_flag'.format(
                self.get_input('line_overload_2').current_value,
                self.get_input('transformer_overload_1').current_value,
                self.get_input('over_voltage_conservative').current_value,
                self.get_input('under_voltage_conservative').current_value,
            ): ['to2_flag', 'lo1_flag', 'uv2_flag', 'ov2_flag'],

            '{}L_{}T_{}OV_{}UV_pass_flag'.format(
                self.get_input('line_overload_1').current_value,
                self.get_input('transformer_overload_2').current_value,
                self.get_input('over_voltage_conservative').current_value,
                self.get_input('under_voltage_conservative').current_value,
            ): ['to1_flag', 'lo2_flag', 'uv2_flag', 'ov2_flag'],

            '{}L_{}T_{}OV_{}UV_pass_flag'.format(
                self.get_input('line_overload_2').current_value,
                self.get_input('transformer_overload_2').current_value,
                self.get_input('over_voltage_conservative').current_value,
                self.get_input('under_voltage_conservative').current_value,
            ): ['to2_flag', 'lo2_flag', 'uv2_flag', 'ov2_flag'],
        }

        # iterate through the combination flags to determine status
        for key, value in self.VIOLATION_COMBINATIONS.items():
            result[key] = not _check_violation_flags(transformer, line, voltage,
                                                     self.VIOLATION_FLAG_NAMES[value[0]],
                                                     self.VIOLATION_FLAG_NAMES[value[1]],
                                                     self.VIOLATION_FLAG_NAMES[value[2]],
                                                     self.VIOLATION_FLAG_NAMES[value[3]],
                                                     )

        return result


# TODO: refactor to take in the scenario here instead of remaking it in analysis.py
@track_timing(TIMER_STATS)
def _check_voltage_violations(bus_voltages, ub1=1.05, lb1=0.95, ub2=1.05833, lb2=0.91667):
    vmax = max(bus_voltages)
    vmin = min(bus_voltages)
    uv_count1 = len([v for v in bus_voltages if v < lb1])
    ov_count1 = len([v for v in bus_voltages if v > ub1])
    uv_count2 = len([v for v in bus_voltages if v < lb2])
    ov_count2 = len([v for v in bus_voltages if v > ub2])

    ov1 = vmax > ub1
    uv1 = vmin < lb1
    ov2 = vmax > ub2
    uv2 = vmin < lb2

    return vmin, vmax, uv1, ov1, uv_count1, ov_count1, uv2, ov2, uv_count2, ov_count2


# TODO: refactor to take in the scenario here instead of remaking it in analysis.py
@track_timing(TIMER_STATS)
def _get_line_loading(line_currents_df, line_normalamps_df, deployment_name, ub1=1.0, ub2=1.5):
    line_loadings = {}
    lv_count1 = 0
    lv_count2 = 0

    # loop through unique line names
    for line in line_currents_df.Name.unique():
        current_mag = []
        # filter out only results with current line name
        line_currents = line_currents_df.query(f"Name == '{line}'")
        nphases = int(len(line_currents))
        # loop through line's magnitudes
        for _, magnitude in line_currents.iterrows():
            current_mag.append(magnitude['Value'] / line_normalamps_df.iloc[0][f"{line}__NormalAmps"])

        # TODO Kwami: how can this be empty?
        # deployment_name is only being passed in to debug this problem.
        if not current_mag:
            line_loadings[line] = 0.0
            logger.error("current_mag was empty, set line_loadings=0.0 "
                         "nphases=%s lencolumns=%s deployment_name=%s line=%s",
                         nphases, len(line_currents_df.keys()), deployment_name, line)
        else:
            line_loadings[line] = max(current_mag)
            if max(current_mag) > ub1:
                lv_count1 += 1
            if max(current_mag) > ub2:
                lv_count2 += 1

    max_line_loading = max(list(line_loadings.values()))
    lo1 = max_line_loading > ub1
    lo2 = max_line_loading > ub2

    return line_loadings, max_line_loading, lo1, lv_count1, lo2, lv_count2


# TODO: refactor to take in the scenario here instead of remaking it in analysis.py
@track_timing(TIMER_STATS)
def _get_transformer_loading(transformer_dataframe, highside_phase_conn_dataframe,
                            transformer_currents_dataframe, transformer_normalamps_dataframe,
                            ub1=1.0, ub2=1.5):
    xfmr_loading_s = {}
    tv_count1 = 0
    tv_count2 = 0

    # loop through unique line names
    for xfmr in transformer_currents_dataframe.Name.unique():
        current_mag = []
        transformer_name = xfmr.replace('Transformer.', '')
        # find transformer data in given dataframes
        transformer = transformer_dataframe.query(f"Name == '{transformer_name}'").iloc[0]
        transformer_phase = highside_phase_conn_dataframe.query(f"Transformer == '{xfmr}'").iloc[0]
        transformer_currents = transformer_currents_dataframe.query(f"Name == '{xfmr}'")

        # set variables necessary
        # TODO: really this shouldn't be necessary, since the dataframe will only have
        # the phases needed when passed in
        nwindings = transformer["NumWindings"]
        high_side_connection = transformer_phase["HighSideConnection"]
        num_phases = int(transformer_phase["NumPhases"])
        phase = len(transformer_currents)

        if num_phases == 3 and high_side_connection == "wye":
            phase = 4
        elif num_phases == 3 and high_side_connection == "delta":
            phase = 3

        for _, magnitude in transformer_currents.iterrows():
            normal_amps = transformer_normalamps_dataframe.iloc[0][f"{xfmr}__NormalAmps"]
            current_mag.append(magnitude['Value'] / normal_amps)

        xfmr_loading_s[xfmr] = max(current_mag)
        if max(current_mag) > ub1:
            tv_count1 += 1
        if max(current_mag) > ub2:
            tv_count2 += 1

    max_xfmr_loading = max(list(xfmr_loading_s.values()))
    to1 = max_xfmr_loading > ub1
    to2 = max_xfmr_loading > ub2

    return xfmr_loading_s, max_xfmr_loading, to1, tv_count1, to2, tv_count2


def _compare_voltages(base_voltage_df, voltage_df, limit=0.03):
    voltage_diff = base_voltage_df - voltage_df
    voltage_deviation_magnitude = abs(voltage_diff)
    voltage_deviation_count = len([f for f in voltage_deviation_magnitude if f > limit])
    voltage_deviation = np.max(voltage_deviation_magnitude)
    voltage_deviation_flag = voltage_deviation > limit
    return voltage_deviation, voltage_deviation_flag, voltage_deviation_count


def _get_total_pv_kw(pvsystems_df):
    return sum(pvsystems_df['kW'])


def _get_total_pv_pmpp(pmpp_df):
    return np.sum(pmpp_df.values)


def _get_total_load_kw(loads_df):
    return sum(loads_df['kW'])


def _check_violation_flags(transformer, line, voltage,
                           transformer_flag, line_flag, voltage_flag_1, voltage_flag_2):
    """Private helper function for getting pass flags

    Parameters
    ----------
    transformer : dict
        transformer load
    line : dict
        line load
    voltage : dict
        voltage violations
    transformer_flag : str
    line_flag : str
    voltage_flag_1 : str
    voltage_flag_2 : str

    Returns
    ------
    bool

    """
    return (transformer[transformer_flag] is not None and transformer[transformer_flag]) | \
           (line[line_flag] is not None and line[line_flag]) | \
           (voltage[voltage_flag_1] is not None and voltage[voltage_flag_1]) | \
           (voltage[voltage_flag_2] is not None and voltage[voltage_flag_2])
