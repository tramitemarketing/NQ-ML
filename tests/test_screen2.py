"""Test dei candidati 5-8 dello screening (pre-registrazione
`docs/superpowers/specs/2026-09-23-screening-candidati-5-8-e-ibridi.md`) e dei moduli condivisi
`nqml.screen.fdr` (Benjamini-Hochberg, p-value bootstrap) e `nqml.screen.overlap`."""
import datetime as dt

import pandas as pd
import pytest

from nqml.config import load_config
from nqml.screen import lasthour, overnight, prevva, vwap
from nqml.screen.fdr import benjamini_hochberg, bootstrap_p
from nqml.screen.overlap import overlap_matrix, overlap_share
from nqml.screen.wall import g_per_day, g_stat

CFG = load_config("config.yaml")
SD = dt.date(2026, 3, 10)  # EDT, 09:30 NY = 13:30 UTC (stessa convenzione di tests/test_orb.py)


def _bars(start_utc: str, specs: list[tuple[float, float, float, float]], vol: float = 1.0) -> pd.DataFrame:
    idx = pd.date_range(start_utc, periods=len(specs), freq="1min", tz="UTC")
    o = [s[0] for s in specs]
    h = [s[1] for s in specs]
    l = [s[2] for s in specs]
    c = [s[3] for s in specs]
    return pd.DataFrame({"open": o, "high": h, "low": l, "close": c, "volume": vol}, index=idx)


# ===========================================================================
# nqml.screen.fdr — Benjamini-Hochberg e p-value bootstrap
# ===========================================================================

def test_benjamini_hochberg_hand_computed_example():
    # p_(i) <= q*i/m: rango1 0.001<=0.025 si, rango2 0.02<=0.05 si, rango3 0.03<=0.075 si, rango4 0.2<=0.10 no
    # -> soglia = p_(3) = 0.03, scoperti i primi tre.
    assert benjamini_hochberg([0.001, 0.02, 0.03, 0.2], q=0.10) == [True, True, True, False]


def test_benjamini_hochberg_no_discovery_when_smallest_p_fails():
    assert benjamini_hochberg([0.5, 0.6, 0.9], q=0.10) == [False, False, False]


def test_benjamini_hochberg_order_independent_of_input_order():
    # stessi p-value dell'esempio a mano, ma in un ordine diverso: le scoperte seguono il p-value, non la posizione.
    out = benjamini_hochberg([0.2, 0.001, 0.03, 0.02], q=0.10)
    assert out == [False, True, True, True]


def test_bootstrap_p_g_exactly_zero_gives_p_close_to_one():
    # ogni giorno ha somma (d_sum) esattamente zero (un evento +0.5 e uno -0.5): qualunque ricampionamento
    # a blocchi per giorno da' sempre stat = 0, quindi p = 1 esatto, non solo "vicino".
    days = [dt.date(2026, 3, d) for d in (10, 11, 12)]
    rows = []
    for d in days:
        rows.append(dict(session_date=d, label=1, rr_ratio=1.0))  # d = +0.5
        rows.append(dict(session_date=d, label=0, rr_ratio=1.0))  # d = -0.5
    per_day = g_per_day(pd.DataFrame(rows))
    p = bootstrap_p(per_day, g_stat, n_boot=200, seed=0)
    assert p == pytest.approx(1.0)


def test_bootstrap_p_g_far_from_zero_gives_floor_p():
    # ogni giorno ha la stessa coppia (d_sum, n) positiva: qualunque ricampionamento da' sempre lo stesso
    # g > 0, quindi la coda "g* <= 0" e' sempre vuota -> p al minimo raggiungibile 2/(B+1) (correzione (k+1)/(B+1)).
    days = [dt.date(2026, 3, d) for d in (10, 11, 12)]
    rows = [dict(session_date=d, label=1, rr_ratio=1.0) for d in days for _ in range(2)]  # d = +0.5 ciascuno
    per_day = g_per_day(pd.DataFrame(rows))
    n_boot = 200
    p = bootstrap_p(per_day, g_stat, n_boot=n_boot, seed=0)
    assert p == pytest.approx(2.0 / (n_boot + 1))


# ===========================================================================
# nqml.screen.overlap — matrice di sovrapposizione
# ===========================================================================

