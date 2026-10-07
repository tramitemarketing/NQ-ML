"""Audit meccanico del look-ahead (generalizza lab/audit_lookahead.py).

Per strategie fornite come funzione Python `fn(bars) -> trades`:
  - `bars`: DataFrame con indice UTC e colonne open, high, low, close, volume (più eventuali colonne
    extra del cliente);
  - `trades`: DataFrame con almeno entry_time (o entry_ts) e side; opzionali exit_time e pnl.
Per ogni istante di taglio T il futuro viene ALTERATO: a tutte le barre con inizio > T si somma una
tendenza forte (verso l'alto in un passaggio, verso il basso nell'altro) con rumore, i volumi vengono
moltiplicati per fattori casuali, le colonne numeriche extra vengono rimescolate; la barra che inizia
esattamente a T conserva l'apertura ma cambia massimo, minimo, chiusura e volume (chi entra
all'apertura di una barra non può conoscerne la chiusura). Una strategia causale deve produrre, per i
trade con ingresso <= T, gli stessi ingressi e gli stessi lati; per quelli chiusi <= T anche la stessa
uscita e lo stesso risultato. Qualunque differenza = la strategia usa informazione futura.
I tagli sono casuali nel periodo E esattamente agli ingressi di trade reali (il punto più sensibile).
Il controllo positivo (una strategia che bara apposta) dimostra che l'audit ha potere su quei dati.
"""
from __future__ import annotations

import traceback

import numpy as np
import pandas as pd

PRICE_COLS = ("open", "high", "low", "close")


def normalize_trades(t: pd.DataFrame) -> pd.DataFrame:
    t = pd.DataFrame(t).copy()
    ren = {"entry_time": "entry_ts", "exit_time": "exit_ts", "pnl": "pnl", "gross_pts": "pnl"}
    t = t.rename(columns={k: v for k, v in ren.items() if k in t.columns})
    if "entry_ts" not in t.columns or "side" not in t.columns:
        raise ValueError("la strategia deve restituire almeno le colonne entry_time e side")
    t["entry_ts"] = pd.to_datetime(t["entry_ts"], utc=True)
    if "exit_ts" in t.columns:
        t["exit_ts"] = pd.to_datetime(t["exit_ts"], utc=True)
    s = t["side"]
    if s.dtype == object or str(s.dtype).startswith(("str", "string")):
        s = s.astype(str).str.lower().map(lambda v: 1 if v in ("long", "buy", "1", "+1") else -1)
    t["side"] = np.sign(pd.to_numeric(s)).astype(int)
    return t.sort_values(["entry_ts", "side"], kind="stable").reset_index(drop=True)


def perturb(bars: pd.DataFrame, T: pd.Timestamp, seed: int, direction: int = 1) -> pd.DataFrame:
    b = bars.copy()
    idx = b.index
    after = np.asarray(idx > T)
    at = np.asarray(idx == T)
    n = int(after.sum())
    rng = np.random.default_rng(seed)
    step = float(np.nanmedian(np.abs(np.diff(b["close"].to_numpy(float))))) or 1e-4 * float(b["close"].abs().median())
    scale = 3 * step
    walk = np.cumsum(rng.normal(direction * scale, scale, n))
    cols = [c for c in PRICE_COLS if c in b.columns]
    for c in cols:
        v = b[c].to_numpy(float).copy()
        v[after] = v[after] + walk
        b[c] = v
    if at.any() and "close" in b.columns:
        jump = direction * scale * 5
        for c, f in (("close", 1.0), ("high", 1.0), ("low", 1.0)):
            if c in b.columns:
                v = b[c].to_numpy(float).copy()
                v[at] = v[at] + f * jump
                b[c] = v
        o = b["open"].to_numpy(float) if "open" in b.columns else b["close"].to_numpy(float)
        if "high" in b.columns:
            b["high"] = np.where(at, np.maximum.reduce([b["high"].to_numpy(float), o, b["close"].to_numpy(float)]),
                                 b["high"].to_numpy(float))
        if "low" in b.columns:
            b["low"] = np.where(at, np.minimum.reduce([b["low"].to_numpy(float), o, b["close"].to_numpy(float)]),
                                b["low"].to_numpy(float))
    if "volume" in b.columns:
        vol = b["volume"].to_numpy(float).copy()
        m = after | at
        vol[m] = np.round(vol[m] * rng.uniform(0.3, 3.0, int(m.sum())))
        b["volume"] = vol
    extra = [c for c in b.columns if c not in PRICE_COLS + ("volume",) and pd.api.types.is_numeric_dtype(b[c])]
    if n > 1:
        perm = rng.permutation(n)
        for c in extra:
            v = b[c].to_numpy().copy()
            v[after] = v[after][perm]
            b[c] = v
    return b


