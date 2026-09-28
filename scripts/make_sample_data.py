"""Generate a small SYNTHETIC dataset with the same columns as the H&M Kaggle files.

It exists only so the pipeline can be tested end to end without the 3.5 GB
download. The numbers it produces are made up: never report results from it.

Usage:
    python scripts/make_sample_data.py                 # writes data/sample/*.csv
    python scripts/build_database.py --raw-dir data/sample --db data/hm_sample.duckdb
"""
import argparse
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
START, END = pd.Timestamp("2018-09-20"), pd.Timestamp("2020-09-22")
COVID_START, COVID_END = pd.Timestamp("2020-03-16"), pd.Timestamp("2020-05-31")

# product_type, product_group, garment_group, index_group, peak month (None = flat), base price
PRODUCT_TYPES = [
    ("T-shirt", "Garment Upper body", "Jersey Basic", "Ladieswear", 7, 0.015),
    ("Vest top", "Garment Upper body", "Jersey Basic", "Divided", 7, 0.012),
    ("Baby Bodysuit", "Garment Full body", "Jersey Basic", "Baby/Children", None, 0.012),
    ("Top", "Garment Upper body", "Jersey Fancy", "Sport", 4, 0.018),
    ("Leggings/Tights", "Garment Lower body", "Jersey Fancy", "Sport", None, 0.02),
    ("Sweater", "Garment Upper body", "Knitwear", "Ladieswear", 11, 0.04),
    ("Cardigan", "Garment Upper body", "Knitwear", "Menswear", 11, 0.035),
    ("Blouse", "Garment Upper body", "Blouses", "Ladieswear", 5, 0.03),
    ("Shirt", "Garment Upper body", "Shirts", "Menswear", None, 0.03),
    ("Trousers", "Garment Lower body", "Trousers", "Ladieswear", None, 0.035),
    ("Jeans", "Garment Lower body", "Trousers Denim", "Divided", None, 0.035),
    ("Shorts", "Garment Lower body", "Shorts", "Divided", 7, 0.02),
    ("Skirt", "Garment Lower body", "Skirts", "Ladieswear", 6, 0.025),
    ("Dress", "Garment Full body", "Dresses Ladies", "Ladieswear", 6, 0.04),
    ("Jumpsuit/Playsuit", "Garment Full body", "Dresses/Skirts girls", "Baby/Children", 6, 0.02),
    ("Jacket", "Garment Upper body", "Outdoor", "Menswear", 10, 0.06),
    ("Coat", "Garment Upper body", "Outdoor", "Ladieswear", 11, 0.08),
    ("Bra", "Underwear", "Under-, Nightwear", "Ladieswear", None, 0.02),
    ("Underwear bottom", "Underwear", "Under-, Nightwear", "Ladieswear", None, 0.01),
    ("Pyjama set", "Nightwear", "Under-, Nightwear", "Ladieswear", 12, 0.025),
    ("Bikini top", "Swimwear", "Swimwear", "Ladieswear", 6, 0.015),
    ("Swimwear bottom", "Swimwear", "Swimwear", "Ladieswear", 6, 0.015),
    ("Sneakers", "Shoes", "Shoes", "Divided", None, 0.04),
    ("Boots", "Shoes", "Shoes", "Ladieswear", 11, 0.06),
    ("Bag", "Accessories", "Accessories", "Ladieswear", None, 0.025),
    ("Earring", "Accessories", "Accessories", "Divided", 12, 0.008),
    ("Hat/beanie", "Accessories", "Accessories", "Menswear", 12, 0.01),
    ("Socks", "Socks & Tights", "Socks and Tights", "Menswear", None, 0.008),
]
INDEX_GROUPS = sorted({p[3] for p in PRODUCT_TYPES})
YOUNG_INDEX_GROUPS = {"Divided", "Sport"}

# colour_group_name, perceived_colour_master_name, base weight, drift over the two years
COLOURS = [
    ("Black", "Black", 0.25, 0.0), ("White", "White", 0.12, 0.0), ("Dark Blue", "Blue", 0.10, -0.3),
    ("Light Blue", "Blue", 0.05, 0.0), ("Beige", "Beige", 0.08, 1.2), ("Grey", "Grey", 0.08, -0.2),
    ("Light Pink", "Pink", 0.06, 0.0), ("Red", "Red", 0.04, -0.3), ("Dark Green", "Green", 0.03, 0.5),
    ("Khaki green", "Khaki green", 0.04, 0.8), ("Dark Brown", "Brown", 0.03, 0.3), ("Yellow", "Yellow", 0.03, 0.0),
    ("Orange", "Orange", 0.02, 0.0), ("Light Purple", "Lilac Purple", 0.02, 0.0), ("Gold", "Metal", 0.02, 0.0),
]


