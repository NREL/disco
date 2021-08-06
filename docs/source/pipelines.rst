*********
Pipelines
*********

To conduct power flow simulations and analysis, people normally need to perform several steps, including
transform model, create configurations, submit jobs, and run post-processing scripts/commands. To streamline this workflow, DISCO leverages the power of
JADE pipeline and manage the steps using stages in simpler manner.

A pipeline can contain one or more stages, each stage can perform config and submit jobs
to generate stage results. The result output from prior stage can be passed to its subsequent stage
as inputs, so that produces further results. DISCO uses pipeline ``template`` and pipeline
``config`` to manage the DISCO analysis workflow.

To generate a pipeline template file, and create a pipeline config file based on it,
use this group command below:

.. code-block:: bash

    $ disco create-pipeline --help

The source models that DISCO pipeline currently supports include:

    * :ref:`SourceTree1Model`


SourceTree1Model
================

Snapshot Hosting Capacity Analysis
----------------------------------

**1. Create Pipeline Template File**

To create pipeline template, use this command:

.. code-block:: bash

    $ disco create-pipeline template <INPUTS>

The opendss model inputs - ``<INPUTS>``  can be source models or preconfigured models.


.. note::

    When creating the pipeline template for snapshot simulation (default), the flag ``--with-loadshape``
    or ``--no-with-loadshape`` must be set to indicate if there's ``LoadShapes.dss`` redirected in  models
    and the according mode it's going to run with,
    
    * if ``--no-with-loadshape``, DISCO runs snapshot simulation by using ``Snapshot`` mode.
    * if ``--with-loadshape``, DISCO runs snapshot simulation by using ``QSTS`` mode with only one timestamp.

a. Source Model Inputs

.. code-block:: bash

    $ disco create-pipeline template tests/data/smart-ds/substations -s snapshot --hosting-capacity -t pipeline-template.toml

b. Preconfigured Model Inputs

Create preconfigured models:

.. code-block:: bash

    $ disco transform-model tests/data/smart-ds/substations snapshot -o snapshot-feeder-models

Then, use ``--preconfigured`` flag to indicate the input models ``snapshot-feeder-models`` are preconfigured.

.. code-block:: bash

    $ disco create-pipeline template snapshot-feeder-models --preconfigured -s snapshot --hosting-capacity -t pipeline-template.toml

The commands above create a pipeline template file named ``pipeline-template.toml``.


**2. Update Pipeline Template File**

In the template generated above, there are 3 sections, including:

    * ``model``
    * ``simulation``
    * ``postprocess``

You can modify the different types of parameters in each section based on your task requirements
on model transform, config/submit jobs, and postprocess. To check the meaning of each parameter,
run ``--help`` on its command.

    * ``model.transform-params`` from ``disco transform-model <INPUTS> snapshot``
    * ``simulation.config-params`` from ``disco config snapshot``.
    * ``simulation.submitter-params`` from ``jade submit-jobs``.
    * ``postprocess.config-params`` from ``jade config create``.
    * ``postprocess.submitter-params`` from ``jade submit-jobs``

Note that, simulation and postprocess can applied different submitter params, including
``hpc_config``, which enables you to use different partitions to run your jobs on
different stages. To create HPC config file, use command ``jade config create``.


**3. Create Pipeline Config File**

.. code-block:: bash

    $ disco create-pipeline config pipeline-template.toml -c pipeline.json

This step creates the pipeline config file named ``pipeline.json``, which contains the stage
information. In this example, there are 2 stages, JADE run each of the stage in order, and manage
the status of each util it completes the whole workflow.


**4. Sumbit Pipeline Using JADE**

.. code-block:: bash

    $ jade pipeline submit pipeline.json -o snapshot-pipeline-output

Pipeline output directory is ``snapshot-pipeline-output`` in this example,
which contains two stages' results, as shown below:

.. code-block:: bash

    $tree snapshot-pipeline-output/ -L 2
    snapshot-pipeline-output/
    ├── config-stage1.json
    ├── config-stage2.json
    ├── output-stage1
    │   ├── config.json
    │   ├── disco-diff.patch
    │   ├── errors.txt
    │   ├── events
    │   ├── feeder_head_table.csv
    │   ├── feeder_losses_table.csv
    │   ├── jade-diff.patch
    │   ├── job-outputs
    │   ├── metadata_table.csv
    │   ├── processed_results.csv
    │   ├── results.csv
    │   ├── results.json
    │   ├── results.txt
    │   ├── run_jobs_batch_0_events.log
    │   ├── thermal_metrics_table.csv
    │   └── voltage_metrics_table.csv
    ├── output-stage2
    │   ├── config.json
    │   ├── disco-diff.patch
    │   ├── errors.txt
    │   ├── events
    │   ├── jade-diff.patch
    │   ├── job-outputs
    │   ├── processed_results.csv
    │   ├── results.csv
    │   ├── results.json
    │   ├── results.txt
    │   └── run_jobs_batch_0_events.log
    ├── pipeline.json
    └── pipeline_submit.log

