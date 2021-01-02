"""Factory functions for creating data generators."""

from jade.exceptions import InvalidParameter
from jade.utils.timing_utils import timed_info
from jade.utils.utils import load_data
from .open_dss_generator import OpenDssGenerator


@timed_info
def read_config_data(config_file):
    """Return a model generator based on the config file."""
    data = load_data(config_file)

    if data["type"] == "GemModel":
        cls = OpenDssGenerator
    else:
        raise InvalidParameter(f"unsupported model type {data['type']}")

    generator = cls(data)
    return generator
