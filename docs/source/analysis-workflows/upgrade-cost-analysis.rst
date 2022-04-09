Upgrade Cost Analysis
=====================

This chapter introduces the worfkow for conducting *upgrade cost analysis* by using DISCO commands
step by step or DISCO pipeline, where the pipeline chains the individual steps and runs upgrade cost
analysis seamlessly. In the following two sections we will introduce the two method separately.

The following commands run with default options, if need any customization, please run ``--help`` on
according commands, and check details about command options.

DISCO Steps
-----------

**1. Transform Model**

Prepare the model with PV deployments by using DISCO model transformation.

.. code-block:: bash

    $ disco transform-model tests/data/smart-ds/substations upgrade -o upgrade-models

If you wish to exclude the load profile from ``Loads.dss`` model, then run this command

.. code-block:: bash

    $ disco transform-model tests/data/smart-ds/substations upgrade --exclude-load-profile -o upgrade-models

Upgrade cost simulation runs faster with model which does not include the load profiles.

**2. Create Config**

With the transformed model, create the `config.json` file with submittable jobs.

.. code-block:: bash

    $ disco config upgrade upgrade-models

Here, DISCO would default upgrade parameters if this option ``--params-file`` is not specified,
where these parameters are all required. You could customize the parameter values based on project
requirements. Except for the required ones, there are also optional parameters which could be
provided to control the upgrade simulations, the optional parameters include the followings,

.. code-block::

    [thermal_upgrade_params]
    parallel_transformer_limit = 4
    parallel_lines_limit = 4
    upgrade_iteration_threshold = 5
    timepoint_multipliers = {}

    [voltage_upgrade_params]
    capacitor_sweep_voltage_gap = 1.0
    reg_control_bands = [1, 2]
    reg_v_delta = 0.5
    max_regulators = 4
    place_new_regulators = false
    use_ltc_placement = false
    timepoint_multipliers = {}
    capacitor_action_flag = true
    existing_regulator_sweep_action = true


**3. Submit Jobs**

Submit jobs by using JADE and conduct upgrade cost analysis within each job. Here, we assume
it run on localhost, please remove the option ``--local`` if run on HPC.

.. code-block:: bash

    $ jade submit-jobs config.json --local --force

This step will generate ``output`` directory which contains all upgrade simulation results.

**4. Upgrade Analysis**

Run post-processing to aggregate upgrade cost analysis results, and create analysis CSV tables.

.. code-block:: bash

    $ disco-internal make-upgrade-tables output

If everything works good, finally it produces two aggregated tables: ``upgrade_summary.csv`` and
``total_upgrade_costs.csv``. 


Pipeline Steps
--------------

**1. Create Template**

Create DISCO pipeline template file, by default, the output file is ``pipeline-template.toml``.

.. code-block:: bash

    $ disco create-pipeline template --task-name UpgradeTask --simulation-type upgrade --upgrade-analysis ~/Workspace/disco/tests/data/smart-ds/substations

Here, we need to enable ``--upgrade-analysis`` option.

**2. Config Pipeline**

Update the pipeline template file for customization if need, the create the pipeline config file
named ``pipeline.json``.

.. code-block:: bash

    $ disco create-pipeline config pipeline-template.toml


**3. Submit Pipeline**

Submit the pipeline by using JADE, 

.. code-block:: bash

    $ jade pipeline submit pipeline.json

If everything runs good, then it produces same aggregated upgrade tables in ``output-stage1``.
