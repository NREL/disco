import abc
import enum
import json
import logging
import os
import random
import sys
from copy import deepcopy
from types import SimpleNamespace
from typing import Optional, Generator, Tuple, Sequence

import opendssdirect as dss
from filelock import SoftFileLock
from unidecode import unidecode

from disco.enums import Placement

logger = logging.getLogger(__name__)


class DeploymentHierarchy(enum.Enum):
    FEEDER = "feeder"
    SUBSTATION = "substation"
    REGION = "region"


class DeploymentCategory(enum.Enum):
    MIXT = "mixt"
    SMALL = "small"
    LARGE = "large"


class PVDSSInstance:
    """OpenDSS file handler for PV deployments."""

    def __init__(self, master_file):
        self.master_file = master_file
    
    @property
    def feeder_name(self):
        return os.path.basename(os.path.os.path.dirname(self.master_file))
    
    def convert_to_ascii(self) -> None:
        """Convert unicode data in ASCII characters for representation"""
        with open(self.master_file, "r") as f:
            data = f.read()
        updated_data = unidecode(data)
        with open(self.master_file, "w") as f:
            f.write(updated_data)
    
    def load_feeder(self) -> None:
        """OpenDSS redirect master DSS file"""
        dss.run_command("Clear")
        logger.info("OpenDSS loads feeder - %s", self.master_file)
        r = dss.run_command(f"Redirect {self.master_file}")
        if r != "":
            logger.error("OpenDSSError: %s. Feeder: %s", str(r), self.master_file)
    
    def search_head_line(self) -> None:
        """Search head line from DSS topology"""
        flag = dss.Topology.First()
        while flag > 0:
            if "line" in dss.Topology.BranchName().lower():
                return dss.Topology.BranchName()
            flag = dss.Topology.Next()
    
    def ensure_energy_meter(self) -> bool:
        missing, misplaced = self.check_energy_meter_status()
        if missing:
            logger.info("Energy meter missing in master file - %s", self.master_file)
            self.place_new_energy_meter()
        elif misplaced:
            logger.info("Energy meter location is not correct in master file - %s", self.master_file)
            self.move_energy_meter_location()
        else:
            logger.info("Energy meter exists and meter status is good in master file - %s", self.master_file)
            pass
        return missing or misplaced
    
    def check_energy_meter_status(self) -> Tuple[bool, bool]:
        """Check if energy meter in dss is missing or misplaced"""
        with open(self.master_file, "r") as f:
            data = f.read()
        
        missing = 'New EnergyMeter' not in data
        misplaced = False
        if not missing:
            head_line = self.search_head_line()
            meter_location = data.split('\nNew EnergyMeter')[1].split('element=')[1].split('\n')[0].split(' ')[0]
            misplaced = meter_location != head_line
        
        return missing, misplaced
    
    def place_new_energy_meter(self) -> None:
        """Place new energy meter if it's missing from master dss file"""
        head_line = self.search_head_line()
        with open(self.master_file, "r") as f:
            data = f.read()
        
        temp = data.split('\nRedirect')[-1].split('\n')[0]
        updated_data = data.replace(temp, temp + f"\nNew EnergyMeter.m1 element={head_line}")
        with open(self.master_file, "w") as f:
            f.write(updated_data)
        logger.info("New energy meter was placed into master file - %s", self.master_file)
    
    def move_energy_meter_location(self) -> None:
        """Move energy meter location if it's misplaced in master dss file"""
        logger.info("Moving energy meter in master file - %s", self.master_file)
        head_line = self.search_head_line()
        with open(self.master_file, "r") as f:
            data = f.read()
        
        meter_location = data.split('\nNew EnergyMeter')[1].split('element=')[1].split('\n')[0].split(' ')[0]
        updated_data = data.replace(meter_location, head_line)
        updated_data += f"\n!Moved energy meter from {meter_location} to {head_line}"
        with open(self.master_file, 'w') as f:
            f.write(updated_data)
        logger.info("Moved energy meter from %s to %s in master file - %s", meter_location, head_line, self.master_file)
    
    def get_nbuses(self) -> int:
        """Get the number of buses in dss"""
        return dss.Circuit.NumBuses()
    
    def get_total_loads(self) -> SimpleNamespace:
        """Return total loads"""
        result = SimpleNamespace(**{
            "total_load": 0,
            "load_dict": {},
            "customer_bus_map": {},
            "bus_load": {},
            "bus_totalload": {}
        })
        flag = dss.Loads.First()
        while flag > 0:
            customer_id = dss.Loads.Name()
            bus = dss.Properties.Value("bus1")
            result.customer_bus_map[customer_id] = bus
            
            load_kW = dss.Loads.kW()
            result.load_dict[customer_id] = load_kW
            result.total_load += load_kW
            
            if not bus in result.bus_load:
                result.bus_load[bus] = []
                result.bus_totalload[bus] = load_kW
            else:
                result.bus_load[bus].append(customer_id)
                result.bus_totalload[bus] += load_kW

            flag = dss.Loads.Next()
        return result

    def get_customer_distance(self) -> SimpleNamespace:
        """Return custmer distance"""
        result = SimpleNamespace(**{"load_distance": {}, "bus_distance": {}})
        flag = dss.Loads.First()
        while flag > 0:
            dss.Circuit.SetActiveBus(dss.Properties.Value("bus1"))
            result.load_distance[dss.Loads.Name()] = dss.Bus.Distance()
            result.bus_distance[dss.Properties.Value("bus1")] = dss.Bus.Distance()
            flag = dss.Loads.Next()
        return result

    def get_highv_buses(self, kv_min: int = 1) -> SimpleNamespace:
        """Return highv buses"""
        result = SimpleNamespace(**{"bus_kv": {}, "hv_bus_distance": {}})
        flag = dss.Lines.First()
        while flag > 0:
            buses = [dss.Lines.Bus1(), dss.Lines.Bus2()]
            for bus in buses:
                dss.Circuit.SetActiveBus(bus)
                kvbase = dss.Bus.kVBase()
                if kvbase >= kv_min:
                    result.bus_kv[bus] = dss.Bus.kVBase()
                    result.hv_bus_distance[bus] = dss.Bus.Distance()
            flag = dss.Lines.Next()
        return result

    def get_existing_pvs(self) -> SimpleNamespace:
        """Return existing pvs"""
        result = SimpleNamespace(**{
            "total_existing_pv": 0,
            "existing_pv": {},
        })
        flag = dss.PVsystems.First()
        while flag > 0:
            bus = dss.Properties.Value("bus1")
            try:
                result.existing_pv[bus] += dss.PVsystems.Pmpp()
            except Exception:
                result.existing_pv[bus] = dss.PVsystems.Pmpp()
            result.total_existing_pv += dss.PVsystems.Pmpp()
            flag = dss.PVsystems.Next()
        return result
    
    def combine_bus_distances(self, customer_distance: SimpleNamespace, highv_buses: SimpleNamespace) -> dict:
        """Return the combined bus distance"""
        customer_bus_distance = customer_distance.bus_distance
        hv_bus_distance = highv_buses.hv_bus_distance
        logger.info(
            "Feeder Name: %s, Highv DistRange: (%s, %s)",
            self.feeder_name,
            min(hv_bus_distance.values()),
            max(hv_bus_distance.values())
        )
        
        combined_bus_distance = deepcopy(hv_bus_distance)
        combined_bus_distance.update(customer_bus_distance)
        return combined_bus_distance

    def get_feeder_stats(self, total_loads: SimpleNamespace, existing_pvs: SimpleNamespace = None) -> SimpleNamespace:
        """Return feeder stats"""
        result = {
            "n_buses": self.get_nbuses(),
            "nload_buses": len(total_loads.bus_totalload.keys()),
            "nzero_load_buses": sum(v == 0 for v in total_loads.bus_totalload.values()),
            "total_load": total_loads.total_load
        }
        if existing_pvs:
            nbase_pv_buses = len([b for b, v in existing_pvs.existing_pv.items() if v > 0])
            pcent_base_pv = (existing_pvs.total_existing_pv * 100) / max(0.0000001, total_loads.total_load)
            result.update({
                "nbase_pv_buses": nbase_pv_buses,
                "pcent_base_pv": pcent_base_pv,
                "total_base_pv": existing_pvs.total_existing_pv
            })
        result = SimpleNamespace(**result)
        return result


