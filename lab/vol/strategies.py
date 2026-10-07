"""Famiglia vol, binario B: generatori di trade (fn(bars, daily) -> DataFrame) e regime di volatilita'.

Convenzioni (identiche per tutti):
- regime = previsione HAR "a pesi fissi" di log RV RTH: (logRV_{t-1} + media5 + media22)/3, nota PRIMA
  dell'apertura di t; percentile causale rispetto alle 250 sessioni valide precedenti (esclusa t).
- entry_ts = timestamp della barra 1m nel cui open/intrabar avviene l'ingresso; exit_ts = timestamp della
  barra 1m al cui close si esce. gross_pts in punti per 1 contratto (grezzi entro RTH, adj oltre la notte).
- nessuna decisione usa dati successivi all'ingresso.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from lab import core
from lab.vol import common as C

RTH0, RTH1 = 570, 960          # 9:30 .. 15:59 (ultima barra 959)


def rth_matrix(bars: pd.DataFrame, daily: pd.DataFrame):
    """Matrici sessione x minuto (390) di open/high/low/close grezzi e timestamp, solo sessioni valide."""
    sess = daily.index[daily["valid"]]
    b = bars[bars["rth"]]
    m = b["ny_min"].to_numpy() - RTH0
    s = pd.DatetimeIndex(b["session"].to_numpy())
    si = sess.get_indexer(s)
    ok = si >= 0
    shape = (len(sess), 390)
    M = {}
    for c in ("open", "high", "low", "close"):
        a = np.full(shape, np.nan)
        a[si[ok], m[ok]] = b[c].to_numpy()[ok]
        M[c] = a
    ts = np.full(shape, np.datetime64("NaT"), dtype="datetime64[ns]")
    ts[si[ok], m[ok]] = b.index.tz_convert("UTC").tz_localize(None).to_numpy()[ok]
    M["ts"] = ts
    M["sess"] = sess
    # riempi eventuali minuti mancanti con l'ultimo close (per prezzi di uscita)
    cl = pd.DataFrame(M["close"]).ffill(axis=1).to_numpy()
    M["close_ff"] = cl
    return M


def _ts(M, i, j):
    """timestamp della barra (i, j) o, se manca, della prima barra successiva disponibile."""
    row = M["ts"][i]
    jj = j
    while jj < 390 and np.isnat(row[jj]):
        jj += 1
    if jj >= 390:
        jj = j
        while jj >= 0 and np.isnat(row[jj]):
            jj -= 1
    return pd.Timestamp(row[jj], tz="UTC")


def regime(daily: pd.DataFrame, bars: pd.DataFrame, feats: pd.DataFrame | None = None) -> pd.DataFrame:
    f = C.daily_features(bars, daily) if feats is None else feats
    fc = ((f["h1"] + f["h5"] + f["h22"]) / 3).shift(1)
    out = pd.DataFrame({"fc": fc})
    out["pct"] = C.rolling_pct_rank(fc, 250, 120)
    out["atr20"] = f["atr20"]
    return out


def mk(rows):
    t = pd.DataFrame(rows, columns=["session", "entry_ts", "exit_ts", "side", "gross_pts"])
    t["session"] = pd.to_datetime(t["session"])
    return t


# ---------------------------------------------------------------- B1: rottura del range della prima ora
def ib_breakout(bars, daily, ib_min=60, last_entry=15 * 60, M=None):
    """Prima rottura (touch + 1 tick) dell'IB (prime `ib_min` minuti) dopo la sua fine; lato = rottura;
    fill = max(open, livello) (stop); uscita al close delle 15:59. Una per giorno."""
    M = rth_matrix(bars, daily) if M is None else M
    rows = []
    jl = last_entry - RTH0
    for i, s in enumerate(M["sess"]):
        h, l, o = M["high"][i], M["low"][i], M["open"][i]
        ibh, ibl = np.nanmax(h[:ib_min]), np.nanmin(l[:ib_min])
        if not np.isfinite(ibh):
            continue
        up, dn = ibh + core.TICK, ibl - core.TICK
        for j in range(ib_min, jl):
            if not np.isfinite(h[j]):
                continue
            hit_u, hit_d = h[j] >= up, l[j] <= dn
            if hit_u and hit_d:
                break                       # barra ambigua: nessun trade
            if hit_u or hit_d:
                side = 1 if hit_u else -1
                px = max(o[j], up) if hit_u else min(o[j], dn)
                ex = M["close_ff"][i, 389]
                rows.append((s, _ts(M, i, j), _ts(M, i, 389), side, side * (ex - px)))
                break
    return mk(rows)


# ---------------------------------------------------------------- B2: direzione della prima ora
def first_hour_follow(bars, daily, ib_min=60, M=None):
    """Alle 10:30 (open della barra ib_min) entra nel verso del movimento open->10:29 close; esce alle 15:59."""
    M = rth_matrix(bars, daily) if M is None else M
    rows = []
    for i, s in enumerate(M["sess"]):
        o0 = M["open"][i, 0]; c = M["close_ff"][i, ib_min - 1]; e = M["open"][i, ib_min]
        if not (np.isfinite(o0) and np.isfinite(c) and np.isfinite(e)) or c == o0:
            continue
        side = 1 if c > o0 else -1
        rows.append((s, _ts(M, i, ib_min), _ts(M, i, 389), side, side * (M["close_ff"][i, 389] - e)))
    return mk(rows)


# ---------------------------------------------------------------- B3: rottura del range di ieri
def prior_range_breakout(bars, daily, M=None):
    """Stop d'ingresso sopra il massimo RTH di ieri / sotto il minimo (+-1 tick), dalle 9:30 alle 15:00,
    prima rottura, uscita 15:59. Livelli di ieri su prezzi adj (attraversa la notte) convertiti in grezzi
    con l'offset adj-grezzo di oggi."""
    M = rth_matrix(bars, daily) if M is None else M
    d = daily[daily["valid"]]
    rows = []
    for i, s in enumerate(M["sess"]):
        if i == 0:
            continue
        # offset adj - grezzo di oggi: dal primo bar RTH
        raw_open = M["open"][i, 0]
        if not np.isfinite(raw_open):
            continue
        off = d["rth_open"].iat[i] - raw_open
        ph, pl = d["rth_high"].iat[i - 1] - off, d["rth_low"].iat[i - 1] - off
        if raw_open > ph or raw_open < pl:
            continue                      # apertura gia' fuori: escluso (il livello non e' un "breakout")
        up, dn = ph + core.TICK, pl - core.TICK
        h, l, o = M["high"][i], M["low"][i], M["open"][i]
        for j in range(0, 330):
            if not np.isfinite(h[j]):
                continue
            hu, hd = h[j] >= up, l[j] <= dn
            if hu and hd:
                break
            if hu or hd:
                side = 1 if hu else -1
                px = max(o[j], up) if hu else min(o[j], dn)
                rows.append((s, _ts(M, i, j), _ts(M, i, 389), side, side * (M["close_ff"][i, 389] - px)))
                break
    return mk(rows)


