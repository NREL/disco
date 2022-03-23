-- Create a job table with results FROM specific tasks.
DROP VIEW IF EXISTS jt_all;
CREATE TEMP VIEW jt_all AS
	SELECT
        tm.name
        ,tm.substation
        ,tm.feeder
        ,tm.scenario
        ,tm.placement
        ,tm.sample
        ,tm.penetration_level
        ,tm.line_max_instantaneous_loading_pct
        ,tm.line_max_moving_average_loading_pct
        ,tm.line_num_time_points_with_instantaneous_violations
        ,tm.line_num_time_points_with_moving_average_violations
        ,tm.transformer_max_instantaneous_loading_pct
        ,tm.transformer_max_moving_average_loading_pct
        ,tm.transformer_num_time_points_with_instantaneous_violations
        ,tm.transformer_num_time_points_with_moving_average_violations
        ,vm.min_voltage
        ,vm.max_voltage
        ,vm.num_nodes_any_outside_ansi_b
        ,vm.num_time_points_with_ansi_b_violations
        ,vm.node_type
        ,pv_distances.weighted_average_pv_distance AS pv_distance
		FROM task
		JOIN job ON job.task_id = task.id
		JOIN thermal_metrics AS tm ON tm.job_id = job.id
		JOIN voltage_metrics AS vm ON vm.job_id = job.id
		JOIN pv_distances ON job.name = pv_distances.job_name
		WHERE
            tm.scenario = 'control_mode'
            AND task.name LIKE '%Time Series'
    ;

-- Create a table of feeders that experienced violations in the base case.
DROP VIEW IF EXISTS bad_feeders;
CREATE TEMP VIEW bad_feeders AS
    SELECT
        feeder
        ,line_max_instantaneous_loading_pct
        ,line_max_moving_average_loading_pct
        ,line_num_time_points_with_instantaneous_violations
        ,line_num_time_points_with_moving_average_violations
        ,transformer_max_instantaneous_loading_pct
        ,transformer_max_moving_average_loading_pct
        ,transformer_num_time_points_with_instantaneous_violations
        ,transformer_num_time_points_with_moving_average_violations
        ,min_voltage
        ,max_voltage
        ,num_nodes_any_outside_ansi_b
        ,num_time_points_with_ansi_b_violations
        FROM jt_all
        WHERE
        sample is NULL
        AND
        (
            (
                line_max_instantaneous_loading_pct >= 150
                OR line_max_moving_average_loading_pct >= 120
                OR line_num_time_points_with_instantaneous_violations >= 350
                OR line_num_time_points_with_moving_average_violations >= 350
                OR transformer_max_instantaneous_loading_pct >= 150
                OR transformer_max_moving_average_loading_pct >= 120
                OR transformer_num_time_points_with_instantaneous_violations >= 350
                OR transformer_num_time_points_with_moving_average_violations >= 350
            )
            OR
            (
                min_voltage <= 0.95
                OR max_voltage >= 1.05
                OR num_nodes_any_outside_ansi_b >= 350
                OR num_time_points_with_ansi_b_violations >= 350
                AND
                (
                    node_type != 'secondaries'
                )
            )
        )
        GROUP BY feeder
        ORDER BY feeder;

DROP VIEW IF EXISTS bad_feeders_pct_threshold;
CREATE TEMP VIEW bad_feeders_pct_threshold AS
    SELECT
        feeder
        ,line_max_instantaneous_loading_pct / 150 AS line_max_instantaneous_loading_pct_pct
        ,line_max_moving_average_loading_pct / 120 AS line_max_moving_average_loading_pct_pct
        ,line_num_time_points_with_instantaneous_violations / 350 AS line_num_time_points_with_instantaneous_violations_pct
        ,line_num_time_points_with_moving_average_violations / 350 AS line_num_time_points_with_moving_average_violations_pct
        ,transformer_max_instantaneous_loading_pct / 150 AS transformer_max_instantaneous_loading_pct_pct
        ,transformer_max_moving_average_loading_pct / 120 AS transformer_max_moving_average_loading_pct_pct
        ,transformer_num_time_points_with_instantaneous_violations / 350 AS transformer_num_time_points_with_instantaneous_violations_pct
        ,transformer_num_time_points_with_moving_average_violations / 350 AS transformer_num_time_points_with_moving_average_violations_pct
        ,min_voltage
        ,max_voltage
        ,num_nodes_any_outside_ansi_b / 350 AS num_nodes_any_outside_ansi_b_pct
        ,num_time_points_with_ansi_b_violations / 350 AS num_time_points_with_ansi_b_violations_pct
    FROM bad_feeders
    ORDER BY feeder;

DROP VIEW IF EXISTS jt;
CREATE TEMP VIEW jt AS
    SELECT * FROM jt_all WHERE feeder NOT IN (SELECT feeder from bad_feeders);

-- Create a metadata table with results FROM specific tasks.
DROP VIEW IF EXISTS mt;
CREATE TEMP VIEW mt AS
	SELECT mt.*
		FROM task
		JOIN job ON job.task_id = task.id
		JOIN metadata AS mt ON mt.job_id = job.id
		WHERE task.name LIKE '%%Time Series'
            AND feeder NOT IN (SELECT feeder from bad_feeders)
            AND mt.scenario = 'control_mode'
    ;

-- Find the max penetration_level for each feeder.
DROP VIEW IF EXISTS hc_max;
CREATE TEMP VIEW hc_max AS
    SELECT
        feeder
        ,scenario
        ,sample
        ,pv_distance
        ,MAX(max_passing_penetration_level) AS max_hc
    FROM hc_by_sample
    GROUP BY feeder, scenario
    ;

