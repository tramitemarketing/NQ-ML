"""Famiglia ml — costruzione del dataset a istanti di decisione fissi.

Disegno (fissato prima di guardare qualunque esito):
- una griglia per sessione di 1440 minuti (17:00 NY della sera prima -> 16:59), prezzi ADJ (coerenti
  attraverso il roll, che cade di notte), minuti mancanti riempiti col close precedente, volume 0;
- istanti di decisione t = 10:00, 10:30, ..., 15:30 NY (12 per sessione). La decisione al minuto t usa
  SOLO le barre con inizio < t (colonne < k); l'ingresso e' l'OPEN della barra che inizia a t;
- esito a orizzonte h: close della barra t+h-1 meno open della barra t (punti). In unita' di volatilita':
  diviso per sig1m * sqrt(h), con sig1m = media delle deviazioni standard dei rendimenti 1m RTH
  delle 20 sessioni PRECEDENTI (nota prima della sessione);
- solo sessioni `valid` (>= 300 barre RTH) come righe; le sessioni precedenti servono per il lookback.
Nessuna normalizzazione calcolata sul campione: ogni scala e' una media mobile del passato.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

NCOL = 1440
RTH0 = 570 + 420          # 09:30 -> colonna 990
RTH1 = 960 + 420          # 16:00 -> colonna 1380 (esclusa)
SLOTS = list(range(600, 931, 30))  # 10:00 .. 15:30 (minuti NY)


def col_of(ny_min: int) -> int:
    return ny_min - 1020 if ny_min >= 1020 else ny_min + 420


def build_grid(bars: pd.DataFrame, daily: pd.DataFrame):
    sess = daily.index
    code = pd.Index(sess).get_indexer(pd.DatetimeIndex(bars["session"].to_numpy()))
    m = bars["ny_min"].to_numpy().astype(int)
    col = np.where(m >= 1020, m - 1020, m + 420)
    ok = code >= 0
    n = len(sess)
    G = {}
    for name, src in (("O", "adj_open"), ("H", "adj_high"), ("L", "adj_low"), ("C", "adj_close"),
                      ("RAW", "close"), ("V", "volume")):
        a = np.full((n, NCOL), np.nan)
        a[code[ok], col[ok]] = bars[src].to_numpy()[ok].astype(float)
        G[name] = a
    present = ~np.isnan(G["C"])
    # forward fill del close lungo la sessione, back fill all'inizio con il primo open
    C = pd.DataFrame(G["C"]).ffill(axis=1)
    first_open = pd.DataFrame(G["O"]).bfill(axis=1).iloc[:, 0]
    Cv = C.to_numpy().copy()
    for i in range(n):
        if np.isnan(Cv[i, 0]):
            j = np.argmax(~np.isnan(Cv[i]))
            Cv[i, :j] = first_open.iat[i] if np.isfinite(first_open.iat[i]) else np.nan
    raw = pd.DataFrame(G["RAW"]).ffill(axis=1).bfill(axis=1).to_numpy()
    G["C"] = Cv
    G["RAW"] = raw
    prevC = np.concatenate([Cv[:, :1], Cv[:, :-1]], axis=1)
    for k in ("O", "H", "L"):
        G[k] = np.where(present, G[k], prevC if k == "O" else Cv)
    G["V"] = np.where(present, G["V"], 0.0)
    G["present"] = present
    return G


def _roll_prev_mean(x: np.ndarray, w: int, minp: int | None = None) -> np.ndarray:
    """media delle w righe PRECEDENTI (esclusa la corrente)."""
    s = pd.DataFrame(x)
    return s.shift(1).rolling(w, min_periods=minp or max(3, w // 2)).mean().to_numpy()


def build_dataset(bars: pd.DataFrame, daily: pd.DataFrame, horizons=(15, 30, 60), slots=SLOTS):
    """Una riga per (sessione valida, slot). Feature solo passate; target a vari orizzonti."""
    daily = daily.copy()
    G = build_grid(bars, daily)
    O, H, L, C, V, RAW = G["O"], G["H"], G["L"], G["C"], G["V"], G["RAW"]
    n = len(daily)
    valid = daily["valid"].to_numpy()

    # ---- scale di volatilita' (tutte dal passato)
    dC = np.diff(C, axis=1)
    rth_d = dC[:, RTH0:RTH1 - 1]
    sd_sess = np.nanstd(rth_d, axis=1)
    sd_sess[~valid] = np.nan
    sd_df = pd.Series(sd_sess)
    sig1m = sd_df.shift(1).rolling(20, min_periods=10).mean().to_numpy()
    sig1m_100 = sd_df.shift(1).rolling(100, min_periods=40).mean().to_numpy()
    sig1m_5 = sd_df.shift(1).rolling(5, min_periods=3).mean().to_numpy()
    rc = daily["rth_close"].to_numpy()
    dclose = pd.Series(rc).diff()
    sigD = dclose.shift(1).rolling(20, min_periods=10).std().to_numpy()   # usa chiusure fino a ieri
    prev_c = pd.Series(rc).shift(1).to_numpy()
    prev_o = daily["rth_open"].shift(1).to_numpy()
    prev_h = daily["rth_high"].shift(1).to_numpy()
    prev_l = daily["rth_low"].shift(1).to_numpy()
    prev_c2 = pd.Series(rc).shift(2).to_numpy()
    c5 = pd.Series(rc).shift(5).to_numpy()
    c20 = pd.Series(rc).shift(20).to_numpy()
    rth_open = O[:, RTH0]
    on_h = np.max(H[:, :RTH0], axis=1)
    on_l = np.min(L[:, :RTH0], axis=1)
    on_v = V[:, :RTH0].sum(1)
    on_v_rel = on_v / _roll_prev_mean(on_v[:, None], 20)[:, 0]
    cumV = np.cumsum(V, axis=1)

    rows = []
    for m in slots:
        k = col_of(m)
        P = C[:, k - 1]                       # ultimo close noto prima di t
        s = sig1m
        f = {}
        f["tod"] = np.full(n, m, float)
        f["dow"] = daily["dow"].to_numpy().astype(float)
        for w in (5, 15, 30, 60, 120, 240):
            f[f"r{w}"] = (P - C[:, k - 1 - w]) / (s * np.sqrt(w))
        kk = k - RTH0
        f["r_sess"] = (P - rth_open) / (s * np.sqrt(kk))
        f["r_on"] = (rth_open - prev_c) / sigD
        f["r_yday"] = (prev_c - prev_o) / sigD
        f["r_yday_cc"] = (prev_c - prev_c2) / sigD
        f["r_5d"] = (P - c5) / (sigD * np.sqrt(5))
        f["r_20d"] = (P - c20) / (sigD * np.sqrt(20))
        f["dist_yclose"] = (P - prev_c) / sigD
        # volatilita' realizzata recente, relativa alla scala
        for w in (15, 30, 60):
            f[f"rv{w}"] = np.std(dC[:, k - 1 - w:k - 1], axis=1) / s
        f["rv_sess"] = np.std(dC[:, RTH0:k - 1], axis=1) / s
        f["rv_on"] = np.std(dC[:, :RTH0 - 1], axis=1) / s
        f["vol_regime"] = sig1m_5 / sig1m_100
        f["sig_level"] = s / RAW[:, k - 1] * 1e4        # vol in bp del prezzo (grezzo)
        # volume relativo per ora del giorno
        cv = cumV[:, k - 1] - cumV[:, RTH0 - 1]
        f["relvol_sess"] = cv / _roll_prev_mean(cv[:, None], 20)[:, 0]
        v30 = cumV[:, k - 1] - cumV[:, k - 31]
        f["relvol_30"] = v30 / _roll_prev_mean(v30[:, None], 20)[:, 0]
        f["relvol_on"] = on_v_rel
        # posizione nei range
        hi = np.max(H[:, RTH0:k], axis=1)
        lo = np.min(L[:, RTH0:k], axis=1)
        f["pos_today"] = (P - lo) / np.maximum(hi - lo, 1e-9)
        f["range_today"] = (hi - lo) / (s * np.sqrt(kk))
        f["pos_yday"] = (P - prev_l) / np.maximum(prev_h - prev_l, 1e-9)
        f["dist_onh"] = (on_h - P) / sigD
        f["dist_onl"] = (P - on_l) / sigD
        f["dist_hi"] = (hi - P) / (s * np.sqrt(kk))
        f["dist_lo"] = (P - lo) / (s * np.sqrt(kk))
        # vwap RTH
        tp = (H[:, RTH0:k] + L[:, RTH0:k] + C[:, RTH0:k]) / 3
        vv = V[:, RTH0:k]
        vw = (tp * vv).sum(1) / np.maximum(vv.sum(1), 1)
        f["dist_vwap"] = (P - vw) / (s * np.sqrt(kk))
        # forma della distribuzione recente
        x = dC[:, k - 61:k - 1]
        xm = x - x.mean(1, keepdims=True)
        sd = x.std(1) + 1e-12
        f["skew60"] = (xm ** 3).mean(1) / sd ** 3
        f["kurt60"] = (xm ** 4).mean(1) / sd ** 4
        f["ac1_60"] = (xm[:, 1:] * xm[:, :-1]).mean(1) / sd ** 2
        xs = dC[:, RTH0:k - 1]
        xsm = xs - xs.mean(1, keepdims=True)
        f["ac1_sess"] = (xsm[:, 1:] * xsm[:, :-1]).mean(1) / (xs.var(1) + 1e-12)
        x5 = C[:, k - 121:k:5]
        f["vr5_120"] = np.var(np.diff(x5, axis=1), axis=1) / (5 * np.var(dC[:, k - 121:k - 1], axis=1) + 1e-12)
        # numero tondo (prezzo grezzo)
        pr = RAW[:, k - 1]
        f["dist_round100"] = ((pr + 50) % 100 - 50) / (s * np.sqrt(30))
        f["dist_round50"] = ((pr + 25) % 50 - 25) / (s * np.sqrt(30))

        tgt = {}
        entry = O[:, k]
        for h in horizons:
            if k + h - 1 < RTH1:
                ex = C[:, k + h - 1]
                tgt[f"pts{h}"] = ex - entry
                tgt[f"y{h}"] = (ex - entry) / (s * np.sqrt(h))
                # variante con ingresso ritardato di 1 minuto (close della barra t): toglie il rimbalzo bid-ask
                tgt[f"y{h}_d1"] = (ex - C[:, k]) / (s * np.sqrt(h))
            else:
                tgt[f"pts{h}"] = np.full(n, np.nan)
                tgt[f"y{h}"] = np.full(n, np.nan)
                tgt[f"y{h}_d1"] = np.full(n, np.nan)
        # chiusura RTH (15:59 close)
        tgt["pts_close"] = C[:, RTH1 - 1] - entry
        tgt["y_close"] = tgt["pts_close"] / (s * np.sqrt(RTH1 - k))
        df = pd.DataFrame({**f, **tgt})
        df["session"] = daily.index.to_numpy()
        df["slot"] = m
        df["k"] = k
        df["sig1m"] = s
        df["entry"] = entry
        df["valid"] = valid
        df["in_phase"] = daily["in_phase"].to_numpy() if "in_phase" in daily else True
        rows.append(df)
    out = pd.concat(rows, ignore_index=True)
    out = out[out["valid"] & np.isfinite(out["sig1m"]) & np.isfinite(out["entry"])]
    out = out.sort_values(["session", "slot"]).reset_index(drop=True)
    return out, G


FEATURES = ["tod", "dow", "r5", "r15", "r30", "r60", "r120", "r240", "r_sess", "r_on", "r_yday",
            "r_yday_cc", "r_5d", "r_20d", "dist_yclose", "rv15", "rv30", "rv60", "rv_sess", "rv_on",
            "vol_regime", "sig_level", "relvol_sess", "relvol_30", "relvol_on", "pos_today",
            "range_today", "pos_yday", "dist_onh", "dist_onl", "dist_hi", "dist_lo", "dist_vwap",
            "skew60", "kurt60", "ac1_60", "ac1_sess", "vr5_120", "dist_round100", "dist_round50"]
