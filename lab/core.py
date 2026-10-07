"""Laboratorio di ricerca aperta (fase "capolavoro di idee", 2026-09-23).

Unica porta ai dati per tutti gli esperimenti in lab/. Tre regole che il codice fa rispettare:

1. BLOCCHI TEMPORALI. I dati si caricano solo per fase:
     discovery     2010-06-07 -> 2018-12-31   (libero: esplorare, sbagliare, provare di tutto)
     validation    2019-01-01 -> 2023-09-30   (solo il controller, solo su candidati congelati)
     confirmation  2023-10-01 -> 2026-03-19   (solo il controller, UNA volta, sui sopravvissuti)
   La cassaforte (2026-03-20 -> 2026-09-30, chiusa dall'utente il 2026-10-07) non e' caricabile da
   nessuna fase: e' dell'utente. I dati dal 2026-10-01 sono "prova in avanti": ognuna parte dalla data
   della propria pre-registrazione (PROTOCOLLO §23); nessuna fase li carica finche' non esiste quella regola.
   validation/confirmation richiedono la variabile d'ambiente LAB_CONTROLLER=1.

2. ROLL. NQ.v.0 e' una serie continua NON aggiustata: al cambio di contratto il prezzo salta
   (base del future). Le date esatte vengono dalla simbologia Databento: il cambio avviene alle
   00:00 UTC (sera NY, DENTRO la notte della sessione di roll). `adj_*` sono i prezzi aggiustati
   all'indietro (additivi): USARE SEMPRE adj_* per qualunque rendimento che attraversa la notte o
   piu' giorni. `roll_bar` marca la prima barra del nuovo contratto; `daily.roll_session` la sessione.
   Rendimenti RTH (09:30-16:00) non toccano mai un roll.

3. REGISTRO. Ogni test guardato va registrato con `record()` (anche i falliti, anche gli esplorativi):
   il numero di tentativi e' parte del risultato.

Convenzione costi (identica al resto del progetto): 2,50 $/lato + 1 tick/lato = 0,75 punti = 15 $
a contratto andata e ritorno. NQ: 20 $/punto, tick 0,25.
"""
from __future__ import annotations

import datetime as dt
import glob
import json
import os
import time
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "ohlcv_1m"
CACHE = ROOT / "data" / "lab"
LEDGER_DIR = ROOT / "lab" / "ledger"
NY = ZoneInfo("America/New_York")

PHASES = {
    "discovery": (dt.date(2010, 6, 7), dt.date(2018, 12, 31)),
    "validation": (dt.date(2019, 1, 1), dt.date(2023, 9, 30)),
    "confirmation": (dt.date(2023, 10, 1), dt.date(2026, 3, 19)),
}
VAULT_START = dt.date(2026, 3, 20)
VAULT_END = dt.date(2026, 9, 30)      # chiusa il 2026-10-07 per decisione dell'utente (PROTOCOLLO §23)
FORWARD_START = dt.date(2026, 10, 1)  # solo prove in avanti pre-registrate

POINT_USD = 20.0
TICK = 0.25
COST_RT_POINTS = 0.75          # 2 x (2.50$/20 + 1 tick)
COST_RT_USD = COST_RT_POINTS * POINT_USD


# --------------------------------------------------------------------------- dati

def _third_friday(y: int, m: int) -> dt.date:
    d = dt.date(y, m, 15)
    while d.weekday() != 4:
        d += dt.timedelta(days=1)
    return d


