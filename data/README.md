# Data

The raw data is not included in this repository (it is ~3.5 GB and covered by Kaggle's
competition terms).

## Download

1. Sign in to Kaggle and open
   <https://www.kaggle.com/competitions/h-and-m-personalized-fashion-recommendations/data>
2. Accept the competition rules (required before downloading).
3. Download only these three files (skip the `images/` folder, which is ~30 GB):
   - `articles.csv`
   - `customers.csv`
   - `transactions_train.csv`
4. Put them in `data/raw/`:

```
data/raw/articles.csv
data/raw/customers.csv
data/raw/transactions_train.csv
```

Then run `python scripts/build_database.py`, which creates `data/hm.duckdb` (~2–3 GB).

## Low-memory laptops

`python scripts/build_database.py --customer-pct 20` keeps a random 20% of customers (with
all of their purchases), which makes every step roughly 5× faster. Percentages and shares
stay representative; counts will be about 20% of the full totals.
