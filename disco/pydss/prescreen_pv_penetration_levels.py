
import logging
from collections import namedtuple


from jade.exceptions import ExecutionError
from jade.result import ResultsSummary
from jade.utils.subprocess_manager import run_command
from jade.utils.utils import dump_data, load_data

from disco.common import EXIT_CODE_GOOD
from disco.exceptions import is_convergence_error
from disco.utils.failing_test_bisector import FailingTestBisector


JobKey = namedtuple("JobKeyByFeeder", ["substation", "feeder", "placement", "sample"])
PRESCREEN_JOBS_OUTPUT = "prescreen-jobs"


logger = logging.getLogger(__name__)


def create_job_key(job):
    deployment = job.model.deployment
    return JobKey(
        substation=deployment.substation,
        feeder=deployment.feeder,
        placement=deployment.project_data["placement"],
        sample=deployment.project_data["sample"],
    )


def run_prescreen(src_config, src_config_file, substation, feeder, placement, sample, prescreen_jobs_output):
    """Run a bisect on the penetration levels for a sample."""
    key = JobKey(substation, feeder, placement, sample)
    jobs = set()
    for job in src_config.iter_pydss_simulation_jobs(exclude_base_case=True):
        job_key = create_job_key(job)
        if key == job_key:
            jobs.add(job)

    jobs = list(jobs)
    jobs.sort(key=lambda x: x.model.deployment.project_data["penetration_level"])
    highest_level = find_highest_passing_penetration_level(key, jobs, src_config_file, prescreen_jobs_output)

    data = key._asdict()
    name = ("__".join((str(x) for x in data.values())))
    data["name"] = name
    data["highest_passing_penetration_level"] = highest_level
    filename = prescreen_jobs_output / (name + ".toml")
    dump_data(data, filename)
    logger.info("Created %s", filename)


def find_highest_passing_penetration_level(key, jobs, src_config_file, prescreen_jobs_output):
    job_names = []
    penetration_levels = []
    for job in jobs:
        job_names.append(job.name)
        penetration_levels.append(job.model.deployment.project_data["penetration_level"])

    bisector = FailingTestBisector(len(penetration_levels))
    index = bisector.get_first_index()
    done = False
    indices_run = set()
    for _ in range(len(penetration_levels)):
        name = job_names[index]
        run_config_file = create_job(src_config_file, name, prescreen_jobs_output)
        output_dir = prescreen_jobs_output / name
        ret = run_command(f"jade submit-jobs --local {run_config_file} -o {output_dir}")
        if ret != EXIT_CODE_GOOD:
            raise Exception(f"Unexpected JADE error occurred: key={key} name={name} ret={ret}")

        ret = _get_job_result(output_dir)
        if ret == EXIT_CODE_GOOD:
            passed = True
        elif is_convergence_error(ret):
            passed = False
        else:
            raise Exception(f"Unknown PyDSS error occurred: key={key} job={name}. End bisect: {ret}")

        indices_run.add(index)
        index, done = bisector.get_next_index(index, passed)
        if done:
            break
        if index in indices_run:
            raise Exception(f"already ran index={index} key={key} name={name}")

    if not done:
        raise Exception("Failed to find highest penetration level from {key}")

    return penetration_levels[index]


def create_job(config_file, name, prescreen_base_output):
    dst_config_file = prescreen_base_output / f"config__{name}.json"
    cmd = f"jade config filter --fields name {name} -o {dst_config_file} {config_file}"
    ret = run_command(cmd)
    if ret != 0:
        raise ExecutionError(f"filter failed: [{cmd}] ret={ret}")

    config = load_data(dst_config_file)
    assert len(config["jobs"]) == 1
    start_time = "2020-04-01T11:00:00.0"
    end_time = "2020-04-30T15:15:00.0"
    config["jobs"][0]["simulation"]["start_time"] = start_time
    config["jobs"][0]["simulation"]["end_time"] = end_time
    config["pydss_inputs"]["Simulation"]["project"]["simulation_range"] = {"start": "11:00:00", "end": "15:00:00"}
    config["pydss_inputs"]["Simulation"]["project"]["convergence_error_percent_threshold"] = 10.0

    config["pydss_inputs"]["Simulation"]["exports"]["export_results"] = False
    config["pydss_inputs"]["Simulation"]["exports"]["export_elements"] = False
    config["pydss_inputs"]["Simulation"]["reports"].clear()
    config["pydss_inputs"]["Scenarios"] = [
        x for x in config["pydss_inputs"]["Scenarios"] if x["name"] == "control_mode"
    ]
    assert config["pydss_inputs"]["Scenarios"]
    dump_data(config, dst_config_file)
    logger.info("Created prescreening job %s", dst_config_file)
    return dst_config_file


def _get_job_result(output_dir):
    result_summary = ResultsSummary(output_dir)
    results = result_summary.list_results()
    assert len(results) == 1
    result = results[0]
    return result.return_code
