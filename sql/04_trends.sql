-- ============================================================================
-- 04  Trends and demand: seasonality, year-over-year shifts in category and
--     colour mix, rising product types, and the weekly series used for forecasting.
-- Y1 and Y2 are back-to-back 52-week years (see scripts/build_database.py).
-- Y2 includes spring 2020, when COVID-19 closed stores and sales shifted online.
-- ============================================================================


-- name: weekly_units_by_index_group
SELECT week_start, index_group_name, sum(units) AS units, sum(revenue) AS revenue
FROM weekly_sales
GROUP BY week_start, index_group_name
ORDER BY week_start, index_group_name;


-- name: weekly_online_share
SELECT
    week_start,
    sum(units)                                                          AS units,
    sum(units) FILTER (WHERE channel = 'Online')::DOUBLE / sum(units)   AS online_unit_share
FROM weekly_sales
GROUP BY week_start
ORDER BY week_start;


-- name: monthly_seasonality_by_garment_group
-- Uses Y1 only (before COVID). Index = average weekly units that month divided by
-- the group's average across all months, so 1.3 means 30% above a normal month.
WITH weeks AS (
    SELECT month(week_start) AS month_no, count(DISTINCT week_start) AS n_weeks
    FROM weekly_sales
    WHERE analysis_year = 'Y1'
    GROUP BY 1
),
monthly AS (
    SELECT garment_group_name, month(week_start) AS month_no, sum(units) AS units
    FROM weekly_sales
    WHERE analysis_year = 'Y1' AND is_product_category(garment_group_name)
    GROUP BY 1, 2
),
weekly_rate AS (
    SELECT m.garment_group_name, m.month_no, m.units::DOUBLE / w.n_weeks AS avg_weekly_units
    FROM monthly m
    JOIN weeks w USING (month_no)
)
SELECT
    garment_group_name,
    month_no,
    avg_weekly_units,
    avg_weekly_units / avg(avg_weekly_units) OVER (PARTITION BY garment_group_name) AS seasonality_index
FROM weekly_rate
ORDER BY garment_group_name, month_no;


-- name: garment_group_yoy
-- Shares are of product-category revenue ("Special Offers" and "Unknown" left out)
WITH totals AS (
    SELECT
        garment_group_name,
        sum(revenue) FILTER (WHERE analysis_year = 'Y1')    AS revenue_y1,
        sum(revenue) FILTER (WHERE analysis_year = 'Y2')    AS revenue_y2
    FROM weekly_sales
    WHERE is_product_category(garment_group_name)
    GROUP BY garment_group_name
)
SELECT
    garment_group_name,
    revenue_y1,
    revenue_y2,
    revenue_y2 / revenue_y1 - 1                             AS revenue_growth,
    revenue_y1 / sum(revenue_y1) OVER ()                    AS share_y1,
    revenue_y2 / sum(revenue_y2) OVER ()                    AS share_y2,
    revenue_y2 / sum(revenue_y2) OVER ()
        - revenue_y1 / sum(revenue_y1) OVER ()              AS share_change
FROM totals
ORDER BY share_change DESC;


-- name: colour_share_yoy
WITH totals AS (
    SELECT
        perceived_colour_master_name,
        sum(units) FILTER (WHERE analysis_year = 'Y1')      AS units_y1,
        sum(units) FILTER (WHERE analysis_year = 'Y2')      AS units_y2
    FROM weekly_sales
    GROUP BY perceived_colour_master_name
)
SELECT
    perceived_colour_master_name,
    units_y1,
    units_y2,
    units_y1::DOUBLE / sum(units_y1) OVER ()                AS share_y1,
    units_y2::DOUBLE / sum(units_y2) OVER ()                AS share_y2,
    units_y2::DOUBLE / sum(units_y2) OVER ()
        - units_y1::DOUBLE / sum(units_y1) OVER ()          AS share_change
FROM totals
ORDER BY share_change DESC;


-- name: product_type_momentum
-- Share of units in the latest 12 weeks versus the same 12 weeks a year earlier.
-- Comparing shares rather than raw units removes overall market swings.
WITH bounds AS (
    SELECT max(week_start) AS last_week FROM weekly_sales
),
periods AS (
    SELECT
        w.product_type_name,
        any_value(w.product_group_name)                                         AS product_group_name,
        coalesce(sum(w.units) FILTER (WHERE w.week_start > b.last_week - INTERVAL 84 DAY), 0)  AS units_recent,
        coalesce(sum(w.units) FILTER (WHERE w.week_start > b.last_week - INTERVAL 448 DAY
                                        AND w.week_start <= b.last_week - INTERVAL 364 DAY), 0) AS units_prior_year
    FROM weekly_sales w
    CROSS JOIN bounds b
    GROUP BY w.product_type_name
),
shares AS (
    SELECT
        *,
        units_recent::DOUBLE / sum(units_recent) OVER ()            AS share_recent,
        units_prior_year::DOUBLE / sum(units_prior_year) OVER ()    AS share_prior_year
    FROM periods
)
SELECT
    product_type_name,
    product_group_name,
    units_recent,
    units_prior_year,
    share_recent,
    share_prior_year,
    share_recent - share_prior_year                                 AS share_change
FROM shares
WHERE share_recent >= 0.002 OR share_prior_year >= 0.002
ORDER BY share_change DESC;


-- name: weekly_units_by_product_group
-- Input for the forecasting section
SELECT week_start, product_group_name, sum(units) AS units
FROM weekly_sales
GROUP BY week_start, product_group_name
ORDER BY product_group_name, week_start;
