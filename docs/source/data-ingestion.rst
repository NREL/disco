**************
Data Ingestion
**************

DISCO can ingest simulation metrics and analysis results into a sqlite database, which
facilitates data sharing between researchers and data query for further investigation.

Ingest to New Database
======================

Suppose we are assigned a task which requires us to run a DISCO pipeline for 
static hosting capacity analysis and the generated pipeline output directory 
is ``/data/snapshot-output/``.

Run the command below to ingest the results into a database.

.. code-block:: bash

    $ disco ingest-tables --task-name "SFO P1U Snapshot" --model-inputs /data/input-models/ --database=test.sqlite /data/snapshot-output/

It will create a database named ``test.sqlite`` with data tables like below,

.. image:: images/db-tables.png


Ingest to Existing Database
===========================

Now we are assigned a second task, and need to run DISCO pipeline for dynamic hosting capacity.
We generated the output directory ``/data/time-series-output``.
Again, we would like to ingest the data into a database.

We have two choices for data ingestion:

1. Ingest the results into a new database, let's say, ``data.sqlite``.
2. Ingest the results into an existing database, for example, the one we created above ``test.sqlite``.

If choose option 1, then just run the command above with new ``--database`` value specified. 
Here, we would like to choose option2, and ingest the results of second task into an existing database,
`test.sqlite` created before. To perform this, we need to assign ``--task-name`` a different value,
otherwise, it would prevent the data ingestion, as the task for each ingestion must be unique.

.. code-block:: bash

    $ disco ingest-tables --task-name "SFO P1U Time-series" --model-inputs /data/input-models/ --database=test.sqlite /data/time-series-output/

.. note::

    Task names must be unique. It's recommended to use a naming convention like this: ``<geography> <simulation_type>``.

Run Database Queries
====================

Create a db connection,

.. code-block:: python

    import sqlite3
    conn = sqlite3.connect("test.sqlite")

Run sql query with ``pandas``,

.. code-block:: python

    import pandas as pd
    query1 = "SELECT * FROM task"
    df = pd.read_sql_query(query1, conn)

For more query examples, please refer to the Jupyter notebook in this repository ``db-query.ipynb``.
