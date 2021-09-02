****************
Transform Models
****************

Transform Model Help
====================

This process transforms user OpenDSS models into a format understood by DISCO
so that it can perform simulation and analysis with the models.

Given an input path of source data DISCO can determine the types of analysis 
it supports. The input path can be one of:

    * a GEM config file; the JSON schema definition is here - :ref:`GEM_JSON_Schema`.
    * a directory path which contains a ``format.toml`` with a source type definition.
      The source types are:

      - EpriModel
      - SourceTree1Model
      - SourceTree2Model

Input File
----------

The ``--help`` option displays the types of analysis the source models support.
For example, if the input path is a GEM file:

.. code-block:: bash

    $ disco transform-model ./gem-file.json --help

    Available analysis types: snapshot upgrade

    For additional help run one of the following:
        disco transform-model ./gem-file.json snapshot --help
        disco transform-model ./gem-file.json upgrade --help


Input Directory
---------------

If the input path is a directory, for example, with ``type = SourceTree1Model``
in *format.toml*.

.. code-block:: bash

    $ disco transform-model tests/data/smart-ds/substations/ --help

    Available analysis types: snapshot time-series upgrade

    For additional help run one of the following:
        disco transform-model tests/data/smart-ds/substations/ snapshot --help
        disco transform-model tests/data/smart-ds/substations/ time-series --help
        disco transform-model tests/data/smart-ds/substations/ upgrade --help

.. note::

    By default, the name of PV deployments directory is ``hc_pv_deployments``, if the PV deployments
    are located in other directory, please specify the right directory by using option `-P/--pv-deployments-dirname`
    in command ``transform-model``.


Load Shape Data files
---------------------
By default DISCO replaces relative paths to load shape data files with absolute
paths and does not copy them. This reduces time and consumed storage space.
However, it also makes the directory non-portable to other systems.

If you want to create a portable directory with copies of these files, add
this flag to the command:

.. code-block:: bash

   $ disco transform-model tests/data/smart-ds/substations time-series -c
   $ disco transform-model tests/data/smart-ds/substations time-series --copy-load-shape-data-files


DISCO Model in Depth
====================

PyDSS Controllers
-----------------

If you have custom *controllers* that need to be applied to simulation,
please make the controllers are registered via PyDSS first.

Suppose we have particular controller settings defined in a ``my-custom-controllers.toml`` file:

.. code-block:: python

    [project123]
    Category = "Legacy"
    ...
    pf = "None"
    pfMin = 0.5
    ...
    Priority = "Var"
    DampCoef = 0.5

.. code-block:: bash

    $ pydss controllers register PvController /path/my-custom-controllers.toml

Once registered, the following information could be used to create the input 
config related to ``pydss_controllers``.

.. code-block:: json

    {
        "name": "project123",
        "controller_type": "PvController"
    }

By default, the target PyDSS file that the PyDSS controller would be applied to 
is the deployment file, you do not need to specify the target DSS files. However,
if you want to specify the target DSS files here, other than the deployment file,

.. code-block:: json

    {
        "name": "project123",
        "controller_type": "PvController",
        "targets": [
            "/data/dss/file1.dss",
            "/data/dss/file2.dss"
        ]
    }

And, ``pydss_controllers`` supports multiple PyDSS controllers here,

.. code-block:: json

    [
        {
            "name": "project123",
            "controller_type": "PvController"
        },
        {
            "name": "project123",
            "type": "StorageController"
        },
    ]


Model Schema
------------

DISCO uses `pydantic <https://pydantic-docs.helpmanual.io/>`_ 
models to define the schema of model inputs for each type of analysis. Given a 
type of anaalysis in DISCO, the schema shows all attributes used  to define 
the analysis models.

*Show Schema*

The input configurations in JSON should meet the specifications defined 
by DISCO. To show the schema of a given analysis type, for example, 
``SnapshotImpactAnalysisModel`` using this command with ``--mode show-schema``
option,

.. code-block:: bash

    $ disco simulation-models --mode show-schema SnapshotImpactAnalysisModel

*Show Example*

A data example may be more straightforward, use ``--mode show-example`` option,

.. code-block:: bash

    $ disco simulation-models --mode show-example SnapshotImpactAnalysisModel --output-file=disco-models/configurations.json
    $ cat disco-models/configurations.json
    [
        {
            "feeder": "J1",
            "tag": "2010",
            "deployment": {
                "name": "deployment_001.dss",
                "dc_ac_ratio": 1.15,
                "directory": "disco-models",
                "kva_to_kw_rating": 1.0,
                "project_data": {},
                "pv_locations": [],
                "pydss_controllers": null
            },
            "simulation": {
                "start_time": "2013-06-17T15:00:00.000",
                "end_time": "2014-06-17T15:00:00.000",
                "step_resolution": 900,
                "simulation_type": "Snapshot"
            },
            "name": "J1_123_Sim_456",
            "base_case": null,
            "include_voltage_deviation": false,
            "blocked_by": [],
            "job_order": null
        }
    ]


Validate Inputs
---------------

If you want to prepare the models manually then you must generate them in a
JSON file and then validate them to make sure they match the schema.

.. code-block:: bash

    $ disco simulation-models validate-file disco-models/configurations.json

The ``ValidationError`` will be raised if any input does not meet the
specification defined by DISCO. The error messages should provide corrective
action.
