import abc
import enum
import logging
import os
import random
import sys
from collections import defaultdict
from copy import deepcopy
from types import SimpleNamespace, Tuple

import opendssdirect as dss
from unidecode import unidecode

from disco.enums import Placement
from disco.sources.source_tree_1.factory import generate_pv_scenario

logger = logging.getLogger(__name__)

PV_SCENARIO_GENERATOR_MAPPING = {
    ScenarioCategory.small: SmallPVScenarioGenerator,
    ScenarioCategory.large: LargePVScenarioGenerator,
    ScenarioCategory.mixt: MixtPVScenarioGenerator
}


class DeploymentHierarchy(enum.Enum):
    feeder = "feeder"
    substation = "substation"
    region = "region"


class ScenarioCategory(enum.Enum):
    mixt = "mixt"
    small = "small"
    large = "large"


class PVDSSHandler:
    """OpenDSS file handler for PV deployments."""

    def __init__(self, master_file, verbose=False):
        self.master_file = master_file
        self.verbose = verbose
        self.convert_to_ascii()
        self.load_feeder()
    
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
        if self.verbose:
            logger.info("OpenDSS loads feeder - %s", self.master_file)
        r = dss.run_command(f"Redirect {self.master_file}")
        if r != "" and self.verbose():
            logger.error(f"OpenDSSError: {r}. System exits!")
            sys.exit(1)
    
    def search_head_line(self) -> None:
        """Search head line from DSS topology"""
        flag = dss.Topology.First()
        while flag > 0:
            if "line" in dss.Topology.BranchName().lower():
                return dss.Topology.BranchName()
            flag = dss.Topology.Next()
    
    def check_energy_meter_status(self) -> Tuple[bool, bool]:
        """Check if energy meter in dss is missing or misplaced"""
        with open(self.master_file, "r") as f:
            data = f.read()
        
        missing = 'New EnergyMeter' not in data
        if missing and self.verbose:
            logger.info("Energy meter missing in master file - %s", self.master_file)
       
        misplaced = False
        if not missing:
            head_line = self.search_head_line()
            meter_location = data.split('\nNew EnergyMeter')[1].split('element=')[1].split('\n')[0].split(' ')[0]
            misplaced = meter_location != head_line
        if misplaced and self.verbose:
            logger.info("Energy meter location is not correct in master file - %s", self.master_file)
       
        return missing, misplaced
    
    def place_new_energy_meter(self) -> None:
        """Place new energy meter if it's missing from master dss file"""
        if self.verbose:
            logger.info("Placing new energy meter into master file - %s", self.master_file)
        
        head_line = self.search_head_line()
        with open(self.master_file, "r") as f:
            data = f.read()
        
        # TODO: refactor, attach new line at the end of file?
        temp = data.split('\nRedirect')[-1].split('\n')[0]
        updated_data = data.replace(temp, temp + f"\nNew EnergyMeter.m1 element={head_line}")
        with open(self.master_file, "w") as f:
            f.write(updated_data)
        
        if self.verbose:
            logger.info("New energy meter was placed into master file - %s", self.master_file)
        
        self.load_feeder()
    
    def move_energy_meter_location(self):
        """Move energy meter location if it's misplaced in master dss file"""
        if self.verbose:
            logger.info("Moving energy meter in master file - %s", self.master_file)
        
        head_line = self.search_head_line()
        with open(self.master_file, "r") as f:
            data = f.read()
        
        meter_location = data.split('\nNew EnergyMeter')[1].split('element=')[1].split('\n')[0].split(' ')[0]
        updated_data = data.replace(meter_location, head_line)
        updated_data += f"\n!Moved energy meter from {meter_location} to {head_line}"
        with open(self.master_file, 'w') as f:
            f.write(updated_data)
        
        if self.verbose:
            logger.info("Moved energy meter from %s to %s in master file - %s", meter_location, head_line, self.master_file)
        
        self.load_feeder()
    
    def get_nbuses(self) -> int:
        """Get the number of buses in dss"""
        return dss.Circuit.NumBuses()
    
    def get_total_loads(self) -> SimpleNamespace:
        """Return total loads"""
        result = SimpleNamespace(**{
            "total_load": 0,
            "customer_loads": {},
            "customer_bus": {},
            "bus_customers": defaultdict(list),
            "bus_totalload": defaultdict(int)
        })
        flag = dss.Loads.First()
        while flag > 0:
            customer_id = dss.Loads.Name()
            bus = dss.Properties.Value("bus1")
            result.customer_bus[customer_id] = bus
            
            load_kW = dss.Loads.kW()
            result.customer_loads[customer_id] = load_kW
            result.total_load += load_kW
            
            result.bus_customers[bus].append(customer_id)
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

    def get_highv_buses(self, kv_min=1) -> SimpleNamespace:
        """Return highv buses"""
        result = SimpleNamespace(**{"bus_kv": {}, "hv_bus_distance": {}})
        flag = dss.Lines.First()
        while flag > 0:
            if dss.Lines.Phases() < 3:
                continue
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
            "existing_pv": defaultdict(int),
        })
        flag = dss.PVsystems.First()
        while flag > 0:
            bus = dss.Properties.Value("bus1")
            result.existing_pv[bus] += dss.PVsystems.kVARated()
            result.total_existing_pv += dss.PVsystems.kVARated()
            flag = dss.PVsystems.Next()
        return result