def _build_cache() -> tuple[pd.DataFrame, pd.DataFrame]:
    files = sorted(glob.glob(str(RAW / "*.parquet")))
    df = pd.concat(pd.read_parquet(f, columns=["open", "high", "low", "close", "volume"]) for f in files)
    df = df.sort_index(kind="stable")
    df = df[~df.index.duplicated(keep="first")]
    ny = df.index.tz_convert(NY)
    mins = (ny.hour * 60 + ny.minute).to_numpy()
    shift = (ny.hour >= 17).astype(int)
    sdate = (ny.tz_localize(None).normalize() + pd.to_timedelta(shift, unit="D"))
    df["session"] = sdate.to_numpy().astype("datetime64[D]")
    df["ny_min"] = mins.astype(np.int16)                 # minuto NY del giorno (0..1439)
    df["dow"] = sdate.dayofweek.to_numpy().astype(np.int8)  # giorno della sessione (0=lun)
    df["rth"] = (mins >= 570) & (mins < 960)
    # tolgo i "giorni" di sessione che cadono di sabato (resti) — la domenica sera e' gia' lunedi'
    df = df[df["dow"] < 5]

    # ---- roll: date esatte dalla simbologia Databento (gratuita, data/lab/nq_v0_mapping.json).
    # Il cambio di instrument_id avviene alle 00:00 UTC del giorno d0 (19:00/20:00 NY, dentro la notte
    # della sessione d0). Il salto e' misurato fra l'ultima barra prima e la prima barra dopo quell'istante.
    mapping = json.load(open(CACHE / "nq_v0_mapping.json"))
    idx = df.index
    roll_ts, roll_jump_v = [], []
    for seg in mapping[1:]:
        t = pd.Timestamp(seg["d0"], tz="UTC")
        i = idx.searchsorted(t)
        if i == 0 or i >= len(idx):
            continue
        roll_ts.append(idx[i])
        roll_jump_v.append(df["open"].iat[i] - df["close"].iat[i - 1])
    roll_ts = pd.DatetimeIndex(roll_ts)
    # aggiustamento all'indietro additivo: ogni barra PRIMA dell'istante di roll riceve + salto
    off = np.zeros(len(df))
    pos = idx.searchsorted(roll_ts)
    for p, j in zip(pos, roll_jump_v):
        off[:p] += j
    df["roll_bar"] = False
    df.iloc[pos, df.columns.get_loc("roll_bar")] = True    # prima barra del nuovo contratto
    for c in ("open", "high", "low", "close"):
        df["adj_" + c] = df[c].to_numpy() + off
    roll_sessions = pd.DatetimeIndex(df["session"].to_numpy()[pos])
    roll_jump = pd.Series(roll_jump_v, index=roll_sessions)

    # ---- tabella giornaliera
    g = df.groupby("session", sort=True)
    r = df[df["rth"]].groupby("session", sort=True)
    daily = pd.DataFrame({
        "n_bars": g.size(),
        "n_rth": r.size(),
        "glbx_open": g["adj_open"].first(),
        "rth_open": r["adj_open"].first(),
        "rth_high": r["adj_high"].max(),
        "rth_low": r["adj_low"].min(),
        "rth_close": r["adj_close"].last(),
        "rth_volume": r["volume"].sum(),
        "day_close": g["adj_close"].last(),       # ultima barra della sessione (~16:59)
    })
    daily["dow"] = daily.index.dayofweek
    daily["roll_session"] = daily.index.isin(roll_sessions)
    daily["roll_jump"] = roll_jump.reindex(daily.index).fillna(0.0)
    daily["valid"] = daily["n_rth"] >= 300      # stessa soglia del progetto (min_rth_bars)
    daily.index.name = "session"
    return df, daily


def _cached() -> tuple[pd.DataFrame, pd.DataFrame]:
    CACHE.mkdir(parents=True, exist_ok=True)
    fb, fd = CACHE / "bars.parquet", CACHE / "daily.parquet"
    newest_raw = max(os.path.getmtime(f) for f in glob.glob(str(RAW / "*.parquet")))
    if fb.exists() and fd.exists() and os.path.getmtime(fb) > newest_raw:
        return pd.read_parquet(fb), pd.read_parquet(fd)
    t0 = time.time()
    bars, daily = _build_cache()
    bars.to_parquet(fb)
    daily.to_parquet(fd)
    print(f"[lab] cache costruita in {time.time()-t0:.0f}s")
    return bars, daily


