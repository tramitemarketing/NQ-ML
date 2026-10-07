import datetime as dt
import math

import pandas as pd

from nqml.config import load_config
from nqml.features.direction import broken_edge, far_edge, toward_target, up
from nqml.features.geometry import geometry_features
from nqml.profile.volume_profile import ValueArea
from nqml.features.day_context import build_day_context
from synthetic import day as _day, event_row as _row

CFG = load_config("config.yaml")
ON = ValueArea(poc=100.0, vah=110.0, val=90.0, total_volume=1.0, n_levels=81)


def test_direction_helpers():
    assert up("long") == 1 and up("short") == -1
    assert toward_target("long", 90, 100) == 10 and toward_target("short", 110, 100) == 10
    assert broken_edge("long", 110, 90) == 90 and broken_edge("short", 110, 90) == 110
    assert far_edge("long", 110, 90) == 110 and far_edge("short", 110, 90) == 90


def test_geometry_long_hand_computed():
    ctx = build_day_context(_day(), CFG)
    other = ValueArea(poc=97.0, vah=100.0, val=93.0, total_volume=1.0, n_levels=29)
    f = geometry_features(_row("long"), ctx, other, atr=2.0)
    assert f["va_type"] == 0 and f["minutes_since_open"] == 40 and f["bars_in_profile"] == 120
    assert f["excursion_depth"] == (90 - 85) / 20 and f["reentry_close_pos"] == (95 - 90) / 20 and f["va_shift"] == 0
    assert f["poc_pos"] == 1 and f["in_other_va"] == 1
    assert f["dist_other_near_atr"] == (93 - 95) / 2 and f["dist_other_far_atr"] == (100 - 95) / 2
    assert f["overlap_on_dev"] == (100 - 93) / 20
    assert f["stop_dist_atr"] == 10.25 / 2 and f["target_dist_atr"] == 15 / 2 and abs(f["rr_ratio"] - 15 / 10.25) < 1e-12
    assert f["va_width_atr"] == 10.0 and f["open_vs_on_va"] == 1     # open RTH 100.5 oltre la VA ON del giorno sintetico (100/100/100) verso il target del long


def test_geometry_short_is_direction_invariant():
    ctx = build_day_context(_day(), CFG)
    other_l = ValueArea(poc=97.0, vah=100.0, val=93.0, total_volume=1.0, n_levels=29)
    other_s = ValueArea(poc=103.0, vah=107.0, val=100.0, total_volume=1.0, n_levels=29)   # specchio attorno a 100
    fl = geometry_features(_row("long"), ctx, other_l, atr=2.0)
    fs = geometry_features(_row("short"), ctx, other_s, atr=2.0)
    for k in ("excursion_depth", "reentry_close_pos", "va_shift", "poc_pos", "in_other_va",
              "dist_other_near_atr", "dist_other_far_atr", "overlap_on_dev", "stop_dist_atr", "target_dist_atr", "rr_ratio"):
        assert fl[k] == fs[k], k


def test_geometry_dev_bars_in_profile_and_missing_other():
    ctx = build_day_context(_day(), CFG)
    row = _row("long") | {"va_type": "DEV"}
    f = geometry_features(row, ctx, None, atr=2.0)
    assert f["va_type"] == 1 and f["bars_in_profile"] == 8            # chiusure 09:35..10:10
    assert math.isnan(f["in_other_va"]) and math.isnan(f["dist_other_near_atr"]) and math.isnan(f["overlap_on_dev"])


def test_geometry_never_touches_entry_fields():
    ctx = build_day_context(_day(), CFG)
    row = _row("long"); row["entry_ts"] = None; row["entry_price"] = float("nan")
    f = geometry_features(row, ctx, ON, atr=2.0)
    assert f["rr_ratio"] > 0
