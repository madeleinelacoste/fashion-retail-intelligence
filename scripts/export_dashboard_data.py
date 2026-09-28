"""Write the CSV files the Tableau / Power BI dashboard is built from.

Usage:
    python scripts/export_dashboard_data.py            # uses data/hm.duckdb (or $HM_DB)
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from hm_analytics import HM  # noqa: E402

OUT = ROOT / "dashboard" / "data"

# output file name -> named query in sql/
EXTRACTS = {
    "monthly_kpis": "monthly_kpis",
    "weekly_sales": "dash_weekly_sales",
    "product_type_scorecard": "dash_product_type_scorecard",
    "customer_segments": "dash_customer_segments",
    "cohort_retention": "cohort_retention",
    "category_pairs": "top_category_pairs",
    "colour_share_yoy": "colour_share_yoy",
    "garment_group_yoy": "garment_group_yoy",
    "seasonality": "monthly_seasonality_by_garment_group",
}


def main():
    hm = HM()
    OUT.mkdir(parents=True, exist_ok=True)
    for filename, query in EXTRACTS.items():
        df = hm.q(query)
        df.to_csv(OUT / f"{filename}.csv", index=False)
        print(f"{filename + '.csv':<30} {len(df):>8,} rows")
    print(f"Saved to {OUT.relative_to(ROOT)}/")


if __name__ == "__main__":
    main()
