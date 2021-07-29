Time Series Impact Analysis
===========================

Check the ``time-series`` command with ``--help`` first.

.. code-block:: bash

    $ disco config time-series --help
    Usage: disco config time-series [OPTIONS] INPUTS

    Create JADE configuration for time series simulations.

    Options:
    -c, --config-file TEXT          JADE config file to create  [default:
                                    config.json]
    -e, --estimated-run-minutes INTEGER
                                    Estimated per-job runtime. Default is None.
    --calc-estimated-run-minutes / --no-calc-estimated-run-minutes
                                    Calculate estimated per-job runtime by
                                    parsing the OpenDSS files.  [default: calc-
                                    estimated-run-minutes]
    --feeder-losses [true|false]    Whether to enable the Feeder Losses report.
                                    If not set, use the value in --reports-
                                    filename.
    --pv-clipping [true|false]      Whether to enable the PV clipping report. If
                                    not set, use the value in --reports-
                                    filename.
    --pv-curtailment [true|false]   Whether to enable the PV curtailment report.
                                    If not set, use the value in --reports-
                                    filename.
    --thermal-metrics [true|false]  Whether to enable the Thermal Metrics
                                    report. If not set, use the value in
                                    --reports-filename.
    --voltage-metrics [true|false]  Whether to enable the Voltage Metrics
                                    report. If not set, use the value in
                                    --reports-filename.
    -r, --reports-filename TEXT     PyDSS report options  [default:
                                    /Users/jgu2/Workspace/disco-jianli/disco/ext
                                    ensions/pydss_simulation/time_series_reports
                                    .toml]
    --skip-night / --no-skip-night  Don't run convergence algorithm or collect
                                    data during nighttime hours.  [default: no-
                                    skip-night]
    --order-by-penetration / --no-order-by-penetration
                                    Make jobs with higher penetration levels
                                    blocked by those with lower levels. This can
                                    be beneficial if you want the higher-
                                    penetration-level jobs to be canceled if a
                                    job with a lower penetration level fails.
                                    However, it can significantly reduce the
                                    number of jobs that can run simultaneously.
                                    [default: no-order-by-penetration]
    --verbose                       Enable debug logging
    --help                          Show this message and exit.


**1. Cofig Jobs**

Assume in current directory, we have a *time-series-models* directory
generated from the ``transform-model`` command.

.. code-block:: bash

    $ disco config time-series time-series-models

Consider to use ``--thermal-metrics``, ``--voltage-metrics``, or ``--reports-filename`` options
in the command above for generating time-series reports from PyDSS.

**2. Sumbit Jobs**

Submit jobs via JADE

.. code-block:: bash

    $ jade submit-jobs config.json

**3. Job Analysis**

Job analysis via JADE

.. code-block:: bash

    $ jade show-results [--output]
