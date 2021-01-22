Snapshot Impact Analysis
========================

The following steps show how to conduct *snapshot impact analysis* using DISCO.
This tutorial assumes there's an existing ``snapshot-impact-analysis-models`` 
directory generated from the ``transform-model`` command in the current working 
directory.

**1. Config Jobs**

Check the ``--help`` option for snapshot impact analysis options.

.. code-block:: bash

    $ disco config snapshot-impact-analysis --help
    Usage: disco config snapshot-impact-analysis [OPTIONS] INPUTS

    Create JADE configuration for snapshot impact analysis.

    Options:
    -c, --config-file TEXT       JADE config file to create  [default:
                                config.json]
    -e, --exports-filename TEXT  PyDSS export options  [default: ~/disco/pydss/config/Exports.toml]
    --verbose                    Enable debug logging
    --help                       Show this message and exit.

Given an output directory from ``transform-model``, we use this command below to 
configure the snapshot impact analysis jobs.

.. code-block:: bash

    $ disco config snapshot-impact-analysis snapshot-impact-analysis-models --config-file config.json

It generates the ``config.json`` for JADE to submit jobs.

**2. Submit Jobs**

With configured jobs in ``config.json``, all that's left to do is run the jobs:

.. code-block:: bash

    $ jade submit-jobs config.json

**3. Job Analysis**

Upon successful completion of each job, it will run and generate a
``post-process-results.json`` file inside of each job's results folder, 
along with a simplified CSV of the results.

.. code-block:: bash

    $ cat ./output/job-outputs/feeder_1__-1__None__None__deployment0.dss/post-process-results.json
    {
        "job": "feeder_1__-1__None__None__deployment0.dss",
        "post-process": "SnapshotImpactAnalysis",
        "results": {
            "inputs": [
            {
                "name": "over_voltage",
                "input_type": "float",
                "value": 3.0
            },
            {
                "name": "under_voltage",
                "input_type": "float",
                "value": 0.95
            },
            {
                "name": "over_voltage_conservative",
                "input_type": "float",
                "value": 1.05833
            },
            {
                "name": "under_voltage_conservative",
                "input_type": "float",
                "value": 0.91667
            },
            {
                "name": "line_overload_1",
                "input_type": "percent",
                "value": 100.0
            },
            {
                "name": "line_overload_2",
                "input_type": "percent",
                "value": 100.0
            },
            {
                "name": "transformer_overload_1",
                "input_type": "percent",
                "value": 100.0
            },
            {
                "name": "transformer_overload_2",
                "input_type": "percent",
                "value": 100.0
            }
            ],
            "outputs": [
            {
                "result_type": "violations",
                "data": {
                "feeder": "feeder_1",
                "deployment": "deployment0",
                "placement": null,
                "sample": null,
                "penetration": 0,
                "peak_load": 2115.474432865047,
                "pv_kw": 123.69600000000001,
                "pv_pmpp": 123.696,
                "pv_to_load_ratio": 5.85,
                "min_voltage": 0.9578933469865691,
                "max_voltage": 1.018676511690172,
                "undervoltage_A_flag": false,
                "overvoltage_A_flag": false,
                "undervoltage_A_count": 0,
                "overvoltage_A_count": 0,
                "undervoltage_B_flag": false,
                "overvoltage_B_flag": false,
                "undervoltage_B_count": 0,
                "overvoltage_B_count": 0,
                "max_flicker": null,
                "flicker_flag": null,
                "flicker_count": null,
                "max_line": 1.670472047303335,
                "1X_line_overloading_flag": true,
                "1X_line_overloading_count": 1,
                "1p5X_line_overloading_flag": true,
                "1p5X_line_overloading_count": 1,
                "max_xfmr_loading": 8.927325959426224,
                "1X_xfmr_overloading_flag": true,
                "1X_xfmr_overloading_count": 12,
                "1p5X_xfmr_overloading_flag": true,
                "1p5X_xfmr_overloading_count": 12,
                "100L100TA_fail_flag": true,
                "100L100TA_pass_flag": false,
                "100L150TA_fail_flag": true,
                "100L150TA_pass_flag": false,
                "150L100TA_fail_flag": true,
                "150L100TA_pass_flag": false,
                "150L150TA_fail_flag": true,
                "150L150TA_pass_flag": false,
                "100L100TB_fail_flag": true,
                "100L100TB_pass_flag": false,
                "100L150TB_fail_flag": true,
                "100L150TB_pass_flag": false,
                "150L100TB_fail_flag": true,
                "150L100TB_pass_flag": false,
                "150L150TB_fail_flag": true,
                "150L150TB_pass_flag": false
                }
            }
            ]
        }
    }

    $ cat ./output/job-outputs/feeder_1__-1__None__None__deployment0.dss/snapshot-impact-analysis-job-post-process.csv
    feeder,deployment,placement,sample,penetration,peak_load,pv_kw,pv_pmpp,pv_to_load_ratio,min_voltage,max_voltage,undervoltage_A_flag,overvoltage_A_flag,undervoltage_A_count,overvoltage_A_count,undervoltage_B_flag,overvoltage_B_flag,undervoltage_B_count,overvoltage_B_count,max_flicker,flicker_flag,flicker_count,max_line,1X_line_overloading_flag,1X_line_overloading_count,1p5X_line_overloading_flag,1p5X_line_overloading_count,max_xfmr_loading,1X_xfmr_overloading_flag,1X_xfmr_overloading_count,1p5X_xfmr_overloading_flag,1p5X_xfmr_overloading_count,100L100TA_fail_flag,100L100TA_pass_flag,100L150TA_fail_flag,100L150TA_pass_flag,150L100TA_fail_flag,150L100TA_pass_flag,150L150TA_fail_flag,150L150TA_pass_flag,100L100TB_fail_flag,100L100TB_pass_flag,100L150TB_fail_flag,100L150TB_pass_flag,150L100TB_fail_flag,150L100TB_pass_flag,150L150TB_fail_flag,150L150TB_pass_flag,name
    feeder_1,deployment0,,,0.0,2115.474432865047,123.69600000000001,123.696,5.85,0.9578933469865691,1.018676511690172,False,False,0,0,False,False,0,0,,,,1.670472047303335,True,1,True,1,8.927325959426224,True,12,True,12,True,False,True,False,True,False,True,False,True,False,True,False,True,False,True,False,feeder_1__-1__None__None__deployment0.dss
