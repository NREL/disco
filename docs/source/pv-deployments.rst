.. _PVDeployments:

**************
PV Deployments
**************

This section shows how to generate DISCO PV deployments from raw opendss models.

.. _SourceTree1PVDeployments:

SourceTree1 PV Deployments
==========================

The main command going to be used is the one below,

.. code-block:: bash

    $ disco pv-deployments source-tree-1 --action <action-name> --hierarchy <hierarchy> --placement <placement type> INPUT_PATH

There are several actions here related to PV deployments manipulation, including

* ``redirect-pvshapes``: Redirect PVShape.dss in both substation and feeder Master.dss files.
* ``transform-loads``: Transform Loads.dss file before conducting PV deployments.
* ``generate-jobs``: Help generate ``create-pv`` and ``create-configs`` jobs in JSON, i.e., jade config.
* ``restore-feeders``: Before and during PV deployments, Loads.dss and Master.dss files were modified, need to restore after that.
* ``create-pv``: create PV deployments on feeders based on `placement`, `sample` and `penetration` levels.
* ``check-pv``: check if there are PV deployments missing at each `placement`, `sample` and `penetration` level.
* ``remove-pv``: delete PV deployments in case there's something wrong.
* ``create-configs``: create PV config files at each `sample` deployment level.
* ``check-configs``: check if there are PV config files missing in deployment directories.
* ``remove-configs``: remove PV config files in case there's something wrong.
* ``list-feeders``: list feeder paths given input of region, substation or feeder.


Redirect PVShapes
-----------------
Before performing PV deployments, we need to ensure the ``PVShapes.dss`` is redirected in the master 
file located in substation and feeder directories. Two steps are required:

First, you need to generate the PV profiles into a ``PVShapes.dss`` file on your own, and then
copy the ``PVShapes.dss`` into each substation and feeder directories.

Second, run the command below.

.. code-block:: bash

    $ disco pv-deployments source-tree-1 -a direct-pvshapes -h <hierarchy> INPUT_PATH


Transform Loads
---------------
Also, ``Loads.dss`` file under the feeder needs to be transformed before PV deployments, so that to
change load model to suitable center-tap schema if needed. The command to run this is,

.. code-block:: bash

    $ disco pv-deployments source-tree-1 -a transform-loads -h <hierarchy> INPUT_PATH


Generate Jobs
-------------
DISCO provides a command to help generate JADE jobs config files for PV deployments and PV configs, that is,

.. code-block:: bash

    $ disco pv-deployments source-tree-1 -a generate-jobs -h <hierarchy> INPUT_PATH

The hierarchy options are:

    * ``city``
    * ``region``
    * ``substation``
    * ``feeder``

We recommand to run this ``generate-jobs`` command with ``--hierarchy=city`` and generate jobs on all
feeders within the city path, if your simulation/analysis jobs run relatively stable, this way can help avoid 
the repeated job generation work on regions, substations, or feeders.
For test or debug purpose,it's good to specify ``--hierarchy=feeder`` for generating config file with one job, 
or ``--hierarchy=substation`` with a few jobs.


This command will generate two JADE config files:

    * ``create-pv-jobs.json`` contains jobs for PV deployments.
    * ``create-config-jobs.json`` contains jobs for PV configs

And, you can submit the jobs via ``jade submit-jobs <config_file>`` command. 

.. warning::

    Since PV configs are based on the result of PV deployments, so you will need to wait PV deployment
    jobs to complete, before to submit PV config jobs.


PV Deployments
--------------

Submit Jobs
^^^^^^^^^^^

To generate PV deployments, you will need to submit the jobs via JADE, that is,

.. code-block:: bash

    $ jade submit-jobs <OPTIONS> create-pv-jobs.json

If the jobs pass, then the PV deployments task is done. If you'd like to explore details 
about ``create-pv`` action based on your hierarchy and according input path, please check the section below.

Details Exploration
^^^^^^^^^^^^^^^^^^^

Here are some example commands showing how to create, check and remove PV deployments.

1. Create PV deployments on feeder1 with ``--placement random``.

.. code-block:: bash

    $ disco pv-deployments source-tree-1 -a create-pv -h feeder -p random --pv-upscale <feeder1_path>


2. Create PV deployments on substation1 with  a few feeders.

.. code-block:: bash

    $ disco pv-deployments source-tree-1 -a create-pv -h substation -p random --pv-upscale <substation1_path>


3. Create PV deployments on region1 with many feeders in parallel by using JADE.

As each region has a large number of feeders, it is recommended to use JADE to parallize the jobs.

