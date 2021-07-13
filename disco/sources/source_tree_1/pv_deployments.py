import abc
import enum
import json
import logging
import os
import random
import shutil
import sys
from copy import deepcopy
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from typing import Optional, Generator, Tuple, Sequence

import opendssdirect as dss
from filelock import SoftFileLock
from unidecode import unidecode

from disco.enums import Placement

logger = logging.getLogger(__name__)

PV_DEPLOYMENT_DIRNAME = "hc_pv_deployments"
PV_SYSTEMS_FILENAME = "PVSystems.dss"
PV_SHAPES_FILENAME = "PVShapes.dss"
PV_CONFIG_FILENAME = "pv_config.json"
PV_INSTALLATION_TOLERANCE = 1.0e-10


class DeploymentHierarchy(enum.Enum):
    FEEDER = "feeder"
    SUBSTATION = "substation"
    REGION = "region"


class DeploymentCategory(enum.Enum):
    MIXED = "mixed"
    SMALL = "small"
    LARGE = "large"


def get_subdir_names(input_path: str) -> list:
    """Given an input path, return directory names under the path.
    Used to parse substation names, and feeder names under input path.
    """
    assert os.path.exists(input_path), f"Path does not exist - {input_path}"
    subdir_names = next(os.walk(input_path))[1]
    return subdir_names


class PVDSSInstance:
    """OpenDSS file handler for PV deployments."""

    def __init__(self, master_file):
        self.master_file = master_file

    @property
    def feeder_name(self):
        return os.path.basename(os.path.os.path.dirname(self.master_file))

    def convert_to_ascii(self) -> None:
        """Convert unicode data in ASCII characters for representation"""
        logger.info("Convert master file - %s", self.master_file)
        data = Path(self.master_file).read_text()
        updated_data = unidecode(data)
        with open(self.master_file, "w") as f:
            f.write(updated_data)

    def load_feeder(self) -> None:
        """OpenDSS redirect master DSS file"""
        dss.run_command("Clear")
        logger.info("OpenDSS loads feeder - %s", self.master_file)
        r = dss.run_command(f"Redirect {self.master_file}")
        if r != "":
            logger.exception("OpenDSSError: %s. Feeder: %s", str(r), self.master_file)
            raise

    def search_head_line(self) -> None:
        """Search head line from DSS topology"""
        flag = dss.Topology.First()
        while flag > 0:
            if "line" in dss.Topology.BranchName().lower():
                return dss.Topology.BranchName()
            flag = dss.Topology.Next()
        assert False, "Failed to search head line."

    def ensure_energy_meter(self) -> bool:
        missing, misplaced = self.check_energy_meter_status()
        if missing:
            logger.info("Energy meter missing in master file - %s", self.master_file)
            self.place_new_energy_meter()
            return True

        if misplaced:
            logger.info("Energy meter location is not correct in master file - %s", self.master_file)
            self.move_energy_meter_location()
            return True

        logger.info("Energy meter exists and meter status is good in master file - %s", self.master_file)
        return False

    def check_energy_meter_status(self) -> Tuple[bool, bool]:
        """Check if energy meter in dss is missing or misplaced"""
        data = Path(self.master_file).read_text()
        missing = 'New EnergyMeter' not in data
        misplaced = False
        if not missing:
            head_line = self.search_head_line()
            meter_location = self._parse_meter_location(data)
            misplaced = meter_location != head_line

        return missing, misplaced

    @staticmethod
    def _parse_meter_location(data: str) -> str:
        """
        Parameters
        ----------
        data: str, the string data read from master file.

        Returns
        -------
        str:
            meter location
        """
        # TODO: Use regex
        return data.split("\nNew EnergyMeter")[1].split("element=")[1].split("\n")[0].split(" ")[0]

    def place_new_energy_meter(self) -> None:
        """Place new energy meter if it's missing from master dss file"""
        head_line = self.search_head_line()
        data = Path(self.master_file).read_text()
        temp = data.split('\nRedirect')[-1].split('\n')[0]
        updated_data = data.replace(temp, temp + f"\nNew EnergyMeter.m1 element={head_line}")
        with open(self.master_file, "w") as f:
            f.write(updated_data)
        logger.info("New energy meter was placed into master file - %s", self.master_file)

    def move_energy_meter_location(self) -> None:
        """Move energy meter location if it's misplaced in master dss file"""
        logger.info("Moving energy meter in master file - %s", self.master_file)
        head_line = self.search_head_line()
        data = Path(self.master_file).read_text()
        meter_location = self._parse_meter_location(data)
        updated_data = data.replace(meter_location, head_line)
        updated_data += f"\n!Moved energy meter from {meter_location} to {head_line}"
        with open(self.master_file, "w") as f:
            f.write(updated_data)
        logger.info("Moved energy meter from %s to %s in master file - %s", meter_location, head_line, self.master_file)

    def redirect_pv_shapes(self, pv_shapes_file) -> bool:
        """Update master file and redirect PVShapes.dss"""
        if not os.path.exists(pv_shapes_file):
            return False

        pv_shapes = os.path.basename(pv_shapes_file)
        index = 0
        with open(self.master_file, "r") as f:
            data = f.readlines()

        for i, line in enumerate(data):
            line = line.strip().lower()
            if line.startswith("redirect"):
                index = i + 1
            if line == f"redirect {pv_shapes}".lower():
                logger.info("Skip %s redirect, it already exists.", pv_shapes)
                return False

        assert index > 0, f"There must be 'Redirect' in {self.master_file}"

        logger.info("Update master file %s to redirect %s", self.master_file, pv_shapes)
        data.insert(index, f"Redirect {pv_shapes}\n")
        with open(self.master_file, "w") as f:
            f.writelines(data)
        return True

    def get_total_loads(self) -> SimpleNamespace:
        """Return total loads"""
        result = SimpleNamespace(
            total_load=0,
            load_dict={},
            customer_bus_map={},
            bus_load={},
            bus_totalload={}
        )
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
        result = SimpleNamespace(load_distance={}, bus_distance={})
        flag = dss.Loads.First()
        while flag > 0:
            dss.Circuit.SetActiveBus(dss.Properties.Value("bus1"))
            result.load_distance[dss.Loads.Name()] = dss.Bus.Distance()
            result.bus_distance[dss.Properties.Value("bus1")] = dss.Bus.Distance()
            flag = dss.Loads.Next()
        return result

    def get_highv_buses(self, kv_min: int = 1) -> SimpleNamespace:
        """Return highv buses"""
        result = SimpleNamespace(bus_kv={}, hv_bus_distance={})
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
        result = SimpleNamespace(total_existing_pv=0, existing_pv={})
        flag = dss.PVsystems.First()
        while flag > 0:
            bus = dss.Properties.Value("bus1")
            try:
                result.existing_pv[bus] += dss.PVsystems.Pmpp()
            except KeyError:
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
            "n_buses": dss.Circuit.NumBuses(),
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


