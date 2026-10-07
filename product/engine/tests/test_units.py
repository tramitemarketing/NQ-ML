"""Test delle singole componenti: statistica, DSR, caricamento, mercato giornaliero, decadimento, CLI."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from revisore import AuditConfig, Market, load_market, load_trades, run_audit
from revisore.decay import decay_analysis
from revisore.stats import day_block_bootstrap, deflated_sharpe, expected_max_sr, probabilistic_sr

from conftest import make_trades, rth_market


def test_dsr_matches_paper_example():
    """Bailey & Lopez de Prado (2014), esempio numerico: SR annuo 2,5 su 1.250 giorni, asimmetria -3,
    curtosi 10, N = 100, varianza annua degli SR 0,5 -> DSR ~ 0,90."""
    sr = 2.5 / np.sqrt(250)
    sr0 = expected_max_sr(100, 0.5 / 250)
    assert sr0 * np.sqrt(250) == pytest.approx(1.79, abs=0.01)
    dsr = probabilistic_sr(sr, sr0, 1250, -3, 10)
    assert dsr == pytest.approx(0.90, abs=0.015)


def test_dsr_decreases_with_trials():
    rng = np.random.default_rng(0)
    r = rng.normal(0.05, 1, 1000)
    vals = [deflated_sharpe(r, n)["dsr"] for n in (1, 10, 100, 1000)]
    assert all(a > b for a, b in zip(vals, vals[1:]))
    one = deflated_sharpe(r, 1)
    assert one["dsr"] == pytest.approx(one["psr"])


def test_bootstrap_null_not_significant_and_blocks_matter():
    rng = np.random.default_rng(1)
    days = np.repeat(np.arange(300), 5)
    day_shock = np.repeat(rng.normal(0, 3, 300), 5)          # trade dello stesso giorno correlati
    v = day_shock + rng.normal(0, 1, 1500) + 0.25
    st = day_block_bootstrap(v, days, n_boot=4000)
    naive_se = v.std(ddof=1) / np.sqrt(len(v))
    assert st["se"] > 1.8 * naive_se                          # il blocco allarga l'incertezza
    ps = [day_block_bootstrap(rng.normal(0, 1, 400), np.arange(400), n_boot=1000, seed=s)["p_pos"] for s in range(40)]
    assert 0.25 < np.mean(ps) < 0.75


def test_load_trades_mapping_sides_and_currency(tmp_path):
    df = pd.DataFrame({"Apertura": ["03/01/2020 10:00", "06/01/2020 11:30"],
                       "Chiusura": ["03/01/2020 12:00", "06/01/2020 15:00"],
                       "Dir": ["Buy", "Sell"], "Profitto USD": [200.0, -100.0], "Contratti": [2, 1]})
    p = tmp_path / "t.csv"
    df.to_csv(p, index=False)
    t = load_trades(p, columns={"entry_time": "Apertura", "exit_time": "Chiusura", "side": "Dir",
                                "pnl": "Profitto USD", "qty": "Contratti"},
                    pnl_unit="currency", point_value=20, dayfirst=True)
    assert list(t["side"]) == [1, -1]
    assert list(t["gross_pts"]) == [5.0, -5.0]               # 200 $ / 20 $/pt / 2 contratti
    assert t["entry_ts"].iloc[0] == pd.Timestamp("2020-01-03 15:00", tz="UTC")
    with pytest.raises(ValueError):
        load_trades(pd.DataFrame({"entry_time": ["2020-01-01"], "side": ["forse"], "pnl": [1]}))


def test_market_price_path_exit_at_close_after_gap():
    bars, _ = rth_market(n_days=3, seed=0)
    m = Market(bars)
    # uscita alle 16:00: nessuna barra delle 16:00 -> chiusura della barra 15:59, non open del giorno dopo
    t = pd.Timestamp("2017-01-02 16:00", tz="America/New_York").tz_convert("UTC").as_unit("ns").value
    k = m.locate(np.array([t]), "exit")[0]
    assert m.pt_px[k] == pytest.approx(bars["close"].iloc[389])
    assert m.n_sessions == 3


def test_daily_market_and_daily_trades():
    rng = np.random.default_rng(7)
    d = pd.bdate_range("2015-01-01", periods=1500)
    close = 100 * np.exp(np.cumsum(rng.normal(0.0015, 0.01, len(d))))
    opn = close * np.exp(rng.normal(0, 0.003, len(d)))
    daily = pd.DataFrame({"Date": d, "Open": opn, "High": np.maximum(opn, close) * 1.005,
                          "Low": np.minimum(opn, close) * 0.995, "Close": close, "Volume": 1e6})
    m = load_market(daily)
    assert m.daily
    pick = np.sort(rng.choice(np.arange(10, 1480), 300, replace=False))
    ent, ex = d[pick], d[pick + 5]
    pnl = m.pt_px[2 * (pick + 5) + 1] - m.pt_px[2 * pick]      # open d -> close d+5
    tr = pd.DataFrame({"entry_time": ent.strftime("%Y-%m-%d"), "exit_time": ex.strftime("%Y-%m-%d"),
                       "side": "long", "pnl": pnl})
    R = run_audit(load_trades(tr), m, AuditConfig(n_boot=1000, n_placebo=100))
    assert R["quality"]["corr"] > 0.999
    assert R["beta"]["beta_mean"] > 0
    assert set(R["placebo"]["scenarios"]) >= {"caso_puro", "solo_long"}


def test_decay_detects_vanishing_edge():
    rng = np.random.default_rng(2)
    sess = pd.bdate_range("2015-01-01", periods=1000)
    v = rng.normal(0, 5, 1000)
    v[:600] += 2.0                                            # vantaggio solo nel periodo di costruzione
    dc = decay_analysis(v, None, sess, is_end=str(sess[599].date()), n_boot=2000)
    assert dc["true_oos"]
    assert dc["is"]["p_pos"] < 0.01
    assert not (dc["ratio"] >= 0.5)
    assert dc["class"] in ("il vantaggio sparisce (cambia segno)",
                           "forte restringimento (tipico di un effetto trovato scavando)")


def test_cli_end_to_end(tmp_path, edge_case):
    from revisore.cli import main
    bars, tr = edge_case
    b = bars.iloc[: 390 * 200]
    t = tr.iloc[:200]
    mp, tp, out, js = tmp_path / "bars.parquet", tmp_path / "trades.csv", tmp_path / "r.html", tmp_path / "r.json"
    b.to_parquet(mp)
    t.to_csv(tp, index=False)
    rc = main(["audit", str(tp), "--market", str(mp), "--n-tried", "50", "--cost", "0.75", "--point-value", "20",
               "--out", str(out), "--json", str(js), "--n-placebo", "100", "--n-boot", "1000"])
    assert rc == 0
    h = out.read_text(encoding="utf-8")
    assert "non consulenza finanziaria" in h.lower()
    assert "data:image/png;base64," in h
    assert "Le prove, una per una" in h
    assert '"grade"' in js.read_text(encoding="utf-8")


def test_cli_lookahead_with_strategy_file(tmp_path, edge_case):
    from revisore.cli import main
    bars, _ = edge_case
    mp = tmp_path / "bars.parquet"
    bars.iloc[: 390 * 30].to_parquet(mp)
    f = tmp_path / "strat.py"
    f.write_text(
        "import numpy as np, pandas as pd\n"
        "def bara(b):\n"
        "    i = np.arange(20, len(b) - 20, 50)\n"
        "    s = np.where(b['close'].to_numpy()[i + 10] > b['open'].to_numpy()[i], 1, -1)\n"
        "    return pd.DataFrame({'entry_time': b.index[i], 'exit_time': b.index[i + 10], 'side': s})\n"
        "def onesta(b):\n"
        "    i = np.arange(20, len(b) - 20, 50)\n"
        "    s = np.where(b['close'].to_numpy()[i - 1] > b['close'].to_numpy()[i - 11], 1, -1)\n"
        "    return pd.DataFrame({'entry_time': b.index[i], 'exit_time': b.index[i + 10], 'side': s})\n",
        encoding="utf-8")
    assert main(["lookahead", "--strategy", f"{f}:bara", "--market", str(mp)]) == 2
    assert main(["lookahead", "--strategy", f"{f}:onesta", "--market", str(mp)]) == 0
