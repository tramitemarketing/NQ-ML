"""Sessioni CME per NQ, calcolate in ora di New York. Unico modulo che conosce il fuso."""
from __future__ import annotations

import datetime as dt
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

NY = ZoneInfo("America/New_York")


def _hm(s: str) -> int:
    h, m = s.split(":")
    return int(h) * 60 + int(m)


def to_ny(idx: pd.DatetimeIndex) -> pd.DatetimeIndex:
    return idx.tz_convert(NY)


def ny_minutes(idx_utc: pd.DatetimeIndex) -> np.ndarray:
    ny = to_ny(idx_utc)
    return (ny.hour * 60 + ny.minute).to_numpy()


def rth_mask(idx_utc: pd.DatetimeIndex, rth_open: str = "09:30", rth_close: str = "16:00") -> np.ndarray:
    m = ny_minutes(idx_utc)
    return (m >= _hm(rth_open)) & (m < _hm(rth_close))


def on_mask(idx_utc: pd.DatetimeIndex, on_open: str = "18:00", rth_open: str = "09:30") -> np.ndarray:
    m = ny_minutes(idx_utc)
    return (m >= _hm(on_open)) | (m < _hm(rth_open))


def session_date(idx_utc: pd.DatetimeIndex) -> pd.Index:
    """Data della sessione RTH a cui la barra appartiene: le barre dalle 17:00 NY in poi
    contano per il giorno dopo (la domenica sera appartiene al lunedì).
    17:00 è fisso: è la chiusura Globex/CME, non un parametro di strategia (non configurabile)."""
    ny = to_ny(idx_utc)
    shift = (ny.hour >= 17).astype(int)
    shifted = ny.tz_localize(None).normalize() + pd.to_timedelta(shift, unit="D")
    return pd.Index(shifted.date)


def rth_open_utc(date: dt.date, rth_open: str = "09:30") -> pd.Timestamp:
    h, m = rth_open.split(":")
    local = pd.Timestamp(dt.datetime(date.year, date.month, date.day, int(h), int(m)), tz=NY)
    return local.tz_convert("UTC")
