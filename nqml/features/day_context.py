"""Ciò che una feature può sapere alla chiusura di una barra 5m: barre, profili, ATR, volume cumulato.
Costruito solo dalle barre fino a `upto` (escluso): il no-lookahead è una proprietà del costruttore."""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from nqml.data.bars import OHLCV, five_min_bin, resample_5m, rth_bars
from nqml.profile.sessions import on_mask, session_date
from nqml.profile.volume_profile import ValueArea, VolumeProfile

FIVE_MIN = pd.Timedelta(minutes=5)


@dataclass
class DayContext:
    session_date: dt.date
    bars1m: pd.DataFrame
    rth1m: pd.DataFrame
    bars5: pd.DataFrame
    on_va: ValueArea | None
    n_on_bars: int
    dev_va_at_close: dict = field(default_factory=dict)
    rth_open_price: float | None = None
    trades: pd.DataFrame | None = None


def _true_range(b5: pd.DataFrame) -> pd.Series:
    prev_close = b5["close"].shift(1)
    tr = pd.concat([
        b5["high"] - b5["low"],
        (b5["high"] - prev_close).abs(),
        (b5["low"] - prev_close).abs(),
    ], axis=1).max(axis=1)
    return tr.fillna(b5["high"] - b5["low"])


def build_day_context(bars1m_day: pd.DataFrame, cfg: dict,
                      prev_tail5: pd.DataFrame | None = None,
                      upto: pd.Timestamp | None = None,
                      trades: pd.DataFrame | None = None) -> DayContext:
    s = cfg["sessions"]
    tick = cfg["instrument"]["tick_size"]
    pct = cfg["detector"]["value_area_pct"]
    period = cfg["features"]["atr_period_5m"]

    bars = bars1m_day if upto is None else bars1m_day.loc[bars1m_day.index < upto]
    sd = session_date(bars.index)[0] if len(bars) else None

    on_bars = bars.loc[on_mask(bars.index, s["on_open"], s["rth_open"])]
    on = VolumeProfile(tick)
    on.add_bars(on_bars)
    on_va = on.value_area(pct)

    rth = rth_bars(bars, s["rth_open"], s["rth_close"])
    rth_open_price = float(rth["open"].iloc[0]) if len(rth) else None

    if len(rth):
        b5 = resample_5m(rth)
        tail = prev_tail5[["open", "high", "low", "close", "volume", "n_1m"]] if prev_tail5 is not None and len(prev_tail5) else None
        both = pd.concat([tail, b5]) if tail is not None else b5
        tr = _true_range(both)
        atr = tr.rolling(period, min_periods=1).mean()
        b5 = b5.copy()
        b5["ts_close"] = b5.index + FIVE_MIN
        b5["atr"] = atr.loc[b5.index].to_numpy()
        b5["cum_vol"] = b5["volume"].cumsum()
        dev = VolumeProfile(tick)
        dev_at_close: dict = {}
        groups = {ts: g for ts, g in rth.groupby(five_min_bin(rth.index))}
        for ts_open, ts_close in zip(b5.index, b5["ts_close"]):
            dev.add_bars(groups[ts_open])
            dev_at_close[ts_close] = dev.value_area(pct)
    else:
        b5 = pd.DataFrame(columns=["open", "high", "low", "close", "volume", "n_1m", "ts_close", "atr", "cum_vol"])
        dev_at_close = {}

    tr = trades
    if tr is not None and upto is not None:
        tr = tr.loc[tr.index < upto]

    return DayContext(session_date=sd, bars1m=bars, rth1m=rth[OHLCV],
                      bars5=b5, on_va=on_va, n_on_bars=int(len(on_bars)),
                      dev_va_at_close=dev_at_close, rth_open_price=rth_open_price,
                      trades=tr)


def dev_va_lookup(ctx: DayContext, ts_close: pd.Timestamp) -> ValueArea | None:
    return ctx.dev_va_at_close.get(ts_close)


def bars5_upto(ctx: DayContext, ts_close: pd.Timestamp) -> pd.DataFrame:
    return ctx.bars5.loc[ctx.bars5["ts_close"] <= ts_close]
