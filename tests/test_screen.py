"""Test del muro per i candidati 2, 3 e 4 dello screening (pre-registrazione
`docs/superpowers/specs/2026-09-22-screening-candidati-2-3-4.md`) e per il modulo condiviso `nqml.screen.wall`."""
import datetime as dt

import pandas as pd
import pytest

from nqml.config import load_config
from nqml.screen import firsthour, gap, vabreak
from nqml.screen.wall import geometry_row, wall_test

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
# nqml.screen.wall — modulo condiviso
# ===========================================================================

def test_wall_test_g_exactly_zero_by_construction():
    df = pd.DataFrame({
        "session_date": [dt.date(2026, 3, 10), dt.date(2026, 3, 11)],
        "label": [1, 0], "rr_ratio": [1.0, 1.0],  # prior 0.5 ciascuno: d = +0.5 e -0.5, somma 0
    })
    out = wall_test(df, n_boot=200, seed=0, alphas=[0.05])
    assert out["n"] == 2
    assert out["g"] == 0.0


def test_wall_test_known_positive_value_with_deterministic_ci():
    # ogni giorno ha la stessa coppia (d_sum, n): qualunque ricampionamento a blocchi per giorno da'
    # sempre lo stesso rapporto -> CI collassa esattamente sul punto, nessuna casualita' nell'asserzione.
    days = [dt.date(2026, 3, d) for d in (10, 11, 12)]
    rows = [dict(session_date=d, label=1, rr_ratio=1.0) for d in days for _ in range(2)]  # d = +0.5 per evento
    df = pd.DataFrame(rows)
    out = wall_test(df, n_boot=50, seed=0, alphas=[0.05, 0.0016666667])
    assert out["g"] == pytest.approx(0.5)
    for alpha in (0.05, 0.0016666667):
        lo, hi = out["ci"][alpha]
        assert lo == pytest.approx(0.5) and hi == pytest.approx(0.5)


def test_geometry_row_flags_m1_m2_pass_m3_fail_below_n():
    days = [dt.date(2026, 3, d) for d in (10, 11, 12)]
    rows = [dict(session_date=d, label=1, rr_ratio=1.0, realized_R=0.3) for d in days for _ in range(2)]
    df = pd.DataFrame(rows)
    row = geometry_row("G1", df, n_boot=50, seed=0, alpha_m1=0.05, alpha_m2=0.0016666667, m3_min_n=500)
    assert row["n"] == 6 and row["g"] == pytest.approx(0.5)
    assert row["m1"] is True and row["m2"] is True and row["m3"] is False  # n=6 < 500
    assert row["ev_no_cost"] == pytest.approx(1.0)  # label*rr - (1-label) = 1*1 - 0
    assert row["mean_r"] == pytest.approx(0.3)


def test_geometry_row_empty_frame_is_all_fail():
    row = geometry_row("G1", pd.DataFrame(columns=["session_date", "label", "rr_ratio", "realized_R"]),
                        50, 0, 0.05, 0.00167, 500)
    assert row["n"] == 0 and row["m1"] is False and row["m2"] is False and row["m3"] is False


# ===========================================================================
# Candidato 2 — Gap di apertura
# ===========================================================================

def test_gap_event_hand_computed():
    day_rth = _bars("2026-03-10 13:30", [(105, 105, 105, 105), (104, 104, 104, 104), (104, 104, 104, 104)])
    ev = gap.gap_event(day_rth, SD, prev_close=100.0, cfg=CFG)
    assert ev is not None
    assert ev["gap"] == 5.0 and ev["prev_close"] == 100.0
    assert ev["entry_ref_price"] == 105.0  # apertura RTH
    assert ev["entry_ts"] == pd.Timestamp("2026-03-10 13:31", tz="UTC")
    assert ev["entry_price"] == 104.0  # apertura della barra 1m successiva
    assert ev["event_id"] == f"{SD}_gap"


def test_gap_event_none_when_no_prev_close_or_gap_too_small_or_no_next_bar():
    day_rth = _bars("2026-03-10 13:30", [(105, 105, 105, 105), (104, 104, 104, 104)])
    assert gap.gap_event(day_rth, SD, prev_close=None, cfg=CFG) is None
    small_gap = _bars("2026-03-10 13:30", [(101, 101, 101, 101), (101, 101, 101, 101)])
    assert gap.gap_event(small_gap, SD, prev_close=100.0, cfg=CFG) is None  # |gap|=1 < 2
    one_bar = _bars("2026-03-10 13:30", [(105, 105, 105, 105)])
    assert gap.gap_event(one_bar, SD, prev_close=100.0, cfg=CFG) is None  # nessuna barra d'ingresso


