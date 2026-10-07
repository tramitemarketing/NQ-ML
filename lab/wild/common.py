"""Infrastruttura comune della famiglia «wild».

UNITA' DICHIARATA PRIMA DI GUARDARE: punti NQ per 1 contratto, al netto di core.COST_RT_POINTS
(0,75 punti a/r), come il controller. Nessuna normalizzazione in ATR (lo stesso metro dei criteri
di validazione del PROTOCOLLO). I trade sono tutti dentro la RTH (09:30-16:00 NY): nessun roll.

Griglia dei prezzi RTH: P[s, k], k = 0..390, e' il prezzo all'istante 09:30 + k minuti:
    P[s, 0]  = open della barra 09:30
    P[s, k]  = close della barra che inizia a 09:30 + (k-1) minuti  (k >= 1)
Un ingresso «a k» usa solo barre chiuse entro l'istante k (nessun look-ahead) ed esegue a P[s,k].
Minuti senza barre (nessun scambio) sono riempiti in avanti.
"""
from __future__ import annotations

import datetime as dt
from functools import lru_cache

import numpy as np
import pandas as pd

from lab import core

FAMILY = "wild"
NMIN = 390
YEARS_NEEDED = 6          # analogo discovery di «3 anni su 5»: 60 % di 9 anni (2010-2018) -> 6/9
K_BONF = 24               # 8 famiglie x 3 candidati: soglia Bonferroni piena 0,05/24


@lru_cache(maxsize=1)
def grid():
    """Ritorna dict con matrici RTH per le sessioni valide in fase discovery."""
    bars, daily = core.load("discovery")
    d = daily[daily["valid"] & daily["in_phase"]].copy()
    r = bars[bars["rth"] & bars["session"].isin(d.index)]
    sess = d.index
    si = sess.get_indexer(pd.DatetimeIndex(r["session"]))
    k = r["ny_min"].to_numpy().astype(int) - 570            # 0..389 (barra che inizia a 09:30+k)
    S = len(sess)
    O = np.full((S, NMIN), np.nan); H = O.copy(); L = O.copy(); C = O.copy()
    V = np.zeros((S, NMIN))
    O[si, k] = r["open"].to_numpy(); H[si, k] = r["high"].to_numpy()
    L[si, k] = r["low"].to_numpy(); C[si, k] = r["close"].to_numpy()
    V[si, k] = r["volume"].to_numpy()
    present = ~np.isnan(C)
    Cf = pd.DataFrame(C).ffill(axis=1).to_numpy()
    first_open = pd.DataFrame(O).bfill(axis=1).to_numpy()[:, 0]
    Cf = np.where(np.isnan(Cf), first_open[:, None], Cf)
    P = np.empty((S, NMIN + 1))
    P[:, 0] = first_open
    P[:, 1:] = Cf
    Hf = np.where(np.isnan(H), Cf, H); Lf = np.where(np.isnan(L), Cf, L)
    return dict(sess=sess, daily=d, P=P, H=Hf, L=Lf, V=V, present=present,
                year=sess.year.to_numpy(), colmean=P.mean(0))


def drift(k_in, k_out):
    """Deriva media (punti) della stessa finestra oraria su tutte le sessioni discovery valide."""
    g = grid()
    cm = g["colmean"]
    return cm[np.asarray(k_out)] - cm[np.asarray(k_in)]


def trades_from(s_idx, k_in, k_out, side):
    g = grid()
    s_idx = np.asarray(s_idx, int); k_in = np.asarray(k_in, int); k_out = np.asarray(k_out, int)
    side = np.asarray(side, float)
    ok = (k_out > k_in) & (k_in >= 0) & (k_out <= NMIN) & (side != 0)
    s_idx, k_in, k_out, side = s_idx[ok], k_in[ok], k_out[ok], side[ok]
    P = g["P"]
    gross = side * (P[s_idx, k_out] - P[s_idx, k_in])
    return pd.DataFrame(dict(s=s_idx, k_in=k_in, k_out=k_out, side=side, gross=gross,
                             session=g["sess"][s_idx], year=g["year"][s_idx]))


def evaluate(t: pd.DataFrame, n_boot: int = 10000, gross_test: bool = False) -> dict:
    """Statistiche complete con i 4 criteri del PROTOCOLLO applicati al discovery."""
    if len(t) == 0:
        return dict(n=0, mean=np.nan, p_pos=1.0, pass_all=False)
    net = t["gross"].to_numpy() - (0.0 if gross_test else core.COST_RT_POINTS)
    st = core.day_block_bootstrap(net, t["session"].to_numpy(), n_boot=n_boot)
    beta = t["side"].to_numpy() * drift(t["k_in"].to_numpy(), t["k_out"].to_numpy())
    beta_adj = float(np.mean(net - beta))
    yr = core.yearly(net, t["session"])
    ypos = int((yr["mean"] > 0).sum()); ytot = int(len(yr))
    dt20 = core.drop_top(net, 20)
    st.update(dict(
        gross=float(t["gross"].mean()), mean_beta=float(beta.mean()), beta_adj=beta_adj,
        exposure=float(t["side"].mean()), years_pos=f"{ypos}/{ytot}", ypos=ypos,
        drop20=dt20,
        c1=bool(st["p_pos"] < 0.05), c1_bonf=bool(st["p_pos"] < 0.05 / K_BONF),
        c2=bool(beta_adj > 0), c3=bool(ypos >= YEARS_NEEDED), c4=bool(dt20 > 0),
    ))
    st["pass_all"] = bool(st["c1"] and st["c2"] and st["c3"] and st["c4"])
    st["pass_all_bonf"] = bool(st["c1_bonf"] and st["c2"] and st["c3"] and st["c4"])
    return st


def rec(test_id, desc, st, **extra):
    core.record(FAMILY, test_id, desc, "discovery", st, **extra)


def fmt(tid, st):
    return (f"{tid:48s} n={st['n']:5d} net={st['mean']:+7.3f} [{st['lo']:+.2f};{st['hi']:+.2f}] "
            f"p={st['p_pos']:.4f} beta={st['mean_beta']:+.3f} badj={st['beta_adj']:+.3f} "
            f"yrs={st['years_pos']} d20={st['drop20']:+.3f} ALL={int(st['pass_all'])}")


def ts_utc(sessions, k):
    """Istante UTC di 09:30 NY + k minuti nella data di sessione."""
    s = pd.DatetimeIndex(sessions).tz_localize(None).normalize()
    loc = (s + pd.Timedelta(hours=9, minutes=30) + pd.to_timedelta(np.asarray(k), unit="m"))
    return loc.tz_localize(core.NY).tz_convert("UTC")
