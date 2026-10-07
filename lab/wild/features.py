"""Caratteristiche giornaliere per le idee selvagge. Tutte calcolate SOLO con barre chiuse entro
l'istante d'ingresso dichiarato; le soglie sono quantili MOBILI dei giorni PRECEDENTI (250 sessioni,
minimo 100), mai del campione intero.

Le funzioni lavorano su una griglia qualsiasi prodotta da `make_grid(bars, daily)`, cosi' i candidati
congelati possono girare su qualunque fase.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

NMIN = 390


def make_grid(bars: pd.DataFrame, daily: pd.DataFrame, only_in_phase: bool = False) -> dict:
    d = daily[daily["valid"]].copy()
    if only_in_phase:
        d = d[d["in_phase"]]
    r = bars[bars["rth"] & bars["session"].isin(d.index)]
    sess = d.index
    si = sess.get_indexer(pd.DatetimeIndex(r["session"]))
    k = r["ny_min"].to_numpy().astype(int) - 570
    S = len(sess)
    O = np.full((S, NMIN), np.nan); C = O.copy()
    V = np.zeros((S, NMIN))
    O[si, k] = r["open"].to_numpy(); C[si, k] = r["close"].to_numpy(); V[si, k] = r["volume"].to_numpy()
    Cf = pd.DataFrame(C).ffill(axis=1).to_numpy()
    first_open = pd.DataFrame(O).bfill(axis=1).to_numpy()[:, 0]
    Cf = np.where(np.isnan(Cf), first_open[:, None], Cf)
    P = np.empty((S, NMIN + 1)); P[:, 0] = first_open; P[:, 1:] = Cf
    Obar = np.where(np.isnan(O), Cf, O)
    return dict(sess=sess, daily=d, P=P, V=V, O=Obar, present=~np.isnan(C),
                in_phase=d["in_phase"].to_numpy(), year=sess.year.to_numpy())


def roll_q(x: np.ndarray, q: float, win: int = 250, minp: int = 100) -> np.ndarray:
    """Quantile mobile dei giorni PRECEDENTI (shift 1)."""
    return pd.Series(x).rolling(win, min_periods=minp).quantile(q).shift(1).to_numpy()


def efficiency_ratio(P, k0, k1):
    path = np.abs(np.diff(P[:, k0:k1 + 1], axis=1)).sum(1)
    return np.abs(P[:, k1] - P[:, k0]) / np.where(path > 0, path, np.nan)


def speed_asym(P, k0, k1):
    """log( |mossa media dei minuti in salita| / |mossa media dei minuti in discesa| )."""
    r = np.diff(P[:, k0:k1 + 1], axis=1)
    up = np.where(r > 0, r, np.nan); dn = np.where(r < 0, -r, np.nan)
    return np.log(np.nanmean(up, 1) / np.nanmean(dn, 1))


def perm_entropy(P, k0, k1, order=3):
    r = np.diff(P[:, k0:k1 + 1], axis=1)
    S, T = r.shape
    out = np.full(S, np.nan)
    import itertools
    perms = {p: i for i, p in enumerate(itertools.permutations(range(order)))}
    for s in range(S):
        x = r[s] + np.random.default_rng(s).normal(0, 1e-9, T)   # rompe i pareggi (tick discreti)
        w = np.lib.stride_tricks.sliding_window_view(x, order)
        codes = np.array([perms[tuple(np.argsort(v))] for v in w])
        c = np.bincount(codes, minlength=len(perms)) / len(codes)
        c = c[c > 0]
        out[s] = -(c * np.log(c)).sum() / np.log(len(perms))
    return out


def records(P, k0, k1, skip=5):
    """Numero di nuovi massimi e nuovi minimi correnti (dopo i primi `skip` minuti) in [k0,k1]."""
    seg = P[:, k0:k1 + 1]
    runmax = np.maximum.accumulate(seg, 1); runmin = np.minimum.accumulate(seg, 1)
    nh = (seg[:, skip + 1:] > runmax[:, skip:-1]).sum(1)
    nl = (seg[:, skip + 1:] < runmin[:, skip:-1]).sum(1)
    # minuto dell'ultimo record
    newrec = (seg[:, skip + 1:] > runmax[:, skip:-1]) | (seg[:, skip + 1:] < runmin[:, skip:-1])
    last = np.where(newrec.any(1), newrec.shape[1] - 1 - np.argmax(newrec[:, ::-1], 1), -1)
    return nh, nl, last


def vol_profile_norm(V, win=20):
    """Volume per minuto diviso per la mediana dello stesso minuto nelle `win` sessioni PRECEDENTI."""
    med = pd.DataFrame(V).rolling(win, min_periods=10).median().shift(1).to_numpy()
    return V / np.where(med > 0, med, np.nan)
