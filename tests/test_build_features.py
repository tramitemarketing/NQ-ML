import importlib
import inspect
import math
import pkgutil
import re

import numpy as np
import pandas as pd
import pytest
from synthetic import day as _day

import nqml.features as features_pkg
import nqml.features.build as build_mod
import nqml.features.geometry as geometry_mod
import nqml.features.volume as volume_mod
from nqml.config import load_config
from nqml.detector.events import event_to_row
from nqml.detector.run_day import run_day
from nqml.features.build import ALL_1A, CORE_1A, EXPLORATORY_1A, FEATURE_SETS, FORBIDDEN_INPUTS, ORDERFLOW_CORE, ORDERFLOW_EXPLORATORY, RollingState, build_features, feature_set, features_for_event
from nqml.features.day_context import build_day_context
from nqml.features.orderflow import KEYS as OF_KEYS
from nqml.profile.sessions import ny_minutes

CFG = load_config("config.yaml")


def _events_of(day_bars):
    res = run_day(day_bars, pd.Timestamp(day_bars.index[-1]).tz_convert("America/New_York").date(), CFG)
    return [event_to_row(e) for e in res.events]


def _same(a: dict, b: dict) -> None:
    assert a.keys() == b.keys()
    for k in a:
        x, y = a[k], b[k]
        if isinstance(x, float) and math.isnan(x):
            assert isinstance(y, float) and math.isnan(y), k
        else:
            assert abs(x - y) < 1e-9, (k, x, y)


def test_feature_sets_are_disjoint_and_complete():
    assert not set(CORE_1A) & set(EXPLORATORY_1A) and len(ALL_1A) == 26
    rows = _events_of(_day())
    ctx = build_day_context(_day(), CFG)
    f = features_for_event(rows[0], ctx, rel_vol_baseline=None, cfg=CFG)
    assert set(f.keys()) == set(ALL_1A)


def test_no_lookahead_truncated_context_gives_identical_features():
    rows = _events_of(_day())
    assert len(rows) == 2
    for row in rows:
        full = build_day_context(_day(), CFG)
        trunc = build_day_context(_day(), CFG, upto=row["reentry_ts"])
        _same(features_for_event(row, full, 80.0, CFG), features_for_event(row, trunc, 80.0, CFG))


def _mirror(day_bars: pd.DataFrame, centre: float = 100.0) -> pd.DataFrame:
    m = day_bars.copy()
    m["open"], m["close"] = 2 * centre - day_bars["open"], 2 * centre - day_bars["close"]
    m["high"], m["low"] = 2 * centre - day_bars["low"], 2 * centre - day_bars["high"]
    return m


def test_symmetry_mirrored_day_gives_identical_features():
    d, dm = _day(), _mirror(_day())
    rows, rows_m = _events_of(d), _events_of(dm)
    assert [r["side"] for r in rows] == ["long", "long"] and [r["side"] for r in rows_m] == ["short", "short"]
    ctx, ctx_m = build_day_context(d, CFG), build_day_context(dm, CFG)
    for r, rm in zip(rows, rows_m):
        assert r["va_type"] == rm["va_type"]
        _same(features_for_event(r, ctx, 80.0, CFG), features_for_event(rm, ctx_m, 80.0, CFG))


def _mirror_trades(tr: pd.DataFrame, centre: float = 100.0) -> pd.DataFrame:
    m = tr.copy()
    m["price"] = 2 * centre - tr["price"]
    m["side"] = tr["side"].map({"A": "B", "B": "A", "N": "N"})
    return m


def _synthetic_trades():
    from test_orderflow import _window_trades
    return _window_trades()


def test_no_lookahead_holds_for_1b_with_trades():
    rows = _events_of(_day())
    tr = _synthetic_trades()
    for row in rows:
        full = build_day_context(_day(), CFG, trades=tr)
        trunc = build_day_context(_day(), CFG, upto=row["reentry_ts"], trades=tr)
        _same(features_for_event(row, full, 80.0, CFG, version="1b"), features_for_event(row, trunc, 80.0, CFG, version="1b"))
        assert set(features_for_event(row, full, 80.0, CFG, version="1b")) == set(feature_set("1b")["all"])


def test_symmetry_holds_for_1b_with_mirrored_trades():
    d, dm = _day(), _mirror(_day())
    tr, trm = _synthetic_trades(), _mirror_trades(_synthetic_trades())
    rows, rows_m = _events_of(d), _events_of(dm)
    ctx, ctx_m = build_day_context(d, CFG, trades=tr), build_day_context(dm, CFG, trades=trm)
    for r, rm in zip(rows, rows_m):
        fa, fb = features_for_event(r, ctx, 80.0, CFG, version="1b"), features_for_event(rm, ctx_m, 80.0, CFG, version="1b")
        _same(fa, fb)
        assert not all(math.isnan(fa[k]) for k in OF_KEYS)       # le feature tick sono davvero confrontate


