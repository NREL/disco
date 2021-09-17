************
Data Sources
************

DISCO currently supports OpenDSS models stored in several source formats,
namely GEM, EPRI, SourceTree1, SourceTree2.

The SMART-DS dataset is an open-source dataset which is in the SourceTree1 format.
This dataset is prepared for performing DISCO hosting capacity analysis after some pre-processing which is described in the link below:

.. toctree::
  :maxdepth: 1

  data-sources/smart-ds-model-preparation

The following sections show how to
prepare the source feeder models which are used as *input paths* for
transforming models with a given analysis type.

.. _GEM_JSON_Schema:

GEM Model
=========

A GEM config file (JSON) contains paths to source models on a filesystem along with
descriptor schema that describe all feeders and their possible deployments. 

Here is an example JSON file:

.. code-block:: json

  {
    "include_voltage_deviation": false,
    "path_base": "gem/feeder_models",
    "type": "GemModel",
    "feeders": [
      {
        "base_case": "deployment0",
        "deployments": [
          {
            "dc_ac_ratios": [],
            "kva_to_kw_ratings": [],
            "loadshape_file": null,
            "loadshape_location": null,
            "name": "deployment0",
            "placement_type": null,
            "project_data": {
              "pydss_other_loads_dss_files": {
                "2010-03-11_12-00-00-000": ["/data/path/loads1.dss"],
                "2010-12-25_15-00-00-000": ["/data/path/loads2.dss"]
              },
              "pydss_other_pvs_dss_files": {
                "2010-03-11_12-00-00-000": ["/data/path/pvs1.dss"],
                "2010-12-25_15-00-00-000": ["/data/path/pvs2.dss"],
              }
            },
            "pv_locations": [],
            "sample": null,
            "pydss_controllers": null,
            "job_order": 0
          }
        ],
        "end_time": "2010-08-11_15:00:00.000",
        "simulation_type": "Snapshot",
        "load_multipliers": [
          0.3,
          1.0,
          0.2,
          0.9
        ],
        "loadshape_location": null,
        "name": "MyFeeder",
        "opendss_location": "/opendss/location/path/",
        "start_time": "2010-08-11_15:00:00.000",
        "step_resolution": 900,
        "thermal_upgrade_overrides": {
          "line_loading_limit": 1.5,
          "dt_loading_limit": 1.5
        },
        "voltage_upgrade_overrides": {
          "initial_voltage_upper_limit": 1.058333,
          "initial_voltage_lower_limit": 0.9167,
          "final_voltage_upper_limit": 1.05,
          "final_voltage_lower_limit": 0.95
        }
      },
    ]
  }


Rules:

  * ``start_time`` and ``end_time`` must be set with timestamps.
  * If ``simulation_type == "Snapshot"``, then ``start_time`` and ``end_time`` must be the same.
  * ``dc_ac_ratios``, ``kva_to_kw_ratings`` may be empty arrays to represent no-PV scenarios.
  * ``pydss_controllers`` has three attributes,

      - ``controller_type``: One controller type defined in PyDSS, for example, "PvController".
      - ``name``: One controller name registered in PyDSS registry.
      - ``targets`` (optional): null, a DSS file, or a list of DSS files. If null, then DISCO automatically sets the deployment file.


EPRI Model
==========

The source URL of EPRI J1, K1, and M1 feeder models is 
https://dpv.epri.com/feeder_models.html. You can download the source data with
this command:

.. code-block:: bash

  $ disco download-source epri J1 K1 M1 --directory ./epri-feeders


.. _SourceTree1Model:

SourceTree1 Model
=================

This format requires the following directory structure:

.. code-block:: bash

  source_model_directory
  ├── format.toml
  ├── <substation>
  │   ├── *.dss
  │   └── <substation>--<feeder>
  │       ├── *.dss
  │       └── hc_pv_deployments
  │           ├── feeder_summary.csv
  │           └── <placement>
  │               ├── <sample>
  │               │   ├── <penetration-level>
  │               │   │   └── PVSystems.dss
  │               │   │   └── PVSystems.dss
  │               │   └── pv_config.json
  └── profiles
      └── <profile>.csv

Where in *format.toml*, it defines ``type = "SourceTree1Model"``.
To see how to generate the PV deployments data in ``hc_pv_deployments`` directory, please
refer to :ref:`SourceTree1PVDeployments`.


.. _SourceTree2Model:

SourceTree2 Model
=================

This format requires the following directory structure:

.. code-block:: bash

  source_model_directory
  ├── inputs
  │   ├── <feeder>
  │   │   ├── LoadShapes
  │   │   │   ├── <profile>.csv
  │   │   ├── OpenDSS
  │   │   │   ├── *.dss
  │   │   ├── PVDeployments
  │   │   │   └── new
  │   │   │       ├── <dc-ac-ratio>
  │   │   │       │   ├── <scale>
  │   │   │       │   │   ├── <placement>
  │   │   │       │   │   │   ├── <sample>
  │   │   │       │   │   │   │   ├── PV_Gen_<sample>_<penetration-level>.txt
  ├── format.toml

Where in *format.toml*, it defines ``type = "SourceTree2Model"``.
