import datetime as dt

import pandas as pd

from nqml.detector.events import Bar5m, Event, event_to_row
from nqml.detector.state_machine import SetupDetector
from nqml.profile.volume_profile import ValueArea

VA = ValueArea(poc=100.0, vah=110.0, val=90.0, total_volume=1.0, n_levels=81)


def bar(hhmm: str, o: float, h: float, l: float, c: float) -> Bar5m:
    return Bar5m(pd.Timestamp(f"2026-03-10 {hhmm}", tz="UTC"), o, h, l, c, 1.0)


def run(det, bars, vas=None):
    vas = vas or [VA] * len(bars)
    return [det.on_bar(b, v) for b, v in zip(bars, vas)]


def test_long_break_and_reentry_emits_detection():
    det = SetupDetector("ON", "long", 90, 0.25)
    out = run(det, [
        bar("10:00", 95, 96, 94, 95),   # dentro
        bar("10:05", 95, 95, 84, 85),   # rottura sotto VAL
        bar("10:10", 85, 89, 83, 88),   # ancora fuori, nuovo low 83
        bar("10:15", 88, 93, 86, 92),   # rientro
    ])
    assert out[:3] == [None, None, None]
    d = out[3]
    assert d.side == "long" and d.va_type == "ON"
    assert d.break_ts == pd.Timestamp("2026-03-10 10:05", tz="UTC")
    assert d.reentry_ts == pd.Timestamp("2026-03-10 10:20", tz="UTC")
    assert d.extreme_price == 83 and d.stop_price == 82.75 and d.target_price == 110
    assert d.entry_ref_price == 92 and d.bars_outside == 2 and d.excursion_minutes == 15
    assert d.va_break == VA and d.va_reentry == VA
    assert det.state == "INSIDE"


def test_short_is_the_mirror_image():
    det = SetupDetector("DEV", "short", 90, 0.25)
    out = run(det, [
        bar("10:00", 105, 106, 104, 105),
        bar("10:05", 105, 116, 105, 115),  # rottura sopra VAH
        bar("10:10", 115, 117, 111, 112),  # nuovo high 117
        bar("10:15", 112, 114, 107, 108),  # rientro
    ])
    d = out[3]
    assert d.side == "short" and d.extreme_price == 117
    assert d.stop_price == 117.25 and d.target_price == 90 and d.bars_outside == 2


def test_timeout_goes_exhausted_and_rearms_only_after_close_inside():
    det = SetupDetector("ON", "long", 90, 0.25)
    bars = [bar("10:00", 85, 86, 84, 85)]                      # rottura alle 10:00
    t = pd.Timestamp("2026-03-10 10:05", tz="UTC")
    while t <= pd.Timestamp("2026-03-10 11:25", tz="UTC"):     # fuori fino alla barra 11:25 (chiude 11:30 = 90 min)
        bars.append(Bar5m(t, 85, 86, 84, 85, 1.0)); t += pd.Timedelta(minutes=5)
    out = run(det, bars)
    assert all(o is None for o in out) and det.state == "BROKEN"
    assert det.on_bar(bar("11:30", 85, 86, 84, 85), VA) is None and det.state == "EXHAUSTED"   # 95 min
    assert det.on_bar(bar("11:35", 85, 95, 85, 95), VA) is None and det.state == "INSIDE"      # riarmo, nessun evento
    assert det.on_bar(bar("11:40", 95, 95, 85, 86), VA) is None and det.state == "BROKEN"
    d = det.on_bar(bar("11:45", 86, 96, 86, 95), VA)
    assert d is not None and d.break_ts == pd.Timestamp("2026-03-10 11:40", tz="UTC")


def test_exhausted_rearms_on_close_beyond_opposite_edge_too():
    det = SetupDetector("ON", "long", 90, 0.25)
    bars = [bar("10:00", 85, 86, 84, 85)]                      # rottura alle 10:00
    t = pd.Timestamp("2026-03-10 10:05", tz="UTC")
    while t <= pd.Timestamp("2026-03-10 11:25", tz="UTC"):     # fuori fino alla barra 11:25 (chiude 11:30 = 90 min)
        bars.append(Bar5m(t, 85, 86, 84, 85, 1.0)); t += pd.Timedelta(minutes=5)
    run(det, bars)
    assert det.on_bar(bar("11:30", 85, 86, 84, 85), VA) is None and det.state == "EXHAUSTED"   # 95 min
    # chiude sopra il bordo opposto VAH=110: riarmo permissivo, nessun evento (spec §5)
    assert det.on_bar(bar("11:35", 105, 115, 105, 112), VA) is None and det.state == "INSIDE"
    # da INSIDE, una chiusura sotto VAL=90 e' una nuova rottura
    assert det.on_bar(bar("11:40", 112, 112, 89, 89), VA) is None and det.state == "BROKEN"


