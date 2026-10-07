"""Compone una giornata: profilo ON fisso, profilo DEV in sviluppo, 4 macchine, filtro ultimo ingresso."""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

import pandas as pd

from nqml.data.bars import five_min_bin, resample_5m, rth_bars
from nqml.detector.events import Bar5m, Event
from nqml.detector.state_machine import SetupDetector
from nqml.profile.sessions import NY, _hm, ny_minutes, on_mask
from nqml.profile.volume_profile import ValueArea, VolumeProfile


@dataclass
class DayResult:
    session_date: dt.date
    n_rth_bars: int
    valid: bool
    on_va: ValueArea | None
    events: list[Event]


def entry_allowed(entry_ts_utc: pd.Timestamp, last_entry: str = "15:30") -> bool:
    return int(ny_minutes(pd.DatetimeIndex([entry_ts_utc]))[0]) <= _hm(last_entry)


def make_event_id(session_date: dt.date, va_type: str, side: str, reentry_ts_utc: pd.Timestamp) -> str:
    hhmm = reentry_ts_utc.tz_convert(NY).strftime("%H%M")
    return f"{session_date:%Y%m%d}-{va_type}-{side}-{hhmm}"


def run_day(bars1m_day: pd.DataFrame, session_date: dt.date, cfg: dict) -> DayResult:
    tick = cfg["instrument"]["tick_size"]
    pct = cfg["detector"]["value_area_pct"]
    max_min = cfg["detector"]["max_excursion_minutes"]
    last_entry = cfg["detector"]["last_entry"]
    rth_open = cfg["sessions"]["rth_open"]
    rth_close = cfg["sessions"]["rth_close"]
    on_open = cfg["sessions"]["on_open"]

    on = VolumeProfile(tick)
    on.add_bars(bars1m_day.loc[on_mask(bars1m_day.index, on_open, rth_open)])
    on_va = on.value_area(pct)

    rth = rth_bars(bars1m_day, rth_open, rth_close)
    n_rth = len(rth)
    if n_rth < cfg["sessions"]["min_rth_bars"]:
        return DayResult(session_date, n_rth, False, on_va, [])

    bars5 = resample_5m(rth)
    groups = {ts: g for ts, g in rth.groupby(five_min_bin(rth.index))}
    machines = [
        SetupDetector(va_type, side, max_min, tick)
        for va_type in ("ON", "DEV") for side in ("long", "short")
    ]
    dev = VolumeProfile(tick)
    events: list[Event] = []
    rows = list(bars5.itertuples())
    for i, r in enumerate(rows):
        dev.add_bars(groups[r.Index])
        dev_va = dev.value_area(pct)
        bar = Bar5m(r.Index, r.open, r.high, r.low, r.close, r.volume)
        for m in machines:
            det = m.on_bar(bar, on_va if m.va_type == "ON" else dev_va)
            if det is None or i + 1 >= len(rows):
                continue
            nxt = rows[i + 1]
            if not entry_allowed(nxt.Index, last_entry):
                continue
            events.append(Event(
                **det.__dict__,
                event_id=make_event_id(session_date, det.va_type, det.side, det.reentry_ts),
                session_date=session_date,
                entry_ts=nxt.Index,
                entry_price=float(nxt.open),
            ))
    return DayResult(session_date, n_rth, True, on_va, events)