def _compare(base: pd.DataFrame, alt: pd.DataFrame, T: pd.Timestamp) -> str | None:
    b0 = base[base["entry_ts"] <= T]
    a0 = alt[alt["entry_ts"] <= T]
    if len(b0) != len(a0) or not (b0["entry_ts"].to_numpy() == a0["entry_ts"].to_numpy()).all() \
            or not (b0["side"].to_numpy() == a0["side"].to_numpy()).all():
        return f"i trade decisi entro T cambiano (originale {len(b0)}, con futuro alterato {len(a0)})"
    if "exit_ts" in b0.columns and "exit_ts" in a0.columns:
        closed = (b0["exit_ts"] <= T).to_numpy()
        if closed.any():
            if not (b0["exit_ts"].to_numpy()[closed] == a0["exit_ts"].to_numpy()[closed]).all():
                return "l'uscita di trade chiusi entro T cambia"
            if "pnl" in b0.columns and "pnl" in a0.columns and not np.allclose(
                    b0["pnl"].to_numpy(float)[closed], a0["pnl"].to_numpy(float)[closed], equal_nan=True):
                return "il risultato di trade chiusi entro T cambia"
    return None


def audit_lookahead(fn, bars: pd.DataFrame, n_random: int = 12, n_entries: int = 10, seed: int = 123,
                    cuts: list | None = None) -> dict:
    """Esegue l'audit. Restituisce {'ok': bool, 'problems': [...], 'n_cuts': int, 'n_runs': int}."""
    bars = bars.sort_index()
    base = normalize_trades(fn(bars.copy()))
    rng = np.random.default_rng(seed)
    idx = bars.index
    if cuts is None:
        lo, hi = int(len(idx) * 0.15), int(len(idx) * 0.95)
        pick = np.sort(rng.choice(np.arange(lo, max(lo + 1, hi)), size=min(n_random, max(1, hi - lo)), replace=False))
        cuts = [idx[i] for i in pick]
        if len(base):
            inner = base[(base["entry_ts"] > idx[lo]) & (base["entry_ts"] < idx[hi - 1])]
            if len(inner):
                sel = rng.choice(len(inner), size=min(n_entries, len(inner)), replace=False)
                cuts += list(inner["entry_ts"].iloc[np.sort(sel)])
    problems = []
    runs = 0
    for i, T in enumerate(cuts):
        T = pd.Timestamp(T)
        if T.tz is None:
            T = T.tz_localize("UTC")
        for direction in (1, -1):
            runs += 1
            pb = perturb(bars, T, seed=seed + 2 * i + (direction > 0), direction=direction)
            try:
                alt = normalize_trades(fn(pb))
            except Exception as ex:  # noqa: BLE001 - la strategia è codice del cliente
                problems.append({"T": str(T), "direction": direction,
                                 "problem": f"la strategia va in errore con il futuro alterato: {ex!r}",
                                 "trace": traceback.format_exc(limit=2)})
                continue
            msg = _compare(base, alt, T)
            if msg:
                problems.append({"T": str(T), "direction": direction, "problem": msg})
    return {"ok": not problems, "problems": problems, "n_cuts": len(cuts), "n_runs": runs,
            "n_trades": int(len(base))}


# --------------------------------------------------------------------------- controlli
def cheating_strategy(bars: pd.DataFrame, horizon: int = 10, every: int | None = None) -> pd.DataFrame:
    """Strategia che BARA apposta: entra all'apertura della barra i nella direzione della chiusura
    della barra i+horizon (che non può conoscere). Serve da controllo positivo."""
    n = len(bars)
    every = every or max(horizon + 1, n // 300)
    i = np.arange(horizon + 1, n - horizon - 1, every)
    c = bars["close"].to_numpy(float)
    o = bars["open"].to_numpy(float) if "open" in bars.columns else c
    side = np.where(c[i + horizon] > o[i], 1, -1)
    return pd.DataFrame({"entry_time": bars.index[i], "exit_time": bars.index[i + horizon],
                         "side": side, "pnl": side * (c[i + horizon] - o[i])})


def honest_strategy(bars: pd.DataFrame, horizon: int = 10, every: int | None = None) -> pd.DataFrame:
    """Controllo negativo: stessa struttura ma decide con le sole barre passate (momentum)."""
    n = len(bars)
    every = every or max(horizon + 1, n // 300)
    i = np.arange(horizon + 1, n - horizon - 1, every)
    c = bars["close"].to_numpy(float)
    o = bars["open"].to_numpy(float) if "open" in bars.columns else c
    side = np.where(c[i - 1] > c[i - 1 - horizon], 1, -1)
    return pd.DataFrame({"entry_time": bars.index[i], "exit_time": bars.index[i + horizon],
                         "side": side, "pnl": side * (c[i + horizon - 1] - o[i])})
