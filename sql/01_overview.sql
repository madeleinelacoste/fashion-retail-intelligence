-- ============================================================================
-- 01  Dataset overview and business KPIs
-- Each "-- name:" line starts a query the notebooks load by name.
-- Run the whole file in the DuckDB CLI with:  duckdb data/hm.duckdb < sql/01_overview.sql
-- ============================================================================


-- name: dataset_overview
SELECT
    (SELECT count(*) FROM transactions)                 AS units_sold,
    (SELECT count(*) FROM customer_visits)              AS baskets,
    (SELECT count(*) FROM customer_summary)             AS purchasing_customers,
    (SELECT count(*) FROM customers)                    AS registered_customers,
    (SELECT count(*) FROM article_summary)              AS articles_sold,
    (SELECT count(*) FROM articles)                     AS articles_in_catalog,
    (SELECT min(t_dat) FROM transactions)               AS first_date,
    (SELECT max(t_dat) FROM transactions)               AS last_date;


-- name: monthly_kpis
WITH bounds AS (
    SELECT min(t_dat) AS first_date, max(t_dat) AS last_date FROM customer_visits
),
monthly AS (
    SELECT
        date_trunc('month', t_dat)::DATE                AS month_start,
        sum(units)                                      AS units,
        sum(spend)                                      AS revenue,
        count(DISTINCT customer_id)                     AS active_customers,
        count(*)                                        AS baskets,
        avg(units)                                      AS units_per_basket,
        avg(spend)                                      AS spend_per_basket,
        sum(online_units)::DOUBLE / sum(units)          AS online_unit_share
    FROM customer_visits
    GROUP BY 1
)
SELECT
    m.*,
    m.month_start >= b.first_date AND last_day(m.month_start) <= b.last_date AS is_complete_month
FROM monthly m
CROSS JOIN bounds b
ORDER BY m.month_start;


-- name: channel_split
SELECT
    channel,
    count(*)                                            AS units,
    sum(price)                                          AS revenue,
    count(*)::DOUBLE / sum(count(*)) OVER ()            AS unit_share,
    sum(price) / sum(sum(price)) OVER ()                AS revenue_share,
    avg(price) / (SELECT avg(price) FROM transactions)  AS price_index
FROM transactions
GROUP BY channel
ORDER BY units DESC;


-- name: data_quality_checks
SELECT 'Customers with no recorded age' AS check_name,
       count(*) FILTER (WHERE age IS NULL)::DOUBLE / count(*) AS value
FROM customers
UNION ALL
SELECT 'Registered customers with no purchases',
       1 - (SELECT count(*) FROM customer_summary)::DOUBLE / count(*)
FROM customers
UNION ALL
SELECT 'Catalog articles never sold',
       1 - (SELECT count(*) FROM article_summary)::DOUBLE / count(*)
FROM articles
UNION ALL
SELECT 'Units in non-category garment groups (Special Offers, Unknown)',
       count(*) FILTER (WHERE NOT is_product_category(garment_group_name))::DOUBLE / count(*)
FROM sales
UNION ALL
SELECT 'Transactions with no matching article',
       count(*) FILTER (WHERE a.article_id IS NULL)::DOUBLE / count(*)
FROM transactions t
LEFT JOIN articles a ON a.article_id = t.article_id;
