"""Test dell'ORB15 (pre-registrazione `docs/superpowers/specs/2026-09-22-screening-nuovi-setup.md`, §2):
opening range, rilevazione della rottura, le 8 geometrie del muro."""
import datetime as dt

import pandas as pd

from nqml.config import load_config
from nqml.screen.orb import geometries, opening_range, orb_events

CFG = load_config("config.yaml")
SD = dt.date(2026, 3, 10)  # 2026-03-10: EDT, 09:30 NY = 13:30 UTC (stessa convenzione di tests/synthetic.py)


def _bars(start_utc: str, specs: list[tuple[float, float, float, float]]) -> pd.DataFrame:
    """specs: lista di (open, high, low, close) -> barre 1m consecutive da start_utc."""
    idx = pd.date_range(start_utc, periods=len(specs), freq="1min", tz="UTC")
    o = [s[0] for s in specs]
    h = [s[1] for s in specs]
    l = [s[2] for s in specs]
    c = [s[3] for s in specs]
    return pd.DataFrame({"open": o, "high": h, "low": l, "close": c, "volume": 1.0}, index=idx)


def _flat_or(high: float, low: float, close: float, n: int = 15) -> pd.DataFrame:
    """15 barre 1m da 09:30 UTC 13:30, opening range fisso."""
    return _bars("2026-03-10 13:30", [(close, high, low, close)] * n)


# ---------------------------------------------------------------------------
# opening_range
# ---------------------------------------------------------------------------

def test_opening_range_uses_only_first_minutes_bars():
    or_bars = _bars("2026-03-10 13:30", [
        (100, 101, 99, 100), (100, 102, 98, 100), (100, 100.5, 99.5, 100),
        (100, 100, 100, 100), (100, 100, 100, 100), (100, 100, 100, 100),
        (100, 100, 100, 100), (100, 100, 100, 100), (100, 100, 100, 100),
        (100, 100, 100, 100), (100, 100, 100, 100), (100, 100, 100, 100),
        (100, 100, 100, 100), (100, 100, 100, 100), (100, 100, 100, 100),
    ])
    # barre successive (09:45+) con estremi molto piu' larghi: non devono contare nell'OR.
    after = _bars("2026-03-10 13:45", [(100, 200, 1, 100), (100, 200, 1, 100)])
    day = pd.concat([or_bars, after])
    orh, orl = opening_range(day)
    assert orh == 102.0 and orl == 98.0


def test_opening_range_none_if_incomplete():
    day = _bars("2026-03-10 13:30", [(100, 101, 99, 100)] * 10)  # solo 10 barre, ne servono 15
    assert opening_range(day) is None


# ---------------------------------------------------------------------------
# orb_events
# ---------------------------------------------------------------------------

def test_orb_events_fires_first_breakout_per_side_and_ignores_later_ones():
    or_bars = _flat_or(high=101, low=99, close=100)
    after = _bars("2026-03-10 13:45", [
        (100, 100.5, 99.5, 100),    # 09:45 dentro il range, nessun evento
        (100, 102.5, 101.8, 102),   # 09:46 chiude sopra ORH=101 -> evento long
        (100, 103.0, 102.5, 102.8),  # 09:47 barra d'ingresso del long (open=100? usato come next.open sotto)
        (100, 105, 104, 104.5),     # 09:48 ancora sopra: NON deve generare un secondo evento long
        (100, 100, 98.0, 98.5),     # 09:49 chiude sotto ORL=99 -> evento short
        (100, 99, 97, 97.5),        # 09:50 barra d'ingresso dello short
        (100, 90, 89, 89.5),        # 09:51 ancora sotto: NON deve generare un secondo evento short
    ])
    day = pd.concat([or_bars, after])
    evs = orb_events(day, SD, CFG)

    assert len(evs) == 2
    long_ev = next(e for e in evs if e["side"] == "long")
    short_ev = next(e for e in evs if e["side"] == "short")

    assert long_ev["event_id"] == f"{SD}_long"
    assert long_ev["orh"] == 101.0 and long_ev["orl"] == 99.0 and long_ev["or_range"] == 2.0
    assert long_ev["break_ts"] == pd.Timestamp("2026-03-10 13:46", tz="UTC")
    assert long_ev["entry_ref_price"] == 102.0  # close della barra di rottura
    assert long_ev["entry_ts"] == pd.Timestamp("2026-03-10 13:47", tz="UTC")
    assert long_ev["entry_price"] == 100.0  # open della barra successiva

    assert short_ev["break_ts"] == pd.Timestamp("2026-03-10 13:49", tz="UTC")
    assert short_ev["entry_ref_price"] == 98.5
    assert short_ev["entry_ts"] == pd.Timestamp("2026-03-10 13:50", tz="UTC")
    assert short_ev["entry_price"] == 100.0


def test_orb_events_no_breakout_returns_empty():
    or_bars = _flat_or(high=101, low=99, close=100)
    after = _bars("2026-03-10 13:45", [(100, 100.9, 99.1, 100)] * 20)  # non rompe mai l'OR
    day = pd.concat([or_bars, after])
    assert orb_events(day, SD, CFG) == []


