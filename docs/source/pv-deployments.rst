**************
PV Deployments
**************

This section shows how to generate DISCO PV deployments from raw opendss models.

.. _SourceTree1PVDeployments:

SourceTree1 PV Deployments
==========================

The main command going to be used is the one below,

.. code-block:: bash

    $ disco pv-deployments source-tree-1 --action <action-name> --hierarchy <storage hierarchy> --placement <placement type> INPUT_PATH

There are several actions here related to PV deployments manipulation, including

* ``create-pv``: create PV deployments on feeders based on `placement`, `sample` and `penetration` levels.
* ``check-pv``: check if there are PV deployments missing at each `placement`, `sample` and `penetration` level.
* ``remove-pv``: delete PV deployments in case there's something wrong.
* ``create-configs``: create PV config files at each `sample` deployment level.
* ``check-configs``: check if there are PV config files missing in deployment directories.
* ``remove-configs``: remove PV config files in case there's something wrong.
* ``list-feeders``: list feeder paths given input of region, substation or feeder.


PV Deployments
--------------

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

After PV deployments creaated, PV config files need to be generated as well for assigning each 
PV system in deployments a PV profile, where the PV config files are created in `sample` directories.
The examples below show commands for creating, checking or removing PV config files.

1. Create PV configs on feeder1 based on PV deployments data.

.. code-block:: bash

    $ disco pv-deployments source-tree-1 -a create-configs -h feeder -p random <feeder1_path>


2. Create PV configs on substation1 with a few feeders.

.. code-block:: bash

    $ disco pv-deployments source-tree-1 -a create-configs -h substation -p random <substation1_path>


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