def test_gap_event_none_when_entry_after_last_entry():
    # 15:30 ET = 19:30 UTC: l'apertura "RTH" simulata qui e' gia' alle 15:30, l'ingresso (15:31) e' escluso.
    late = _bars("2026-03-10 19:30", [(105, 105, 105, 105), (104, 104, 104, 104)])
    assert gap.gap_event(late, SD, prev_close=100.0, cfg=CFG) is None


def _gap_ev(entry_ref: float, gap_val: float, prev_close: float) -> dict:
    return dict(event_id=f"{SD}_gap", session_date=SD, open_ts=pd.Timestamp("2026-03-10 13:30", tz="UTC"),
                entry_ref_price=entry_ref, entry_ts=pd.Timestamp("2026-03-10 13:31", tz="UTC"),
                entry_price=entry_ref, gap=gap_val, prev_close=prev_close)


def test_gap_geometries_hand_computed_up_gap():
    rows = {r["geom"]: r for r in gap.geometries(_gap_ev(entry_ref=105.0, gap_val=5.0, prev_close=100.0), CFG)}
    assert set(rows) == {"F_k0.5", "F_k1", "F_k2", "P_k0.5", "P_k1", "P_k2"}
    # F (chiusura del gap, verso C=100, sotto e=105) e' short: stop = e + k*G
    f1 = rows["F_k1"]
    assert f1["side"] == "short" and f1["target_price"] == 100.0 and f1["stop_price"] == 110.0
    assert abs(f1["rr_ratio"] - 1.0) < 1e-9  # rr = 1/k = 1
    # P (prosecuzione, nella direzione del gap, in su) e' long: target = e + k*G, stop = C
    p1 = rows["P_k1"]
    assert p1["side"] == "long" and p1["target_price"] == 110.0 and p1["stop_price"] == 100.0
    assert abs(p1["rr_ratio"] - 1.0) < 1e-9  # rr = k = 1


def test_gap_geometries_mirror_on_down_gap():
    rows = {r["geom"]: r for r in gap.geometries(_gap_ev(entry_ref=95.0, gap_val=-5.0, prev_close=100.0), CFG)}
    # direzioni ribaltate rispetto al gap in su, stesso |rr| per costruzione (dipende solo da |gap| e k)
    assert rows["F_k1"]["side"] == "long" and rows["F_k1"]["target_price"] == 100.0 and rows["F_k1"]["stop_price"] == 90.0
    assert rows["P_k1"]["side"] == "short" and rows["P_k1"]["target_price"] == 90.0 and rows["P_k1"]["stop_price"] == 100.0
    for k in ("F_k0.5", "F_k1", "F_k2", "P_k0.5", "P_k1", "P_k2"):
        up = {r["geom"]: r for r in gap.geometries(_gap_ev(105.0, 5.0, 100.0), CFG)}
        assert abs(rows[k]["rr_ratio"] - up[k]["rr_ratio"]) < 1e-9


# ===========================================================================
# Candidato 3 — Estremi della prima ora
# ===========================================================================

def _flat_fh(high: float, low: float, close: float, n: int = 60) -> pd.DataFrame:
    return _bars("2026-03-10 13:30", [(close, high, low, close)] * n)


def test_first_hour_range_uses_only_first_60_minutes():
    fh_bars = _bars("2026-03-10 13:30", [(100, 101, 99, 100), (100, 102, 98, 100)] + [(100, 100, 100, 100)] * 58)
    after = _bars("2026-03-10 14:30", [(100, 200, 1, 100), (100, 200, 1, 100)])
    day = pd.concat([fh_bars, after])
    fhh, fhl = firsthour.first_hour_range(day)
    assert fhh == 102.0 and fhl == 98.0


def test_first_hour_range_none_if_incomplete():
    day = _bars("2026-03-10 13:30", [(100, 101, 99, 100)] * 30)  # solo 30 barre, ne servono 60
    assert firsthour.first_hour_range(day) is None


