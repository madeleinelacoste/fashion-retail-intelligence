"""Simple, explainable weekly demand forecasts for the trends notebook.

The goal is a fair comparison of a few methods a merchandise planner could
actually use, scored on the most recent weeks the models never saw.
"""
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression


def wape(actual, predicted):
    """Weighted absolute percentage error: total absolute error / total actual units."""
    actual, predicted = np.asarray(actual, float), np.asarray(predicted, float)
    return np.abs(actual - predicted).sum() / np.abs(actual).sum()


def _features(index, origin, disruption):
    t = np.asarray((index - origin).days / 7.0)
    angle = 2 * np.pi * np.asarray(index.dayofyear) / 365.25
    cols = {"trend": t}
    for k in (1, 2, 3):
        cols[f"sin{k}"] = np.sin(k * angle)
        cols[f"cos{k}"] = np.cos(k * angle)
    if disruption is not None:
        start, end = pd.Timestamp(disruption[0]), pd.Timestamp(disruption[1])
        cols["disruption"] = ((index >= start) & (index <= end)).astype(float)
    return pd.DataFrame(cols, index=index)


def compare_forecasts(series, horizon=12, disruption=None):
    """Hold out the last `horizon` weeks and forecast them four ways.

    series:     weekly units indexed by week start date (Mondays)
    disruption: optional (start, end) dates of a known one-off shock in the
                training data (e.g. COVID store closures) so the regression
                does not mistake it for seasonality or trend.

    Returns (predictions DataFrame, scores DataFrame sorted best first).
    """
    series = series.asfreq("W-MON", fill_value=0).astype(float)
    if len(series) < 52 + horizon + 8:
        raise ValueError("Need at least ~72 weeks of history.")
    train, test = series.iloc[:-horizon], series.iloc[-horizon:]
    last_year = series.shift(52)

    preds = pd.DataFrame({"Actual": test})

    # 1. Same week last year
    preds["Seasonal naive"] = last_year.loc[test.index]

    # 2. Same week last year, scaled by how the latest 8 weeks compare with a year earlier
    recent = train.iloc[-8:].sum()
    recent_last_year = last_year.loc[train.index[-8:]].sum()
    growth = recent / recent_last_year if recent_last_year > 0 else 1.0
    preds["Seasonal naive x recent trend"] = last_year.loc[test.index] * growth

    # 3. Flat average of the latest 8 weeks
    preds["Recent 8-week average"] = train.iloc[-8:].mean()

    # 4. Regression on log units: trend + yearly seasonality (+ disruption flag)
    origin = series.index[0]
    model = LinearRegression().fit(_features(train.index, origin, disruption), np.log1p(train))
    preds["Seasonal regression"] = np.expm1(model.predict(_features(test.index, origin, disruption)))

    scores = pd.DataFrame(
        {"WAPE": {m: wape(test, preds[m]) for m in preds.columns if m != "Actual"}}
    ).sort_values("WAPE")
    return preds, scores
