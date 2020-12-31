"""Download EPRI source data of J1, K1, and M1 feeders."""

import logging
import os
import shutil
import tempfile
import zipfile
from urllib.parse import urlparse
from urllib.request import urlopen

from jade.utils.utils import dump_data


logger = logging.getLogger(__name__)


EPRI_FEEDER_MODELS = {
    "J1": "https://dpv.epri.com/media/feeder_j1_opendss_model.zip",
    "K1": "https://dpv.epri.com/media/feeder_k1_opendss_model.zip",
    "M1": "https://dpv.epri.com/media/feeder_m1_opendss_model.zip",
}


def download_epri_feeder_opendss_data(feeder, output_directory=None):
    """Download EPRI feeder OpenDSS model from website.

    Parameters
    ----------
    feeder : str
        The feeder name
    outdir : str
        The output directory for downloaded OpenDSS model.

    Returns
    -------
    str
        the directory of downloaded OpenDSS model.

    Raises
    ------
    ValueError
        Invalid feeder, choose from - 'J1', 'K1', 'M1'.
    """
    if feeder not in EPRI_FEEDER_MODELS:
        raise ValueError("Invalid feeder, choose from - 'J1', 'K1', 'M1'.")

    output_directory = output_directory or tempfile.gettempdir()
    opendss_directory = os.path.join(output_directory, f"{feeder}")

    if os.path.exists(opendss_directory):
        return opendss_directory

    os.makedirs(opendss_directory)
    try:
        url = EPRI_FEEDER_MODELS[feeder]
        # download zip file
        file_name = os.path.basename(urlparse(url).path)
        zip_file = os.path.join(opendss_directory, file_name)
        with urlopen(url) as response, open(zip_file, "wb") as f:
            shutil.copyfileobj(response, f)
        # extract zip file
        with zipfile.ZipFile(zip_file) as f:
            for info in f.namelist():
                file_name = os.path.basename(info)
                if not file_name:
                    continue
                dst_file = os.path.join(opendss_directory, file_name)
                with f.open(info) as src, open(dst_file, "wb") as dst:
                    shutil.copyfileobj(src, dst)
        os.remove(zip_file)
    except Exception:
        shutil.rmtree(opendss_directory)
        raise

    return opendss_directory


def define_epri_source_format(output_directory=None):
    data = {
        "type": "EpriModel"
    }
    
    if output_directory and os.path.exists(output_directory):
        filename = os.path.join(output_directory, "format.toml")
    else:
        filename = "format.toml"
    
    dump_data(data, filename)
