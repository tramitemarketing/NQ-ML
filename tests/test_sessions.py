import datetime as dt

import pandas as pd

from nqml.profile.sessions import on_mask, rth_mask, rth_open_utc, session_date, ny_minutes


def test_rth_open_utc_summer_dst():
    # 2026-03-08 inizia l'ora legale USA: 09:30 NY = 13:30 UTC
    assert rth_open_utc(dt.date(2026, 3, 10)) == pd.Timestamp("2026-03-10 13:30", tz="UTC")


def test_rth_open_utc_winter_standard_time():
    # 2026-11-01 finisce l'ora legale USA: 09:30 NY = 14:30 UTC
    assert rth_open_utc(dt.date(2026, 11, 3)) == pd.Timestamp("2026-11-03 14:30", tz="UTC")


def test_session_date_evening_belongs_to_next_day():
    idx = pd.DatetimeIndex([
        "2026-03-09 22:00",  # lun 18:00 NY -> sessione di mar 10
        "2026-03-10 13:30",  # mar 09:30 NY -> mar 10
        "2026-03-10 20:59",  # mar 16:59 NY -> mar 10
        "2026-03-08 22:00",  # dom 18:00 NY -> lun 9
    ], tz="UTC")
    assert list(session_date(idx)) == [
        dt.date(2026, 3, 10), dt.date(2026, 3, 10), dt.date(2026, 3, 10), dt.date(2026, 3, 9),
    ]


def test_rth_and_on_masks():
    idx = pd.DatetimeIndex([
        "2026-03-10 13:29",  # 09:29 NY: ON
        "2026-03-10 13:30",  # 09:30 NY: RTH
        "2026-03-10 19:59",  # 15:59 NY: RTH
        "2026-03-10 20:00",  # 16:00 NY: nessuna delle due
        "2026-03-09 22:00",  # 18:00 NY: ON
        "2026-03-09 21:59",  # 17:59 NY: manutenzione, nessuna
    ], tz="UTC")
    assert list(rth_mask(idx)) == [False, True, True, False, False, False]
    assert list(on_mask(idx)) == [True, False, False, False, True, False]


def test_ny_minutes():
    idx = pd.DatetimeIndex(["2026-03-10 13:30", "2026-03-10 19:55"], tz="UTC")
    assert list(ny_minutes(idx)) == [9 * 60 + 30, 15 * 60 + 55]