def hex_ids(rng, n, length=64):
    return ["".join(row) for row in rng.choice(list("0123456789abcdef"), size=(n, length))]


def make_articles(rng, n_products):
    rows, span = [], (END - START).days
    for product_code in range(108775, 108775 + n_products):
        t = rng.integers(len(PRODUCT_TYPES))
        ptype, pgroup, ggroup, igroup, peak, base = PRODUCT_TYPES[t]
        launch = START - pd.Timedelta(days=int(rng.integers(0, 150))) if rng.random() < 0.3 \
            else START + pd.Timedelta(days=int(rng.integers(0, span)))
        progress = min(max((launch - START).days / span, 0), 1)
        weights = np.array([w * (1 + d * progress) for _, _, w, d in COLOURS])
        n_variants = rng.integers(1, 4)
        for variant, c in enumerate(rng.choice(len(COLOURS), size=n_variants, replace=False, p=weights / weights.sum())):
            colour, master, _, _ = COLOURS[c]
            rows.append({
                "article_id": f"0{product_code:06d}{variant + 1:03d}",
                "product_code": product_code, "prod_name": f"{ptype} {product_code}",
                "product_type_no": t, "product_type_name": ptype, "product_group_name": pgroup,
                "graphical_appearance_no": 1010016, "graphical_appearance_name": "Solid",
                "colour_group_code": c, "colour_group_name": colour,
                "perceived_colour_value_id": 1, "perceived_colour_value_name": "Medium",
                "perceived_colour_master_id": c, "perceived_colour_master_name": master,
                "department_no": 1000 + t, "department_name": f"{ggroup} {igroup}",
                "index_code": igroup[0], "index_name": igroup, "index_group_no": INDEX_GROUPS.index(igroup),
                "index_group_name": igroup, "section_no": t, "section_name": f"{igroup} {pgroup}",
                "garment_group_no": 1000 + t, "garment_group_name": ggroup,
                "detail_desc": f"Synthetic {ptype.lower()} in {colour.lower()}.",
                # generator-only fields, dropped before writing
                "_launch": launch, "_life_days": int(rng.gamma(3, 60)) + 28,
                "_pop": rng.lognormal(0, 1.1), "_peak": peak, "_price": base * rng.lognormal(0, 0.3),
                "_young": igroup in YOUNG_INDEX_GROUPS,
            })
    return pd.DataFrame(rows)


def make_customers(rng, n):
    young = rng.random(n) < 0.6
    age = np.where(young, rng.normal(27, 5, n), rng.normal(48, 10, n)).clip(16, 90).round()
    news = rng.choice(["NONE", "Regularly", "Monthly", None], size=n, p=[0.6, 0.38, 0.005, 0.015])
    subscribed = np.isin(news, ["Regularly", "Monthly"])
    df = pd.DataFrame({
        "customer_id": hex_ids(rng, n),
        "FN": np.where(subscribed, 1.0, np.nan),
        "Active": np.where(subscribed & (rng.random(n) < 0.97), 1.0, np.nan),
        "club_member_status": rng.choice(["ACTIVE", "PRE-CREATE", "LEFT CLUB"], size=n, p=[0.93, 0.06, 0.01]),
        "fashion_news_frequency": news,
        "age": pd.array(np.where(rng.random(n) < 0.01, np.nan, age), dtype="Int64"),
        "postal_code": hex_ids(rng, n),
    })
    return df


def daily_demand(days):
    doy = days.dayofyear.to_numpy()
    demand = 1 + 0.2 * np.sin(2 * np.pi * (doy - 80) / 365)
    demand += 0.6 * ((days.month == 11) & (days.day >= 22) & (days.day <= 30))   # Black Friday week
    demand += 0.4 * ((days.month == 12) & (days.day <= 22))
    demand += 0.3 * ((days.month == 6) & (days.day >= 20)) + 0.3 * ((days.month == 7) & (days.day <= 10))
    demand *= np.where((days >= COVID_START) & (days <= COVID_END), 0.6, 1.0)
    demand *= 1 + 0.08 * (days - START).days.to_numpy() / 365
    return demand


