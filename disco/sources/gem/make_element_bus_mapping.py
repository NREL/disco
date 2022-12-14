#!/usr/bin/env python

"""Maps elements to attached buses for each feeder in a path."""

import json
import logging
import os
import re
import sys

from jade.loggers import setup_logging
from jade.utils.utils import get_cli_string

REGION_BUS_MAPPING_FILENAME = "bus_mapping_summary.json"

logger = None


class MissingBus(Exception):
    pass


class BadFormat(Exception):
    pass


# This matches 1423_0_1409_0 and 242228 from
# New Capacitor.1423_0_1409_0 Bus1=242228 phases=3 Kv=4.8 conn=delta Kvar=450.0
REGEX_CAPACITOR = re.compile(r"New (?P<capacitor>Capacitor\.\w+).*Bus\w+=(?P<bus>\w+)", re.IGNORECASE)

# This matches 1418_0_7958_0, 242223, and 242246 from
# New Line.1418_0_7958_0 Units=km Length=0.15155920328177602 bus1=242223.1.2.3 bus2=242246.1.2.3 switch=n enabled=y phases=3 geometry=oh__314784__
REGEX_LINE = re.compile(r"New (?P<line>Line\.\w+).*bus\w+=(?P<bus_from>\w+).*bus\w+=(?P<bus_to>\w+)", re.IGNORECASE)

# This matches load_694781 and 242205_xfmr from
# New Load.load_694781 conn=delta bus1=242205_xfmr.1.2.3 kV=0.48 model=1 kW=3.225882583335277 kvar=0.7400682202361257 Phases=3
REGEX_LOAD = re.compile(r"New (?P<load>Load\.\w+).*bus\w+=(?P<bus>\w+)", re.IGNORECASE)

# This matches pv_865744 and 242208_xfmr from
# New PVSystem.pv_865744 bus1=242208_xfmr.1.2 phases=2 kV=0.20784609690826525 kVA=1.5829000000000002 Pmpp=1.439 conn=wye
REGEX_PV_SYSTEM = re.compile(r"New (?P<pv_system>PVSystem\.[\w-]+) bus\w+=(?P<bus>\w+)", re.IGNORECASE)

# This matches 1417_0_4346_0 and 3 from
# New Transformer.1417_0_4346_0 phases=1 windings=3 wdg=1 conn=delta bus=242214.2.3 Kv=4.8 kva=15.0 EmergHKVA=22.5 %r=0.1 wdg=2 conn=wye bus=242214_xfmr.1.0 Kv=0.12 kva=15.0 EmergHKVA=22.5 %r=0.1 wdg=3 conn=wye bus=242214_xfmr.0.2 Kv=0.12 kva=15.0 EmergHKVA=22.5 %r=0.1 XHL=0.1 XLT=0.1 XHT=0.1
REGEX_TRANSFORMER = re.compile(r"New (?P<transformer>Transformer\.\w+).*windings=(?P<windings>\d+).*bus=", re.IGNORECASE)
# After the above string has been split by "wdg=" this matches each wdg number and bus.
REGEX_TRANSFORMER_BUSES = re.compile(r"^(?P<winding>\d+).*conn=\w+.*bus=(?P<bus>\w+)", re.IGNORECASE)

# This matches an alternate transformer representation.
# New Transformer.trans_242188_reg phases=3 windings=2 buses=(242188_src.1.2.3,242188_dummy.1.2.3) conns=(Delta, Wye) kvs=(4.8, 4.8) kvas=(100000.0, 100000.0) XHL=0.1
REGEX_TRANSFORMER_ALT = re.compile(r"New (?P<transformer>Transformer\.\w+).*windings=(?P<windings>\d+).*buses=\((?P<buses>[\w\.,]+)\)", re.IGNORECASE)


def _check_bus(feeder_mapping, bus, name):
    if bus not in feeder_mapping["bus_coords"]:
        logger.warning("element=%s bus=%s is not present", name, bus)
        #raise MissingBus(f"bus={bus} element={elem_type}.{name} is not present")
        return False
    return True


