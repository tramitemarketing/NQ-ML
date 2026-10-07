"""Famiglia r2_analog (giro 2): il mercato come sistema dinamico e come linguaggio.

Convenzioni fissate PRIMA di guardare qualunque risultato (2026-09-23):

DATI GIORNALIERI (solo sessioni valide, RTH 09:30-15:59, prezzi grezzi per i log-rendimenti intraday:
in RTH non c'e' mai un roll; prezzi adj per notte e ieri):
  P5[k], k=0..78: prezzo ai confini dei 5 minuti. P5[0] = open della barra 09:30; P5[k] = close della
  barra 09:30+5k-1. r5[k] = log(P5[k+1]/P5[k]) (78 rendimenti 5m).
  sigma5_hat_t = sqrt(media, sulle 20 sessioni valide PRECEDENTI, di sum(r5^2)/78)  (nota alle 09:30).
  sigmaD_hat_t = sigma5_hat_t * sqrt(78).
  Contesto (unita' sigmaD_hat): notte = (adj open 09:30 - adj close RTH di ieri)/raw open 09:30;
  ieri = log(close/open RTH di ieri, grezzi).

RAPPRESENTAZIONE DELLA MATTINA (finestra W minuti da 09:30, W in {60, 90, 150}):
  path[k] = log(P5[k]/P5[0]) / sigma5_hat, k = 1..W/5  (cammino cumulativo in unita' di vol prevista).
  Rappresentazioni (dichiarate):
    "path"  = euclidea sul cammino cumulativo;
    "ctx"   = path + [notte, ieri] * sqrt(W/5) (il contesto pesa come la fine del cammino);
    "shape" = distanza di correlazione (cammino z-normalizzato: solo forma, non ampiezza);
    "incr"  = euclidea sugli incrementi 5m (non cumulati);
    "dtw"   = DTW sul cammino cumulativo con banda di Sakoe-Chiba 3.
  K in {10, 25, 50, 100}.
  Biblioteca: le 750 sessioni valide PRECEDENTI a t (minimo 250); mai t stessa o giorni successivi.

ESITO (pomeriggio): y = log(close 15:59 / open della barra alla fine della finestra) / (sigma5_hat*sqrt(n5)),
  n5 = numero di barre 5m del pomeriggio. Il segnale e' noto alla chiusura della barra (fine finestra - 1),
  l'ingresso e' all'OPEN della barra successiva: esattamente il punto d'inizio di y.
  Volatilita' del pomeriggio: lrv = log(sum r5^2 del pomeriggio / n5 / sigma5_hat^2).

PREVISIONE PER ANALOGHI: pred = media di y dei K vicini; disp = dev. std di y dei vicini;
  agree = |media dei segni di y dei vicini|; vpred = media di lrv dei vicini.
PLACEBO: K giorni scelti a caso fra gli stessi della biblioteca (200 ripetizioni).
METRICHE (diagnostiche, discovery): IC = correlazione di Pearson pred-y (q = z(pred)*z(y) per giorno,
  bootstrap a blocchi per giorno); "sign" = media di sign(pred)*y in unita' di vol.
TRADEABLE: netto in PUNTI per contratto (costi 0,75), come il controller. Beta: controller.beta_component.
"""
from __future__ import annotations

import pickle
from pathlib import Path

import numpy as np
import pandas as pd

from lab import core

FAM = "r2_analog"
COST = core.COST_RT_POINTS
M0, M1 = 570, 960
LIB_WIN, LIB_MIN = 750, 250
WINDOWS = (60, 90, 150)
REPS = ("path", "ctx", "shape", "incr", "dtw")
KS = (10, 25, 50, 100)

_CACHE = Path(__file__).resolve().parents[2] / "data" / "lab" / "r2_analog_disc.pkl"


# ------------------------------------------------------------------ matrici giornaliere

