import os

from jade.common import OUTPUT_DIR
from disco import timer_stats_collector

from .upgrades.automated_thermal_upgrades import determine_thermal_upgrades
from .upgrades.automated_voltage_upgrades import determine_voltage_upgrades
from .upgrades.cost_computation import compute_all_costs


class UpgradeSimulation:
    
    def __init__(self, job, job_global_config, output=OUTPUT_DIR):
        self.job = job
        self.job_global_config = job_global_config
        self.output = output
    
    @property
    def model(self):
        return self.job.model
    
    @property
    def job_output(self):
        return os.path.join(self.output, self.model.name)
    
    def get_thermal_upgrades_directory(self):
        thermal_upgrades = os.path.join(self.job_output, "ThermalUpgrades")
        os.makedirs(thermal_upgrades, exist_ok=True)
        return thermal_upgrades
    
    def get_voltage_upgrades_directory(self):
        voltage_upgrades = os.path.join(self.job_output, "VoltageUpgrades")
        os.makedirs(voltage_upgrades, exist_ok=True)
        return voltage_upgrades

    def get_upgrade_costs_directory(self):
        upgrade_costs = os.path.join(self.job_output, "UpgradeCosts")
        os.makedirs(upgrade_costs, exist_ok=True)
        return upgrade_costs
    
    def get_feeder_stats_json_file(self):
        feeder_stats_json_file = os.path.join(self.job_output, "feeder_stats.json")
        return feeder_stats_json_file
    
    def get_thermal_upgrades_dss_file(self):
        return os.path.join(self.job_output, "thermal_upgrades.dss")
    
    def get_voltage_upgrades_dss_file(self):
        return os.path.join(self.job_output, "voltage_upgrades.dss")
    
    def get_upgraded_master_dss_file(self):
        return os.path.join(self.job_output, "upgraded_master.dss")

    def get_line_upgrades_json_file(self):
        thermal_upgrades = self.get_thermal_upgrades_directory()
        return os.path.join(thermal_upgrades, "line_upgrades.json")
    
    def get_transformer_upgrades_json_file(self):
        thermal_upgrades = self.get_thermal_upgrades_directory()
        return os.path.join(thermal_upgrades, "transformer_upgrades.json")
    
    def get_voltage_upgrades_json_file(self):
        voltage_upgrades = self.get_voltage_upgrades_directory()
        return os.path.join(voltage_upgrades, "voltage_upgrades.json")
    
    def get_thermal_summary_json_file(self):
        thermal_upgrades = self.get_thermal_upgrades_directory()
        return os.path.join(thermal_upgrades, "thermal_summary.json")
    
    def get_voltage_summary_json_file(self):
        voltage_upgrades = self.get_voltage_upgrades_directory()
        return os.path.join(voltage_upgrades, "voltage_summary.json")

    def get_line_upgrade_options_file(self):
        thermal_upgrades = self.get_thermal_upgrades_directory()
        return os.path.join(thermal_upgrades, "line_upgrade_options.json")
    
    def get_transformer_upgrade_options_file(self):
        thermal_upgrades = self.get_thermal_upgrades_directory()
        return os.path.join(thermal_upgrades, "xfmr_upgrade_options.json")
    
    def get_thermal_upgrade_costs_file(self):
        upgrade_costs = self.get_upgrade_costs_directory()
        return os.path.join(upgrade_costs, "thermal_upgrade_costs.json")
    
    def get_voltage_upgrade_costs_file(self):
        upgrade_costs = self.get_upgrade_costs_directory()
        return os.path.join(upgrade_costs, "voltage_upgrade_costs.json")
    
    def get_total_upgrade_costs_file(self):
        upgrade_costs = self.get_upgrade_costs_directory()
        return os.path.join(upgrade_costs, "total_upgrade_costs.json")

    @staticmethod
    def generate_command(job, output, config_file, verbose=False):
        """
        Parameters
        ----------
        job: UpgradeParameters
            The instance of upgradeParameters
        output: str
            The output directory of jobs, e.g output/job-outputs
        config_file: str
            The path of config file during runtime
        verbose: bool
            Enable verbose logging if True
        """
        command = [
            "jade-internal run upgrade_simulation",
            f"--name={job.name}",
            f"--output={output}",
            f"--config-file={config_file}"
        ]

        if verbose:
            command.append("--verbose")
        
        return " ".join(command)

    def run(
        self,
        enable_pydss_solve,
        pydss_controller_model,
        dc_ac_ratio,
        thermal_config,
        voltage_config,
        cost_database_filepath,
        verbose=False
    ):  
        determine_thermal_upgrades(
            job_name = self.job.name,
            master_path=self.model.deployment.deployment_file,
            enable_pydss_solve=enable_pydss_solve,
            thermal_config=thermal_config,
            pydss_volt_var_model=pydss_controller_model,
            line_upgrade_options_file=self.get_line_upgrade_options_file(),
            xfmr_upgrade_options_file=self.get_transformer_upgrade_options_file(),
            thermal_summary_file=self.get_thermal_summary_json_file(),
            thermal_upgrades_dss_filepath=self.get_thermal_upgrades_dss_file(),
            upgraded_master_dss_filepath=self.get_upgraded_master_dss_file(),
            output_json_line_upgrades_filepath=self.get_line_upgrades_json_file(),
            output_json_xfmr_upgrades_filepath=self.get_transformer_upgrades_json_file(),
            feeder_stats_json_file = self.get_feeder_stats_json_file(),
            thermal_upgrades_directory=self.get_thermal_upgrades_directory(),
            dc_ac_ratio=dc_ac_ratio,
            verbose=verbose
        )
        determine_voltage_upgrades(
            job_name = self.job.name,
            master_path=self.model.deployment.deployment_file,
            enable_pydss_solve=enable_pydss_solve,
            pydss_volt_var_model=pydss_controller_model,
            thermal_config=thermal_config,
            voltage_config=voltage_config,
            thermal_upgrades_dss_filepath=self.get_thermal_upgrades_dss_file(),
            voltage_upgrades_dss_filepath=self.get_voltage_upgrades_dss_file(),
            upgraded_master_dss_filepath=self.get_upgraded_master_dss_file(),
            voltage_summary_file=self.get_voltage_summary_json_file(),
            output_json_voltage_upgrades_filepath = self.get_voltage_upgrades_json_file(),
            feeder_stats_json_file = self.get_feeder_stats_json_file(),
            voltage_upgrades_directory=self.get_voltage_upgrades_directory(),
            dc_ac_ratio=dc_ac_ratio,
            output_folder=self.job_output,
            verbose=verbose
        )
        compute_all_costs(
            output_json_xfmr_upgrades_filepath=self.get_transformer_upgrades_json_file(),
            output_json_line_upgrades_filepath=self.get_line_upgrades_json_file(),
            output_json_voltage_upgrades_filepath=self.get_voltage_upgrades_json_file(),
            cost_database_filepath=cost_database_filepath,
            thermal_cost_output_filepath=self.get_thermal_upgrade_costs_file(),
            voltage_cost_output_filepath=self.get_voltage_upgrade_costs_file(),
            total_cost_output_filepath=self.get_total_upgrade_costs_file()
        )
        timer_stats_collector.log_stats(clear=True)
