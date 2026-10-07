import datetime as dt

import numpy as np
import pandas as pd
import pytest

from nqml.backtest.fastboot import block_bootstrap_ci_fast
from nqml.backtest.metrics import block_bootstrap_ci, mean_r_stat
from nqml.config import load_config
from nqml.screen.drift import segment_drift, wald_null
from nqml.screen.fdr import benjamini_hochberg, one_sided_p
from nqml.screen.wall2 import ev_test, mirror_stats, r_gross, units

CFG = load_config("config.yaml")
TICK = CFG["instrument"]["tick_size"]
PV = CFG["instrument"]["point_value_usd"]
COMMISSION = CFG["costs"]["commission_per_side_usd"]


def _path(specs):
    """specs: lista di (hhmm_utc, high, low, close) -> barre 1m su un solo giorno RTH."""
    idx = pd.DatetimeIndex([pd.Timestamp(f"2026-03-10 {t}", tz="UTC") for t, *_ in specs])
    return pd.DataFrame({"open": [c for *_, c in specs], "high": [h for _, h, *_ in specs],
                         "low": [l for _, _, l, _ in specs], "close": [c for *_, c in specs], "volume": 1.0}, index=idx)


def _row(side="long", **kw):
    base = dict(side=side, entry_ts=pd.Timestamp("2026-03-10 14:10", tz="UTC"), entry_price=100.0,
                stop_price=95.0 if side == "long" else 105.0, target_price=110.0 if side == "long" else 90.0)
    return base | kw


# ---------------------------------------------------------------------------
# r_gross — trade-through di 1 tick sul target (spec §1), al tocco esatto NO
# ---------------------------------------------------------------------------

def test_target_touch_exact_is_not_a_hit_long():
    # high == target esatto (110), nessuna barra successiva -> chiude a tempo, non al target.
    bars = _path([("14:10", 101, 99, 100), ("14:11", 110.0, 100, 105)])
    out = r_gross(_row(), bars, CFG)
    assert out["label"] == 0 and out["exit_reason"] == "time"


def test_target_trade_through_one_tick_is_a_hit_long():
    # high == target + 1 tick (110.25) -> hit, fill al prezzo di target (110), non al prezzo toccato.
    bars = _path([("14:10", 101, 99, 100), ("14:11", 110.25, 100, 110)])
    out = r_gross(_row(), bars, CFG)
    assert out["label"] == 1 and out["exit_reason"] == "target"
    assert out["pnl_pts"] == pytest.approx(10.0)          # 110 - 100, non 110.25 - 100
    assert out["R_gross"] == pytest.approx(10.0 / 5.0)     # r_unit = |100 - 95|


def test_target_touch_exact_is_not_a_hit_short():
    # low == target esatto (90), nessuna barra successiva -> chiude a tempo.
    bars = _path([("14:10", 101, 99, 100), ("14:11", 95, 90.0, 92)])
    out = r_gross(_row("short"), bars, CFG)
    assert out["label"] == 0 and out["exit_reason"] == "time"


def test_target_trade_through_one_tick_is_a_hit_short():
    # low == target - 1 tick (89.75) -> hit, fill al prezzo di target (90).
    bars = _path([("14:10", 101, 99, 100), ("14:11", 95, 89.75, 90)])
    out = r_gross(_row("short"), bars, CFG)
    assert out["label"] == 1 and out["exit_reason"] == "target"
    assert out["pnl_pts"] == pytest.approx(10.0)           # -(90 - 100), mirror del caso long
    assert out["R_gross"] == pytest.approx(10.0 / 5.0)      # r_unit = |100 - 105|


def test_stop_still_fills_at_stop_price_not_touch():
    # convenzione invariata rispetto al labeler: lo stop e' un hit al tocco (non serve trade-through).
    bars = _path([("14:10", 101, 99, 100), ("14:11", 100, 95.0, 96)])
    out = r_gross(_row(), bars, CFG)
    assert out["label"] == 0 and out["exit_reason"] == "stop" and out["pnl_pts"] == pytest.approx(-5.0)


# ---------------------------------------------------------------------------
# ev_test — CI quasi degenere su frame costanti, p a una coda al pavimento / vicino a 1
# ---------------------------------------------------------------------------

def _const_frame(value: float, n_days: int = 50) -> pd.DataFrame:
    dates = [dt.date(2020, 1, 1) + dt.timedelta(days=i) for i in range(n_days)]
    return pd.DataFrame({"session_date": dates, "R_gross": [value] * n_days})


def test_ev_test_clearly_positive_frame_p_at_floor():
    n_boot = 2000
    out = ev_test(_const_frame(1.0), value_col="R_gross", n_boot=n_boot, seed=0)
    assert out["point"] == pytest.approx(1.0)
    assert out["ci"][0] == pytest.approx(1.0) and out["ci"][1] == pytest.approx(1.0)  # quasi degenere
    assert out["p_one_sided"] == pytest.approx(1 / (n_boot + 1))
    assert out["n"] == 50


