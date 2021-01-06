.. _user_scenario_pydss_simulation:

User Scenario PyDSS Simulation
==============================

Workflow Overview
-----------------

The workflow in simple looks like below,

* User creates OpenDSS input files for one or more simulations.
* User creates a JADE configuration for one or more simulation jobs.
* JADE runs the jobs.

And, the implementation of JADE classes in user-defined OpenDSS simulation
are:

* ``UserScenarioPyDssInputs``
* ``UserScenarioDeploymentParameters``
* ``UserScenarioPyDssConfiguration``
* ``UserScenarioPyDssSimulation``


Local OpenDSS Configuration
---------------------------

If you are running on a local OpenDSS directory:

.. code-block:: bash

    $ jade auto-config user_scenario_pydss_simulation <your-opendss-directory>


Simulation Example in Code
--------------------------

Here's a simulation example,

.. code-block:: python

    import logging
    import os

    from jade.loggers import setup_logging
    from disco.extensions.user_scenario_pydss_simulation.user_scenario_pydss_inputs import UserScenarioPyDssInputs
    from disco.extensions.user_scenario_pydss_simulation.user_scenario_pydss_configuration import UserScenarioDeploymentParameters, UserScenarioPyDssConfiguration
    from disco.extensions.user_scenario_pydss_simulation.user_scenario_pydss_simulation import  UserScenarioPyDssSimulation

    logger = setup_logging("config", "log.txt", console_level=logging.INFO)

    dss_directory = "dss-directory"
    dss_file = os.path.join(dss_directory, "Master_noVP.dss")
    scenario = "test"
    inputs = UserScenarioPyDssInputs(dss_directory)
    config = UserScenarioPyDssConfiguration(inputs)
    job = UserScenarioDeploymentParameters(scenario, dss_file)
    config.add_job(job)
    config.dump("config.json")

Now submit the job for execution:

.. code-block:: python

    $ jade submit-jobs config.json