class PVScenarioGeneratorBase:
    
    def __init__(self, data, verbose=False) -> None:
        # TODO: define data inputs
        self.data = data
        self.undeployed_capacity = 0
        self.threshold = 1.0e-10
    
    @property
    @abc.abstractmethod
    def pv_type(self):
        pass
    
    @property
    @abc.abstractmethod
    def pv_file(self):
        pass
    
    def generate_pv_scenario(self, existing_pv):
        pv_string = "! =====================PV SCENARIO FILE==============================\n"
        remaining_pv_to_install = self.get_remaining_pv_to_install()
        priority_buses = self.get_priority_buses()
        
        ncs, subset_index = 0, 0
        while remaining_pv_to_install > 0:
            if subset_idx == 0 and self.data.pv_upscale:
                for bus in priority_buses:
                    base_min_pv_size = self.data.base_existing_pv[bus]
                    if base_min_pv_size > 0:
                        continue
                    min_pv_size = existing_pv[bus]
                    max_pv_size = self.get_max_pv_size(bus)
                    random_pv_size = self.generate_pv_size_from_pdf(min_pv_size, max_pv_size)
                    pv_size = min(random_pv_size, min_pv_size + remaining_pv_to_install)
                    pv_added_capacity = pv_size - min_pv_size
                    remaining_pv_to_install -= pv_added_capacity
                    pv_string = self.add_pv_string(bus, pv_size, pv_string)
                    existing_pv[bus] = pv_size
            elif subset_idx == 0 and not self.data.pv_upscale:
                for bus in priority_buses:
                    base_min_pv_size = self.data.base_existing_pv[bus]
                    if base_min_pv_size > 0:
                        continue
                    min_pv_size = existing_pv[bus]
                    pv_size = min_pv_size
                    pv_added_capacity = 0
                    remaining_pv_to_install -= pv_added_capacity
                    pv_string = self.add_pv_string(bus, pv_size, pv_string)
            
            # TODO: check
            subset_index += 1
            candidate_bus, candidate_bus_map = self.get_pv_bus_subset(subset_idx)
            candidate_bus_array = [bus for bus in candidate_bus if not bus in priority_buses]
            
            while len(candidate_bus_array) > 0:
                random.shuffle(candidate_bus_array)
                picked_candiate = candidate_bus_array[0]
                base_min_pv_size = self.data.base_existing_pv[picked_candiate]
                min_pv_size = existing_pv[picked_candiate]
                if (base_min_pv_size > 0 or min_pv_size > 0) and (not self.data.pv_upscale):
                    pass
                else:
                    max_pv_size = self.get_maximum_pv_size(picked_candiate)
                    random_pv_size = self.generate_pv_size_from_pdf(0, max_pv_size)
                    pv_size = min(random_pv_size, 0 + remaining_pv_to_install)
                    pv_string = self.add_pv_string(picked_candiate, pv_size)
                    pv_added_capacity = pv_size
                    remaining_pv_to_install -= pv_added_capacity
                    ncs += 1
                candidate_bus_array.remove(picked_candiate)
                if abs(remaining_pv_to_install) <= self.threshold and len(pv_string.split("New PVSystem.")) > 0:
                    self.write_pv_string(pv_string, **kwargs)
                if subset_index * self.data.proximity_step > 100:
                    break
                if remaining_pv_to_install > self.threshold:
                    self.undeployed_capacity = remaining_pv_to_install
            logger.info(
                "Sample: %s, Placement: %s, @penetration %s, number of new installable PVs: %s, Remain_to_install: %s kW", 
                deployment,
                self.data.placement,
                self.data.penetration,
                ncs,
                remaining_pv_to_install
            )
        return exisitng_pv
    
    def get_all_remaining_pv_to_install(self):
        total_pv_to_install = self.data.total_load * self.data.penetration / 100
        all_remaining_pv_to_install = total_pv_to_install - self.data.total_existing_pv
        if all_remaining_pv_to_install <= 0:
            minimum_penetration = (total_existing_pv * 100) / max(0.0001, total_load)
            logger.error(
                "Failed to generate PV scenario. The system has more than the target PV penetration. \
                Please increase penetration to at least %s. System exits!", minimum_penetration
            )
            sys.exit(1)
        return all_remaining_pv_to_install

    def get_priority_buses(self):
        priority_buses = list(self.data.existing_pv)
        if len(priority_buses) == len(self.data.bus_totalload):
            logger.warning(
                "Beaware - Sample: %s, Placement: %s, @penetration %s, all buses already have PV installed.",
                self.params.deployment, self.params.placement, self.params.penetration
            )
        return priority_buses
    
    @abc.abstractmethod
    def get_remaining_pv_to_install(self):
        pass
    
    @abc.abstractmethod
    def get_maximum_pv_size(self):
        pass
    
    @abc.abstractmethod
    def get_customer_bus_map(self):
        pass
    
    @abc.abstractmethod
    def get_bus_distance_map(self):
        pass
    
    def generate_pv_size_from_pdf(self, min_size, max_size):
        # TODO: double check, designed in purpose?
        pv_size = max_size
        return pv_size
    
    def add_pv_string(self, bus, pv_size, pv_string):
        if pv_size <= 0:
            return ""
        
        pv_name = f"{pv_type}_{bus.replace('.', '_')}_pv"
        dss.Circuit.SetActiveBus(bus)
        ph = len(bus.split(".")) - 1
        if ph > 1:
            conn = "delta"
            kv = round(dss.Bus.kVBase()*(3)**0.5, 4)
        elif ph == -1 or ph == 4:
            conn = "wye"
            kv = round(dss.Bus.kVBase()*(3)**0.5, 4)
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

    def write_pv_string(self, pv_string):
        # TODO: data
        line = (
            f"// PV Scenario for {total_pv_to_install} kW total size, "
            f"Scenario type {scenario_type}, Deployment {deployment} "
            f"and penetration {penetration}% (PV to load ratio) \n"
        )
        with open(self.pv_file, "w") as f:
            f.write(line)
            f.write(pv_string)

    def get_pv_bus_subset(self, subset_idx):
        max_dist = max(self.data.bus_distance.values())
        min_dist = min(self.data.bus_distance.values())
        if self.data.placement == Placement.CLOSE:
            lb_dist = (subset_idx - 1) * (self.data.proximity_step * max_dist) / 100
            ub_dist = subset_idx * proximity_step * max_dist / 100
        elif self.data.placement == Placement.FAR:
            ub_dist = (100 - (subset_idx - 1) * proximity_step) * max_dist / 100
            lb_dist = (100 - subset_idx * proximity_step) * max_dist / 100
        elif self.data.placement == Placement.RANDOM:
            lb_dist = min_dist
            ub_dist = max_dist
        
        candidate_customers = {
            k: v for k, v in self.data.bus_distance.items() 
            if v > lb_dist and v <= ub_dist
        }
        candidate_customers_array = list(candidate_customers.keys())

        return candidate_customers_array, candidate_customers


