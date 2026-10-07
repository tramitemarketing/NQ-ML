import pandas as pd

from nqml.config import load_config
from nqml.labels.labeler import apply_costs, label_event, time_stop_minute

CFG = load_config("config.yaml")


def _path(specs):
    """specs: lista di (hhmm_utc, high, low, close) -> barre 1m RTH del 2026-03-10 (EDT: 13:30 UTC = 09:30 NY)."""
    idx = pd.DatetimeIndex([pd.Timestamp(f"2026-03-10 {t}", tz="UTC") for t, *_ in specs])
    return pd.DataFrame({"open": [c for *_, c in specs], "high": [h for _, h, *_ in specs],
                         "low": [l for _, _, l, _ in specs], "close": [c for *_, c in specs], "volume": 1.0}, index=idx)


def _row(side="long", **kw):
    base = dict(event_id="e1", side=side, entry_ts=pd.Timestamp("2026-03-10 14:10", tz="UTC"), entry_price=100.0,
                stop_price=95.0 if side == "long" else 105.0, target_price=110.0 if side == "long" else 90.0)
    return base | kw


def test_target_first_is_label_1():
    bars = _path([("14:10", 101, 99, 100), ("14:11", 104, 100, 103), ("14:12", 111, 103, 110)])
    out = label_event(_row(), bars, CFG)
    assert out["label"] == 1 and out["exit_reason"] == "target" and out["exit_price_raw"] == 110.0
    assert out["exit_ts"] == pd.Timestamp("2026-03-10 14:12", tz="UTC")
    assert out["pnl_pts_raw"] == 10.0 and out["r_unit_pts"] == abs(100.25 - 95.0)


def test_stop_first_is_label_0():
    bars = _path([("14:10", 101, 99, 100), ("14:11", 100, 94, 95), ("14:12", 111, 95, 110)])
    out = label_event(_row(), bars, CFG)
    assert out["label"] == 0 and out["exit_reason"] == "stop" and out["exit_price_raw"] == 95.0 and out["pnl_pts_raw"] == -5.0


def test_both_in_same_bar_is_stop():
    bars = _path([("14:10", 111, 94, 100)])
    out = label_event(_row(), bars, CFG)
    assert out["label"] == 0 and out["exit_reason"] == "stop"


def test_time_stop_exits_at_1555_close():
    bars = _path([("14:10", 101, 99, 100), ("19:54", 101, 99, 100), ("19:55", 102, 99, 101.5), ("19:56", 120, 80, 100)])  # 15:55 NY = 19:55 UTC
    out = label_event(_row(), bars, CFG)
    assert out["label"] == 0 and out["exit_reason"] == "time" and out["exit_price_raw"] == 101.5
    assert out["exit_ts"] == pd.Timestamp("2026-03-10 19:55", tz="UTC") and out["pnl_pts_raw"] == 1.5


def test_bars_before_entry_are_ignored_and_short_mirrors():
    bars = _path([("14:09", 120, 80, 100), ("14:10", 101, 99, 100), ("14:11", 100, 89, 90)])
    out = label_event(_row("short"), bars, CFG)
    assert out["label"] == 1 and out["exit_reason"] == "target" and out["pnl_pts_raw"] == 10.0


def test_no_bars_after_entry():
    out = label_event(_row(), _path([("14:00", 101, 99, 100)]), CFG)
    assert out["exit_reason"] == "no_bars" and out["label"] == 0 and out["pnl_pts_raw"] == 0.0


