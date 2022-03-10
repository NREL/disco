.. _installation:

************
Installation
************

DISCO can be installed on your computer or HPC. If trying to install it on your
computer, you can choose to install it in a conda environment or Docker
container.

Use Conda
=========

This section shows how to create a virtual Python environment by using Conda,
and install necessary packages required by DISCO, including JADE, PyDSS and
third-party libraries.

1. Create a Conda virtual environment. This example uses the name ``disco``
   as a convention.

.. code-block:: bash

    $ conda create -n disco python=3.7
    $ conda activate disco
    # Run this command if your git version is lower than 2.19.
    $ conda install git">=2.19"

.. warning:: Python 3.7 is required. Newer versions won't work.

Optional: Install desired packages.

.. code-block:: bash

    $ conda install ipython

2. Clone DISCO repo from GitHub and install.

.. code-block:: bash

    $ cd <path-to-your-local-repos>
    $ git clone git@github.com:NREL/disco.git
    $ cd disco
    $ pip install -e .

    # If you will also be developing DISCO code then include dev packages.
    $ pip install -e '.[dev]'

Known Windows installation problem: DISCO requires PyDSS which requires the
Shapely package. In some cases Shapely will fail to install.
pip will report an error about ``geos_c.dll``. Install it from conda and then
retry.

.. code-block:: bash

    $ conda install shapely
    $ pip install -e .

Now, the Conda environment ``disco`` is ready to use.
To deactivate it, use commands below:

.. code-block:: bash

    $ conda deactivate


Use Docker
==========

Docker can run on different OS platforms - Linux, Mac, Windows, etc.
Please follow the document https://docs.docker.com/ to install Docker CE
on your machine first. Then, can continue DISCO installation with docker.

1. Clone DISCO source code to your machine.

.. code-block:: bash

    $ git clone git@github.com:NREL/disco.git

2. Clone PyDSS source code to your ``disco`` folder.

.. code-block:: bash

    $ cd disco
    $ git clone git@github.com:NREL/PyDSS.git

3. Build ``disco`` docker image

.. code-block:: bash

    docker build -t disco .

4. Run ``disco`` docker container

.. code-block:: bash

    docker run --rm -it -v absolute-disco-models-path:/data/disco-models disco

After the container starts, the terminal will show something like this

.. code-block:: bash

    (disco) root@d14851e20888:/data#

Then type ``disco`` to show DISCO related commands

.. code-block:: bash

    (disco) root@d14851e20888:/data# disco
    Usage: disco [OPTIONS] COMMAND [ARGS]...

      Entry point

    Options:
      --help  Show this message and exit.

    Commands:
      auto-config-analysis        Automatically create a configuration.
      generate-input-data         Generate input data for a model.

This base image is https://hub.docker.com/r/continuumio/miniconda3, which is
built on top of ``debian``, so you can use Linux commands for operation.

5. To exit docker environment, just type

::

    exit

For more about docker commands, please refer https://docs.docker.com/engine/reference/commandline/docker/.
