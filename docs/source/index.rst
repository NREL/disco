.. disco documentation master file, created by
   sphinx-quickstart on Mon May  6 14:12:42 2019.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

*******************
DISCO Documentation
*******************
DISCO is a collection of software modules that run distribution simulations
and analyze results. It's built on top of two other Python packages - PyDSS 
and JADE. 

   * `PyDSS <https://nrel.github.io/PyDSS/index.html>`_ is a high level Python interface for 
     OpenDSS and provides distribution simulations.
   * `JADE <https://nrel.github.io/jade/>`_ is a Python
     package that automates execution of jobs on any computer or HPC, and report results.

The three works together to provide facilities for distribution simulations and analysis.
The followings provide brief descriptions for each about its role in workflow.

What does DISCO do? 

   * Defines a specification for configuring model inputs so that simulation jobs
     can be parallelized through JADE.
   * Provides interfaces for customizing PyDSS configuration and running PyDSS simulations.
   * Runs post-process task based on simulation output data to answer analysis questions.

What does JADE do?

   * Configures jobs, parallelize execution locally or on HPC, report results.
   * Contains general utility functions to help you accesss and process output data.

What does PyDSS do?

   * Provides core functions that DISCO can interact with for distribution simulation.
   * Manages the project settings, simulation types, running states, and simulatioin reports.

.. toctree::
   :maxdepth: 1
   :caption: User Guide

   installation
   overview
   quick-start
   data-sources
   transform-models
   analysis-workflows
   debugging-issues
   advanced-guide

.. toctree::
   :maxdepth: 1
   :caption: Contribution

   build-docs
   license


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
