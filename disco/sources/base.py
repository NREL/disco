import fileinput
import logging
import os
import re
import shutil
from abc import ABC, abstractmethod
from pathlib import Path

from disco.enums import SimulationType, SimulationHierarchy
from disco.exceptions import AnalysisConfigurationException
from disco.models.base import OpenDssDeploymentModel
from disco.utils.dss_utils import comment_out_leading_strings

FORMAT_FILENAME = "format.toml"
TYPE_KEY = "type"

SOURCE_CONFIGURATION_FILENAME = "configurations.json"

DEFAULT_SNAPSHOT_IMPACT_ANALYSIS_PARAMS = {
    "output_dir": "snapshot-models",
    "start_time": "2020-04-15T14:00:00",
    "end_time": "2020-04-15T14:00:00",
    "simulation_type": SimulationType.SNAPSHOT.value,
}

DEFAULT_TIME_SERIES_IMPACT_ANALYSIS_PARAMS = {
    "output_dir": "time-series-models",
    "start_time": "2020-01-01T00:00:00",
    "end_time": "2020-01-02T00:00:00",
    "simulation_type": SimulationType.QSTS.value,
    "step_resolution": 900,
}

DEFAULT_UPGRADE_COST_ANALYSIS_PARAMS = {
    "output_dir": "upgrade-models",
    "start_time": "2020-01-01T00:00:00",
    "end_time": "2020-01-08T00:00:00",
    "simulation_type": SimulationType.SNAPSHOT.value,
}

DEFAULT_PV_DEPLOYMENTS_DIRNAME = "hc_pv_deployments"

logger = logging.getLogger(__name__)


class BaseSourceDataModel(ABC):
    """Base class for source data models"""

    @staticmethod
    @abstractmethod
    def get_transform_subcommand(name):
        """Return the click transform-model command.

        Returns
        -------
        click.command

        """

    @staticmethod
    @abstractmethod
    def list_transform_subcommands():
        """List the available click transform-model subcommands.

        Returns
        -------
        list
            List of click command objects

        """

    @classmethod
    @abstractmethod
    def transform(cls, config, simulation_model, output_path):
        """Transform the input data to a DISCO data model.

        Parameters
        ----------
        config : dict
        simulation_model : BaseAnalysisModel
        output_path : str

        """