# ---------------------------------------------------------------- B4/B5/B8: trade giornalieri RTH
def rth_day(bars, daily, side_series: pd.Series, M=None):
    """Open 9:30 -> close 15:59 nel verso side_series (indice sessione, valori +1/-1/0, noti prima dell'open)."""
    M = rth_matrix(bars, daily) if M is None else M
    rows = []
    sd = side_series.reindex(M["sess"]).fillna(0).to_numpy()
    for i, s in enumerate(M["sess"]):
        if sd[i] == 0:
            continue
        o, c = M["open"][i, 0], M["close_ff"][i, 389]
        if not (np.isfinite(o) and np.isfinite(c)):
            continue
        rows.append((s, _ts(M, i, 0), _ts(M, i, 389), int(sd[i]), sd[i] * (c - o)))
    return mk(rows)


def window_trade(bars, daily, side_series: pd.Series, m_in: int, m_out: int, M=None):
    """Ingresso all'open della barra NY m_in, uscita al close della barra m_out-1 (RTH)."""
    M = rth_matrix(bars, daily) if M is None else M
    j0, j1 = m_in - RTH0, m_out - RTH0 - 1
    rows = []
    sd = side_series.reindex(M["sess"]).fillna(0).to_numpy()
    for i, s in enumerate(M["sess"]):
        if sd[i] == 0:
            continue
        o, c = M["open"][i, j0], M["close_ff"][i, j1]
        if not (np.isfinite(o) and np.isfinite(c)):
            continue
        rows.append((s, _ts(M, i, j0), _ts(M, i, j1), int(sd[i]), sd[i] * (c - o)))
    return mk(rows)