.. code-block:: bash

    $ disco pv-deployments source-tree-1 -a list-feeders -h region <region1_path>
    # Create a <commands.txt> file which contains create-pv commands on feeders as above.
    $ jade config create <commands.txt> -c config1.json
    $ jade submit-jobs config1.json


4. If you like to check which PV deployments are missing due to job failures,

.. code-block:: bash

    $ disco pv-deployments source-tree-1 -a check-pv -h feeder -p random <feeder1_path>
    $ disco pv-deployments source-tree-1 -a check-pv -h substation  -p random <substation1_path>
    $ disco pv-deployments source-tree-1 -a check-pv -h region  -p random <region1_path>

It returns the missing samples and penetrations on each feeder. If don't have ``--placement`` specified,
the result would include `placement` missing information on each feeder.


5. If you found some issues with the PV deployments, and like to delete them, here are example commands,

.. code-block:: bash

    $ disco pv-deployments source-tree-1 -a remove-pv -h feeder  -p random <feeder1_path>
    $ disco pv-deployments source-tree-1 -a remove-pv -h substation  -p random <substation1_path>
    $ disco pv-deployments source-tree-1 -a remove-pv -h region  -p random <region1_path>


PV Configs
----------

Submit Jobs
^^^^^^^^^^^

To generate PV configs, you will need to submit the jobs via JADE, that is,

.. code-block:: bash

    $ jade submit-jobs <OPTIONS> create-config-jobs.json

If the jobs pass, then the PV configs task is done. If you'd like to explore details 
about ``create-configs`` action based on your hierarchy and according input path, please check the section below.

Details Exploration
^^^^^^^^^^^^^^^^^^^

After PV deployments creaated, PV config files need to be generated as well for assigning each 
PV system in deployments a PV profile, where the PV config files are created in `sample` directories.
The examples below show commands for creating, checking or removing PV config files.

1. Create PV configs on feeder1 based on PV deployments data.

.. code-block:: bash

    $ disco pv-deployments source-tree-1 -a create-configs -h feeder <feeder1_path>


2. Create PV configs on substation1 with a few feeders.

.. code-block:: bash

    $ disco pv-deployments source-tree-1 -a create-configs -h substation <substation1_path>

.. warning::

    The option ``-p`` or ``--placement`` does not apply to ``create-configs`` action, as after all 
    pv configs created in each feeder, a sum group file based on customer types would be created
    based on the pv configs of the feeder.

3. Create PV configs on region1 with many feeders in parallel by using JADE.

.. code-block:: bash

    $ disco pv-deployments source-tree-1 -a list-feeders -h region <region1_path>
    # Create a <commands.txt> file which contains create-configs commands on feeders as above.
    $ jade config create <commands.txt> -c config2.json
    $ jade submit-jobs config2.json

4. Check if there is PV config files missing on feeders.

.. code-block:: bash

    $ disco pv-deployments source-tree-1 -a check-configs -h feeder -p random <feeder1_path>
    $ disco pv-deployments source-tree-1 -a check-configs -h substation -p random <substation1_path>
    $ disco pv-deployments source-tree-1 -a check-configs -h region -p random <region1_path>

5. Remove PV configs if there were something wrong.

.. code-block:: bash

    $ disco pv-deployments source-tree-1 -a remove-configs -h feeder -p random <feeder1_path>
    $ disco pv-deployments source-tree-1 -a remove-configs -h substation -p random <substation1_path>
    $ disco pv-deployments source-tree-1 -a remove-configs -h region -p random <region1_path>


Restore Feeders
---------------

As the ``Loads.dss`` in SourceTree1 models needs to be transformed during PV deployments, and the 
content of ``Loads.dss`` was modified. However, we backed up the original ``Loads.dss`` before 
PV deployments, so we can rename back after that. Simply, the steps look like this.

One more thing, to speed up PV deployments, we commented out ``LoadShapes.dss`` before PV deployments in master
files, we need to revert it back after PV deployments.

1. Before PV deployments:

* Rename raw ``Loads.dss`` into ``Original_Loads.dss``.

2. During PV deployments:

* DISCO PV deployment program transformed ``Loads.dss`` in place.
* and, stripped ``yearly=<pv-profile>`` from the load lines.

3. After PV deployments:

* Rename transformed ``Loads.dss`` file into ``PV_Loads.dss``.
* Rename ``Original_Loads.dss`` back to ``Loads.dss``.

Run the command below to rename ``Loads.dss`` file and related,

.. code-block:: bash

    $ disco pv-deployments source-tree-1 -a restore-feeders -h <hierarchy> INPUT_PATH