class PVScenarioDeployerBase:
    
    def __init__(self, feeder_path: str, config: SimpleNamespace) -> None:
        """
        Initialize PV scenario generator class
        
        Parameters
        ----------
        feeder_path: str, the input path of a feeder model.
        config: SimpleNamespace, the pv deployment config namespace.
        """
        self.feeder_path = feeder_path
        self.config = config
        self.current_cycle = None
        self.pv_threshold = 1.0e-10
        self.output_dirname = "hc_pv_deployments"
        self.pv_deployments = "PVDeployments.dss"
        self.pv_systems = "PVSystems.dss"
        self.load_shapes = "LoadShapes.dss"
    
    @property
    @abc.abstractmethod
    def deployment_cycles(self) -> list:
        """Return a list of cicyles for generating pv scenarios"""
        pass
    
    def get_feeder_name(self) -> str:
        """Return the feeder name"""
        return os.path.basename(self.feeder_path)
    
    def get_master_file(self) -> Optional[str]:
        """Return the full path of master file"""
        master_file = os.path.join(self.feeder_path, self.config.master_filename)
        if not os.path.exists(master_file):
            logger.error("'%s' not found in '%s'. System exits!", self.config.master_filename, self.feeder_path)
        return master_file
    
    def load_pvdss_instance(self) -> PVDSSInstance:
        """Setup DSS handler for master dss file processing"""
        master_file = self.get_master_file()
        pvdss_instance = PVDSSInstance(master_file)
        try:
            lock_file = master_file + ".lock"
            with SoftFileLock(lock_file=lock_file):
                pvdss_instance.convert_to_ascii()
                pvdss_instance.load_feeder()
                flag = pvdss_instance.ensure_energy_meter()
                if flag:
                    pvdss_instance.load_feeder()  # Need to reload after master file updated.
        except Exception as error:
            logger.exception("Failed to load master file - %s", master_file)
        return pvdss_instance
    
    def deploy_all_pv_scenarios(self) -> dict:
        """Given a feeder path, generate all PV scenarios for the feeder"""
        feeder_name = self.get_feeder_name()
        pvdss_instance = self.load_pvdss_instance()
        
        # total load
        total_loads = pvdss_instance.get_total_loads()
        feeder_stats = pvdss_instance.get_feeder_stats(total_loads)
        if total_loads.total_load <= 0:
            logger.error("This feeder '%s' has no load, we cannot generate PV scenarios", feeder_name)
            return feeder_stats.__dict__
        
        # combined bus distance
        customer_distance = pvdss_instance.get_customer_distance()
        highv_buses = pvdss_instance.get_highv_buses()
        combined_bus_distance = pvdss_instance.combine_bus_distances(customer_distance, highv_buses)
        if max(combined_bus_distance.values()) == 0:
            logger.warning(
                "Check your feeder model for '%s'.\n\
                The bus distance array does not look correct. Maximum bus distance = 0.00 km",
                feeder_name
            )
        hv_bus_map = {
            f"Large_{k.replace('.','-')}": k
            for k in highv_buses.hv_bus_distance.keys()
        }
        
        # existing pvs
        existing_pvs = pvdss_instance.get_existing_pvs()
        base_existing_pv = existing_pvs.existing_pv
        feeder_stats = pvdss_instance.get_feeder_stats(total_loads, existing_pvs)
        if feeder_stats.pcent_base_pv > self.config.max_penetration:
            logger.error(
                "The existing PV amount on feeder '%s' exceeds \
                the maximum penetration level of %s\%. It represents %s\%",
                feeder_name, self.cofig.max_penetration, feeder_stats.pcent_base_pv
            )
            return feeder_stats.__dict__
        
        # average_pv_distance = {}
        dnum = self.config.deployment_number + 1
        start = self.config.min_penetration
        end = self.config.max_penetration + 1
        step = self.config.penetration_step
        for deployment in range(1, dnum):
            existing_pv = deepcopy(base_existing_pv)
            pv_records = {}
            for penetration in range(start, end, step):
                data = SimpleNamespace(**{
                    "base_existing_pv": base_existing_pv,
                    "total_load": total_loads.total_load,
                    "load_dict": total_loads.load_dict,
                    "bus_totalload": total_loads.bus_totalload,
                    "total_existing_pv": sum(existing_pv.values()),
                    "existing_pv": existing_pv,
                    "hv_bus_distance": highv_buses.hv_bus_distance,
                    "customer_bus_distance": customer_distance.bus_distance,
                    "hv_bus_map": hv_bus_map,
                    "customer_bus_map": total_loads.customer_bus_map,
                    "bus_kv": highv_buses.bus_kv,
                    "pv_records": pv_records,
                    "penetration": penetration,
                    "deployment": deployment
                })
                existing_pv, pv_records = self.deploy_pv_scenario(data)
                # avg_dist = self.compute_average_pv_distance(combined_bus_distance, existing_pv)
                # key = (self.config.placement, deployment, penetration)
                # average_pv_distance[key] = [self.config.placement, deployment, penetration, avg_dist]
        
        return feeder_stats.__dict__
    
    def get_output_root_path(self):
        """Return the root path of PV depployments"""
        return os.path.join(self.feeder_path, self.output_dirname)
    
    def get_output_placement_path(self) -> str:
        """Return the placement path of PV deployments"""
        root_path = self.get_output_root_path()
        placement_path = os.path.join(root_path, self.config.placement)
        return placement_path
    
    def get_pv_deployments_file(self, deployment: int, penetration: int) -> str:
        """Return the path of PV depployment file"""
        placement_path = self.get_output_placement_path()
        penetration_path = os.path.join(placement_path, str(deployment), str(penetration))
        os.makedirs(penetration_path, exist_ok=True)
        pv_deployments_file = os.path.join(penetration_path, self.pv_deployments)
        return pv_deployments_file
    
    def deploy_pv_scenario(self, data: SimpleNamespace) -> dict:
        """Generate PV deployments dss file in scenario
        
        Parameters
        ----------
        data: SimpleNamespace, the data used for defining PV scenario

        Returns
        -------
        dict:
            The updated existing_pv
        """
        pv_string = "! =====================PV SCENARIO FILE==============================\n"
        
        categorical_remaining_pvs = self.get_categorical_remaining_pvs(data)
        bus_distances = self.get_bus_distances(data)
        customer_bus_map = self.get_customer_bus_map(data)
        priority_buses = self.get_priority_buses(data)
        existing_pv = data.existing_pv
        pv_records = data.pv_records
        
        undeployed_capacity = 0
        for pv_type in self.deployment_cycles:
            self.current_cycle = pv_type
            remaining_pv_to_install = categorical_remaining_pvs[pv_type] + undeployed_capacity
            bus_distance = bus_distances[pv_type]
            customer_bus_map = customer_bus_map[pv_type]
            
            ncs, subset_idx = 0, 0
            while remaining_pv_to_install > 0:
                if subset_idx == 0:
                    if self.config.pv_upscale:
                        for bus in priority_buses:
                            if bus in data.base_existing_pv:
                                base_min_pv_size = data.base_existing_pv[bus]
                            else:
                                base_min_pv_size = 0
                            if base_min_pv_size > 0:
                                continue
                            min_pv_size = existing_pv[bus]
                            max_pv_size = self.get_maximum_pv_size(bus, data)
                            random_pv_size = self.generate_pv_size_from_pdf(min_pv_size, max_pv_size)
                            pv_size = min(random_pv_size, min_pv_size + remaining_pv_to_install)
                            pv_added_capacity = pv_size - min_pv_size
                            remaining_pv_to_install -= pv_added_capacity
                            pv_string = self.add_pv_string(bus, pv_type.value, pv_size, pv_string)
                            pv_records[bus] = pv_size
                            existing_pv[bus] = pv_size
                            ncs += 1
                    else:
                        for bus in priority_buses:
                            if bus in data.base_existing_pv:
                                base_min_pv_size = data.base_existing_pv[bus]
                            else:
                                base_min_pv_size
                            if base_min_pv_size > 0:
                                continue
                            min_pv_size = existing_pv[bus]
                            pv_size = min_pv_size
                            pv_added_capacity = 0
                            remaining_pv_to_install -= pv_added_capacity
                            pv_string = self.add_pv_string(bus, pv_type.value, pv_size, pv_string)
                            pv_records[bus] = pv_size
                            existing_pv[bus] = pv_size

                subset_idx += 1
                candidate_bus_array = self.get_pv_bus_subset(bus_distance, subset_idx, priority_buses)
                if subset_idx > (100 / self.config.proximity_step):
                    logger.warning("There is not PVDeployments.dss file created - %s", self.feeder_path)
                    break
               
                while len(candidate_bus_array) > 0:
                    random.shuffle(candidate_bus_array)
                    picked_candidate = candidate_bus_array[0]
                    if picked_candidate in data.base_existing_pv:
                        base_min_pv_size = data.base_existing_pv[picked_candidate]
                    else:
                        base_min_pv_size = 0
                    if picked_candidate in existing_pv:
                        min_pv_size = existing_pv[picked_candidate]
                    else:
                        min_pv_size = 0
                    if (base_min_pv_size > 0 or min_pv_size > 0) and (not self.config.pv_upscale):
                        pass
                    else:
                        max_pv_size = self.get_maximum_pv_size(picked_candidate, data)
                        random_pv_size = self.generate_pv_size_from_pdf(0, max_pv_size)
                        pv_size = min(random_pv_size, 0 + remaining_pv_to_install)
                        pv_string = self.add_pv_string(picked_candidate, pv_type.value, pv_size, pv_string)
                        pv_records[picked_candidate] = pv_size
                        existing_pv[picked_candidate] = pv_size
                        pv_added_capacity = pv_size
                        remaining_pv_to_install -= pv_added_capacity
                        ncs += 1
                    candidate_bus_array.remove(picked_candidate)
                    
                    if abs(remaining_pv_to_install) <= self.pv_threshold and len(pv_string.split("New PVSystem.")) > 0:
                        if len(pv_records) > 0:
                            self.write_pv_string(pv_string, data)
                        break
                    if subset_idx * self.config.proximity_step > 100:
                        break
                    if remaining_pv_to_install > self.pv_threshold:
                        undeployed_capacity = remaining_pv_to_install
                
                logger.debug(
                    "Sample: %s, Placement: %s, @penetration %s, number of new installable PVs: %s, Remain_to_install: %s kW", 
                    data.deployment,
                    self.config.placement,
                    data.penetration,
                    ncs,
                    remaining_pv_to_install
                )
        return existing_pv, pv_records
    
    def get_total_pv(self, data: SimpleNamespace) -> dict:
        """Return total PV, including PV already installed and remaining to install"""
        total_pv = data.total_load * data.penetration / 100
        return total_pv
    
    def get_all_remaining_pv_to_install(self, data: SimpleNamespace) -> dict:
        """Return all remaining PV to install"""
        total_pv = self.get_total_pv(data)
        all_remaining_pv_to_install = total_pv - data.total_existing_pv
        if all_remaining_pv_to_install <= 0:
            minimum_penetration = (data.total_existing_pv * 100) / max(0.0001, data.total_load)
            logger.error(
                "%s - Failed to generate PV scenario. The system has more than the target PV penetration. \
                Please increase penetration to at least %s.", self.feeder_path, minimum_penetration
            )
        return all_remaining_pv_to_install

    def get_priority_buses(self, data: SimpleNamespace) -> list:
        """Return a list of priority buses."""
        priority_buses = list(data.existing_pv.keys())
        if len(priority_buses) == len(data.bus_totalload):
            logger.warning(
                "Beaware - Sample: %s, Placement: %s, @penetration %s, all buses already have PV installed.",
                data.deployment, self.config.placement, data.penetration
            )
        return priority_buses
    
    @abc.abstractmethod
    def get_categorical_remaining_pvs(self, data: SimpleNamespace) -> dict:
        """Return remaining sall, large PV to install"""
        pass
    
    def get_bus_distances(self, data: SimpleNamespace) -> dict:
        """Return bus distance of large/small category"""
        return {
            DeploymentCategory.SMALL: data.customer_bus_distance,
            DeploymentCategory.LARGE: data.hv_bus_distance
        }
    
    def get_customer_bus_map(self, data: SimpleNamespace) -> dict:
        return {
            DeploymentCategory.SMALL: data.customer_bus_map,
            DeploymentCategory.LARGE: data.hv_bus_map
        }
    
    @classmethod
    @abc.abstractmethod
    def get_maximum_pv_size(cls, bus: str, data: SimpleNamespace, **kwargs) -> float:
        pass
    
    @staticmethod
    def generate_pv_size_from_pdf(min_size: float, max_size: float, pdf: Sequence = None) -> float:
        # TODO: A placeholder function for later update
        pv_size = max_size
        return pv_size
    
    @staticmethod
    def add_pv_string(bus: str, pv_type: str, pv_size: float, pv_string: str) -> str:
        """Add PV string to exiting string"""
        if pv_size <= 0:
            return ""
        
        pv_name = f"{pv_type}_{bus.replace('.', '_')}_pv"
        dss.Circuit.SetActiveBus(bus)
        node_list = bus.split(".")
        ph = len(node_list) - 1
        if ph == 3:
            conn = "delta"
            kv = round(dss.Bus.kVBase()*(3)**0.5, 4)
        elif ph == -1 or ph == 4:
            conn = "wye"
            kv = round(dss.Bus.kVBase()*(3)**0.5, 4)
        elif ph == 2:
            conn = "wye"
            if "0" in node_list[1:]:
                kv = round(dss.Bus.kVBase(), 4)
            else:
                kv = round(dss.Bus.kVBase() * 2, 4)
            ph = 1
        else:
            conn = "wye"
            kv = round(dss.Bus.kVBase(), 4)
        pv_size = round(pv_size, 3)
        new_pv_string = (
            f"New PVSystem.{pv_name} phases={ph} "
            f"bus1={bus} kv={kv} irradiance=1 "
            f"Pmpp={pv_size} pctPmpp=100 kVA={pv_size} "
            f"conn={conn} %cutin=0.1 %cutout=0.1 "
            f"Vmaxpu=1.2 !{pv_type} \n"
        )
        pv_string += new_pv_string
        return pv_string

    def write_pv_string(self, pv_string: str, data: SimpleNamespace) -> None:
        """Write PV string to PV deployment file."""
        total_pv = self.get_total_pv(data)
        pv_deployments_file = self.get_pv_deployments_file(data.deployment, data.penetration)
        line = (
            f"// PV Scenario for {total_pv} kW total size, "
            f"Scenario type {self.config.placement}, Deployment {data.deployment} "
            f"and penetration {data.penetration}% (PV to load ratio) \n"
        )
        with open(pv_deployments_file, "w") as f:
            f.write(line)
            f.write(pv_string)

    def get_pv_bus_subset(self, bus_distance: dict, subset_idx: int, priority_buses: list) -> list:
        """Return candidate buses"""
        max_dist = max(bus_distance.values())
        min_dist = min(bus_distance.values())
        if self.config.placement == Placement.CLOSE.value:
            lb_dist = (subset_idx - 1) * (self.config.proximity_step * max_dist) / 100
            ub_dist = subset_idx * self.config.proximity_step * max_dist / 100
        elif self.config.placement == Placement.FAR.value:
            ub_dist = (100 - (subset_idx - 1) * self.config.proximity_step) * max_dist / 100
            lb_dist = (100 - subset_idx * self.config.proximity_step) * max_dist / 100
        elif self.config.placement == Placement.RANDOM.value:
            lb_dist = min_dist
            ub_dist = max_dist
        
        candidate_bus_map = {
            k: v for k, v in bus_distance.items() 
            if v > lb_dist and v <= ub_dist
        }
        candidate_buses = list(candidate_bus_map.keys())
        candidate_bus_array = [b for b in candidate_buses if not b in priority_buses]
        return candidate_bus_array

    def compute_average_pv_distance(self, bus_distance: dict, existing_pv: dict) -> float:
        """Compute the average PV distance"""
        slack_dico = {
            k: bus_distance[k]
            for k, v in existing_pv.items()
            if v > 0 and k in list(bus_distance.keys())
        }
        average_pv_distance = np.mean(np.array(list(slack_dico.values())))
        return average_pv_distance

    def get_load_shapes_file(self) -> str:
        """Return the loadshapes file in feeder path"""
        load_shapes_file = os.path.join(self.feeder_path, self.load_shapes)
        return load_shapes_file
    
    def create_all_pv_configs(self) -> None:
        """Create PV configs JSON file"""
        root_path = self.get_output_root_path()
        if not os.path.exists(root_path):
            return
        
        load_shapes_file = self.get_load_shapes_file()
        placement_path = self.get_output_placement_path()
        deployments = next(os.walk(placement_path))[1]
        for deployment in deployments:
            sample_path = os.path.join(placement_path, deployment)
            penetrations = [int(p) for p in next(os.walk(sample_path))[1]]
            penetrations.sort()
            for i in range(len(penetrations)):
                max_pen = penetrations.pop()
                pv_file = os.path.join(sample_path, str(max_pen), self.pv_deployments)
                
                if os.path.exists(pv_file):
                    break
            pv_config = self.assign_profile(pv_file, load_shapes_file)
            self.save_pv_config(pv_config, sample_path)
        logger.info("All PV config files generated in placement - %s", placement_path)
   
    def assign_profile(self, pv_deployments_file: str, load_shapes_file: str, limit: int = 5) -> dict:
        """Assign PV profile to PV systems."""
        pv_dict = self.get_pvsys(pv_deployments_file)
        shape_list = self.get_shape_list(load_shapes_file)
        pv_conf = {"pv_systems": []}
        for pv_name, pv_value in pv_dict.items():
            if float(pv_value) > limit:
                control_name = "volt-var"
            else:
                control_name = "pf1"
            random.shuffle(shape_list)
            pv_profile = shape_list[0]
            pv_conf['pv_systems'].append({
                "name": pv_name,
                "pydss_controller": {
                    "controller_type": "PvController",
                    "name": control_name
                },
                "pv_profile": pv_profile
            })
        return pv_conf
    
    @staticmethod
    def get_pvsys(pv_deployments_file: str) -> dict:
        """Return a mapping of PV systems"""
        pv_dict = {}
        with open(pv_deployments_file) as f:
            slines = f.readlines()
            for line in slines:
                if "pvsystem" in line.lower():
                    value = line.lower().split("pmpp=")[1].split(" ")[0]
                    pv_dict[line.lower().split("pvsystem.")[1].split(" ")[0]] = value
        return pv_dict
    
    def get_shape_list(self, load_shapes_file: str) -> list:
        """Return a list of loadshapes"""
        load_shapes_file = self.get_load_shapes_file()
        shape_list = []
        with open(load_shapes_file) as f:
            slines = f.readlines()
            for line in slines:
                if "loadshape" in line.lower():
                    shape_list.append(line.lower().split("loadshape.")[1].split(' ')[0])
        return shape_list
    
    def save_pv_config(self, pv_config: dict, sample_path: str) -> None:
        """Save PV configuration to JSON file"""
        pv_config_file = os.path.join(sample_path, "pv_config.json")
        with open(pv_config_file, "w") as f:
            json.dump(pv_config, f, indent=2)
        logger.info("PV config file generated - %s", pv_config_file)