def build(bars: pd.DataFrame, daily: pd.DataFrame) -> dict:
    r = bars[bars["rth"]]
    piv = {}
    for col in ("open", "close", "adj_open", "adj_close"):
        p = r.pivot_table(index="session", columns="ny_min", values=col, aggfunc="first")
        piv[col] = p.reindex(columns=range(M0, M1))
    sess = piv["close"].index
    dv = daily.reindex(sess)
    close = piv["close"].ffill(axis=1)
    opn = piv["open"].fillna(close.shift(1, axis=1))
    aclose = piv["adj_close"].ffill(axis=1)
    aopen = piv["adj_open"].fillna(aclose.shift(1, axis=1))
    ok = (dv["valid"].fillna(False).to_numpy() & opn[M0].notna().to_numpy() & close[M1 - 1].notna().to_numpy())
    O, C = opn.to_numpy(float), close.to_numpy(float)
    AO, AC = aopen.to_numpy(float), aclose.to_numpy(float)
    P5 = np.column_stack([O[:, 0]] + [C[:, 5 * k - 1] for k in range(1, 79)])
    r5 = np.diff(np.log(P5), axis=1)
    rv = (r5 ** 2).sum(1)
    # sigma5_hat: sessioni valide precedenti
    s5 = np.full(len(sess), np.nan)
    rv_ok = np.where(ok, rv, np.nan)
    idx_ok = np.where(ok)[0]
    for j, i in enumerate(idx_ok):
        if j >= 20:
            s5[i] = np.sqrt(np.mean(rv_ok[idx_ok[j - 20:j]]) / 78)
    sD = s5 * np.sqrt(78)
    # contesto: notte e ieri (ultima sessione valida precedente)
    prev = np.full(len(sess), -1)
    last = -1
    for i in range(len(sess)):
        prev[i] = last
        if ok[i]:
            last = i
    has_prev = prev >= 0
    pc = np.where(has_prev, AC[np.maximum(prev, 0), -1], np.nan)
    night = (AO[:, 0] - pc) / O[:, 0] / sD
    yday = np.where(has_prev, np.log(C[np.maximum(prev, 0), -1] / O[np.maximum(prev, 0), 0]), np.nan) / sD
    ok = ok & np.isfinite(s5) & np.isfinite(night) & np.isfinite(yday)
    return {"sess": pd.DatetimeIndex(sess), "ok": ok, "in_phase": dv["in_phase"].fillna(False).to_numpy(),
            "O": O, "C": C, "AO": AO, "AC": AC, "P5": P5, "r5": r5, "s5": s5, "sD": sD,
            "night": night, "yday": yday, "year": pd.DatetimeIndex(sess).year.to_numpy()}


def setup_discovery():
    bars, daily = core.load("discovery")
    if _CACHE.exists():
        M = pickle.load(open(_CACHE, "rb"))
    else:
        M = build(bars, daily)
        pickle.dump(M, open(_CACHE, "wb"))
    return bars, daily, M


# ------------------------------------------------------------------ rappresentazioni ed esiti

def features(M: dict, W: int, rep: str) -> np.ndarray:
    k = W // 5
    lp = np.log(M["P5"][:, 1:k + 1] / M["P5"][:, [0]]) / M["s5"][:, None]
    if rep in ("path", "dtw"):
        return lp
    if rep == "ctx":
        w = np.sqrt(k)
        return np.column_stack([lp, w * M["night"], w * M["yday"]])
    if rep == "shape":
        z = lp - lp.mean(1, keepdims=True)
        return z / np.maximum(z.std(1, keepdims=True), 1e-9)
    if rep == "incr":
        return M["r5"][:, :k] / M["s5"][:, None]
    raise ValueError(rep)


