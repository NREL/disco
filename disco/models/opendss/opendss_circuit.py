import json
import logging
import shutil
import sys
from pathlib import Path

import opendssdirect as odd
from dss import DSSJSONFlags
from opendssdirect._version import __version__ as opendssdirect_version
from pydantic import validator

from opendss_base_model import OpenDssBaseModel, OpenDssElementBaseModel
from generated_opendss_models import (
    Capacitor,
    EnergyMeter,
    Line,
    LineCode,
    Load,
    LoadShape,
    PVSystem,
    RegControl,
    Transformer,
)


logger = logging.getLogger(__name__)


class BusCoordinates(OpenDssBaseModel):
    x: float | None = None
    y: float | None = None


class Bus(OpenDssElementBaseModel):
    name: str
    coordinates: BusCoordinates
    distance: float
    kv_base: float
    nodes: list[int]
    num_nodes: int
    num_customers: int

    @validator("num_nodes")
    def check_num_nodes(cls, num_nodes, values):
        if "nodes" not in values:
            return num_nodes
        nodes = values["nodes"]
        if num_nodes != len(nodes):
            raise ValueError(f"{num_nodes=} must equal the length of {nodes=}")
        return num_nodes


class Circuit(OpenDssElementBaseModel):
    """Defines an OpenDSS Circuit."""

    kv_base: float | None

    def new_open_dss_string(self):
        return f"New Circuit.{self.name}"


class CircuitContainer(OpenDssBaseModel):
    """Container for all elements in the OpenDSS circuit."""

    circuit: Circuit
    buses: list[Bus]
    capacitors: list[Capacitor] = []
    energy_meters: list[EnergyMeter] = []
    line_codes: list[LineCode] = []
    lines: list[Line] = []
    load_shapes: list[LoadShape] = []
    loads: list[Load] = []
    pv_systems: list[PVSystem] = []
    reg_controls: list[RegControl] = []
    transformers: list[Transformer] = []
    opendssdirect_version: str

    def new_open_dss_string(self):
        return "\n".join(self.list_text_commands())

    def list_text_commands(self) -> list[str]:
        """Return a list of text commands that will create the OpenDSS circuit."""
        commands = ["Clear"]
        commands.append(self.circuit.new_open_dss_string())
        for _, elem_list in self._iter_element_lists():
            for elem in elem_list:
                commands.append(elem.new_open_dss_string())
        return commands

    def _iter_element_lists(self):
        for elem_list in (
            ("LoadShapes", self.load_shapes),
            ("LineCodes", self.line_codes),
            ("Lines", self.lines),
            ("Transformers", self.transformers),
            ("Capacitors", self.capacitors),
            ("Loads", self.loads),
            ("PVSystems", self.pv_systems),
            ("RegControls", self.reg_controls),
            ("EnergyMeters", self.energy_meters),
        ):
            yield elem_list

    def initialize_dss_circuit(self):
        """Initialize the circuit in OpenDSS."""
        for command in self.list_text_commands():
            odd.Text.Command(command)
        logger.info("Initialized circuit %s", self.circuit.name)

    def to_dss_files(self, directory: Path, overwrite=False):
        """Write the OpenDSS commands to create a circuit to a directory of files,
        one per element type.
        """
        _handle_overwrite(directory, overwrite)
        master_file = directory / "Master.dss"
        with open(master_file, "w", encoding="utf-8") as f_master:
            f_master.write("Clear\n\n")
            f_master.write(self.circuit.new_open_dss_string())
            f_master.write("\n")
            for elem_type_name, elem_list in self._iter_element_lists():
                filename = directory / f"{elem_type_name}.dss"
                with open(filename, "w", encoding="utf-8") as f_elem:
                    for elem in elem_list:
                        f_elem.write(elem.new_open_dss_string())
                        f_elem.write("\n")
                f_master.write(f"Redirect {filename.name}\n")
                with open(directory / "Buscoords.dss", "w", encoding="utf-8") as f_bus:
                    for bus in self.buses:
                        if (
                            bus.coordinates.x is not None
                            and bus.coordinates.y is not None
                        ):
                            f_bus.write(
                                f"{bus.name}, {bus.coordinates.x}, {bus.coordinates.y}\n"
                            )
            f_master.write("Solve\n")

        logger.info("Wrote circuit to %s", directory)

    def to_dss_file_format(self, directory: str):
        """Serialize the OpenDSS models in an OpenDSS directory structure."""
        self.initialize_dss_circuit()
        odd.Text.Command(f'Save circuit dir="{directory}"')
        logger.info("Saved OpenDSS circuit to %s", directory)

    def to_json_file(self, filename, indent=2):
        """Write the OpenDSS elements to a JSON file."""
        with open(filename, "w", encoding="utf-8") as f_out:
            f_out.write(self.json(by_alias=True, indent=indent))
        logger.info("Wrote circuit to %s", filename)

    @classmethod
    def from_dss_file(cls, filename: str):
        """Return an instance of Circuit by compiling an OpenDSS master file."""
        compile_circuit(filename)
        buses = create_buses()

        pv_systems = []
        for pv in export_class_to_dict("PVSystem"):
            pv_systems.append(PVSystem(**pv))

        line_names = set()
        flag = odd.Lines.First()
        while flag > 0:
            line_names.add(odd.Lines.Name())
            flag = odd.Lines.Next()

        # The EnergyMeter does not define the full name of its host element.
        energy_meters = []
        for meter in export_class_to_dict("EnergyMeter"):
            if meter["element"] in line_names:
                meter["element"] = f"Line.{meter['element']}"
            else:
                raise NotImplementedError(
                    f"EnergyMeter {meter} is not defined on a line"
                )
            energy_meters.append(meter)

        return cls(
            circuit=Circuit(
                name=odd.Circuit.Name(), kv_base=buses[0].kv_base if buses else None
            ),
            buses=create_buses(),
            capacitors=[Capacitor(**x) for x in export_class_to_dict("Capacitor")],
            energy_meters=energy_meters,
            line_codes=[LineCode(**x) for x in export_class_to_dict("LineCode")],
            lines=[Line(**x) for x in export_class_to_dict("Line")],
            load_shapes=[LoadShape(**x) for x in export_class_to_dict("LoadShape")],
            loads=[Load(**x) for x in export_class_to_dict("Load")],
            pv_systems=[PVSystem(**x) for x in export_class_to_dict("PVSystem")],
            transformers=[
                Transformer(**x) for x in export_class_to_dict("Transformer")
            ],
            opendssdirect_version=opendssdirect_version,
        )

    @classmethod
    def from_json_file(cls, filename: str):
        """Return an instance of Circuit by loading a JSON file."""
        with open(filename, "r", encoding="utf-8") as f_in:
            circuit = cls(**json.load(f_in))

        if opendssdirect_version != circuit.opendssdirect_version:
            logger.warning(
                "Current OpenDSSDirect.py version %s does not match the serialized version %s",
                opendssdirect_version,
                circuit.opendssdirect_version,
            )
        return circuit