class LargePVScenarioDeployer(PVScenarioDeployerBase):
    
    @property
    def deployment_cycles(self) -> list:
        return [DeploymentCategory.LARGE]
    
    def get_categorical_remaining_pvs(self, data: SimpleNamespace) -> dict:
        all_remaining_pv_to_install = self.get_all_remaining_pv_to_install(data)
        categorical_remaining_pvs = {
            DeploymentCategory.LARGE: all_remaining_pv_to_install,
            DeploymentCategory.SMALL: 0
        }
        return categorical_remaining_pvs
    
    @classmethod
    def get_maximum_pv_size(cls, bus: str, data: SimpleNamespace, **kwargs) -> int:
        max_bus_pv_size = 100 * random.randint(1, 50)
        return max_bus_pv_size


class SmallPVScenarioDeployer(PVScenarioDeployerBase):

    @property
    def deployment_cycles(self) -> list:
        return [DeploymentCategory.SMALL]
    
    def get_categorical_remaining_pvs(self, data: SimpleNamespace) -> dict:
        all_remaining_pv_to_install = self.get_all_remaining_pv_to_install(data)
        categorical_remaining_pvs = {
            DeploymentCategory.LARGE: 0,
            DeploymentCategory.SMALL: all_remaining_pv_to_install
        }
        return categorical_remaining_pvs
    
    @classmethod
    def get_maximum_pv_size(cls, bus: str, data: SimpleNamespace, max_load_factor: float = 3,  **kwargs) -> float:
        roof_area = kwargs.get("roof_area", {})
        pv_efficiency = kwargs.get("pv_efficiency", None)
        customer_annual_kwh = kwargs.get("customer_annual_kwh", {})
        annual_sun_hours = kwargs.get("annual_sun_hours", None)
        
        pv_size_array = [max_load_factor * data.bus_totalload[bus]]
        if roof_area and pv_efficiency:
            value = roof_area[bus] * pv_efficiency
            pv_size_array.append(value)
        if customer_annual_kwh and annual_sun_hours:
            value = customer_annual_kwh_dict[bus] / anual_sun_hours
            pv_size_array.append(value)
        max_bus_pv_size = min(pv_size_array)
        return max_bus_pv_size