def _check_transformer_buses(feeder_mapping, transformer, buses):
    if not _check_bus(feeder_mapping, buses["primary"], transformer):
        logger.warning("Missing coordinates for transformer=%s primary bus", transformer)
        return False

    if not _check_bus(feeder_mapping, buses["secondary"], transformer):
        logger.warning("Missing coordinates for transformer=%s secondary bus", transformer)
        feeder_mapping["bus_coords"][buses["secondary"]] = \
            feeder_mapping["bus_coords"][buses["primary"]]

    return True


def _check_bus_presence(feeder_mapping):
    for element_type, element_mapping in feeder_mapping.items():
        if element_type == "bus_coords":
            continue
        if element_type == "transformers":
            # Already checked.
            continue
        if element_type == "lines":
            for element, bus in element_mapping.items():
                _check_bus(feeder_mapping, bus["from"], element)
                _check_bus(feeder_mapping, bus["to"], element)
        else:
            for element, bus in element_mapping.items():
                _check_bus(feeder_mapping, bus, element)


def _handle_capacitor(feeder_mapping, line):
    match = REGEX_CAPACITOR.search(line)
    if not match:
        raise BadFormat(f"unsupported capacitor format: {line}")

    groupdict = match.groupdict()
    capacitor = groupdict["capacitor"]
    bus = groupdict["bus"]
    if capacitor in feeder_mapping["capacitors"]:
        logger.warning("Detected duplicate capacitor=%s", capacitor)
        return
    feeder_mapping["capacitors"][capacitor] = bus


def _handle_line(feeder_mapping, line):
    match = REGEX_LINE.search(line)
    if not match:
        raise BadFormat(f"unsupported line format: {line}")

    groupdict = match.groupdict()
    line_elem = groupdict["line"]
    bus_from = groupdict["bus_from"]
    bus_to = groupdict["bus_to"]
    if line_elem in feeder_mapping["lines"]:
        logger.warning("Detected duplicate line=%s", line_elem)
        return
    feeder_mapping["lines"][line_elem] = {
        "from": bus_from,
        "to": bus_to,
    }


def _handle_load(feeder_mapping, line):
    match = REGEX_LOAD.search(line)
    if not match:
        raise BadFormat(f"unsupported load format: {line}")

    groupdict = match.groupdict()
    load = groupdict["load"]
    bus = groupdict["bus"]
    if load in feeder_mapping["loads"]:
        logger.warning("Detected duplicate load=%s", load)
        return
    feeder_mapping["loads"][load] = bus


def _handle_pv_system(feeder_mapping, line):
    match = REGEX_PV_SYSTEM.search(line)
    if not match:
        raise BadFormat(f"unsupported pv_system format: {line}")

    groupdict = match.groupdict()
    pv_system = groupdict["pv_system"]
    bus = groupdict["bus"]
    if pv_system in feeder_mapping["pv_systems"]:
        assert bus == feeder_mapping["pv_systems"][pv_system]
    else:
        feeder_mapping["pv_systems"][pv_system] = bus