def test_orb_events_incomplete_opening_range_returns_empty():
    day = _bars("2026-03-10 13:30", [(100, 101, 99, 100)] * 10)
    assert orb_events(day, SD, CFG) == []


def test_orb_events_skips_breakout_after_last_entry():
    or_bars = _flat_or(high=101, low=99, close=100)
    # 15:30 ET = 19:30 UTC: barra di rottura esattamente a 15:30, la barra d'ingresso (15:31) e' oltre
    # l'ultimo ingresso configurato (detector.last_entry = 15:30) -> l'evento va scartato.
    late = _bars("2026-03-10 19:30", [(100, 102, 101.5, 102), (100, 102, 101.5, 102)])
    day = pd.concat([or_bars, late])
    assert orb_events(day, SD, CFG) == []


def test_orb_events_no_next_bar_is_skipped():
    or_bars = _flat_or(high=101, low=99, close=100)
    # una sola barra dopo l'apertura, che rompe al rialzo, ma senza barra successiva per l'ingresso.
    after = _bars("2026-03-10 13:45", [(100, 102, 101.5, 102)])
    day = pd.concat([or_bars, after])
    assert orb_events(day, SD, CFG) == []


# ---------------------------------------------------------------------------
# geometries
# ---------------------------------------------------------------------------

def _ev(side: str, entry_ref: float) -> dict:
    return dict(event_id=f"{SD}_{side}", session_date=SD, side=side,
                break_ts=pd.Timestamp("2026-03-10 13:46", tz="UTC"), entry_ref_price=entry_ref,
                entry_ts=pd.Timestamp("2026-03-10 13:47", tz="UTC"), entry_price=entry_ref,
                orh=101.0, orl=99.0, or_range=2.0, minutes_since_open=16.0)


def test_geometries_long_hand_computed():
    rows = geometries(_ev("long", entry_ref=101.5), CFG)
    assert len(rows) == 8
    assert [r["geom"] for r in rows] == ["S1_T0.5", "S1_T1", "S1_T1.5", "S1_T2", "S2_T0.5", "S2_T1", "S2_T1.5", "S2_T2"]

    by_geom = {r["geom"]: r for r in rows}
    # S1 largo = ORL - 1 tick = 99 - 0.25 = 98.75; denom = |101.5 - 98.75| = 2.75
    assert by_geom["S1_T1"]["stop_price"] == 98.75
    assert by_geom["S1_T1"]["target_price"] == 103.5  # 101.5 + 1*2
    assert abs(by_geom["S1_T1"]["rr_ratio"] - 2.0 / 2.75) < 1e-9
    assert by_geom["S1_T0.5"]["target_price"] == 102.5
    assert abs(by_geom["S1_T0.5"]["rr_ratio"] - 1.0 / 2.75) < 1e-9
    assert by_geom["S1_T2"]["target_price"] == 105.5
    assert abs(by_geom["S1_T2"]["rr_ratio"] - 4.0 / 2.75) < 1e-9

    # S2 stretto = ORH - 1 tick = 101 - 0.25 = 100.75; denom = |101.5 - 100.75| = 0.75
    assert by_geom["S2_T1"]["stop_price"] == 100.75
    assert by_geom["S2_T1"]["target_price"] == 103.5
    assert abs(by_geom["S2_T1"]["rr_ratio"] - 2.0 / 0.75) < 1e-9


def test_geometries_short_mirrors_long_rr():
    long_rows = {r["geom"]: r for r in geometries(_ev("long", entry_ref=101.5), CFG)}
    # entry_ref speculare rispetto al centro dell'OR (100): 101.5 -> 98.5
    short_rows = {r["geom"]: r for r in geometries(_ev("short", entry_ref=98.5), CFG)}

    assert len(short_rows) == 8
    # stop speculari: S1 = ORH + tick = 101.25; S2 = ORL + tick = 99.25
    assert short_rows["S1_T1"]["stop_price"] == 101.25
    assert short_rows["S2_T1"]["stop_price"] == 99.25
    # target speculari: 98.5 - k*2
    assert short_rows["S1_T0.5"]["target_price"] == 97.5
    assert short_rows["S1_T2"]["target_price"] == 94.5

    # rr identico geometria per geometria (stessa distanza assoluta target-e e stop-e).
    for geom in long_rows:
        assert abs(long_rows[geom]["rr_ratio"] - short_rows[geom]["rr_ratio"]) < 1e-9


def test_geometries_skips_when_stop_equals_entry():
    # ORL - tick == entry_ref: S1 non ha senso (denom 0), restano solo le 4 righe di S2.
    ev = _ev("long", entry_ref=98.75)  # = orl(99) - tick(0.25)
    rows = geometries(ev, CFG)
    assert len(rows) == 4
    assert all(r["geom"].startswith("S2_") for r in rows)
