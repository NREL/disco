"""Generates OpenDSS data for distribution simulations."""

from collections import namedtuple
import fileinput
import itertools
import logging
import os
import pathlib
import re
import shutil

from jade.exceptions import InvalidParameter
from jade.utils.timing_utils import timed_info
from jade.utils.utils import dump_data, modify_file, get_filenames_by_ext, \
    ExtendedJSONEncoder
from disco.enums import SimulationType
from disco.models.base import OpenDssDeploymentModel, PyDSSControllerModel, \
    ImpactAnalysisBaseModel
from disco.sources.base import SOURCE_CONFIGURATION_FILENAME
from disco.sources.gem.model_input_interface import ModelInputDataInterface


logger = logging.getLogger(__name__)


class OpenDssGenerator(ModelInputDataInterface):
    """Generates OpenDSS data for distribution simulations."""

    _loadshapes_file = "LoadShapes.dss"

    def __init__(self, data):
        self._feeders = []
        self._include_voltage_deviation = data.get('include_voltage_deviation', False)
        for feeder in data["feeders"]:
            if feeder["name"] == "":
                logger.warning("Feeder name is empty; skipping %s", feeder)
            elif "DEAD" in feeder["name"].upper():
                logger.warning("Skipping 'dead' feeder %s", feeder["name"])
            else:
                self._feeders.append(Feeder(feeder))

        feeder_dirnames = set()
        for feeder in self._feeders:
            feeder_dirname = self._feeder_dirname(feeder)
            if feeder_dirname in feeder_dirnames:
                raise InvalidParameter(f"duplicate feeder dirname: {feeder_dirname}")
            feeder_dirnames.add(feeder_dirname)

            deployment_names = set()
            for deployment in feeder.deployments:
                if deployment.name in deployment_names:
                    raise InvalidParameter(
                        f"duplicate deployment found: {deployment.name}"
                    )
                deployment_names.add(deployment.name)

        self._modified_master_files = set()
        self._output_dir = None

    @staticmethod
    def _create_name(inputs):
        return "__".join([str(x) for x in [inputs.feeder.name,
                                           inputs.feeder.tag,
                                           inputs.deployment.name,
                                           inputs.dc_ac_ratio,
                                           inputs.kva_to_kw_rating]])

    @staticmethod
    def _feeder_dirname(feeder):
        return feeder.name + "__" + feeder.tag

    def _feeder_dir(self, output_dir, feeder):
        feeder_dirname = self._feeder_dirname(feeder)
        return os.path.join(output_dir, feeder_dirname)

    @staticmethod
    def _opendss_dir(feeder_dir):
        return os.path.join(feeder_dir, "OpenDSS")

    @staticmethod
    def _loadshapes_dir(feeder_dir):
        return os.path.join(feeder_dir, "LoadShapes")

    @staticmethod
    def _deployment_dir(feeder_dir):
        return os.path.join(feeder_dir, "PVDeployments")

    @staticmethod
    def _deployment_file(deployment_dir, deployment):
        return os.path.join(deployment_dir, deployment.name + ".dss")

    @staticmethod
    def _master_file(feeder_dir):
        return os.path.join(OpenDssGenerator._opendss_dir(feeder_dir),
                            "Master.dss")

    @staticmethod
    def _new_master_file(feeder_dir):
        return os.path.join(OpenDssGenerator._opendss_dir(feeder_dir),
                            "MasterDisco.dss")

    def _configurations_dir(self):
        return os.path.join(self._output_dir, "configurations")

    @staticmethod
    def _get_pattern(data, pattern_type):
        assert pattern_type in ("dc_ac_ratio_patterns", "kva_to_kw_rating_patterns")
        patterns = set()
        for item in data[pattern_type]:
            val = None
            string = None
            if "all" in item:
                val = item["all"]
                string = "all_" + str(val)
            pattern = (val, string)
            if pattern in patterns:
                raise InvalidParameter("duplicate {pattern_type} {pattern}")
            patterns.add(pattern)

        return list(patterns)

    @timed_info
    def generate_output_data(self, output_dir, include_pv_systems, simulation_model):
        self._output_dir = output_dir

        jobs = []
        for feeder in self._feeders:
            if not self._check_required_feeder_files(feeder):
                continue
            feeder_dir = self._feeder_dir(self._output_dir, feeder)
            opendss_dir = self._opendss_dir(feeder_dir)
            self._copy_dss_files(feeder.opendss_location, opendss_dir)
            for deployment in feeder.deployments:
                self._copy_deployment_data(deployment, feeder_dir,
                                           include_pv_systems)
                for args in itertools.product(deployment.dc_ac_ratios,
                                              deployment.kva_to_kw_ratings):
                    inputs = DeploymentInputs(feeder, deployment, *args)
                    job = self._generate_job(inputs, output_dir, feeder_dir, simulation_model)
                    jobs.append(job)

        if jobs:
            self._create_config_file(jobs)

        logger.info("Done generating data in %s", output_dir)

    def _create_config_file(self, jobs):
        config_file = os.path.join(self._output_dir, SOURCE_CONFIGURATION_FILENAME)
        dump_data(jobs, config_file, indent=2, cls=ExtendedJSONEncoder)

    @staticmethod
    def _check_required_feeder_files(feeder):
        is_valid = True

        if not os.path.exists(feeder.opendss_location):
            logger.error(
                "Possible bad feeder %s - tag %s. Path isn't present: %s",
                feeder.name, feeder.tag, feeder.opendss_location
            )
            is_valid = False

        required = ["Master.dss"]
        for filename in required:
            path = os.path.join(feeder.opendss_location, filename)
            if not os.path.exists(path):
                logger.error(
                    "Feeder-tag=%s-%s %s does not exist in %s",
                    feeder.name, feeder.tag, filename, feeder.opendss_location
                )
                is_valid = False

        return is_valid

    @staticmethod
    def _copy_dss_files(src, dst):
        """Copy .dss files recursively, fixing data-file paths as necessary.

        Parameters
        ----------
        src : str
            source directory
        dst : str
            destination directory

        """
        os.makedirs(dst, exist_ok=True)
        target_dirs = set([dst])

        for path in get_filenames_by_ext(src, ".dss"):
            relpath = os.path.relpath(path, src)
            target_path = os.path.join(dst, relpath)
            dirname = os.path.dirname(target_path)
            # This tracks directory creations in memory in order to reduce
            # fileystem operations which could be slow on distributed systems
            # like Lustre.
            if dirname not in target_dirs:
                os.mkdir(dirname)
                target_dirs.add(dirname)
            shutil.copyfile(path, target_path)
            logger.debug("Copied %s to %s", path, target_path)

            src_dir = os.path.abspath(os.path.dirname(path))
            # TODO: add support for copying data files if we use this source model again.
            OpenDssGenerator.make_data_file_references_absolute(src_dir, target_path)

    @staticmethod
    def make_data_file_references_absolute(src_dir, filename):
        """Change the path to any data file referenced in a .dss file to its
        absolute path."""
        # Example line:
        # New Loadshape.Residential1234 npts=123456 minterval=5 mult=[file=../BuildingData/Dataset_12_34/Residential/RES1234/LoadProfiles/12345.csv, col=1, header=no]
        regex = re.compile(r"file=(.*), col=")
        def replace_func(match):
            path = os.path.normpath(match.group(1).replace("\\", "/"))
            new_path = os.path.normpath(os.path.join(src_dir, path))
            return "file=" + new_path + ", col="

        with fileinput.input(files=[filename], inplace=True) as f_in:
            for line in f_in:
                line = re.sub(regex, replace_func, line)
                print(line, end="")
                logger.debug("line=%s", line)

    def _copy_deployment_data(self, deployment, feeder_dir, include_pv_systems):
        self._attach_pv_deployment(deployment, feeder_dir)

        new_master_file = self._new_master_file(feeder_dir)
        if new_master_file not in self._modified_master_files:
            path_master_file = self._master_file(feeder_dir)
            # Solve will be called from the PV deployment file.
            regex_solve = re.compile(r"^\s*Solve\s*$")
            modify_file(path_master_file, comment_out_solve, regex_solve)
            if not include_pv_systems:
                # Comment out any PVSystems file in the original data. The QSTS
                # code reads from the PVDeployments folder instead. The new
                # masterfile is named "MasterDisco.dss"
                modify_file(path_master_file, comment_out_pv_systems,
                            "PVSystems.dss")
                logger.debug("Comment out existing PVSystems file. %s",
                             path_master_file)

            shutil.move(path_master_file, new_master_file)
            logger.debug("Moved %s to %s", path_master_file, new_master_file)
            self._modified_master_files.add(new_master_file)

    def _attach_pv_deployment(self, deployment, feeder_dir):
        """Add redirects to the master file file within the PV deployment."""
        deployment_dir = self._deployment_dir(feeder_dir)
        os.makedirs(deployment_dir, exist_ok=True)

        # Copy the PV file to the deployments folder with deployment.name as
        # the file name.
        pv_file = self._deployment_file(deployment_dir, deployment)
        if os.path.exists(pv_file):
            return

        master_file = os.path.join(feeder_dir, "OpenDSS", "MasterDisco.dss")

        # Below Solve is added to the file because OpenDSS will not properly
        # initialized internal memory structures unless Solve is called after
        # all new elements have been added.

        if not deployment.pv_locations:
            # TODO: hack
            with open(pv_file, "w") as f_out:
                f_out.write(f"Redirect {master_file}\n")
                f_out.write("\nSolve\n")
            return

        pv_locations = deployment.pv_locations
        if not isinstance(pv_locations, list):
            pv_locations = [pv_locations]

        with fileinput.input(pv_locations) as fr, open(pv_file, "w") as fw:
            for line in fr:
                fw.write(line)

        logger.debug("Copied %s to %s", deployment.name, pv_file)

        # Include MasterDisco.dss within this file.
        tmp = pv_file + ".tmp"
        with open(tmp, "w") as fp_out:
            fp_out.write(f"Redirect {master_file}\n\n")
            with open(pv_file) as fp_in:
                for line in fp_in:
                    fp_out.write(line)
            fp_out.write("\nSolve\n")
        shutil.move(tmp, pv_file)

    def _generate_job(self, inputs, output, feeder_dir, simulation_model):
        deployment_dir = self._deployment_dir(feeder_dir)
        os.makedirs(deployment_dir, exist_ok=True)
        feeder = inputs.feeder
        deployment = inputs.deployment
        opendss_dir = os.path.join(feeder_dir, "OpenDSS")

        project_data = {
            "penetration": deployment.penetration,
            "placement_type": deployment.placement_type,
            "sample": deployment.sample,
        }
        project_data.update(deployment.project_data)
        simulation_params = {
            "simulation_type": feeder.simulation_type.value,
            "start_time": feeder.start_time,
            "end_time": feeder.end_time,
            "step_resolution": feeder.step_resolution,
        }
        feeder_dirname = self._feeder_dirname(feeder)
        deployment_file = os.path.join(output, feeder_dirname, "PVDeployments", deployment.name + ".dss")
        if deployment.pydss_controllers:
            pydss_controllers = [
                PyDSSControllerModel(
                    controller_type=x["controller_type"],
                    name=x["name"],
                )
                for x in deployment.pydss_controllers
            ]
        else:
            pydss_controllers = None

        deployment_model = OpenDssDeploymentModel.validate(
            dict(
                deployment_file=deployment_file,
                feeder=feeder.name,
                dc_ac_ratio=inputs.dc_ac_ratio,
                kva_to_kw_rating=inputs.kva_to_kw_rating,
                directory=output,
                project_data=project_data,
                pydss_controllers=pydss_controllers,
            )
        )

        name = "__".join([
            feeder_dirname,
            str(inputs.dc_ac_ratio),
            str(inputs.kva_to_kw_rating),
            deployment.name,
            str(deployment.job_order)
        ])

        data = {
            "deployment": deployment_model,
            "simulation": simulation_params,
            "name": name,
            "model_type": simulation_model.__name__,
            "job_order": deployment.job_order
        }
        if issubclass(simulation_model, ImpactAnalysisBaseModel):
            data["base_case"] = inputs.feeder.base_case

        return simulation_model.validate(data).dict()