From the result tree, the metrics summary tables ``*.csv`` were created in ``output-stage1``
by the postprocess job from stage 2.



Time-series Hosting Capacity Analysis
-------------------------------------

Simlarly, you can run time-series hosting capacity analysis using pipeline.
However, there is a difference for time-series pipeline, where one more
stage named ``prescreen`` could be enabled, so that to prescreen pv penetration levels
and avoid running jobs with higher failure potentials, which could help reduce the consumption of
allocated HPC hours.

**1. Create Pipeline Template File**

.. code-block:: bash

    $ disco create-pipeline template tests/data/smart-ds/substations -s time-series --hosting-capacity -t pipeline-template.toml

If you need to prescreen PV penetration levels, use the flag ``--prescreen`` to create the template.

.. code-block:: bash

    $ disco create-pipeline template tests/data/smart-ds/substations -s time-series --prescreen --hosting-capacity -t pipeline-template.toml

This step create the ``pipeline-template.toml`` file.

**2. Update Pipeline Tempalte File**

There are 3 (or 4, with ``--prescreen`` enabled) sections in the template file generated above.
    * ``model``
    * ``prescreen`` (optional)
    * ``simulation``
    * ``postprocess``

Update the params in each section based on your task requirements,

    * ``model.transform-params`` from ``disco transform-model <INPUTS> time-series``
    * ``prescreen.config-params`` from ``disco config time-series``
    * ``prescreen.prescreen-params`` from ``disco prescreen-pv-penetration-levels create``
        and ``disco prescreen-pv-penetration-levels filter-config``.
    * ``simulation.submitter-params`` from ``jade submit-jobs``.
    * ``postprocess.config-params`` from ``jade config create``.
    * ``postprocess.submitter-params`` from ``jade submit-jobs``

then save it.


**3. Create Pipeline Config File**

.. code-block:: bash

    $ disco create-pipeline config pipeline-template.toml -c pipeline.json

This command creates the pipeline config file named ``pipeline.json``, there are 3 stages if
you have ``--prescreen`` enabled, otherwise, 2 stages - ``simulation`` and ``postprocess``.


**4. Submit Pipeline Using JADE**

.. code-block:: bash

    $ jade pipeline submit pipeline.json -o time-series-pipeline-output

Pipeline output directory is ``time-series-pipeline-output`` in this example,
which contains the results of 3 stages with ``--prescreen`` enabled.

.. code-block:: bash

    $tree time-series-pipeline-output/ -L 2
    time-series-pipeline-output
    ├── config-stage1.json
    ├── config-stage2.json
    ├── config-stage3.json
    ├── output-stage1
    │   ├── config.json
    │   ├── disco-diff.patch
    │   ├── errors.txt
    │   ├── events
    │   ├── filter_prescreened_jobs.log
    │   ├── jade-diff.patch
    │   ├── job-outputs
    │   ├── processed_results.csv
    │   ├── results.csv
    │   ├── results.json
    │   ├── results.txt
    │   └── run_jobs_batch_0_events.log
    │   ├── output-stage2
    │   ├── config.json
    │   ├── disco-diff.patch
    │   ├── errors.txt
    │   ├── events
    │   ├── feeder_head_table.csv
    │   ├── feeder_losses_table.csv
    │   ├── jade-diff.patch
    │   ├── job-outputs
    │   ├── metadata_table.csv
    │   ├── processed_results.csv
    │   ├── results.csv
    │   ├── results.json
    │   ├── results.txt
    │   ├── run_jobs_batch_0_events.log
    │   ├── thermal_metrics_table.csv
    │   └── voltage_metrics_table.csv
    ├── output-stage3
    │   ├── config.json
    │   ├── disco-diff.patch
    │   ├── errors.txt
    │   ├── events
    │   ├── jade-diff.patch
    │   ├── job-outputs
    │   ├── processed_results.csv
    │   ├── results.csv
    │   ├── results.json
    │   ├── results.txt
    │   └── run_jobs_batch_0_events.log
    ├── pipeline.json
    └── pipeline_submit.log

As shown above, the metrics summary tables ``*.csv`` were created in ``output-stage2``
by postprocess job from stage 3.
