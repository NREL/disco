***********
Quick Start
***********

This tutorial will show an example by using SMART-DS models with snapshot
impact analysis.

Source Data
===========

Suppose the DISCO repo is downloaded to ``~/disco`` directory, where the
SMART-DS data is located in the directory ``tests/data/smart-ds/substations/``.


Transform Model
===============

Given snapshot impact analysis type, DISCO takes directory inputs of SMART-DS 
models and transforms them into DISCO models.

.. code-block:: bash

    $ disco transform-model ~/disco/tests/data/smart-ds/substations/ snapshot
    Transformed data from ~/disco/tests/data/smart-ds/substations/ to snapshot-models for Snapshot Analysis.

By default, it generates a directory named ``snapshot-models``
with transformed models, i.e. DISCO mdoels.


Config Jobs
===========

Then config jobs using DISCO with ``snapshot`` command,

.. code-block:: bash

    $ disco config snapshot ./snapshot-models
    Created config.json for Snapshot Analysis

A job config file named ``config.json`` was created.


Submit Jobs
===========

Then ``config.json`` can be submitted through JADE.

.. code-block:: bash

    $ jade submit-jobs config.json

.. note::

    If you are submitting jobs on HPC, you'll need the ``hpc_config.toml`` file
    which can be found in the root of JADE. Copy and modify it as necessary. 
    Refer to `JADE instructions 
    <https://nrel.github.io/jade/tutorial.html#cli-execution>`_ 
    to submit and run the jobs.

Then, the submitted jobs run to completion and generate an output directory
named ``output``.

Result Analysis
===============

To get a quick summary of job results using JADE:

.. code-block:: bash
    
    $ jade show-results
    Results from directory: output
    JADE Version: 0.1.1
    01/04/2021 08:52:36

    +-----------------------------------------+-------------+----------+--------------------+----------------------------+
    |                 Job Name                | Return Code |  Status  | Execution Time (s) |      Completion Time       |
    +-----------------------------------------+-------------+----------+--------------------+----------------------------+
    |  p1uhs10_1247__p1udt14394__random__1__5 |      0      | finished | 23.069955110549927 | 2021-01-04 08:52:35.939785 |
    | p1uhs10_1247__p1udt14394__random__1__10 |      0      | finished | 23.06603503227234  | 2021-01-04 08:52:35.942345 |
    |  p1uhs10_1247__p1udt14394__random__2__5 |      0      | finished | 23.062479972839355 | 2021-01-04 08:52:35.943899 |
    | p1uhs10_1247__p1udt14394__random__2__10 |      0      | finished | 23.05748414993286  | 2021-01-04 08:52:35.944780 |
    +-----------------------------------------+-------------+----------+--------------------+----------------------------+

    Num successful: 4
    Num failed: 0
    Total: 4

    Avg execution time (s): 23.06
    Min execution time (s): 23.06
    Max execution time (s): 23.07

This is the complete workflow for conducting snapshot impact analysis on
SMART_DS feeders.
