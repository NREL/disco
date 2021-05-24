"""Factory functions to create source models from source data"""

import os

from jade.exceptions import InvalidConfiguration
from jade.utils.utils import load_data
from disco.sources import EpriModel
from disco.sources import GemModel
from disco.sources import SourceTree1Model
from disco.sources import SourceTree2Model
from .base import FORMAT_FILENAME, TYPE_KEY

SUPPORTED_FORMATS = {
    "EpriModel": EpriModel,
    "GemModel": GemModel,
    "SourceTree1Model": SourceTree1Model,
    "SourceTree2Model": SourceTree2Model,
}


def list_subcommands(input_path):
    """List the available transform subcommands for the source model.

    Parameters
    ----------
    input_path : str
        filename or directory, depending on source data type

    Returns
    -------
    list

    """
    source_model = make_source_model(input_path)
    return source_model.list_transform_subcommands()


def make_source_model(input_path):
    """Construct the correct source model for input_path.

    Parameters
    ----------
    input_path : str
        filename or directory, depending on source data type

    Returns
    -------
    class
        derived from BaseSourceDataModel

    Raises
    ------
    InvalidConfiguration
        Raised if the format is not specified or supported.

    """
    if os.path.isdir(input_path):
        source_type = _make_source_model_from_directory(input_path)
    else:
        source_type = _make_source_model_from_file(input_path)

    if source_type not in SUPPORTED_FORMATS:
        raise InvalidConfiguration(f"{source_type} is not a supported format")

    return SUPPORTED_FORMATS[source_type]


def _make_source_model_from_directory(input_path):
    format_file = os.path.join(input_path, FORMAT_FILENAME)
    if not os.path.exists(format_file):
        raise InvalidConfiguration(f"{FORMAT_FILENAME} is not present in {input_path}")

    config = load_data(format_file)
    source_type = config.get(TYPE_KEY)
    if source_type is None:
        raise InvalidConfiguration(f"{TYPE_KEY} is not defined in {format_file}")

    return source_type


def _make_source_model_from_file(input_path):
    config = load_data(input_path)
    source_type = config.get(TYPE_KEY)
    if source_type is None:
        raise InvalidConfiguration(f"{TYPE_KEY} is not defined in {input_path}")

    return source_type
