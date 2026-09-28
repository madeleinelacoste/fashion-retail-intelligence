# %% [markdown]
# # 01 · Merchandising Performance
#
# **Business question:** Which parts of H&M's assortment drive sales, how efficiently is
# the range working, and where is the business relying on markdowns?
#
# All SQL lives in `sql/`; this notebook loads each query by name (`hm.q("...")`) and
# turns the results into charts. Run `python scripts/build_database.py` first.
#
# **A note on prices.** H&M scaled the prices in this dataset, so absolute values are not
# real currency. Everything below is expressed as shares, ratios or indexes, which are
# unaffected by the scaling.

# %%
import sys
from pathlib import Path

ROOT = Path.cwd().parent if Path.cwd().name == "notebooks" else Path.cwd()
sys.path.insert(0, str(ROOT / "src"))

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from hm_analytics import HM, charts

charts.apply_style()
pd.options.display.float_format = "{:,.3f}".format
hm = HM()
print(f"Using database: {hm.path}")

# %% [markdown]
# ## 1. The dataset at a glance

# %%
overview = hm.q("dataset_overview").T.rename(columns={0: "value"})
overview

# %%
hm.q("data_quality_checks")

# %%
monthly = hm.q("monthly_kpis")
complete = monthly[monthly.is_complete_month]

fig, ax = plt.subplots(figsize=(10, 4.5))
ax.bar(complete.month_start, complete.units, width=20, color=charts.ACCENT)
ax.set_title("Units sold per month")
charts.subtitle(ax, "Complete months only")
ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v / 1e6:.1f}M" if v >= 1e6 else f"{v / 1e3:.0f}K"))
ax.grid(axis="x", visible=False)
charts.save(fig, "01_monthly_units")
plt.show()

complete[["month_start", "active_customers", "units_per_basket", "online_unit_share"]]

# %% [markdown]
# ## 2. Where do sales come from?
#
# **Productivity index** = a garment group's share of revenue ÷ its share of the
# articles sold. Above 1.0 means the group earns more than its share of the range;
# below 1.0 means it takes up more of the assortment than its sales justify.
#
# Garment-group comparisons in this notebook leave out "Special Offers" (a promotion
# bucket) and "Unknown" (no label), which are not product categories. Together they are
# under 2% of units (see the data quality checks above).

# %%
index_groups = hm.q("performance_by_index_group")
index_groups

# %%
garment = hm.q("performance_by_garment_group")

fig, ax = plt.subplots(figsize=(9, 7))
top = garment.nlargest(15, "revenue")
order = top.sort_values("productivity_index", ascending=False)
charts.barh(ax, order.garment_group_name, order.productivity_index,
            highlight=set(order.loc[order.productivity_index >= 1, "garment_group_name"]), fmt="{:.2f}")
ax.axvline(1, color=charts.TEXT_SECONDARY, linewidth=1, linestyle="--")
ax.set_title("Assortment productivity by garment group")
charts.subtitle(ax, "Revenue share ÷ article share · blue = earns more than its share of the range · top 15 groups by revenue")
charts.save(fig, "01_garment_group_productivity")
plt.show()

garment[["garment_group_name", "revenue_share", "article_share", "productivity_index", "price_index"]]

# %%
hm.q("top_product_types").head(15)

# %% [markdown]
# ## 3. How concentrated are sales?
#
# A long tail of slow-selling articles ties up design, buying and inventory budget.
# The Pareto curve shows how few articles account for most revenue.

# %%
pareto = hm.q("article_pareto_curve")
summary = hm.q("pareto_summary").iloc[0]

fig, ax = plt.subplots(figsize=(7.5, 5.5))
ax.plot(pareto.cum_article_share, pareto.cum_revenue_share, color=charts.ACCENT)
ax.plot([0, 1], [0, 1], color=charts.MUTED, linewidth=1, linestyle="--")
x80 = summary.article_share_for_80pct_revenue
ax.scatter([x80], [0.8], s=60, color=charts.ACCENT, zorder=3, edgecolor="white", linewidth=2)
ax.annotate(f"{x80:.0%} of articles\n→ 80% of revenue", (x80, 0.8), xytext=(x80 + 0.08, 0.62),
            color=charts.TEXT, arrowprops=dict(arrowstyle="-", color=charts.TEXT_SECONDARY))
charts.pct_axis(ax, "x")
charts.pct_axis(ax, "y")
ax.set_xlabel("Share of articles (best-selling first)")
ax.set_ylabel("Cumulative share of revenue")
ax.set_title("A small share of articles drives most revenue")
charts.save(fig, "01_pareto_curve")
plt.show()

print(f"{summary.article_share_for_50pct_revenue:.1%} of articles generate 50% of revenue")
print(f"{summary.article_share_for_80pct_revenue:.1%} of articles generate 80% of revenue")
print(f"The top 10% of articles generate {summary.revenue_share_top_10pct_articles:.1%} of revenue")
print(f"The bottom half of articles generate {summary.revenue_share_bottom_50pct_articles:.1%} of revenue")