class PVScenarioGeneratorBase(abc.ABC):

    def __init__(self, feeder_path: str, config: SimpleNamespace) -> None:
        """
        Initialize PV scenario generator class

        Parameters
        ----------
        feeder_path: str, the input path of a feeder model.
        config: SimpleNamespace, the pv deployment config namespace.
        """
        self.feeder_path = feeder_path
        self.substation_path = os.path.dirname(feeder_path)
        self.config = config
        self.current_cycle = None

    @property
    @abc.abstractmethod
    def deployment_cycles(self) -> list:
        """Return a list of cicyles for generating pv scenarios"""

    def get_feeder_name(self) -> str:
        """Return the feeder name"""
        return os.path.basename(self.feeder_path)

    def get_master_file(self, input_path: str) -> Optional[str]:
        """Return the full path of master file"""
        master_file = os.path.join(input_path, self.config.master_filename)
        if not os.path.exists(master_file):
            logger.exception("'%s' not found in '%s'. System exits!", self.config.master_filename, self.feeder_path)
            raise
        return master_file

    def load_pvdss_instance(self) -> PVDSSInstance:
        """Setup DSS handler for master dss file processing"""
        master_file = self.get_master_file(self.feeder_path)
        pv_shapes_file = self.get_pv_shapes_file(self.feeder_path)
        pvdss_instance = PVDSSInstance(master_file)
        try:
            lock_file = master_file + ".lock"
            with SoftFileLock(lock_file=lock_file, timeout=300):  # Timeout for loading master file
                pvdss_instance.convert_to_ascii()
                pvdss_instance.load_feeder()
                flag = pvdss_instance.ensure_energy_meter()
                if flag:
                    pvdss_instance.load_feeder()  # Need to reload after master file updated.
                flag = pvdss_instance.redirect_pv_shapes(pv_shapes_file)
                if flag:
                    pvdss_instance.load_feeder()
        except Exception as error:
            logger.exception("Failed to load master file - %s", master_file)
            raise
        return pvdss_instance

    def redirect_substation_pv_shapes(self):
        """Redirect PVShapes.dss in Master.dss in substation"""
        master_file = self.get_master_file(self.substation_path)
        pvdss_instance = PVDSSInstance(master_file)
        
        try:
            lock_file = master_file + ".lock"
            with SoftFileLock(lock_file=lock_file, timeout=300):  # Timeout for loading master file
                pv_shapes_file = self.get_pv_shapes_file(self.substation_path)
                pvdss_instance.redirect_pv_shapes(pv_shapes_file)
        except Exception as error:
            logger.exception("Failed redirect '%s' in master file - %s", pv_shapes_file, master_file)
            raise
    
    def deploy_all_pv_scenarios(self) -> dict:
        """Given a feeder path, generate all PV scenarios for the feeder"""
        feeder_name = self.get_feeder_name()
        pvdss_instance = self.load_pvdss_instance()

        # total load
        total_loads = pvdss_instance.get_total_loads()
        feeder_stats = pvdss_instance.get_feeder_stats(total_loads)
        if total_loads.total_load <= 0:
            feeder_stats_string = json.dumps(feeder_stats.__dict__)
            logger.exception(
                "Failed to generate PV scenarios on feeder - %s, stats: %s",
                feeder_name, feeder_stats_string
            )
            raise

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
            feeder_stats_string = json.dumps(feeder_stats.__dict__)
            logger.exception(
                "Failed to generate PV scenarios on feeder - %s. \
                The existing PV amount exceeds the maximum penetration level of %s\%. Stats: %s",
                feeder_name, self.cofig.max_penetration, feeder_stats_string
            )
            raise

        snum = self.config.sample_number + 1
        start = self.config.min_penetration
        end = self.config.max_penetration + 1
        step = self.config.penetration_step
        for sample in range(1, snum):
            existing_pv = deepcopy(base_existing_pv)
            pv_records = {}
            for penetration in range(start, end, step):
                data = SimpleNamespace(
                    base_existing_pv=base_existing_pv,
                    total_load=total_loads.total_load,
                    load_dict=total_loads.load_dict,
                    bus_totalload=total_loads.bus_totalload,
                    total_existing_pv=sum(existing_pv.values()),
                    existing_pv=existing_pv,
                    hv_bus_distance=highv_buses.hv_bus_distance,
                    customer_bus_distance=customer_distance.bus_distance,
                    hv_bus_map=hv_bus_map,
                    customer_bus_map=total_loads.customer_bus_map,
                    bus_kv=highv_buses.bus_kv,
                    pv_records=pv_records,
                    penetration=penetration,
                    sample=sample
                )
                existing_pv, pv_records = self.deploy_pv_scenario(data)

        return feeder_stats.__dict__

    def get_output_root_path(self):
        """Return the root path of PV depployments"""
        return os.path.join(self.feeder_path, PV_DEPLOYMENT_DIRNAME)

    def get_output_placement_path(self) -> str:
        """Return the placement path of PV deployments"""
        root_path = self.get_output_root_path()
        placement_path = os.path.join(root_path, self.config.placement)
        return placement_path

    def get_pv_deployments_file(self, sample: int, penetration: int) -> str:
        """Return the path of PV depployment file"""
        placement_path = self.get_output_placement_path()
        penetration_path = os.path.join(placement_path, str(sample), str(penetration))
        os.makedirs(penetration_path, exist_ok=True)
        pv_deployments_file = os.path.join(penetration_path, PV_SYSTEMS_FILENAME)
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
                            # TODO: pv_added_capacity no effect now
                            pv_added_capacity = 0
                            remaining_pv_to_install -= pv_added_capacity
                            pv_string = self.add_pv_string(bus, pv_type.value, pv_size, pv_string)
                            pv_records[bus] = pv_size
                            existing_pv[bus] = pv_size

                subset_idx += 1
                candidate_bus_array = self.get_pv_bus_subset(bus_distance, subset_idx, priority_buses)
                if subset_idx > (100 / self.config.proximity_step):
                    logger.exception("No %s file created on feeder - %s", PV_SYSTEMS_FILENAME, self.feeder_path)
                    raise

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
                        pv_size = min(random_pv_size, remaining_pv_to_install)
                        pv_string = self.add_pv_string(picked_candidate, pv_type.value, pv_size, pv_string)
                        pv_records[picked_candidate] = pv_size
                        existing_pv[picked_candidate] = pv_size
                        pv_added_capacity = pv_size
                        remaining_pv_to_install -= pv_added_capacity
                        ncs += 1
                    candidate_bus_array.remove(picked_candidate)

                    if abs(remaining_pv_to_install) <= PV_INSTALLATION_TOLERANCE:
                        break

                if len(pv_records) > 0:
                    self.write_pv_string(pv_string, data)

                if remaining_pv_to_install > PV_INSTALLATION_TOLERANCE:
                    undeployed_capacity = remaining_pv_to_install
                elif len(pv_records) > 0 and len(pv_string.split("New PVSystem.")) > 0:
                    self.write_pv_string(pv_string, data)

                logger.debug(
                    "Sample: %s, Placement: %s, @penetration %s, number of new installable PVs: %s, Remain_to_install: %s kW",
                    data.sample,
                    self.config.placement,
                    data.penetration,
                    ncs,
                    remaining_pv_to_install
                )

                if subset_idx * self.config.proximity_step > 100:
                    break

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
            logger.exception(
                "Failed to generate PV scenarios on feeder - %s. \
                The system has more than the target PV penetration. \
                Please increase penetration to at least %s.", self.feeder_path, minimum_penetration
            )
            raise
        return all_remaining_pv_to_install

    def get_priority_buses(self, data: SimpleNamespace) -> list:
        """Return a list of priority buses."""
        priority_buses = list(data.existing_pv.keys())
        if len(priority_buses) == len(data.bus_totalload):
            logger.warning(
                "Beaware - Sample: %s, Placement: %s, @penetration %s, all buses already have PV installed.",
                data.sample, self.config.placement, data.penetration
            )
        return priority_buses

    @abc.abstractmethod
    def get_categorical_remaining_pvs(self, data: SimpleNamespace) -> dict:
        """Return remaining sall, large PV to install"""

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
        """Return maximum pv size"""

    @staticmethod
    def generate_pv_size_from_pdf(min_size: float, max_size: float, pdf: Sequence = None) -> float:
        # TODO: A placeholder function for later update
        pv_size = max_size
        return pv_size

    @staticmethod
    def add_pv_string(bus: str, pv_type: str, pv_size: float, pv_string: str) -> str:
        """Add PV string to exiting string"""
        if round(pv_size, 3) <= 0:
            return pv_string

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
            f"Vmaxpu=1.2\n"
        )
        pv_string += new_pv_string
        return pv_string

    def write_pv_string(self, pv_string: str, data: SimpleNamespace) -> None:
        """Write PV string to PV deployment file."""
        total_pv = self.get_total_pv(data)
        pv_deployments_file = self.get_pv_deployments_file(data.sample, data.penetration)
        line = (
            f"// PV Scenario for {total_pv} kW total size, "
            f"Scenario type {self.config.placement}, Sample {data.sample} "
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
            if v >= lb_dist and v <= ub_dist
        }
        candidate_bus_array = [b for b in candidate_bus_map if not b in priority_buses]
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

    def get_pv_shapes_file(self, input_path: str) -> str:
        """Return the loadshapes file in feeder path"""
        pv_shapes_file = os.path.join(input_path, PV_SHAPES_FILENAME)
        return pv_shapes_file

    def create_all_pv_configs(self) -> None:
        """Create PV configs JSON file"""
        root_path = self.get_output_root_path()
        if not os.path.exists(root_path):
            logger.info("Deployment path %s not exis under %s", PV_DEPLOYMENT_DIRNAME, self.feeder_path)
            return []

        config_files = []
        pv_shapes_file = self.get_pv_shapes_file(self.feeder_path)
        placement_path = self.get_output_placement_path()
        if not os.path.exists(placement_path):
            return []

        samples = get_subdir_names(placement_path)
        for sample in samples:
            sample_path = os.path.join(placement_path, sample)
            pv_systems = set()
            pv_configurations = []
            for pen in os.listdir(sample_path):
                pen_dir = os.path.join(sample_path, pen)
                if not os.path.isdir(pen_dir):
                    continue
                pv_deployments_file = os.path.join(pen_dir, PV_SYSTEMS_FILENAME)
                if os.path.exists(pv_deployments_file):
                    pv_configurations += self.assign_profile(pv_deployments_file, pv_shapes_file, pv_systems)
            final = {'pv_systems': pv_configurations}
            pv_config_file = self.save_pv_config(final, sample_path)
            config_files.append(pv_config_file)
        logger.info("%s PV config files generated in placement - %s", len(config_files), placement_path)
        return config_files

    def assign_profile(self, pv_deployments_file: str, pv_shapes_file: str, pv_systems: set, limit: int = 5) -> dict:
        """Assign PV profile to PV systems."""
        pv_dict = self.get_pvsys(pv_deployments_file)
        shape_list = self.get_shape_list(pv_shapes_file)
        pv_conf = []
        for pv_name, pv_value in pv_dict.items():
            if pv_name in pv_systems:
                continue
            if float(pv_value) > limit:
                control_name = "volt-var"
            else:
                control_name = "pf1"
            random.shuffle(shape_list)
            pv_profile = shape_list[0]
            pv_conf.append({
                "name": pv_name,
                "pydss_controller": {
                    "controller_type": "PvController",
                    "name": control_name
                },
                "pv_profile": pv_profile
            })
            pv_systems.add(pv_name)
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

    def get_shape_list(self, pv_shapes_file: str) -> list:
        """Return a list of loadshapes"""
        shape_list = []
        with open(pv_shapes_file) as f:
            slines = f.readlines()
            for line in slines:
                if "loadshape" in line.lower():
                    shape_list.append(line.lower().split("loadshape.")[1].split(' ')[0])
        return shape_list

    def save_pv_config(self, pv_config: dict, sample_path: str) -> None:
        """Save PV configuration to JSON file"""
        pv_config_file = os.path.join(sample_path, PV_CONFIG_FILENAME)
        with open(pv_config_file, "w") as f:
            json.dump(pv_config, f, indent=2)
        logger.info("PV config file generated - %s", pv_config_file)
        return pv_config_file


