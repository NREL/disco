********
Overview
********

This section gives an overview about DISCO, what DISCO can do, what DISCO workflow
looks like, and the main steps to run DISCO workflow.

DISCO can be used for distributed grid system simulation with further analysis.
The analysis types are shown below, behind the scenes, PyDSS support the simulations
for each type of analysis.

* snapshot impact analysis
* hosting capacity analysis (based on snapshot impact analysis results)
* time series impact analysis
* upgrade cost analysis

The diagram below shows the DISCO workflow,

.. image:: images/DISCO-Workflow.png
   :align: center

As shown from the diagram, the main steps to run an analysis workflow are:

* Prepare the OpenDSS models with given data source.
* Transform the source OpenDSS models into DISCO models with deployments.
* Configure JADE jobs using DISCO with prepared DISCO models as inputs.
* Submit jobs using JADE, and wait for job completion.


Data Sources
============

Currengly, DISCO supports several types of data sources (or feeders) in OpenDSS 
data formats.

#. GEM Model, Grid-connected Energy systems Modeling

#. EPRI Model - J1, K1, and M1, https://dpv.epri.com/feeder_models.html

#. SourceTree1 Model, this format requires directory structure *tree1* defined by DISCO - :ref:`SourceTree1Model`.

#. SourceTree2 Model, this format requires directory structure *tree2* defined by DISCO - :ref:`SourceTree2Model`.


Transform Model
===============

Given an analysis type, the source OpenDSS models need to be transformed into 
DISCO models which then could be used as inputs for configuring JADE jobs.


Config Jobs
===========

DISCO has implemented abstract classes in JADE used for configuring jobs, it 
take standard DISCO models as inputs, the generate configuration JSON file.


Submit Jobs
===========

With job configuration file, then JADE commands can be used for job submission on
running hosts, the hosts could be computers, laptops, or HPC. The jobs would be
running in batch, and creates output directory after completion.


Result Analysis
===============

After job runs finished, JADE can assist with job analysis, including the status
of the jobs - success or failed; the execution time of the jobs; the statics of 
compute resources the jobs used; and if there were any errors or events happen, 
etc.
