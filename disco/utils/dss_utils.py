"""Contains OpenDSS utility functions."""

import fileinput
import logging
import re

logger = logging.getLogger(__name__)


def read_capacitor_changes(event_log):
    """Read the capacitor state changes from an OpenDSS event log.

    Parameters
    ----------
    event_log : str
        Path to event log

    Returns
    -------
    dict
        Maps capacitor names to count of state changes.

    """
    capacitor_changes = {}
    regex = re.compile(r"(Capacitor\.\w+)")

    data = read_event_log(event_log)
    for row in data:
        match = regex.search(row["Element"])
        if match:
            name = match.group(1)
            if name not in capacitor_changes:
                capacitor_changes[name] = 0
            action = row["Action"].replace("*", "")
            if action in ("OPENED", "CLOSED", "STEP UP"):
                capacitor_changes[name] += 1

    return capacitor_changes


def read_event_log(filename):
    """Return OpenDSS event log information.

    Parameters
    ----------
    filename : str
        path to event log file.


    Returns
    -------
    list
        list of dictionaries (one dict for each row in the file)

    """
    data = []

    with open(filename) as f_in:
        for line in f_in:
            tokens = [x.strip() for x in line.split(",")]
            row = {}
            for token in tokens:
                name_and_value = [x.strip() for x in token.split("=")]
                name = name_and_value[0]
                value = name_and_value[1]
                row[name] = value
            data.append(row)

    return data


def comment_out_leading_strings(filename, strings):
    """Insert a comment character on any line that begins with one of strings.

    Parameters
    ----------
    filename : str
    strings : list

    """
    with fileinput.input(files=[filename], inplace=True) as f_in:
        for line in f_in:
            if line.lower().startswith(strings):
                line = "!" + line
            print(line, end="")