def make_visits(rng, customers):
    days = pd.date_range(START, END)
    demand = daily_demand(days)
    accept = demand / demand.max()
    n_days = len(days)
    rate = rng.lognormal(np.log(3), 1.0, len(customers))          # shopping days per year
    existing = rng.random(len(customers)) < 0.45
    first = np.where(existing, 0, rng.integers(0, n_days, len(customers)))
    life = rng.exponential(420, len(customers)).astype(int) + 1
    online_pref = rng.beta(1.2, 3, len(customers))

    cust_idx, day_idx = [], []
    for i in range(len(customers)):
        last = min(n_days - 1, first[i] + life[i])
        n = rng.poisson(rate[i] * (last - first[i] + 1) / 365 * 2) + 1
        candidates = rng.integers(first[i], last + 1, n)
        kept = candidates[rng.random(n) < accept[candidates]]
        kept = np.unique(kept) if len(kept) else candidates[:1]
        cust_idx.append(np.full(len(kept), i))
        day_idx.append(kept)
    visits = pd.DataFrame({"cust": np.concatenate(cust_idx), "day": np.concatenate(day_idx)})
    visits["date"] = days[visits.day]
    shift = np.where(visits.date >= COVID_START, 0.2, 0.0)
    visits["online"] = rng.random(len(visits)) < np.clip(online_pref[visits.cust] + shift, 0, 1)
    visits["size"] = rng.geometric(0.45, len(visits))
    return visits


def assign_articles(rng, visits, articles, young_customer):
    rows = visits.loc[visits.index.repeat(visits["size"])].reset_index(drop=True)
    rows["young"] = young_customer[rows.cust]
    launch = articles._launch.to_numpy()
    end = launch + pd.to_timedelta(articles._life_days, unit="D").to_numpy()
    peak = articles._peak.to_numpy(dtype=float)   # NaN = no seasonal peak
    base_pop = articles._pop.to_numpy()
    young_article = articles._young.to_numpy()
    rows["article"] = -1
    for date, idx in rows.groupby("date").groups.items():
        active = (launch <= date) & (end >= date)
        season = np.where(np.isnan(peak), 1.0, 1 + 0.9 * np.cos(2 * np.pi * (date.month - peak) / 12))
        weight = base_pop * season * active
        for is_young in (True, False):
            sub = idx[rows.loc[idx, "young"].to_numpy() == is_young]
            if len(sub) == 0:
                continue
            w = weight * np.where(young_article == is_young, 2.0, 1.0)
            rows.loc[sub, "article"] = rng.choice(len(articles), size=len(sub), p=w / w.sum())
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--customers", type=int, default=30_000)
    parser.add_argument("--products", type=int, default=1_500)
    parser.add_argument("--out", type=Path, default=ROOT / "data" / "sample")
    args = parser.parse_args()
    rng = np.random.default_rng(42)

    articles = make_articles(rng, args.products)
    customers = make_customers(rng, args.customers)
    young_customer = (customers.age.fillna(30) < 35).to_numpy()
    visits = make_visits(rng, customers)
    rows = assign_articles(rng, visits, articles, young_customer)

    art = articles.iloc[rows.article.to_numpy()].reset_index(drop=True)
    age_share = ((rows.date - art._launch).dt.days / art._life_days).to_numpy()
    discount = np.where(age_share > 0.6, rng.choice([0.5, 0.6, 0.7], len(rows)), 1.0)
    transactions = pd.DataFrame({
        "t_dat": rows.date.dt.strftime("%Y-%m-%d"),
        "customer_id": customers.customer_id.to_numpy()[rows.cust],
        "article_id": art.article_id,
        "price": (art._price * discount).round(6),
        "sales_channel_id": np.where(rows.online, 2, 1),
    }).sort_values("t_dat")

    args.out.mkdir(parents=True, exist_ok=True)
    articles.drop(columns=[c for c in articles.columns if c.startswith("_")]).to_csv(args.out / "articles.csv", index=False)
    customers.to_csv(args.out / "customers.csv", index=False)
    transactions.to_csv(args.out / "transactions_train.csv", index=False)
    print(f"SYNTHETIC sample: {len(articles):,} articles, {len(customers):,} customers, "
          f"{len(transactions):,} transactions -> {args.out}")


if __name__ == "__main__":
    main()
