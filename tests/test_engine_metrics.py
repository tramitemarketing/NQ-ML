import datetime as dt

import numpy as np
import pandas as pd

from nqml.backtest.engine import simulate_one_position, taken
from nqml.backtest.metrics import block_bootstrap_ci, diff_mean_r_stat, mean_r_stat, per_day_table, summarize

T = lambda s: pd.Timestamp(f"2026-03-10 {s}", tz="UTC")


def _df():
    return pd.DataFrame({
        "event_id": list("abcde"),
        "session_date": [dt.date(2026, 3, 10)] * 5,
        "entry_ts": [T("14:10"), T("14:10"), T("14:20"), T("14:40"), T("15:00")],
        "exit_ts":  [T("14:30"), T("14:30"), T("14:25"), T("14:50"), T("15:10")],
        "ev_r":     [0.5, 0.9, 0.2, 0.3, 0.1],
        "realized_R": [1.0, 2.0, -1.0, 1.0, -1.0],
        "pnl_usd":  [100.0, 200.0, -100.0, 100.0, -100.0],
        "take":     [True, True, True, True, False],
    })


def test_engine_one_position_duplicates_and_skips():
    out = simulate_one_position(_df(), "take").set_index("event_id")["status"]
    assert out["b"] == "taken" and out["a"] == "duplicate"          # stesso entry_ts, vince ev_r maggiore
    assert out["c"] == "skipped_in_position"                          # 14:20 <= exit 14:30
    assert out["d"] == "taken" and out["e"] == "not_taken"
    assert list(taken(_df(), "take")["event_id"]) == ["b", "d"]


def test_summarize_hand_computed():
    tr = taken(_df(), "take")                                         # b (+2R, +200), d (+1R, +100)
    s = summarize(tr, n_days=2, point_value=20.0)
    assert s["n"] == 2 and s["win_rate"] == 1.0 and s["mean_R"] == 1.5 and s["expectancy_usd"] == 150.0
    assert s["profit_factor"] == float("inf") and s["max_dd_R"] == 0.0 and s["trades_per_day"] == 1.0 and s["pct_days_active"] == 0.5
    tr2 = pd.DataFrame({"session_date": [dt.date(2026, 3, 10), dt.date(2026, 3, 11), dt.date(2026, 3, 12)],
                        "entry_ts": [T("14:00"), T("14:00") + pd.Timedelta(days=1), T("14:00") + pd.Timedelta(days=2)],
                        "realized_R": [1.0, -2.0, 0.5], "pnl_usd": [100.0, -200.0, 50.0]})
    s2 = summarize(tr2, n_days=3, point_value=20.0)
    assert s2["max_dd_R"] == 2.0 and s2["max_dd_usd"] == 200.0 and abs(s2["profit_factor"] - 150 / 200) < 1e-12
    assert s2["months_total"] == 1 and s2["months_negative"] == 1


def test_summarize_days_param_sharpe_over_all_test_days():
    days = [dt.date(2026, 3, 10), dt.date(2026, 3, 11), dt.date(2026, 3, 12)]
    tr = pd.DataFrame({"session_date": [days[0], days[0]],
                        "entry_ts": [T("14:00"), T("14:30")],
                        "realized_R": [1.0, -0.5], "pnl_usd": [100.0, -50.0]})
    s_no_days = summarize(tr, n_days=3, point_value=20.0)
    s_days = summarize(tr, n_days=3, point_value=20.0, days=days)
    daily_over_days = pd.Series([50.0, 0.0, 0.0])
    expected_sharpe = daily_over_days.mean() / daily_over_days.std(ddof=1) * (252 ** 0.5)
    assert abs(s_days["sharpe_daily"] - expected_sharpe) < 1e-9
    assert np.isnan(s_no_days["sharpe_daily"])                       # senza days: un solo giorno con trade, std indefinita


def test_summarize_days_param_counts_empty_month():
    days = [dt.date(2026, 3, 10), dt.date(2026, 4, 5)]                # due mesi, il secondo senza trade
    tr = pd.DataFrame({"session_date": [days[0]], "entry_ts": [T("14:00")], "realized_R": [1.0], "pnl_usd": [100.0]})
    s = summarize(tr, n_days=2, point_value=20.0, days=days)
    assert s["months_total"] == 2 and s["months_negative"] == 0      # mese vuoto: 0 non è negativo


def test_per_day_table_and_bootstrap_ci_contains_point_estimate():
    days = [dt.date(2026, 3, 10), dt.date(2026, 3, 11), dt.date(2026, 3, 12)]
    A = pd.DataFrame({"session_date": [days[0], days[0], days[2]], "realized_R": [1.0, 0.5, -0.5], "pnl_usd": [1.0, 1.0, 1.0]})
    B = pd.DataFrame({"session_date": [days[1]], "realized_R": [-1.0], "pnl_usd": [1.0]})
    pd_tab = per_day_table({"A": A, "B": B}, days)
    assert list(pd_tab.index) == days and pd_tab.loc[days[0], "A_n"] == 2 and pd_tab.loc[days[1], "A_n"] == 0
    point = mean_r_stat("A")(pd_tab)
    assert abs(point - (1.0 + 0.5 - 0.5) / 3) < 1e-12
    lo, hi = block_bootstrap_ci(pd_tab, mean_r_stat("A"), n_boot=2000, seed=0)
    assert lo <= point <= hi
    lo2, hi2 = block_bootstrap_ci(pd_tab, mean_r_stat("A"), n_boot=2000, seed=0)
    assert (lo, hi) == (lo2, hi2)                                     # deterministico col seed
    d = diff_mean_r_stat("A", "B")(pd_tab)
    assert abs(d - (point - (-1.0))) < 1e-12


def test_block_bootstrap_ci_alpha_narrows_interval():
    days = [dt.date(2026, 3, 10), dt.date(2026, 3, 11), dt.date(2026, 3, 12)]
    A = pd.DataFrame({"session_date": [days[0], days[0], days[2]], "realized_R": [1.0, 0.5, -0.5], "pnl_usd": [1.0, 1.0, 1.0]})
    pd_tab = per_day_table({"A": A}, days)
    lo95, hi95 = block_bootstrap_ci(pd_tab, mean_r_stat("A"), n_boot=2000, seed=0)
    lo99, hi99 = block_bootstrap_ci(pd_tab, mean_r_stat("A"), n_boot=2000, seed=0, alpha=0.01)
    assert lo99 <= lo95 and hi95 <= hi99                              # 99% e' piu' ampio (contiene) del 95% a parita' di seed
