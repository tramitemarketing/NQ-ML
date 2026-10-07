import datetime as dt
from pathlib import Path

import pandas as pd

from nqml.tick.windows import load_day_trades, merge_intervals, window_path, windows_for_days

T = lambda s: pd.Timestamp(f"2026-03-10 {s}", tz="UTC")


def test_merge_intervals_overlapping_adjacent_and_disjoint():
    out = merge_intervals([(T("14:00"), T("14:10")), (T("14:05"), T("14:20")), (T("14:20"), T("14:25")), (T("15:00"), T("15:10")), (T("13:30"), T("13:40"))])
    assert out == [(T("13:30"), T("13:40")), (T("14:00"), T("14:25")), (T("15:00"), T("15:10"))]


def test_windows_for_days_filters_and_merges():
    ev = pd.DataFrame({
        "event_id": ["a", "b", "c", "d"],
        "session_date": [dt.date(2026, 3, 10)] * 3 + [dt.date(2026, 3, 11)],
        "break_ts": [T("14:00"), T("14:05"), T("15:00"), T("14:00") + pd.Timedelta(days=1)],
        "reentry_ts": [T("14:10"), T("14:20"), T("15:10"), T("14:10") + pd.Timedelta(days=1)],
    })
    sampled = pd.DataFrame({"session_date": [dt.date(2026, 3, 10)]})
    w = windows_for_days(ev, sampled)
    assert list(w.columns) == ["session_date", "win_start", "win_end"] and len(w) == 2
    assert list(w["win_start"]) == [T("14:00"), T("15:00")] and list(w["win_end"]) == [T("14:20"), T("15:10")]


def test_window_path_and_load_day_trades(tmp_path: Path):
    p = window_path(tmp_path, dt.date(2026, 3, 10), T("14:00"), T("14:20"))
    assert p == tmp_path / "2026-03-10" / "1400-1420.parquet"
    assert load_day_trades(tmp_path, dt.date(2026, 3, 10)) is None
    p.parent.mkdir(parents=True)
    idx = pd.DatetimeIndex([T("14:01"), T("14:00")], tz="UTC", name="ts_event")
    pd.DataFrame({"price": [100.25, 100.0], "size": [2, 1], "side": ["B", "A"]}, index=idx).to_parquet(p)
    q = window_path(tmp_path, dt.date(2026, 3, 10), T("15:00"), T("15:10"))
    pd.DataFrame({"price": [101.0], "size": [5], "side": ["N"]}, index=pd.DatetimeIndex([T("15:05")], tz="UTC", name="ts_event")).to_parquet(q)
    tr = load_day_trades(tmp_path, dt.date(2026, 3, 10))
    assert list(tr.columns) == ["price", "size", "side"] and tr.index.is_monotonic_increasing and len(tr) == 3
    assert tr.index.name == "ts_event" and str(tr.index.tz) == "UTC"