class Feeder:
    """Defines a feeder."""
    def __init__(self, data):
        self.name = data["name"]
        self.tag = data.get("tag", None)
        self.base_case = data.get("base_case", None)
        self.deployments = [Deployment(x) for x in data["deployments"]]
        self.opendss_location = data["opendss_location"]
        self.loadshape_location = data["loadshape_location"]
        self.simulation_type = SimulationType(data.get("simulation_type", "Snapshot"))
        self.start_time = data["start_time"]
        self.end_time = data["end_time"]
        self.step_resolution = data["step_resolution"]

        if self.simulation_type == SimulationType.SNAPSHOT:
            if self.start_time != self.end_time:
                raise InvalidParameter(
                    "start_time and end_time must be the same for snapshot "
                    f"simulations: {data}"
                )

        if not self.tag:
            self.tag = self.create_feeder_tag()

    def create_feeder_tag(self):
        """A TEMP solution of creating feeder tag from opendss_location.

        Suppose the directory structure is like this::

            opendss_location = (
                "/project/xxx/run2/distribution/xxx/feeder_models/"
                "opendss/xxx/scenarios/xxx/"
                "2050/2010-07-10_15-00-00-000/X/456/xxx"
            )

        The tag would become "2050__2010-07-10_15-00-00-000__X__456"

        """
        path = pathlib.Path(self.opendss_location)
        parents = [p.name for p in path.parents if p.name]
        if len(parents) > 4:
            tag = "__".join(reversed(parents[:4]))
        else:
            tag = "__".join(reversed(parents))
        return tag


