"""ATR(14) su barre 5m del giorno precedente: l'unita' di misura `A` usata dai candidati 5, 6 e 7 dello
screening (pre-registrazione `docs/superpowers/specs/2026-09-23-screening-candidati-5-8-e-ibridi.md`, §1).
Non reinventa la formula di true range/ATR: riusa `nqml.features.day_context._true_range` (stessa identica
formula usata da `RollingState`/`build_day_context` nella pipeline delle feature) e `nqml.data.bars.resample_5m`.
Qui serve solo il valore di ATR alla CHIUSURA della sessione precedente (non l'evoluzione intra-day che serve a
`build_day_context`), quindi si calcola una serie leggera per giorno invece di costruire un DayContext completo
per ogni candidato."""
from __future__ import annotations

import datetime as dt

import pandas as pd

from nqml.data.bars import resample_5m, rth_bars, sessions_iter
from nqml.features.day_context import _true_range


def previous_day_atr(bars: pd.DataFrame, cfg: dict) -> dict[dt.date, float]:
    """Per ogni giorno valido (>= min_rth_bars barre RTH), l'ATR(14) calcolato sulle barre 5m RTH, in coda
    continua attraverso i giorni (stessa continuita' di RollingState.prev_tail5), preso alla chiusura della
    barra 5m PRECEDENTE quella del giorno stesso: cioe' il valore che il giorno in questione eredita dal
    giorno di trading immediatamente precedente. Il primo giorno valido non ha una voce (nessun giorno prima)."""
    period = cfg["features"]["atr_period_5m"]
    rth_open, rth_close = cfg["sessions"]["rth_open"], cfg["sessions"]["rth_close"]
    min_rth = cfg["sessions"]["min_rth_bars"]

    out: dict[dt.date, float] = {}
    prev_tail: pd.DataFrame | None = None
    last_atr: float | None = None
    for sd, day in sessions_iter(bars):
        day_rth = rth_bars(day, rth_open, rth_close).drop(columns=["session_date"])
        if len(day_rth) < min_rth:
            continue
        if last_atr is not None:
            out[sd] = last_atr
        b5 = resample_5m(day_rth)
        if len(b5) == 0:
            continue
        both = pd.concat([prev_tail, b5]) if prev_tail is not None else b5
        tr = _true_range(both)
        atr = tr.rolling(period, min_periods=1).mean()
        last_atr = float(atr.loc[b5.index[-1]])
        prev_tail = b5.tail(period)
    return out
