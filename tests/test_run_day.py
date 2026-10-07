import datetime as dt

import pandas as pd

from nqml.config import load_config
from nqml.detector.run_day import entry_allowed, make_event_id, run_day


def _bars(start_utc: str, n: int, low: float, high: float, close: float, vol: float = 1.0):
    idx = pd.date_range(start_utc, periods=n, freq="1min", tz="UTC")
    return pd.DataFrame({"open": close, "high": high, "low": low, "close": close, "volume": vol}, index=idx)


def _synthetic_day():
    """ON piatto a 100 (VA = 100/100/100). RTH: 30 min a 100, 5 min a 95-96, poi 100 fino alle 15:59."""
    on = _bars("2026-03-09 22:00", 10 * 60 + 30, 100, 100, 100)            # 18:00 -> 04:29 NY (EDT = UTC-4), basta per il profilo
    rth_a = _bars("2026-03-10 13:30", 30, 100, 100, 100)                    # 09:30-09:59
    rth_b = _bars("2026-03-10 14:00", 5, 95, 96, 96)                        # 10:00-10:04: rottura sotto 100
    rth_c = _bars("2026-03-10 14:05", 390 - 35, 100, 100, 100)              # 10:05-15:59: rientro e piatto
    return pd.concat([on, rth_a, rth_b, rth_c])


def test_on_long_event_from_synthetic_day():
    cfg = load_config("config.yaml")
    res = run_day(_synthetic_day(), dt.date(2026, 3, 10), cfg)
    assert res.valid and res.n_rth_bars == 390
    assert (res.on_va.poc, res.on_va.vah, res.on_va.val) == (100.0, 100.0, 100.0)
    on_long = [e for e in res.events if e.va_type == "ON" and e.side == "long"]
    assert len(on_long) == 1
    e = on_long[0]
    assert e.break_ts == pd.Timestamp("2026-03-10 14:00", tz="UTC")
    assert e.reentry_ts == pd.Timestamp("2026-03-10 14:10", tz="UTC")
    assert e.entry_ts == pd.Timestamp("2026-03-10 14:10", tz="UTC") and e.entry_price == 100.0
    assert e.extreme_price == 95.0 and e.stop_price == 94.75 and e.target_price == 100.0
    assert e.event_id == "20260310-ON-long-1010" and e.session_date == dt.date(2026, 3, 10)
    assert all(entry_allowed(ev.entry_ts) for ev in res.events)

    # la stessa rottura/rientro produce anche un evento DEV-long (la VA DEV al 10:00 include gia'
    # le barre 95-96 appena aggiunte al profilo in sviluppo).
    assert len(res.events) == 2
    dev = [ev for ev in res.events if ev.va_type == "DEV"]
    assert len(dev) == 1
    d = dev[0]
    assert d.side == "long" and d.break_ts == pd.Timestamp("2026-03-10 14:00", tz="UTC")
    assert d.target_price == 100.0


def test_day_with_too_few_rth_bars_is_invalid():
    cfg = load_config("config.yaml")
    day = _bars("2026-03-10 13:30", 100, 100, 100, 100)
    res = run_day(day, dt.date(2026, 3, 10), cfg)
    assert res.valid is False and res.events == [] and res.n_rth_bars == 100


def test_entry_allowed_cutoff():
    assert entry_allowed(pd.Timestamp("2026-03-10 19:30", tz="UTC"))          # 15:30 NY
    assert not entry_allowed(pd.Timestamp("2026-03-10 19:35", tz="UTC"))      # 15:35 NY


def test_make_event_id_uses_ny_time_of_reentry_close():
    eid = make_event_id(dt.date(2026, 3, 10), "DEV", "short", pd.Timestamp("2026-03-10 14:20", tz="UTC"))
    assert eid == "20260310-DEV-short-1020"
