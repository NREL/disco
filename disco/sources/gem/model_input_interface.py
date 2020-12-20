"""Defines interface for model input data."""

import abc


class ModelInputDataInterface(abc.ABC):
    """Defines interface for model input data."""

    @abc.abstractmethod
    def generate_output_data(self, output_dir, include_pv_systems):
        """Generate output data.

        Parameters
        ----------
        output_dir : str
            Directory in which to generate output data.
        include_pv_systems : bool
            Whether to include PVSystems.dss in the simulation.

        """