class _Poisoned(dict):
    """Riga che esplode se qualcuno legge una chiave post-decisione, anche via .get()."""
    def __getitem__(self, k):
        assert k not in FORBIDDEN_INPUTS, f"feature builder ha letto {k}"
        return super().__getitem__(k)
    def get(self, k, default=None):
        assert k not in FORBIDDEN_INPUTS, f"feature builder ha letto {k}"
        return super().get(k, default)
    def __contains__(self, k):
        assert k not in FORBIDDEN_INPUTS, f"feature builder ha testato {k}"
        return super().__contains__(k)


def test_features_never_read_entry_fields_all_modules():
    rows = _events_of(_day())
    ctx = build_day_context(_day(), CFG, trades=_synthetic_trades())
    assert set(features_for_event(_Poisoned(rows[0]), ctx, None, CFG, version="1b")) == set(feature_set("1b")["all"])
    for info in pkgutil.iter_modules(features_pkg.__path__):
        mod = importlib.import_module(f"nqml.features.{info.name}")
        src = inspect.getsource(mod).replace('FORBIDDEN_INPUTS = ("entry_ts", "entry_price")', "")
        assert not re.search(r"['\"]entry_(ts|price)['\"]", src), mod.__name__


def test_build_features_1b_uses_loader_and_only_days():
    rows = _events_of(_day())
    events = pd.DataFrame(rows)
    days = pd.DataFrame([dict(session_date=rows[0]["session_date"], n_rth_bars=390, valid=True, n_events=2, on_vah=100.0, on_val=100.0, on_poc=100.0)])
    calls = []
    def loader(sd):
        calls.append(sd); return _synthetic_trades()
    out = build_features(events, days, _day(), CFG, version="1b", trades_loader=loader, only_days={rows[0]["session_date"]})
    assert calls == [rows[0]["session_date"]] and len(out) == 2 and (out["feature_version"] == "1b").all()
    assert set(feature_set("1b")["all"]) <= set(out.columns) and out["delta_excursion"].notna().all()
    out0 = build_features(events, days, _day(), CFG, version="1b", trades_loader=loader, only_days=set())
    assert len(out0) == 0


def test_build_features_1b_raises_when_loader_returns_none_for_worked_day():
    rows = _events_of(_day())
    events = pd.DataFrame(rows)
    days = pd.DataFrame([dict(session_date=rows[0]["session_date"], n_rth_bars=390, valid=True, n_events=2, on_vah=100.0, on_val=100.0, on_poc=100.0)])
    with pytest.raises(ValueError, match=str(rows[0]["session_date"])):
        build_features(events, days, _day(), CFG, version="1b", trades_loader=lambda sd: None, only_days={rows[0]["session_date"]})


def test_rolling_state_baseline_and_build_features():
    st = RollingState(CFG)
    assert st.baseline(600) is None
    ctx = build_day_context(_day(), CFG)
    st.update(ctx, CFG)
    minute = int(ny_minutes(pd.DatetimeIndex([pd.Timestamp("2026-03-10 14:10", tz="UTC")]))[0])   # 10:10 NY
    assert st.baseline(minute) == 30 * 2.0 + 5 * 3.0 + 5 * 1.0
    # build_features su un giorno: eventi + 26 feature + version
    rows = _events_of(_day())
    events = pd.DataFrame(rows)
    days = pd.DataFrame([dict(session_date=rows[0]["session_date"], n_rth_bars=390, valid=True, n_events=2,
                              on_vah=100.0, on_val=100.0, on_poc=100.0)])
    out = build_features(events, days, _day(), CFG)
    assert len(out) == 2 and set(ALL_1A) <= set(out.columns) and (out["feature_version"] == "1a").all()
    assert out["rel_vol_session"].isna().all()      # primo giorno: nessuna baseline


def test_feature_sets_registry():
    a, b = feature_set("1a"), feature_set("1b")
    assert a["core"] == CORE_1A and a["exploratory"] == EXPLORATORY_1A and a["all"] == ALL_1A and a["has_orderflow"] is False
    assert b["core"] == CORE_1A + ORDERFLOW_CORE and b["exploratory"] == EXPLORATORY_1A + ORDERFLOW_EXPLORATORY
    assert b["context_only"] == a["context_only"] and b["has_orderflow"] is True and len(b["all"]) == 34
    assert not set(ORDERFLOW_CORE) & set(ALL_1A)
    with pytest.raises(KeyError):
        feature_set("9z")


def test_feature_sets_1c_have_no_exploratory_and_offset():
    a, b = feature_set("1c_A"), feature_set("1c_B")
    assert a["core"] == CORE_1A and a["exploratory"] == [] and a["file"] == "1c" and a["offset"] is True and not a["has_orderflow"]
    assert b["core"] == CORE_1A + ORDERFLOW_CORE and b["exploratory"] == [] and b["file"] == "1c" and b["offset"] is True and b["has_orderflow"]
    assert feature_set("1a")["file"] == "1a" and feature_set("1a")["offset"] is False
    assert feature_set("1b")["file"] == "1b" and feature_set("1b")["offset"] is False
