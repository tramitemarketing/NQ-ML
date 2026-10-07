import datetime as dt

import pandas as pd

from nqml.backtest.stress import revalue, stress_scenarios, stress_table
from nqml.config import load_config

CFG = load_config("config.yaml")
T = lambda s: pd.Timestamp(f"2026-03-10 {s}", tz="UTC")


def _taken():
    return pd.DataFrame({
        "session_date": [dt.date(2026, 3, 10)] * 4,
        "entry_ts": [T("14:10"), T("14:40"), T("15:00"), T("15:20")],
        "side": ["long", "long", "short", "long"],
        "stop_price": [95.0, 95.0, 105.0, 95.0],
        "entry_price_raw": [100.0, 100.0, 100.0, 100.0],
        "exit_price_raw": [110.0, 95.0, 90.0, 120.0],
        "exit_reason": ["target", "stop", "target", "target"],
    })


def test_scenarios_and_base_equals_default_costs():
    names = [s["name"] for s in stress_scenarios(CFG)]
    assert names == ["base", "slip_2", "slip_3", "comm_x2", "drop_top_5pct"]
    base = revalue(_taken(), stress_scenarios(CFG)[0], CFG)
    assert abs(base.loc[0, "pnl_usd"] - 190.0) < 1e-9      # come in test_labeler: (110-100.25)*20-5


def test_more_slippage_hurts_stops_not_targets():
    base, s2 = revalue(_taken(), stress_scenarios(CFG)[0], CFG), revalue(_taken(), stress_scenarios(CFG)[1], CFG)
    assert s2.loc[0, "exit_fill"] == base.loc[0, "exit_fill"] == 110.0      # target: limite
    assert s2.loc[1, "pnl_usd"] < base.loc[1, "pnl_usd"]                       # stop: peggiora
    assert s2.loc[0, "pnl_usd"] < base.loc[0, "pnl_usd"]                       # ingresso peggiore anche sul target


def test_drop_top_removes_best_trades():
    sc = {"name": "drop", "slippage_ticks": 1, "commission": 2.5, "drop_top_pct": 0.25}
    out = revalue(_taken(), sc, CFG)
    assert len(out) == 3 and out["realized_R"].max() < revalue(_taken(), stress_scenarios(CFG)[0], CFG)["realized_R"].max()


def test_stress_table_rows():
    tab = stress_table(_taken(), n_days=1, cfg=CFG)
    assert list(tab["name"]) == ["base", "slip_2", "slip_3", "comm_x2", "drop_top_5pct"]
    assert tab.loc[tab["name"] == "base", "n"].iloc[0] == 4 and tab["mean_R"].notna().all()