class MixtPVScenarioDeployer(PVScenarioDeployerBase):
    
    @property
    def deployment_cycles(self) -> list:
        return [DeploymentCategory.SMALL, DeploymentCategory.LARGE]
    
    def get_categorical_remaining_pvs(self, data: SimpleNamespace) -> dict:
        all_remaining_pv_to_install = self.get_all_remaining_pv_to_install(data)
        small_pv_to_install = (self.config.percent_shares[1] / 100) * all_remaining_pv_to_install
        large_pv_to_install = (1 - self.config.percent_shares[1] / 100) * all_remaining_pv_to_install
        categorical_remaining_pvs = {
            DeploymentCategory.LARGE: large_pv_to_install,
            DeploymentCategory.SMALL: small_pv_to_install
        }
        return categorical_remaining_pvs

    @classmethod
    def get_maximum_pv_size(cls, bus: str, data: SimpleNamespace, **kwargs) -> float:
        if self.current_cycle == DeploymentCategory.LARGE:
            return LargePVScenarioDeployer.get_maximum_pv_size(bus, data, **kwargs)
        if self.current_cycle == DeploymentCategory.SMALL:
            return SmallPVScenarioDeployer.get_maximum_pv_size(bus, data, **kwargs)
        return None


class PVDeploymentGeneratorBase(abc.ABC):
    
    def __init__(self, input_path: str, config: SimpleNamespace) -> None:
        """
        Initialize pv deployment generator class
        
        Parameters:
        ----------
        input_path: str, the input path of raw dss data for generating pv deployments.
        config: SimpleNamespace, the pv deployment configuration namespace.
        """
        self.input_path = input_path
        self.config = config
    
    @abc.abstractmethod
    def get_feeder_paths(self) -> list:
        """Return all feeder paths recursively under given input_path."""
        pass
    
    def generate_pv_deployments(self) -> dict:
        """Given input path, generate pv deployments"""
        summary = {}
        # TODO: try parallize using multiprocessing
        feeder_paths = self.get_feeder_paths()
        for feeder_path in feeder_paths:
            deployer = get_pv_scenario_deployer(feeder_path, self.config)
            feeder_stats = deployer.deploy_all_pv_scenarios()
            summary[feeder_path] = feeder_stats
            deployer.create_all_pv_configs()
        return summary
    
    def generate_pv_configs(self) -> None:
        """Generate pv config JSON files based on PV deployments"""
        feeder_paths = self.get_feeder_paths()
        for feeder_path in feeder_paths:
            deployer = get_pv_scenario_deployer(feeder_path, self.config)
            deployer.create_all_pv_configs()


