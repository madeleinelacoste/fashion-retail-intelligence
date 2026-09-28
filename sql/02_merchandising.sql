-- ============================================================================
-- 02  Merchandising: where sales come from, how productive the assortment is,
--     how much is sold on markdown, and how the mix changes by season
-- ============================================================================


-- name: performance_by_index_group
-- price_index compares the group's average selling price with the overall average (1.0)
SELECT
    index_group_name,
    count(*)                                            AS units,
    sum(price)                                          AS revenue,
    sum(price) / sum(sum(price)) OVER ()                AS revenue_share,
    count(*)::DOUBLE / sum(count(*)) OVER ()            AS unit_share,
    count(DISTINCT article_id)                          AS articles_sold,
    avg(price) / (SELECT avg(price) FROM transactions)  AS price_index
FROM sales
GROUP BY index_group_name
ORDER BY revenue DESC;


-- name: performance_by_garment_group
-- productivity_index = revenue share / share of articles.
-- Above 1 means the group earns more than its share of the assortment.
-- Shares are of product-category sales ("Special Offers" and "Unknown" left out).
WITH g AS (
    SELECT
        garment_group_name,
        count(*)                                        AS units,
        sum(price)                                      AS revenue,
        count(DISTINCT article_id)                      AS articles_sold,
        avg(price)                                      AS avg_price
    FROM sales
    WHERE is_product_category(garment_group_name)
    GROUP BY garment_group_name
)
SELECT
    garment_group_name,
    units,
    revenue,
    articles_sold,
    revenue / sum(revenue) OVER ()                      AS revenue_share,
    articles_sold::DOUBLE / sum(articles_sold) OVER ()  AS article_share,
    (revenue / sum(revenue) OVER ())
        / (articles_sold::DOUBLE / sum(articles_sold) OVER ()) AS productivity_index,
    revenue / articles_sold                             AS revenue_per_article,
    avg_price / (SELECT avg(price) FROM transactions)   AS price_index
FROM g
ORDER BY revenue DESC;


-- name: top_product_types
SELECT
    product_type_name,
    any_value(product_group_name)                       AS product_group_name,
    count(*)                                            AS units,
    sum(price)                                          AS revenue,
    sum(price) / sum(sum(price)) OVER ()                AS revenue_share,
    count(DISTINCT article_id)                          AS articles_sold,
    avg(price) / (SELECT avg(price) FROM transactions)  AS price_index
FROM sales
GROUP BY product_type_name
ORDER BY revenue DESC
LIMIT 25;


-- name: article_pareto_curve
-- Cumulative share of revenue against cumulative share of articles, thinned to ~1,000 points
WITH ranked AS (
    SELECT
        row_number() OVER (ORDER BY revenue DESC)       AS rank,
        count(*) OVER ()                                AS n_articles,
        sum(revenue) OVER (ORDER BY revenue DESC ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)
            / sum(revenue) OVER ()                      AS cum_revenue_share
    FROM article_summary
)
SELECT
    rank::DOUBLE / n_articles                           AS cum_article_share,
    cum_revenue_share
FROM ranked
WHERE rank = 1
   OR rank = n_articles
   OR rank % greatest(1, floor(n_articles / 1000))::BIGINT = 0
ORDER BY rank;


-- name: pareto_summary
WITH ranked AS (
    SELECT
        revenue,
        row_number() OVER (ORDER BY revenue DESC)       AS rank,
        count(*) OVER ()                                AS n_articles,
        sum(revenue) OVER (ORDER BY revenue DESC ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)
            / sum(revenue) OVER ()                      AS cum_revenue_share
    FROM article_summary
)
SELECT
    max(n_articles)                                                         AS articles_sold,
    min(rank) FILTER (WHERE cum_revenue_share >= 0.5)::DOUBLE / max(n_articles) AS article_share_for_50pct_revenue,
    min(rank) FILTER (WHERE cum_revenue_share >= 0.8)::DOUBLE / max(n_articles) AS article_share_for_80pct_revenue,
    sum(revenue) FILTER (WHERE rank <= 0.1 * n_articles) / sum(revenue)     AS revenue_share_top_10pct_articles,
    sum(revenue) FILTER (WHERE rank > 0.5 * n_articles) / sum(revenue)      AS revenue_share_bottom_50pct_articles
FROM ranked;


