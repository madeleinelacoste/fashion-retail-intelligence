-- ============================================================================
-- 03  Customer behavior: purchase frequency, RFM segments, retention,
--     which entry categories bring customers back, age and channel profiles
-- ============================================================================


-- name: visit_frequency_distribution
SELECT
    CASE
        WHEN visits = 1 THEN '1'
        WHEN visits = 2 THEN '2'
        WHEN visits <= 4 THEN '3-4'
        WHEN visits <= 9 THEN '5-9'
        WHEN visits <= 19 THEN '10-19'
        ELSE '20+'
    END                                                     AS shopping_days,
    min(visits)                                             AS sort_key,
    count(*)                                                AS customers,
    count(*)::DOUBLE / sum(count(*)) OVER ()                AS customer_share,
    sum(spend) / sum(sum(spend)) OVER ()                    AS revenue_share,
    avg(spend)                                              AS avg_spend
FROM customer_summary
GROUP BY 1
ORDER BY sort_key;


-- name: rfm_segment_summary
SELECT
    segment,
    count(*)                                                AS customers,
    count(*)::DOUBLE / sum(count(*)) OVER ()                AS customer_share,
    sum(spend) / sum(sum(spend)) OVER ()                    AS revenue_share,
    avg(recency_days)                                       AS avg_recency_days,
    avg(visits)                                             AS avg_shopping_days,
    avg(spend)                                              AS avg_spend
FROM customer_rfm
GROUP BY segment
ORDER BY revenue_share DESC;


-- name: rfm_segment_profile
SELECT
    r.segment,
    avg(c.age)                                                          AS avg_age,
    avg(c.online_share)                                                 AS avg_online_share,
    avg(CASE WHEN c.club_member_status = 'ACTIVE' THEN 1.0 ELSE 0.0 END) AS active_club_member_share,
    avg(CASE WHEN c.fashion_news_frequency <> 'None' THEN 1.0 ELSE 0.0 END) AS fashion_news_share,
    avg(c.units / c.visits)                                             AS avg_units_per_basket
FROM customer_rfm r
JOIN customer_summary c USING (customer_id)
GROUP BY r.segment
ORDER BY r.segment;


-- name: cohort_retention
-- Cohort = month of a customer's first purchase in the data.
-- Early cohorts include existing customers whose true first purchase came
-- before the data starts, so the notebook drops the first few.
WITH cohorts AS (
    SELECT customer_id, date_trunc('month', first_purchase)::DATE AS cohort_month
    FROM customer_summary
),
activity AS (
    SELECT DISTINCT customer_id, date_trunc('month', t_dat)::DATE AS activity_month
    FROM customer_visits
),
counts AS (
    SELECT
        c.cohort_month,
        date_diff('month', c.cohort_month, a.activity_month)   AS months_since_first,
        count(*)                                               AS active_customers
    FROM activity a
    JOIN cohorts c USING (customer_id)
    GROUP BY 1, 2
),
sizes AS (
    SELECT cohort_month, active_customers AS cohort_size
    FROM counts
    WHERE months_since_first = 0
)
SELECT
    counts.cohort_month,
    counts.months_since_first,
    counts.active_customers,
    sizes.cohort_size,
    counts.active_customers::DOUBLE / sizes.cohort_size       AS retention_rate
FROM counts
JOIN sizes USING (cohort_month)
ORDER BY 1, 2;


-- name: new_customer_repeat_rate
-- Share of new customers who come back within 90 days.
-- Customers first seen in the first 90 days are skipped (many are existing customers),
-- as are those first seen in the last 90 days (not enough time to return).
WITH bounds AS (
    SELECT min(t_dat) AS first_date, max(t_dat) AS last_date FROM transactions
)
SELECT
    count(*)                                                        AS new_customers,
    avg(CASE WHEN c.second_purchase <= c.first_purchase + INTERVAL 90 DAY THEN 1.0 ELSE 0.0 END) AS repeat_rate_90d
