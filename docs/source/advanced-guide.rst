.. _advanced_guide:

Advanced Guide
##############

This page describes how to use the DISCO package to create, modify, and run
simulations locally or on an HPC.

DISCO create JADE extensions in DISCO, and calls high-level interfaces of PyDSS 
to run simulations on top of OpenDSS.The supported simulations in DISCO currently 
include:

  * DISCO PV Deployment Simulation via ``pydss_simulation`` extension.
  * User Scenario PyDSS Simulation via ``user_scenario_pydss_simulation``.
  * Automated Upgrade Simulation via ``automated_upgrade_simulation``


Please refer to the following links and check the simulation types in detail.

.. toctree::
  :maxdepth: 1

  advanced-guide/analysis-deployment
  advanced-guide/user-scenario-pydss-simulation
  advanced-guide/automated-upgrade-simulation

If you need to create your own extension, the 
`JADE documentation <https://nrel.github.io/jade/advanced_usage.html>`_
can provides step-by-step instructions.
