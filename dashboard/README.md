# Dashboard Build Guide (Tableau Public)

Live dashboard:
[H&M Retail Analytics on Tableau Public](https://public.tableau.com/app/profile/madeleine.lacoste/viz/HMRetailMerchandisingAnalytics/MerchandisingOverview)

Tableau Public is free: <https://public.tableau.com> (download Tableau Public Desktop).
Run `python scripts/export_dashboard_data.py` first; it writes the CSVs below into
`dashboard/data/` (they are generated locally and not committed).

| File | Grain | Used for |
|---|---|---|
| `monthly_kpis.csv` | month | KPI tiles |
| `weekly_sales.csv` | week × index group × garment group × channel | Weekly trend, category mix |
| `product_type_scorecard.csv` | index group × garment group × product type | Scorecard |
| `customer_segments.csv` | segment × age band × shopper type × club status | Customer KPI and customer page |
| `cohort_retention.csv` | cohort month × months since first purchase | Retention heatmap |
| `seasonality.csv` | garment group × month | Seasonality heatmap |
| `garment_group_yoy.csv`, `colour_share_yoy.csv` | category / colour | Share-change bars |
| `category_pairs.csv` | garment-group pair | Cross-sell bars |

`weekly_sales` and `product_type_scorecard` keep every garment group so totals are
complete; use their `is_product_category` column to leave out "Special Offers" and
"Unknown" in category comparisons. The seasonality, share-change and cross-sell files
already exclude them.

Prices are scaled in the H&M data: show sales as **units, shares or indexes**, never
currency (rename `revenue` to "Sales (scaled)").

## Setup

Add each CSV as its **own data source** (Data → New Data Source → Text file); no
relationships are needed. Convert `months_since_first` and `month_no` to discrete
dimensions.

## Calculated fields

Shares and indexes in the scorecard and KPIs are **weighted by units**; a plain average
would give a tiny product type the same weight as a large one.

```
// product_type_scorecard
Revenue share   = SUM([revenue]) / MIN({FIXED : SUM([revenue])})
Markdown share  = SUM([markdown_unit_share] * [units]) / SUM([units])
Online share    = SUM([online_unit_share] * [units]) / SUM([units])
Price index     = SUM([price_index] * [units]) / SUM([units])

// monthly_kpis
Online share (KPI)     = SUM([online_unit_share] * [units]) / SUM([units])
Units per basket (KPI) = SUM([units]) / SUM([baskets])

// customer_segments
Customer share = SUM([customers]) / TOTAL(SUM([customers]))
Revenue share  = SUM([revenue]) / TOTAL(SUM([revenue]))
Spend index    = (SUM([revenue]) / SUM([customers]))
                 / (TOTAL(SUM([revenue])) / TOTAL(SUM([customers])))

// seasonality
Month = LEFT(DATENAME('month', MAKEDATE(2019, [month_no], 1)), 3)

// garment_group_yoy and colour_share_yoy
Share change (pts) = [share_change] * 100      // format: +0.0" pts";-0.0" pts"
Gained share       = SUM([share_change]) >= 0

// colour_share_yoy
Include colour = [share_y1] >= 0.005 OR [share_y2] >= 0.005

// category_pairs
Pair = [group_a] + " + " + [group_b]
```

The scorecard's `Revenue share` uses a FIXED total so a Top-N filter does not change the
denominator; add the `is_product_category` filter **to context** so the total covers
product categories only.

## Page 1 — Merchandising Overview

1. **KPI tiles** (Text marks): units sold `SUM(units)` and units per basket from
   `monthly_kpis`; online share `Online share (KPI)`; customers `SUM(customers)` from
   `customer_segments` (summing monthly active customers would count repeat shoppers
   many times).
2. **Weekly units by channel** (`weekly_sales`, Area): `week_start` as a continuous exact
   date on Columns, `SUM(units)` on Rows, `channel` on Colour. Add a reference band from
   16 Mar to 31 May 2020 annotated "COVID-19: stores closed, sales moved online".
3. **Category mix** (bar): `SUM(revenue)` by `garment_group_name` as Percent of Total,
   filtered to `is_product_category = True`, sorted descending.
4. **Scorecard** (`product_type_scorecard`, text table): top 20 product types by revenue
   with revenue share, price index, markdown share and online share; colour only the
   markdown column.
5. **Filters**: Index group, Channel, Analysis year, applied to all sheets using
   `weekly_sales`.

## Page 2 — Customers

1. **Segment size vs value**: side-by-side bars of `Customer share` and `Revenue share` by
   `segment`.
2. **Retention heatmap** (`cohort_retention`, Square marks): `months_since_first` (1–12) on
   Columns, cohort month (discrete month-year) on Rows, `AVG(retention_rate)` on Colour
   and Label. Exclude the Sep–Nov 2018 cohorts (they include existing customers).
3. **Spend by shopper type** and **by age band**: bars of `Spend index` with a reference
   line at 1.0 (exclude the Unknown age band).
4. **Filters**: Age band, Club member status, applied to all sheets using
   `customer_segments`.

## Page 3 — Trends

1. **Seasonality heatmap**: `Month` (sorted by `month_no`) on Columns, top 12 garment
   groups on Rows, `AVG(seasonality_index)` on a diverging palette centred at 1.0.
2. **Share shifts**: diverging bars of `Share change (pts)` for garment groups and colour
   families, coloured by `Gained share`.
3. **Cross-sell**: bars of `lift` by `Pair`, with a reference line at 1.0 ("chance").

## Style checklist

- One accent colour for the main measure; grey for context.
- Titles state the takeaway (for example "Store sales collapsed in spring 2020 while
  online grew"), not just the metric name.
- No dual axes. No pie charts with more than 3 slices.
- Footnote with the data source and the "prices are scaled" note.
- When publishing, turn off "Allow workbook and its data to be downloaded".
