"""r2_autosearch — feature causali, ranghi causali, rendimenti futuri. Vedi s00_piano.py."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from lab import core

FAM = "r2_autosearch"
COST = core.COST_RT_POINTS
HERE = Path(__file__).resolve().parent
CACHE = HERE / "cache"
TIMES = [585] + list(range(600, 931, 30))          # 09:45, 10:00 ... 15:30 (13)
HORIZONS = [15, 30, 60, 120, "close"]
FEATS = ["r5", "r15", "r60", "r_open", "gap", "r_on", "r_prev", "r_5d", "rv_sur", "rv60_sur",
         "vol_rel", "vol60_rel", "pos_today", "pos_yday", "pos_night", "pos_20d", "dist_hi",
         "dist_lo", "range_rel", "on_range_rel", "vol_regime", "since_hi", "since_lo"]
QCONDS = [("le", 0.10), ("le", 0.25), ("le", 0.50), ("gt", 0.50), ("ge", 0.75), ("ge", 0.90)]
RANK_WIN, RANK_MIN = 250, 60


def cond_names():
    sym = {"le": "<=", "gt": ">", "ge": ">="}
    out = [f"{f}{sym[op]}{q:.2f}" for f in FEATS for op, q in QCONDS]
    out += [f"dow=={d}" for d in range(5)]
    return out


def cond_feat():
    """indice della 'feature' di ogni condizione (dow = gruppo a parte)."""
    return np.array([i for i in range(len(FEATS)) for _ in QCONDS] + [len(FEATS)] * 5)


def _prev_mean(a: np.ndarray, w: int, minp: int) -> np.ndarray:
    """media delle w righe PRECEDENTI (asse 0), NaN-aware."""
    s = pd.DataFrame(a.reshape(len(a), -1))
    m = s.shift(1).rolling(w, min_periods=minp).mean().to_numpy()
    return m.reshape(a.shape)


def build(bars: pd.DataFrame, daily: pd.DataFrame):
    """dict con: sessions (sessioni valide), F (n_s, n_T, n_feat) feature grezze causali,
    G (n_s, n_T, n_H) rendimenti lordi LONG in punti dall'open della barra T (NaN se l'orizzonte non esiste),
    dow (n_s,)."""
    d = daily[daily["valid"]].copy()
    sess = d.index
    rth = bars[bars["rth"] & bars["session"].isin(sess.values)]
    col = (rth["ny_min"].to_numpy() - 570).astype(int)
    row = sess.get_indexer(pd.DatetimeIndex(rth["session"].to_numpy()))
    ns = len(sess)
    mats = {}
    for c in ("adj_open", "adj_high", "adj_low", "adj_close", "volume"):
        m = np.full((ns, 390), np.nan)
        m[row, col] = rth[c].to_numpy(dtype=float)
        mats[c] = m
    # barre mancanti: close portato avanti, open = close precedente, high/low = close
    C = pd.DataFrame(mats["adj_close"]).ffill(axis=1).to_numpy()
    O = mats["adj_open"].copy()
    prevC = np.concatenate([np.full((ns, 1), np.nan), C[:, :-1]], axis=1)
    O = np.where(np.isnan(O), prevC, O)
    O[:, 0] = np.where(np.isnan(O[:, 0]), d["rth_open"].to_numpy(), O[:, 0])
    O = pd.DataFrame(O).ffill(axis=1).to_numpy()
    C = np.where(np.isnan(C), O, C)
    H = np.where(np.isnan(mats["adj_high"]), C, mats["adj_high"])
    L = np.where(np.isnan(mats["adj_low"]), C, mats["adj_low"])
    V = np.nan_to_num(mats["volume"])

    # notte della sessione (fuori RTH, prima delle 09:30), prezzi adj
    nb = bars[(~bars["rth"]) & ((bars["ny_min"] < 570) | (bars["ny_min"] >= 1080)) & bars["session"].isin(sess.values)]
    g = nb.groupby("session")
    n_hi = g["adj_high"].max().reindex(sess).to_numpy()
    n_lo = g["adj_low"].min().reindex(sess).to_numpy()

    rng = (d["rth_high"] - d["rth_low"]).to_numpy()
    atr20 = pd.Series(rng).shift(1).rolling(20, min_periods=10).mean().to_numpy()
    atr250 = pd.Series(rng).shift(1).rolling(250, min_periods=60).mean().to_numpy()
    y_hi = d["rth_high"].shift(1).to_numpy(); y_lo = d["rth_low"].shift(1).to_numpy()
    y_cl = d["rth_close"].shift(1).to_numpy(); y_op = d["rth_open"].shift(1).to_numpy()
    cl5 = d["rth_close"].shift(6).to_numpy()
    hi20 = d["rth_high"].shift(1).rolling(20, min_periods=10).max().to_numpy()
    lo20 = d["rth_low"].shift(1).rolling(20, min_periods=10).min().to_numpy()
    nrange = n_hi - n_lo
    nrange_m = pd.Series(nrange).shift(1).rolling(20, min_periods=10).mean().to_numpy()
    glbx = d["glbx_open"].to_numpy()
    op0 = O[:, 0]

    dC = C - np.concatenate([O[:, :1], C[:, :-1]], axis=1)       # variazione close-su-close (prima: dall'open)
    cum_sq = np.cumsum(dC ** 2, axis=1)
    cum_v = np.cumsum(V, axis=1)
    runH = np.maximum.accumulate(H, axis=1)
    runL = np.minimum.accumulate(L, axis=1)
    idx = np.broadcast_to(np.arange(390)[None, :], (ns, 390))
    lastH = np.maximum.accumulate(np.where(H >= runH, idx, -1), axis=1)   # minuto dell'ultimo nuovo massimo
    lastL = np.maximum.accumulate(np.where(L <= runL, idx, -1), axis=1)

    nT, nF = len(TIMES), len(FEATS)
    F = np.full((ns, nT, nF), np.nan)
    rawrv = np.full((ns, nT), np.nan); rawrv60 = rawrv.copy(); rawv = rawrv.copy(); rawv60 = rawrv.copy()
    for k, T in enumerate(TIMES):
        j = T - 570                        # barre 0..j-1 note; ingresso all'open della barra j
        p = C[:, j - 1]

        def back(m):
            return O[:, max(0, j - m)]
        rawrv[:, k] = np.sqrt(cum_sq[:, j - 1])
        rawrv60[:, k] = np.sqrt(cum_sq[:, j - 1] - (cum_sq[:, j - 61] if j > 60 else 0))
        rawv[:, k] = cum_v[:, j - 1]
        rawv60[:, k] = cum_v[:, j - 1] - (cum_v[:, j - 61] if j > 60 else 0)
        hi, lo = runH[:, j - 1], runL[:, j - 1]
        with np.errstate(invalid="ignore", divide="ignore"):
            cols = dict(
                r5=(p - back(5)) / atr20, r15=(p - back(15)) / atr20, r60=(p - back(60)) / atr20,
                r_open=(p - op0) / atr20, gap=(op0 - y_cl) / atr20, r_on=(op0 - glbx) / atr20,
                r_prev=(y_cl - y_op) / atr20, r_5d=(y_cl - cl5) / atr20,
                pos_today=(p - lo) / np.where(hi - lo > 0, hi - lo, np.nan),
                pos_yday=(p - y_lo) / np.where(y_hi - y_lo > 0, y_hi - y_lo, np.nan),
                pos_night=(p - n_lo) / np.where(nrange > 0, nrange, np.nan),
                pos_20d=(p - lo20) / np.where(hi20 - lo20 > 0, hi20 - lo20, np.nan),
                dist_hi=(hi - p) / atr20, dist_lo=(p - lo) / atr20, range_rel=(hi - lo) / atr20,
                on_range_rel=nrange / nrange_m, vol_regime=atr20 / atr250,
                since_hi=(j - 1 - lastH[:, j - 1]).astype(float), since_lo=(j - 1 - lastL[:, j - 1]).astype(float),
            )
        for f, v in cols.items():
            F[:, k, FEATS.index(f)] = v
    with np.errstate(invalid="ignore", divide="ignore"):
        F[:, :, FEATS.index("rv_sur")] = rawrv / _prev_mean(rawrv, 20, 10)
        F[:, :, FEATS.index("rv60_sur")] = rawrv60 / _prev_mean(rawrv60, 20, 10)
        F[:, :, FEATS.index("vol_rel")] = rawv / _prev_mean(rawv, 20, 10)
        F[:, :, FEATS.index("vol60_rel")] = rawv60 / _prev_mean(rawv60, 20, 10)

    G = np.full((ns, nT, len(HORIZONS)), np.nan)
    for k, T in enumerate(TIMES):
        j = T - 570
        for m, h in enumerate(HORIZONS):
            if h == "close":
                G[:, k, m] = C[:, 389] - O[:, j]
            elif j + h < 390:                     # esce prima della chiusura (altrimenti coincide con "close")
                G[:, k, m] = C[:, j + h - 1] - O[:, j]
    return dict(sessions=sess, F=F, G=G, dow=d["dow"].to_numpy())


def causal_ranks(F: np.ndarray) -> np.ndarray:
    """rango percentile di F[i] fra le stesse (T, feature) delle RANK_WIN sessioni PRECEDENTI."""
    ns = F.shape[0]
    R = np.full(F.shape, np.nan)
    for i in range(RANK_MIN, ns):
        w = F[max(0, i - RANK_WIN):i]
        ok = np.isfinite(w)
        cnt = ok.sum(0)
        less = ((w < F[i][None]) & ok).sum(0) + 0.5 * ((w == F[i][None]) & ok).sum(0)
        with np.errstate(invalid="ignore", divide="ignore"):
            r = less / np.where(cnt >= RANK_MIN, cnt, np.nan)
        R[i] = np.where(np.isfinite(F[i]), r, np.nan)
    return R


def cond_masks(R: np.ndarray, dow: np.ndarray) -> np.ndarray:
    """(n_s, n_T, n_cond) booleano."""
    ns, nT, nF = R.shape
    out = np.zeros((ns, nT, nF * len(QCONDS) + 5), bool)
    c = 0
    for f in range(nF):
        r = R[:, :, f]
        for op, q in QCONDS:
            with np.errstate(invalid="ignore"):
                out[:, :, c] = (r <= q) if op == "le" else ((r > q) if op == "gt" else (r >= q))
            c += 1
    for dd in range(5):
        out[:, :, c] = (dow == dd)[:, None]
        c += 1
    return out


def panel(phase="discovery", warmup_days=0, cache=True):
    CACHE.mkdir(exist_ok=True)
    fp = CACHE / f"panel_{phase}.npz"
    if cache and fp.exists() and phase == "discovery":
        z = np.load(fp)
        return dict(sessions=pd.DatetimeIndex(z["sessions"]), R=z["R"], G=z["G"], dow=z["dow"], F=z["F"],
                    in_phase=z["in_phase"])
    bars, daily = core.load(phase, warmup_days=warmup_days)
    P = build(bars, daily)
    P["R"] = causal_ranks(P["F"])
    P["in_phase"] = daily.loc[P["sessions"], "in_phase"].to_numpy()
    if cache and phase == "discovery":
        np.savez_compressed(fp, sessions=P["sessions"].values, R=P["R"], G=P["G"], dow=P["dow"], F=P["F"],
                            in_phase=P["in_phase"])
    return P


def rule_mask(P: dict, T: int, conds) -> np.ndarray:
    """maschera per sessione di una regola (istante T, condizioni per nome)."""
    k = TIMES.index(T)
    M = cond_masks(P["R"][:, k:k + 1], P["dow"])[:, 0]
    names = cond_names()
    m = np.ones(len(M), bool)
    for c in conds:
        m &= M[:, names.index(c)]
    return m
