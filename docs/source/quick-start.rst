***********
Quick Start
***********

This tutorial will show an example by using SMART-DS models with snapshot
impact analysis. Note that you could generally substitute "time-series" for "snapshot"
for that type of simulation.

Source Data
===========

Suppose the DISCO repo is downloaded to the ``~/disco`` directory, where the
SMART-DS data is located in the directory ``tests/data/smart-ds/substations/``.


Transform Model
===============
DISCO transforms the SMART-DS models into DISCO models with this command.

.. code-block:: bash

    $ disco transform-model ~/disco/tests/data/smart-ds/substations/ snapshot
    Transformed data from ~/disco/tests/data/smart-ds/substations/ to snapshot-feeder-models for Snapshot Analysis.

By default, it generates a directory named ``snapshot-feeder-models`` with transformed models.


Config Jobs
===========

Configure jobs for execution through JADE with this command:

.. code-block:: bash

    $ disco config snapshot ./snapshot-feeder-models
    Created config.json for Snapshot Analysis

A job config file named ``config.json`` was created.

Parameters that you may want to configure:

- By default, the PyDSS-exported circuit element properties are taken from
  `snapshot-exports.toml <https://github.com/NREL/disco/blob/main/disco/pydss/config/snapshot-exports.toml>`_.
  Specify a different file with ``-e <your-file>``.
- PyDSS will not automatically export results to CSV files by default.
  You can set ``export_data_tables`` to ``true`` in ``config.json``.
- DISCO applies a DC-AC ratio of 1.15 to all PVSystems by default. You can customize it with the
  option ``--dc-ac-ratio``. Set it to ``1.0`` to prevent any changes to your models.
- DISCO uses a standard IEEE volt-var curve by default. You can customize the value with the option
  ``--volt-var-curve``. This must be a controller name registered with PyDSS.
  Run ``pydss controllers show`` to see the registered controllers.
- DISCO does not store per-element data in reports by default. For example, it stores max/min
  voltages across all buses and not the max/min voltages for each bus.
  You can set ``store_per_element_data`` to ``true`` in ``config.json``.
- Other PyDSS parameters: Refer to the ``pydss_inputs`` section of ``config.json``.
  `PyDSS documentation <https://nrel.github.io/PyDSS/simulation_settings.html>`_

Submit Jobs
===========

Then batch of jobs in ``config.json`` can be submitted through JADE. Two examples are shown below:
one on a local machine and one on an HPC.

.. code-block:: bash

    $ jade submit-jobs --local config.json
    $ jade submit-jobs -h hpc_config.toml config.json

.. note::

    Create hpc_config.toml with ``jade config hpc`` and modify it as necessary.
    Refer to `JADE instructions <https://nrel.github.io/jade/tutorial.html#cli-execution>`_ 
    for additional information on how to customize execution.

The submitted jobs run to completion and generate an output directory named ``output``.

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


Each job output directory contains PyDSS-exported data and reports.

- Reports (ex: thermal_metrics.json, voltage_metrics.json) are stored in ``<output-dir>/job-outputs/<job-name>/pydss_project/project.zip`` in the ``Results`` sub-directory.
- Exported data tables, if enabled, are stored in the ``Exports`` sub-directory.
- You can access the PyDSS-exported data in a Jupyter notebook data-viewer UI or programmatically
  as shown in this `documentation <https://nrel.github.io/PyDSS/tutorial.html#analyze-results>`_.

This is the complete workflow for conducting snapshot impact analysis on SMART_DS feeders.
