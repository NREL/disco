.. disco documentation master file, created by
   sphinx-quickstart on Mon May  6 14:12:42 2019.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

*******************
DISCO Documentation
*******************
DISCO (Distribution Integration Solution Cost Options) is an NREL-developed, 
python-based software tool for conducting scalable, repeatable distribution analyses. 
While DISCO was originally developed to support photovoltaic (PV) impact analyses, 
it can also be used to understand the impact of other distributed energy resources (DER) 
and load changes on distribution systems. Analysis modules currently included in DISCO are:

* Snapshot hosting capacity analysis, in which hosting capacity is based on a 
  traditional definition of if operating thresholds are exceeded for 
  worst-case/bounding snapshots in time
* Snapshot impact analysis, which calculates the same impact metrics as 
  hosting capacity, but for specific user-defined PV deployment scenarios
* Dynamic hosting capacity analysis, in which hosting capacity is calculating 
  using quasi-static time-series (QSTS) simulations and dynamic impact metrics 
  for voltage and thermal loading. PV curtailment, 
  number of device (voltage regulator, capacitor switch) operations, and 
  energy losses are also calculated as part of this analysis because excessive 
  PV curtailment, increases in device operations and associated replacement 
  cost increases, and energy losses can also serve to limit how much PV can 
  be economically interconnected to a given feeder.  
* Dynamic impact analysis, which is to dynamic hosting capacity analysis as 
  snapshot impact analysis is to snapshot hosting capacity analyses. 
* Automated upgrade cost analysis, which involves automatically determine 
  distribution system upgrades required to mitigate any voltage and thermal 
  violations that exist on the feeder and then calculate the cost associated 
  with those upgrades. This module current only considers traditional infrastructure 
  upgrade options (reconductoring, upgrade transformers, installing voltage 
  regulators and capacitor banks, and changing the controls or setpoints on 
  voltage regulators and capacitor banks). 

DISCO analysis is based on power flow modeling with OpenDSS used as the simulation engine. 
PyDSS (https://nrel.github.io/PyDSS) is used to interface with OpenDSS 
and provide additional control layers. 

The benefit of using DISCO instead of just directly using OpenDSS or PyDSS is two-fold:

* DISCO provides the infrastructure required to run a large number of analyses 
  by managing job submission and execution through JADE (https://nrel.github.io/jade/).
* DISCO provides ready-made, tested code to calculate snapshot and dynamic impact 
  metrics, allowing for repeatable analyses across projects and teams without 
  having to re-create code to process OpenDSS results. 
* DISCO’s automated upgrade cost analysis tool provides a way to conduct upgrade 
  cost analyses over a large number of feeders where manual upgrade analysis 
  would be too time-consuming to execute. The default unit cost database 
  included with DISCO also provides unit cost information that can be used in 
  cost estimates if the user does not have any cost data specific to their own 
  company or scenario. 

Examples of how DISCO has been or is currently being used are:

* Automated impact and upgrade cost analysis for the Los Angeles 100% Renewable 
  Energy Study, which required understanding upgrade needs on ~2,000 circuits 
  based on load and DER changes associated with 100% renewables pathways.
* Evaluating curtailment risk associated with using advanced inverter controls 
  and flexible interconnection options for PV grid integration on 100’s of circuits. 

DISCO does not yet have the ability to conduct end-to-end techno-economic analyses 
of different distribution integration solutions, including looking at impact on 
customer bills, utility revenue, or the economic impact to customers and utilities 
of reduced electricity demand. Thus, this is not a tool for comprehensive 
techno-economic analysis. 

.. toctree::
   :maxdepth: 1
   :caption: User Guide

   installation
   overview
   quick-start
   data-sources
   pv-deployments
   transform-models
   analysis-workflows
   pipelines
   debugging-issues
   data-ingestion
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
