"""Test end-to-end del verdetto sui quattro casi richiesti: vantaggio vero, caso, beta, look-ahead."""
from __future__ import annotations

import numpy as np
import pandas as pd

from revisore import AuditConfig, Market, load_trades, run_audit
from revisore.report import render
from revisore.lookahead import audit_lookahead, cheating_strategy, honest_strategy

FAST = dict(n_boot=2000, n_placebo=200)


def test_planted_edge_is_A_or_B(edge_case):
    bars, tr = edge_case
    R = run_audit(load_trades(tr), Market(bars), AuditConfig(n_tried=50, cost=0.5, point_value=20, **FAST))
    v = R["verdict"]
    assert v["grade"] in ("A", "B"), (v, [(c["key"], c["status"], c["value"]) for c in R["checks"]])
    assert not v["flags"]["beta"] and not v["flags"]["no_edge"]
    assert R["boot"]["p_pos"] < 0.001
    assert R["dsr"]["dsr"] > 0.95
    assert R["placebo"]["scenarios"]["caso_puro"]["percentile"] >= 99
    # il P&L dichiarato coincide con il riprezzato
    assert R["quality"]["corr"] > 0.999
    assert abs(R["beta"]["beta_mean"]) < 0.3


def test_random_strategy_has_no_edge(random_case):
    bars, tr = random_case
    R = run_audit(load_trades(tr), Market(bars), AuditConfig(n_tried=1, cost=0.5, point_value=20, **FAST))
    v = R["verdict"]
    assert v["grade"] in ("D", "E"), v
    assert v["flags"]["no_edge"]
    pct = R["placebo"]["scenarios"]["caso_puro"]["percentile"]
    assert 2 < pct < 98


def test_long_on_rising_market_flagged_as_beta(beta_case):
    bars, tr = beta_case
    R = run_audit(load_trades(tr), Market(bars), AuditConfig(n_tried=1, cost=0.75, point_value=20, **FAST))
    v, be = R["verdict"], R["beta"]
    # il netto e' fortemente positivo e "significativo"...
    assert R["boot"]["mean"] > 10 and R["boot"]["p_pos"] < 0.001
    # ...ma e' tutto beta
    assert be["flag"] and v["flags"]["beta"]
    assert be["share_explained"] > 0.7
    assert be["stat_adj"]["p_pos"] > 0.05
    assert v["grade"] == "D"
    assert be["n_overnight"] == len(tr)
    # il placebo "solo long" guadagna quanto la strategia: la mostra come beta
    sl = R["placebo"]["scenarios"]["solo_long"]
    assert sl["median"] > 10
    assert sl["percentile"] < 95
    # e il mercato e' salito quasi solo fuori dalla finestra diurna
    ws = be["window_split"]
    assert ws["outside"] > 0.8 * ws["total"]
    assert "Segnalazione beta" in render(R)


def test_lookahead_catches_cheater_and_passes_honest(edge_case):
    bars, _ = edge_case
    b = bars.iloc[: 390 * 40]
    assert not audit_lookahead(cheating_strategy, b)["ok"]
    assert audit_lookahead(honest_strategy, b)["ok"]


def test_lookahead_catches_peek_at_entry_bar_close(edge_case):
    """Il trucco piu' sottile: entra all'apertura di una barra nel verso della SUA chiusura. Lo
    cattura solo il taglio esattamente all'ingresso (barra a T con chiusura alterata)."""
    bars, _ = edge_case
    b = bars.iloc[: 390 * 40]

    def peek(bb):
        i = np.arange(50, len(bb) - 5, 97)
        side = np.where(bb["close"].to_numpy()[i] > bb["open"].to_numpy()[i], 1, -1)
        return pd.DataFrame({"entry_time": bb.index[i], "exit_time": bb.index[i + 3], "side": side})

    res = audit_lookahead(peek, b, n_random=0, n_entries=6)
    assert not res["ok"]


def test_lookahead_in_full_audit_gives_F(edge_case):
    bars, tr = edge_case
    b = bars.iloc[: 390 * 40]
    trades = load_trades(cheating_strategy(b).assign(pnl_points=lambda d: d["pnl"]).drop(columns="pnl"))
    R = run_audit(trades, Market(b), AuditConfig(cost=0.5, **FAST), strategy=cheating_strategy)
    assert R["verdict"]["grade"] == "F"
    assert R["verdict"]["flags"]["leak"]
    assert R["lookahead"]["control_caught"]
    assert "Look-ahead catturato" in render(R)


def test_wrong_timezone_is_detected(edge_case):
    """Trade scritti in ora di New York ma letti come UTC: i P&L non tornano con il mercato."""
    bars, tr = edge_case
    t = load_trades(tr, tz="UTC")
    R = run_audit(t, Market(bars), AuditConfig(cost=0.5, **FAST))
    assert R["quality"]["corr"] < 0.6
    assert R["verdict"]["grade"] == "F" and R["verdict"]["flags"]["data"]
    assert R["quality"]["tz_hint_hours"] in (4, 5)