def test_ev_test_clearly_negative_frame_p_near_one():
    n_boot = 2000
    out = ev_test(_const_frame(-1.0), value_col="R_gross", n_boot=n_boot, seed=0)
    assert out["point"] == pytest.approx(-1.0)
    assert out["p_one_sided"] == pytest.approx(1.0)


def test_ev_test_null_col_is_subtracted_before_aggregation():
    df = pd.DataFrame({
        "session_date": [dt.date(2020, 1, 1), dt.date(2020, 1, 2)],
        "R_gross": [1.0, 1.0],
        "null": [0.4, 0.4],
    })
    out = ev_test(df, value_col="R_gross", null_col="null", n_boot=500, seed=0)
    assert out["point"] == pytest.approx(0.6)


# ---------------------------------------------------------------------------
# block_bootstrap_ci_fast — accordo con la versione lenta esistente entro l'errore Monte Carlo
# ---------------------------------------------------------------------------

def test_block_bootstrap_ci_fast_agrees_with_slow_version_within_monte_carlo_error():
    rng = np.random.default_rng(7)
    n_days = 80
    n_per_day = rng.integers(1, 6, size=n_days)
    s_per_day = rng.normal(loc=0.3, scale=1.0, size=n_days) * n_per_day

    per_day_fast = pd.DataFrame({"s": s_per_day, "n": n_per_day})
    per_day_slow = pd.DataFrame({"x_sumR": s_per_day, "x_n": n_per_day})

    n_boot = 20000
    point_fast, ci_fast, dist = block_bootstrap_ci_fast(per_day_fast, n_boot=n_boot, seed=1, alpha=0.05)
    ci_slow = block_bootstrap_ci(per_day_slow, mean_r_stat("x"), n_boot=n_boot, seed=2)

    assert point_fast == pytest.approx(float(s_per_day.sum() / n_per_day.sum()))
    assert len(dist) == n_boot
    # NON ci si aspetta uguaglianza esatta: la versione veloce ricampiona con un'unica matrice
    # (n_boot, n_days) e riduce in un colpo, quella lenta ricostruisce un array 1D per ogni ricampionamento
    # dentro un ciclo Python — stesso seed, ordine di consumo dell'RNG diverso, quindi ricampionamenti
    # diversi. Con n_boot grande i due CI convergono comunque allo stesso intervallo asintotico: tolleranza
    # larga (errore Monte Carlo atteso), non uguaglianza bit-per-bit.
    assert ci_fast[0] == pytest.approx(ci_slow[0], abs=0.05)
    assert ci_fast[1] == pytest.approx(ci_slow[1], abs=0.05)


def test_block_bootstrap_ci_fast_is_fast_at_10000_on_1800_days():
    import time

    rng = np.random.default_rng(3)
    n_days = 1800
    n_per_day = rng.integers(1, 6, size=n_days)
    s_per_day = rng.normal(loc=0.05, scale=1.0, size=n_days) * n_per_day
    per_day = pd.DataFrame({"s": s_per_day, "n": n_per_day})

    t0 = time.perf_counter()
    block_bootstrap_ci_fast(per_day, n_boot=10000, seed=0, alpha=0.05)
    elapsed = time.perf_counter() - t0
    assert elapsed < 1.0


# ---------------------------------------------------------------------------
# mirror_stats — algebra su una coppia costruita a mano (giorni omogenei -> CI degenere)
# ---------------------------------------------------------------------------

def test_mirror_stats_hand_made_pair():
    days = pd.Index([dt.date(2020, 1, 1), dt.date(2020, 1, 2)], name="session_date")
    ev_orig = dict(point=0.6, per_day=pd.DataFrame({"s": [6.0, 6.0], "n": [10, 10]}, index=days))
    ev_mirror = dict(point=0.2, per_day=pd.DataFrame({"s": [2.0, 2.0], "n": [10, 10]}, index=days))

    out = mirror_stats(ev_orig, ev_mirror, n_boot=500, seed=0)
    assert out["micro"] == pytest.approx(0.4)
    assert out["drift"] == pytest.approx(0.2)
    # entrambi i lati hanno lo stesso rapporto s/n su ogni giorno -> qualunque ricampionamento a blocchi
    # riproduce esattamente lo stesso punto: CI degenere, utile a isolare l'algebra dal rumore Monte Carlo.
    assert out["ci_micro"][0] == pytest.approx(0.4) and out["ci_micro"][1] == pytest.approx(0.4)
    assert out["ci_drift"][0] == pytest.approx(0.2) and out["ci_drift"][1] == pytest.approx(0.2)


# ---------------------------------------------------------------------------
# drift.segment_drift — nessuna fuga d'informazione dal futuro
# ---------------------------------------------------------------------------

