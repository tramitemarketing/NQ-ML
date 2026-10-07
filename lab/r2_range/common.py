"""Famiglia r2_range (giro 2): usare la volatilita' PREVISTA per la DIREZIONE.

Convenzioni fissate PRIMA di guardare qualunque risultato (2026-09-23):

PREVISIONE DEL RANGE (strettamente causale, nota alle 09:30):
  y_t = log(range RTH_t in % dell'open grezzo RTH)
  regressori: y di ieri, media di y sulle 5 e 22 sessioni valide PRECEDENTI (HAR sul range),
              log(range notturno 18:00-09:29 della sessione t, adj, in % del close grezzo delle 09:29)
  OLS mobile sulle 500 sessioni valide precedenti (min 150), stimata SOLO su sessioni < t.
  R_hat_t (punti) = exp(pred) * smearing(media di exp(residui) della finestra) / 100 * open grezzo RTH.
  (L'open grezzo delle 09:30 e' noto all'istante in cui R_hat serve: tutti i segnali partono da 09:31.)
  Variante "naive" (solo diagnostica/placebo): media dei range RTH delle 20 sessioni valide precedenti.

ESECUZIONE:
  Segnale alla chiusura della barra m (1m); ingresso all'OPEN della barra m+1.
  Stop: fill al livello di stop, o all'open se la barra apre oltre (peggiore).
  Target: fill solo con trade-through di 1 tick (high >= T + 0,25 per il long), al prezzo T.
  Stop e target nella stessa barra -> stop (peggiore). La barra d'ingresso conta gia'.
  Uscita a tempo: close della barra (t_exit - 1); a fine giornata = close della barra 15:59.
  Solo sessioni valide, prezzi adj (in RTH nessun roll), costi core.COST_RT_POINTS = 0,75.

UNITA' (dichiarata prima): metrica di decisione = NETTO IN PUNTI per contratto (come il controller).
  Diagnostica secondaria: netto in unita' di R_hat (net / R_hat) e lordo in R_hat.
  Le soglie dei segnali sono sempre in unita' di R_hat (scale-free).
"""
from __future__ import annotations

import pickle
from pathlib import Path

import numpy as np
import pandas as pd

from lab import core

FAM = "r2_range"
COST = core.COST_RT_POINTS
TICK = core.TICK
M0, M1 = 570, 960          # minuti RTH
NM = M1 - M0               # 390


# ------------------------------------------------------------------ matrici RTH

def build(bars: pd.DataFrame, daily: pd.DataFrame) -> dict:
    r = bars[bars["rth"]]
    P = {}
    for col in ("adj_open", "adj_high", "adj_low", "adj_close", "open", "close"):
        p = r.pivot_table(index="session", columns="ny_min", values=col, aggfunc="first")
        P[col] = p.reindex(columns=range(M0, M1))
    sess = P["adj_close"].index
    C = P["adj_close"].ffill(axis=1)
    prevC = C.shift(1, axis=1)
    for k in ("adj_open", "adj_high", "adj_low"):
        P[k] = P[k].fillna(prevC)
    P["adj_close"] = C
    P["close"] = P["close"].ffill(axis=1)
    P["open"] = P["open"].fillna(P["close"].shift(1, axis=1))
    dv = daily.reindex(sess)
    ok = (dv["valid"].fillna(False).to_numpy() & P["adj_open"][M0].notna().to_numpy()
          & P["adj_close"][M1 - 1].notna().to_numpy())
    out = {k: v.to_numpy(float) for k, v in P.items()}
    out["sess"] = pd.DatetimeIndex(sess)
    out["ok"] = ok
    out["in_phase"] = dv["in_phase"].fillna(False).to_numpy()
    rc = dv["rth_close"].where(dv["valid"].fillna(False))
    out["prev_close"] = rc.ffill().shift(1).to_numpy()
    H = np.where(np.isfinite(out["adj_high"]), out["adj_high"], -np.inf)
    L = np.where(np.isfinite(out["adj_low"]), out["adj_low"], np.inf)
    out["runH"] = np.maximum.accumulate(H, axis=1)
    out["runL"] = np.minimum.accumulate(L, axis=1)
    return out


def ts_utc(sess, minute: int) -> pd.Timestamp:
    t = pd.Timestamp(sess) + pd.Timedelta(minutes=int(minute))
    return t.tz_localize(core.NY).tz_convert("UTC")


# ------------------------------------------------------------------ previsione del range

def overnight(bars: pd.DataFrame) -> pd.DataFrame:
    m = bars["ny_min"].to_numpy()
    on = bars[(~bars["rth"].to_numpy()) & ((m >= 1080) | (m < 570))]
    g = on.groupby("session")
    return pd.DataFrame({"on_hi": g["adj_high"].max(), "on_lo": g["adj_low"].min(),
                         "on_rawlast": g["close"].last(), "on_last": g["adj_close"].last()})


