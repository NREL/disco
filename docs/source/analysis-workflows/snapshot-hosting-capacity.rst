Snapshot Hosting Capacity
=========================

The following steps show how to conduct *snapshot hosting* using DISCO.
This tutorial assumes there's an existing ``snapshot-models`` 
directory generated from the ``transform-model`` command in the current working 
directory.

**1. Config Jobs**

Check the ``--help`` option for snapshot impact analysis options.

.. code-block:: bash

    $ disco config snapshot --help
    Usage: disco config snapshot [OPTIONS] INPUTS

      Create JADE configuration for snapshot simulations.

    Options:
      -c, --config-file TEXT          JADE config file to create  [default:
                                      config.json]

      -h, --hosting-capacity          Enable hosting capacity computations
                                      [default: False]

      -i, --impact-analysis           Enable impact analysis computations
                                      [default: False]

      --impact-analysis-inputs-filename TEXT
                                      impact analysis inputs  [default: /Users/username
                                      /sandboxes/disco/disco/analysis/impact_analy
                                      sis_inputs.toml]

      -e, --exports-filename TEXT     PyDSS export options  [default: /Users/username
                                      /sandboxes/disco/disco/pydss/config/Exports.
                                      toml]

      --verbose                       Enable debug logging
      --help                          Show this message and exit.

Given an output directory from ``transform-model``, we use this command below to 
configure the snapshot impact analysis jobs.

.. code-block:: bash

    $ disco config snapshot --hosting-capacity --config-file config.json

It generates the ``config.json`` for JADE to submit jobs.

**2. Submit Jobs**

With configured jobs in ``config.json``, all that's left to do is run the jobs:

.. code-block:: bash

    $ jade submit-jobs config.json

**3. Job Analysis**

Upon successful completion of all jobs it will post-process the results and
create a summary file.
