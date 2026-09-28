-- ============================================================================
-- 00  Summary tables
-- Run automatically by scripts/build_database.py after the raw data is loaded.
-- Everything in sql/01-05 reads from these tables plus the three base tables:
--   articles, customers, transactions
-- Each transaction row is one unit sold. Prices in the H&M data are scaled,
-- so "revenue" below means scaled sales value and is compared as shares or indexes.
-- ============================================================================


-- "Special Offers" and "Unknown" are garment_group_name values that are not product
-- categories (a promotion bucket and a missing label). Analyses that compare garment
-- groups as categories filter them out with this macro; totals still include them.
CREATE OR REPLACE MACRO is_product_category(garment_group) AS
    garment_group NOT IN ('Special Offers', 'Unknown');


-- Transactions joined to product attributes (a view, so nothing is duplicated)
CREATE OR REPLACE VIEW sales AS
SELECT
    t.*,
    a.product_type_name,
    a.product_group_name,
    a.garment_group_name,
    a.index_group_name,
    a.index_name,
    a.department_name,
    a.section_name,
    a.colour_group_name,
    a.perceived_colour_master_name
FROM transactions t
JOIN articles a USING (article_id);


-- One row per article: volume, pricing and lifecycle.
-- ref_price is the article's 90th-percentile selling price, used as its "full price".
-- A unit counts as marked down when it sold at least 15% below that.
CREATE OR REPLACE TABLE article_summary AS
WITH ref AS (
    SELECT article_id, quantile_cont(price, 0.9) AS ref_price
    FROM transactions
    GROUP BY article_id
)
SELECT
    t.article_id,
    min(t.t_dat) AS first_sale,
    max(t.t_dat) AS last_sale,
    count(*) AS units,
    sum(t.price) AS revenue,
    avg(t.price) AS avg_price,
    any_value(r.ref_price) AS ref_price,
    sum(CASE WHEN t.price < 0.85 * r.ref_price THEN 1 ELSE 0 END) AS markdown_units,
    count(DISTINCT t.customer_id) AS customers,
    date_diff('week', min(t.t_dat), max(t.t_dat)) + 1 AS active_weeks
FROM transactions t
JOIN ref r USING (article_id)
GROUP BY t.article_id;


-- One row per basket (a customer's purchases on one day)
CREATE OR REPLACE TABLE customer_visits AS
SELECT
    customer_id,
    t_dat,
    count(*) AS units,
    sum(price) AS spend,
    sum(CASE WHEN channel = 'Online' THEN 1 ELSE 0 END) AS online_units
FROM transactions
GROUP BY customer_id, t_dat;


-- One row per purchasing customer
CREATE OR REPLACE TABLE customer_summary AS
WITH numbered AS (
    SELECT *, row_number() OVER (PARTITION BY customer_id ORDER BY t_dat) AS visit_no
    FROM customer_visits
)
SELECT
    n.customer_id,
    min(n.t_dat) AS first_purchase,
    max(n.t_dat) AS last_purchase,
    min(n.t_dat) FILTER (WHERE n.visit_no = 2) AS second_purchase,
    count(*) AS visits,
    sum(n.units) AS units,
    sum(n.spend) AS spend,
    sum(n.online_units)::DOUBLE / sum(n.units) AS online_share,
    any_value(c.age) AS age,
    coalesce(any_value(c.age_band), 'Unknown') AS age_band,
    coalesce(any_value(c.club_member_status), 'UNKNOWN') AS club_member_status,
    coalesce(any_value(c.fashion_news_frequency), 'None') AS fashion_news_frequency
FROM numbered n
LEFT JOIN customers c USING (customer_id)
GROUP BY n.customer_id;


-- RFM segmentation
--   Recency  = days since last purchase (scored in quintiles, 5 = most recent)
--   Frequency = number of shopping days (fixed bins, because most customers tie at 1 or 2)
--   Monetary = total spend (quintiles)
CREATE OR REPLACE TABLE customer_rfm AS
WITH base AS (
    SELECT
        customer_id,
        visits,
        spend,
        date_diff('day', last_purchase, (SELECT max(t_dat) FROM transactions)) AS recency_days
    FROM customer_summary
),
scored AS (
    SELECT
        *,
        ntile(5) OVER (ORDER BY recency_days DESC) AS r_score,
        CASE
            WHEN visits = 1 THEN 1
            WHEN visits = 2 THEN 2
            WHEN visits <= 4 THEN 3
            WHEN visits <= 9 THEN 4
            ELSE 5
        END AS f_score,
        ntile(5) OVER (ORDER BY spend) AS m_score
    FROM base
)
SELECT
    *,
    CASE
        WHEN r_score >= 4 AND f_score >= 4 THEN 'Champions'
        WHEN r_score >= 3 AND f_score >= 3 THEN 'Loyal'
        WHEN r_score >= 4 THEN 'New / Recent'
        WHEN r_score <= 2 AND f_score >= 3 THEN 'At Risk'
        WHEN r_score <= 2 AND m_score >= 4 THEN 'Lapsed High Spenders'
        WHEN r_score <= 2 THEN 'Lapsed'
        ELSE 'Occasional'
    END AS segment
FROM scored;


-- Weekly sales cube for trend work (complete Monday-Sunday weeks only)
CREATE OR REPLACE TABLE weekly_sales AS
SELECT
    week_start,
    analysis_year,
    index_group_name,
    garment_group_name,
    product_group_name,
    product_type_name,
    perceived_colour_master_name,
    channel,
    count(*) AS units,
    sum(price) AS revenue
FROM sales
WHERE in_full_week
GROUP BY ALL;


-- Which garment groups are bought together in the same basket
-- (product categories only; total_baskets still counts every basket)
CREATE OR REPLACE TABLE category_pairs AS
WITH basket_groups AS (
    SELECT DISTINCT customer_id, t_dat, garment_group_name AS grp
    FROM sales
    WHERE is_product_category(garment_group_name)
),
total AS (
    SELECT count(*) AS n FROM customer_visits
),
support AS (
    SELECT grp, count(*) AS baskets FROM basket_groups GROUP BY grp
),
pairs AS (
    SELECT x.grp AS group_a, y.grp AS group_b, count(*) AS baskets_both
    FROM basket_groups x
    JOIN basket_groups y
      ON x.customer_id = y.customer_id AND x.t_dat = y.t_dat AND x.grp < y.grp
    GROUP BY 1, 2
)
SELECT
    p.group_a,
    p.group_b,
    p.baskets_both,
    sa.baskets AS baskets_a,
    sb.baskets AS baskets_b,
    total.n AS total_baskets,
    p.baskets_both::DOUBLE / total.n AS support,
    p.baskets_both::DOUBLE / sa.baskets AS pct_of_a_baskets_with_b,
    p.baskets_both::DOUBLE / sb.baskets AS pct_of_b_baskets_with_a,
    p.baskets_both::DOUBLE * total.n / (sa.baskets::DOUBLE * sb.baskets) AS lift
FROM pairs p
JOIN support sa ON sa.grp = p.group_a
JOIN support sb ON sb.grp = p.group_b
CROSS JOIN total;
