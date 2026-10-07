"""Placebo: quanto "vince" il caso con la stessa struttura della strategia.

Ogni simulazione ricostruisce l'intero storico dei trade del cliente con ingressi casuali ma la
stessa forma: stesso numero di trade per giorno, stessi orari e stesse durate (o stessi giorni con
orari estratti dagli orari reali), stessi costi, e lati:
  - "casuali"  : 50/50, il caso puro;
  - "stessi"   : i lati reali -> quanto vale il solo sbilanciamento long/short senza la scelta del momento;
  - "long"     : solo long -> quanto rende "comprare e basta" nelle stesse ore (il beta).
NB: non esiste uno scenario "stessi giorni e stessi lati, orari casuali": se il lato dipende da ciò
che succede durante il giorno (es. il verso di una rottura), spostare l'ingresso PRIMA dell'orario
reale regala al placebo informazione futura e lo rende ottimista (misurato: +9 punti su un breakout).
Il risultato reale (riprezzato sugli stessi dati di mercato, così il confronto è alla pari) viene
collocato nella distribuzione: percentile e p = (1 + #placebo >= reale) / (1 + n).
Metodo calibrato nel laboratorio (lab/wild/REPORT.md): 1.266 regole senza senso, stessi criteri.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .market import Market, ns

SCENARIOS = {
    "caso_puro": ("giorni", "casuali"),
    "stessi_lati": ("giorni", "stessi"),
    "solo_long": ("giorni", "long"),
    "stessi_giorni": ("orari", "casuali"),
}
LABELS = {
    "caso_puro": "Giorni casuali, lati a caso (il caso puro)",
    "stessi_lati": "Giorni casuali, stessi lati (conta solo lo sbilanciamento long/short)",
    "solo_long": "Giorni casuali, solo long (comprare e basta: il beta)",
    "stessi_giorni": "Stessi giorni, orari e lati casuali (il caso nei giorni scelti dalla strategia)",
}


def _structure(market: Market, t: pd.DataFrame) -> dict:
    e = ns(t["entry_ts"])
    x = ns(t["exit_ts"])
    se = t["sidx0"].to_numpy().astype(np.int64)
    sx = t["sidx1"].to_numpy().astype(np.int64)
    return {"se": se, "sx": sx, "off_e": e - market.anchor_ns[se], "off_x": x - market.anchor_ns[sx],
            "side": t["side"].to_numpy().astype(np.int64)}


def simulate(market: Market, t: pd.DataFrame, mode: str, sides: str, n_sims: int, cost: float,
             seed: int = 0, chunk: int = 50) -> np.ndarray:
    """Media netta per trade (punti) in ciascuna delle n_sims simulazioni."""
    st = _structure(market, t)
    se, sx, off_e, off_x, side = st["se"], st["sx"], st["off_e"], st["off_x"], st["side"]
    n = len(se)
    hold = sx - se
    ns_ = market.n_sessions
    rng = np.random.default_rng(seed)
    days, day_code = np.unique(se, return_inverse=True)
    lo, hi = int(se.min()), int(sx.max())
    pool = np.flatnonzero(market.valid_sess)
    pool = pool[(pool >= lo) & (pool <= hi - int(hold.max()))]
    if len(pool) == 0:
        pool = np.arange(lo, max(lo + 1, hi - int(hold.max())))
    out = np.empty(n_sims)
    for a in range(0, n_sims, chunk):
        m = min(chunk, n_sims - a)
        if mode == "giorni":
            replace = len(pool) < len(days)
            tgt = np.stack([rng.choice(pool, size=len(days), replace=replace) for _ in range(m)])
            ne = tgt[:, day_code]
            nx = np.minimum(ne + hold[None, :], ns_ - 1)
            te = market.anchor_ns[ne] + off_e[None, :]
            tx = market.anchor_ns[nx] + off_x[None, :]
        elif mode == "orari":
            ne = np.broadcast_to(se, (m, n))
            nx = np.broadcast_to(sx, (m, n))
            draw = off_e[rng.integers(0, n, size=(m, n))]
            dur = (off_x - off_e)[None, :]
            same = (hold == 0)[None, :]
            tx_same = np.minimum(draw + dur, market.sess_end_off[se][None, :])
            te = market.anchor_ns[ne] + draw
            tx = np.where(same, market.anchor_ns[ne] + tx_same, market.anchor_ns[nx] + off_x[None, :])
        else:
            raise ValueError(mode)
        if sides == "casuali":
            sd = rng.choice(np.array([-1, 1]), size=(m, n))
        elif sides == "long":
            sd = np.ones((m, n), np.int64)
        else:
            sd = np.broadcast_to(side, (m, n))
        k0 = market.locate(te.ravel(), "entry").reshape(m, n)
        k1 = np.maximum(market.locate(tx.ravel(), "exit").reshape(m, n), k0)
        pnl = sd * (market.pt_px[k1] - market.pt_px[k0]) - cost
        out[a:a + m] = pnl.mean(1)
    return out


def run_placebo(market: Market, t: pd.DataFrame, cost: float, n_sims: int = 1000, seed: int = 0,
                scenarios: list[str] | None = None) -> dict:
    real = float(np.mean(t["market_pts"].to_numpy() - cost))
    res = {"real_net_mean": real, "n_sims": n_sims, "scenarios": {}}
    for i, name in enumerate(scenarios or list(SCENARIOS)):
        mode, sides = SCENARIOS[name]
        dist = simulate(market, t, mode, sides, n_sims, cost, seed=seed + 101 * i)
        pct = float(((dist < real).mean() + 0.5 * (dist == real).mean()) * 100)   # ranghi medi per i pari
        p = float((1 + (dist >= real).sum()) / (1 + len(dist)))
        res["scenarios"][name] = {"label": LABELS[name], "dist": dist, "percentile": pct, "p": p,
                                  "median": float(np.median(dist)), "q95": float(np.percentile(dist, 95)),
                                  "q05": float(np.percentile(dist, 5))}
    return res
