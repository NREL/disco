Upgrade Cost Analysis
=====================

After running ``transform-model`` command on source, then we get the well-prepared 
DISCO models, with which as inputs we can then configure the jobs,

* run single upgrade cost analysis if ``job_order`` field in model is ``null``;
* or if ``job_order`` specified, run sequential upgrade cost analysis.

The following steps show how to conduct upgrade cost analysis using DISCO modeles 
- ``upgrade-cost-analysis-models`` generated from ``transform-model``.

**1. Config Jobs**

We use DISCO ``disco config`` command to config jobs. 
you can help get what options we need here with ``--help`` option.

.. code-block:: bash

    $ disco config upgrade-cost-analysis --help
    Usage: disco config upgrade-cost-analysis [OPTIONS] INPUTS

    Create JADE configuration for upgrade cost analysis.

    Options:
    -d, --cost-database PATH  The unit cost database spreadsheet.  [default:
                                ~/disco/disco/analysis/generic_cost_database_v1.xlsx]
    -p, --params-file PATH    Thermal & Voltage upgrade parameters file.
                                [default: upgrade-params.toml]
    --show-params             Show the default upgrade parameters in file.
    -s, --sequential-upgrade  Enable sequential upgrades.
    -n, --nearest-redirect    Redirect DSS files from nearest lower-order jobs.
    -c, --config-file PATH    JADE config file to create  [default: config.json]
    --verbose                 Enable debug logging.
    --help                    Show this message and exit.

* **disco-database**: the path to the *unit cost database file*, the default is 
  ``~/disco/disco/analysis/generic_cost_database_v1.xlsx``.

* **show-params**: an option for showing the upgrade parameters from 
  ``--params-file`` that would be passed to PyDSS for upgrade simulation. 
  By default, ``--params-file=upgrade-params.toml``, DISCO creates that with 
  pre-defined parameters if it does not exist.

.. code-block:: bash

    $ disco config upgrade-cost-analysis --show-params .
    Thermal Upgrade Config
    ----------
    Parameter                 Value
    line_loading_limit      : 1.0
    dt_loading_limit        : 1.0
    line_safety_margin      : 1.5
    xfmr_safety_margin      : 1.5
    nominal_voltage         : 120
    max_iterations          : 20
    create_upgrade_plots    : false
    tps_to_test             : [0.2, 1.8, 0.1, 0.9]
    create_upgrades_library : true
    upgrade_library_path    :

    Voltage Upgrade Config
    ----------
    Parameter                     Value
    target_v                    : 1
    initial_voltage_upper_limit : 1.0583
    initial_voltage_lower_limit : 0.9167
    final_voltage_upper_limit   : 1.05
    final_voltage_lower_limit   : 0.95
    nominal_voltage             : 120
    nominal_pu_voltage          : 1
    tps_to_test                 : [0.2, 1.3, 0.1, 0.9]
    create_topology_plots       : false
    cap_sweep_voltage_gap       : 1
    reg_control_bands           : [1, 2]
    reg_v_delta                 : 0.5
    max_regulators              : 4
    use_ltc_placement           : true
    thermal_scenario_name       : ThermalUpgrade

    Upgrade params from 'upgrade-params.toml'.

These parameters would be applied to all upgrade simulation jobs globally. 
You can cutomize the values by editing this params file manually, then save.

    [1] Thermal Upgrade Config: a dict configuration for thermal upgrade post-processing in PyDSS.

    .. note::

        If ``create_upgrades_library = true``, then ``upgrade_library_path`` is not 
        a required filed. However, if ``false``, then ``upgrade_library_path`` 
        should be set correctly, and the path is a directory which contains your 
        ``Line_upgrades_library.json``, and ``Transformer_upgrades_library.json``.
        Make sure these upgrades ``json`` files were created before the configuration.

    [2] Voltage Upgrade Config: a dict configuration for voltage upgrade post-processing in PyDSS.

    .. note::

        In this config, ``Thermal scenario name`` is default to ``ThermalUpgrade``, 
        your overrides to this would not apply.

* **config-file**: the output config file, by default, it's ``config.json``.


After we learned the parameters, then we are going to create the job configs for
upgrade cost analysis.

**- Single upgrade cost analysis**

Run ``disco config upgrade-cost-analysis`` to generate the job configuration file,
which will create a ``config.json`` file,

.. code-block:: bash

    $ disco config upgrade-cost-analysis upgrade-cost-analysis-models


**- Sequential Upgrade Analysis with considering job order**

.. code-block:: bash

    $ disco config upgrade-cost-analysis upgrade-cost-analysis-models --sequential-upgrade
    $ disco config upgrade-cost-analysis upgrade-cost-analysis-models --sequential-upgrade --nearest-redirect

* **sequential-upgrade**: the value is ``true`` or ``flase``, default is ``false``. 
  If ``true``, it'll run upgrades sequentially based on the job order. The job 
  order is determined by ``job_order`` value in model inputs, please 
  make sure the values are provided if ``sequential-upgrade`` is 
  ``true``.Then upgrade simulations runs from lower level of ``job_order`` 
  to higher level within feeder.

