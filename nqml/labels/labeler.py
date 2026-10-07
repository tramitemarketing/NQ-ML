"""Label dal percorso 1m dopo l'ingresso (spec §7). Salva prezzi grezzi: i costi si applicano dopo, così gli stress
sono una rivalutazione e non un re-run."""
from __future__ import annotations

import pandas as pd

from nqml.features.direction import up
from nqml.profile.sessions import _hm, ny_minutes


def time_stop_minute(cfg: dict) -> int:
    return _hm(cfg["detector"]["time_stop"])


def label_event(row: dict, rth1m_day: pd.DataFrame, cfg: dict) -> dict:
    side = row["side"]
    u = up(side)
    entry_ts = pd.Timestamp(row["entry_ts"])
    entry = float(row["entry_price"])
    stop, target = float(row["stop_price"]), float(row["target_price"])
    tick = cfg["instrument"]["tick_size"]
    slip = cfg["costs"]["slippage_ticks_per_side"] * tick
    ts_stop = time_stop_minute(cfg)

    path = rth1m_day.loc[rth1m_day.index >= entry_ts]
    path = path.loc[ny_minutes(path.index) <= ts_stop]
    r_unit = abs(entry + u * slip - stop)
    base = dict(event_id=row["event_id"], entry_price_raw=entry, r_unit_pts=r_unit)

    if u * (entry - stop) <= 0 or u * (target - entry) <= 0:
        return base | dict(label=0, exit_reason="gap", exit_ts=entry_ts, exit_price_raw=entry, pnl_pts_raw=0.0)

    if len(path) == 0:
        return base | dict(label=0, exit_reason="no_bars", exit_ts=entry_ts, exit_price_raw=entry, pnl_pts_raw=0.0)

    for ts, b in path.iterrows():
        hit_stop = b["low"] <= stop if side == "long" else b["high"] >= stop
        hit_target = b["high"] >= target if side == "long" else b["low"] <= target
        if hit_stop:
            return base | dict(label=0, exit_reason="stop", exit_ts=ts, exit_price_raw=stop, pnl_pts_raw=u * (stop - entry))
        if hit_target:
            return base | dict(label=1, exit_reason="target", exit_ts=ts, exit_price_raw=target, pnl_pts_raw=u * (target - entry))
    last_ts, last = path.index[-1], path.iloc[-1]
    close = float(last["close"])
    return base | dict(label=0, exit_reason="time", exit_ts=last_ts, exit_price_raw=close, pnl_pts_raw=u * (close - entry))


def apply_costs(df: pd.DataFrame, slippage_ticks: int, commission_per_side: float, cfg: dict) -> pd.DataFrame:
    out = df.copy()
    tick = cfg["instrument"]["tick_size"]
    pv = cfg["instrument"]["point_value_usd"]
    u = out["side"].map(up).astype(float)
    slip = slippage_ticks * tick
    out["entry_fill"] = out["entry_price_raw"] + u * slip
    market_exit = out["exit_reason"] != "target"
    out["exit_fill"] = out["exit_price_raw"] - u * slip * market_exit.astype(float)
    out["pnl_usd"] = u * (out["exit_fill"] - out["entry_fill"]) * pv - 2.0 * commission_per_side
    out["realized_R"] = out["pnl_usd"] / ((out["entry_fill"] - out["stop_price"]).abs() * pv)
    no_trade = out["exit_reason"].isin(["no_bars", "gap"])
    out.loc[no_trade, ["pnl_usd", "realized_R"]] = 0.0
    return out
