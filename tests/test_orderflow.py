import math

import numpy as np
import pandas as pd
from synthetic import day as _day, event_row as _row

from nqml.config import load_config
from nqml.features.day_context import build_day_context
from nqml.features.orderflow import con_side, contro_side, delta, orderflow_features

CFG = load_config("config.yaml")
T = lambda s: pd.Timestamp(f"2026-03-10 {s}", tz="UTC")


def _trades(rows):
    """rows: (hh:mm:ss, price, size, side)."""
    idx = pd.DatetimeIndex([T(t) for t, *_ in rows], tz="UTC", name="ts_event")
    return pd.DataFrame({"price": [p for _, p, *_ in rows], "size": [s for _, _, s, _ in rows], "side": [sd for *_, sd in rows]}, index=idx)


def test_sides_and_delta():
    assert con_side("long") == "A" and contro_side("long") == "B" and con_side("short") == "B"
    tr = _trades([("14:00:01", 95.0, 3, "A"), ("14:00:02", 95.0, 1, "B"), ("14:00:03", 95.0, 2, "N")])
    assert delta(tr, "long") == (1 - 3) / 4 and delta(tr, "short") == (3 - 1) / 4        # N ignorato
    assert math.isnan(delta(tr.iloc[0:0], "long"))


def _window_trades():
    # finestra long [14:00, 14:10): estremo 95 toccato alle 14:00-14:04 (barre b del giorno sintetico); rientro 14:05-14:09
    return _trades([
        ("14:00:10", 95.5, 4, "A"), ("14:00:20", 95.25, 2, "B"),            # minuto 14:00: con 4, contro 2
        ("14:01:10", 95.0, 6, "A"), ("14:01:30", 95.0, 1, "B"),             # 14:01: con 6, contro 1 (zona estremo: 95.0..96.0)
        ("14:02:10", 95.25, 1, "A"), ("14:02:40", 95.5, 5, "B"),            # 14:02
        ("14:03:10", 95.75, 1, "B"),                                        # 14:03
        ("14:04:10", 96.0, 20, "B"),                                        # 14:04: trade grande
        ("14:06:10", 99.0, 2, "A"), ("14:07:10", 100.0, 8, "B"),            # barra di rientro 14:05-14:09
        ("14:10:05", 100.0, 50, "B"),                                       # DOPO reentry_ts: mai letto
    ])


def test_orderflow_features_hand_computed():
    row = _row("long") | {"extreme_price": 95.0}
    ctx = build_day_context(_day(), CFG, trades=_window_trades())
    f = orderflow_features(row, ctx, CFG)
    # finestra W (14:00..14:09): con(A) = 4+6+1+2 = 13, contro(B) = 2+1+5+1+20+8 = 37 -> delta = (37-13)/50
    assert abs(f["delta_excursion"] - (37 - 13) / 50) < 1e-12
    # rientro R (14:05..14:09): A 2, B 8 -> (8-2)/10
    assert abs(f["delta_reentry"] - 0.6) < 1e-12
    # zona estremo |p-95| <= 1.0 (4 tick): i trade 95.0..96.0, NON quelli del rientro a 99 e 100 -> V_con(Z) = 4+6+1 = 11 -> 11/50
    assert abs(f["absorption_score"] - 11 / 50) < 1e-12
    # delta nella zona: contro(B) = 2+1+5+1+20 = 29, con(A) = 11 -> (29-11)/40
    assert abs(f["extreme_zone_delta"] - 18 / 40) < 1e-12
    # t_ext = 14:00 (prima barra 1m con low == 95) -> 3 minuti prima: 13:57..13:59, nessun trade -> NaN
    assert math.isnan(f["delta_at_extreme"])
    # trade grandi: q95 delle size in W [4,2,6,1,1,5,1,20,2,8] = 20*0.95-quantile -> >= 14.6 -> solo il 20 -> share 20/50, delta (20-0)/20 = 1
    assert abs(f["large_trade_share"] - 20 / 50) < 1e-12 and f["large_trade_delta"] == 1.0
    # divergenza: t_ext e' il primo bucket (14:00): nessun bucket precedente -> 0
    assert f["cum_delta_divergence"] == 0


def test_cum_delta_divergence_detects_earlier_pressure_peak():
    # estremo toccato al minuto 14:02 (barre del giorno sintetico toccano 95 da 14:00 a 14:04; qui spostiamo l'estremo del row a 95.0 ma
    # costruiamo trade con pressione "con" che sale a 14:00-14:01 e cala prima di 14:02)
    row = _row("long") | {"extreme_price": 95.0, "break_ts": T("14:00"), "reentry_ts": T("14:10")}
    tr = _trades([("14:00:10", 95.5, 10, "A"), ("14:01:10", 95.5, 10, "A"), ("14:02:10", 95.0, 1, "A"), ("14:02:20", 95.0, 9, "B")])
    day = _day()
    day["low"] = day["low"].astype(float)               # evita TypeError su assegnazione float in colonna int64 (pandas 3.0)
    day.loc[T("14:00"):T("14:01"), ["low"]] = 95.5       # le barre 14:00 e 14:01 non toccano piu' 95: t_ext = 14:02
    ctx = build_day_context(day, CFG, trades=tr)
    f = orderflow_features(row, ctx, CFG)
    # c per minuto: 14:00 -> 10, 14:01 -> 20, 14:02 -> 20 + (1-9) = 12; c_ext = 12 < c_max(prima) = 20 -> 1
    assert f["cum_delta_divergence"] == 1


def test_no_trades_gives_all_nan():
    ctx = build_day_context(_day(), CFG)
    f = orderflow_features(_row("long") | {"extreme_price": 95.0}, ctx, CFG)
    assert len(f) == 8 and all(math.isnan(v) for v in f.values())