class Deployment:
    """Defines a deployment."""
    def __init__(self, data):
        self.name = data["name"]
        self.dc_ac_ratios = data["dc_ac_ratios"]
        self.kva_to_kw_ratings = data["kva_to_kw_ratings"]
        self.loadshape_file = data["loadshape_file"]
        self.loadshape_location = data["loadshape_location"]
        self.job_order = data.get("job_order", None)

        # Handle legacy formats.
        if "pv_location" in data:
            self.pv_locations = [data["pv_location"]]
        else:
            self.pv_locations = data.get("pv_locations", [])
        self.pydss_controllers = data.get("pydss_controllers", [])
        if isinstance(self.pydss_controllers, dict):
            self.pydss_controllers = [self.pydss_controllers]

        for param in ("dc_ac_ratios", "kva_to_kw_ratings"):
            val = getattr(self, param)
            if val is None or val == []:
                setattr(self, param, [None])

        # Optional
        self.penetration = data.get("penetration", None)
        self.sample = data.get("sample", None)
        self.placement_type = data.get("placement_type", None)
        self.project_data = data.get("project_data", {})


DeploymentInputs = namedtuple(
    "Inputs",
    "feeder, deployment, dc_ac_ratio, kva_to_kw_rating"
)


def comment_out_pv_systems(line, *args, **_):
    """Comments out the redirect to a given string."""
    return line.replace("Redirect " + args[0], "!Redirect " + args[0])


def comment_out_solve(line, *args, **_):
    """Comments out the Solve command."""
    regex = args[0]
    match = regex.search(line)
    if match:
        return "!Solve"
    return line