def _rth_bars_for_days(dates: list[dt.date], opens: list[float], closes: list[float]) -> pd.DataFrame:
    idx, rows = [], []
    for d, o, c in zip(dates, opens, closes):
        ts0 = pd.Timestamp(f"{d} 09:30", tz="America/New_York").tz_convert("UTC")
        ts1 = ts0 + pd.Timedelta(minutes=1)
        idx += [ts0, ts1]
        rows += [dict(open=o, high=max(o, c), low=min(o, c), close=o),
                  dict(open=c, high=max(o, c), low=min(o, c), close=c)]
    return pd.DataFrame(rows, index=pd.DatetimeIndex(idx))


def test_segment_drift_no_leakage_from_future_sessions():
    n = 10
    dates = [dt.date(2026, 1, 1) + dt.timedelta(days=i) for i in range(n)]
    # per costruzione (close - open) / n_bars = i per la sessione i (open=0, close=2*i, 2 barre).
    bars1 = _rth_bars_for_days(dates, opens=[0.0] * n, closes=[2.0 * i for i in range(n)])
    d1 = segment_drift(bars1, "rth", window=5)

    t0 = 6
    closes2 = [2.0 * i if i < t0 else 999.0 for i in range(n)]  # tutte le sessioni >= t0 alterate
    bars2 = _rth_bars_for_days(dates, opens=[0.0] * n, closes=closes2)
    d2 = segment_drift(bars2, "rth", window=5)

    assert d1.loc[dates[t0]] == pytest.approx(d2.loc[dates[t0]])
    expected = np.mean([float(i) for i in range(max(0, t0 - 5), t0)])  # sessioni 1..5 -> media 3.0
    assert d1.loc[dates[t0]] == pytest.approx(expected)


def test_wald_null_formula_hand_computed():
    days = pd.Index([dt.date(2026, 1, 6), dt.date(2026, 1, 7)], name="session_date")
    drift_series = pd.Series([0.02, -0.01], index=days)
    events = pd.DataFrame({
        "side": ["long", "short"],
        "session_date": days,
        "minutes_held": [30.0, 20.0],
        "r_unit_pts": [5.0, 4.0],
    })
    out = wald_null(events, drift_series)
    assert out[0] == pytest.approx(1 * 0.02 * 30.0 / 5.0)
    assert out[1] == pytest.approx(-1 * -0.01 * 20.0 / 4.0)


# ---------------------------------------------------------------------------
# units — costi in R sul caso a mano
# ---------------------------------------------------------------------------

def test_units_costs_in_r_on_market_exit():
    df = pd.DataFrame([dict(side="long", exit_reason="stop", pnl_pts=-5.0, r_unit_pts=5.0, atr=2.0)])
    out = units(df, CFG)
    tick_value = TICK * PV
    expected_cost_R = (2 * COMMISSION + 2 * tick_value) / (5.0 * PV)   # 1 tick ingresso + 1 tick uscita a mercato
    assert out.loc[0, "R_gross"] == pytest.approx(-5.0 / 5.0)
    assert out.loc[0, "usd_gross"] == pytest.approx(-5.0 * PV)
    assert out.loc[0, "atr_units"] == pytest.approx(-5.0 / 2.0)
    assert out.loc[0, "R_gross"] - out.loc[0, "R_net"] == pytest.approx(expected_cost_R)


def test_units_costs_in_r_on_target_exit_only_entry_slippage():
    df = pd.DataFrame([dict(side="long", exit_reason="target", pnl_pts=10.0, r_unit_pts=5.0, atr=2.0)])
    out = units(df, CFG)
    tick_value = TICK * PV
    expected_cost_R = (2 * COMMISSION + 1 * tick_value) / (5.0 * PV)   # solo 1 tick, sull'ingresso: il target e' limite
    assert out.loc[0, "R_gross"] - out.loc[0, "R_net"] == pytest.approx(expected_cost_R)


def test_units_no_trade_rows_are_zeroed():
    df = pd.DataFrame([dict(side="long", exit_reason="gap", pnl_pts=0.0, r_unit_pts=5.0, atr=2.0)])
    out = units(df, CFG)
    for c in ["R_gross", "usd_gross", "atr_units", "R_net", "usd_net", "atr_units_net"]:
        assert out.loc[0, c] == 0.0


# ---------------------------------------------------------------------------
# fdr — percorso a una coda, confermato insieme a benjamini_hochberg
# ---------------------------------------------------------------------------

def test_one_sided_p_combines_with_benjamini_hochberg():
    n_boot = 2000
    dist_pos = np.full(n_boot, 1.0)   # distribuzione degenere, chiaramente positiva
    dist_neg = np.full(n_boot, -1.0)  # chiaramente negativa
    ps = [one_sided_p(dist_pos), one_sided_p(dist_pos), one_sided_p(dist_pos), one_sided_p(dist_neg)]
    assert ps[:3] == [pytest.approx(1 / (n_boot + 1))] * 3
    assert ps[3] == pytest.approx(1.0)
    assert benjamini_hochberg(ps, q=0.10) == [True, True, True, False]
