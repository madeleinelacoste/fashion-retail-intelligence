-- ============================================================================
-- 05  Dashboard extracts
-- Tables shaped for Tableau Public / Power BI. scripts/export_dashboard_data.py
-- writes these (plus a few queries from files 01-04) to dashboard/data/*.csv.
-- Rows keep every garment group so totals are complete; filter on
-- is_product_category for category comparisons.
-- ============================================================================


-- name: dash_weekly_sales
SELECT
    week_start,
    analysis_year,
    index_group_name,
    garment_group_name,
    is_product_category(garment_group_name)                 AS is_product_category,
    channel,
    sum(units)                                              AS units,
    sum(revenue)                                            AS revenue
FROM weekly_sales
GROUP BY ALL
ORDER BY week_start;


-- name: dash_product_type_scorecard
SELECT
    s.index_group_name,
    s.garment_group_name,
    is_product_category(s.garment_group_name)               AS is_product_category,
    s.product_type_name,
    count(*)                                                AS units,
    sum(s.price)                                            AS revenue,
    count(DISTINCT s.article_id)                            AS articles_sold,
    avg(s.price) / (SELECT avg(price) FROM transactions)    AS price_index,
    avg(CASE WHEN s.price < 0.85 * a.ref_price THEN 1.0 ELSE 0.0 END) AS markdown_unit_share,
    avg(CASE WHEN s.channel = 'Online' THEN 1.0 ELSE 0.0 END)         AS online_unit_share
FROM sales s
JOIN article_summary a USING (article_id)
GROUP BY ALL
ORDER BY revenue DESC;


-- name: dash_customer_segments
SELECT
    r.segment,
    c.age_band,
    CASE
        WHEN c.online_share = 0 THEN 'Store only'
        WHEN c.online_share = 1 THEN 'Online only'
        ELSE 'Both channels'
    END                                                     AS shopper_type,
    c.club_member_status,
    count(*)                                                AS customers,
    sum(c.spend)                                            AS revenue,
    sum(c.visits)                                           AS shopping_days,
    avg(r.recency_days)                                     AS avg_recency_days
FROM customer_rfm r
JOIN customer_summary c USING (customer_id)
GROUP BY ALL;
