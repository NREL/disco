.. _installation:

************
Installation
************
We recommend that you install DISCO in a virtual environment such as ``Conda``.

Conda Installation
==================

1. Create a Conda virtual environment. This example uses the name ``disco``
   as a convention.

.. code-block:: bash

    $ conda create -n disco python=3.9
    $ conda activate disco
    # Run this command if your git version is lower than 2.19.
    $ conda install git">=2.19"

Optional: Install desired packages.

.. code-block:: bash

    $ conda install ipython

2. Install DISCO from the PyPi repository.

.. code-block:: bash

    $ pip install NREL-disco

**Known Windows installation problem**: DISCO requires PyDSS which requires the
Shapely package. In some cases Shapely will fail to install.
pip will report an error about ``geos_c.dll``. Install it from conda and then
retry.

.. code-block:: bash

    $ conda install shapely

Then retry the DISCO installation command.

3. If you will run your jobs through JADE, install DISCO's extensions.

.. code-block:: bash

    $ disco install-extensions

Now, the Conda environment ``disco`` is ready to use.
To deactivate it, run the command below:

.. code-block:: bash

    $ conda deactivate


Developer Installation
======================
Follow these instructions if you will be developing DISCO code and running tests.

.. code-block:: bash

    $ git clone git@github.com:NREL/disco.git
    $ cd disco
    $ pip install -e '.[dev]'