def load(phase: str, warmup_days: int = 0) -> tuple[pd.DataFrame, pd.DataFrame]:
    """(bars, daily) della fase. `warmup_days` sessioni PRECEDENTI all'inizio della fase possono
    essere incluse per calcolare indicatori (lookback); i test vanno misurati solo su
    `daily.in_phase` / `bars.in_phase`. Mai niente dalla cassaforte."""
    if phase not in PHASES:
        raise ValueError(phase)
    if phase != "discovery" and os.environ.get("LAB_CONTROLLER") != "1":
        raise PermissionError(f"la fase {phase!r} e' riservata al controller")
    lo, hi = PHASES[phase]
    assert hi < VAULT_START
    bars, daily = _cached()
    sess = daily.index
    in_phase = (sess >= pd.Timestamp(lo)) & (sess <= pd.Timestamp(hi))
    first_i = int(np.argmax(in_phase))
    start_i = max(0, first_i - warmup_days)
    keep = sess[start_i:][: (in_phase.sum() + (first_i - start_i))]
    daily = daily.loc[keep].copy()
    daily["in_phase"] = (daily.index >= pd.Timestamp(lo)) & (daily.index <= pd.Timestamp(hi))
    bars = bars[(bars["session"] >= keep[0].to_datetime64()) & (bars["session"] <= keep[-1].to_datetime64())].copy()
    bars["in_phase"] = bars["session"] >= np.datetime64(lo)
    assert pd.Timestamp(bars["session"].max()) < pd.Timestamp(VAULT_START)
    return bars, daily


# --------------------------------------------------------------------------- statistica

def day_block_bootstrap(values: np.ndarray, days: np.ndarray, n_boot: int = 10000, seed: int = 0,
                        alpha: float = 0.05) -> dict:
    """Media per evento con CI e p-value a blocchi per giorno (i trade dello stesso giorno restano insieme).
    p_two: bilaterale contro 0 (bootstrap centrato); p_pos: unilaterale per media > 0."""
    values = np.asarray(values, float)
    ok = np.isfinite(values)
    values, days = values[ok], np.asarray(days)[ok]
    if len(values) == 0:
        return {"n": 0, "n_days": 0, "mean": np.nan, "lo": np.nan, "hi": np.nan, "p_two": np.nan, "p_pos": np.nan}
    codes, uniq = pd.factorize(days)
    s = np.bincount(codes, weights=values)
    n = np.bincount(codes).astype(float)
    nd = len(s)
    point = s.sum() / n.sum()
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, nd, size=(n_boot, nd))
    dist = s[idx].sum(1) / n[idx].sum(1)
    centered = dist - point
    p_two = float((np.abs(centered) >= abs(point)).mean())
    p_pos = float((centered >= point).mean())
    return {"n": int(n.sum()), "n_days": int(nd), "mean": float(point),
            "lo": float(np.percentile(dist, 100 * alpha / 2)), "hi": float(np.percentile(dist, 100 * (1 - alpha / 2))),
            "p_two": max(p_two, 1 / n_boot), "p_pos": max(p_pos, 1 / n_boot)}


def yearly(values: np.ndarray, days) -> pd.DataFrame:
    """Media, n e somma per anno solare: la domanda 'quanti anni su quanti?'."""
    d = pd.DataFrame({"v": np.asarray(values, float), "y": pd.DatetimeIndex(days).year})
    return d.groupby("y")["v"].agg(["mean", "count", "sum"])


def drop_top(values: np.ndarray, k: int = 20) -> float:
    """Media dopo aver tolto i k trade migliori (test 'lotteria')."""
    v = np.sort(np.asarray(values, float)[np.isfinite(values)])
    return float(v[:-k].mean()) if len(v) > k else np.nan


# --------------------------------------------------------------------------- registro

def record(family: str, test_id: str, description: str, phase: str, stats: dict, **extra) -> None:
    """Una riga per ogni test guardato. Un file JSONL per famiglia (niente scritture concorrenti)."""
    LEDGER_DIR.mkdir(parents=True, exist_ok=True)
    row = {"ts": dt.datetime.now().isoformat(timespec="seconds"), "family": family, "test_id": test_id,
           "phase": phase, "description": description}
    row.update({k: (float(v) if isinstance(v, (np.floating, np.integer)) else v) for k, v in stats.items()})
    row.update(extra)
    with open(LEDGER_DIR / f"{family}.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")