def test_overlap_share_hand_computed_tiny_fixture():
    a = pd.DataFrame({
        "session_date": [SD, SD], "side": ["long", "long"],
        "signal_ts": [pd.Timestamp("2026-03-10 14:00", tz="UTC"), pd.Timestamp("2026-03-10 18:00", tz="UTC")],
    })
    b = pd.DataFrame({
        "session_date": [SD], "side": ["long"],
        "signal_ts": [pd.Timestamp("2026-03-10 14:10", tz="UTC")],  # entro 15 min del primo evento di a, non del secondo
    })
    assert overlap_share(a, b, window_minutes=15) == pytest.approx(0.5)


def test_overlap_share_no_match_different_side_or_day():
    a = pd.DataFrame({"session_date": [SD], "side": ["long"], "signal_ts": [pd.Timestamp("2026-03-10 14:00", tz="UTC")]})
    b_wrong_side = pd.DataFrame({"session_date": [SD], "side": ["short"], "signal_ts": [pd.Timestamp("2026-03-10 14:05", tz="UTC")]})
    b_wrong_day = pd.DataFrame({"session_date": [dt.date(2026, 3, 11)], "side": ["long"], "signal_ts": [pd.Timestamp("2026-03-11 14:05", tz="UTC")]})
    assert overlap_share(a, b_wrong_side) == 0.0
    assert overlap_share(a, b_wrong_day) == 0.0


def test_overlap_share_empty_a_is_nan():
    empty = pd.DataFrame(columns=["session_date", "side", "signal_ts"])
    b = pd.DataFrame({"session_date": [SD], "side": ["long"], "signal_ts": [pd.Timestamp("2026-03-10 14:00", tz="UTC")]})
    assert pd.isna(overlap_share(empty, b))


def test_overlap_matrix_diagonal_is_nan_and_shape():
    a = pd.DataFrame({"session_date": [SD], "side": ["long"], "signal_ts": [pd.Timestamp("2026-03-10 14:00", tz="UTC")]})
    b = pd.DataFrame({"session_date": [SD], "side": ["long"], "signal_ts": [pd.Timestamp("2026-03-10 14:05", tz="UTC")]})
    m = overlap_matrix({"a": a, "b": b})
    assert list(m.index) == ["a", "b"] and list(m.columns) == ["a", "b"]
    assert pd.isna(m.loc["a", "a"]) and pd.isna(m.loc["b", "b"])
    assert m.loc["a", "b"] == pytest.approx(1.0)  # entro 15 min, stesso giorno/lato


# ===========================================================================
# Candidato 5 — Ritorno alla media sul VWAP
# ===========================================================================

def test_vwap_sigma_definition_hand_computed():
    day = _bars("2026-03-10 13:30", [(100, 100, 100, 100), (104, 104, 104, 104)], vol=1.0)
    vs = vwap._vwap_sigma(day)
    assert vs["vwap"].iloc[0] == pytest.approx(100.0) and vs["sigma"].iloc[0] == pytest.approx(0.0)
    # tp=[100,104], vol=[1,1]: vwap=102, var = (100^2+104^2)/2 - 102^2 = 10408-10404 = 4 -> sigma=2
    assert vs["vwap"].iloc[1] == pytest.approx(102.0) and vs["sigma"].iloc[1] == pytest.approx(2.0)


def _vwap_warmup_and_jump(p: float, d: float, n_warmup: int = 9) -> pd.DataFrame:
    """n_warmup barre piatte a `p` (09:30 in poi) + una barra "salto" a p+d esattamente alle 10:00 ET (m=600)
    + una barra d'ingresso alle 10:01. Con n_warmup=9: sigma = d*sqrt(9)/10 = 0,3d < d/4 di soglia -> il
    salto rompe sempre 2 sigma (vedi calcolo nella docstring del modulo test)."""
    warmup = _bars("2026-03-10 13:30", [(p, p, p, p)] * n_warmup)  # 09:30 + n_warmup-1 min, tutte < 10:00
    jump = _bars("2026-03-10 14:00", [(p + d, p + d, p + d, p + d)])  # 10:00 ET esatto, barra doji: tp = chiusura
    entry = _bars("2026-03-10 14:01", [(p + d, p + d, p + d, p + d)])
    return pd.concat([warmup, jump, entry])


