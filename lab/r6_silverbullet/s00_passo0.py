"""Passo 0 di r6_silverbullet (PREREG): copertura notturna e CONTEGGI di setup/ordini/fill. Nessun esito di trade."""
import math

import numpy as np
import pandas as pd

from lab import core

WINDOWS = {"03-04": 180, "10-11": 600, "14-15": 840}   # minuti NY dall'inizio del giorno solare
P_REF, TICK, LOOKBACK = 30400.0, core.TICK, 24


def ceil_tick(x: float) -> float:
    return math.ceil(x / TICK - 1e-9) * TICK


def bars5(bars: pd.DataFrame) -> pd.DataFrame:
    b = bars[["adj_open", "adj_high", "adj_low", "adj_close", "open"]]
    g = b.groupby(b.index.floor("5min"))
    out = pd.DataFrame({"o": g["adj_open"].first(), "h": g["adj_high"].max(), "l": g["adj_low"].min(),
                        "c": g["adj_close"].last(), "raw_o": g["open"].first()})
    out["ny"] = out.index.tz_convert(core.NY)
    return out


if __name__ == "__main__":
    bars, daily = core.load("discovery")
    d = daily[daily["valid"] & daily["in_phase"]]
    bars = bars[bars["session"].isin(d.index.values)]

    print("1. copertura Globex 02:30-03:59 ET (% di minuti con barra), per anno")
    m = bars["ny_min"].to_numpy()
    sel = bars[(m >= 150) & (m < 240)]
    cov = sel.groupby("session").size() / 90
    print(cov.reindex(d.index).fillna(0).groupby(d.index.year).mean().mul(100).round(1).to_string())

    B = bars5(bars)
    t5 = B.index
    o, h, l, c = (B[k].to_numpy() for k in ("o", "h", "l", "c"))
    ny = B["ny"]
    one = bars[["adj_high", "adj_low"]]
    rows = []
    for day in pd.DatetimeIndex(d.index):
        for w, wm in WINDOWS.items():
            wopen = (day + pd.Timedelta(minutes=wm)).tz_localize(core.NY)
            i0, iw, i1 = t5.searchsorted([wopen - pd.Timedelta(minutes=30), wopen, wopen + pd.Timedelta(minutes=60)])
            if i1 <= i0:
                continue
            win = np.arange(iw, i1)
            row = {"anno": day.year, "finestra": w, "finestra_ok": len(win) >= 4}
            if len(win) < 4:
                rows.append(row); continue
            sw = None
            for i in range(max(i0, LOOKBACK), i1):
                lo, hi = l[i - LOOKBACK:i].min(), h[i - LOOKBACK:i].max()
                if l[i] < lo and c[i] > lo:
                    sw = (i, +1, l[i]); break
                if h[i] > hi and c[i] < hi:
                    sw = (i, -1, h[i]); break
            row["sweep"] = sw is not None
            if sw is None:
                rows.append(row); continue
            si, bias, ext = sw
            P = B["raw_o"].iat[win[0]]
            gap_min, cap = max(TICK, ceil_tick(0.5 * P / P_REF)), 60 * P / P_REF
            fvg = None
            for k in range(max(si + 1, win[0], 2), i1):
                if bias > 0 and l[k] - h[k - 2] >= gap_min and c[k - 1] > o[k - 1]:
                    fvg = (k, l[k]); break
                if bias < 0 and l[k - 2] - h[k] >= gap_min and c[k - 1] < o[k - 1]:
                    fvg = (k, h[k]); break
            row["fvg"] = fvg is not None
            if fvg is None:
                rows.append(row); continue
            k, entry = fvg
            stop = ext - TICK if bias > 0 else ext + TICK
            row["lato_sbagliato"] = (stop >= entry) if bias > 0 else (stop <= entry)
            row["rischio_oltre_tetto"] = (not row["lato_sbagliato"]) and abs(entry - stop) > cap
            row["rischio_pt"] = abs(entry - stop)
            if row["lato_sbagliato"] or row["rischio_oltre_tetto"]:
                rows.append(row); continue
            row["ordine"] = True
            # fill: barre a 1 minuto dalla fine della candela c3 fino alla chiusura della finestra
            seg = one.loc[t5[k] + pd.Timedelta(minutes=5): t5[i1 - 1] + pd.Timedelta(minutes=4)]
            if bias > 0:
                row["fill_tocco"] = bool((seg.adj_low <= entry).any())
                row["fill_1tick"] = bool((seg.adj_low <= entry - TICK).any())
            else:
                row["fill_tocco"] = bool((seg.adj_high >= entry).any())
                row["fill_1tick"] = bool((seg.adj_high >= entry + TICK).any())
            rows.append(row)
    R = pd.DataFrame(rows)
    FLAGS = ["finestra_ok", "sweep", "fvg", "lato_sbagliato", "rischio_oltre_tetto", "ordine", "fill_tocco", "fill_1tick"]
    R[FLAGS] = R[FLAGS].fillna(False).astype(bool).astype(int)
    cnt = R.groupby(["anno", "finestra"])[["finestra_ok", "sweep", "fvg", "lato_sbagliato", "rischio_oltre_tetto",
                                           "ordine", "fill_tocco", "fill_1tick"]].sum().astype(int)
    print("\n2. conteggi per anno e finestra")
    print(cnt.to_string())
    print("\ntotale per finestra")
    print(cnt.groupby("finestra").sum().to_string())
    rp = R.loc[R["ordine"] == 1, "rischio_pt"]
    print("\nrischio (punti) degli ordini: mediana %.2f, 10%% %.2f, 90%% %.2f" % tuple(np.percentile(rp, [50, 10, 90])))
    core.record("r6_silverbullet", "passo0_counts", "Passo 0: conteggi setup/ordini/fill per finestra (nessun esito)",
                "discovery", {"per_finestra": cnt.groupby("finestra").sum().to_dict(orient="index")})
