import datetime as dt
import threading
import types
from pathlib import Path

import pandas as pd

from nqml.config import load_config
from nqml.tick.fetch import estimate_windows_cost, fetch_all_windows, fetch_trades_window, trades_spec
from nqml.tick.windows import window_path

CFG = load_config("config.yaml")
T = lambda s: pd.Timestamp(f"2026-03-10 {s}", tz="UTC")


class FakeStore:
    def __init__(self, df): self._df = df
    def to_df(self): return self._df


class FakeClient:
    def __init__(self, cost=0.02, df=None):
        self.calls, self.cost_calls = 0, 0
        self._lock = threading.Lock()
        self._df, self._cost = df, cost
        self.metadata = types.SimpleNamespace(get_cost=self._get_cost)
        self.timeseries = types.SimpleNamespace(get_range=self._get_range)
    def _get_cost(self, **kw): self.cost_calls += 1; return self._cost
    def _get_range(self, **kw):
        with self._lock:                                  # contatore sicuro anche con workers > 1
            self.calls += 1
        return FakeStore(self._df)


def _raw():
    idx = pd.DatetimeIndex([T("14:00:01"), T("14:00:02")], tz="UTC", name="ts_event")
    return pd.DataFrame({"rtype": 0, "publisher_id": 1, "instrument_id": 7, "action": "T", "side": ["A", "B"], "depth": 0,
                         "price": [100.0, 100.25], "size": [1, 3], "flags": 0, "ts_in_delta": 0, "sequence": 0, "symbol": "NQ.v.0"}, index=idx)


def test_trades_spec_iso_utc():
    s = trades_spec(CFG, T("14:00"), T("14:20"))
    assert (s.dataset, s.symbol, s.stype_in, s.schema) == ("GLBX.MDP3", "NQ.v.0", "continuous", "trades")
    assert s.start == "2026-03-10T14:00:00" and s.end == "2026-03-10T14:20:00"


def test_estimate_windows_cost_one_call_per_window():
    w = pd.DataFrame({"session_date": [dt.date(2026, 3, 10)] * 2, "win_start": [T("14:00"), T("15:00")], "win_end": [T("14:20"), T("15:10")]})
    c = FakeClient(cost=0.03)
    out = estimate_windows_cost(c, w, CFG)
    assert c.cost_calls == 2 and list(out["cost_usd"]) == [0.03, 0.03] and out["cost_usd"].sum() == 0.06


def test_fetch_trades_window_keeps_price_size_side():
    df = fetch_trades_window(FakeClient(df=_raw()), trades_spec(CFG, T("14:00"), T("14:20")))
    assert list(df.columns) == ["price", "size", "side"] and list(df["side"]) == ["A", "B"] and df.index.name == "ts_event"


def test_fetch_all_windows_is_atomic_and_resumable(tmp_path: Path):
    w = pd.DataFrame({"session_date": [dt.date(2026, 3, 10)] * 2, "win_start": [T("14:00"), T("15:00")], "win_end": [T("14:20"), T("15:10")]})
    c = FakeClient(df=_raw())
    assert fetch_all_windows(c, w, tmp_path, CFG) == 2 and c.calls == 2
    assert window_path(tmp_path, dt.date(2026, 3, 10), T("14:00"), T("14:20")).exists()
    assert not list(tmp_path.rglob("*.tmp"))
    assert fetch_all_windows(c, w, tmp_path, CFG) == 0 and c.calls == 2      # cache: nessuna nuova chiamata


def test_fetch_all_windows_parallel_writes_each_window_once(tmp_path: Path):
    n = 12
    w = pd.DataFrame({"session_date": [dt.date(2026, 3, 10)] * n,
                      "win_start": [T(f"{14 + k // 4:02d}:{(k % 4) * 15:02d}") for k in range(n)],
                      "win_end": [T(f"{14 + k // 4:02d}:{(k % 4) * 15 + 10:02d}") for k in range(n)]})
    c = FakeClient(df=_raw())
    assert fetch_all_windows(c, w, tmp_path, CFG, workers=4) == n and c.calls == n
    assert len(list(tmp_path.rglob("*.parquet"))) == n and not list(tmp_path.rglob("*.tmp"))
    assert fetch_all_windows(c, w, tmp_path, CFG, workers=4) == 0 and c.calls == n
