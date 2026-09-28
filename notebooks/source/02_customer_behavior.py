# %% [markdown]
# # 02 · Customer Behavior
#
# **Business question:** Who are H&M's most valuable customers, how well does the
# business keep new customers, and which products bring people back?
#
# A **shopping day** (or basket) is all of a customer's purchases on one date.

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

# %% [markdown]
# ## 1. How often do customers shop?

# %%
freq = hm.q("visit_frequency_distribution")

fig, ax = plt.subplots(figsize=(9, 4.8))
x = np.arange(len(freq))
ax.bar(x - 0.2, freq.customer_share, width=0.38, label="Share of customers", color=charts.SERIES[0])
ax.bar(x + 0.2, freq.revenue_share, width=0.38, label="Share of revenue", color=charts.SERIES[1])
ax.set_xticks(x, freq.shopping_days)
ax.set_xlabel("Shopping days over the two years")
charts.pct_axis(ax, "y")
ax.grid(axis="x", visible=False)
ax.legend(loc="upper right")
ax.set_title("A minority of frequent shoppers drives a large share of revenue")
charts.save(fig, "02_frequency_distribution")
plt.show()
freq

# %% [markdown]
# ## 2. RFM segmentation
#
# Each customer is scored 1–5 on **Recency** (days since last purchase), **Frequency**
# (shopping days) and **Monetary** value (total spend), then grouped into segments
# (definitions in `sql/00_build_tables.sql`).

# %%
segments = hm.q("rfm_segment_summary")
order = segments.sort_values("revenue_share", ascending=False)

fig, ax = plt.subplots(figsize=(9, 5))
y = np.arange(len(order))[::-1]
ax.barh(y + 0.2, order.customer_share, height=0.38, label="Share of customers", color=charts.SERIES[0])
ax.barh(y - 0.2, order.revenue_share, height=0.38, label="Share of revenue", color=charts.SERIES[1])
ax.set_yticks(y, order.segment)
charts.pct_axis(ax, "x")
ax.grid(axis="y", visible=False)
ax.legend(loc="lower right")
ax.set_title("Customer segments: size vs. value")
charts.save(fig, "02_rfm_segments")
plt.show()
segments

# %%
hm.q("rfm_segment_profile")

# %% [markdown]
# ## 3. Retention by first-purchase cohort
#
# Customers are grouped by the month of their first purchase in the data. The first
# three cohorts are dropped: many of those "new" customers had simply shopped before
# the data begins.

# %%
cohorts = hm.q("cohort_retention")
first_cohorts = sorted(cohorts.cohort_month.unique())[:3]
cohorts = cohorts[~cohorts.cohort_month.isin(first_cohorts)]
grid = cohorts.pivot_table(index="cohort_month", columns="months_since_first", values="retention_rate")
grid = grid.loc[:, 1:12]
grid.index = pd.to_datetime(grid.index).strftime("%b %Y")

fig, ax = plt.subplots(figsize=(11, 7))
ax.imshow(grid.values, cmap="Blues", aspect="auto", vmin=0)
ax.set_xticks(range(grid.shape[1]), grid.columns)
ax.set_yticks(range(grid.shape[0]), grid.index)
ax.set_xlabel("Months since first purchase")
ax.grid(False)
vmax = np.nanmax(grid.values)
for i in range(grid.shape[0]):
    for j in range(grid.shape[1]):
        value = grid.values[i, j]
        if not np.isnan(value):
            ax.text(j, i, f"{value:.0%}", ha="center", va="center", fontsize=8,
                    color="white" if value > vmax * 0.6 else charts.TEXT)
ax.set_title("Share of each cohort that shops again in a given month")
charts.save(fig, "02_cohort_retention")
plt.show()

# %% [markdown]
# ## 4. Which first purchases lead to repeat customers?
#
# For customers whose first purchase falls at least 90 days after the data starts, what
# share come back within 90 days, split by what was in their first basket? This is
# descriptive: a high rate could reflect the kind of shopper who buys that category,
# not the category itself. "Special Offers" and "Unknown" are left out because they are
# not product categories.

# %%
baseline = hm.q("new_customer_repeat_rate").iloc[0]
entry = hm.q("repeat_rate_by_entry_category")
entry = entry[entry.new_customers >= entry.new_customers.sum() * 0.01]   # ignore tiny groups

fig, ax = plt.subplots(figsize=(9, 7))
charts.barh(ax, entry.garment_group_name, entry.repeat_rate_90d,
            highlight=set(entry.loc[entry.repeat_rate_90d > baseline.repeat_rate_90d, "garment_group_name"]))
