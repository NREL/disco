import abc
import enum
import json
import logging
import os
import random
import re
import shutil
from collections import defaultdict
from copy import deepcopy
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from tempfile import NamedTemporaryFile
from types import SimpleNamespace
from typing import Optional, Tuple, Sequence

import numpy as np
import opendssdirect as dss
from filelock import SoftFileLock

from jade.utils.run_command import check_run_command
from jade.utils.utils import load_data, dump_data
from disco.common import LOADS_SUM_GROUP_FILENAME, PV_SYSTEMS_SUM_GROUP_FILENAME
from disco.enums import Placement

logger = logging.getLogger(__name__)


PV_SYSTEMS_FILENAME = "PVSystems.dss"
PV_SHAPES_FILENAME = "PVShapes.dss"
PV_CONFIG_FILENAME = "pv_config.json"
PV_INSTALLATION_TOLERANCE = 1.0e-10

LOADS_FILENAME = "Loads.dss"
ORIGINAL_LOADS_FILENAME = "Original_Loads.dss"
TRANSFORMED_LOADS_FILENAME = "PV_Loads.dss"

LOADSHAPES_FILENAME = "LoadShapes.dss"
ORGINAL_LOADSHAPES_FILENAME = "Original_LoadShapes.dss"


class DeploymentHierarchy(enum.Enum):
    FEEDER = "feeder"
    SUBSTATION = "substation"
    REGION = "region"
    CITY = "city"


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
    
    # Ignore these folder names
    ignored_names = {"subtransmission", "aggregate", "analysis", "hc_pv_deployments", "zip"}
    clean_names = [name for name in subdir_names if name not in ignored_names]
    return clean_names


