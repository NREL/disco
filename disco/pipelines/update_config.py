import pathlib

from jade.utils.utils import load_data, dump_data


def set_hc_postprocess_blocked_by(commands_file):
    """Update blocked_by of hosting capacity postprocess job"""
    path = pathlib.Path(commands_file)
    command = path.read_text().split("\n")[0]
    config_file = command.split("=")[-1]
    data = load_data(config_file)
    
    if len(data["jobs"]) <= 1:
        return
    
    for i in range(1, len(data["jobs"])):
        data["jobs"][i]["blocked_by"].append(i)
    dump_data(data, config_file, indent=2)
