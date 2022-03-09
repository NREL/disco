Hosting Capacity Analysis
=========================

This section shows how to conduct *hosting capacity analysis* using DISCO pipeline with *snapshot*
and *time-series* models as inputs. This tutorial assumes there's an existing ``snapshot-models`` 
directory generated from the ``transform-model`` command as below. The workflow below can also be 
applied to ``time-series-models``.

**1. Config Pipeline**

Check the ``--help`` option for creating pipeline template.

.. code-block:: bash

    $ disco create-pipeline template --help
    Usage: disco create-pipeline template [OPTIONS] INPUTS

      Create pipeline template file

    Options:
      -P, --preconfigured             Whether inputs models are preconfigured
                                      [default: False]
      -s, --simulation-type [snapshot|time-series]
                                      Choose a DISCO simulation type  [default:
                                      snapshot]
      -i, --impact-analysis           Enable impact analysis computations
                                      [default: False]
      -h, --hosting-capacity          Enable hosting capacity computations
                                      [default: False]
      -p, --prescreen                 Enable PV penetration level prescreening
                                      [default: False]
      -t, --template-file TEXT        Output pipeline template file  [default:
                                      pipeline-template.toml]
      -r, --reports-filename TEXT     PyDSS report options. If None, use the
                                      default for the simulation type.
      --help                          Show this message and exit.


Given an output directory from ``transform-model``, we use this command with ``--preconfigured`` option
to create the template.

.. code-block:: bash

    $ disco create-pipeline template --simulation-type=snapshot --hosting-capacity --preconfigured snapshot-models


.. note::

    For configure time-series hosting capacity pipeline, use ``--simulation-type=time-series``


It creates the ``pipeline-template.toml`` with configurable parameters of different sections. Update
parameter values if need, then run

.. code-block:: bash

    $ disco create-pipeline config pipeline-template.toml

This command creates a ``pipeline.json`` file containing two stages:

* stage 1 - simulation
* stage 2 - post-process

Accordingly, there would be an output directories for each stage,

* output-stage1
* output-stage2

**2. Submit Pipeline**

With configured DISCO pipeline in ``pipeline.json``, the next step is to submit the pipeline by using JADE:

.. code-block:: bash

    $ jade pipeline submit pipeline.json

What does each stage do?
* In simulation stage, it runs power flow simulation and collect report metrics in CSVs.
* In post-process stage, it takes the metrics from previous stage and calculates the hosting capacity.


**3. Check Results**

Upon successful completion of DISCO model simulation, the following stage (post-process) will take
the simulation results, collect metrics from it, and report in CSV formats. There are five tables in
``output-stage1``

* ``feeder_head_table.csv``
* ``feeder_losses_table.csv``
* ``metadata_table.csv``
* ``thermal_metrics_table.csv``
* ``voltage_metrics_table.csv``

Each table contains different set of metrics related to the *snapshot* or *time-series* simulation.
The hosting capacity results are computed based on these metrics, along with the CSV metrics in the
same output directory ``output-stage1``, there are hosting capacity results generated in JSON through
post-processing.

* ``hosting_capacity_summary__<scenario_name>.json``
* ``hosting_capacity_overall__<scenario_name>.json``

The scenarion name could be ``scenario``, ``pf1`` and/or ``control_mode``, depending on your 
simulation type and/or ``--with-loadshape`` option.


**4. Results database**

With this pipeline, the hosting capacity results and report metrics would be ingested into a
SQLite database named ``results.sqlite`` by default which could be found in ``output-stage1``. 
You can use standard SQL to query data, and perform further analysis. 

If you want to ingest the results into another database, or an existing database, please specify
the absolute path of the database.

For sqlite query examples, please refer to the Jupyter notebook ``notebooks/db-query.ipynb`` in
the source code repo.