class PVDSSInstance:
    """OpenDSS file handler for PV deployments."""

    def __init__(self, master_file):
        self.master_file = master_file

    @property
    def feeder_name(self) -> str:
        """Parse feeder name from master file path"""
        return os.path.basename(os.path.dirname(self.master_file))

    @property
    def feeder_path(self) -> str:
        """Parse feeder path from master file path"""
        return os.path.dirname(self.master_file)

    # def convert_to_ascii(self) -> None:
    #     """Convert unicode data in ASCII characters for representation"""
    #     logger.info("Convert master file - %s", self.master_file)
    #     data = Path(self.master_file).read_text()
    #     updated_data = unidecode(data)
    #     with open(self.master_file, "w") as f:
    #         f.write(updated_data)

    def disable_loadshapes_redirect(self) -> None:
        """To comment out 'Redirect LoadShapes.dss' in Master.dss file
        
        Redirect LoadShapes.dss is time consuming during OpenDSS loads the feeder, which
        make the PV deployments take a long to run. However, LoadShapes is not in use during 
        PV deployments. To speed up, we'll comment out the redirect and revert it back after
        PV deployments finished.
        """
        logger.info("Disable LoadShapes.dss redirect in master file - %s", self.master_file)
        
        redirected = False
        updated_data = []
        with open(self.master_file, "r") as f:
            for line in f.readlines():
                if line.lower().startswith("redirect loadshapes.dss"):
                    line = "!" + line
                    redirected = True
                updated_data.append(line)

        if not redirected:
            return
        
        with open(self.master_file, "w") as fw:
            fw.writelines(updated_data)

    def load_feeder(self) -> None:
        """OpenDSS redirect master DSS file"""
        dss.Text.Command("Clear")
        logger.info("OpenDSS loads feeder - %s", self.master_file)
        r = dss.Text.Command(f"Redirect '{self.master_file}'")
        if r is not None:
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
        self.customer_types = {}

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
        pvdss_instance = PVDSSInstance(master_file)
        try:
            lock_file = master_file + ".lock"
            with SoftFileLock(lock_file=lock_file, timeout=900):
                # This code was ported from a different location. The functionality
                # should not be needed. Leaving it commented-out in case this assumption
                # is incorrect.
                # unidecode is no longer being installed with disco.
                # pvdss_instance.convert_to_ascii()
                pvdss_instance.disable_loadshapes_redirect()
                pvdss_instance.load_feeder()
                flag = pvdss_instance.ensure_energy_meter()
                if flag:
                    pvdss_instance.load_feeder()  # Need to reload after master file updated.
        except Exception as error:
            logger.exception("Failed to load master file - %s", master_file)
            raise
        return pvdss_instance

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
            random.seed(self.config.random_seed + sample)
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

    def get_metadata_directory(self):
        """Return the metadata directory of the feeder"""
        metadata_directory = os.path.join(self.feeder_path, "metadata")
        os.makedirs(metadata_directory, exist_ok=True)
        return metadata_directory

    def get_pv_deployments_path(self):
        """Return the root path of PV deployments"""
        return os.path.join(self.feeder_path, self.config.pv_deployments_dirname)

    def get_deployment_placement_paths(self) -> str:
        """Return the placement path of PV deployments"""
        root_path = self.get_pv_deployments_path()
        if self.config.placement:
            placement_paths = [os.path.join(root_path, self.config.placement)]
        else:
            placement_paths = [
                os.path.join(root_path, p.value) for p in Placement
            ]
        return placement_paths

    def get_pv_systems_file(self, sample: int, penetration: int) -> str:
        """Return the path of PV depployment file"""
        assert self.config.placement is not None, "Placement should not be None"
        placement_path = self.get_deployment_placement_paths()[0]
        penetration_path = os.path.join(placement_path, str(sample), str(penetration))
        os.makedirs(penetration_path, exist_ok=True)
        pv_systems_file = os.path.join(penetration_path, PV_SYSTEMS_FILENAME)
        return pv_systems_file

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
            while remaining_pv_to_install > PV_INSTALLATION_TOLERANCE:
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
                    logger.info(
                        "No %s file created on feeder - %s, beacause capacity remains %s",
                        PV_SYSTEMS_FILENAME,
                        self.feeder_path,
                        remaining_pv_to_install
                    )
                    break

                while len(candidate_bus_array) > 0:
                    picked_candidate = random.choice(candidate_bus_array)
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

    def add_pv_string(self, bus: str, pv_type: str, pv_size: float, pv_string: str) -> str:
        """Add PV string to exiting string"""
        if round(pv_size, 3) <= 0:
            return pv_string

        pv_name = self.generate_pv_name(bus, pv_type)
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
            f"Pmpp={pv_size} %Pmpp=100 kVA={pv_size} "
            f"conn=wye %cutin=0.1 %cutout=0.1 "
            f"Vmaxpu=1.2\n"
        )
        pv_string += new_pv_string
        return pv_string
    
    @staticmethod
    def generate_pv_name(bus, pv_type):
        return f"{pv_type}_{bus.replace('.', '_')}_pv"

    def write_pv_string(self, pv_string: str, data: SimpleNamespace) -> None:
        """Write PV string to PV deployment file."""
        total_pv = self.get_total_pv(data)
        pv_systems_file = self.get_pv_systems_file(data.sample, data.penetration)
        line = (
            f"// PV Scenario for {total_pv} kW total size, "
            f"Scenario type {self.config.placement}, Sample {data.sample} "
            f"and penetration {data.penetration}% (PV to load ratio) \n"
        )
        with open(pv_systems_file, "w") as f:
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
        root_path = self.get_pv_deployments_path()
        if not os.path.exists(root_path):
            logger.info(
                "Deployment path %s not exis under %s",
                self.config.pv_deployments_dirname,
                self.feeder_path
            )
            return []
        
        config_files = []
        pv_shapes_file = self.get_pv_shapes_file(self.feeder_path)
        placement_paths = self.get_deployment_placement_paths()
        for placement_path in placement_paths:
            if not os.path.exists(placement_path):
                continue
            samples = get_subdir_names(placement_path)
            for sample in samples:
                random.seed(self.config.random_seed + int(sample))
                sample_path = os.path.join(placement_path, sample)
                pv_systems = set()
                pv_configs, pv_profiles = [], {}
                for pen in os.listdir(sample_path):
                    pen_dir = os.path.join(sample_path, pen)
                    if not os.path.isdir(pen_dir):
                        continue
                    pv_systems_file = os.path.join(pen_dir, PV_SYSTEMS_FILENAME)
                    if os.path.exists(pv_systems_file):
                        pv_conf, pv_prof = self.assign_profile(pv_systems_file, pv_shapes_file, pv_systems)
                        pv_configs += pv_conf
                        pv_profiles.update(pv_prof)
                        self.attach_profile(pv_systems_file, pv_profiles)
                final = {"pv_systems": pv_configs}
                pv_config_file = self.save_pv_config(final, sample_path)
                config_files.append(pv_config_file)
        logger.info("%s PV config files generated for feeder - %s", len(config_files), self.feeder_path)
        logger.info("Attached PV profiles to PV systems for feeder - %s", self.feeder_path)
        return config_files

    def get_customer_types(self):
        # NOTE: In Loads.dss file, each line contains string like "yearly=com_kw_29321_pu".
        # However "yearly=xxxx" only exists in the original loads file, but not the transformed
        # one during the PV deployment process. After the deployments, the original
        # loads files were renmaed back, and would not exist.
        loads_file = os.path.join(self.feeder_path, ORIGINAL_LOADS_FILENAME)
        if not os.path.exists(loads_file):
            loads_file = os.path.join(self.feeder_path, LOADS_FILENAME)
        
        bus_key = "bus1="
        shape_key = "yearly="
        load_key = "Load."

        bus_customer_types, load_customer_types = {}, {}
        with open(loads_file, "r") as f:
            for line in f.readlines():
                if bus_key not in line.lower():
                    continue
                bus = line.split(bus_key)[1].split(" ")[0].split(".")[0]
                shape_name = line.split(shape_key)[1].split(" ")[0]
                load = line.split(load_key)[1].split(" ")[0]
                if "com_" in shape_name:
                    customer_type = "commercial"
                elif "res_" in shape_name:
                    customer_type = "residential"
                else:
                    customer_type = None
                
                # NOTE: here assume all nodes on same bus have same customer type
                bus_customer_types[bus] = customer_type
                load_customer_types[load] = customer_type

        return {
            "bus_customer_types": bus_customer_types,
            "load_customer_types": load_customer_types
        }

    def assign_profile(
        self,
        pv_systems_file: str,
        pv_shapes_file: str,
        pv_systems: set,
        limit: int = 5
    ) -> dict:
        """Assign PV profile to PV systems."""
        pv_dict = self.get_pvsys(pv_systems_file)
        shape_list = self.get_shape_list(pv_shapes_file)
        pv_conf, pv_prof = [], {}
        for pv_name, value in pv_dict.items():
            pv_value = value["pmpp"]
            if pv_name in pv_systems:
                continue
            if float(pv_value) > limit:
                control_name = "volt_var_ieee_1547_2018_catB"
            else:
                control_name = "pf1"
            pv_profile = random.choice(shape_list)

            pv_conf.append({
                "name": pv_name,
                "pydss_controller": {
                    "controller_type": "PvController",
                    "name": control_name
                },
                "pv_profile": pv_profile,
                "customer_type": self.get_bus_customer_type(value["bus"])
            })
            pv_systems.add(pv_name)
            pv_prof[pv_name] = pv_profile
        return pv_conf, pv_prof
    
    def get_bus_customer_type(self, bus):
        if not self.customer_types:
            self.customer_types = self.get_customer_types()
        
        return self.customer_types["bus_customer_types"][bus]

    @staticmethod
    def get_pvsys(pv_systems_file: str) -> dict:
        """Return a mapping of PV systems"""
        pv_dict = {}
        with open(pv_systems_file) as f:
            for line in f.readlines():
                lowered_line = line.lower()
                if "pvsystem" in lowered_line:
                    pmpp = lowered_line.split("pmpp=")[1].split(" ")[0]
                    pv_name = lowered_line.split("pvsystem.")[1].split(" ")[0]
                    bus = lowered_line.split("bus1=")[1].split(" ")[0].split(".")[0]
                    pv_dict[pv_name] = {
                        "pmpp": pmpp,
                        "bus": bus
                    }
        return pv_dict

    def get_shape_list(self, pv_shapes_file: str) -> list:
        """Return a list of loadshapes"""
        shape_list = []
        with open(pv_shapes_file) as f:
            for line in f.readlines():
                lowered_line = line.lower()
                if "loadshape" in lowered_line:
                    shape_list.append(lowered_line.split("loadshape.")[1].split(' ')[0])
        return shape_list

    def save_pv_config(self, pv_config: dict, sample_path: str) -> None:
        """Save PV configuration to JSON file"""
        pv_config_file = os.path.join(sample_path, PV_CONFIG_FILENAME)
        with open(pv_config_file, "w") as f:
            json.dump(pv_config, f, indent=2)
        logger.info("PV config file generated - %s", pv_config_file)
        return pv_config_file
    
    def attach_profile(self, pv_systems_file: str, pv_profiles: dict) -> None:
        """Attach PV profile to each system with 'yearly=<pv-profile>' in PVSystems.dss"""
        regex1 = re.compile("yearly=[\w\.\-_]+")
        regex2 = re.compile(r"new pvsystem\.([^\s]+)")
        
        updated_data = []
        with open(pv_systems_file, "r") as fr:
            for line in fr.readlines():
                lowered_line = line.lower()
                if "new pvsystem" not in lowered_line:
                    updated_data.append(line)
                    continue
                
                match1 = regex1.search(line)
                if match1:
                    line = " ".join(line.split(match1.group(0))).strip()
                
                match2 = regex2.search(lowered_line)
                assert match2, line
                pv_name = match2.group(0).split(".")[1]
                pv_profile = pv_profiles.get(pv_name, None)
                if not pv_profile:
                    raise Exception(f"No PV profile founded for {pv_name} - [{line}]]")
                new_line = line.strip() + f" yearly={pv_profile}\n"
                updated_data.append(new_line)
        
        with open(pv_systems_file, "w") as fw:
            fw.writelines(updated_data)
    
    def create_pv_systems_sum_group_file(self, pv_config_files):
        """
        Walk through all PV configs created in each sample, and generate a sum group JSON file
        at the feeder level.

        Parameters
        ----------
        pv_config_files: list,

        Returns
        -------
        str,
        """
        sum_groups = defaultdict(set)
        for config_file in pv_config_files:
            data = load_data(config_file)["pv_systems"]
            for item in data:
                sum_groups[item["customer_type"]].add(item["name"])
        
        result = {
            "sum_groups":[
                {"name": customer_type, "elements": list(elements)}
                for customer_type, elements in sum_groups.items()
            ]
        }
        filename = os.path.join(self.get_metadata_directory(), PV_SYSTEMS_SUM_GROUP_FILENAME)
        dump_data(result, filename, indent=2)
        logger.info("PV Systems sum group file created - %s", filename)
    
    def create_loads_sum_group_file(self):
        """Create a sum group file for loads based on customer types"""
        if not self.customer_types:
            self.customer_types = self.get_customer_types()
        customer_types = self.customer_types["load_customer_types"]

        sum_groups = defaultdict(set)
        for load, customer_type in customer_types.items():
            sum_groups[customer_type].add(load)
        
        result = {
            "sum_groups": [
                {"name": customer_type, "elements": list(elements)}
                for customer_type, elements in sum_groups.items()
            ]
        }
        filename = os.path.join(self.get_metadata_directory(), LOADS_SUM_GROUP_FILENAME)
        dump_data(result, filename, indent=2)
        logger.info("Loads sum group file created - %s", filename)


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
            value = customer_annual_kwh[bus] / annual_sun_hours
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

    def get_maximum_pv_size(self, bus: str, data: SimpleNamespace, **kwargs) -> float:
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

    def __init__(self, input_path: str, hierarchy: DeploymentHierarchy, config: SimpleNamespace) ->None:
        self.input_path = input_path
        self.hierarchy = hierarchy
        self.config = config

    def get_region_paths(self, city_path: str) -> list:
        """Given a city path, return all region paths of the city"""
        if self.hierarchy != DeploymentHierarchy.CITY:
            raise ValueError("The hierarchy value should be 'city' for '--hierarchy' option")

        # NOTE: Assume all region directories are named with pattern 'PXX'
        subdir_names = get_subdir_names(city_path)
        region_names = [name for name in subdir_names if name.startswith("P")]
        
        region_paths = [os.path.join(city_path, name) for name in region_names]
        return region_paths

    def get_substation_paths(self) -> list:
        """Given an input path, return a list of substation paths"""
        if self.hierarchy == DeploymentHierarchy.FEEDER:
            paths = self._get_substation_paths_from_feeder_input(self.input_path)
        elif self.hierarchy == DeploymentHierarchy.SUBSTATION:
            paths = self._get_substation_paths_from_substation_input(self.input_path)
        elif self.hierarchy == DeploymentHierarchy.REGION:
            paths = self._get_substation_paths_from_region_input(self.input_path)
        elif self.hierarchy == DeploymentHierarchy.CITY:
            paths = self._get_substation_paths_from_city_input(self.input_path)
        else:
            assert False, self.hierarchy
        return paths

    @staticmethod
    def _get_substation_paths_from_feeder_input(feeder_path: str) -> list:
        """Given a feeder path, return its substation path"""
        return [os.path.dirname(feeder_path)]

    @staticmethod
    def _get_substation_paths_from_substation_input(substation_path: str) -> list:
        """Given a substation input path, return it as a list"""
        return [substation_path]

    @staticmethod
    def _get_substation_paths_from_region_input(region_path: str) -> list:
        """Search region input path, return all substation paths in region"""
        opendss_path = os.path.join(
            region_path,
            "solar_none_batteries_none_timeseries",
            "opendss"
        )
        if not os.path.exists(opendss_path):
            opendss_path = os.path.join(
                region_path,
                "scenarios",
                "base_timeseries",
                "opendss"
            )
        substation_names = get_subdir_names(opendss_path)
        
        # NOTE: exclude directory named "subtransmission" from substations
        if "subtransmission" in substation_names:
            substation_names.remove("subtransmission")
        
        substation_paths = [
            os.path.join(opendss_path, substation_name)
            for substation_name in substation_names
        ]
        return substation_paths
    
    def _get_substation_paths_from_city_input(self, city_path: str) -> list:
        """Search city input path, return all substation paths in all regions of the city"""
        region_paths = self.get_region_paths(city_path)
        substation_paths = []
        for region_path in region_paths:
            substation_paths.extend(self._get_substation_paths_from_region_input(region_path))
        return substation_paths
    
    def get_feeder_paths(self) -> list:
        """Given an input path, return a list of feeder paths"""
        if self.hierarchy == DeploymentHierarchy.FEEDER:
            paths = self._get_feeder_paths_from_feeder_input(self.input_path)
        elif self.hierarchy == DeploymentHierarchy.SUBSTATION:
            paths = self._get_feeder_paths_from_substation_input(self.input_path)
        elif self.hierarchy == DeploymentHierarchy.REGION:
            paths = self._get_feeder_paths_from_region_input(self.input_path)
        elif self.hierarchy == DeploymentHierarchy.CITY:
            paths = self._get_feeder_paths_from_city_input(self.input_path)
        else:
            assert False, self.hierarchy
        return paths

    @staticmethod
    def _get_feeder_paths_from_feeder_input(feeder_path: str) -> list:
        """Search feeder input path, return it as a list"""
        feeder_paths = [feeder_path]
        return feeder_paths

    @staticmethod
    def _get_feeder_paths_from_substation_input(substation_path: str) -> list:
        """Search substation input path, return all feeder paths in substation"""
        feeder_names = get_subdir_names(substation_path)
        
        # NOTE: found a directory named "subtransmission", it's not a feeder
        if "subtransmission" in feeder_names:
            feeder_names.remove("subtransmission")
        
        feeder_paths = [
            os.path.join(substation_path, feeder_name)
            for feeder_name in feeder_names
        ]
        return feeder_paths

    def _get_feeder_paths_from_region_input(self, region_path: str) -> list:
        """Search region input path, return all feeder paths in region"""
        feeder_paths = []
        substation_paths = self._get_substation_paths_from_region_input(region_path)
        for substation_path in substation_paths:
            feeder_names = get_subdir_names(substation_path)
            feeder_paths.extend([
                os.path.join(substation_path, feeder_name)
                for feeder_name in feeder_names
            ])
        return feeder_paths

    def _get_feeder_paths_from_city_input(self, city_path: str) -> list:
        """Search city input path, return aall feeder paths in city"""
        feeder_paths = []
        substation_paths = self._get_substation_paths_from_city_input(city_path)
        for substation_path in substation_paths:
            feeder_names = get_subdir_names(substation_path)
            feeder_paths.extend([
                os.path.join(substation_path, feeder_name)
                for feeder_name in feeder_names
            ])
        return feeder_paths

    def get_deployment_path(self, feeder_path: str) -> str:
        """Return the deployment path"""
        path = os.path.join(feeder_path, self.config.pv_deployments_dirname)
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


