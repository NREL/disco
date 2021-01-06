Analysis Deployment
===================

To get a quick summary of job results:

.. code-block:: bash

    $ jade show-results [--output OUTPUT-DIR]

Here is how to reload simulation objects to perform analysis. 
This example is based on a pydss_simulation. 
For generic analysis use JobAnalysis instead of PyDssAnalysis.

.. code-block:: python

    import logging
    import os

    from jade.loggers import setup_logging
    from disco.pydss.pydss_analysis import PyDssAnalysis
    from disco.extensions.pydss_simulation.pydss_configuration import PyDssConfiguration

    logger = setup_logging("config", "log.txt", console_level=logging.INFO)

    config = PyDssConfiguration.deserialize("config.json")
    analysis = PyDssAnalysis("output", config)
    analysis.show_results()

    # Copy name from the output of show_results().
    name = analysis.list_results()[0].name

    # Look up job-specific parameters.
    job = analysis.get_job(name)
    print(job)
    print(job.deployment)
    print(job.deployment.project_data)

    simulation = analysis.get_simulation(name)

    # Get access to result dataframes.
    results = analysis.read_results(simulation)
    scenario = results.scenarios[0]

    # Get loading percentages.
    line_loading = scenario.get_line_loading_percentages()
    transformer_loading = scenario.get_transformer_loading_percentages()

    # Find out what classes and properties are available.
    for element_class in scenario.list_element_classes():
        for prop in scenario.list_element_properties(element_class):
            print(element_class, prop)

    for name in scenario.list_element_names("Lines", "Currents"):
        df = scenario.get_dataframe("Lines", "Currents", name)
        print(df.head())
        # Limit to phase A terminal 1.
        df_a1 = scenario.get_dataframe("Lines", "Currents", name, phase_terminal="A1")
        print(df.head(df_a1))

    # Browse static element information.
    for filename in scenario.list_element_info_files():
        print(filename)
        df = scenario.read_element_info_file(filename)
        print(df.head())

    # Use class names to read specific element infomation.
    df = scenario.read_element_info_file("Lines")
    df = scenario.read_element_info_file("TransformersPhase")

    # Read events from the OpenDSS event log.
    event_log = scenario.read_event_log(simulation)

    # Get the count of each capacitor's state changes from the event log.
    capacitor_changes = scenario.read_capacitor_changes(simulation)
