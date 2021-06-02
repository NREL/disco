****************
Debugging Issues
****************

This section describes debugging techniques for issues encountered during the
simulation and analysis process. All of these tools produce output data in both
unstructured (.log) and structured form (.csv, .json, etc.).  Aggregating data
from a batch with thousands of jobs will often require use of UNIX tools (find,
grep, awk, etc.) along with bash or Python scripts to process data in stages.

It is highly recommended that you become proficient at working in a UNIX
environment with these tools. The internet has plenty of resources to help.
Here is one such `site
<https://www.tutorialspoint.com/unix/unix-pipes-filters.htm>`_.

Using JADE
==========

Please refer to JADE documentation -
https://nrel.github.io/jade/tutorial.html#debugging

Note that if you need result status in structured form, such as if you want to
find all failed jobs, refer to ``<output-dir>/results.json``.

Using PyDSS
===========

DISCO creates a PyDSS project directory for each simulation job. The directory
will have the following contents:

* ``project.zip``
* ``store.h5``

When running on an HPC the directory contents will always be zipped because
huge numbers of directories can be problematic for the shared filesystem.

Here is example content of an extracted job:

.. code-block:: bash

  $ find output/job-outputs/p1uhs9_1247__p1udt6854__random__9__100/pydss-project

  output/job-outputs/p1uhs9_1247__p1udt6854__random__9__100/pydss-project
  output/job-outputs/p1uhs9_1247__p1udt6854__random__9__100/pydss-project/DSSfiles
  output/job-outputs/p1uhs9_1247__p1udt6854__random__9__100/pydss-project/DSSfiles/deployment.dss
  output/job-outputs/p1uhs9_1247__p1udt6854__random__9__100/pydss-project/Exports
  output/job-outputs/p1uhs9_1247__p1udt6854__random__9__100/pydss-project/Exports/control_mode
  output/job-outputs/p1uhs9_1247__p1udt6854__random__9__100/pydss-project/Logs
  output/job-outputs/p1uhs9_1247__p1udt6854__random__9__100/pydss-project/Logs/pydss.log
  output/job-outputs/p1uhs9_1247__p1udt6854__random__9__100/pydss-project/Logs/pydss_project__control_mode__reports.log
  output/job-outputs/p1uhs9_1247__p1udt6854__random__9__100/pydss-project/Scenarios
  output/job-outputs/p1uhs9_1247__p1udt6854__random__9__100/pydss-project/Scenarios/control_mode
  output/job-outputs/p1uhs9_1247__p1udt6854__random__9__100/pydss-project/Scenarios/control_mode/ExportLists/Exports.toml
  output/job-outputs/p1uhs9_1247__p1udt6854__random__9__100/pydss-project/Scenarios/control_mode/pyControllerList/PvControllers.toml

To debug a problem you can unzip the contents. However, this can be problematic
if you need to inspect lots of jobs. You may be better off using a tool like
``Vim`` that lets you view compressed files in place.

You can also use ``zipgrep`` to search specific files within the .zip for
patterns. This is extremely helpful if you need to inspect many jobs. This tool
uses ``egrep`` so you may need to consult help from both locations to customize
searches.

Errors
------
All errors get logged in ``pydss.log``. Look there for problems reported by
OpenDSS.

Searching for errors
--------------------
 Here is an example of searching for a pattern without unzipping:

.. code-block:: bash

    $ zipgrep "Convergence error" output/job-outputs/p1uhs9_1247__p1udt6854__random__9__100/pydss_project/project.zip Logs/pydss.log

Here is an example that searches all jobs:

.. code-block:: bash

    $ for x in `find output/job-outputs -name project.zip`; do echo "$x"; zipgrep "Convergence error" $x Logs/pydss.log; done

You will likely want to redirect that command's output to another file for
further processing (or pipe it to another command).

Convergence errors
------------------
PyDSS creates a report showing each instance of a convergence error for a PV
controller.  An example name of this file is
``pydss_project__control_mode__reports.log``. This file contains line-delimited
JSON objects.  This means that each line is valid JSON but the entire file is
not.

Here is an example of one line of the file pretty-printed as JSON:

.. code-block:: json

    {
      "Report": "Convergence",
      "Scenario": "control_mode",
      "Time": 523800,
      "DateTime": "2020-01-07 01:30:00",
      "Controller": "pyCont_PVSystem_small_p1ulv32837_1_2_pv",
      "Controlled element": "PVSystem.small_p1ulv32837_1_2_pv",
      "Error": 0.00241144335086263,
      "Control algorithm": "VVar"
    }

Here are some example commands to convert the file to JSON. This example uses
an excellent 3rd-party JSON-parsing tool called ``jq`` which you have to
install. (On Eagle: ``conda install -c conda-forge jq``). You may have a
different method.

.. code-block:: bash

    $ zipgrep -h Convergence output/job-outputs/p1uhs9_1247__p1udt6854__random__9__100/pydss_project/project.zip Logs/pydss_project__control_mode__reports.log | jq . -s

**Note**: That command used ``-h`` to suppress the filename from the output.

This next command will do do the same for all jobs. Note that it loses the
association between job and error. You would need to do some extra work to keep
those associations.

.. code-block:: bash

    $ for x in `find output/job-outputs -name project.zip`; do zipgrep -h "Convergence" $x Logs/pydss_project__control_mode__reports.log; done | jq . -s

.. warning:: Be aware of how much CPU and memory will be consumed by these
   operations. You may want to redirect this output to a temporary text file
   first.

In both cases you will probably want to redirect the output to a JSON file for
further processing.

Running searches in parallel
----------------------------
The DISCO repository has a script that extracts data from ``project.zip`` with
the Python multiprocessing library. You can use this as an example to speed up
large searches. Do not run this kind of search on the login node.

Refer to ``disco/cli/make_summary_tables.py``.
