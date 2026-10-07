"""Walk-forward a finestra espandente con embargo e cassaforte (spec §9.1, §11.2)."""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class Fold:
    k: int
    train_start: dt.date
    fit_end: dt.date
    val_start: dt.date
    val_end: dt.date
    test_start: dt.date
    test_end: dt.date


def _d(s: str) -> dt.date:
    return dt.date.fromisoformat(s)


def _dates_of(df: pd.DataFrame) -> pd.Series:
    return pd.to_datetime(df["session_date"]).dt.date


def trading_dates(days: pd.DataFrame, cfg: dict) -> list[dt.date]:
    vault = _d(cfg["vault"]["start"])
    d = _dates_of(days[days["valid"]])
    return sorted(x for x in set(d) if x < vault)


def make_folds(dates: list[dt.date], cfg: dict) -> list[Fold]:
    wf = cfg["walkforward"]
    train_start = _d(wf["train_start"])
    folds: list[Fold] = []
    for k, (ws, we) in enumerate(wf["test_windows"]):
        ws, we = _d(ws), _d(we)
        in_win = [x for x in dates if ws <= x <= we]
        if not in_win:
            raise ValueError(f"nessun giorno di trading nella finestra {ws}..{we}")
        test_start, test_end = in_win[0], in_win[-1]
        i = dates.index(test_start)
        val_end = dates[i - 1 - wf["embargo_trading_days"]]
        val_start = (pd.Timestamp(val_end) - pd.DateOffset(months=wf["val_months"]) + pd.Timedelta(days=1)).date()
        fit_end = max(x for x in dates if x < val_start)
        folds.append(Fold(k, train_start, fit_end, val_start, val_end, test_start, test_end))
    return folds


def fold_slices(df: pd.DataFrame, fold: Fold) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    d = _dates_of(df)
    fit = df[(d >= fold.train_start) & (d <= fold.fit_end)]
    val = df[(d >= fold.val_start) & (d <= fold.val_end)]
    test = df[(d >= fold.test_start) & (d <= fold.test_end)]
    return fit, val, test


def assert_no_vault(df: pd.DataFrame, cfg: dict) -> None:
    vault = _d(cfg["vault"]["start"])
    if (_dates_of(df) >= vault).any():
        raise ValueError(f"cassaforte violata: righe con session_date >= {vault}")
