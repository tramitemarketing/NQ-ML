"""Feature giornaliere dell'indicatore «Range Atteso», costruite ESATTAMENTE come le vede lo script Pine.

Lo script Pine lavora su barre da 30 minuti (request.security "30") di NQ1!: su TradingView il continuo
cambia contratto al confine di sessione (18:00 NY), quindi dentro una sessione tutti i prezzi sono dello
stesso contratto. Qui si ricostruisce la stessa serie dai dati 1m del laboratorio:

  prezzo_sessione = adj - offset_sessione,   offset_sessione = adj_close - close dell'ULTIMA barra della sessione

cioe' i prezzi grezzi del contratto attivo a fine sessione, senza il salto di roll che Databento mette alle
00:00 UTC dentro la notte. Differenze (range) = differenze adj; livelli = grezzi del contratto corrente.

Definizioni (identiche nel Pine, vedi range_atteso.pine):
  sessione        = barra giornaliera CME (18:00 NY del giorno prima -> 17:00 NY)
  notte (ON)      = barre della sessione con ora NY >= 18:00 oppure < 09:30   (18:00 -> 09:29:59)
  RTH             = barre 09:30 -> 15:59:59
  giorno valido   = almeno 10 barre RTH da 30 minuti con scambi (esclude le mezze giornate 9:30-13:00)
  y               = ln(100 * (max RTH - min RTH) / open RTH)          [log del range in % dell'apertura]
  l1, m5, m22     = ultimo y, media degli ultimi 5 e 22 y dei giorni VALIDI precedenti (strettamente prima)
  lon             = ln(100 * max(maxON - minON, 0.25) / close delle 09:29)
  ref             = close della barra 09:00-09:30 (= close delle 09:29), prezzo del contratto corrente

Nessuna quantita' di una sessione S usa dati successivi alle 09:29:59 di S (le colonne di esito
rth_* servono solo a VALUTARE la previsione, mai a costruirla).
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lab import core  # noqa: E402

HERE = Path(__file__).resolve().parent
TICK = 0.25
MIN_RTH_30M = 10
N_HIST = 22
PHASE_ALL = ("discovery", "validation", "confirmation")


def load_bars() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Barre 1m e tabella giornaliera 2010-06-07 -> 2026-03-19, SOLO tramite lab.core.load.
    Le fasi validation/confirmation richiedono LAB_CONTROLLER=1: usato qui solo per stimare e valutare
    questo indicatore (autorizzazione dell'utente). La cassaforte (>= 2026-03-20) non e' caricabile."""
    os.environ["LAB_CONTROLLER"] = "1"
    parts = [core.load(p) for p in PHASE_ALL]
    bars = pd.concat([b for b, _ in parts]).sort_index()
    daily = pd.concat([d for _, d in parts]).sort_index()
    assert pd.Timestamp(bars["session"].max()) < pd.Timestamp(core.VAULT_START)
    assert daily.index.max() < pd.Timestamp(core.VAULT_START)
    assert not bars.index.duplicated().any()
    return bars, daily


def session_prices(bars: pd.DataFrame) -> pd.DataFrame:
    """OHLC 1m nel 'contratto della sessione' (come NQ1! su TradingView). Colonne p_open/p_high/p_low/p_close."""
    sess = bars["session"].to_numpy()
    off_last = (bars["adj_close"] - bars["close"]).groupby(sess).last()
    off = off_last.reindex(pd.DatetimeIndex(sess)).to_numpy()
    out = pd.DataFrame(index=bars.index)
    for c in ("open", "high", "low", "close"):
        out["p_" + c] = bars["adj_" + c].to_numpy() - off
    out["session"] = sess
    out["ny_min"] = bars["ny_min"].to_numpy()
    return out