class LargePVScenarioGenerator(PVScenarioGeneratorBase):
    
    def get_remaining_pv_to_install(self):
        all_remaining_pv_to_install = self._get_all_remaining_pv_to_install()
        remaining_pv_to_install = all_remaining_pv_to_install + self.undeployed_capacity
        return remaining_pv_to_install
    
    def get_maximum_pv_size(
        self,
        bus: int,
        customer_annual_kwh: dict = None,
        annual_sun_hours: float = None,
        roof_area: dict = None,
        pv_efficiency: float = None,
        max_load_factor: float = 3
    ):
        max_bus_pv_size = 100 * random.randint(1, 50)
        return max_bus_pv_size

    def get_customer_bus_map(self):
        return self.data.hv_bus_map
    
    def get_bus_distance_map(self):
        return self.data.hv_bus_distance


class SmallPVScenarioGenerator(PVScenarioGeneratorBase):

    def get_remaining_pv_to_install(self):
        all_remaining_pv_to_install = self._get_all_remaining_pv_to_install()
        remaining_pv_to_install = all_remaining_pv_to_install + self.undeployed_capacity
        return remaining_pv_to_install
    
    def get_maximum_pv_size(
        self,
        bus: int,
        customer_annual_kwh: dict = None,
        annual_sun_hours: float = None,
        roof_area: dict = None,
        pv_efficiency: float = None,
        max_load_factor: float = 3
    ):
        pv_size_array = [max_load_factor * self.data.bus_totalload[bus]]
        if roof_area and pv_efficiency:
            value = roof_area[bus] * pv_efficiency
            pv_size_array.append(value)
        if customer_annual_kwh and annual_sun_hours:
            value = customer_annual_kwh_dict[bus] / anual_sun_hours
            pv_size_array.append(value)
        max_bus_pv_size = min(pv_size_array)
        return max_bus_pv_size

    def get_customer_bus_map(self):
        return self.data.cutomer_bus_map

    def get_bus_distance_map(self):
        return self.data.customer_bus_distance