def test_vwap_events_short_when_close_breaks_two_sigma_above():
    day = _vwap_warmup_and_jump(p=100.0, d=100.0)  # vwap=110, sigma=30, soglia sopra=170, chiusura=200
    evs = vwap.vwap_events(day, SD, CFG, atr_prev_day=10.0)
    assert len(evs) == 1
    ev = evs[0]
    assert ev["side"] == "short"
    assert ev["vwap"] == pytest.approx(110.0) and ev["sigma"] == pytest.approx(30.0)
    assert ev["entry_ref_price"] == pytest.approx(200.0)
    assert ev["entry_price"] == pytest.approx(200.0)
    assert ev["atr"] == 10.0


def test_vwap_events_long_mirrors_short():
    day = _vwap_warmup_and_jump(p=200.0, d=-100.0)  # vwap=190, sigma=30, soglia sotto=130, chiusura=100
    evs = vwap.vwap_events(day, SD, CFG, atr_prev_day=10.0)
    assert len(evs) == 1
    ev = evs[0]
    assert ev["side"] == "long"
    assert ev["vwap"] == pytest.approx(190.0) and ev["sigma"] == pytest.approx(30.0)
    assert ev["entry_ref_price"] == pytest.approx(100.0)


def _vwap_ev(side: str, entry_ref: float, vwap_val: float, atr: float | None) -> dict:
    return dict(event_id=f"{SD}_{side}", session_date=SD, side=side,
                signal_ts=pd.Timestamp("2026-03-10 14:00", tz="UTC"), entry_ref_price=entry_ref,
                entry_ts=pd.Timestamp("2026-03-10 14:01", tz="UTC"), entry_price=entry_ref,
                vwap=vwap_val, sigma=30.0, atr=atr)


def test_vwap_geometries_hand_computed_short():
    rows = {r["geom"]: r for r in vwap.geometries(_vwap_ev("short", entry_ref=200.0, vwap_val=110.0, atr=10.0), CFG)}
    assert set(rows) == {"TVWAP_A1.0", "TVWAP_A1.5", "TVWAP_A2.0", "TMID_A1.0", "TMID_A1.5", "TMID_A2.0"}
    # TVWAP = 110 (ritorno pieno); stop = e - u*k*A = 200 + k*10 (u=-1)
    assert rows["TVWAP_A1.0"]["stop_price"] == 210.0 and rows["TVWAP_A1.0"]["target_price"] == 110.0
    assert rows["TVWAP_A1.0"]["rr_ratio"] == pytest.approx(9.0)  # |110-200|/|200-210| = 90/10
    # TMID = meta' strada fra e=200 e vwap=110 -> 155
    assert rows["TMID_A2.0"]["stop_price"] == 220.0 and rows["TMID_A2.0"]["target_price"] == 155.0
    assert rows["TMID_A2.0"]["rr_ratio"] == pytest.approx(2.25)  # |155-200|/|200-220| = 45/20


def test_vwap_geometries_long_mirrors_short_rr():
    long_rows = {r["geom"]: r for r in vwap.geometries(_vwap_ev("long", entry_ref=100.0, vwap_val=190.0, atr=10.0), CFG)}
    assert long_rows["TVWAP_A1.0"]["stop_price"] == 90.0 and long_rows["TVWAP_A1.0"]["target_price"] == 190.0
    assert long_rows["TVWAP_A1.0"]["rr_ratio"] == pytest.approx(9.0)  # stesso |rr| della coppia short


def test_vwap_geometries_empty_when_atr_missing():
    assert vwap.geometries(_vwap_ev("short", 200.0, 110.0, atr=None), CFG) == []


# ===========================================================================
# Candidato 6 — Tenuta overnight
# ===========================================================================