class LargePVScenarioGenerator(PVScenarioGeneratorBase):

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


class SmallPVScenarioGenerator(PVScenarioGeneratorBase):

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
    def get_maximum_pv_size(cls, bus: str, data: SimpleNamespace, max_load_factor: float = 3.1,  **kwargs) -> float:
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


class MixedPVScenarioGenerator(PVScenarioGeneratorBase):

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
            return LargePVScenarioGenerator.get_maximum_pv_size(bus, data, **kwargs)
        if self.current_cycle == DeploymentCategory.SMALL:
            return SmallPVScenarioGenerator.get_maximum_pv_size(bus, data, **kwargs)
        return None


def get_pv_scenario_generator(feeder_path: str, config: SimpleNamespace):
    """Return a PV scenario generator instnace"""
    pv_scenario_generator_mapping = {
        DeploymentCategory.SMALL: SmallPVScenarioGenerator,
        DeploymentCategory.LARGE: LargePVScenarioGenerator,
        DeploymentCategory.MIXED: MixedPVScenarioGenerator
    }
    category = DeploymentCategory(config.category)
    generator_class = pv_scenario_generator_mapping[category]
    generator = generator_class(feeder_path, config)
    return generator


class PVDataStorage:
    """A class for handling PV data storage on file system"""

    def __init__(self, input_path: str, hierarchy: DeploymentHierarchy):
        self.input_path = input_path
        self.hierarchy = hierarchy

    def get_feeder_paths(self) -> list:
        """Given an input path, return a list of feeder paths"""
        if self.hierarchy == DeploymentHierarchy.FEEDER:
            paths = self._search_feeder_input()
        elif self.hierarchy == DeploymentHierarchy.SUBSTATION:
            paths = self._search_substation_input()
        elif self.hierarchy == DeploymentHierarchy.REGION:
            paths = self._search_region_input()
        return paths

    def _search_feeder_input(self) -> list:
        """Search feeder input path, return it as a list"""
        feeder_paths = [self.input_path]
        return feeder_paths

    def _search_substation_input(self) -> list:
        """Search substation input path, return all feeder paths in substation"""
        feeder_names = get_subdir_names(self.input_path)
        feeder_paths = [
            os.path.join(self.input_path, feeder_name)
            for feeder_name in feeder_names
        ]
        return feeder_paths

    def _search_region_input(self) -> list:
        """Search region input path, return all feeder paths in region"""
        opendss_path = os.path.join(
            self.input_path,
            "solar_none_batteries_none_timeseries",
            "opendss"
        )
        feeder_paths = []
        substation_names = get_subdir_names(opendss_path)
        for substation_name in substation_names:
            substation_path = os.path.join(opendss_path, substation_name)
            feeder_names = get_subdir_names(substation_path)
            feeder_paths.extend([
                os.path.join(opendss_path, substation_name, feeder_name)
                for feeder_name in feeder_names
            ])
        return feeder_paths

    def get_deployment_path(self, feeder_path: str) -> str:
        """Return the deployment path"""
        path = os.path.join(feeder_path, PV_DEPLOYMENT_DIRNAME)
        if os.path.exists(path):
            return path
        return None

    def get_placement_paths(self, feeder_path: str, placement: Placement = None):
        """Return the placement path in deployment"""
        paths = []
        placements = [placement] if placement else [p for p in Placement]
        deployment_path = self.get_deployment_path(feeder_path)
        if not deployment_path:
            return paths

        for p in placements:
            path = os.path.join(deployment_path, p.value)
            if os.path.exists(path):
                paths.append(path)
        return paths

    def get_sample_paths(self, feeder_path: str, placement: Placement = None):
        """Return the sample path in deployment"""
        paths = []
        placement_paths = self.get_placement_paths(feeder_path, placement)
        for placement_path in placement_paths:
            samples = os.listdir(placement_path)
            sample_paths = [os.path.join(placement_path, str(s)) for s in samples]
            paths.extend(sample_paths)
        return paths

    def get_pv_config_file(self, sample_path: str):
        """Return PV config file"""
        config_file = os.path.join(sample_path, PV_CONFIG_FILENAME)
        return config_file