def test_reentry_bar_that_exceeds_timeout_emits_nothing():
    det = SetupDetector("ON", "long", 90, 0.25)
    bars = [bar("10:00", 85, 86, 84, 85)]
    t = pd.Timestamp("2026-03-10 10:05", tz="UTC")
    while t <= pd.Timestamp("2026-03-10 11:25", tz="UTC"):
        bars.append(Bar5m(t, 85, 86, 84, 85, 1.0)); t += pd.Timedelta(minutes=5)
    run(det, bars)
    assert det.on_bar(bar("11:30", 85, 96, 85, 95), VA) is None   # rientra ma 95 > 90
    assert det.state == "EXHAUSTED"


def test_never_reenters_emits_nothing():
    det = SetupDetector("ON", "long", 90, 0.25)
    out = run(det, [bar("10:00", 85, 86, 84, 85), bar("10:05", 85, 86, 83, 84)])
    assert out == [None, None]


def test_dev_va_moving_to_include_price_still_emits_with_shift_recorded():
    det = SetupDetector("DEV", "long", 90, 0.25)
    va1 = ValueArea(poc=100.0, vah=110.0, val=90.0, total_volume=1.0, n_levels=81)
    va2 = ValueArea(poc=95.0, vah=108.0, val=84.0, total_volume=1.0, n_levels=97)
    out = run(det, [bar("10:00", 85, 86, 84, 85), bar("10:05", 85, 86, 84, 85)], [va1, va2])
    d = out[1]
    assert d is not None and d.va_break == va1 and d.va_reentry == va2 and d.target_price == 108


def test_crossing_the_whole_va_resets_without_event():
    det = SetupDetector("ON", "long", 90, 0.25)
    out = run(det, [
        bar("10:00", 85, 86, 84, 85),     # rottura sotto
        bar("10:05", 85, 115, 85, 112),   # chiude sopra VAH: attraversata tutta
        bar("10:10", 112, 112, 100, 100), # dentro: nessun evento
    ])
    assert out == [None, None, None] and det.state == "INSIDE"


def test_none_value_area_is_ignored():
    det = SetupDetector("DEV", "long", 90, 0.25)
    assert det.on_bar(bar("10:00", 85, 86, 84, 85), None) is None and det.state == "INSIDE"


def test_event_and_event_to_row_flatten_value_areas():
    det = SetupDetector("ON", "long", 90, 0.25)
    out = run(det, [
        bar("10:00", 95, 96, 94, 95),   # dentro
        bar("10:05", 95, 95, 84, 85),   # rottura sotto VAL
        bar("10:10", 85, 89, 83, 88),   # ancora fuori, nuovo low 83
        bar("10:15", 88, 93, 86, 92),   # rientro
    ])
    d = out[3]
    e = Event(
        **d.__dict__,
        event_id="20260310-ON-long-1020",
        session_date=dt.date(2026, 3, 10),
        entry_ts=pd.Timestamp("2026-03-10 10:20", tz="UTC"),
        entry_price=92.5,
    )
    row = event_to_row(e)
    assert row["vah_break"] == VA.vah and row["val_break"] == VA.val and row["poc_break"] == VA.poc
    assert row["vah_reentry"] == VA.vah and row["val_reentry"] == VA.val and row["poc_reentry"] == VA.poc
    assert row["n_levels_break"] == VA.n_levels and row["total_volume_break"] == VA.total_volume
    assert row["n_levels_reentry"] == VA.n_levels and row["total_volume_reentry"] == VA.total_volume
    assert "va_break" not in row and "va_reentry" not in row
    assert row["event_id"] == "20260310-ON-long-1020"
    assert row["session_date"] == dt.date(2026, 3, 10)
    assert row["entry_ts"] == pd.Timestamp("2026-03-10 10:20", tz="UTC")
    assert row["entry_price"] == 92.5
    assert row["reentry_ts"] == d.reentry_ts
    assert row["stop_price"] == d.stop_price
    assert row["target_price"] == d.target_price


def test_extreme_includes_the_reentry_bar_long():
    det = SetupDetector("ON", "long", 90, 0.25)
    out = run(det, [
        bar("10:00", 95, 95, 84, 85),   # rottura, extremo provvisorio 84
        bar("10:05", 85, 96, 80, 95),   # rientro: nuovo low 80 sulla barra stessa
    ])
    d = out[1]
    assert d is not None
    assert d.extreme_price == 80 and d.stop_price == 79.75


def test_extreme_includes_the_reentry_bar_short():
    det = SetupDetector("DEV", "short", 90, 0.25)
    out = run(det, [
        bar("10:00", 105, 116, 105, 115),  # rottura sopra VAH, estremo provvisorio 116
        bar("10:05", 115, 120, 104, 100),  # rientro: nuovo high 120 sulla barra stessa
    ])
    d = out[1]
    assert d is not None
    assert d.extreme_price == 120 and d.stop_price == 120.25
