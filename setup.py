"""
setup.py
"""
import os
import logging
from codecs import open
from pathlib import Path
from setuptools import setup, find_packages
from setuptools.command.develop import develop
from setuptools.command.install import install
import sys


logger = logging.getLogger(__name__)


def read_lines(filename):
    return Path(filename).read_text().splitlines()


class PostDevelopCommand(develop):
    """Post-installation for development mode."""
    def run(self):
        develop.run(self)
        install_jade_extensions()


class PostInstallCommand(install):
    """Post-installation for installation mode."""
    def run(self):
        install.run(self)
        install_jade_extensions()


def install_jade_extensions():
    # These won't be available until after jade gets installed by pip.
    from jade.extensions.registry import Registry
    from jade.utils.subprocess_manager import run_command

    registry_filename = Path.home() / Registry._REGISTRY_FILENAME
    if os.path.exists(registry_filename):
        os.remove(registry_filename)
    ext = os.path.join(here, "disco", "extensions", "jade_extensions.json")
    run_command(f"jade extensions register {ext}")
    run_command("jade extensions add-logger disco")


here = os.path.abspath(os.path.dirname(__file__))

with open("README.md", encoding="utf-8") as f:
    readme = f.read()

with open(os.path.join(here, "disco", "version.py"), encoding="utf-8") as f:
    lines = f.read().split("\n")
    if len(lines) != 2:
        print("Invalid format in version.py", file=sys.stderr)
        sys.exit(1)


version = lines[0].split()[2].strip('"').strip("'")

install_requires = [
    "NREL-jade",
    "chevron",
    "click>=8.0",
    "dsspy>=2.2.0",
    "filelock",
    "matplotlib",
    "networkx",
    "opendssdirect.py>=0.7.0",
    "openpyxl",
    "pandas==1.5.*",
    "pydantic>=1.6.0",
    "seaborn",
    "scikit-learn",
    "sqlalchemy",
    "toml>=0.10.0",
]
dev_requires = [
    "flake8",
    "ghp-import",
    "mock>=3.0.0",
    "pycodestyle",
    "pylint",
    "pytest",
    "pytest-cov",
    "sphinx>=2.0",
    "sphinx-rtd-theme>=0.4.3",
    "sphinxcontrib-plantuml",
    "tox",
]
test_requires = ["pytest"]

setup(
    name="NREL-disco",
    version=version,
    description="DISCO",
    long_description=readme,
    long_description_content_type="text/markdown",
    maintainer_email="daniel.thom@nrel.gov",
    url="https://github.com/NREL/disco",
    packages=find_packages(),
    package_dir={"disco": "disco"},
    entry_points={
        "console_scripts": [
            "disco=disco.cli.disco:cli",
            "disco-internal=disco.cli.disco_internal:cli",
        ],
    },
    include_package_data=True,
    package_data={
        "disco": [
            "analysis/*.toml",
            "analysis/*.xlsx",
            "pipelines/template/*.toml",
            "extensions/pydss_simulation/*.toml",
            "extensions/pydss_simulation/trained_lm_time_prediction.sav",
            "extensions/upgrade_simulation/upgrades/*.xlsx",
            "extensions/upgrade_simulation/upgrades/*.toml",
            "extensions/*.json",
            "postprocess/config/*.toml",
            "postprocess/toolbox/query_tool.ipynb",
            "pydss/config/*.toml",
        ],
    },
    license="BSD license",
    zip_safe=False,
    keywords=["disco"],
    python_requires=">=3.7",
    classifiers=[
        "Development Status :: 4 - Beta",
        "License :: OSI Approved :: BSD License",
        "Natural Language :: English",
        "Programming Language :: Python :: 3.9",
    ],
    test_suite="tests",
    install_requires=install_requires,
    extras_require={
        "dev": dev_requires,
        "extras": ["ipywidgets"]
    },
    # Disabled because this method is not compatible with wheels, and so we
    # can't build a PyPi package.
    #cmdclass={"install": PostInstallCommand, "develop": PostDevelopCommand},
)