-- name: tail_by_garment_group
-- "Tail" articles are those outside the set that together produce 80% of revenue
WITH ranked AS (
    SELECT
        article_id,
        revenue,
        sum(revenue) OVER (ORDER BY revenue DESC ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING)
            / sum(revenue) OVER ()                      AS revenue_share_before
    FROM article_summary
),
flagged AS (
    SELECT r.*, a.garment_group_name, coalesce(r.revenue_share_before, 0) >= 0.8 AS is_tail
    FROM ranked r
    JOIN articles a USING (article_id)
    WHERE is_product_category(a.garment_group_name)
)
SELECT
    garment_group_name,
    count(*)                                                        AS articles,
    avg(is_tail::INTEGER)                                           AS tail_article_share,
    coalesce(sum(revenue) FILTER (WHERE is_tail), 0) / sum(revenue) AS tail_revenue_share
FROM flagged
GROUP BY garment_group_name
ORDER BY tail_article_share DESC;


-- name: markdown_by_garment_group
-- markdown_unit_share = share of units sold 15%+ below the article's reference price
-- avg_markdown_depth   = average discount on those marked-down units
SELECT
    t.garment_group_name,
    count(*)                                                        AS units,
    avg(CASE WHEN t.price < 0.85 * s.ref_price THEN 1.0 ELSE 0.0 END) AS markdown_unit_share,
    avg(1 - t.price / s.ref_price) FILTER (WHERE t.price < 0.85 * s.ref_price) AS avg_markdown_depth
FROM sales t
JOIN article_summary s USING (article_id)
WHERE is_product_category(t.garment_group_name)
GROUP BY t.garment_group_name
ORDER BY markdown_unit_share DESC;


-- name: markdown_by_month
SELECT
    t.month_start,
    count(*)                                                        AS units,
    avg(CASE WHEN t.price < 0.85 * s.ref_price THEN 1.0 ELSE 0.0 END) AS markdown_unit_share,
    avg(1 - t.price / s.ref_price) FILTER (WHERE t.price < 0.85 * s.ref_price) AS avg_markdown_depth
FROM transactions t
JOIN article_summary s USING (article_id)
GROUP BY t.month_start
ORDER BY t.month_start;


-- name: channel_mix_by_garment_group
SELECT
    garment_group_name,
    count(*)                                                        AS units,
    avg(CASE WHEN channel = 'Online' THEN 1.0 ELSE 0.0 END)         AS online_unit_share
FROM sales
WHERE is_product_category(garment_group_name)
GROUP BY garment_group_name
ORDER BY online_unit_share DESC;


-- name: lifecycle_by_garment_group
-- Only articles first seen 8+ weeks after the data starts (so they are genuinely new)
-- and 26+ weeks before it ends (so they had time to sell). Lifecycles longer than
-- the observation window are still cut short, so treat the medians as lower bounds.
WITH bounds AS (
    SELECT min(t_dat) AS first_date, max(t_dat) AS last_date FROM transactions
)
SELECT
    a.garment_group_name,
    count(*)                                        AS articles,
    median(s.active_weeks)                          AS median_selling_weeks,
    median(s.units)                                 AS median_units_per_article,
    avg(s.units)                                    AS avg_units_per_article
FROM article_summary s
JOIN articles a USING (article_id)
CROSS JOIN bounds b
WHERE s.first_sale >= b.first_date + INTERVAL 56 DAY
  AND s.first_sale <= b.last_date - INTERVAL 182 DAY
  AND is_product_category(a.garment_group_name)
GROUP BY a.garment_group_name
ORDER BY median_selling_weeks DESC;


-- name: new_vs_carryover_by_season
-- "New" = the article's first observed sale falls inside that season.
-- The first season is excluded because every article looks new there, and the
-- last season is excluded because it is incomplete.
SELECT
    t.season_start,
    any_value(t.season_label)                                           AS season_label,
    count(DISTINCT t.article_id)                                        AS articles_sold,
    count(DISTINCT t.article_id) FILTER (WHERE s.first_sale >= t.season_start) AS new_articles,
    sum(t.price) FILTER (WHERE s.first_sale >= t.season_start) / sum(t.price)   AS new_article_revenue_share
FROM transactions t
JOIN article_summary s USING (article_id)
WHERE t.season_start > (SELECT min(season_start) FROM transactions)
  AND t.season_start < (SELECT max(season_start) FROM transactions)
GROUP BY t.season_start
ORDER BY t.season_start;


-- name: colour_mix_by_season
SELECT
    season_start,
    any_value(season_label)                                             AS season_label,
    perceived_colour_master_name,
    count(*)                                                            AS units,
    count(*)::DOUBLE / sum(count(*)) OVER (PARTITION BY season_start)   AS unit_share
FROM sales
WHERE season_start > (SELECT min(season_start) FROM transactions)
  AND season_start < (SELECT max(season_start) FROM transactions)
GROUP BY season_start, perceived_colour_master_name
ORDER BY season_start, units DESC;