class MixtPVScenarioGenerator(PVScenarioGeneratorBase):
    
    def get_remaining_pv_to_install(self):
        all_remaining_pv_to_install = self._get_all_remaining_pv_to_install()
        small_remaining_pv_to_install = (percent_shares[1]/100) * all_remaining_pv_to_install
        large_remaining_pv_to_install_large = (1 - percent_shares[1]/100) * all_remaining_pv_to_install
        

    def get_maximum_pv_size(self):
        pass


class PVDeploymentGeneratorBase(abc.ABC):
    
    def __init__(self, input_path, config, master_file_basename="Master.dss", verbose=False):
        self.input_path = self._ensure_input_path(input_path)
        self.config = config
        self.verbose = verbose
        self.master_file_basename = master_file_basename
    
    @staticmethod
    def _ensure_input_path(input_path):
        if not input_path or not os.path.exists(input_path):
            raise ValueError(f"Invalid input path for PV deployments - {input_path}")
        input_path = input_path.rstrip(os.path.sep)
        return input_path
    
    @abc.abstractmethod
    def get_feeder_paths(self):
        pass
    
    def generate_pv_deployments(self, output_path=None):
        feeder_paths = self.get_feeder_paths()
        output_path = self._ensure_output_path(output_path)
        
        summary = {}
        for feeder_path in feeder_paths:
            result = self._generate_all_scenarios(master_file, output_path)
        
        # TODO
    
    @abc.abstractmethod
    def _ensure_output_path(self, output_path):
        pass
    
    def _get_master_file(self, feeder_path):
        master_file = os.path.join(feeder_path, self.master_file_basename)
        if os.path.exists(master_file):
            return master_file
        
        logger.error("'%s' not found in '%s'. System exits!", basename, directory)
        sys.exit(1)
    
    def _get_pv_deployment_file(self, output_path, placement, deployment, penetration):
        pv_deployment_path = os.path.join(
            output_path,
            "hc_pv_deployments",
            str(self.config.placement),
            str(deployment),
            str(penetration)
        )
        os.makedirs(pv_deployment_path, exist_ok=True)
        pv_deployment_file = os.path.join(pv_deployment_path, "PVDeployments.dss")
        return pv_deployment_file
    
    def iterate_penetrations(self):
        start = self.config.min_penetration
        end = self.config.max_penetration + 1
        step = self.config.penetration_step
        for penetration in range(start, end, step):
            yield penetration
    
    def _generate_all_scenarios(self, feeder_path, output_path):
        master_file = self._get_master_file(feeder_path)
        feeder_name = os.path.basename(feeder_path)
        
        handler = PVDSSHandler(master_file)
        missing, misplaced = handler.check_energy_meter_status()
        if missing:
            handler.place_new_energy_meter()
        elif misplaced:
            handler.move_energy_meter_location()
        elif self.verbose:
            logger.info("Energy meter exists and meter status is good in master file - %s", self.master_file)
        
        # total loads
        total_loads = handler.get_total_loads()
        feeder_stat = {
            "n_buses": handler.get_nbuses(),
            "nload_buses": len(total_loads.bus_totalload.keys()),
            "nzero_load_buses": sum(v == 0 for v in total_loads.bus_totalload.values()),
            "total_load": total_loads.total_load
        }
        if total_loads.total_load <= 0:
            logger.warning("This feeder '%s' has no load, we cannot generate PV scenarios", feeder_name)
            return None, None, feeder_stat
        
        # combined bus distance
        customer_distance = handler.get_customer_distance()
        highv_buses = handler.get_highv_buses()
        if self.verbose:
            logger.info(
                "Feeder Name: %s, Highv DistRange: (%s, %s)",
                feeder_name,
                min(highv_buses.hv_bus_distance.values()),
                max(highv_buses.hv_bus_distance.values())
            )
        combined_bus_distance = deepcopy(highv_buses.hv_bus_distance)
        combined_bus_distance.update(customer_distance.bus_distance)
        if max(combined_bus_distance.values()) == 0:
            logger.error(
                "Check your feeder model for '%s'.\n\
                The bus distance array does not look correct. Maximum bus distance = 0.00 km",
                feeder_name
            )
            sys.exit(1)
        
        # existing pvs
        base_existing_pvs = handler.get_existing_pvs()
        nbase_pv_buses = len([b for b, v in base_existing_pvs.base_existing_pv.items() if v > 0])
        pcent_base_pv = (base_existing_pvs.total_existing_pv * 100) / max(0.0000001, total_loads.total_load)
        feeder_stat.update({
            "nbase_pv_buses": nbase_pv_buses, 
            "pcent_base_pv": pcent_base_pv,
            "total_base_pv": base_existing_pvs.total_existing_pv
        })
        if pcent_base_pv > self.params.max_penetration:
            logger.warning("This feeder has no load, we cannot generate PV scenarios")
            return None, None, feeder_stat
        
        average_pv_distance = {}
        for deployment in range(1, self.config.deployment_number+1):
            existing_pvs = handler.get_existing_pvs()
            total_existing_pv = existing_pvs.total_existing_pv
            existing_pv = existing_pvs.existing_pv
            for penetration in self.iterate_penetrations():
                total_existing_pv = sum(existing_pv.values())
                pv_deployment_file = self._get_pv_deployment_file(
                    output_path=output_path,
                    placement=self.data.placement,
                    deployment=deployment,
                    penetration=penetration
                )
                data = {
                    "base_existing_pv": base_existing_pvs.existing_pv,
                    "existing_pv": existing_pv,
                    # TODO: other inputs
                }
                existing_pv = self.generate_pv_scenario(data=data)
                avg_dist = compute_average_pv_distance(combined_bus_distance, existing_pv)
                key = (self.config.placement, deployment, penetration)
                average_pv_distance[key] = [self.config.placement, deployment, penetration, avg_dist]
        
        return feeder_stat
    
    def _generate_pv_scenario(self, data):
        category = ScenarioCategory(self.data.category)
        data = SimpleNamespace(**data)
        generator_class = PV_SCENARIO_GENERATOR_MAPPING[category]
        generator = generator_class(data, verbose=self.verbose)
        result = generator.generate_pv_scenario()
        return result
    
    def compute_average_pv_distance(self, bus_distance, existing_pv):
        slack_dico = {
            k: bus_distbus_distanceance_dict[k]
            for k, v in existing_pv.items()
            if v > 0 and k in list(bus_distance.keys())
        }
        average_pv_distance = np.mean(np.array(list(slack_dico.values())))
        return average_pv_distance


