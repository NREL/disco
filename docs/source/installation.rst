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

1. Clone JADE from Github, and create a Conda virtual environment (https://nrel.github.io/jade/installation.html).

.. code-block:: bash

    $ git clone git@github.com:NREL/jade.git
    $ cd jade
    $ conda env create -f environment.yml -n <env-name>

Then activate the Python environment, and install JADE,

.. code-block:: bash

    $ conda activate <env-name>
    $ pip install -e .

2. Clone PyDSS repo from Github and install.

.. code-block:: bash

    $ cd ..
    $ git clone git@github.com:NREL/PyDSS.git
    $ cd PyDSS
    $ pip install -e .

3. Clone DISCO repo from Github and install.

.. code-block:: bash

    $ cd ..
    $ git clone git@github.com:NREL/disco.git
    $ cd disco
    $ pip install -e .

    # If you will also be developing DISCO code then include dev packages.
    $ pip install -e . -r dev-requirements.txt

4. Register the JADE extensions implemented in DISCO, and add logger.

.. code-block:: bash

    $ jade extensions register disco/disco/extensions/jade_extensions.json
    $ jade extensions add-logger disco

Now, the Conda environment ``<env-name>`` is ready to use.
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