def generate_json_schema(directory: Path, overwrite=False):
    """Generate JSON schema for all OpenDSS models."""
    _handle_overwrite(directory, overwrite)
    for name, cls in (
        ("LoadShape", LoadShape),
        ("LineCode", LineCode),
        ("Line", Line),
        ("Transformer", Transformer),
        ("Capacitor", Capacitor),
        ("Load", Load),
        ("PVSystem", PVSystem),
        ("RegControl", RegControl),
        ("EnergyMeter", EnergyMeter),
    ):
        filename = directory / f"{name}.json"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(cls.schema_json(indent=2))
    print(f"Wrote JSON schema to {directory}")


def _handle_overwrite(directory: Path, overwrite):
    if directory.exists():
        if overwrite:
            shutil.rmtree(directory)
        else:
            raise Exception(
                "{directory=} already exists. Choose a different path or pass overwrite=True."
            )
    directory.mkdir()


def compile_circuit(filename: str):
    """Compile an OpenDSS circuit from a master file."""
    odd.Text.Command(f"Redirect '{filename}'")
    logger.info("Compiled %s", filename)


def create_buses() -> list[Bus]:
    """Create Bus objects. Assumes that the circuit has been compiled."""
    buses = []

    for name in odd.Circuit.AllBusNames():
        odd.Circuit.SetActiveBus(name)
        # TODO: ensure energy meter is defined
        if odd.Bus.Coorddefined():
            coords = BusCoordinates(x=odd.Bus.X(), y=odd.Bus.Y())
        else:
            coords = BusCoordinates()
        bus = Bus(
            name=name,
            coordinates=coords,
            distance=odd.Bus.Distance(),
            kv_base=odd.Bus.kVBase(),
            nodes=odd.Bus.Nodes(),
            num_nodes=odd.Bus.NumNodes(),
            num_customers=odd.Bus.N_Customers(),
        )
        buses.append(bus)

    return buses


def export_class_to_dict(class_name: str) -> list[dict]:
    """Export all elements of type class_name to dictionaries.

    Parameters
    ----------
    class_name : str
        OpenDSS class, such as Load

    """
    odd.Basic.SetActiveClass(class_name)
    return json.loads(odd.ActiveClass.ToJSON(options=DSSJSONFlags.Full))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    if len(sys.argv) != 2:
        logger.error("Usage: python %s MASTER_FILE", sys.argv[0])
        sys.exit(1)

    container = CircuitContainer.from_dss_file(sys.argv[1])
    container.to_dss_files(Path("test_circuit"), overwrite=True)
    container.to_json_file("test_circuit.json")
    container2 = CircuitContainer.from_json_file("test_circuit.json")
    assert container == container2

    if Path("opendss_circuit").exists():
        shutil.rmtree("opendss_circuit")
    container.to_dss_file_format("opendss_circuit")
    generate_json_schema(Path("opendss_model_schema"), overwrite=True)
