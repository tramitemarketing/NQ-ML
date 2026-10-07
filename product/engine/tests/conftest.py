"""Mercati e strategie sintetici per i test (nessun dato reale)."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

NY = "America/New_York"


def rth_market(n_days: int = 750, seed: int = 0, edge: float = 0.0, sigma: float = 1.0):
    """Barre da 1 minuto 09:30-15:59 NY (tipo azioni: buco notturno). Se edge > 0, ogni giorno ha un
    segno s = +-1 e fra le 10:00 e le 10:59 il prezzo deriva di s*edge punti in totale (vantaggio piantato).
    Restituisce (bars, segni per giorno)."""
    rng = np.random.default_rng(seed)
    days = pd.bdate_range("2017-01-02", periods=n_days)
    mins = np.arange(390)
    sig = rng.choice([-1, 1], size=n_days)
    inc = rng.normal(0, sigma, size=(n_days, 390))
    win = (mins >= 30) & (mins < 90)
    inc[:, win] += (sig[:, None] * edge / win.sum())
    gaps = rng.normal(0, 5 * sigma, n_days)
    close = 5000 + np.cumsum((inc + np.where(mins == 0, 1, 0)[None, :] * gaps[:, None]).ravel())
    opn = np.concatenate([[5000.0], close[:-1]])
    # all'apertura del giorno l'open include il gap
    first = np.arange(n_days) * 390
    opn[first] = close[first] - inc.ravel()[first]
    hi = np.maximum(opn, close) + np.abs(rng.normal(0, 0.3 * sigma, close.size))
    lo = np.minimum(opn, close) - np.abs(rng.normal(0, 0.3 * sigma, close.size))
    local = (np.repeat(days.values, 390) + np.tile(pd.to_timedelta(570 + mins, unit="min").values, n_days))
    idx = pd.DatetimeIndex(local).tz_localize(NY).tz_convert("UTC")
    bars = pd.DataFrame({"open": opn, "high": hi, "low": lo, "close": close,
                         "volume": rng.integers(100, 1000, close.size).astype(float)}, index=idx)
    return bars, pd.Series(sig, index=days)


def futures_market(n_days: int = 500, seed: int = 1, night_drift: float = 0.0, sigma: float = 2.0):
    """Barre da 5 minuti, sessione 18:00 (sera prima) -> 16:55 NY, tipo future. `night_drift`: punti
    medi guadagnati fra le 18:00 e le 09:30 (il mercato sale di notte)."""
    rng = np.random.default_rng(seed)
    days = pd.bdate_range("2016-01-04", periods=n_days)
    rel = np.arange(0, 23 * 60, 5)                      # minuti dalle 18:00
    nb = len(rel)
    night = rel < (15 * 60 + 30)                        # 18:00 -> 09:30
    inc = rng.normal(0, sigma, size=(n_days, nb))
    inc[:, night] += night_drift / night.sum()
    close = 10000 + np.cumsum(inc.ravel())
    opn = np.concatenate([[10000.0], close[:-1]])
    hi = np.maximum(opn, close) + 0.25
    lo = np.minimum(opn, close) - 0.25
    base = np.repeat((days - pd.Timedelta(days=1)).values, nb) + np.tile(
        pd.to_timedelta(18 * 60 + rel, unit="min").values, n_days)
    idx = pd.DatetimeIndex(base).tz_localize(NY, ambiguous="NaT", nonexistent="NaT")
    ok = ~idx.isna()
    bars = pd.DataFrame({"open": opn, "high": hi, "low": lo, "close": close, "volume": 100.0}, index=idx)[ok]
    bars.index = bars.index.tz_convert("UTC")
    return bars


def price_at(bars: pd.DataFrame, ts_local: pd.Series) -> np.ndarray:
    """Open della prima barra >= ts (come il motore)."""
    t = pd.DatetimeIndex(ts_local).tz_localize(NY).tz_convert("UTC")
    k = np.clip(bars.index.searchsorted(t), 0, len(bars) - 1)
    return bars["open"].to_numpy()[k]


def make_trades(bars, entries_local, exits_local, sides) -> pd.DataFrame:
    e = pd.Series(pd.DatetimeIndex(entries_local))
    x = pd.Series(pd.DatetimeIndex(exits_local))
    sides = np.asarray(sides)
    pnl = sides * (price_at(bars, x) - price_at(bars, e))
    return pd.DataFrame({"entry_time": e.dt.strftime("%Y-%m-%d %H:%M"), "exit_time": x.dt.strftime("%Y-%m-%d %H:%M"),
                         "side": np.where(sides > 0, "long", "short"), "pnl_points": pnl.round(2)})


@pytest.fixture(scope="session")
def edge_case():
    bars, sig = rth_market(n_days=750, seed=3, edge=4.0)
    d = sig.index
    tr = make_trades(bars, d + pd.Timedelta(hours=10), d + pd.Timedelta(hours=11), sig.to_numpy())
    return bars, tr


@pytest.fixture(scope="session")
def random_case():
    bars, _ = rth_market(n_days=750, seed=5, edge=0.0)
    rng = np.random.default_rng(11)
    d = bars.index.tz_convert(NY).tz_localize(None).normalize().unique()
    d = d[rng.random(len(d)) < 0.7]
    start = pd.to_timedelta(rng.integers(600, 900, len(d)), unit="min")
    dur = pd.to_timedelta(rng.integers(15, 90, len(d)), unit="min")
    tr = make_trades(bars, d + start, d + start + dur, rng.choice([-1, 1], len(d)))
    return bars, tr


@pytest.fixture(scope="session")
def beta_case():
    bars = futures_market(n_days=500, seed=2, night_drift=25.0)
    rng = np.random.default_rng(4)
    sess = pd.bdate_range("2016-01-04", periods=500)
    sess = sess[1:-1][rng.random(498) < 0.6]
    entries = sess - pd.Timedelta(hours=6)          # 18:00 della sera prima
    exits = sess + pd.Timedelta(hours=9, minutes=30)
    tr = make_trades(bars, entries, exits, np.ones(len(sess), int))
    return bars, tr