class BaseOpenDssModel(BaseSourceDataModel, ABC):
    """Base model for a single OpenDSS configuration"""

    # Example line:
    # New Loadshape.Residential1234 npts=123456 minterval=5 mult=[file=../BuildingData/Dataset_12_34/Residential/RES1234/LoadProfiles/12345.csv]
    REGEX_LOAD_SHAPE_DATA_FILE = re.compile(r"file=([\.\w/\\-]+)")

    @property
    @abstractmethod
    def substation(self):
        """The substation name"""

    @property
    @abstractmethod
    def feeder(self):
        """The feeder name"""

    @property
    @abstractmethod
    def dc_ac_ratio(self):
        """The DC/AC ratio"""

    @property
    def kva_to_kw_rating(self):
        """The kva_to_kw_rating"""
        return 1.0

    @property
    @abstractmethod
    def name(self):
        """The name of the deployment"""

    @property
    @abstractmethod
    def loadshape_directory(self):
        """The directory containing load shapes"""

    @property
    @abstractmethod
    def opendss_directory(self):
        """The directory of OpenDSS model"""

    @property
    @abstractmethod
    def master_file(self):
        """Master file of OpenDSS model"""

    @property
    @abstractmethod
    def metadata_directory(self):
        """The directory of project metadata"""

    @property
    def project_data(self):
        """PyDSS controllers"""
        return {}

    @property
    @abstractmethod
    def pydss_controllers(self):
        """PyDSS controllers"""

    @property
    @abstractmethod
    def pv_locations(self):
        """PV systems file of OpenDSS model."""

    def _create_common_files(self, workspace, copy_load_shape_data_files, hierarchy):
        """Create files common to all deployments.

        Parameters
        ----------
        workspace : OpenDssFeederWorkspace
        copy_load_shape_data_files : bool

        """
        self._copy_files(
            src_dir=self.opendss_directory,
            dst_dir=workspace.opendss_directory,
            copy_load_shape_data_files=copy_load_shape_data_files,
        )
        if hierarchy == SimulationHierarchy.FEEDER and not os.path.exists(self.master_file):
            raise AnalysisConfigurationException(f"{self.master_file} is not present")

        if os.path.exists(self.master_file):
            # This may overwrite a file copied above.
            shutil.copyfile(self.master_file, workspace.master_file)
            # If you modify this list, compare the similar list in scripts/copy_smart_ds_dataset.py
            # The two locations may have different goals, and so do not share the same list reference.
            strings_to_remove = (
                "solve",
                "batchedit fuse",
                "new energymeter",
                "new monitor",
                "export monitors",
                "plot",
            )
            comment_out_leading_strings(workspace.master_file, strings_to_remove)

        if self.loadshape_directory is not None:
            self._copy_files(
                src_dir=self.loadshape_directory,
                dst_dir=workspace.loadshape_directory,
                copy_load_shape_data_files=copy_load_shape_data_files,
            )
        
        if self.metadata_directory is not None and os.path.exists(self.metadata_directory):
            self._copy_files(
                src_dir=self.metadata_directory,
                dst_dir=workspace.metadata_directory
            )

    def create_base_case(self, name, outdir, copy_load_shape_data_files=False):
        """Create a base case with no added PV.

        Parameters
        ----------
        name : str
            The job name
        outdir : str
            The base directory of opendss feeder model.
        copy_load_shape_data_files : bool

        Returns
        -------
        OpenDssDeploymentModel

        """
        workspace = OpenDssFeederWorkspace(outdir)
        if not os.path.exists(workspace.master_file):
            self._create_common_files(
                workspace,
                copy_load_shape_data_files,
                SimulationHierarchy.FEEDER,
            )

        deployment_file = Path(workspace.pv_deployments_directory) / (name + ".dss")
        rel_path = self._get_master_file_relative_path(deployment_file, Path(workspace.master_file))
        with open(deployment_file, "w") as fw:
            fw.write(f"Redirect {rel_path}\n")
            fw.write("\nSolve\n")

        return OpenDssDeploymentModel.validate(
            dict(
                deployment_file=str(deployment_file),
                substation=self.substation,
                feeder=self.feeder,
                dc_ac_ratio=self.dc_ac_ratio,
                directory=outdir,
                kva_to_kw_rating=self.kva_to_kw_rating,
                project_data=self.project_data,
                pydss_controllers=self.pydss_controllers,
            )
        )

    def create_substation_base_case(self, name, outdir, copy_load_shape_data_files=False):
        """Create a base case with no added PV.

        Parameters
        ----------
        name : str
            The job name
        outdir : str
            The base directory of opendss substation model.
        copy_load_shape_data_files : bool

        Returns
        -------
        OpenDssDeploymentModel

        """
        workspace = OpenDssSubstationWorkspace(outdir)
        if not os.path.exists(workspace.master_file):
            self._create_common_files(
                workspace,
                copy_load_shape_data_files,
                SimulationHierarchy.SUBSTATION,
            )

        deployment_file = Path(workspace.pv_deployments_directory) / (name + ".dss")
        rel_path = self._get_master_file_relative_path(deployment_file, Path(workspace.master_file))
        with open(deployment_file, "w") as fw:
            fw.write(f"Redirect {rel_path}\n")
            fw.write("\nSolve\n")

        return OpenDssDeploymentModel.validate(
            dict(
                deployment_file=str(deployment_file),
                substation=self.substation,
                feeder="None",
                dc_ac_ratio=self.dc_ac_ratio,
                directory=outdir,
                kva_to_kw_rating=self.kva_to_kw_rating,
                project_data=self.project_data,
                pydss_controllers=None,
            )
        )

    def create_deployment(
        self,
        name,
        outdir,
        hierarchy,
        pv_profile=None,
        copy_load_shape_data_files=False,
        strip_load_shape_profiles=False
    ):
        """Create the deployment.

        Parameters
        ----------
        name : str
            The deployment name
        outdir : str
            The base directory of opendss feeder model.
        hierarchy : SimulationHierarchy
        pv_profile : str
            Optional load shape profile name to apply to all PVSystems
        copy_load_shape_data_files : bool
        strip_load_shape_profiles : bool
            Strip load shape profiles from DSS models.

        Returns
        -------
        OpenDssDeploymentModel

        """
        workspace = OpenDssFeederWorkspace(outdir)
        if not os.path.exists(workspace.master_file):
            self._create_common_files(workspace, copy_load_shape_data_files, hierarchy)
        
        if strip_load_shape_profiles:
            self._strip_load_profiles_from_loads_file(workspace)
            self._strip_shape_files_from_master_file(workspace)

        deployment_file = self._create_deployment_file(
            name=name,
            workspace=workspace,
            hierarchy=hierarchy,
            pv_profile=pv_profile,
            strip_load_shape_profiles=strip_load_shape_profiles
        )
        if hierarchy == SimulationHierarchy.FEEDER:
            directory = outdir
            feeder = self.feeder
        else:
            directory = os.path.dirname(outdir)
            feeder = "None"
        return OpenDssDeploymentModel.validate(
            dict(
                deployment_file=deployment_file,
                substation=self.substation,
                feeder=feeder,
                dc_ac_ratio=self.dc_ac_ratio,
                directory=directory,
                kva_to_kw_rating=self.kva_to_kw_rating,
                project_data=self.project_data,
                pydss_controllers=self.pydss_controllers,
            )
        )

    @staticmethod
    def _copy_files(src_dir, dst_dir, exclude=None, copy_load_shape_data_files=False):
        """Copy files from src to dst directory.

        Parameters
        ----------
        src_dir : str
            Source directory
        dst_dir : str
            Destination directory
        exclude : list | str, optional
            Excluded file names from copy, by default None
        copy_load_shape_data_files : bool

        """
        if not exclude:
            exclude = []

        if isinstance(exclude, str):
            exclude = [exclude]

        for name in os.listdir(src_dir):
            if name in exclude or os.path.isdir(os.path.join(src_dir, name)):
                continue
            src_file = os.path.join(src_dir, name)
            dst_file = os.path.join(dst_dir, name)
            shutil.copyfile(src_file, dst_file)
            if os.path.splitext(dst_file)[1] in (".dss", ".txt"):
                if copy_load_shape_data_files:
                    BaseOpenDssModel.copy_any_load_shape_data_files(Path(src_file), Path(dst_file))
                else:
                    BaseOpenDssModel.make_data_file_references_absolute(
                        os.path.abspath(src_dir), dst_file
                )

    def _create_deployment_file(self, name, workspace, hierarchy, pv_profile=None, strip_load_shape_profiles=False):
        """Create deployment dss file.

        Parameters
        ----------
        name : str
            Name of deployment.
        workspace : OpenDssFeederWorkspace
            Instance of OpenDssFeederWorkspace
        hierarchy : SimulationHierarchy
        pv_profile : str | dict
            Optional load shape profile name to apply to PVSystems.
            If str, apply the name to all PVSystems.
            If dict, keys are PVSystem names and values are profile names.
        strip_load_shape_profiles: bool
            Strip load shape profiles from PVsystems if True, default False.
        """
        deployment_file = Path(workspace.pv_deployments_directory) / (name + ".dss")
        rel_path = self._get_master_file_relative_path(deployment_file, Path(workspace.master_file))
        if not self.pv_locations:
            with open(deployment_file, "w") as fw:
                fw.write(f"Redirect {rel_path}\n\n")
                fw.write("\nSolve\n")
            return str(deployment_file)

        regex1 = re.compile("yearly=[\w\.\-_]+")
        regex2 = re.compile(r"new pvsystem\.([^\s]+)")
        with open(deployment_file, "w") as fw, fileinput.input(self.pv_locations) as fr:
            if hierarchy == SimulationHierarchy.FEEDER:
                fw.write(f"Redirect {rel_path}\n\n")
            for line in fr:
                
                # Exclude load profiles for upgrades to reduce simulation time.
                if strip_load_shape_profiles:
                    match = regex1.search(line)
                    if match:
                        value = match.group(0)
                        line = " ".join(line.split(value)).strip() + "\n"
                
                elif pv_profile is not None:
                    lowered = line.lower()
                    if "new pvsystem" in lowered and "yearly" not in lowered:
                        if isinstance(pv_profile, str):
                            profile = pv_profile
                        else:
                            match = regex2.search(lowered)
                            assert match, lowered
                            pv_system = match.group(1)
                            if pv_system not in pv_profile:
                                raise Exception(f"no profile found for {pv_system}")
                            profile = pv_profile[pv_system]
                        if profile is not None:
                            line = line.strip() + f" yearly={profile}\n"
                fw.write(line)

            if hierarchy == SimulationHierarchy.FEEDER:
                fw.write("\nSolve\n")

        return str(deployment_file)

    @staticmethod
    def copy_any_load_shape_data_files(src_file, dst_file):
        """Copy any referenced load shape data file into the destination directory.

        Parameters
        ----------
        src_file : Path
        dst_file : Path

        """
        # Feeder-level has an "OpenDSS" directory but substation-level
        # doesn't, hence this hack.
        is_feeder_level = "OpenDSS" in str(dst_file)
        if is_feeder_level:
            profiles_dir = dst_file.parent.parent / "profiles"
        else:
            profiles_dir = dst_file.parent / "profiles"
        # TODO: This could be optimized in the future. We could combine the caller's
        # copy of src_file to dst_file with this rewrite.
        with fileinput.input(files=[dst_file], inplace=True) as f:
            for line in f:
                matches = BaseOpenDssModel.REGEX_LOAD_SHAPE_DATA_FILE.findall(line)
                replacements = {}
                for match in matches:
                    src_data_file_rel_path = Path(match)
                    src_data_file_path = (src_file.parent / src_data_file_rel_path).resolve()
                    name = src_data_file_path.name
                    dst_data_file_path = profiles_dir / name
                    if not dst_data_file_path.exists():
                        shutil.copyfile(src_data_file_path, dst_data_file_path)
                        logger.debug("Copied load shape data file %s", dst_data_file_path)
                    if is_feeder_level:
                        replacements[match] = str(Path("..") / "profiles" / name)
                    else:
                        replacements[match] = str(Path("profiles") / name)
                for old, new in replacements.items():
                    line = line.replace(old, new)
                print(line, end="")

    def _get_master_file_relative_path(self, deployment_file, master_path):
        return Path("..") / (master_path.relative_to(deployment_file.parent.parent))

    @staticmethod
    def make_data_file_references_absolute(src_dir, filename):
        """Change the path to any data file referenced in a .dss file to its
        absolute path."""

        def replace_func(match):
            path = os.path.normpath(match.group(1).replace("\\", "/"))
            new_path = "file=" + os.path.normpath(os.path.join(src_dir, path))
            return new_path

        with fileinput.input(files=[filename], inplace=True) as f_in:
            for line in f_in:
                line = re.sub(BaseOpenDssModel.REGEX_LOAD_SHAPE_DATA_FILE, replace_func, line)
                print(line, end="")
    
    @staticmethod
    def _strip_shape_files_from_master_file(workspace):
        """Exclude load and pv shapes from master DSS model file"""
        new_lines = []
        with open(workspace.master_file, "r") as f:
            for line in f.readlines():
                lowered = line.strip().lower()
                if lowered.startswith("!"):
                    new_lines.append(line)
                    continue
                elif "redirect loadshapes.dss" in lowered or "redirect pvshapes" in lowered:
                    new_lines.append("!" + line)
                else:
                    new_lines.append(line)
        
        with open(workspace.master_file, "w") as f:
            f.writelines(new_lines)

    @staticmethod
    def _strip_load_profiles_from_loads_file(workspace):
        """Exclude load profiles from loads DSS model file"""
        loads = os.path.basename(workspace.loads_file)
        loads_in_master = False
        with open(workspace.master_file, "r") as f:
            for line in f.readlines():
                if line.strip().startswith("!"):
                    continue
                if loads in line:
                    loads_in_master = True
                    break
        
        if not loads_in_master:
            return
        
        regex = re.compile("yearly=[\w\.\-_]+")
        new_lines = []
        with open(workspace.loads_file, "r") as f:
            for line in f.readlines():
                if not line.strip():
                    continue
                matched = regex.search(line)
                if not matched:
                    new_lines.append(line)
                    continue
                value = matched.group(0)
                new_line = " ".join(line.split(value)).strip()
                new_lines.append(new_line + "\n")

        with open(workspace.loads_file, "w") as f:
            f.writelines(new_lines)