def _handle_transformer(feeder_mapping, line):
    match = REGEX_TRANSFORMER.search(line)
    if match:
        groupdict = match.groupdict()
        transformer = groupdict["transformer"]
        if transformer in feeder_mapping["transformers"]:
            logger.warning("Detected duplicate transformer=%s", transformer)
            return

        sections = line.split("wdg=")
        # First section does not contain wdg + bus.
        assert len(sections) == int(groupdict["windings"]) + 1, line
        buses = []
        for i, section in enumerate(sections):
            if i == 0:
                continue
            match = REGEX_TRANSFORMER_BUSES.search(section)
            assert match
            assert int(match.groupdict()["winding"]) == i
            bus = match.groupdict()["bus"]
            if bus not in buses:
                buses.append(bus)

        assert len(buses) >= 2
        t_buses = {
            "primary": buses[0],
            "secondary": buses[1],
        }
        _check_transformer_buses(feeder_mapping, transformer, t_buses)
        feeder_mapping["transformers"][transformer] = t_buses
    else:
        match = REGEX_TRANSFORMER_ALT.search(line)
        if not match:
            raise BadFormat(f"unsupported transformer format: {line}")

        groupdict = match.groupdict()
        transformer = groupdict["transformer"]
        if transformer in feeder_mapping["transformers"]:
            logger.warning("Detected duplicate transformer=%s", transformer)
            return

        buses = groupdict["buses"].split(",")
        assert len(buses) >= 2, line
        for i, bus in enumerate(buses):
            index = bus.find(".")
            if index == -1:
                raise BadFormat(f"unsupported bus format {bus}")
            buses[i] = bus[:index]
        t_buses = {
            "primary": buses[0],
            "secondary": buses[1],
        }
        _check_transformer_buses(feeder_mapping, transformer, t_buses)
        feeder_mapping["transformers"][transformer] = t_buses


def _make_feeder_dict():
    return {
        "bus_coords": {},
        "capacitors": {},
        "lines": {},
        "loads": {},
        "pv_systems": {},
        "transformers": {},
    }


def _process_bus_coords_file(mapping, filename):
    with open(filename) as f_in:
        for line in f_in:
            fields = line.split()
            if not fields:
                continue
            bus = fields[0]
            x = fields[1]
            y = fields[2]
            assert bus not in mapping
            mapping["bus_coords"][bus] = {"x": x, "y": y}


ELEMENT_HANDLERS = {
    "new capacitor.": _handle_capacitor,
    "new line.": _handle_line,
    "new load.": _handle_load,
    "new pvsystem.": _handle_pv_system,
    "new transformer.": _handle_transformer,
}


def _process_element_file(mapping, filename):
    with open(filename) as f_in:
        for line in f_in:
            for substring, handler in ELEMENT_HANDLERS.items():
                if substring in line.lower():
                    handler(mapping, line)


def _get_bus_coords_files(directory):
    for dirpath, _, filenames in os.walk(directory):
        for filename in filenames:
            if filename.lower() == "buscoords.dss":
                yield os.path.join(dirpath, filename)


def _get_dss_files(directory):
    for dirpath, _, filenames in os.walk(directory):
        for filename in filenames:
            if os.path.splitext(filename)[1] == ".dss" and filename.lower() != "buscoords.dss":
                yield os.path.join(dirpath, filename)


def get_bus_to_element(bus_to_elems, feeder_mapping, element_type):
    """Builds a dict that maps bus names to a list of attached elements.

    Parameters
    ----------
    feeder_mapping : dict
        dictionary created by this module at a feeder level
    element_type : str
        Only consider this element type.
    bus_to_elems : dict
        Output dictionary to fill in.

    Returns
    -------
    dict
        Example::

        {123456: [{"type": "pv_systems", "name": "pv_123456"}]}

    """
    if element_type in ("transformers", "lines"):
        raise Exception("not supported")
    for element, bus in feeder_mapping[element_type].items():
        item = {"type": element_type, "name": element}
        if bus not in bus_to_elems:
            bus_to_elems[bus] = [item]
        else:
            bus_to_elems[bus].append(item)


def get_element_coordinates(feeder_mapping, element_type, name):
    """Return the coordinates of the bus to which the element is attached.

    Parameters
    ----------
    feeder_mapping : dict
        dictionary created by this module at a feeder level
    element_type : str
        capacitors, lines, loads, etc.
    name : str
        Element name

    Returns
    -------
    dict | None
        None is returned if no coordinates are stored.

        Example output::

        {'x': '34374.509', 'y': '206624.15'}

        If element_type == 'lines'
        {'from': None, 'to': {'x': '34802.251', 'y': '206769.654'}}

    """
    bus = feeder_mapping[element_type][name]
    if element_type == "lines":
        from_coords = feeder_mapping["bus_coords"].get(bus["from"])
        to_coords = feeder_mapping["bus_coords"].get(bus["to"])
        return {"from": from_coords, "to": to_coords}
    if element_type == "transformers":
        bus = bus["primary"]

    return feeder_mapping["bus_coords"].get(bus)