# %%
tail = hm.q("tail_by_garment_group")
fig, ax = plt.subplots(figsize=(9, 7))
charts.barh(ax, tail.garment_group_name, tail.tail_article_share)
charts.pct_axis(ax, "x")
ax.set_title("Share of each group's articles in the long tail")
charts.subtitle(ax, "Tail = articles outside the set that produces 80% of total revenue")
charts.save(fig, "01_long_tail_by_group")
plt.show()
tail

# %% [markdown]
# ## 4. Markdown dependence
#
# The data has no promotion flag, so markdowns are inferred: each article's
# **reference price** is its 90th-percentile selling price, and a unit sold at least
# 15% below that counts as marked down. This is a proxy — it can't separate a
# clearance markdown from, say, a member discount.

# %%
md = hm.q("markdown_by_garment_group")
top_groups = garment.nlargest(15, "revenue").garment_group_name
md_top = md[md.garment_group_name.isin(top_groups)].sort_values("markdown_unit_share", ascending=False)

fig, ax = plt.subplots(figsize=(9, 7))
charts.barh(ax, md_top.garment_group_name, md_top.markdown_unit_share)
charts.pct_axis(ax, "x")
ax.set_title("Share of units sold on markdown, by garment group")
charts.subtitle(ax, "Units sold 15%+ below the article's reference price · top 15 groups by revenue")
charts.save(fig, "01_markdown_by_group")
plt.show()
md_top

# %%
md_month = hm.q("markdown_by_month")
md_month = md_month[md_month.month_start.isin(complete.month_start)]

fig, ax = plt.subplots(figsize=(10, 4.5))
ax.plot(md_month.month_start, md_month.markdown_unit_share, color=charts.ACCENT, marker="o", markersize=5)
charts.pct_axis(ax, "y")
ax.set_ylim(0, None)
ax.set_title("Markdown share of units by month")
charts.subtitle(ax, "Peaks show when the business clears stock")
charts.save(fig, "01_markdown_by_month")
plt.show()

# %% [markdown]
# ## 5. Lifecycles and newness

# %%
hm.q("lifecycle_by_garment_group")

# %%
newness = hm.q("new_vs_carryover_by_season")
fig, ax = plt.subplots(figsize=(9, 4.5))
ax.bar(newness.season_label, newness.new_article_revenue_share, color=charts.ACCENT, width=0.6)
charts.pct_axis(ax, "y")
ax.grid(axis="x", visible=False)
ax.set_title("Share of each season's revenue from newly launched articles")
charts.subtitle(ax, "New = first sale falls inside the season · first and last (partial) seasons excluded")
charts.save(fig, "01_newness_by_season")
plt.show()
newness

# %% [markdown]
# ## 6. Colour mix by season

# %%
colours = hm.q("colour_mix_by_season")
top_colours = colours.groupby("perceived_colour_master_name").units.sum().nlargest(10).index
grid = (colours[colours.perceived_colour_master_name.isin(top_colours)]
        .pivot_table(index="perceived_colour_master_name", columns="season_start", values="unit_share")
        .reindex(top_colours))
labels = colours.drop_duplicates("season_start").set_index("season_start").season_label

fig, ax = plt.subplots(figsize=(10, 5.5))
im = ax.imshow(grid.values, cmap="Blues", aspect="auto")
ax.set_xticks(range(grid.shape[1]), [labels[c] for c in grid.columns], rotation=30, ha="right")
ax.set_yticks(range(grid.shape[0]), grid.index)
ax.grid(False)
for i in range(grid.shape[0]):
    for j in range(grid.shape[1]):
        value = grid.values[i, j]
        ax.text(j, i, f"{value:.0%}", ha="center", va="center", fontsize=8.5,
                color="white" if value > np.nanmax(grid.values) * 0.6 else charts.TEXT)
ax.set_title("Colour share of units by season")
charts.subtitle(ax, "Top 10 colour families · each column sums to 100% across all colours")
charts.save(fig, "01_colour_mix_by_season")
plt.show()

# %% [markdown]
# ## Findings
#
# - **Concentration:** 6.4% of articles produce half of revenue and 19.5% produce 80%; the
#   top 10% of articles alone take 62%, while the bottom 50% contribute just 2.4%. Range
#   decisions at the top of the curve matter far more than those in the tail.
# - **Productivity:** Dressed (2.95×), Swimwear (2.35×), Skirts (2.0×) and Denim (1.97×)
#   earn well above their share of the range. Accessories (0.26×) hold 11% of articles
#   for 3% of revenue, and 96% of Accessories articles sit in the long tail. Jersey Fancy
#   is the biggest group by revenue (14%) but occupies 21% of articles, giving 0.67×.
# - **Markdown exposure:** about 33% of units sell 15%+ below reference price. Exposure is
#   highest in Socks and Tights (46%) and Outdoor (41%) and lowest in Jersey Basic (24%).
#   Without stock data this flags where to review buy depth and pricing, not the cause.
# - **Seasonal newness:** articles launched within the season account for 25–40% of that
#   season's revenue. The share is highest in spring (40% in Spring 2019) and lowest in
#   summer (25–26%), so summer revenue depends more on carry-over articles.