def bars30(bars: pd.DataFrame) -> pd.DataFrame:
    """Barre da 30 minuti (allineate a :00/:30 NY) come le costruisce TradingView, una riga per barra.
    Indice: (session, b30) con b30 = minuto NY // 30 riportato all'ordine della sessione (18:00 = primo)."""
    p = session_prices(bars)
    m = p["ny_min"].to_numpy()
    b = m // 30
    order = np.where(m >= 1080, b - 48, b)          # 18:00 -> -12 ... 17:30 -> 35 (ordine di sessione)
    p["b30"] = b
    p["ord"] = order
    g = p.groupby(["session", "ord"], sort=True)
    o = pd.DataFrame({"b30": g["b30"].first(), "open": g["p_open"].first(), "high": g["p_high"].max(),
                      "low": g["p_low"].min(), "close": g["p_close"].last()})
    o["m"] = o["b30"] * 30                            # minuto NY di apertura della barra da 30m
    return o


def daily_table(bars: pd.DataFrame) -> pd.DataFrame:
    """Una riga per sessione (tutte, anche non valide): feature note alle 09:29:59 + esiti RTH + OHLC Globex."""
    b = bars30(bars).reset_index()
    m = b["m"].to_numpy()
    is_on = (m >= 1080) | (m < 570)
    is_rth = (m >= 570) & (m < 960)
    on = b[is_on].groupby("session")
    rth = b[is_rth].groupby("session")
    ref = b[b["m"] == 540].groupby("session")["close"].last()     # close della barra 09:00-09:30
    allg = b.groupby("session")
    t = pd.DataFrame({
        "on_hi": on["high"].max(), "on_lo": on["low"].min(), "ref": ref,
        "rth_open": rth["open"].first(), "rth_hi": rth["high"].max(), "rth_lo": rth["low"].min(),
        "rth_close": rth["close"].last(), "n30_rth": rth.size(),
        "d_hi": allg["high"].max(), "d_lo": allg["low"].min(), "d_close": allg["close"].last(),
    })
    t.index = pd.DatetimeIndex(t.index)
    t["n30_rth"] = t["n30_rth"].fillna(0).astype(int)
    t["valid"] = t["n30_rth"] >= MIN_RTH_30M
    t["rng"] = t["rth_hi"] - t["rth_lo"]
    t["y"] = np.log(100 * t["rng"] / t["rth_open"])
    # storia dei soli giorni validi, poi "ultimo valore noto STRETTAMENTE prima di S"
    yv = t.loc[t["valid"], "y"]
    h = pd.DataFrame({"l1": yv, "m5": yv.rolling(5).mean(), "m22": yv.rolling(N_HIST).mean(),
                      "nh": np.minimum(np.arange(1, len(yv) + 1), N_HIST)}, index=yv.index)
    h = h.reindex(t.index).ffill().shift(1)
    t = t.join(h)
    t["lon"] = np.log(100 * np.maximum(t["on_hi"] - t["on_lo"], TICK) / t["ref"])
    # ATR(14) di Wilder sulle barre giornaliere Globex (come ta.atr(14) sul "D" di TradingView), noto a S = fino a S-1
    pc = t["d_close"].shift(1)
    tr = np.maximum(t["d_hi"] - t["d_lo"], np.maximum((t["d_hi"] - pc).abs(), (t["d_lo"] - pc).abs()))
    tr = tr.fillna(t["d_hi"] - t["d_lo"])
    t["atr14"] = rma(tr.to_numpy(), 14)
    t["atr14_prev"] = t["atr14"].shift(1)
    # media semplice del range RTH delle 20 sessioni valide precedenti
    mv = t.loc[t["valid"], "rng"].rolling(20).mean()
    t["mean20"] = mv.reindex(t.index).ffill().shift(1)
    return t


def rma(x: np.ndarray, n: int) -> np.ndarray:
    """ta.rma di Pine: seme = media semplice dei primi n valori, poi a = 1/n."""
    out = np.full(len(x), np.nan)
    if len(x) < n:
        return out
    out[n - 1] = np.mean(x[:n])
    a = 1.0 / n
    for i in range(n, len(x)):
        out[i] = a * x[i] + (1 - a) * out[i - 1]
    return out