* **nearest-redirect**, by default ``false``, it means DISCO redirects the 
  upgrade DSS files from all lower-order jobs. If ``true``, DISCO will redirect 
  upgrade DSS files only from nearest lower-order jobs. For example, suppose we 
  have four jobs, the job order are 1, 2, 3, 4. If ``nearest-redirect=false``, 
  DISCO will redirect upgrade DSS files generated from job-1, job-2 and job-3 
  to job-4. If ``nearest-redirect=true``, then DISCO will only redirect 
  upgrade DSS files generated from job-3 to job-4.


**2. Submit Jobs**

Now, our ``config.json`` is created, too submit jobs, use JADE command below:

.. code-block:: bash

    $ jade submit-jobs config.json


**3. Job Analysis**

After jobs finish, check the results using ``jade show-results``.

.. code-block:: bash

    $ jade show-results
    Results from directory: output
    JADE Version: 0.1.0
    02/23/2020 16:20:12

    +-----------------------------------------+-------------+----------+--------------------+----------------------------+
    |                 Job Name                | Return Code |  Status  | Execution Time (s) |      Completion Time       |
    +-----------------------------------------+-------------+----------+--------------------+----------------------------+
    | feeder_3__-1__None__None__deployment0.dss |      0      | finished | 9.103492021560669  | 2020-02-23 16:20:02.732357 |
    |  feeder_3__3__1.15__1.0__deployment1.dss  |      0      | finished |  9.10144591331482  | 2020-02-23 16:20:02.734277 |
    |  feeder_3__3__1.15__1.0__deployment2.dss  |      0      | finished |  9.09758710861206  | 2020-02-23 16:20:02.734846 |
    |  feeder_3__3__1.15__1.0__deployment3.dss  |      0      | finished | 10.095330953598022 | 2020-02-23 16:20:03.736296 |
    |  feeder_3__3__1.15__1.0__deployment4.dss  |      0      | finished | 10.09266185760498  | 2020-02-23 16:20:03.737270 |
    |  feeder_3__3__1.15__1.0__deployment5.dss  |      0      | finished | 10.08967399597168  | 2020-02-23 16:20:03.738050 |
    |  feeder_1__-1__None__None__deployment0.dss |      0      | finished | 16.100937843322754 | 2020-02-23 16:20:09.754281 |
    |   feeder_1__3__1.15__1.0__deployment1.dss  |      0      | finished | 17.099663019180298 | 2020-02-23 16:20:10.757113 |
    |   feeder_1__3__1.15__1.0__deployment2.dss  |      0      | finished | 18.098870992660522 | 2020-02-23 16:20:11.760401 |
    |   feeder_1__3__1.15__1.0__deployment3.dss  |      0      | finished |  18.0959370136261  | 2020-02-23 16:20:11.761575 |
    |   feeder_1__3__1.15__1.0__deployment4.dss  |      0      | finished | 18.091224193572998 | 2020-02-23 16:20:11.762137 |
    |   feeder_1__3__1.15__1.0__deployment5.dss  |      0      | finished | 18.080937147140503 | 2020-02-23 16:20:11.762635 |
    +-----------------------------------------+-------------+----------+--------------------+----------------------------+

    Num successful: 12
    Num failed: 0
    Total: 12

    Avg execution time (s): 13.60
    Min execution time (s): 9.10
    Max execution time (s): 18.10

The ``UpgradeCostAnalysis`` results are stored in each job output direcotry, please check ``post-process-results.json``
and ``post_process`` subfolder for CSV outputs. For example, in job directory ``/data/tests/output/job-outputs/feeder_3__3__1.15__1.0__deployment3.dss``.
The ``post-process-results.json`` looks like this,

.. code-block:: python

    {
        "job": "feeder_3__3__1.15__1.0__deployment3.dss",
        "post-process": "UpgradeCostAnalysis",
        "results": {
            "inputs": [
                ...
            ],
            "outputs": [
                {
                    "result_type": "detailed_line_upgrade_costs",
                    "data": "output/job-outputs/feeder_3__3__1.15__1.0__deployment3.dss/post_process/detailed_line_upgrade_costs.csv"
                },
                {
                    "result_type": "detailed_transformer_costs",
                    "data": "output/job-outputs/feeder_3__3__1.15__1.0__deployment3.dss/post_process/detailed_transformer_costs.csv"
                },
                {
                    "result_type": "summary_of_upgrade_costs",
                    "data": "output/job-outputs/feeder_3__3__1.15__1.0__deployment3.dss/post_process/summary_of_upgrade_costs.csv"
                }
            ]
        }
    }

The ``post_process`` subfolder contains the CSV files as shown in the JSON ``outputs`` section above.

Done! You've already run the *upgrade cost analysis* with DISCO and JADE successfully.


**4. Logging DISCO**

JADE provides funcationality of logging ``disco``, if DISCO related logging messages do not show up,
please add the logger ``disco`` to JADE via this command:

.. code-block:: bash

    jade extensions add-logger disco

Now, more logging messages should help you identify the reasons of job failure if any.
