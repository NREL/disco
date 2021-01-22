Hosting Capacity Analysis
=========================

In previous section, we learned how to transform model with *snapshot impact 
analysis* by using this command,

.. code-block:: bash

    $ disco transform-model ~/disco/tests/data/smart-ds/substations snapshot-impact-analysis

It generates a directory named ``snapshot-impact-analysis-models`` with transformed models.
This tutorial assumes you also output the transformed models into ``snapshot-impact-analysis-models``,
with the models, we can run *hosting capacity analysis* based on *snapshot impact analysis*.

To simplify the full run of *hosting capacity analysis* and *snapshot impact analysis*, we have
created a `pipeline <https://nrel.github.io/jade/pipeline.html>`_
that will run all of these steps:

.. code-block:: bash

    $ jade pipeline create \
      "disco config snapshot-impact-analysis snapshot-impact-analysis-models -c config-stage1.json" \
      "~/disco/disco/extensions/pydss_simulation/create_merge_feeders_results.py"

The command above generates a pipeline configuration file ``pipeline.toml``, 
which contains two commands for configuring two stages. In stage 1, it will generate
a snapshot impact analysis config ``config-stage1.json``, and run it. 
In following stage 2, it will generate a second JADE config to merge the impact 
analysis results into per-feeder CSVs, and then run that.

.. note::

    Here, we assume the DISCO repo was cloned to ``~/disco`` directory. Another,
    the config file ouput from stage 1 need to be ``config-stage1.json``.

This command will execute the pipeline:

.. code-block:: bash

    $ jade pipeline submit pipeline.toml

.. note::

    Refer to the JADE documentation to optimize execution on the HPC.

The final feeder-specific output csvs will show up in ``./output/output-stage2/job-outputs``.

.. code-block:: bash

    $ cat output/output-stage2/job-outputs/feeder_1-snapshot-impact-analysis-batch-post-process.csv
    feeder,deployment,placement,sample,penetration,peak_load,pv_kw,pv_pmpp,pv_to_load_ratio,min_voltage,max_voltage,undervoltage_A_flag,overvoltage_A_flag,undervoltage_A_count,overvoltage_A_count,undervoltage_B_flag,overvoltage_B_flag,undervoltage_B_count,overvoltage_B_count,max_flicker,flicker_flag,flicker_count,max_line,1X_line_overloading_flag,1X_line_overloading_count,1p5X_line_overloading_flag,1p5X_line_overloading_count,max_xfmr_loading,1X_xfmr_overloading_flag,1X_xfmr_overloading_count,1p5X_xfmr_overloading_flag,1p5X_xfmr_overloading_count,100L100TA_fail_flag,100L100TA_pass_flag,100L150TA_fail_flag,100L150TA_pass_flag,150L100TA_fail_flag,150L100TA_pass_flag,150L150TA_fail_flag,150L150TA_pass_flag,100L100TB_fail_flag,100L100TB_pass_flag,100L150TB_fail_flag,100L150TB_pass_flag,150L100TB_fail_flag,150L100TB_pass_flag,150L150TB_fail_flag,150L150TB_pass_flag,name
    feeder_1,deployment0,,,0.0,2115.474432865047,123.69600000000001,123.696,5.85,0.9578933469865691,1.018676511690172,False,False,0,0,False,False,0,0,,,,1.670472047303335,True,1,True,1,8.927325959426224,True,12,True,12,True,False,True,False,True,False,True,False,True,False,True,False,True,False,True,False,feeder_1__-1__None__None__deployment0.dss
    ...
