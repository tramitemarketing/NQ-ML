import math

import numpy as np
import pandas as pd

from nqml.config import load_config
from nqml.features.day_context import build_day_context
from nqml.features.volume import atr_at, norm_slope, volume_features
from synthetic import day as _day, event_row as _row

CFG = load_config("config.yaml")


def test_norm_slope():
    assert norm_slope(np.array([1.0, 2.0, 3.0])) == 0.5            # pendenza 1 / media 2
    assert norm_slope(np.array([3.0, 2.0, 1.0])) == -0.5
    assert math.isnan(norm_slope(np.array([5.0]))) and math.isnan(norm_slope(np.array([0.0, 0.0])))


def test_volume_features_hand_computed():
    ctx = build_day_context(_day(), CFG)
    row = _row("long") | {"extreme_price": 95.0, "break_ts": pd.Timestamp("2026-03-10 14:00", tz="UTC"),
                          "reentry_ts": pd.Timestamp("2026-03-10 14:10", tz="UTC")}
    f = volume_features(row, ctx, rel_vol_baseline=50.0, cfg=CFG)
    # finestra 10:00-10:09: 5 barre vol 3 + 5 barre vol 1 -> media 2, pendenza OLS = -0.2424.. / 2
    win = np.array([3.0] * 5 + [1.0] * 5)
    assert abs(f["vol_slope_excursion"] - norm_slope(win)) < 1e-12
    assert f["vol_at_extreme"] == 3.0 / 2.0                        # prima barra con low == 95 ha volume 3
    assert f["vol_reentry_bar"] == 5.0 / ((6 * 10.0 + 15.0) / 7)   # barra 10:05 (vol 5) / media delle 7 barre 5m precedenti (sei da 10, una da 15)
    assert f["vol_excursion_vs_pre"] == 2.0 / 2.0                  # 30 minuti prima: 09:30-09:59 vol 2
    assert f["vol_reentry_slope"] == 0.0                           # 10:05-10:09 volumi tutti 1.0: pendenza 0
    assert f["rel_vol_session"] == (30 * 2.0 + 5 * 3.0 + 5 * 1.0) / 50.0
    assert f["atr_14_5m"] == atr_at(ctx, row["reentry_ts"])
    assert f["day_range_atr"] == (101 - 95) / f["atr_14_5m"]


def test_volume_features_missing_baseline_is_nan():
    ctx = build_day_context(_day(), CFG)
    f = volume_features(_row("long") | {"extreme_price": 95.0}, ctx, rel_vol_baseline=None, cfg=CFG)
    assert math.isnan(f["rel_vol_session"])
