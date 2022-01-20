import os
import logging
from PyDSS.controllers import PvControllerModel

# master_filename = "Master.dss"
# dss_filepath = r"C:\Users\SABRAHAM\Desktop\NREL\current_projects\SETO_distcost\AutomatedUpgrades\case1_2_gc4_os3\x_1\OpenDSS\x_1"
# dss_filepath = r"C:\Users\SABRAHAM\Desktop\NREL\current_projects\SETO_distcost\feeder_models\P10U\scenarios\base_timeseries\opendss\sb2_p10uhs2_1247_trans_51\sb2_p10uhs2_1247_trans_51--p10udt1066"
# dss_filepath = r"C:\Users\SABRAHAM\Desktop\NREL\current_projects\SETO_distcost\feeder_models\P10U\scenarios\base_timeseries\opendss\sb2_p10uhs2_1247_trans_51\sb2_p10uhs2_1247_trans_51--p10udt1066"

master_filename = "PVSystems.dss"
# dss_filepath = r"C:\Users\SABRAHAM\Desktop\NREL\current_projects\SETO_distcost\AutomatedUpgrades\smart-ds_test\substations\p1uhs23_1247\p1uhs23_1247--p1udt21301\hc_pv_deployments\close\1\5"
# dss_filepath = r"C:\Users\SABRAHAM\Desktop\NREL\current_projects\SETO_distcost\AutomatedUpgrades\smart-ds_test\substations\p1uhs23_1247\p1uhs23_1247--p1udt21301\hc_pv_deployments\close\1\15"
# dss_filepath = r"C:\Users\SABRAHAM\Desktop\NREL\current_projects\SETO_distcost\AutomatedUpgrades\smart-ds_test\substations\p1uhs21_1247\p1uhs21_1247--p1udt5257\hc_pv_deployments\close\1\5"
dss_filepath = r"C:\Users\SABRAHAM\Desktop\NREL\current_projects\SETO_distcost\AutomatedUpgrades\smart-ds_test\substations\p1uhs21_1247\p1uhs21_1247--p1udt5257\hc_pv_deployments\close\1\15"

# master_filename = "deployment.dss"
master_path = os.path.join(dss_filepath, master_filename)
output_folder = os.path.join(dss_filepath, "upgrades")

# TODO use this
upgrade_process_type = "thermal_only"  # other option is 'voltage_only', 'thermal+voltage', 'voltage+thermal'

log_console_level = logging.DEBUG
log_file_level = logging.DEBUG

# volt_var_model = None
volt_var_model = PvControllerModel(
    Control1="VVar",
    Control2="None",
    Control3="None",
    pf=1,
    pfMin=0.8,
    pfMax=1,
    Pmin=0,
    Pmax=1,
    uMin=0.9399999999999999,
    uDbMin=0.97,
    uDbMax=1.03,
    uMax=1.06,
    QlimPU=0.44,
    PFlim=0.9,
    enable_pf_limit=False,
    uMinC=1.06,
    uMaxC=1.1,
    PminVW=10,
    VWtype="Rated Power",
    percent_p_cutin=10,
    percent_p_cutout=10,
    Efficiency=100,
    Priority="Var",
    DampCoef=0.8,
)


PYDSS_PARAMS = {"enable_pydss_solve": True, "pydss_volt_var_model": volt_var_model}
# pydss_params = {"enable_pydss_solve": False, "pydss_volt_var_model": volt_var_model}

# define thermal parameters
thermal_config = {
    "xfmr_upper_limit": 1.25,
    "line_upper_limit": 1.25,
    "line_design_pu": 0.75,
    "xfmr_design_pu": 0.75,
    "voltage_upper_limit": 1.05,
    "voltage_lower_limit": 0.95,
}  # in per unit

# define voltage upgrade parameters
voltage_config = {}
voltage_config["target_v"] = 1
voltage_config["nominal_voltage"] = 120  # 240
voltage_config["nominal_pu_voltage"] = 1
voltage_config["tps_to_test"] = []
voltage_config["capacitor_sweep_voltage_gap"] = 1
voltage_config["reg_control_bands"] = [1, 2]
voltage_config["reg_v_delta"] = 0.5
voltage_config["max_regulators"] = 4
voltage_config["place_new_regulators"] = False
voltage_config["use_ltc_placement"] = False
voltage_config.update(
    {"initial_upper_limit": 1.05, "initial_lower_limit": 0.95}
)  # in per unit
voltage_config.update(
    {"final_upper_limit": 1.05, "final_lower_limit": 0.95}
)  # in per unit

create_topology_plots = False