def test_overnight_event_hand_computed():
    entry_rth = _bars("2026-03-10 13:30", [(99, 100, 99, 100)])  # chiusura RTH = 100
    exit_rth = _bars("2026-03-11 13:30", [(105, 106, 104, 105.5)])  # apertura RTH successiva = 105
    ev = overnight.overnight_event(entry_rth, SD, exit_rth, dt.date(2026, 3, 11), CFG, atr_prev_day=10.0)
    assert ev["side"] == "long" and ev["entry_price"] == 100.0 and ev["entry_ref_price"] == 100.0
    assert ev["next_open_price"] == 105.0 and ev["next_open_ts"] == exit_rth.index[0]
    assert ev["atr"] == 10.0 and ev["event_id"] == f"{SD}_overnight"


def test_overnight_event_none_when_a_day_has_no_rth_bars():
    entry_rth = _bars("2026-03-10 13:30", [(99, 100, 99, 100)])
    empty = pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
    assert overnight.overnight_event(entry_rth, SD, empty, dt.date(2026, 3, 11), CFG, 10.0) is None


def test_overnight_span_bounds_are_exclusive_then_inclusive():
    entry_full = _bars("2026-03-10 19:59", [(100, 100, 100, 100), (100, 100, 100, 100)])  # 15:59 e 16:00 ET
    entry_ts = entry_full.index[0]
    exit_full = _bars("2026-03-10 22:00", [(101, 101, 101, 101), (105, 105, 105, 105)])  # ON + apertura RTH succ.
    next_open_ts = exit_full.index[-1]
    span = overnight.overnight_span(entry_full, entry_ts, exit_full, next_open_ts)
    assert list(span.index) == [entry_full.index[1], exit_full.index[0], exit_full.index[1]]


def test_overnight_geometries_hand_computed():
    ev = dict(entry_ref_price=100.0, atr=10.0)
    rows = {r["geom"]: r for r in overnight.geometries(ev, CFG)}
    assert set(rows) == {"S1.0_T1.0", "S1.0_T2.0", "S2.0_T1.0", "S2.0_T2.0"}
    assert rows["S1.0_T1.0"]["stop_price"] == 90.0 and rows["S1.0_T1.0"]["target_price"] == 110.0
    assert rows["S1.0_T1.0"]["rr_ratio"] == pytest.approx(1.0)
    assert rows["S2.0_T1.0"]["stop_price"] == 80.0 and rows["S2.0_T1.0"]["rr_ratio"] == pytest.approx(0.5)


def _on_row(entry_price=100.0, stop=90.0, target=110.0) -> dict:
    return dict(event_id=f"{SD}_overnight", side="long", entry_ts=pd.Timestamp("2026-03-10 20:00", tz="UTC"),
                entry_price=entry_price, stop_price=stop, target_price=target)


def test_label_overnight_event_stop_hit_in_span():
    span = _bars("2026-03-10 21:00", [(95, 96, 85, 90)])  # low=85 <= stop=90
    lab = overnight.label_overnight_event(_on_row(), span, CFG)
    assert lab["label"] == 0 and lab["exit_reason"] == "stop" and lab["exit_price_raw"] == 90.0


def test_label_overnight_event_target_hit_in_span():
    span = _bars("2026-03-10 21:00", [(95, 115, 94, 112)])  # high=115 >= target=110
    lab = overnight.label_overnight_event(_on_row(), span, CFG)
    assert lab["label"] == 1 and lab["exit_reason"] == "target" and lab["exit_price_raw"] == 110.0


def test_label_overnight_event_closes_at_next_open_not_close_when_untouched():
    # nessuno dei due livelli toccato entro la barra di apertura RTH successiva (ultima dello span):
    # l'esito e' "time", chiuso all'APERTURA di quella barra (102), non alla sua chiusura (104) — la
    # deroga del candidato 6.
    span = pd.concat([
        _bars("2026-03-10 21:00", [(100, 101, 99, 100)]),   # overnight piatto, nessun hit
        _bars("2026-03-11 13:30", [(102, 103, 101, 104)]),  # apertura RTH successiva: open=102, close=104
    ])
    lab = overnight.label_overnight_event(_on_row(), span, CFG)
    assert lab["label"] == 0 and lab["exit_reason"] == "time"
    assert lab["exit_price_raw"] == 102.0  # apertura, non 104 (chiusura)


def test_label_overnight_event_no_bars_in_span():
    lab = overnight.label_overnight_event(_on_row(), pd.DataFrame(columns=["open", "high", "low", "close"]), CFG)
    assert lab["label"] == 0 and lab["exit_reason"] == "no_bars"


