"""Build the DuckDB database used by every SQL file, notebook and dashboard extract.

Reads the three H&M CSV files, cleans them, adds calendar fields, then runs
sql/00_build_tables.sql to create the summary tables the analysis relies on.

Usage:
    python scripts/build_database.py                         # full dataset from data/raw
    python scripts/build_database.py --customer-pct 10       # 10% customer sample (faster)
    python scripts/build_database.py --raw-dir data/sample --db data/hm_sample.duckdb
"""
import argparse
import datetime as dt
import time
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]


def run_sql_file(con, path):
    """Run every statement in a .sql file, printing how long each one takes."""
    lines = [line for line in path.read_text(encoding="utf-8").splitlines() if not line.strip().startswith("--")]
    for statement in "\n".join(lines).split(";"):
        statement = statement.strip()
        if not statement:
            continue
        start = time.time()
        con.execute(statement)
        print(f"  {statement.splitlines()[0][:70]:<70} {time.time() - start:6.1f}s")


def analysis_years(first_date, last_date):
    """Two back-to-back 52-week years ending on the last complete Monday-Sunday week."""
    last_full_sunday = last_date - dt.timedelta(days=(last_date.weekday() + 1) % 7)
    first_full_monday = first_date + dt.timedelta(days=(7 - first_date.weekday()) % 7)
    y2_start = last_full_sunday - dt.timedelta(days=363)
    y1_start = y2_start - dt.timedelta(days=364)
    if y1_start < first_full_monday:
        raise ValueError("Data covers less than two full years; adjust analysis_years().")
    return first_full_monday, last_full_sunday, y1_start, y2_start


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--raw-dir", default=ROOT / "data" / "raw", type=Path)
    parser.add_argument("--db", default=ROOT / "data" / "hm.duckdb", type=Path)
    parser.add_argument("--customer-pct", type=int, default=100,
                        help="Keep this percentage of customers (1-100). Sampling is by customer, so baskets stay intact.")
    args = parser.parse_args()

    raw = args.raw_dir
    for name in ("articles.csv", "customers.csv", "transactions_train.csv"):
        if not (raw / name).exists():
            raise SystemExit(f"Missing {raw / name}. See data/README.md for download instructions.")

    args.db.parent.mkdir(parents=True, exist_ok=True)
    if args.db.exists():
        args.db.unlink()
    con = duckdb.connect(str(args.db))
    sample_filter = f"hash(customer_id) % 100 < {args.customer_pct}" if args.customer_pct < 100 else "TRUE"

    print("Loading articles ...")
    con.execute(f"""
        CREATE TABLE articles AS
        SELECT * REPLACE (lpad(article_id, 10, '0') AS article_id)
        FROM read_csv('{raw / "articles.csv"}', header = true,
                      types = {{'article_id': 'VARCHAR', 'product_code': 'VARCHAR'}})
    """)

    print("Loading customers ...")
    con.execute(f"""
        CREATE TABLE customers AS
        SELECT
            customer_id,
            age,
            CASE
                WHEN age IS NULL THEN 'Unknown'
                WHEN age < 25 THEN '16-24'
                WHEN age < 35 THEN '25-34'
                WHEN age < 45 THEN '35-44'
                WHEN age < 55 THEN '45-54'
                ELSE '55+'
            END AS age_band,
            coalesce(club_member_status, 'UNKNOWN') AS club_member_status,
            CASE upper(fashion_news_frequency)
                WHEN 'REGULARLY' THEN 'Regularly'
                WHEN 'MONTHLY' THEN 'Monthly'
                ELSE 'None'
            END AS fashion_news_frequency,
            FN = 1 AS fashion_news_opt_in,
            Active = 1 AS active_flag,
            postal_code
        FROM read_csv('{raw / "customers.csv"}', header = true,
                      types = {{'customer_id': 'VARCHAR', 'age': 'INTEGER', 'FN': 'DOUBLE',
                               'Active': 'DOUBLE', 'postal_code': 'VARCHAR'}})
        WHERE {sample_filter}
    """)

    print("Loading transactions (this is the slow step on the full dataset) ...")
    con.execute(f"""
        CREATE TEMP TABLE raw_transactions AS
        SELECT t_dat, customer_id, lpad(article_id, 10, '0') AS article_id, price, sales_channel_id
        FROM read_csv('{raw / "transactions_train.csv"}', header = true,
                      columns = {{'t_dat': 'DATE', 'customer_id': 'VARCHAR', 'article_id': 'VARCHAR',
                                 'price': 'DOUBLE', 'sales_channel_id': 'INTEGER'}})
        WHERE {sample_filter}
    """)

    first_date, last_date = con.execute("SELECT min(t_dat), max(t_dat) FROM raw_transactions").fetchone()
    first_full, last_full, y1_start, y2_start = analysis_years(first_date, last_date)
    print(f"  Data runs {first_date} to {last_date}")
    print(f"  Y1 = {y1_start} to {y2_start - dt.timedelta(days=1)}, Y2 = {y2_start} to {last_full}")

    con.execute(f"""
        CREATE TABLE transactions AS
        WITH base AS (
            SELECT *,
                (date_trunc('quarter', t_dat - INTERVAL 2 MONTH) + INTERVAL 2 MONTH)::DATE AS season_start
            FROM raw_transactions
        )
        SELECT
            t_dat,
            customer_id,
            article_id,
            price,
            sales_channel_id,
            -- H&M does not document the channel codes; 2 is widely treated as online.
            CASE sales_channel_id WHEN 2 THEN 'Online' ELSE 'Store' END AS channel,
            date_trunc('week', t_dat)::DATE AS week_start,
            date_trunc('month', t_dat)::DATE AS month_start,
            weekofyear(t_dat) AS week_of_year,
            season_start,
            CASE month(season_start)
                WHEN 3 THEN 'Spring ' || year(season_start)
                WHEN 6 THEN 'Summer ' || year(season_start)
                WHEN 9 THEN 'Autumn ' || year(season_start)
                ELSE 'Winter ' || year(season_start) || '/' || right((year(season_start) + 1)::VARCHAR, 2)
            END AS season_label,
            CASE
                WHEN t_dat BETWEEN DATE '{y1_start}' AND DATE '{y2_start - dt.timedelta(days=1)}' THEN 'Y1'
                WHEN t_dat BETWEEN DATE '{y2_start}' AND DATE '{last_full}' THEN 'Y2'
            END AS analysis_year,
            t_dat BETWEEN DATE '{first_full}' AND DATE '{last_full}' AS in_full_week
        FROM base
        ORDER BY t_dat
    """)
    con.execute("DROP TABLE raw_transactions")

    print("Building summary tables ...")
    run_sql_file(con, ROOT / "sql" / "00_build_tables.sql")

    counts = con.execute("""
        SELECT (SELECT count(*) FROM transactions), (SELECT count(*) FROM customer_summary),
               (SELECT count(*) FROM article_summary)
    """).fetchone()
    print(f"Done: {counts[0]:,} transactions, {counts[1]:,} purchasing customers, {counts[2]:,} articles sold -> {args.db}")
    con.close()


if __name__ == "__main__":
    main()
