import os

from jade.utils.utils import dump_data

from .base import FORMAT_FILENAME, TYPE_KEY


def create_model_format_file(output, model_name):
    data = {TYPE_KEY: model_name}
    filename = os.path.join(output, FORMAT_FILENAME)
    dump_data(data, filename)
    return filename
