"""Campionamento stratificato dei giorni (spec §12-bis): quota costante per mese, seed fisso, regola di budget."""
from __future__ import annotations

import datetime as dt

import numpy as np
import pandas as pd


def month_key(d: dt.date) -> str:
    return f"{d.year:04d}-{d.month:02d}"


def sample_days(valid_days: list[dt.date], fraction: float, seed: int, start: dt.date, end_exclusive: dt.date) -> pd.DataFrame:
    pop = sorted(d for d in valid_days if start <= d < end_exclusive)
    rng = np.random.default_rng(seed)
    rows: list[dict] = []
    by_month: dict[str, list[dt.date]] = {}
    for d in pop:
        by_month.setdefault(month_key(d), []).append(d)
    for m in sorted(by_month):
        days = by_month[m]
        n_sel = max(1, int(round(fraction * len(days))))
        chosen = sorted(rng.choice(np.array(days, dtype=object), size=n_sel, replace=False).tolist())
        rows += [dict(session_date=d, month=m, n_valid_in_month=len(days), n_selected_in_month=n_sel) for d in chosen]
    return pd.DataFrame(rows, columns=["session_date", "month", "n_valid_in_month", "n_selected_in_month"])


def budget_fraction(fraction: float, cost_usd: float, budget_usd: float) -> float:
    return fraction if cost_usd <= budget_usd else round(fraction * budget_usd / cost_usd, 3)