class PVDeploymentManager(PVDataStorage):

    def __init__(self,input_path: str, hierarchy: DeploymentHierarchy, config: SimpleNamespace) -> None:
        """
        Initialize pv deployment manager class

        Parameters
        ----------
        hierarchy: DeploymentHierarchy, the predefined hierarchy
        input_path: str, the input path of raw dss data for generating pv deployments.
        config: SimpleNamespace, the pv deployment configuration namespace.
        """
        super().__init__(input_path, hierarchy)
        self.config = config

    def generate_pv_deployments(self) -> dict:
        """Given input path, generate pv deployments"""
        summary = {}
        feeder_paths = self.get_feeder_paths()
        for feeder_path in feeder_paths:
            generator = get_pv_scenario_generator(feeder_path, self.config)
            generator.redirect_substation_pv_shapes()
            feeder_stats = generator.deploy_all_pv_scenarios()
            summary[feeder_path] = feeder_stats
        return summary

    def remove_pv_deployments(self, placement: Placement = None) -> list:
        """Given input path, remove all pv deployments of all placements"""
        removed = []
        feeder_paths = self.get_feeder_paths()
        for feeder_path in feeder_paths:
            if placement is None:
                deployment_path = self.get_deployment_path(feeder_path)
                if not deployment_path:
                    continue
                shutil.rmtree(deployment_path)
                removed.append(deployment_path)
            else:
                placement_paths = self.get_placement_paths(feeder_path, placement)
                for placement_path in placement_paths:
                    shutil.rmtree(placement_path)
                    removed.append(placement_path)
        return removed

    def check_pv_deployments(self, placement: Placement = None) -> SimpleNamespace:
        """Given input path, check if all pv deployments status"""
        result = SimpleNamespace(placements={}, samples={}, penetrations={})
        feeder_paths = self.get_feeder_paths()
        for feeder_path in feeder_paths:
            missing_placements = self.get_missing_placements(feeder_path, placement)
            if missing_placements:
                result.placements[feeder_path] = missing_placements
            missing_samples = self.get_missing_samples(feeder_path, placement)
            if missing_samples:
                result.samples[feeder_path] = missing_samples
            missing_penetrations = self.get_missing_penetrations(feeder_path, placement)
            if missing_penetrations:
                result.penetrations[feeder_path] = missing_penetrations
        return result

    def get_missing_placements(self, feeder_path: str, placement: Placement = None) -> dict:
        """Return missing placement information in PV deployments on feeder."""
        desired_placements = {p.value for p in Placement}
        deployment_path = self.get_deployment_path(feeder_path)
        existing_placements = set(os.listdir(deployment_path))
        missing_placements = list(desired_placements.difference(existing_placements))
        if placement.value not in missing_placements:
            return []
        return [placement.value]

    def get_missing_samples(self, feeder_path: str, placement: Placement = None) -> dict:
        """Return missing sample information in PV deployments on feeder."""
        desired_samples = {str(i) for i in range(1, self.config.sample_number + 1)}
        placement_paths = self.get_placement_paths(feeder_path, placement)
        result = {}
        for placement_path in placement_paths:
            placement = os.path.basename(placement_path)
            exsiting_samples = set(os.listdir(placement_path))
            missing_samples = list(desired_samples.difference(exsiting_samples))
            if missing_samples:
                result[placement] = missing_samples
        return result

    def get_missing_penetrations(self, feeder_path: str, placement: Placement = None):
        """Return missing penetration information in PV deployments on feeder."""
        desired_penetrations = {str(i) for i in range(
            self.config.min_penetration,
            self.config.max_penetration + 1,
            self.config.penetration_step
        )}
        result = {}
        sample_paths = self.get_sample_paths(feeder_path, placement=placement)
        for sample_path in sample_paths:
            placement, sample = sample_path.split(os.path.sep)[-2:]
            existing_penetrations = os.listdir(sample_path)
            if placement not in result:
                result[placement] = {}
            missing_penetrations = list(desired_penetrations.difference(existing_penetrations))
            if missing_penetrations:
                result[placement][sample] = missing_penetrations
        clean_result = deepcopy(result)
        for placement in result:
            if not result[placement]:
                clean_result.pop(placement)
        return clean_result


