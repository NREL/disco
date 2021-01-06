Time Series Impact Analysis
===========================

Check the ``time-series-impact-analysis`` command with ``--help`` first,

.. code-block:: bash

    $ disco config time-series-impact-analysis --help
    Usage: disco config time-series-impact-analysis [OPTIONS] INPUTS

    Create JADE configuration for time series impact analysis.

    Options:
    -c, --config-file TEXT       JADE config file to create  [default:
                                config.json]
    -r, --reports-filename TEXT  PyDSS report options  [default: /Users/jgu2/Wor
                                kspace/disco/disco/extensions/pydss_simulation/
                                time_series_impact_analysis_reports.toml]
    --verbose                    Enable debug logging
    --help                       Show this message and exit.


**1. Cofig Jobs**

Assume in current directory, we have a *time-series-imapct-analysis-models* directory
generated from ``transform-model`` command.

.. code-block:: bash

    $ disco config time-series-impact-analysis time-series-impact-analysis-models

**2. Sumbit Jobs**

Submit jobs via JADE,

.. code-block:: bash

    $ jade submit-jobs config.json

**3. Job Analysis**

Job analysis via JADE,

.. code-block:: bash

    $ jade show-results [--output]
