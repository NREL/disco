"""Implements functionality for QSTS inputs."""


from collections import namedtuple
import enum
import logging
import os
import re

from jade.jobs.job_inputs_interface import JobInputsInterface
from jade.exceptions import InvalidParameter
from jade.utils.utils import handle_file_not_found, handle_key_error
from disco.enums import get_placement_from_value, get_scale_from_value, \
    SCALE_MAPPING


logger = logging.getLogger(__name__)


class SourceTree2ModelInputs(JobInputsInterface):
    """Implements functionality for Source Tree 2 inputs."""

    _PV_DEPLOYMENTS = os.path.join("PVDeployments", "new")
    _REGEX_DCAC_RATIO = re.compile(r"DCAC([\d\.]+)")
    _KEYS_TYPE = namedtuple(
        "SourceTree2Keys", "feeder, dcac_ratio, scale, placement"
    )

    def __init__(self, base_directory):
        """Constructs SourceTree2ModelInputs.

        Parameters
        ----------
        base_directory : str

        """
        self._base = base_directory
        self._inputs_dir = os.path.join(self._base, "inputs")

        if not os.path.exists(self._base):
            raise InvalidParameter("inputs directory does not exist: {}"
                                   .format(self._base))


        self._parameters = self._parse_directories()

        logger.debug("Created %s at %s", self.__class__.__name__,
                     self._base)

    @property
    def base_directory(self):
        return self._base

    def create_key(self, feeder, dcac_ratio, scale, placement):
        """Create a parameter key for accessing deployments and penetration
        levels.

        Parameters
        ----------
        feeder : str
        dcac_ratio : float
        scale : Scale
        placement : Placement

        Returns
        -------
        namedtuple

        """
        return self._KEYS_TYPE._make((feeder, dcac_ratio, scale, placement))

    def get_available_parameters(self):
        """Return a dictionary containing all available parameters.

        Returns
        -------
        dict
            dictionary layout::

                {
                    (Feeder, DcacRatio, Scale, Placement) : {
                        deployments: Set(
                            penetration_levels,
                        )
                    }
                }

        """
        return self._parameters

    def get_deployment_file(self, key, deployment, penetration_level):
        """Get the path to an input deployment file for the given parameters.

        Parameters
        ----------
        key : namedtuple
        deployment : int
        penetration_level : int

        Returns
        -------
        str
            full path to file

        """
        filename = os.path.join(
            self._inputs_dir,
            key.feeder,
            self._PV_DEPLOYMENTS,
            self._get_dcac_directory(key.dcac_ratio),
            SCALE_MAPPING[key.scale],
            key.placement.value,
            str(deployment),
            f"PV_Gen_{deployment}_{penetration_level}.txt"
        )

        if not os.path.exists(filename):
            raise InvalidParameter(f"file does not exist: {filename}")
        return filename

    def get_dss_filename(self, feeder, filename):
        """Return the path to DSS file.

        Parameters
        ----------
        feeder : str
        filename : str

        Returns
        -------
        str
            path to file

        Raises
        ------
        InvalidParameter
            Raised if the file does not exist.

        """
        dss_filename = os.path.join(self._inputs_dir, feeder, "OpenDSS",
                                    filename)
        if not os.path.exists(dss_filename):
            raise InvalidParameter(f"file does not exist: {dss_filename}")

        return dss_filename

    def get_loadshape_directory(self, feeder):
        """Return the path to the load shape files.

        Parameters
        ----------
        feeder : str

        Returns
        -------
        str

        """
        return os.path.join(self._inputs_dir, feeder, "LoadShapes")

    def get_opendss_directory(self, feeder):
        """Return the path to the OpenDSS files.

        Parameters
        ----------
        feeder : str

        Returns
        -------
        str

        """
        return os.path.join(self._inputs_dir, feeder, "OpenDSS")

    def list_feeders(self):
        """List available feeders.

        Returns
        -------
        list of str
            available feeders

        """
        return self._list_available_params("feeder")

    def list_dcac_ratios(self):
        """List available DC/AC ratios.

        Returns
        -------
        list of float
            available DC/AC ratios

        """
        return self._list_available_params("dcac_ratio")

    def list_scales(self):
        """List available scales.

        Returns
        -------
        list of Scale
            available scales

        """
        return self._list_available_params("scale")

    def list_placements(self):
        """List available placements.

        Returns
        -------
        list of Placement
            available placements

        """
        return self._list_available_params("placement")

    @handle_key_error
    def list_deployments(self, key):
        """List available deployments.

        Parameters
        ----------
        key : namedtuple

        Returns
        -------
        list of int
            available deployments

        """
        deployments = list(self._parameters[key].keys())
        deployments.sort()
        return deployments

    @handle_key_error
    def list_penetration_levels(self, key, deployment):
        """List available penetration levels.

        Parameters
        ----------
        key : namedtuple
        deployment : int

        Returns
        -------
        list of int
            available penetration levels

        """
        levels = list(self._parameters[key][deployment])
        levels.sort()
        return levels

    def list_penetration_levels_by_step(self, key, deployment, step=10):
        """List available penetration levels by step.

        Parameters
        ----------
        key : namedtuple
        deployment : int
        step : int
            Must be a multiple of 5.

        Returns
        -------
        list of int
            available penetration levels

        Raises
        ------
        InvalidParameter
            Raised if key or deployment is not valid.

        """
        available_levels = self.list_penetration_levels(key, deployment)

        start = available_levels[0]
        stop = available_levels[-1] + 1

        # Convert to set for faster searches.
        available_levels = set(available_levels)

        levels = []
        for level in range(start, stop, step):
            if level not in available_levels:
                raise InvalidParameter(
                    "penetration level {} is not available for {}".format(
                        level, (key, deployment))
                )

            levels.append(level)

        return levels

    @staticmethod
    def _get_items_from_directory(path):
        """Basically just strips out files like README.md."""
        return [x for x in os.listdir(path)
                if os.path.isdir(os.path.join(path, x))]

    def _get_dcac_ratios_from_directory(self, path):
        ratios = []
        for item in self._get_items_from_directory(path):
            match = self._REGEX_DCAC_RATIO.search(item)
            if match:
                ratios.append(float(match.group(1)))
        return ratios

    @staticmethod
    def _get_dcac_directory(dcac_ratio):
        return "DCAC" + str(dcac_ratio)

    def _list_available_params(self, param):
        params = set()
        is_enum = False
        for key in self._parameters:
            value = key._asdict()[param]
            assert value is not None
            params.add(value)
            if isinstance(value, enum.Enum):
                is_enum = True

        key = None
        if is_enum:
            key = lambda x: x.value
        return sorted(list(params), key=key)

    @handle_file_not_found
    def _list_feeders(self):
        feeders = self._get_items_from_directory(self._inputs_dir)
        feeders.sort()
        return feeders

    @handle_file_not_found
    def _list_dcac_ratios(self, feeder):
        dcac_path = os.path.join(
            self._inputs_dir,
            feeder,
            self._PV_DEPLOYMENTS,
        )
        ratios = self._get_dcac_ratios_from_directory(dcac_path)

        ratios.sort()
        return ratios

    @handle_file_not_found
    def _list_scales(self, feeder, dcac_ratio):
        scale_path = os.path.join(
            self._inputs_dir,
            feeder,
            self._PV_DEPLOYMENTS,
            self._get_dcac_directory(dcac_ratio),
        )
        scales = [get_scale_from_value(x)
                  for x in self._get_items_from_directory(scale_path)]
        scales.sort(key=lambda x: x.value)
        return scales

    @handle_file_not_found
    def _list_placements(self, feeder, dcac, scale):
        placement_path = os.path.join(
            self._inputs_dir,
            feeder,
            self._PV_DEPLOYMENTS,
            self._get_dcac_directory(dcac),
            SCALE_MAPPING[scale],
        )
        placements = [get_placement_from_value(x)
                      for x in self._get_items_from_directory(
                          placement_path)]
        placements.sort(key=lambda x: x.value)
        return placements

    @handle_file_not_found
    def _list_deployments(self, feeder, dcac, scale, placement):
        deployment_path = os.path.join(
            self._inputs_dir,
            feeder,
            self._PV_DEPLOYMENTS,
            self._get_dcac_directory(dcac),
            SCALE_MAPPING[scale],
            placement.value,
        )
        deployments = self._get_items_from_directory(deployment_path)
        return sorted([int(x) for x in deployments])

    @handle_file_not_found
    def _list_penetration_levels(self, feeder, dcac, scale, placement,
                                 deployment):
        penetration_path = os.path.join(
            self._inputs_dir,
            feeder,
            self._PV_DEPLOYMENTS,
            self._get_dcac_directory(dcac),
            SCALE_MAPPING[scale],
            placement.value,
            str(deployment),
        )

        levels = []
        regex = re.compile(r"PV_Gen_{}_(\d+)\.txt".format(deployment))
        for filename in os.listdir(penetration_path):
            match = regex.search(filename)
            if match:
                levels.append(int(match.group(1)))

        return sorted(levels)

    def _parse_directories(self):
        data = {}
        for feeder in self._list_feeders():
            self._parse_dcacs(data, feeder)

        return data

    def _parse_dcacs(self, data, feeder):
        for dcac in self._list_dcac_ratios(feeder):
            self._parse_scales(data, feeder, dcac)

    def _parse_scales(self, data, feeder, dcac):
        for scale in self._list_scales(feeder, dcac):
            self._parse_placements(data, feeder, dcac, scale)

    def _parse_placements(self, data, feeder, dcac, scale):
        for placement in self._list_placements(feeder, dcac, scale):
            self._parse_deployments(data, feeder, dcac, scale, placement)

    def _parse_deployments(self, data, feeder, dcac, scale, placement):
        key = self._KEYS_TYPE(feeder, dcac, scale, placement)
        data[key] = {}
        for deployment in self._list_deployments(feeder, dcac, scale,
                                                 placement):
            data[key][deployment] = set()
            self._parse_penetrations(data[key][deployment], feeder, dcac,
                                     scale, placement, deployment)

    def _parse_penetrations(self, data, feeder, dcac, scale, placement,
                            deployment):
        for level in self._list_penetration_levels(feeder, dcac, scale,
                                                   placement, deployment):
            data.add(level)