def make_element_bus_mapping_file(file_obj, output_file):
    """Make a mapping of elements to attached buses in a model-inputs path.

    Parameters
    ----------
    text : str
        Text of a .dss file

    Returns
    -------
    dict

    """
    feeder_mapping = _make_feeder_dict()
    _process_element_file(feeder_mapping, file_obj)

    # Much of the data has missing bus coordinates for transformer secondary
    # buses. The transformer processing code above implemented a workaround,
    # and so now they have coordinates.
    # Now, we check buses connected to the rest of the elements.
    _check_bus_presence(feeder_mapping)

    write_element_bus_mapping(feeder_mapping, output_file)
    print(f"Wrote {output_file}")
    return feeder_mapping


def merge_feeder_mappings(mapping_main, mapping_new):
    assert sorted(list(mapping_main.keys())) == sorted(list(mapping_new.keys()))
    for element_type in mapping_new.keys():
        if element_type == "bus_coords":
            continue
        for element, data in mapping_new[element_type].items():
            if element in mapping_main[element_type]:
                logger.info("Overwriting element %s %s", element_type, element)
            mapping_main[element_type][element] = data


def make_element_bus_mapping(path):
    """Make a mapping of elements to attached buses in a model-inputs path.

    Parameters
    ----------
    path : str
        Path to model-inputs directory (created by generate-input-data)

    Returns
    -------
    dict
        Maps feeder name to feeder mapping file.

    """
    config_file = os.path.join(path, "configurations.json")
    if not os.path.exists(config_file):
        logger.error("Did not detect %s in '%s'. Please pass a model-inputs directory.",
                     config_file, path)
        sys.exit(1)

    feeders = [x for x in os.listdir(path) if os.path.isdir(os.path.join(path, x))]

    feeder_files = {}

    # Get the bus coordinates first so that we can ensure that all element
    # buses are present.
    for feeder in feeders:
        feeder_mapping = _make_feeder_dict()
        feeder_path = os.path.join(feeder, path)
        for filename in _get_bus_coords_files(feeder_path):
            _process_bus_coords_file(feeder_mapping, filename)

        for filename in _get_dss_files(path):
            _process_element_file(feeder_mapping, filename)

        # Much of the data has missing bus coordinates for transformer
        # secondary buses. The transformer processing code above implemented a
        # workaround, and so now they have coordinates.  Now, we check buses
        # connected to the rest of the elements.
        _check_bus_presence(feeder_mapping)

        output_file = os.path.join(path, f"bus_mapping_feeder__{feeder}.json")
        write_element_bus_mapping(feeder_mapping, output_file)
        feeder_files[feeder] = output_file
        print(f"Wrote {output_file}")

    return feeder_files


def write_element_bus_mapping(mapping, output_file):
    """Write the mapping to output_file."""
    with open(output_file, "w") as f_out:
        json.dump(mapping, f_out)
        logger.info("Wrote %s", output_file)


def main():
    global logger
    if len(sys.argv) != 2:
        print(f"Usage:  {sys.argv[0]} MODEL-INPUTS-DIRECTORY")
        sys.exit(1)

    path = sys.argv[1]
    level = logging.INFO
    log_file = os.path.join(path, "bus_mapping.log")
    logger = setup_logging("bus_mapping", log_file, console_level=logging.ERROR, file_level=level,
                           packages=["disco"])
    logger.info(get_cli_string())

    try:
        feeder_files = make_element_bus_mapping(path)
        summary_file = os.path.join(path, REGION_BUS_MAPPING_FILENAME)
        with open(summary_file, "w") as f_out:
            json.dump(feeder_files, f_out, indent=2)
            print(f"Wrote summary file {summary_file}")
        print(f"Check {log_file} for warnings")
    except Exception:
        logger.exception("Failed to make bus mapping for %s", path)
        raise


if __name__ == "__main__":
    main()