class PVDataManager(PVDataStorage):
    
    def __init__(self, input_path: str, hierarchy: DeploymentHierarchy, config: SimpleNamespace) -> None:
        """
        Initialize pv data manager class

        Parameters
        ----------
        hierarchy: DeploymentHierarchy, the predefined hierarchy
        input_path: str, the input path of raw dss data for generating pv deployments.
        config: SimpleNamespace, the pv deployment configuration namespace.
        """
        super().__init__(input_path, hierarchy, config)

    def redirect(self, input_path: str) -> bool:
        """Given a path, update the master file by redirecting PVShapes.dss"""
        pv_shapes_file = os.path.join(input_path, PV_SHAPES_FILENAME)
        self._copy_pv_shapes_file(input_path)
        
        master_file = os.path.join(input_path, self.config.master_filename)
        if not os.path.exists(master_file):
            logger.exception("'%s' not found in '%s'. System exits!", self.config.master_filename, input_path)
            raise
        
        index = 0
        with open(master_file, "r") as fr:
            data = fr.readlines()

        for i, line in enumerate(data):
            line = line.strip().lower()
            if line.startswith("redirect"):
                index = i + 1
            if line == f"redirect {PV_SHAPES_FILENAME}".lower():
                logger.info("Skip %s redirect, it already exists.", PV_SHAPES_FILENAME)
                return False

        assert index > 0, f"There must be 'Redirect' in {master_file}"

        logger.info("Update master file %s to redirect %s", master_file, PV_SHAPES_FILENAME)
        data.insert(index, f"Redirect {PV_SHAPES_FILENAME}\n")
        with open(master_file, "w") as fw:
            fw.writelines(data)
        return True

    def _copy_pv_shapes_file(self, input_path: str) -> None:
        """Copy PVShapes.dss file from source to feeder/substatation directories"""
        input_path  = Path(input_path)
        # NOTE: Coordinate different path patterns among different cities
        if "solar_none_batteries_none_timeseries" in str(input_path):
            index = 3 if input_path.parent.name == "opendss" else 4
        else:
            index = 4 if input_path.parent.name == "opendss" else 5
        src_file = input_path.parents[index] / "pv-profiles" / PV_SHAPES_FILENAME
        if not src_file.exists():
            raise ValueError("PVShapes.dss file does not exist - " + str(src_file))
        dst_file = input_path / PV_SHAPES_FILENAME
        
        with open(src_file, "r") as fr, open(dst_file, "w") as fw:
            new_lines = []
            for line in fr.readlines():
                pv_profile = re.findall(r"file=[a-zA-Z0-9\-\_\/\.]*", line)[0]
                city_path = Path(os.path.sep.join([".."] * (index + 1)))
                relative_pv_profile = city_path / "pv-profiles" / os.path.basename(pv_profile)
                relative_pv_profile = "file=" + str(relative_pv_profile)
                new_line = line.replace(pv_profile, relative_pv_profile)
                new_lines.append(new_line)
            fw.writelines(new_lines)

    def redirect_substation_pv_shapes(self) -> None:
        """Run PVShapes redirect in substation directories in parallel"""
        substation_paths = self.get_substation_paths()
        logger.info("Running PVShapes redirect in %s substation directories...", len(substation_paths))
        with ProcessPoolExecutor() as executor:
            executor.map(self.redirect, substation_paths)
        logger.info("Substation PVShapes redirect done!")
    
    def redirect_feeder_pv_shapes(self) -> None:
        """Run PVShapes redirect in feeder directories in parallel"""
        feeder_paths = self.get_feeder_paths()
        logger.info("Running PVShapes redirect in %s feeder directories...", len(feeder_paths))
        with ProcessPoolExecutor() as executor:
            executor.map(self.redirect, feeder_paths)
        logger.info("Feeder PVShapes redirect done!")
    
    def rename(self, feeder_path: str) -> None:
        """Rename transformed/original Loads files"""
        loads_file = os.path.join(feeder_path, LOADS_FILENAME)
        original_loads_file = os.path.join(feeder_path, ORIGINAL_LOADS_FILENAME)
        transformed_loads_file = os.path.join(feeder_path, TRANSFORMED_LOADS_FILENAME)
        
        if not os.path.exists(original_loads_file):
            return
        
        if os.path.exists(transformed_loads_file):
            os.remove(transformed_loads_file)
        
        os.rename(loads_file, transformed_loads_file)
        try:
            os.chmod(transformed_loads_file, 0o666)
        except OSError:
            pass
        
        os.rename(original_loads_file, loads_file)
        try:
            os.chmod(loads_file, 0o666)
        except OSError:
            pass
    
    def rename_feeder_loads(self, feeder_paths: list) -> None:
        """Rename transformed Loads.dss to PV_Loads.dss"""
        logger.info("Renaming loads files in %s feeder directories...", len(feeder_paths))
        deployed = []
        for feeder_path in feeder_paths:
            original_loads_file = os.path.join(feeder_path, ORIGINAL_LOADS_FILENAME)
            if not os.path.exists(original_loads_file):
                continue
            deployed.append(feeder_path)
        
        with ProcessPoolExecutor() as executor:
            executor.map(self.rename, deployed)
        logger.info("Feeder Loads rename done, total %s", len(deployed))
    
    def revert(self, feeder_path: str):
        """Enable LoadShapes redirect by removing the starting symbol !."""
        master_file = os.path.join(feeder_path, self.config.master_filename)
        redirected = True
        data = []
        with open(master_file, "r") as fr:
            for line in fr.readlines():
                if line.startswith("!") and "redirect loadshapes.dss" in line.lower():
                    line = line.lstrip("!")
                    redirected = False
                data.append(line)
        
        if redirected:
            return
        
        with open(master_file, "w") as fw:
            fw.writelines(data)
        logger.info("Master file get reverted with LoadShape.dss redirected - %s", master_file)
    
    def revert_master_files(self, feeder_paths: list) -> None:
        """Revert master files with LoadShapes.dss redirect enabled"""
        with ProcessPoolExecutor() as executor:
            executor.map(self.revert, feeder_paths)
        logger.info("Feeder Redirect LoadShapes.dss enabled in master files, total %s", len(feeder_paths))
    
    def restore_feeder_data(self) -> None:
        """After PV deployments, we need to restore feeder data transformed during PV deployments
            1) rename transformed Loads.dss to PV_Loads.dss;
            2) uncomment on LoadShapes.dss redirect in master file.
        """
        feeder_paths = self.get_feeder_paths()
        self.rename_feeder_loads(feeder_paths)
        self.revert_master_files(feeder_paths)
    
    def transform(self, feeder_path: str) -> None:
        """Transform feeder Loads.dss
        
        change load model to suitable center-tap schema if needed
        """
        original_loads_file = os.path.join(feeder_path, ORIGINAL_LOADS_FILENAME)
        loads_file = os.path.join(feeder_path, LOADS_FILENAME)
        if os.path.exists(original_loads_file):
            self.restore_loads_file(original_loads_file)
        else:
            self.backup_loads_file(loads_file)
        
        with open(original_loads_file, "r") as fr, open(loads_file, "w") as fw:
            load_lines = fr.readlines()
            rekeyed_load_dict = self.build_load_dictionary(load_lines)
            updated_lines = self.update_loads(load_lines, rekeyed_load_dict)
            new_lines = self.strip_pv_profile(updated_lines)
            fw.writelines(new_lines)
        logger.info("Loads transformed - '%s'.", loads_file)
    
    def restore_loads_file(self, original_loads_file: str) -> bool:
        """Restore Loads file from backup"""
        if not os.path.exists(original_loads_file):
            return False
        
        loads_file = os.path.join(os.path.dirname(original_loads_file), LOADS_FILENAME)
        if os.path.exists(loads_file):
            os.remove(loads_file)
        
        shutil.copyfile(original_loads_file, loads_file)
        try:
            os.chmod(loads_file, 0o666)
        except Exception:
            pass
        return True
    
    def backup_loads_file(self, loads_file: str) -> bool:
        """Create a backup of Loads.dss file"""
        feeder_path = os.path.dirname(loads_file)
        original_loads_file = os.path.join(feeder_path, ORIGINAL_LOADS_FILENAME)
        if os.path.exists(original_loads_file):
            return False
        
        shutil.copyfile(loads_file, original_loads_file)
        try:
            os.chmod(original_loads_file, 0o666)
        except Exception:
            pass
        return True
    
    def strip_pv_profile(self, load_lines: list) -> list:
        """To strip 'yearly=<pv-profile>' from load lines during PV deployments"""
        regex = re.compile(r"\syearly=\S+", flags=re.IGNORECASE)
        new_lines = []
        for line in load_lines:
            match = regex.search(line.strip())
            if not match:
                new_lines.append(line)
            else:
                line = "".join(line.split(match.group(0)))
                new_lines.append(line)
        return new_lines
    
    def get_attribute(self, line: str, attribute_id: str) -> str:
        """
        Get the attribute from line string.

        Attribute ID
        for kv: 'kv='
        for name: 'new load.' (load example)
        for bus: 'bus1='
        for kw: 'kw='
        """
        attribute = None
        lowered_line = line.lower()
        if attribute_id in lowered_line:
            attribute = lowered_line.split(attribute_id)[1].split(" ")[0]
            if "kv" in attribute_id or "kw" in attribute_id:
                attribute = float(attribute)
        return attribute

    def build_load_dictionary(self, load_lines: list) -> dict:
        """Util function for building dict from load lines."""
        load_dict = {}
        for idx, line in enumerate(load_lines):
            lowered_line = line.lower()
            if 'new' not in lowered_line:
                continue
            
            bus_node = self.get_attribute(line, "bus1=")
            if bus_node is None:
                continue
            
            kv = self.get_attribute(line, "kv=")
            kw = self.get_attribute(line, "kw=")
            kvar = self.get_attribute(line, "kvar=")
            kva = self.get_attribute(line, "kva=")
            phases = self.get_attribute(line, "phases=")
            init_name = self.get_attribute(line, "new load.")
            
            if "." in bus_node:
                bus = bus_node.split(".")[0]
                nodes = bus_node.split(".")[1:]
            else:
                bus = bus_node
                nodes = []
            
            if len(nodes) < 3:
                name = "_".join(init_name.split("_")[:-1])
            else:
                name = init_name
            
            if (bus, name) in load_dict.keys():
                if nodes:
                    load_dict[bus, name]["node"] += nodes
                if "kw=" in lowered_line:
                    load_dict[bus, name]["kw"] += kw
                if "kvar=" in lowered_line:
                    load_dict[bus, name]["kvar"] += kvar
                if "kva=" in lowered_line:
                    load_dict[bus, name]["kva"] += kva
            else:
                load_dict[bus, name] = {}
                load_dict[bus, name]["name"] = name
                load_dict[bus, name]["bus"] = bus
                load_dict[bus, name]["node"] = nodes
                if "kw=" in lowered_line:
                    load_dict[bus, name]["kw"] = kw
                if "kvar=" in lowered_line:
                    load_dict[bus, name]["kvar"] = kvar
                if "kva=" in lowered_line:
                    load_dict[bus, name]["kva"] = kva
                if "phases=" in lowered_line:
                    load_dict[bus, name]["phases"] = phases
                load_dict[bus,name]["line_idx"] = idx 
                load_dict[bus,name]["kv"] = kv
        
        rekeyed_load_dict = {v["line_idx"]: v for k, v in load_dict.items()}
        return rekeyed_load_dict

    def update_loads(self, lines: dict, rekeyed_load_dict: dict) -> list:
        """Update load lines based on given load dict"""
        new_load_lines = []
        for k, v in rekeyed_load_dict.items():
            if v["node"]:
                bus_name = f"{v['bus']}.{'.'.join(v['node'])}"
            else:
                bus_name = v["bus"]
            
            lines[k] = lines[k].replace(self.get_attribute(lines[k],"bus1="), bus_name)
            lines[k] = lines[k].replace(self.get_attribute(lines[k],"load."), v["name"])

            if np.isclose(v["kv"], 0.12) and len(v["node"])==2:
                kv = 0.208
                phases = "2"
            else:
                kv = v["kv"]
                phases = v["phases"]
            
            lowered_line = lines[k].lower()
            lowered_line = lowered_line.replace(f"kv={self.get_attribute(lines[k], 'kv=')}", f"kv={kv}")
            lowered_line = lowered_line.replace(f"phases={self.get_attribute(lines[k], 'phases=')}", f"phases={phases}")
            if "kw=" in lowered_line:
                lowered_line = lowered_line.replace(f"kw={self.get_attribute(lines[k], 'kw=')}", f"kw={str(v['kw'])}")
            if "kvar=" in lowered_line:
                lowered_line = lowered_line.replace(f"kvar={self.get_attribute(lines[k], 'kvar=')}", f"kvar={str(v['kvar'])}")
            if "kva=" in lowered_line:
                lowered_line = lowered_line.replace(f"kva={self.get_attribute(lines[k], 'kva=')}", f"kva={str(v['kva'])}")
            lines[k] = lowered_line
        
        new_load_lines = [lines[x] for x in rekeyed_load_dict.keys()]
        return new_load_lines

    def transform_feeder_loads(self) -> None:
        """Before PV deployments, transform Loads.dss"""
        feeder_paths = self.get_feeder_paths()
        logger.info("Transforming loads files in %s feeders...", len(feeder_paths))
        with ProcessPoolExecutor() as executor:
            executor.map(self.transform, feeder_paths)
        logger.info("Feeder Loads transformed, total %s feeders.", len(feeder_paths))