# ===========================================================================
# Candidato 7 — Momentum dell'ultima ora
# ===========================================================================

def _lasthour_day(close_1500: float, open_rth: float = 100.0, entry_open: float | None = None) -> pd.DataFrame:
    entry_open = close_1500 + 0.5 if entry_open is None else entry_open
    open_bar = _bars("2026-03-10 13:30", [(open_rth, open_rth, open_rth, open_rth)])
    signal_bar = _bars("2026-03-10 19:00", [(close_1500, close_1500, close_1500, close_1500)])  # 15:00 ET
    entry_bar = _bars("2026-03-10 19:01", [(entry_open, entry_open, entry_open, entry_open)])
    return pd.concat([open_bar, signal_bar, entry_bar])


def test_lasthour_event_long_when_session_up():
    day = _lasthour_day(close_1500=105.0)
    ev = lasthour.lasthour_event(day, SD, CFG, atr_prev_day=10.0)
    assert ev["side"] == "long" and ev["entry_ref_price"] == 105.0 and ev["rth_open_price"] == 100.0
    assert ev["entry_price"] == 105.5 and ev["atr"] == 10.0


def test_lasthour_event_short_mirrors_long():
    day = _lasthour_day(close_1500=95.0, entry_open=94.5)
    ev = lasthour.lasthour_event(day, SD, CFG, atr_prev_day=10.0)
    assert ev["side"] == "short" and ev["entry_ref_price"] == 95.0


def test_lasthour_event_none_when_flat():
    day = _lasthour_day(close_1500=100.0, entry_open=100.0)
    assert lasthour.lasthour_event(day, SD, CFG, atr_prev_day=10.0) is None


def test_lasthour_event_none_when_missing_1500_bar():
    day = _bars("2026-03-10 13:30", [(100, 100, 100, 100)] * 5)  # nessuna barra alle 15:00
    assert lasthour.lasthour_event(day, SD, CFG, atr_prev_day=10.0) is None


def _lh_ev(side: str, entry_ref: float, atr: float) -> dict:
    return dict(event_id=f"{SD}_{side}", session_date=SD, side=side, entry_ref_price=entry_ref, atr=atr,
                signal_ts=pd.Timestamp("2026-03-10 19:00", tz="UTC"), rth_open_price=100.0,
                entry_ts=pd.Timestamp("2026-03-10 19:01", tz="UTC"), entry_price=entry_ref)


def test_lasthour_geometries_hand_computed_long():
    rows = {r["geom"]: r for r in lasthour.geometries(_lh_ev("long", entry_ref=105.0, atr=10.0), CFG)}
    assert set(rows) == {"S0.5_T0.5", "S0.5_T1.0", "S1.0_T0.5", "S1.0_T1.0"}
    assert rows["S0.5_T0.5"]["stop_price"] == 100.0 and rows["S0.5_T0.5"]["target_price"] == 110.0
    assert rows["S0.5_T0.5"]["rr_ratio"] == pytest.approx(1.0)
    assert rows["S1.0_T1.0"]["stop_price"] == 95.0 and rows["S1.0_T1.0"]["rr_ratio"] == pytest.approx(1.0)


def test_lasthour_geometries_short_mirrors_long_rr():
    long_rows = {r["geom"]: r for r in lasthour.geometries(_lh_ev("long", 105.0, 10.0), CFG)}
    short_rows = {r["geom"]: r for r in lasthour.geometries(_lh_ev("short", 95.0, 10.0), CFG)}
    assert short_rows["S0.5_T0.5"]["stop_price"] == 100.0 and short_rows["S0.5_T0.5"]["target_price"] == 90.0
    for geom in long_rows:
        assert long_rows[geom]["rr_ratio"] == pytest.approx(short_rows[geom]["rr_ratio"])


# ===========================================================================
# Candidato 8 — Apertura fuori dalla value area di ieri
# ===========================================================================

