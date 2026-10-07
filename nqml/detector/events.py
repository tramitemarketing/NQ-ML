"""Tipi del detector: barra 5m in ingresso, rilevazione (senza ingresso) ed evento completo."""
from __future__ import annotations

import datetime as dt
from dataclasses import asdict, dataclass
from typing import NamedTuple

import pandas as pd

from nqml.profile.volume_profile import ValueArea


class Bar5m(NamedTuple):
    ts_open: pd.Timestamp
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass(frozen=True)
class Detection:
    va_type: str
    side: str
    break_ts: pd.Timestamp        # open della barra 5m di rottura
    reentry_ts: pd.Timestamp      # CHIUSURA della barra 5m di rientro (istante della decisione)
    extreme_price: float
    va_break: ValueArea
    va_reentry: ValueArea
    entry_ref_price: float        # close della barra di rientro
    stop_price: float
    target_price: float
    bars_outside: int
    excursion_minutes: int


@dataclass(frozen=True, kw_only=True)
class Event(Detection):
    event_id: str
    session_date: dt.date
    entry_ts: pd.Timestamp   # open della barra 5m successiva
    entry_price: float       # open di quella barra, senza slippage


def event_to_row(e: Event) -> dict:
    row = asdict(e)
    for name in ("va_break", "va_reentry"):
        va = row.pop(name)
        suffix = name.split("_")[1]
        row[f"vah_{suffix}"] = va["vah"]
        row[f"val_{suffix}"] = va["val"]
        row[f"poc_{suffix}"] = va["poc"]
        row[f"n_levels_{suffix}"] = va["n_levels"]
        row[f"total_volume_{suffix}"] = va["total_volume"]
    return row
