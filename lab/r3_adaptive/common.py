"""r3_adaptive — libreria di regole semplici e motore delle meta-procedure online. Vedi s00_piano.py."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from scipy.signal import lfilter

from lab import core
from lab.r2_autosearch import common as ac

FAM = "r3_adaptive"
COST = core.COST_RT_POINTS
HERE = Path(__file__).resolve().parent
CACHE = HERE / "cache"
TL = [600, 660, 720, 780, 840, 900]
HL = [30, 60, "close"]
SIGS = ["r15", "r60", "r_open", "gap", "r_on", "r_prev", "r_5d", "pos_today", "pos_night", "pos_20d", "long"]
SEARCH = (pd.Timestamp("2011-07-01"), pd.Timestamp("2015-12-31"))
CHECK = (pd.Timestamp("2016-01-01"), pd.Timestamp("2018-12-31"))


def panel_from(bars=None, daily=None):
    """F, G, sessioni, in_phase. Senza argomenti: pannello discovery in cache di r2_autosearch."""
    if bars is None:
        z = np.load(ac.CACHE / "panel_discovery.npz")
        return dict(sessions=pd.DatetimeIndex(z["sessions"]), F=z["F"], G=z["G"], in_phase=z["in_phase"])
    P = ac.build(bars, daily)
    P["in_phase"] = daily.loc[P["sessions"], "in_phase"].to_numpy()
    return P


def library(P):
    """SIDE (n_s, N) in {-1,0,+1}, G_rule (n_s, N) rendimento long lordo del (T,h), meta DataFrame."""
    F, G = P["F"], P["G"]
    sides, gs, meta = [], [], []
    for T in TL:
        k = ac.TIMES.index(T)
        for h in HL:
            m = ac.HORIZONS.index(h)
            g = G[:, k, m]
            if not np.isfinite(g).any():
                continue
            for sname in SIGS:
                if sname == "long":
                    s = np.ones(len(g))
                else:
                    x = F[:, k, ac.FEATS.index(sname)]
                    if sname.startswith("pos"):
                        x = x - 0.5
                    s = np.sign(np.nan_to_num(x, nan=0.0))
                for dname, d in (("follow", 1), ("fade", -1)):
                    sd = d * s
                    sd = np.where(np.isfinite(g), sd, 0.0)
                    sides.append(sd); gs.append(np.nan_to_num(g))
                    meta.append(dict(rule=f"{sname}_{dname}_T{T}_h{h}", sig=sname, dir=dname, T=T, h=str(h), k=k, m=m))
    return np.array(sides).T, np.array(gs).T, pd.DataFrame(meta)


def gross_net(SIDE, GR, sign_day=None):
    """lordo e netto per regola e giorno (0 se nessun trade). sign_day: placebo 'segno per giorno'."""
    g = GR if sign_day is None else GR * sign_day[:, None]
    gross = SIDE * g
    traded = SIDE != 0
    return gross, gross - COST * traded, traded


# ------------------------------------------------------------------ periodi e punteggi causali

def period_ids(sessions: pd.DatetimeIndex, freq: str) -> np.ndarray:
    if freq == "month":
        key = sessions.year * 100 + sessions.month
    else:
        iso = sessions.isocalendar()
        key = (iso["year"] * 100 + iso["week"]).to_numpy()
    key = np.asarray(key)
    return np.concatenate([[0], np.cumsum(key[1:] != key[:-1])])


def topk_positions(NET, traded, pid, L, k, score, filt, atr=None):
    """maschera (n_s, N) delle regole operate ogni giorno. La scelta del periodo usa solo le 21*L
    sessioni PRECEDENTI al primo giorno del periodo."""
    n_s, N = NET.shape
    w = 21 * L
    starts = np.r_[0, np.flatnonzero(np.diff(pid)) + 1]
    cs = np.vstack([np.zeros((1, N)), np.cumsum(NET, 0)])
    cs2 = np.vstack([np.zeros((1, N)), np.cumsum(NET ** 2, 0)])
    ok = starts >= w
    st = starts[ok]
    mean = (cs[st] - cs[st - w]) / w
    if score == "t":
        var = (cs2[st] - cs2[st - w]) / w - mean ** 2
        sc = mean / np.sqrt(np.maximum(var, 1e-12)) * np.sqrt(w)
    else:
        sc = mean
    sel = np.zeros((len(st), N), bool)
    top = np.argpartition(-sc, k - 1, axis=1)[:, :k] if k < N else np.tile(np.arange(N), (len(st), 1))
    np.put_along_axis(sel, top, True, axis=1)
    if filt:
        sel &= mean > 0
    per_sel = np.zeros((len(starts), N), bool)
    per_sel[np.flatnonzero(ok)] = sel
    return per_sel[pid]


def portfolio(NET, traded, pos):
    """P&L netto giornaliero (1 contratto diviso fra le regole attive che tradano). NaN = nessun trade."""
    a = pos & traded
    n = a.sum(1)
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(n > 0, (NET * a).sum(1) / n, np.nan)


def hedge_weights(NET, traded, atr, eta, halflife):
    """pesi causali: w_d ~ exp(eta * somma (scontata) dei netti/ATR20 fino a d-1)."""
    U = np.nan_to_num(NET / atr[:, None])
    if halflife:
        lam = 0.5 ** (1 / halflife)
        S = lfilter([1.0], [1.0, -lam], U, axis=0)
    else:
        S = np.cumsum(U, 0)
    S = np.vstack([np.zeros((1, S.shape[1])), S[:-1]])          # solo il passato
    X = eta * S
    X -= X.max(1, keepdims=True)
    W = np.exp(X)
    return W / W.sum(1, keepdims=True)


def hedge_pnl(NET, traded, W):
    Wt = W * traded
    s = Wt.sum(1)
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(s > 0, (Wt * NET).sum(1) / s, np.nan)


def regime_stats(G, F):
    """statistiche causali (sessioni PRECEDENTI) sui rendimenti di 30 minuti 10:00->16:00."""
    seg = np.column_stack([G[:, ac.TIMES.index(T), ac.HORIZONS.index(30)] for T in range(600, 901, 30)]
                          + [G[:, ac.TIMES.index(930), ac.HORIZONS.index("close")]])
    seg = np.nan_to_num(seg)
    n_s = len(seg)
    x0, x1 = seg[:, :-1], seg[:, 1:]
    daysum = seg.sum(1)
    abssum = np.abs(seg).sum(1)

    def prev_roll(a, w=20):
        return pd.DataFrame(a).shift(1).rolling(w, min_periods=w).sum().to_numpy()
    sxy = prev_roll((x0 * x1).sum(1)); sxx = prev_roll((x0 ** 2).sum(1))
    ac1 = (sxy / sxx).ravel()
    vr = (prev_roll(daysum ** 2) / prev_roll((seg ** 2).sum(1))).ravel()   # VR(12 x 30m) = var(somma)/somma var
    with np.errstate(invalid="ignore", divide="ignore"):
        er_d = np.abs(daysum) / abssum
    er = (prev_roll(np.nan_to_num(er_d)) / 20).ravel()
    return dict(ac1=ac1, vr=vr, er=er)


def causal_median(x, w=250, minp=120):
    return pd.Series(x).shift(1).rolling(w, min_periods=minp).median().to_numpy()


def atr20_from_daily(daily, sessions):
    """ATR20 causale in punti come in r2_autosearch.build: range RTH medio delle 20 sessioni valide precedenti."""
    d = daily[daily["valid"]]
    a = (d["rth_high"] - d["rth_low"]).shift(1).rolling(20, min_periods=10).mean()
    return a.reindex(sessions).to_numpy()


def discovery_panel():
    """pannello discovery + ATR20 (in cache)."""
    CACHE.mkdir(exist_ok=True)
    P = panel_from()
    fp = CACHE / "atr20_discovery.npy"
    if fp.exists():
        P["atr"] = np.load(fp)
    else:
        _, daily = core.load("discovery")
        P["atr"] = atr20_from_daily(daily, P["sessions"])
        np.save(fp, P["atr"])
    return P
