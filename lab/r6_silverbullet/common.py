"""ICT Silver Bullet, specifica del repo cjosh4toyotas-stack/silver-bullet-backtest v1.1 con le deviazioni del
PREREG (soglie scalate col prezzo, fill a 1 minuto con attraversamento di 1 tick). Vedi PREREG.md."""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

from lab import core

WINDOWS = {"03-04": 180, "10-11": 600, "14-15": 840}
P_REF, TICK, LOOKBACK = 30400.0, core.TICK, 24
HOLD_MIN = 120


def ceil_tick(x: float) -> float:
    return math.ceil(x / TICK - 1e-9) * TICK


class Data:
    def __init__(self, bars: pd.DataFrame, daily: pd.DataFrame):
        d = daily[daily["valid"] & daily["in_phase"]]
        self.sessions = pd.DatetimeIndex(d.index)
        b = bars[bars["session"].isin(d.index.values)]
        self.bars = b
        self.t1 = b.index
        self.o1, self.h1, self.l1, self.c1 = (b[k].to_numpy() for k in ("adj_open", "adj_high", "adj_low", "adj_close"))
        self.raw1 = b["close"].to_numpy()
        self.sess1 = b["session"].to_numpy()
        g = b[["adj_open", "adj_high", "adj_low", "adj_close", "open"]].groupby(b.index.floor("5min"))
        B = pd.DataFrame({"o": g["adj_open"].first(), "h": g["adj_high"].max(), "l": g["adj_low"].min(),
                          "c": g["adj_close"].last(), "raw_o": g["open"].first()})
        self.t5 = B.index
        self.o5, self.h5, self.l5, self.c5, self.raw5 = (B[k].to_numpy() for k in ("o", "h", "l", "c", "raw_o"))

    def i1(self, ts) -> int:
        return int(self.t1.searchsorted(ts))


def orders(D: Data, fixed_thresholds: bool = False, fill_touch: bool = False, windows=None) -> pd.DataFrame:
    """Un ordine (al massimo) per sessione e finestra; colonna fill_i = indice 1m del fill (-1 se non eseguito)."""
    o, h, l, c = D.o5, D.h5, D.l5, D.c5
    t5 = D.t5
    rows = []
    for day in D.sessions:
        for w, wm in (windows or WINDOWS).items():
            wopen = (day + pd.Timedelta(minutes=wm)).tz_localize(core.NY)
            wclose = wopen + pd.Timedelta(minutes=60)
            i0, iw, i1 = t5.searchsorted([wopen - pd.Timedelta(minutes=30), wopen, wclose])
            if i1 - iw < 4:
                continue
            sw = None
            for i in range(max(i0, LOOKBACK), i1):
                lo, hi = l[i - LOOKBACK:i].min(), h[i - LOOKBACK:i].max()
                if l[i] < lo and c[i] > lo:
                    sw = (i, +1, l[i]); break
                if h[i] > hi and c[i] < hi:
                    sw = (i, -1, h[i]); break
            if sw is None:
                continue
            si, bias, ext = sw
            P = D.raw5[iw]
            if fixed_thresholds:
                gap_min, cap = 0.5, 60.0
            else:
                gap_min, cap = max(TICK, ceil_tick(0.5 * P / P_REF)), 60 * P / P_REF
            fvg = None
            for k in range(max(si + 1, iw, 2), i1):
                if bias > 0 and l[k] - h[k - 2] >= gap_min and c[k - 1] > o[k - 1]:
                    fvg = (k, l[k]); break
                if bias < 0 and l[k - 2] - h[k] >= gap_min and c[k - 1] < o[k - 1]:
                    fvg = (k, h[k]); break
            if fvg is None:
                continue
            k, entry = fvg
            stop = ext - TICK if bias > 0 else ext + TICK
            if (bias > 0 and stop >= entry) or (bias < 0 and stop <= entry):
                continue
            risk = abs(entry - stop)
            if risk > cap:
                continue
            a, b = D.i1(t5[k] + pd.Timedelta(minutes=5)), D.i1(wclose)
            thr = 0.0 if fill_touch else TICK
            if bias > 0:
                hit = np.nonzero(D.l1[a:b] <= entry - thr)[0]
            else:
                hit = np.nonzero(D.h1[a:b] >= entry + thr)[0]
            if len(hit) == 0:
                continue
            rows.append({"session": day, "window": w, "bias": bias, "entry": entry, "stop": stop, "risk": risk,
                         "fill_i": a + int(hit[0]), "raw_px": D.raw1[a + int(hit[0])]})
    return pd.DataFrame(rows)


def horizon_px(D: Data, i: int, minutes: int) -> tuple[float, int]:
    """Close dell'ultima barra 1m che inizia entro fill_start + minutes - 1 (stessa sessione)."""
    j = int(D.t1.searchsorted(D.t1[i] + pd.Timedelta(minutes=minutes - 1), side="right")) - 1
    while D.sess1[j] != D.sess1[i]:
        j -= 1
    return D.c1[j], j


def manage(D: Data, i: int, side: int, entry: float, stop: float, target: float) -> tuple[float, int, str]:
    """Gestione a 1 minuto dal minuto del fill: nel minuto del fill conta solo lo stop; poi stop prima del
    target; target con attraversamento di 1 tick; uscita a tempo dopo HOLD_MIN minuti al close."""
    _, jend = horizon_px(D, i, HOLD_MIN)
    for j in range(i, jend + 1):
        if (side > 0 and D.l1[j] <= stop) or (side < 0 and D.h1[j] >= stop):
            return stop, j, "stop"
        if j > i and ((side > 0 and D.h1[j] >= target + TICK) or (side < 0 and D.l1[j] <= target - TICK)):
            return target, j, "target"
    return D.c1[jend], jend, "time"


def trades(D: Data, od: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for r in od.itertuples():
        tgt = r.entry + 2 * r.risk * r.bias
        px, j, why = manage(D, r.fill_i, r.bias, r.entry, r.stop, tgt)
        row = {"session": r.session, "window": r.window, "entry_ts": D.t1[r.fill_i], "exit_ts": D.t1[j],
               "side": r.bias, "gross_pts": (px - r.entry) * r.bias, "risk": r.risk, "why": why,
               "raw_px": r.raw_px}
        for H in (15, 30, 60, 120):
            p, _ = horizon_px(D, r.fill_i, H)
            row[f"a{H}_pts"] = (p - r.entry) * r.bias
        rows.append(row)
    return pd.DataFrame(rows)