class FeederPVDeploymentGenerator(PVDeploymentGeneratorBase):
    """PV deployment generator for one feeder"""
    def get_feeder_paths(self) -> list:
        """Given a feeder path, return as a list if not"""
        if not isinstance(self.input_path, list):
            feeder_paths = [self.input_path]
        return feeder_paths


class SubstationPVDeploymentGenerator(PVDeploymentGeneratorBase):
    """PV deployment generator for all feeders under one substation"""
    
    def get_feeder_paths(self) -> list:
        """Given a substation path, return all feeder paths in the substation"""
        feeder_names = next(os.walk(self.input_path))[1]
        feeder_paths = [
            os.path.join(self.input_path, feeder_name)
            for feeder_name in feeder_names
        ]
        return feeder_paths


class RegionPVDeploymentGenerator(PVDeploymentGeneratorBase):
    """PV deployment generator for all feeders under one region"""
    
    def get_feeder_paths(self) -> list:
        """Given a region path, return all feeder paths in the region"""
        self.input_path = os.path.join(
            self.input_path,
            "solar_none_batteries_none_timeseries",
            "opendss"
        )
        feeder_paths = []
        substation_names = next(os.walk(self.input_path))[1]
        for substation_name in substation_names:
            substation_path = os.path.join(self.input_path, substation_name)
            feeder_names = next(os.walk(substation_path))[1]
            feeder_paths.extend([
                os.path.join(self.input_path, substation_name, feeder_name)
                for feeder_name in feeder_names
            ])
        return feeder_paths


def get_pv_scenario_deployer(feeder_path: str, config: SimpleNamespace):
    """Return a PV scenario generator instnace"""
    pv_scenario_deployer_mapping = {
        DeploymentCategory.SMALL: SmallPVScenarioDeployer,
        DeploymentCategory.LARGE: LargePVScenarioDeployer,
        DeploymentCategory.MIXT: MixtPVScenarioDeployer
    }
    category = DeploymentCategory(config.category)
    deployer_class = pv_scenario_deployer_mapping[category]
    deployer = deployer_class(feeder_path, config)
    return deployer