def forecast(bars: pd.DataFrame, daily: pd.DataFrame, win: int = 500, minp: int = 150) -> pd.DataFrame:
    """Una riga per sessione valida: R_hat (punti), R_naive, range realizzato, ecc."""
    d = daily[daily["valid"]].copy()
    rb = bars[bars["rth"]]
    gr = rb.groupby("session")
    d["raw_open"] = gr["open"].first().reindex(d.index)
    on = overnight(bars).reindex(d.index)
    d = d.join(on)
    d["rng_pts"] = d["rth_high"] - d["rth_low"]
    y = np.log(d["rng_pts"] / d["raw_open"] * 100)
    d["y"] = y
    X = pd.DataFrame({
        "l1": y.shift(1), "l5": y.shift(1).rolling(5).mean(), "l22": y.shift(1).rolling(22).mean(),
        "lon": np.log((d["on_hi"] - d["on_lo"]).clip(lower=TICK) / d["on_rawlast"] * 100),
    }, index=d.index)
    Xv = np.column_stack([np.ones(len(X)), X.to_numpy()])
    yv = y.to_numpy()
    okr = np.isfinite(Xv).all(1) & np.isfinite(yv)
    pred = np.full(len(yv), np.nan)
    smear = np.full(len(yv), np.nan)
    for t in range(len(yv)):
        if not np.isfinite(Xv[t]).all():
            continue
        lo = max(0, t - win)
        m = okr[lo:t]
        if m.sum() < minp:
            continue
        A, b = Xv[lo:t][m], yv[lo:t][m]
        beta, *_ = np.linalg.lstsq(A, b, rcond=None)
        pred[t] = Xv[t] @ beta
        smear[t] = np.mean(np.exp(b - A @ beta))
    d["pred_y"] = pred
    d["R_hat"] = np.exp(pred) * smear / 100 * d["raw_open"]
    d["R_naive"] = d["rng_pts"].shift(1).rolling(20).mean()
    d["on_mid"] = (d["on_hi"] + d["on_lo"]) / 2
    d["prev_close"] = d["rth_close"].shift(1)
    rel = (d["R_hat"] / d["raw_open"]).to_numpy()
    pr = np.full(len(rel), np.nan)
    for i in range(len(rel)):
        past = rel[max(0, i - 250):i]
        past = past[np.isfinite(past)]
        if len(past) >= 100 and np.isfinite(rel[i]):
            pr[i] = (past < rel[i]).mean()
    d["R_pct"] = pr
    return d


def attach(M: dict, F: pd.DataFrame) -> None:
    f = F.reindex(M["sess"])
    for c in ("R_hat", "R_naive", "R_pct", "on_mid", "on_hi", "on_lo", "raw_open", "rng_pts"):
        M[c] = f[c].to_numpy(float)
    M["ok"] = M["ok"] & np.isfinite(M["R_hat"]) & np.isfinite(M["prev_close"])


_CACHE = Path(__file__).resolve().parents[2] / "data" / "lab" / "r2_range_disc.pkl"


def prepare(bars, daily):
    F = forecast(bars, daily)
    M = build(bars, daily)
    attach(M, F)
    return M, F


def setup_discovery():
    """(bars, daily, M, F) sul discovery; M e F in cache locale (solo discovery)."""
    bars, daily = core.load("discovery")
    if _CACHE.exists():
        M, F = pickle.load(open(_CACHE, "rb"))
    else:
        M, F = prepare(bars, daily)
        pickle.dump((M, F), open(_CACHE, "wb"))
    return bars, daily, M, F


# ------------------------------------------------------------------ simulatore