def _prev_day_rth_with_known_va() -> pd.DataFrame:
    """Stessa forma di VA di tests/test_screen.py::_on_bars_with_known_va, sulla sessione RTH intera:
    poc=100.0, vah=100.0, val=99.5 (w=0.5)."""
    entries = [(99.5, 1.0), (99.75, 3.0), (100.0, 10.0), (100.25, 2.0), (100.5, 1.0)]
    idx = pd.date_range("2026-03-09 13:30", periods=len(entries), freq="1min", tz="UTC")
    p = [e[0] for e in entries]
    v = [e[1] for e in entries]
    return pd.DataFrame({"open": p, "high": p, "low": p, "close": p, "volume": v}, index=idx)


def test_prev_day_value_area_hand_computed():
    va = prevva.prev_day_value_area(_prev_day_rth_with_known_va(), CFG)
    assert va.vah == 100.0 and va.val == 99.5 and va.poc == 100.0


def test_prevva_events_above_yesterday_va():
    va = prevva.prev_day_value_area(_prev_day_rth_with_known_va(), CFG)
    day = _bars("2026-03-10 13:30", [(105, 105, 105, 105), (106, 106, 106, 106)])
    evs = {e["family"]: e for e in prevva.prevva_events(day, SD, CFG, va)}
    assert set(evs) == {"R", "C"}
    assert evs["R"]["side"] == "short" and evs["C"]["side"] == "long"
    assert evs["R"]["nearest_edge"] == 100.0 and evs["R"]["w"] == pytest.approx(0.5)
    assert evs["R"]["entry_ref_price"] == 105.0 and evs["R"]["entry_price"] == 106.0


def test_prevva_events_below_yesterday_va_mirrors_above():
    va = prevva.prev_day_value_area(_prev_day_rth_with_known_va(), CFG)
    day = _bars("2026-03-10 13:30", [(95, 95, 95, 95), (94, 94, 94, 94)])
    evs = {e["family"]: e for e in prevva.prevva_events(day, SD, CFG, va)}
    assert evs["R"]["side"] == "long" and evs["C"]["side"] == "short"
    assert evs["R"]["nearest_edge"] == 99.5


def test_prevva_events_empty_when_open_inside_va():
    va = prevva.prev_day_value_area(_prev_day_rth_with_known_va(), CFG)
    day = _bars("2026-03-10 13:30", [(99.75, 99.75, 99.75, 99.75), (99.75, 99.75, 99.75, 99.75)])
    assert prevva.prevva_events(day, SD, CFG, va) == []


def _pv_ev(family: str, side: str, entry_ref: float, edge: float, w: float) -> dict:
    return dict(event_id=f"{SD}_{family}", session_date=SD, family=family, side=side,
                signal_ts=pd.Timestamp("2026-03-10 13:30", tz="UTC"), entry_ref_price=entry_ref,
                entry_ts=pd.Timestamp("2026-03-10 13:31", tz="UTC"), entry_price=entry_ref,
                vah_prec=100.0, val_prec=99.5, w=w, nearest_edge=edge)


def test_prevva_geometries_family_r_hand_computed():
    rows = {r["geom"]: r for r in prevva.geometries(_pv_ev("R", "short", entry_ref=105.0, edge=100.0, w=0.5), CFG)}
    assert set(rows) == {"R_K0.25", "R_K0.5", "R_K0.75", "R_K1.0"}
    # target fisso = 100 (bordo piu' vicino); stop = e - u*k*w = 105 + k*0.5 (u=-1)
    assert rows["R_K1.0"]["target_price"] == 100.0 and rows["R_K1.0"]["stop_price"] == 105.5
    assert rows["R_K1.0"]["rr_ratio"] == pytest.approx(5.0 / 0.5)


def test_prevva_geometries_family_c_hand_computed():
    rows = {r["geom"]: r for r in prevva.geometries(_pv_ev("C", "long", entry_ref=105.0, edge=100.0, w=0.5), CFG)}
    assert set(rows) == {"C_K0.25", "C_K0.5", "C_K0.75", "C_K1.0"}
    # stop fisso = 100 (bordo piu' vicino); target = e + u*k*w = 105 + k*0.5 (u=+1)
    assert rows["C_K1.0"]["stop_price"] == 100.0 and rows["C_K1.0"]["target_price"] == 105.5
    assert rows["C_K1.0"]["rr_ratio"] == pytest.approx(0.5 / 5.0)
