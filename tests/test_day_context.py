import datetime as dt

import numpy as np
import pandas as pd
from synthetic import bars as _bars
from synthetic import day as _day

from nqml.config import load_config
from nqml.features.day_context import bars5_upto, build_day_context, dev_va_lookup
from nqml.profile.volume_profile import VolumeProfile


def test_context_shapes_and_on_profile():
    ctx = build_day_context(_day(), load_config("config.yaml"))
    assert ctx.session_date == dt.date(2026, 3, 10)
    assert len(ctx.rth1m) == 390 and len(ctx.bars5) == 78
    assert ctx.n_on_bars == 600 and (ctx.on_va.poc, ctx.on_va.vah, ctx.on_va.val) == (100.0, 100.0, 100.0)
    assert ctx.rth_open_price == 100.5
    assert list(ctx.bars5.columns) == ["open", "high", "low", "close", "volume", "n_1m", "ts_close", "atr", "cum_vol"]


def test_dev_va_at_close_matches_replay():
    ctx = build_day_context(_day(), load_config("config.yaml"))
    ts_close = pd.Timestamp("2026-03-10 14:05", tz="UTC")               # chiusura della barra 10:00
    vp = VolumeProfile(0.25)
    vp.add_bars(ctx.rth1m.loc[ctx.rth1m.index < ts_close])
    assert dev_va_lookup(ctx, ts_close) == vp.value_area(0.70)
    assert dev_va_lookup(ctx, pd.Timestamp("2026-03-10 13:31", tz="UTC")) is None   # non e' una chiusura 5m


def test_atr_and_cum_vol():
    ctx = build_day_context(_day(), load_config("config.yaml"))
    b5 = ctx.bars5
    first = b5.iloc[0]
    assert first["atr"] == 1.0                                  # TR = high-low della prima barra, nessuna precedente
    row = b5.loc[pd.Timestamp("2026-03-10 14:00", tz="UTC")]    # barra 10:00: high 96, low 95, prev close 100.5
    assert row["atr"] == np.mean([1.0] * 6 + [5.5])              # 6 TR da 1.0 + TR 5.5 = max(1, |96-100.5|, |95-100.5|)
    assert row["cum_vol"] == 30 * 2.0 + 5 * 3.0
    assert row["ts_close"] == pd.Timestamp("2026-03-10 14:05", tz="UTC")


def test_prev_tail_feeds_atr():
    prev = pd.DataFrame({"open": 100.0, "high": 110.0, "low": 90.0, "close": 100.0, "volume": 1.0, "n_1m": 5},
                        index=pd.date_range("2026-03-09 19:50", periods=2, freq="5min", tz="UTC"))
    ctx = build_day_context(_day(), load_config("config.yaml"), prev_tail5=prev)
    first = ctx.bars5.iloc[0]
    # TR oggi prima barra: max(1, |101-100|, |100-100|) = 1; con i due TR precedenti da 20 -> media (20+20+1)/3
    assert abs(first["atr"] - (20 + 20 + 1) / 3) < 1e-9


def test_upto_truncates_everything():
    upto = pd.Timestamp("2026-03-10 14:05", tz="UTC")
    ctx = build_day_context(_day(), load_config("config.yaml"), upto=upto)
    assert ctx.rth1m.index.max() < upto and ctx.bars5["ts_close"].max() == upto
    assert len(bars5_upto(ctx, upto)) == 7
    assert dev_va_lookup(ctx, pd.Timestamp("2026-03-10 14:10", tz="UTC")) is None


def test_trades_are_truncated_by_upto():
    idx = pd.DatetimeIndex(["2026-03-10 14:00", "2026-03-10 14:04", "2026-03-10 14:05"], tz="UTC", name="ts_event")
    tr = pd.DataFrame({"price": [95.0, 95.25, 100.0], "size": [1, 2, 3], "side": ["A", "B", "B"]}, index=idx)
    ctx = build_day_context(_day(), load_config("config.yaml"), trades=tr)
    assert len(ctx.trades) == 3
    ctx2 = build_day_context(_day(), load_config("config.yaml"), trades=tr, upto=pd.Timestamp("2026-03-10 14:05", tz="UTC"))
    assert len(ctx2.trades) == 2 and ctx2.trades.index.max() < pd.Timestamp("2026-03-10 14:05", tz="UTC")
    assert build_day_context(_day(), load_config("config.yaml")).trades is None


def test_no_rth_bars_keeps_rth1m_schema():
    on_only = _bars("2026-03-09 22:00", 600, 100, 100, 100)
    ctx = build_day_context(on_only, load_config("config.yaml"))
    assert len(ctx.rth1m) == 0
    assert list(ctx.rth1m.columns) == ["open", "high", "low", "close", "volume"]
    assert len(ctx.bars5) == 0
    assert list(ctx.bars5.columns) == ["open", "high", "low", "close", "volume", "n_1m", "ts_close", "atr", "cum_vol"]
    assert ctx.rth_open_price is None
    assert ctx.dev_va_at_close == {}
    assert ctx.on_va is not None
