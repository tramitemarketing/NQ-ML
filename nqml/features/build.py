"""Set di feature della Milestone 1a e costruzione per evento / per giornata. Nessun tick, nessun prezzo assoluto."""
from __future__ import annotations

from collections import deque

import numpy as np
import pandas as pd

from nqml.data.bars import sessions_iter
from nqml.features.day_context import DayContext, build_day_context, dev_va_lookup
from nqml.features.geometry import geometry_features
from nqml.features.orderflow import orderflow_features
from nqml.features.volume import atr_at, volume_features
from nqml.profile.sessions import ny_minutes

CORE_1A = ["va_type", "minutes_since_open", "bars_in_profile", "open_vs_on_va",
           "va_width_atr", "excursion_depth", "excursion_minutes", "reentry_close_pos", "va_shift",
           "in_other_va", "stop_dist_atr", "rr_ratio",
           "vol_slope_excursion", "vol_at_extreme", "vol_reentry_bar"]
EXPLORATORY_1A = ["bars_outside", "poc_pos", "dist_other_near_atr", "dist_other_far_atr", "overlap_on_dev",
                  "target_dist_atr", "vol_excursion_vs_pre", "vol_reentry_slope", "rel_vol_session",
                  "atr_14_5m", "day_range_atr"]
CONTEXT_ONLY_1A = ["va_type", "minutes_since_open", "bars_in_profile", "open_vs_on_va", "stop_dist_atr", "rr_ratio"]
ALL_1A = CORE_1A + EXPLORATORY_1A
FORBIDDEN_INPUTS = ("entry_ts", "entry_price")   # post-decisione: il builder non li legge mai

ORDERFLOW_CORE = ["delta_excursion", "delta_reentry", "absorption_score"]
ORDERFLOW_EXPLORATORY = ["delta_at_extreme", "extreme_zone_delta", "large_trade_share", "large_trade_delta", "cum_delta_divergence"]


def _fs(core, exploratory, context_only, has_orderflow, file: str | None = None, offset: bool = False):
    return {"core": list(core), "exploratory": list(exploratory), "context_only": list(context_only),
            "all": list(core) + list(exploratory), "has_orderflow": has_orderflow, "file": file, "offset": offset}


FEATURE_SETS = {
    "1a": _fs(CORE_1A, EXPLORATORY_1A, CONTEXT_ONLY_1A, False, file="1a"),
    "1b": _fs(CORE_1A + ORDERFLOW_CORE, EXPLORATORY_1A + ORDERFLOW_EXPLORATORY, CONTEXT_ONLY_1A, True, file="1b"),
    # 1c (spec §12-ter): bracci A e B sullo stesso file unito, esplorative spente, offset del prior calibrato
    "1c_A": _fs(CORE_1A, [], CONTEXT_ONLY_1A, False, file="1c", offset=True),
    "1c_B": _fs(CORE_1A + ORDERFLOW_CORE, [], CONTEXT_ONLY_1A, True, file="1c", offset=True),
}


def feature_set(version: str) -> dict:
    if version not in FEATURE_SETS:
        raise KeyError(f"versione feature sconosciuta: {version!r} (note: {sorted(FEATURE_SETS)})")
    return FEATURE_SETS[version]


def features_for_event(row: dict, ctx: DayContext, rel_vol_baseline: float | None, cfg: dict, version: str = "1a") -> dict:
    fs = feature_set(version)
    reentry_ts = pd.Timestamp(row["reentry_ts"])
    other = dev_va_lookup(ctx, reentry_ts) if row["va_type"] == "ON" else ctx.on_va
    atr = atr_at(ctx, reentry_ts)
    f = geometry_features(row, ctx, other, atr)
    f.update(volume_features(row, ctx, rel_vol_baseline, cfg))
    if fs["has_orderflow"]:
        f.update(orderflow_features(row, ctx, cfg))
    return {k: f[k] for k in fs["all"]}


class RollingState:
    """Stato che attraversa i giorni: coda 5m per l'ATR e curve di volume cumulato per rel_vol_session."""

    def __init__(self, cfg: dict):
        self.prev_tail5: pd.DataFrame | None = None
        self.cum_curves: deque[dict[int, float]] = deque(maxlen=cfg["features"]["rel_vol_lookback_days"])
        self._period = cfg["features"]["atr_period_5m"]

    def baseline(self, ny_minute_of_close: int) -> float | None:
        vals = [c[ny_minute_of_close] for c in self.cum_curves if ny_minute_of_close in c]
        return float(np.mean(vals)) if vals else None

    def update(self, ctx: DayContext, cfg: dict) -> None:
        if len(ctx.bars5) == 0:
            return
        closes = pd.DatetimeIndex(ctx.bars5["ts_close"])
        minutes = ny_minutes(closes)
        self.cum_curves.append({int(m): float(v) for m, v in zip(minutes, ctx.bars5["cum_vol"])})
        self.prev_tail5 = ctx.bars5.tail(self._period)


def build_features(events: pd.DataFrame, days: pd.DataFrame, bars: pd.DataFrame, cfg: dict, version: str = "1a",
                   trades_loader=None, only_days: set | None = None, progress: bool = False) -> pd.DataFrame:
    fs = feature_set(version)
    if fs["has_orderflow"] and trades_loader is None:
        raise ValueError(f"la versione {version} richiede un trades_loader")
    valid_days = set(pd.to_datetime(days.loc[days["valid"], "session_date"]).dt.date)
    ev_by_day = {sd: g for sd, g in events.groupby(pd.to_datetime(events["session_date"]).dt.date)}
    state = RollingState(cfg)
    out_rows: list[dict] = []
    for i, (sd, day_bars) in enumerate(sessions_iter(bars)):
        if sd not in valid_days:
            continue
        worked = only_days is None or sd in only_days
        trades = None
        if fs["has_orderflow"] and worked:
            trades = trades_loader(sd)
            if trades is None:
                raise ValueError(f"trades_loader non ha trovato trade per il giorno campionato {sd}: "
                                 "le feature di order flow diventerebbero NaN in silenzio")
        ctx = build_day_context(day_bars, cfg, prev_tail5=state.prev_tail5, trades=trades)
        if worked:
            for _, r in ev_by_day.get(sd, pd.DataFrame()).iterrows():
                row = r.to_dict()
                minute = int(ny_minutes(pd.DatetimeIndex([pd.Timestamp(row["reentry_ts"])]))[0])
                feats = features_for_event(row, ctx, state.baseline(minute), cfg, version)
                out_rows.append(row | feats | {"feature_version": version})
        state.update(ctx, cfg)
        if progress and i % 250 == 0:
            print(f"  {sd}  feature calcolate {len(out_rows)}")
    return pd.DataFrame(out_rows)