class PVDeploymentManager(PVDataStorage):

    def __init__(self, input_path: str, hierarchy: DeploymentHierarchy, config: SimpleNamespace) -> None:
        """
        Initialize pv deployment manager class

        Parameters
        ----------
        hierarchy: DeploymentHierarchy, the predefined hierarchy
        input_path: str, the input path of raw dss data for generating pv deployments.
        config: SimpleNamespace, the pv deployment configuration namespace.
        """
        super().__init__(input_path, hierarchy, config)

    def generate_pv_deployments(self) -> dict:
        """Given input path, generate pv deployments"""
        summary = {}
        feeder_paths = self.get_feeder_paths()
        for feeder_path in feeder_paths:
            generator = get_pv_scenario_generator(feeder_path, self.config)
            logger.info(
                "Set initial integer seed %s for PV deployments on feeder - %s",
                self.config.random_seed, feeder_path
            )
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

    def generate_pv_creation_jobs(self):
        """Generate PV creation jobs at feeder hierarchy"""
        feeder_paths = self.get_feeder_paths()
        placements = [p.value for p in Placement]
        if self.config.placement:
            placements = [self.config.placement]
        
        options = ""
        options += f"-c {self.config.category} "
        options += f"-f {self.config.master_filename} "
        options += f"-m {self.config.min_penetration} "
        options += f"-M {self.config.max_penetration} "
        options += f"-s {self.config.penetration_step} "
        options += f"-n {self.config.sample_number} "
        options += f"-S {self.config.proximity_step} "
        options += f"-o {self.config.pv_deployments_dirname} "
        options += f"-r {self.config.random_seed} "
        if self.config.pv_size_pdf:
            options += f"-x {self.config.pv_size_pdf} "
        if not self.config.pv_upscale:
            options += "--no-pv-upscale "
        options.strip()
        
        commands = []
        for feeder_path in feeder_paths:
            for placement in placements:
                cmd = (
                    "disco pv-deployments source-tree-1 "
                    f"-a create-pv -h feeder -p {placement} {options} {feeder_path}\n"
                )
                commands.append(cmd.encode())
        
        with NamedTemporaryFile(delete=False) as f:
            f.writelines(commands)
            commands_file = f.name
        
        config_file = "create-pv-jobs.json"
        try:
            config_cmd = f"jade config create {commands_file} -c {config_file}"
            check_run_command(config_cmd)
        finally:
            os.unlink(commands_file)
        
        return config_file


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
        super().__init__(input_path, hierarchy, config)

    def generate_pv_configs(self) -> list:
        """Generate pv config JSON files based on PV deployments"""
        config_files = []
        feeder_paths = self.get_feeder_paths()
        for feeder_path in feeder_paths:
            generator = get_pv_scenario_generator(feeder_path, self.config)
            result = generator.create_all_pv_configs()
            config_files.extend(result)
            
            generator.create_pv_systems_sum_group_file(pv_config_files=result)
            generator.create_loads_sum_group_file()

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

    def generate_pv_config_jobs(self):
        """Generate PV configs jobs at feeder hierarchy"""
        feeder_paths = self.get_feeder_paths()
        
        options = ""
        options += f"-c {self.config.category} "
        options += f"-f {self.config.master_filename} "
        options += f"-m {self.config.min_penetration} "
        options += f"-M {self.config.max_penetration} "
        options += f"-s {self.config.penetration_step} "
        options += f"-n {self.config.sample_number} "
        options += f"-S {self.config.proximity_step} "
        options += f"-o {self.config.pv_deployments_dirname} "
        options += f"-r {self.config.random_seed} "
        if self.config.pv_size_pdf:
            options += f"-x {self.config.pv_size_pdf} "
        if not self.config.pv_upscale:
            options += "--no-pv-upscale "
        options.strip()
        
        commands = []
        for feeder_path in feeder_paths:
            cmd = (
                "disco pv-deployments source-tree-1 "
                f"-a create-configs -h feeder {options} {feeder_path}\n"
            )
            commands.append(cmd.encode())
        
        with NamedTemporaryFile(delete=False) as f:
            f.writelines(commands)
            commands_file = f.name
        
        config_file = "create-config-jobs.json"
        try:
            config_cmd = f"jade config create {commands_file} -c {config_file}"
            check_run_command(config_cmd)
        finally:
            os.unlink(commands_file)
        
        return config_file
