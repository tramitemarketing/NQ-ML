"""H03: comportamento intraday condizionato alla vol implicita (regimi noti all'apertura).
Unita': punti NQ netti (0,75) per 1 contratto, piu' il lordo in % del grezzo come diagnostica.
Regimi (pct rank causale 250): VRP_har alto/basso (quintili), VXN alto/basso, VIX9D/VIX alto/basso.
Regole (lato deciso con informazione nota all'ingresso):
  gapfade   : lato = -segno(gap), 09:30 -> 16:00
  gapfade60 : lato = -segno(gap), 09:30 -> 10:30
  fh_cont   : lato = segno(10:30 - 09:30), 10:30 -> 16:00
  last30    : lato = segno(15:30 - 09:30), 15:30 -> 16:00
  rthlong   : long 09:30 -> 16:00 (eccesso = meno la media RTH di tutto il campione)
  nightlong : long 16:00 -> 09:30 successivo (adj), eccesso idem
  biggap_fade: |gap| > 0.5 * sigma implicita giornaliera (VXN/sqrt(252) * prezzo), lato -segno(gap), 09:30->16:00
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from lab import core
from lab.r4_implied import common as C


def price_at(bars, minute, col="adj_open"):
    b = bars[bars["ny_min"] == minute]
    return b.groupby("session")[col].first()


def main():
    f = C.load_features()
    bars = C._CACHE["bars"]
    idx = f.index
    p0930 = f["rth_open"]
    p1030 = price_at(bars, 630).reindex(idx)
    p1530 = price_at(bars, 930).reindex(idx)
    pclose = f["rth_close"]
    gap = f["gap_pts"]
    sig_imp = f["VXN"] / 100 / np.sqrt(252) * f["raw_open"]     # sigma implicita giornaliera in punti
    rules = {
        "gapfade": (-np.sign(gap), pclose - p0930),
        "gapfade60": (-np.sign(gap), p1030 - p0930),
        "fh_cont": (np.sign(p1030 - p0930), pclose - p1030),
        "last30": (np.sign(p1530 - p0930), pclose - p1530),
        "rthlong": (pd.Series(1.0, index=idx), pclose - p0930),
        "nightlong": (pd.Series(1.0, index=idx), f["night_next_pts"]),
    }
    regimes = {}
    for s in ["vrp_har_s", "vxn_s", "ts_9d_s"]:
        rk = C.prank(f[s])
        regimes[f"{s}_top"] = rk >= 0.8
        regimes[f"{s}_bot"] = rk <= 0.2
    regimes["all"] = pd.Series(True, index=idx)
    for rn, (side, move) in rules.items():
        gross = side * move
        if rn in ("rthlong", "nightlong"):
            gross = gross - gross.mean()                     # eccesso sulla deriva
        for gn, g in regimes.items():
            m = g & gross.notna() & (side != 0)
            v = gross[m]
            net = v - (0 if rn in ("rthlong", "nightlong") else core.COST_RT_POINTS)
            tid = f"H03_{rn}_{gn}"
            st = C.rec(tid, f"intraday {rn} nel regime {gn}; punti {'eccesso lordo' if rn in ('rthlong','nightlong') else 'netti'}",
                       net.to_numpy(), v.index.values, rule=rn, regime=gn,
                       gross_pct=float((v / f['raw_open'][m] * 100).mean()))
            print(C.fmt(tid, st))
    # gap grande rispetto all'implicita
    for k in (0.25, 0.5, 1.0):
        m = (gap.abs() > k * sig_imp) & gap.notna()
        v = (-np.sign(gap) * (pclose - p0930))[m]
        net = v - core.COST_RT_POINTS
        tid = f"H03_biggap_fade_k{k}"
        st = C.rec(tid, f"fade del gap > {k} sigma implicita giornaliera, 09:30->16:00, punti netti", net.to_numpy(), v.index.values, k=k)
        print(C.fmt(tid, st))
        v2 = (np.sign(gap) * (p1030 - p0930))[m] - core.COST_RT_POINTS
        tid = f"H03_biggap_cont60_k{k}"
        st = C.rec(tid, f"prosecuzione del gap > {k} sigma implicita, 09:30->10:30, punti netti", v2.to_numpy(), v2.index.values, k=k)
        print(C.fmt(tid, st))


if __name__ == "__main__":
    main()
