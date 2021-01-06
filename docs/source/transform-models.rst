****************
Transform Models
****************


Transform Model Help
====================

Based on the source OpenDSS models prepared, we are going to transfom the raw 
models into DISCO models by using ``disco transform-model``, so that DISCO can
perform simulation and analysis based on the transformed models.

Given an input path of data source, DISCO can determine the types of analysis 
it supports. The input path can be:

    * a GEM file, the JSON schema definition could be found here - :ref:`GEM_JSON_Schema`.
    * or, a directory path which contains the ``format.toml`` with souce type definition.
      The source types are:
      - EpriModel
      - SourceTree1Model
      - SourceTree2Model

Input File
----------

The ``--help`` option could help figure out what types of analysis the source
models support. For example, if the input path is a GEM file,

.. code-block:: bash

    $ disco transform-model ./gem-file.json --help

    Available analysis types: snapshot-impact-analysis upgrade-cost-analysis

    For additional help run one of the following:
        disco transform-model ./gem-file.json snapshot-impact-analysis --help
        disco transform-model ./gem-file.json upgrade-cost-analysis --help


Input Directory
---------------

If the input path is a directory, for example, with ``type = typeSourceTree1Model``
in *format.toml*.

.. code-block:: bash

    $ disco transform-model tests/data/smart-ds/substations/ --help

    Available analysis types: snapshot-impact-analysis time-series-impact-analysis upgrade-cost-analysis

    For additional help run one of the following:
        disco transform-model tests/data/smart-ds/substations/ snapshot-impact-analysis --help
        disco transform-model tests/data/smart-ds/substations/ time-series-impact-analysis --help
        disco transform-model tests/data/smart-ds/substations/ upgrade-cost-analysis --help


DISCO Model in Depth
====================

PyDSS Controllers
-----------------

If you have custom *controllers* that needs to be applied to simulation,
please make the controllers are registered via PyDSS first.

Suppose we have particular controller settings defined in a ``my-custom-controllers.toml`` file,
for example,

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

The input confiugations in JOSN should meet the specifications of job defined 
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

If you want to repare the models mannually, after the config file gets prepared,
suppose ``disco-models/configurations.json``, then it needs to be validated and 
make sure they meet the specifications defined in schema.

.. code-block:: bash

    $ disco simulation-models validate-file disco-models/configurations.json

The ``ValidationError`` may raise if any input does not meet the specification 
defined by DISCO. If that happens, then need to check the error messages,
and correct the inputs config. You may need to repeat util the validation success.
