import datetime as dt
from pathlib import Path

import pandas as pd
import pytest

from nqml.data.bars import five_min_bin, load_bars, resample_5m, rth_bars, sessions_iter


def _flat(idx, price=1.0, vol=1.0):
    return pd.DataFrame(
        {"open": price, "high": price, "low": price, "close": price, "volume": vol}, index=idx
    )


def test_rth_bars_filters_to_rth_and_tags_session_date():
    idx = pd.date_range("2026-03-10 13:25", periods=10, freq="1min", tz="UTC")  # 13:25..13:34
    out = rth_bars(_flat(idx))
    assert len(out) == 5
    assert out.index[0] == pd.Timestamp("2026-03-10 13:30", tz="UTC")
    assert (out["session_date"] == dt.date(2026, 3, 10)).all()


def test_rth_bars_honours_configured_rth_open():
    idx = pd.date_range("2026-03-10 13:25", periods=40, freq="1min", tz="UTC")  # 09:25..10:04 NY
    out = rth_bars(_flat(idx), rth_open="10:00")
    dropped = pd.date_range("2026-03-10 13:30", "2026-03-10 13:59", freq="1min", tz="UTC")  # 09:30..09:59 NY
    assert not any(ts in out.index for ts in dropped)
    assert out.index[0] == pd.Timestamp("2026-03-10 14:00", tz="UTC")
    assert (out.index >= pd.Timestamp("2026-03-10 14:00", tz="UTC")).all()


def test_resample_5m_is_aligned_and_aggregates_ohlcv():
    idx = pd.date_range("2026-03-10 13:30", periods=10, freq="1min", tz="UTC")
    df = pd.DataFrame({
        "open": [float(i) for i in range(10)],
        "high": [float(i + 1) for i in range(10)],
        "low": [float(i) for i in range(10)],
        "close": [i + 0.5 for i in range(10)],
        "volume": [1.0] * 10,
    }, index=idx)
    out = resample_5m(df)
    assert list(out.index) == [
        pd.Timestamp("2026-03-10 13:30", tz="UTC"),
        pd.Timestamp("2026-03-10 13:35", tz="UTC"),
    ]
    first = out.iloc[0]
    assert first["open"] == 0.0 and first["high"] == 5.0 and first["low"] == 0.0
    assert first["close"] == 4.5 and first["volume"] == 5.0 and first["n_1m"] == 5


def test_resample_5m_drops_empty_bins_between_days():
    a = pd.date_range("2026-03-10 19:55", periods=5, freq="1min", tz="UTC")
    b = pd.date_range("2026-03-11 13:30", periods=5, freq="1min", tz="UTC")
    out = resample_5m(_flat(a.append(b)))
    assert len(out) == 2


def test_five_min_bin_floors():
    idx = pd.DatetimeIndex(["2026-03-10 13:34", "2026-03-10 13:35"], tz="UTC")
    assert list(five_min_bin(idx)) == [
        pd.Timestamp("2026-03-10 13:30", tz="UTC"),
        pd.Timestamp("2026-03-10 13:35", tz="UTC"),
    ]


def test_load_bars_concats_sorted_and_deduped(tmp_path: Path):
    d = tmp_path / "ohlcv_1m"; d.mkdir()
    a = _flat(pd.date_range("2026-03-10 13:30", periods=3, freq="1min", tz="UTC"))
    b = _flat(pd.date_range("2026-03-10 13:32", periods=3, freq="1min", tz="UTC"))  # sovrapposto di 1
    a.index.name = b.index.name = "ts_event"
    b.to_parquet(d / "2026-04.parquet"); a.to_parquet(d / "2026-03.parquet")
    out = load_bars(tmp_path)
    assert len(out) == 5 and out.index.is_monotonic_increasing and out.index.name == "ts_event"


def test_load_bars_empty_raises_systemexit(tmp_path: Path):
    (tmp_path / "ohlcv_1m").mkdir()
    with pytest.raises(SystemExit):
        load_bars(tmp_path)


def test_sessions_iter_groups_by_session_date():
    idx = pd.DatetimeIndex(["2026-03-09 22:00", "2026-03-10 13:30", "2026-03-10 21:30"], tz="UTC")  # lun 18:00, mar 09:30, mar 17:30
    out = list(sessions_iter(_flat(idx)))
    assert [sd for sd, _ in out] == [dt.date(2026, 3, 10), dt.date(2026, 3, 11)]
    assert list(out[0][1].columns) == ["open", "high", "low", "close", "volume"]