-- Create a table showing hosting capacity by feeder and sample.
DROP VIEW IF EXISTS hc_by_sample;
CREATE TEMP VIEW hc_by_sample AS
    SELECT
        feeder
        ,scenario
        ,sample
        ,pv_distance
        ,MAX(penetration_level) AS max_passing_penetration_level
        FROM jt
        WHERE
            true
            AND
            (
                line_max_instantaneous_loading_pct >= 150
                OR line_max_moving_average_loading_pct >= 120
                OR line_num_time_points_with_instantaneous_violations >= 350
                OR line_num_time_points_with_moving_average_violations >= 350
                OR transformer_max_instantaneous_loading_pct >= 150
                OR transformer_max_moving_average_loading_pct >= 120
                OR transformer_num_time_points_with_instantaneous_violations >= 350
                OR transformer_num_time_points_with_moving_average_violations >= 350
            )
            AND
            (
                min_voltage <= 0.95
                OR max_voltage >= 1.05
                OR num_nodes_any_outside_ansi_b >= 350
                OR num_time_points_with_ansi_b_violations >= 350
            )
        GROUP BY feeder, sample;

-- Same as hc_by_sample but include feeders with no passing samples.
DROP VIEW IF EXISTS hc_by_sample_kw;
CREATE TEMP VIEW hc_by_sample_kw AS
    SELECT 
       mt.feeder
       ,mt.scenario
       ,mt.sample
       ,hc_by_sample.pv_distance
       ,hc_by_sample.max_passing_penetration_level
       ,hc_by_sample.max_passing_penetration_level * mt.load_capacity_kw / 100 AS max_hc_kw
    FROM mt
    JOIN hc_by_sample ON
        mt.feeder = hc_by_sample.feeder
        AND mt.scenario = hc_by_sample.scenario
        AND mt.sample = hc_by_sample.sample
        WHERE
            mt.sample is not NULL
        GROUP BY mt.feeder, mt.scenario, mt.sample
    ORDER BY mt.feeder;

DROP VIEW IF EXISTS hc_per_level1;
CREATE TEMP VIEW hc_per_level1 AS
    SELECT DISTINCT
        feeder
        ,scenario
        ,sample
        ,penetration_level
        FROM jt
        WHERE
            true
            AND
            (
                line_max_instantaneous_loading_pct >= 150
                OR line_max_moving_average_loading_pct >= 120
                OR line_num_time_points_with_instantaneous_violations >= 350
                OR line_num_time_points_with_moving_average_violations >= 350
                OR transformer_max_instantaneous_loading_pct >= 150
                OR transformer_max_moving_average_loading_pct >= 120
                OR transformer_num_time_points_with_instantaneous_violations >= 350
                OR transformer_num_time_points_with_moving_average_violations >= 350
            )
            AND
            (
                min_voltage <= 0.95
                OR max_voltage >= 1.05
                OR num_nodes_any_outside_ansi_b >= 350
                OR num_time_points_with_ansi_b_violations >= 350
            )
        ;

DROP VIEW IF EXISTS hc_per_level2;
CREATE TEMP VIEW hc_per_level2 AS
    SELECT
        feeder
        ,scenario
        ,sample
        ,penetration_level
        ,1 AS tmp_value
    FROM hc_per_level1
    ;

-- Create a table that shows the number of passing samples at each penetration level.
-- TODO: this doesn't show samples with no passing levels
DROP VIEW IF EXISTS hc_pp;
CREATE TEMP VIEW hc_pp AS
    SELECT
        feeder
        ,scenario
        ,penetration_level
        ,SUM(tmp_value) / 10.0 AS passing_probability
    FROM hc_per_level2
    WHERE
        sample IS NOT NULL
    GROUP BY feeder, penetration_level
    ;

-- Create a table showing HC metrics for all feeders with at least one passing penetration level.
DROP VIEW IF EXISTS hc_summary;
CREATE TEMP VIEW hc_summary AS
    SELECT
        sq1.*
        ,sq2.min_penetration_level AS min_hc
        ,hc_max.max_hc
        ,(hc_max.max_hc - sq1.expected_hc) / (sq1.expected_hc - sq2.min_penetration_level)
            AS disparity_index
    FROM
        (
            SELECT
                feeder
                ,scenario
                ,SUM(passing_probability) * 5 AS expected_hc
            FROM hc_pp
            GROUP BY feeder
        ) AS sq1
    LEFT JOIN (
        SELECT
            feeder
            ,scenario
            ,MAX(penetration_level) AS min_penetration_level
            ,passing_probability
        FROM hc_pp
        WHERE passing_probability = 1.0
        GROUP BY feeder
    ) AS sq2
    ON sq1.feeder = sq2.feeder AND sq1.scenario = sq2.scenario
    JOIN hc_max ON sq1.feeder = hc_max.feeder AND sq1.scenario = hc_max.scenario
    ORDER BY sq1.feeder
    ;


-- Join hc_summary with all feeders that passed with their base case.
DROP VIEW IF EXISTS hc_summary2;
CREATE TEMP VIEW hc_summary2 AS
    SELECT
        distinct(mt.feeder)
        ,mt.scenario
        ,CASE WHEN hc_summary.expected_hc IS NULL THEN 0 ELSE hc_summary.expected_hc END AS expected_hc
        ,CASE WHEN hc_summary.min_hc IS NULL THEN 0 ELSE hc_summary.min_hc END AS min_hc
        ,CASE WHEN hc_summary.max_hc IS NULL THEN 0 ELSE hc_summary.max_hc END AS max_hc
        ,hc_summary.disparity_index
    FROM
        mt
    LEFT JOIN hc_summary
        ON mt.feeder = hc_summary.feeder and mt.scenario = hc_summary.scenario
    WHERE
        mt.scenario = 'control_mode'
    ORDER BY mt.feeder
;