def test_firsthour_events_fires_first_breakout_per_side_and_ignores_later_ones():
    fh_bars = _flat_fh(high=101, low=99, close=100)
    after = _bars("2026-03-10 14:30", [
        (100, 100.5, 99.5, 100),     # 10:30 dentro il range, nessun evento
        (100, 102.5, 101.8, 102),    # 10:31 chiude sopra FHH=101 -> evento long
        (100, 103.0, 102.5, 102.8),  # 10:32 barra d'ingresso del long
        (100, 105, 104, 104.5),      # 10:33 ancora sopra: NON un secondo evento long
        (100, 100, 98.0, 98.5),      # 10:34 chiude sotto FHL=99 -> evento short
        (100, 99, 97, 97.5),         # 10:35 barra d'ingresso dello short
    ])
    day = pd.concat([fh_bars, after])
    evs = firsthour.firsthour_events(day, SD, CFG)
    assert len(evs) == 2
    long_ev = next(e for e in evs if e["side"] == "long")
    short_ev = next(e for e in evs if e["side"] == "short")
    assert long_ev["fhh"] == 101.0 and long_ev["fhl"] == 99.0 and long_ev["fh_range"] == 2.0
    assert long_ev["break_ts"] == pd.Timestamp("2026-03-10 14:31", tz="UTC")
    assert long_ev["entry_ref_price"] == 102.0
    assert long_ev["entry_ts"] == pd.Timestamp("2026-03-10 14:32", tz="UTC") and long_ev["entry_price"] == 100.0
    assert short_ev["entry_ref_price"] == 98.5


def test_firsthour_events_skips_breakout_after_last_entry():
    fh_bars = _flat_fh(high=101, low=99, close=100)
    late = _bars("2026-03-10 19:30", [(100, 102, 101.5, 102), (100, 102, 101.5, 102)])  # 15:30 ET
    day = pd.concat([fh_bars, late])
    assert firsthour.firsthour_events(day, SD, CFG) == []


def _fh_ev(side: str, entry_ref: float) -> dict:
    return dict(event_id=f"{SD}_{side}", session_date=SD, side=side,
                break_ts=pd.Timestamp("2026-03-10 14:31", tz="UTC"), entry_ref_price=entry_ref,
                entry_ts=pd.Timestamp("2026-03-10 14:32", tz="UTC"), entry_price=entry_ref,
                fhh=101.0, fhl=99.0, fh_range=2.0, minutes_since_open=61.0)


def test_firsthour_geometries_hand_computed_long():
    rows = {r["geom"]: r for r in firsthour.geometries(_fh_ev("long", entry_ref=101.5), CFG)}
    assert len(rows) == 8
    # S1 largo = FHL - 1 tick = 98.75; denom = |101.5-98.75| = 2.75
    assert rows["S1_T1"]["stop_price"] == 98.75 and rows["S1_T1"]["target_price"] == 103.5
    assert abs(rows["S1_T1"]["rr_ratio"] - 2.0 / 2.75) < 1e-9
    # S2 stretto = FHH - 1 tick = 100.75
    assert rows["S2_T1"]["stop_price"] == 100.75 and rows["S2_T1"]["target_price"] == 103.5


def test_firsthour_geometries_short_mirrors_long_rr():
    long_rows = {r["geom"]: r for r in firsthour.geometries(_fh_ev("long", entry_ref=101.5), CFG)}
    short_rows = {r["geom"]: r for r in firsthour.geometries(_fh_ev("short", entry_ref=98.5), CFG)}
    assert short_rows["S1_T1"]["stop_price"] == 101.25 and short_rows["S2_T1"]["stop_price"] == 99.25
    for geom in long_rows:
        assert abs(long_rows[geom]["rr_ratio"] - short_rows[geom]["rr_ratio"]) < 1e-9


# ===========================================================================
# Candidato 4 — Prosecuzione della value area
# ===========================================================================

def _on_bars_with_known_va() -> pd.DataFrame:
    """5 barre ON, una per livello, volumi [1,3,10,10,2,1] sui livelli [99.5..100.5] passo 0.25 di tick:
    stessa forma di tests/test_volume_profile.py::test_value_area_hand_computed (traslata a ~100), con
    VA risultante poc=100.0, vah=100.0, val=99.5 (w=0.5)."""
    entries = [(99.5, 1.0), (99.75, 3.0), (100.0, 10.0), (100.25, 2.0), (100.5, 1.0)]
    idx = pd.date_range("2026-03-09 22:00", periods=len(entries), freq="1min", tz="UTC")
    p = [e[0] for e in entries]
    v = [e[1] for e in entries]
    return pd.DataFrame({"open": p, "high": p, "low": p, "close": p, "volume": v}, index=idx)


