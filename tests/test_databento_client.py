import types
from pathlib import Path

import pandas as pd
import pytest

from nqml.data.databento_client import (
    CostAboveThreshold, FetchSpec, cached_fetch_month, estimate_cost, fetch_range, guard_cost, month_ranges,
)


class FakeStore:
    def __init__(self, df):
        self._df = df

    def to_df(self):
        return self._df


class FakeClient:
    def __init__(self, cost=1.0, df=None):
        self.calls = 0
        self.metadata = types.SimpleNamespace(get_cost=lambda **kw: cost)
        self.timeseries = types.SimpleNamespace(get_range=self._get_range)
        self._df = df

    def _get_range(self, **kw):
        self.calls += 1
        return FakeStore(self._df)


SPEC = FetchSpec("GLBX.MDP3", "NQ.v.0", "continuous", "ohlcv-1m", "2026-08-01", "2026-09-01")


def _raw_df():
    idx = pd.DatetimeIndex(["2026-08-03 13:30", "2026-08-03 13:31"], tz="UTC", name="ts_event")
    return pd.DataFrame({
        "rtype": 32, "publisher_id": 1, "instrument_id": 7,
        "open": [1.0, 2.0], "high": [1.5, 2.5], "low": [0.5, 1.5], "close": [1.2, 2.2],
        "volume": [10, 20], "symbol": ["NQU6", "NQU6"],
    }, index=idx)


def test_month_ranges_splits_at_month_starts():
    assert month_ranges("2016-09-20", "2016-11-05") == [
        ("2016-09-20", "2016-10-01"), ("2016-10-01", "2016-11-01"), ("2016-11-01", "2016-11-05"),
    ]


def test_month_ranges_single_partial_month():
    assert month_ranges("2026-09-01", "2026-09-19") == [("2026-09-01", "2026-09-19")]


def test_guard_cost_raises_above_threshold_without_confirmation():
    with pytest.raises(CostAboveThreshold):
        guard_cost(12.67, 5.0, confirmed=False)
    guard_cost(12.67, 5.0, confirmed=True)
    guard_cost(3.0, 5.0, confirmed=False)


def test_estimate_cost_calls_metadata():
    assert estimate_cost(FakeClient(cost=4.2), SPEC) == 4.2


def test_fetch_range_keeps_ohlcv_symbol_and_utc_index():
    df = fetch_range(FakeClient(df=_raw_df()), SPEC)
    assert list(df.columns) == ["open", "high", "low", "close", "volume", "symbol"]
    assert str(df.index.tz) == "UTC" and df.index.name == "ts_event"


def test_cached_fetch_month_reads_cache_second_time(tmp_path: Path):
    client = FakeClient(df=_raw_df())
    p = tmp_path / "2026-08.parquet"
    a = cached_fetch_month(client, SPEC, p)
    assert client.calls == 1 and p.exists()
    b = cached_fetch_month(client, SPEC, p)
    assert client.calls == 1
    pd.testing.assert_frame_equal(a, b)
    assert str(b.index.tz) == "UTC"


def test_cached_fetch_month_leaves_no_tmp_file_after_success(tmp_path: Path):
    client = FakeClient(df=_raw_df())
    p = tmp_path / "2026-08.parquet"
    cached_fetch_month(client, SPEC, p)
    assert p.exists()
    assert not p.with_suffix(".parquet.tmp").exists()
    assert list(tmp_path.glob("*.tmp")) == []