def sim(M: dict, si, m_in, side, stop_d=None, tgt_d=None, m_out=None) -> pd.DataFrame:
    """Trade: sessione si (indice riga), ingresso all'open della barra m_in (minuto NY), lato side,
    stop/target a distanza in punti dal prezzo d'ingresso (NaN = assente), uscita a tempo alla close
    della barra m_out-1 (default 960 -> close 15:59)."""
    si = np.asarray(si, int); m_in = np.asarray(m_in, int); side = np.asarray(side, int)
    n = len(si)
    stop_d = np.full(n, np.nan) if stop_d is None else np.broadcast_to(np.asarray(stop_d, float), (n,))
    tgt_d = np.full(n, np.nan) if tgt_d is None else np.broadcast_to(np.asarray(tgt_d, float), (n,))
    m_out = np.full(n, M1) if m_out is None else np.minimum(np.broadcast_to(np.asarray(m_out, int), (n,)), M1)
    O, H, L, C = M["adj_open"], M["adj_high"], M["adj_low"], M["adj_close"]
    gross = np.full(n, np.nan); mx = np.zeros(n, int); how = np.empty(n, object)
    for i in range(n):
        s, a, z, sd = si[i], m_in[i] - M0, m_out[i] - M0, side[i]
        if a >= z or a < 0:
            continue
        e = O[s, a]
        st = e - sd * stop_d[i] if np.isfinite(stop_d[i]) else np.nan
        tg = e + sd * tgt_d[i] if np.isfinite(tgt_d[i]) else np.nan
        px, ex, h = C[s, z - 1], z, "time"
        if np.isfinite(st) or np.isfinite(tg):
            hh, ll, oo = H[s, a:z], L[s, a:z], O[s, a:z]
            if sd > 0:
                hs = ll <= st if np.isfinite(st) else np.zeros(z - a, bool)
                ht = hh >= tg + TICK if np.isfinite(tg) else np.zeros(z - a, bool)
            else:
                hs = hh >= st if np.isfinite(st) else np.zeros(z - a, bool)
                ht = ll <= tg - TICK if np.isfinite(tg) else np.zeros(z - a, bool)
            js = np.argmax(hs) if hs.any() else 10**6
            jt = np.argmax(ht) if ht.any() else 10**6
            if js <= jt and js < 10**6:
                op = oo[js]
                fill = st if js == 0 else (min(op, st) if sd > 0 else max(op, st))
                px, ex, h = fill, a + js + 1, "stop"
            elif jt < 10**6:
                px, ex, h = tg, a + jt + 1, "tgt"
        gross[i] = sd * (px - e); mx[i] = ex + M0; how[i] = h
    return pd.DataFrame({"session": M["sess"][si], "si": si, "m_in": m_in, "m_out": mx, "side": side,
                         "gross_pts": gross, "R": M["R_hat"][si], "how": how})


def to_controller(M: dict, t: pd.DataFrame) -> pd.DataFrame:
    """Formato del controller (entry_ts = open della barra d'ingresso, exit_ts = inizio della barra
    successiva all'ultima tenuta)."""
    t = t[np.isfinite(t["gross_pts"])].copy()
    ent = [ts_utc(s, m) for s, m in zip(t["session"], t["m_in"])]
    ext = [ts_utc(s, m) for s, m in zip(t["session"], t["m_out"])]
    return pd.DataFrame({"session": pd.DatetimeIndex(t["session"]).astype("datetime64[ns]"),
                         "entry_ts": pd.DatetimeIndex(ent), "exit_ts": pd.DatetimeIndex(ext),
                         "side": t["side"].astype(int).to_numpy(),
                         "gross_pts": t["gross_pts"].astype(float).to_numpy()})


# ------------------------------------------------------------------ statistica

def beta(bars: pd.DataFrame, M: dict, t: pd.DataFrame) -> np.ndarray:
    from lab.controller import beta_component
    return beta_component(bars, to_controller(M, t))


def evaluate(t: pd.DataFrame, bars=None, M=None, full=True) -> dict:
    t = t[np.isfinite(t["gross_pts"])]
    if len(t) == 0:
        return {"n": 0}
    net = t["gross_pts"].to_numpy(float) - COST
    days = t["session"].to_numpy()
    st = core.day_block_bootstrap(net, days, n_boot=4000)
    st["gross"] = float(t["gross_pts"].mean())
    st["net_R"] = float(np.nanmean(net / t["R"].to_numpy()))
    st["gross_R"] = float(np.nanmean(t["gross_pts"].to_numpy() / t["R"].to_numpy()))
    st["long_share"] = float((t["side"] > 0).mean())
    if full:
        yr = core.yearly(net, t["session"])
        st["years_pos"] = f"{int((yr['mean'] > 0).sum())}/{len(yr)}"
        st["yearly"] = {int(k): round(float(v), 3) for k, v in yr["mean"].items()}
        st["drop20"] = core.drop_top(net, 20)
        if bars is not None and M is not None:
            b = beta(bars, M, t)
            sb = core.day_block_bootstrap(net - b, days, n_boot=4000)
            st["beta_mean"] = float(np.mean(b))
            st["net_minus_beta"] = sb["mean"]; st["p_pos_beta"] = sb["p_pos"]
    return st


def rec(test_id: str, desc: str, st: dict, **extra) -> dict:
    core.record(FAM, test_id, desc, "discovery", st, **extra)
    return st


def fmt(st: dict) -> str:
    keys = ["n", "mean", "lo", "hi", "p_pos", "p_two", "gross", "gross_R", "net_R", "years_pos", "drop20",
            "net_minus_beta", "p_pos_beta", "long_share"]
    out = []
    for k in keys:
        if k in st:
            v = st[k]
            out.append(f"{k}={v:.3f}" if isinstance(v, float) else f"{k}={v}")
    return " ".join(out)