FROM customer_summary c
CROSS JOIN bounds b
WHERE c.first_purchase >= b.first_date + INTERVAL 90 DAY
  AND c.first_purchase <= b.last_date - INTERVAL 90 DAY;


-- name: repeat_rate_by_entry_category
-- Same definition, split by the garment groups in the customer's first basket
-- (a customer whose first basket spans two groups counts in both).
-- Product categories only: "Special Offers" and "Unknown" are left out.
WITH bounds AS (
    SELECT min(t_dat) AS first_date, max(t_dat) AS last_date FROM transactions
),
eligible AS (
    SELECT c.*
    FROM customer_summary c
    CROSS JOIN bounds b
    WHERE c.first_purchase >= b.first_date + INTERVAL 90 DAY
      AND c.first_purchase <= b.last_date - INTERVAL 90 DAY
),
entry AS (
    SELECT DISTINCT
        e.customer_id,
        s.garment_group_name,
        coalesce(e.second_purchase <= e.first_purchase + INTERVAL 90 DAY, FALSE) AS repeat_90d
    FROM eligible e
    JOIN sales s ON s.customer_id = e.customer_id AND s.t_dat = e.first_purchase
    WHERE is_product_category(s.garment_group_name)
)
SELECT
    garment_group_name,
    count(*)                                                AS new_customers,
    avg(repeat_90d::INTEGER)                                AS repeat_rate_90d
FROM entry
GROUP BY garment_group_name
ORDER BY repeat_rate_90d DESC;


-- name: age_band_summary
SELECT
    age_band,
    count(*)                                                AS customers,
    count(*)::DOUBLE / sum(count(*)) OVER ()                AS customer_share,
    sum(spend) / sum(sum(spend)) OVER ()                    AS revenue_share,
    avg(spend)                                              AS avg_spend,
    avg(visits)                                             AS avg_shopping_days,
    avg(online_share)                                       AS avg_online_share
FROM customer_summary
GROUP BY age_band
ORDER BY age_band;


-- name: age_band_category_mix
-- What each age band spends its money on (shares sum to 1 within each band)
SELECT
    c.age_band,
    s.index_group_name,
    sum(s.price)                                                        AS revenue,
    sum(s.price) / sum(sum(s.price)) OVER (PARTITION BY c.age_band)     AS share_of_band_revenue
FROM sales s
JOIN customer_summary c USING (customer_id)
GROUP BY c.age_band, s.index_group_name
ORDER BY c.age_band, s.index_group_name;


-- name: engagement_summary
SELECT
    'Club member status'                                    AS attribute,
    club_member_status                                      AS value,
    count(*)                                                AS customers,
    avg(spend)                                              AS avg_spend,
    avg(visits)                                             AS avg_shopping_days
FROM customer_summary
GROUP BY club_member_status
UNION ALL
SELECT
    'Fashion news frequency',
    fashion_news_frequency,
    count(*),
    avg(spend),
    avg(visits)
FROM customer_summary
GROUP BY fashion_news_frequency
ORDER BY attribute, customers DESC;


-- name: channel_preference
SELECT
    CASE
        WHEN online_share = 0 THEN 'Store only'
        WHEN online_share = 1 THEN 'Online only'
        ELSE 'Both channels'
    END                                                     AS shopper_type,
    count(*)                                                AS customers,
    count(*)::DOUBLE / sum(count(*)) OVER ()                AS customer_share,
    sum(spend) / sum(sum(spend)) OVER ()                    AS revenue_share,
    avg(spend)                                              AS avg_spend,
    avg(visits)                                             AS avg_shopping_days
FROM customer_summary
GROUP BY 1
ORDER BY avg_spend DESC;


-- name: top_category_pairs
-- Garment groups bought together more often than chance (lift > 1).
-- Pairs appearing in fewer than 0.1% of baskets are ignored as noise.
SELECT
    group_a,
    group_b,
    baskets_both,
    support,
    pct_of_a_baskets_with_b,
    pct_of_b_baskets_with_a,
    lift
FROM category_pairs
WHERE support >= 0.001
ORDER BY lift DESC
LIMIT 15;