class OpenDssSubstationWorkspace:
    """Defines a substation and all dependent OpenDSS files."""

    def __init__(self, substation_directory):
        self._substation_directory = substation_directory
        self._create_directories()

    def _create_directories(self):
        os.makedirs(self.substation_directory, exist_ok=True)
        os.makedirs(self.pv_deployments_directory, exist_ok=True)
        os.makedirs(self.profiles_directory, exist_ok=True)

    @property
    def opendss_directory(self):
        return self.substation_directory

    @property
    def profiles_directory(self):
        return os.path.join(self.substation_directory, "profiles")

    @property
    def pv_deployments_directory(self):
        return os.path.join(self.substation_directory, "PVDeployments")

    @property
    def master_file(self):
        return os.path.join(self.substation_directory, "Master.dss")

    @property
    def substation_directory(self):
        return self._substation_directory



class OpenDssFeederWorkspace:
    """Defines a feeder and all dependent OpenDSS files."""

    def __init__(self, feeder_directory):
        self._feeder_directory = feeder_directory
        self._create_directories()

    def _create_directories(self):
        os.makedirs(self.feeder_directory, exist_ok=True)
        os.makedirs(self.loadshape_directory, exist_ok=True)
        os.makedirs(self.opendss_directory, exist_ok=True)
        os.makedirs(self.pv_deployments_directory, exist_ok=True)
        os.makedirs(self.profiles_directory, exist_ok=True)
        os.makedirs(self.metadata_directory, exist_ok=True)

    @property
    def feeder_directory(self):
        return self._feeder_directory

    @property
    def loadshape_directory(self):
        return os.path.join(self.feeder_directory, "LoadShapes")

    @property
    def opendss_directory(self):
        return os.path.join(self.feeder_directory, "OpenDSS")

    @property
    def profiles_directory(self):
        return os.path.join(self.feeder_directory, "profiles")

    @property
    def pv_deployments_directory(self):
        return os.path.join(self.feeder_directory, "PVDeployments")

    @property
    def master_file(self):
        return os.path.join(self.opendss_directory, "Master.dss")

    @property
    def metadata_directory(self):
        return os.path.join(self.feeder_directory, "Metadata")

    @property
    def loads_file(self):
        return os.path.join(self.opendss_directory, "Loads.dss")