class PVConfigManager(PVDataStorage):

    def __init__(self,input_path: str, hierarchy: DeploymentHierarchy, config: SimpleNamespace) -> None:
        """
        Initialize pv config manager class

        Parameters
        ----------
        hierarchy: DeploymentHierarchy, the predefined hierarchy
        input_path: str, the input path of raw dss data for generating pv deployments.
        config: SimpleNamespace, the pv deployment configuration namespace.
        """
        super().__init__(input_path, hierarchy)
        self.config = config

    def generate_pv_configs(self) -> list:
        """Generate pv config JSON files based on PV deployments"""
        config_files = []
        feeder_paths = self.get_feeder_paths()
        for feeder_path in feeder_paths:
            generator = get_pv_scenario_generator(feeder_path, self.config)
            result = generator.create_all_pv_configs()
            config_files.extend(result)
        return config_files

    def remove_pv_configs(self, placement: Placement = None) -> list:
        """Remove pv config JSON files from PV deployments"""
        removed = []
        feeder_paths = self.get_feeder_paths()
        for feeder_path in feeder_paths:
            sample_paths = self.get_sample_paths(feeder_path, placement)
            for sample_path in sample_paths:
                config_file = self.get_pv_config_file(sample_path)
                if os.path.exists(config_file):
                    os.remove(config_file)
                    removed.append(config_file)
        return removed

    def check_pv_configs(self, placement: Placement = None) -> dict:
        """Check pv config existence in pv deployments"""
        total_missing = {}
        feeder_paths = self.get_feeder_paths()
        for feeder_path in feeder_paths:
            missing = {}
            sample_paths = self.get_sample_paths(feeder_path, placement)
            for sample_path in sample_paths:
                pv_config_file = os.path.join(sample_path, PV_CONFIG_FILENAME)
                sample = os.path.basename(sample_path)
                if os.path.exists(pv_config_file):
                    continue
                if placement.value in missing:
                    missing[placement.value].append(sample)
                else:
                    missing[placement.value] = [sample]
            if missing:
                total_missing[feeder_path] = deepcopy(missing)
        return total_missing
