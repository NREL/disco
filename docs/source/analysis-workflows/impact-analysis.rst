Impact Analysis
===============
This section shows how to perform customized analysis with time-series simulations on a set of input models.

Other sections of this documentation describe workflows that rely on DISCO/PyDSS to collect
specific metrics from each simulation. For example, the dynamic hosting capacity analysis workflow
collects metrics for max instantaneous and moving-average line and transformer loading violations.
It does not store values for every line and transformer at every time point because of the amount
of storage space that requires. This section shows how to collect all of the data.

Transform Model
---------------
As with earlier sections this assumes that you have cloned the disco repo to the ``~/disco`` directory.
Transform the source models into DISCO models with this command:

.. code-block:: bash

    $ disco transform-model ~/disco/tests/data/smart-ds/substations/ time-series
    Transformed data from ~/disco/tests/data/smart-ds/substations/ to time-series-feeder-models for TimeSeries Analysis.

.. note:: For your own models you will likely need to set ``--start``, ``--end``, and ``--resolution``.


Config Jobs
-----------

1. Copy this text into a file called ``exports.toml``. This will instruct PyDSS to store each of these
   properties for each element at each time point.

::

    [Loads.Powers]
    store_values_type = "all"

    [PVSystems.Powers]
    store_values_type = "all"

    [Buses.puVmagAngle]
    store_values_type = "all"

    [Circuits.TotalPower]
    store_values_type = "all"

    [Circuits.LineLosses]
    store_values_type = "all"

    [Circuits.Losses]
    store_values_type = "all"

    [Lines.Currents]
    store_values_type = "all"

    [Lines.NormalAmps]
    store_values_type = "all"

    [Lines.Losses]
    store_values_type = "all"

    [Lines.Powers]
    store_values_type = "all"

    [Transformers.Currents]
    store_values_type = "all"

    [Transformers.Losses]
    store_values_type = "all"

    [Transformers.NormalAmps]
    store_values_type = "all"

    [Transformers.Powers]
    store_values_type = "all"

2. Create the configuration with all reports disabled, custom exports, all data exported, a custom
   DC-AC ratio, and a specific volt-var curve.

.. note:: If you're using a Windows terminal, the ``\`` characters used here for line breaks probably won't work.

.. code-block:: bash

    $ disco config time-series time-series-feeder-models \
        --config-file time-series-config.json \
        --volt-var-curve volt_var_ieee_1547_2018_catB \
        --dc-ac-ratio=1.0 \
        --exports-filename exports.toml \
        --export-data-tables \
        --thermal-metrics=false \
        --voltage-metrics=false \
        --feeder-losses=false


Submit Jobs
-----------
Run the jobs with JADE. Two examples are shown: one on a local machine and one on an HPC.

.. code-block:: bash

    $ jade submit-jobs --local time-series-config.json -o time-series-output
    $ jade submit-jobs -h hpc_config.toml time-series-config.json -o time-series-output

Confirm that all jobs passed.

.. code-block:: bash
    
    $ jade show-results -o time-series-output

View Output Files
-----------------
Each job's outputs will be stored in ``time-series-output/job-outputs/<job-name>/pydss_project/project.zip``.
Extract one zip file. You will see exported data for all element properties. For example, this file
contains bus voltages for the volt-var scenario: ``Exports/control_mode/Buses__puVmagAngle.csv``.
The same file will exist for the pf1 scenario.

Access Results Programmatically
-------------------------------
DISCO includes analysis code to help look at thermal loading and voltage violations. Here is
some example code:

.. code-block:: python

    import logging
    import os

    from jade.loggers import setup_logging
    from disco.pydss.pydss_analysis import PyDssAnalysis, PyDssScenarioAnalysis
    from disco.extensions.pydss_simulation.pydss_configuration import PyDssConfiguration

    logger = setup_logging("config", "log.txt", console_level=logging.INFO)

    output_dir = "time-series-output"
    config = PyDssConfiguration.deserialize(os.path.join(output_path, "config.json"))
    analysis = PyDssAnalysis(output_path, config)
    analysis.show_results()

    # Copy name from the output of show_results().
    name = analysis.list_results()[1].name

    # Look up job-specific parameters.
    job = analysis.get_job(name)
    print(job)
    print(job.model.deployment)
    print(job.model.deployment.project_data)

    simulation = analysis.get_simulation(name)

    # Get access to result dataframes.
    results = analysis.read_results(simulation)
    scenario = results.scenarios[0]
    scenario_analysis = PyDssScenarioAnalysis(simulation, results, scenario.name)

    # Get list of voltage magnitudes for each bus.
    voltages_per_bus = scenario_analysis.get_pu_bus_voltage_magnitudes()

    # Get loading percentages.
    line_loading = scenario_analysis.get_line_loading_percentages()
    transformer_loading = scenario_analysis.get_transformer_loading_percentages()

    # Find out what classes and properties are available.
    for element_class in scenario.list_element_classes():
        for prop in scenario.list_element_properties(element_class):
            print(element_class, prop)

    for name in scenario.list_element_names("Lines", "Currents"):
        df = scenario.get_dataframe("Lines", "Currents", name)
        print(df.head())

    # Browse static element information.
    for filename in scenario.list_element_info_files():
        print(filename)
        df = scenario.read_element_info_file(filename)
        print(df.head())

    # Use class names to read specific element infomation.
    df = scenario.read_element_info_file("Loads")
    df = scenario.read_element_info_file("PVSystems")

    # Read events from the OpenDSS event log.
    event_log = scenario.read_event_log()

    # Get the count of each capacitor's state changes from the event log.
    capacitor_changes = scenario.read_capacitor_changes()


Use the PyDSS Data Viewer
-------------------------
PyDSS includes a data viewer that makes it easy to plot circuit element values in a Jupyter
notebook. Refer to its `docs <https://nrel.github.io/PyDSS/tutorial.html#data-viewer>`_.
