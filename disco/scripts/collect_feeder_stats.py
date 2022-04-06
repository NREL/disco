"""Produces CSV files with feeder stats. Requires disco-transformed input directory."""

import re
import sys
from pathlib import Path


ELEMENTS = {
    "capacitors.dss": ["capacitor", "capcontrol"],
    "linecodes.dss":["linecode"],
    "lines.dss": ["line"],
    "loads.dss": ["load"],
    "loadshapes.dss": ["loadshape"],
    "pvshapes.dss": ["loadshape"],
    "pvsystems.dss": ["pvsystem"],
    "regulators.dss": ["regcontrol"],
    "transformers.dss": ["transformer"],
}


FIELDS = {
    "capcontrol": "cap_controls",
    "capacitor": "capacitors",
    "linecode": "line_codes",
    "line": "lines",
    "loadshape": "load_shapes",
    "load": "loads",
    "pvsystem": "pv_systems",
    "regcontrol": "reg_controls",
    "transformer": "transformers",
}

REGEX_PMPP = re.compile(r"new pvsystem.*\spmpp=([\d\.]+)", re.IGNORECASE)


def count_element_types(filename: Path, element: str):
    count = 0
    for line in filename.read_text().splitlines():
        if line.strip().lower().startswith(f"new {element}"):
            count += 1
    return count


def sum_pmpps(filename: Path):
    total = 0
    count = 0
    for line in filename.read_text().splitlines():
        match = REGEX_PMPP.search(line)
        if match:
            pmpp = float(match.group(1))
            total += pmpp
            count += 1
    return total, count


def collect_feeder_counts(path: Path):
    counts = {}
    for filename in path.iterdir():
        elements = ELEMENTS.get(filename.name.lower())
        if elements is not None:
            for element in elements:
                if element not in counts:
                    counts[element] = 0
                counts[element] += count_element_types(filename, element)
    return counts


def main():
    if len(sys.argv) == 1:
        print(f"Usage: python {sys.argv[0]} SUBSTATION_PATH", file=sys.stderr)
        sys.exit(1)

    base_path = Path(sys.argv[1])
    if not base_path.exists():
        print(f"{base_path} does not exist", file=sys.stderr)
        sys.exit(1)

    feeder_stats = []
    pv_stats = []
    for substation_path in base_path.iterdir():
        if substation_path.is_dir():
            for feeder_path in substation_path.iterdir():
                dss_path = feeder_path / "OpenDSS"
                if dss_path.is_dir():
                    counts = collect_feeder_counts(dss_path)
                    counts["substation"] = substation_path.name
                    counts["feeder"] = feeder_path.name
                    feeder_stats.append(counts)
                pv_path = feeder_path / "PVDeployments"
                if pv_path.is_dir():
                    for filename in pv_path.iterdir():
                        if filename.suffix == ".dss":
                            name = filename.name.replace(filename.suffix, "")
                            # sum_pmpps assumes that Pmpp is always defined.
                            # If that is incorrect, use count_element_types instead.
                            pmpp, count = sum_pmpps(filename)
                            #count = count_element_types(filename, "pvsystem")
                            pv_stats.append({"job_name": name, "pv_systems": count, "pmpp": pmpp})

    if feeder_stats:
        output_file = base_path / "feeder_stats.csv"
        header = ["substation", "feeder"] + list(FIELDS.values())
        with open(output_file, "w") as f_out:
            f_out.write(",".join(header))
            f_out.write("\n")
            for feeder in feeder_stats:
                values = [feeder["substation"], feeder["feeder"]]
                for field in FIELDS:
                    values.append(feeder.get(field, ""))
                f_out.write(",".join([str(x) for x in values]))
                f_out.write("\n")
        print(f"Created {output_file}")
    else:
        print(f"Did not find any feeder files in {base_path}. Did you run `disco transform-model` to produce it?")

    if pv_stats:
        output_file = base_path / "pv_system_stats.csv"
        fields = ["job_name", "pv_systems", "pmpp"]
        with open(output_file, "w") as f_out:
            f_out.write(",".join(fields))
            f_out.write("\n")
            for row in pv_stats:
                values = ",".join([str(row[x]) for x in fields])
                f_out.write(values)
                f_out.write("\n")
        print(f"Created {output_file}")
    else:
        print(f"Did not find any PVSystem files in {base_path}")

if __name__ == "__main__":
    main()
