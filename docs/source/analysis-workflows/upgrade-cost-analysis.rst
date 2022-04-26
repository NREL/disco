Upgrade Cost Analysis
=====================

This chapter introduces the workflow for conducting *upgrade cost analysis* by using DISCO commands
step by step or DISCO pipeline, where the pipeline chains the individual steps and runs upgrade cost
analysis seamlessly. In the following two sections we will introduce the two methods separately.

The following commands run with default options. If you need any customization, please run ``--help`` on
the commands to see the available options.

Step-by-Step Workflow
---------------------

**1. Transform Model**

Prepare the model with PV deployments by using DISCO model transformation.

.. code-block:: bash

    $ disco transform-model tests/data/smart-ds/substations upgrade -o upgrade-models

Load shape profiles for ``Load`` elements are not used by the upgrade module, and so we recommend that
you remove them from the models in order to speed-up the simulations. Do so with this option:

.. code-block:: bash

    $ disco transform-model tests/data/smart-ds/substations upgrade --exclude-load-profile -o upgrade-models

**2. Create Config**

With the transformed model, create the `config.json` file with submittable jobs.

.. code-block:: bash

    $ disco config upgrade upgrade-models

DISCO will use default upgrade parameters if the option ``--params-file`` is not specified.
If ``--params-file`` is specified, that file must contain all required parameters.

Here are optional parameters that you can customize in the same file:

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

Submit jobs by using JADE and conduct upgrade cost analysis within each job. 
This command assumes that you are running on a local system. Please remove the option
``--local`` if you run on an HPC.

.. code-block:: bash

    $ jade submit-jobs config.json --local --force

This step will generate the directory ``output``, which contains all upgrade results.

**4. Upgrade Analysis**

Run post-processing to aggregate upgrade cost analysis results and create analysis CSV tables.

.. code-block:: bash

    $ disco-internal make-upgrade-tables output

If everything succeeds, it produces two aggregated tables: ``upgrade_summary.csv`` and
``total_upgrade_costs.csv``. 


Pipeline Workflow
-----------------

**1. Create Template**

Create a DISCO pipeline template file. By default, the output file is ``pipeline-template.toml``.

.. code-block:: bash

    $ disco create-pipeline template --task-name UpgradeTask --simulation-type upgrade --upgrade-analysis ~/Workspace/disco/tests/data/smart-ds/substations

Here, we need to enable the ``--upgrade-analysis`` option.

**2. Config Pipeline**

Update the pipeline template file for customization if needed. Then create the pipeline config file
``pipeline.json`` with this command.

.. code-block:: bash

    $ disco create-pipeline config pipeline-template.toml


**3. Submit Pipeline**

Submit the pipeline with JADE

.. code-block:: bash

    $ jade pipeline submit pipeline.json

If everything succeeds, it produces same aggregated upgrade tables in ``output-stage1``.