def test_apply_costs_arithmetic():
    df = pd.DataFrame([
        dict(side="long", stop_price=95.0, entry_price_raw=100.0, exit_price_raw=110.0, exit_reason="target"),
        dict(side="long", stop_price=95.0, entry_price_raw=100.0, exit_price_raw=95.0, exit_reason="stop"),
        dict(side="short", stop_price=105.0, entry_price_raw=100.0, exit_price_raw=101.5, exit_reason="time"),
    ])
    out = apply_costs(df, slippage_ticks=1, commission_per_side=2.5, cfg=CFG)
    # long target: entry 100.25, exit 110 (limite) -> 9.75 pt * 20 - 5 = 190 $; R unit = 5.25 pt = 105 $
    assert out.loc[0, "entry_fill"] == 100.25 and out.loc[0, "exit_fill"] == 110.0
    assert abs(out.loc[0, "pnl_usd"] - 190.0) < 1e-9 and abs(out.loc[0, "realized_R"] - 190.0 / 105.0) < 1e-9
    # long stop: exit 94.75 -> -5.5 pt * 20 - 5 = -115 $; R = -115/105
    assert abs(out.loc[1, "pnl_usd"] + 115.0) < 1e-9 and abs(out.loc[1, "realized_R"] + 115.0 / 105.0) < 1e-9
    # short time: entry 99.75, exit 101.75 -> -(101.75-99.75) = -2 pt * 20 - 5 = -45 $; R unit = |99.75-105| = 5.25
    assert abs(out.loc[2, "pnl_usd"] + 45.0) < 1e-9 and abs(out.loc[2, "realized_R"] + 45.0 / 105.0) < 1e-9
    # 2 tick: il target non peggiora, lo stop sì
    out2 = apply_costs(df, slippage_ticks=2, commission_per_side=2.5, cfg=CFG)
    assert out2.loc[0, "exit_fill"] == 110.0 and out2.loc[1, "exit_fill"] == 94.5


def test_time_stop_minute():
    assert time_stop_minute(CFG) == 15 * 60 + 55


def test_apply_costs_no_bars_has_zero_pnl():
    df = pd.DataFrame([
        dict(side="long", stop_price=95.0, entry_price_raw=100.0, exit_price_raw=100.0, exit_reason="no_bars"),
        dict(side="long", stop_price=95.0, entry_price_raw=100.0, exit_price_raw=95.0, exit_reason="stop"),
    ])
    out = apply_costs(df, slippage_ticks=1, commission_per_side=2.5, cfg=CFG)
    assert out.loc[0, "pnl_usd"] == 0.0 and out.loc[0, "realized_R"] == 0.0
    assert out.loc[1, "pnl_usd"] < 0.0


def test_entry_already_beyond_stop_is_gap():
    bars = _path([("14:10", 101, 99, 100), ("14:11", 104, 100, 103), ("14:12", 111, 103, 110)])
    out = label_event(_row(entry_price=90.0, stop_price=95.0), bars, CFG)
    assert out["exit_reason"] == "gap" and out["label"] == 0 and out["pnl_pts_raw"] == 0.0
    assert out["exit_price_raw"] == 90.0


def test_entry_already_beyond_target_is_gap():
    bars = _path([("14:10", 101, 99, 100), ("14:11", 104, 100, 103), ("14:12", 111, 103, 110)])
    out = label_event(_row(entry_price=112.0, target_price=110.0), bars, CFG)
    assert out["exit_reason"] == "gap" and out["label"] == 0 and out["pnl_pts_raw"] == 0.0


def test_normal_long_is_unaffected_by_gap_check():
    bars = _path([("14:10", 101, 99, 100), ("14:11", 104, 100, 103), ("14:12", 111, 103, 110)])
    out = label_event(_row(), bars, CFG)
    assert out["label"] == 1 and out["exit_reason"] == "target" and out["exit_price_raw"] == 110.0


def test_apply_costs_gap_has_zero_pnl():
    df = pd.DataFrame([
        dict(side="long", stop_price=95.0, entry_price_raw=90.0, exit_price_raw=90.0, exit_reason="gap"),
        dict(side="long", stop_price=95.0, entry_price_raw=100.0, exit_price_raw=95.0, exit_reason="stop"),
    ])
    out = apply_costs(df, slippage_ticks=1, commission_per_side=2.5, cfg=CFG)
    assert out.loc[0, "pnl_usd"] == 0.0 and out.loc[0, "realized_R"] == 0.0
    assert out.loc[1, "pnl_usd"] < 0.0