def test_vabreak_events_fires_at_first_break_even_without_reentry():
    on = _on_bars_with_known_va()
    rth_a = _bars("2026-03-10 13:30", [(100, 100, 100, 100)] * 5)          # 09:30-09:34: dentro la VA (val=99.5, vah=100.0)
    rth_b = _bars("2026-03-10 13:35", [(90, 90, 90, 90)] * 5)              # 09:35-09:39: rompe sotto val -> BROKEN
    rth_c = _bars("2026-03-10 13:40", [(90, 90, 90, 90)] * 380)            # 09:40-15:59: resta fuori per sempre (MAI rientra)
    day = pd.concat([on, rth_a, rth_b, rth_c])

    evs = vabreak.vabreak_events(day, SD, CFG)
    on_evs = [e for e in evs if e["va_type"] == "ON"]
    assert len(on_evs) == 1  # un solo evento ON, benche' il prezzo non sia mai rientrato nella VA
    e = on_evs[0]
    assert e["side"] == "short"  # rottura in giu' -> prosecuzione short
    assert e["break_ts"] == pd.Timestamp("2026-03-10 13:40", tz="UTC")  # chiusura della barra 5m di rottura
    assert e["entry_ref_price"] == 90.0
    assert e["entry_ts"] == pd.Timestamp("2026-03-10 13:40", tz="UTC") and e["entry_price"] == 90.0
    assert e["vah"] == 100.0 and e["val"] == 99.5 and e["poc"] == 100.0 and e["w"] == 0.5
    assert e["event_id"] == f"{SD}_ON_short"


def _va_ev(side: str, entry_ref: float, vah: float, val: float, poc: float, w: float) -> dict:
    return dict(event_id=f"{SD}_ON_{side}", session_date=SD, va_type="ON", side=side,
                break_ts=pd.Timestamp("2026-03-10 13:40", tz="UTC"), entry_ref_price=entry_ref,
                entry_ts=pd.Timestamp("2026-03-10 13:40", tz="UTC"), entry_price=entry_ref,
                vah=vah, val=val, poc=poc, w=w)


def test_vabreak_geometries_hand_computed_short():
    ev = _va_ev("short", entry_ref=90.0, vah=100.0, val=99.5, poc=100.0, w=0.5)
    rows = {r["geom"]: r for r in vabreak.geometries(ev, CFG)}
    assert set(rows) == {"S1_T0.25", "S1_T0.5", "S1_T0.75", "S1_T1.0", "S2_T0.25", "S2_T0.5", "S2_T0.75", "S2_T1.0"}
    # S1 rientro = val + tick = 99.75; S2 POC = poc + tick = 100.25 (rottura in giu')
    assert rows["S1_T1.0"]["stop_price"] == 99.75 and rows["S1_T1.0"]["target_price"] == 89.5
    assert abs(rows["S1_T1.0"]["rr_ratio"] - 0.5 / 9.75) < 1e-9
    assert rows["S2_T1.0"]["stop_price"] == 100.25 and rows["S2_T1.0"]["target_price"] == 89.5
    assert abs(rows["S2_T1.0"]["rr_ratio"] - 0.5 / 10.25) < 1e-9


def test_vabreak_geometries_hand_computed_long_mirrors_short():
    ev = _va_ev("long", entry_ref=110.0, vah=100.0, val=99.5, poc=99.75, w=0.5)
    rows = {r["geom"]: r for r in vabreak.geometries(ev, CFG)}
    # S1 rientro = vah - tick = 99.75; S2 POC = poc - tick = 99.5 (rottura in su)
    assert rows["S1_T1.0"]["stop_price"] == 99.75 and rows["S1_T1.0"]["target_price"] == 110.5
    assert abs(rows["S1_T1.0"]["rr_ratio"] - 0.5 / 10.25) < 1e-9
    assert rows["S2_T1.0"]["stop_price"] == 99.5 and rows["S2_T1.0"]["target_price"] == 110.5
    assert abs(rows["S2_T1.0"]["rr_ratio"] - 0.5 / 10.5) < 1e-9