def outcome(M: dict, W: int, H: int | None = None) -> dict:
    """Esito dall'open della barra 09:30+W alla close della barra (09:30+W+H-1) (H=None: fino alle 15:59)."""
    k0 = W // 5
    k1 = 78 if H is None else min(78, k0 + H // 5)
    n5 = k1 - k0
    y = np.log(M["P5"][:, k1] / M["P5"][:, k0]) / (M["s5"] * np.sqrt(n5))
    rr = M["r5"][:, k0:k1]
    lrv = np.log((rr ** 2).sum(1) / n5 / M["s5"] ** 2)
    a = W  # colonna della barra d'ingresso
    b = W + 5 * n5 - 1
    pts = M["AC"][:, b] - M["AO"][:, a]
    return {"y": y, "lrv": lrv, "pts": pts, "m_in": M0 + a, "m_out": M0 + b + 1, "n5": n5}


# ------------------------------------------------------------------ distanze e analoghi

def _dtw_matrix(X: np.ndarray, band: int = 3) -> np.ndarray:
    from numba import njit, prange

    @njit(parallel=True, cache=False)
    def run(X, band):
        n, L = X.shape
        D = np.full((n, n), np.inf)
        for i in prange(n):
            dp = np.empty((L + 1, L + 1))
            for j in range(i):
                for a in range(L + 1):
                    for b in range(L + 1):
                        dp[a, b] = np.inf
                dp[0, 0] = 0.0
                for a in range(1, L + 1):
                    lo = max(1, a - band); hi = min(L, a + band)
                    for b in range(lo, hi + 1):
                        c = (X[i, a - 1] - X[j, b - 1]) ** 2
                        m = dp[a - 1, b - 1]
                        if dp[a - 1, b] < m:
                            m = dp[a - 1, b]
                        if dp[a, b - 1] < m:
                            m = dp[a, b - 1]
                        dp[a, b] = c + m
                D[i, j] = np.sqrt(dp[L, L])
        return D
    return run(np.ascontiguousarray(X, dtype=np.float64), band)


def distance_matrix(X: np.ndarray, rep: str) -> np.ndarray:
    """D[i, j] definito per j < i (passato); il resto e' +inf."""
    X = np.where(np.isfinite(X), X, 0.0)
    if rep == "dtw":
        return _dtw_matrix(X)
    if rep == "shape":
        D = np.sqrt(np.maximum(2 * X.shape[1] - 2 * X @ X.T, 0))
    else:
        sq = (X ** 2).sum(1)
        D = np.sqrt(np.maximum(sq[:, None] + sq[None, :] - 2 * X @ X.T, 0))
    D[np.triu_indices(len(X))] = np.inf
    return D


def neighbors(D: np.ndarray, ok: np.ndarray, kmax: int = 100) -> np.ndarray:
    """Per ogni sessione i (ok) gli indici dei kmax vicini fra le LIB_WIN sessioni valide precedenti."""
    n = len(ok)
    NN = np.full((n, kmax), -1)
    idx_ok = np.where(ok)[0]
    for j, i in enumerate(idx_ok):
        if j < LIB_MIN:
            continue
        lib = idx_ok[max(0, j - LIB_WIN):j]
        d = D[i, lib]
        o = np.argsort(d, kind="stable")[:kmax]
        NN[i] = lib[o]
    return NN


def random_neighbors(ok: np.ndarray, kmax: int, rng) -> np.ndarray:
    n = len(ok)
    NN = np.full((n, kmax), -1)
    idx_ok = np.where(ok)[0]
    for j, i in enumerate(idx_ok):
        if j < LIB_MIN:
            continue
        lib = idx_ok[max(0, j - LIB_WIN):j]
        NN[i] = rng.choice(lib, size=kmax, replace=False)
    return NN


def agg(NN: np.ndarray, K: int, v: np.ndarray, fn="mean") -> np.ndarray:
    has = NN[:, 0] >= 0
    out = np.full(len(NN), np.nan)
    vals = v[NN[has, :K]]
    if fn == "mean":
        out[has] = np.nanmean(vals, 1)
    elif fn == "std":
        out[has] = np.nanstd(vals, 1)
    elif fn == "agree":
        out[has] = np.abs(np.nanmean(np.sign(vals), 1))
    return out


# ------------------------------------------------------------------ statistica

def ic_stats(pred, y, sess, mask) -> dict:
    m = mask & np.isfinite(pred) & np.isfinite(y)
    p, yy = pred[m], y[m]
    q = (p - p.mean()) / p.std() * (yy - yy.mean()) / yy.std()
    st = core.day_block_bootstrap(q, sess[m], n_boot=2000)
    st["ic"] = float(np.corrcoef(p, yy)[0, 1])
    s = np.sign(p) * yy
    st["sign_mean"] = float(s.mean())
    st["long_share"] = float((p > 0).mean())
    yr = pd.Series(q).groupby(pd.DatetimeIndex(sess[m]).year).mean()
    st["years_pos"] = f"{int((yr > 0).sum())}/{len(yr)}"
    return st


def rec(test_id: str, desc: str, st: dict, **extra) -> dict:
    core.record(FAM, test_id, desc, "discovery", st, **extra)
    return st


def ts_utc(sess, minute: int) -> pd.Timestamp:
    t = pd.Timestamp(sess) + pd.Timedelta(minutes=int(minute))
    return t.tz_localize(core.NY).tz_convert("UTC")


def trades_frame(M: dict, si, side, m_in, m_out, gross) -> pd.DataFrame:
    si = np.asarray(si, int)
    s = M["sess"][si]
    return pd.DataFrame({"session": pd.DatetimeIndex(s).astype("datetime64[ns]"),
                         "entry_ts": pd.DatetimeIndex([ts_utc(a, m_in) for a in s]),
                         "exit_ts": pd.DatetimeIndex([ts_utc(a, m_out) for a in s]),
                         "side": np.asarray(side, int), "gross_pts": np.asarray(gross, float)})


def evaluate_trades(bars, t: pd.DataFrame) -> dict:
    from lab.controller import beta_component
    net = t["gross_pts"].to_numpy(float) - COST
    days = t["session"].to_numpy()
    st = core.day_block_bootstrap(net, days, n_boot=4000)
    st["gross"] = float(t["gross_pts"].mean())
    st["long_share"] = float((t["side"] > 0).mean())
    yr = core.yearly(net, t["session"])
    st["years_pos"] = f"{int((yr['mean'] > 0).sum())}/{len(yr)}"
    st["yearly"] = {int(k): round(float(v), 2) for k, v in yr["mean"].items()}
    st["drop20"] = core.drop_top(net, 20)
    b = beta_component(bars, t)
    sb = core.day_block_bootstrap(net - b, days, n_boot=4000)
    st["beta_mean"] = float(np.mean(b)); st["net_minus_beta"] = sb["mean"]; st["p_pos_beta"] = sb["p_pos"]
    return st


def fmt(st: dict) -> str:
    keys = ["n", "mean", "lo", "hi", "p_pos", "p_two", "ic", "sign_mean", "gross", "years_pos", "drop20",
            "net_minus_beta", "p_pos_beta", "long_share", "plac_pct"]
    out = []
    for k in keys:
        if k in st:
            v = st[k]
            out.append(f"{k}={v:.4f}" if isinstance(v, float) else f"{k}={v}")
    return " ".join(out)


# ------------------------------------------------------------------ vol del pomeriggio (A03/A04, candidati)

def roll_pred(y, X, ok, win=500, minp=250):
    """OLS mobile: previsione per t stimata sulle `win` sessioni ok precedenti (min `minp`)."""
    X = np.asarray(X, float).reshape(len(y), -1)
    Xv = np.column_stack([np.ones(len(X)), X])
    good = ok & np.isfinite(Xv).all(1) & np.isfinite(y)
    out = np.full(len(y), np.nan)
    idx = np.where(good)[0]
    for j, t in enumerate(idx):
        if j < minp:
            continue
        lib = idx[max(0, j - win):j]
        b, *_ = np.linalg.lstsq(Xv[lib], y[lib], rcond=None)
        out[t] = Xv[t] @ b
    return out


def vol_bench_X(M, W, extended=False):
    """Benchmark lineare della vol del pomeriggio (A03); `extended` aggiunge i controlli di A04."""
    k = W // 5
    r = M["r5"]; s2 = M["s5"] ** 2
    mlrv = np.log((r[:, :k] ** 2).sum(1) / k / s2)
    m30 = np.log((r[:, k - 6:k] ** 2).sum(1) / 6 / s2 + 1e-6)
    nig = np.log(M["night"] ** 2 + 0.01)
    rvd = (r ** 2).sum(1)
    prev = np.full(len(rvd), np.nan); last = np.nan
    for i in range(len(rvd)):
        prev[i] = last
        if M["ok"][i]:
            last = rvd[i]
    yv = np.log(prev / 78 / s2)
    mret = np.log(M["P5"][:, k] / M["P5"][:, 0])
    eff = np.abs(mret) / np.abs(r[:, :k]).sum(1)
    cols = [mlrv, m30, nig, yv, eff]
    if extended:
        mz = mret / (M["s5"] * np.sqrt(k))
        ticks = np.log(M["s5"] * M["O"][:, 0] / core.TICK)
        cols += [mz, M["night"], M["yday"], mlrv ** 2, mlrv * eff, ticks]
    return np.column_stack(cols)


def lz76(s) -> int:
    """Complessita' di Lempel-Ziv 1976 (numero di frasi) di una sequenza (Kaspar-Schuster)."""
    i, k, l, c, kmax, nn = 0, 1, 1, 1, 1, len(s)
    while True:
        if s[i + k - 1] == s[l + k - 1]:
            k += 1
            if l + k > nn:
                c += 1
                break
        else:
            kmax = max(k, kmax)
            i += 1
            if i == l:
                c += 1; l += kmax
                if l + 1 > nn:
                    break
                i, k, kmax = 0, 1, 1
            else:
                k = 1
    return c