ax.axvline(baseline.repeat_rate_90d, color=charts.TEXT_SECONDARY, linewidth=1, linestyle="--")
ax.text(baseline.repeat_rate_90d, -0.9, f" all new customers: {baseline.repeat_rate_90d:.0%}",
        color=charts.TEXT_SECONDARY, fontsize=9)
charts.pct_axis(ax, "x")
ax.set_title("90-day repeat rate by first-basket garment group")
charts.subtitle(ax, "Blue = above the average for all new customers")
charts.save(fig, "02_repeat_rate_by_entry_category")
plt.show()
print(f"{int(baseline.new_customers):,} new customers, {baseline.repeat_rate_90d:.1%} returned within 90 days")
entry

# %% [markdown]
# ## 5. Age and category preferences

# %%
hm.q("age_band_summary")

# %%
mix = hm.q("age_band_category_mix")
grid = mix.pivot_table(index="index_group_name", columns="age_band", values="share_of_band_revenue").fillna(0)
grid = grid[[c for c in grid.columns if c != "Unknown"]]

fig, ax = plt.subplots(figsize=(8, 4.5))
ax.imshow(grid.values, cmap="Blues", aspect="auto", vmin=0)
ax.set_xticks(range(grid.shape[1]), grid.columns)
ax.set_yticks(range(grid.shape[0]), grid.index)
ax.set_xlabel("Customer age")
ax.grid(False)
vmax = grid.values.max()
for i in range(grid.shape[0]):
    for j in range(grid.shape[1]):
        value = grid.values[i, j]
        ax.text(j, i, f"{value:.0%}", ha="center", va="center", fontsize=9,
                color="white" if value > vmax * 0.6 else charts.TEXT)
ax.set_title("Where each age group spends")
charts.subtitle(ax, "Share of each age band's revenue by department group · columns sum to 100%")
charts.save(fig, "02_age_category_mix")
plt.show()

# %% [markdown]
# ## 6. Channel and loyalty-program behavior

# %%
channel = hm.q("channel_preference")
fig, ax = plt.subplots(figsize=(8, 3.5))
spend_index = channel.avg_spend / (channel.avg_spend * channel.customer_share).sum()
charts.barh(ax, channel.shopper_type, spend_index, fmt="{:.2f}×")
ax.set_title("Average spend per customer by channel use")
charts.subtitle(ax, "Indexed to the average customer (1.0×)")
charts.save(fig, "02_channel_spend")
plt.show()
channel

# %%
hm.q("engagement_summary")

# %% [markdown]
# ## 7. What gets bought together?
#
# **Lift** = how much more often two garment groups appear in the same basket than if
# customers picked them independently. Lift of 2 means twice as often as chance.
# Only product categories are paired ("Special Offers" and "Unknown" are left out).

# %%
hm.q("top_category_pairs")

# %% [markdown]
# ## Findings
#
# - **Value concentration:** a third of customers (33%) shopped on only one day and
#   contribute under 5% of revenue, while the 8% who shopped on 20+ days contribute 39%.
#   In RFM terms, Champions are 27% of customers and 67% of revenue; Lapsed customers
#   are 28% of the base but 4% of revenue.
# - **Retention:** 37.5% of new customers buy again within 90 days. In the cohort view,
#   monthly return rates for cohorts from mid-2019 onward mostly sit around 10–15%,
#   below the earliest cohorts shown (Dec 2018 – Mar 2019, mostly 15–20%), which likely
#   still include some existing customers first seen near the start of the data.
# - **Entry categories:** 90-day repeat rates by first-basket garment group sit in a
#   narrow 36–41% band (Dresses Ladies, Skirts and Blouses highest at 41%; Shirts and
#   Socks and Tights lowest at 36%). First category is a weak signal of short-term
#   loyalty on its own.
# - **Channel and age:** customers who shop both online and in store are 36% of customers
#   but 68% of revenue; online-only shoppers are 46% of customers but 26% of revenue.
#   The 25–34 age band is the most valuable (29% of customers, 37% of revenue). These are
#   associations, not proof that a second channel raises spend.
# - **Basket affinity:** the strongest cross-category pairs are seasonal: Shorts with
#   Swimwear (lift 1.97) and Shorts with Skirts (1.95), plus Dresses with Skirts (1.80),
#   which points to summer outfit-building as a cross-sell opportunity.
