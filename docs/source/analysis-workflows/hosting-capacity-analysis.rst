Hosting Capacity Analysis
=========================

This tutorial assumes there is a ``snapshot-impact-analysis-models`` folder in 
the current working directory, and that DISCO was cloned to ``~/disco``.

Full Snapshot Impact and Hosting Capacity Analysis
--------------------------------------------------

To simplify the full run of ``SnapshotImpactAnalysis`` and ``HostingCapacityAnalysis``, we have
created a `pipeline <https://nrel.github.io/jade/pipeline.html>`_
that will run all of these steps at once:

.. code-block:: bash

    $ jade pipeline create ~/disco/disco/extensions/pydss_simulation/create_pydss_simulation_config.py \
        ~/disco/disco/extensions/pydss_simulation/create_merge_feeders_results.py
    # Optional - to pass overrides to `SnapshotImpactAnalysis`:
    # $ jade pipeline create \
    #     "~/disco/disco/extensions/pydss_simulation/create_pydss_simulation_config.py over_voltage=1.5" \
    #     ~/disco/disco/extensions/pydss_simulation/create_merge_feeders_results.py

This will generate ``pipeline.toml``, which will generate a ``SnapshotImpactAnalysis`` config,
run it, generate a second JADE config to merge the impact analysis results into per-feeder CSVs,
and then run that.

So, running:

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
