**********
Build docs
**********

To build docs locally, use command below:

.. code-block::

    $ cd docs

    # Rebuild the API pages on first build or if code has changed.
    $ rm -rf source/disco
    $ sphinx-apidoc -o source/disco ../disco

    $ make html


To publish the updated docs on Github pages, use this command,

.. code-block:: bash

    $ cd docs
    $ make github
