"""Giornata sintetica usata da più test: ON piatto a 100, RTH con una rottura sotto 100 alle 10:00 e rientro alle 10:05."""
import datetime as dt

import pandas as pd


def bars(start_utc, n, low, high, close, vol=1.0):
    idx = pd.date_range(start_utc, periods=n, freq="1min", tz="UTC")
    return pd.DataFrame({"open": close, "high": high, "low": low, "close": close, "volume": vol}, index=idx)


def day():
    on = bars("2026-03-09 22:00", 600, 100, 100, 100)                 # 18:00 -> 03:59 NY (EDT)
    a = bars("2026-03-10 13:30", 30, 100, 101, 100.5, vol=2.0)        # 09:30-09:59
    b = bars("2026-03-10 14:00", 5, 95, 96, 96, vol=3.0)              # 10:00-10:04: rottura sotto 100
    c = bars("2026-03-10 14:05", 355, 100, 100, 100, vol=1.0)         # 10:05-15:59: rientro e piatto
    return pd.concat([on, a, b, c])


def event_row(side="long"):
    """Riga di events.parquet (dict) coerente con day(): VA di riferimento 90/100/110."""
    common = dict(va_type="ON", session_date=dt.date(2026, 3, 10),
                  break_ts=pd.Timestamp("2026-03-10 14:00", tz="UTC"), reentry_ts=pd.Timestamp("2026-03-10 14:10", tz="UTC"),
                  vah_break=110.0, val_break=90.0, poc_break=100.0, vah_reentry=110.0, val_reentry=90.0, poc_reentry=100.0,
                  bars_outside=1, excursion_minutes=10)
    if side == "long":
        return common | dict(side="long", extreme_price=85.0, entry_ref_price=95.0, stop_price=84.75, target_price=110.0)
    return common | dict(side="short", extreme_price=115.0, entry_ref_price=105.0, stop_price=115.25, target_price=90.0)
