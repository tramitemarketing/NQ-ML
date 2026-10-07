import datetime as dt

import pandas as pd

from nqml.tick.sampling import budget_fraction, month_key, sample_days


def _bdays(start, end):
    return [d.date() for d in pd.bdate_range(start, end)]


def test_sample_days_is_stratified_per_month_and_deterministic():
    days = _bdays("2021-09-20", "2021-12-31")           # set 9 gg, ott 21, nov 22, dic 23
    s1 = sample_days(days, 0.45, 0, dt.date(2021, 9, 20), dt.date(2022, 1, 1))
    s2 = sample_days(days, 0.45, 0, dt.date(2021, 9, 20), dt.date(2022, 1, 1))
    assert s1.equals(s2)
    per_month = s1.groupby("month")["session_date"].count().to_dict()
    assert per_month == {"2021-09": 4, "2021-10": 9, "2021-11": 10, "2021-12": 10}   # round(0.45*n), min 1
    assert s1["session_date"].is_monotonic_increasing and s1["session_date"].is_unique
    assert set(s1["session_date"]) <= set(days)
    row = s1[s1["month"] == "2021-10"].iloc[0]
    assert row["n_valid_in_month"] == 21 and row["n_selected_in_month"] == 9


def test_sample_days_respects_range_and_min_one():
    days = _bdays("2021-08-01", "2022-02-28")
    s = sample_days(days, 0.05, 0, dt.date(2021, 9, 20), dt.date(2022, 1, 1))
    assert s["session_date"].min() >= dt.date(2021, 9, 20) and s["session_date"].max() < dt.date(2022, 1, 1)
    assert (s.groupby("month")["session_date"].count() >= 1).all()      # 0.05*9 = 0.45 -> min 1 a settembre


def test_different_seed_changes_sample_but_not_counts():
    days = _bdays("2021-09-20", "2021-12-31")
    a = sample_days(days, 0.45, 0, dt.date(2021, 9, 20), dt.date(2022, 1, 1))
    b = sample_days(days, 0.45, 1, dt.date(2021, 9, 20), dt.date(2022, 1, 1))
    assert len(a) == len(b) and set(a["session_date"]) != set(b["session_date"])


def test_budget_fraction():
    assert budget_fraction(0.45, 90.0, 105.0) == 0.45
    assert budget_fraction(0.45, 140.0, 105.0) == round(0.45 * 105 / 140, 3)
    assert month_key(dt.date(2026, 3, 19)) == "2026-03"
