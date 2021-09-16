******************************
SMART-DS DSS MODEL PREPARATION
******************************
Pre-processing is performed on the SMART-DS data to prepare it for hosting capacity analysis.
The chart below shows the various stages of pre-processing performed on the SMART-DS OpenDSS Models.

.. image:: images/SMART-DS-flowchart.png
   :align: center
   :width: 400


SMART-DS Dataset
================
More documentation on the open source SMART-DS datasets can be found at https://www.nrel.gov/grid/smart-ds.html

The dataset can be copied using https://github.com/NREL/disco/blob/main/scripts/copy_smart_ds_dataset.py


Usage:

.. code-block:: bash

    python

Restructure to substation transformer
=====================================
The SMART-DS dataset has Open DSS models defined at the feeder and substation level. In this stage, Open DSS models are restructured and defined such that the analysis can be performed at the substation transformer level. 
This can be performed using https://github.com/NREL/disco/blob/main/scripts/

Usage:

.. code-block:: bash

    python smartds_restructuring_transformer_folder.py BASE_PATH ORIGINAL_DATASET NEW_DATASET LIST_OF_REGIONS")

Example:

.. code-block:: bash

    python smartds_restructuring_transformer_folder.py /projects/distcosts3/SMART-DS/v1.0/2018 SFO SFO_xfmr A,B,C")


Feeder screening & model fixes
==============================
In this, all the base-case feeders are passed through a preliminary screening process. 
Here, disconnected nodes are removed, and the models are checked for connectivity, isolated nodes and extreme cases of thermal or voltage violations.
These would need to be addressed before proceeding to the hosting capacity analysis.


Usage:

.. code-block:: bash

    python


Create PV deployments
=====================
In this stage, PV deployments are generated for hosting capacity analysis. There are 10 sample PV deployments for every placement type (close, random, far) for every 5% increment upto 200% PV to load ratio . 
This can be done using disco, documentation for which can found here:
https://github.nrel.gov/pages/Hosting-Capacity-Analysis/disco/pv-deployments.html