class FeederPVDeploymentGenerator(PVDeploymentGeneratorBase):
    
    def get_feeder_paths(self):
        """Given a feeder path, return"""
        if not isinstance(self.input_path, list):
            feeder_paths = [self.input_path]
        return feeder_paths

    def _ensure_output_path(self, output_path):
        if not output_path:
            output_path = self.input_path
        return output_path


class SubstationPVDeploymentGenerator(PVDeploymentGeneratorBase):
    
    def get_feeder_paths(self):
        """Given a substation path, return all feeder paths in the substation"""
        feeder_names = next(os.walk(self.input_path))[1]
        feeder_paths = [
            os.path.join(self.input_path, feeder_name)
            for feeder_name in feeder_names
        ]
        return feeder_paths

    def _ensure_output_path(self, output_path):
        if not output_path:
            output_path = os.path.dirname(self.input_path)
        return output_path


class RegionPVDeploymentGenerator(PVDeploymentGeneratorBase):
    
    def get_feeder_paths(self):
        """Given a region path, return all feeder paths in the region"""
        feeder_paths = []
        substation_names = next(os.walk(self.input_path))[1]
        for substation_name in substation_names:
            substation_path = os.path.join(self.input_path, substation_name)
            feeder_names = next(os.walk(substation_path))[1]
            feeder_paths.extend([
                os.path.join(self.input_path, feeder_name)
                for feeder_name in feeder_names
            ])
        return feeder_paths

    def _ensure_output_path(self, output_path):
        if not output_path:
            output_path = os.path.dirname(self.input_path)
        return output_path
