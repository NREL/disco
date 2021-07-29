Snapshot Hosting Capacity Analysis
==================================

The following steps show how to conduct *hosting capacity analysis* using DISCO pipeline. 
This tutorial assumes there's an existing ``snapshot-models`` 
directory generated from the ``transform-model`` command in the current working 
directory.

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

    $ disco create-pipeline template --hosting-capacity --preconfigured snapshot-models

It creates the ``pipeline-template.toml`` with configurable parameters of different sections. Update
parameter values if need, then run

.. code-block:: bash

    $ disco create-pipeline config pipeline-template.toml

This command creates a ``pipeline.json`` file containing two stages: simulation and post-process,
where the hosting capacity analysis happens in the post-processing stage.

**2. Submit Pipeline**

With configured DISCO pipeline in ``pipeline.json``, the next step is to submit the pipeline by using JADE:

.. code-block:: bash

    $ jade pipeline submit pipeline.json

**3. Check Metrics**

Upon successful completion of DISCO model simulation, the following stage (post-process) will take
the simulation results, collect metrics from it, and report in CSV formats. There are five tables,

* ``feeder_head_table.csv``
* ``feeder_losses_table.csv``
* ``metadata_table.csv``
* ``thermal_metrics_table.csv``
* ``voltage_metrics_table.csv``

Each table contains different set of metrics, inspect the values for hosting capacity analysis.
