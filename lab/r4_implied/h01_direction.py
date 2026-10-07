"""H01: i segnali di implicita predicono la DIREZIONE di NQ? (ricerca, unita' % del grezzo, eccesso sulla deriva)
Per ogni segnale s (noto all'apertura RTH di S) e orizzonte h in {1,5,20} sessioni (open->open):
  lin  : pos = 2*(pct_rank_250(s)-0.5) in [-1,1]           (timing lineare, ~neutrale al beta)
  top  : pos = 1 se rank >= 0.8 (long nei giorni di segnale alto), P&L con rendimento demeanato (eccesso)
  bot  : pos = 1 se rank <= 0.2, idem
P&L giornaliero a portafogli sovrapposti; righe solo nei giorni con posizione != 0.
Segno atteso dichiarato prima: VRP/VXN alti -> rendimenti futuri piu' alti (premio al rischio); gli altri bilaterali."""
from __future__ import annotations

import numpy as np
import pandas as pd

from lab.r4_implied import common as C

SIGNALS = ["vrp_har_s", "vrp_rv22_s", "vrp_rv5_s", "vrp_lvl_s", "vxn_s", "ts_3m_s", "ts_9d_s", "vvix_s", "vvix_vix_s",
           "skew_s", "vxn_vix_s", "dvxn1_s", "dvxn5_s", "vxn_dev20_s"]


def main():
    f = C.load_features()
    r = f["oo1_pct"]
    rx = r - r.mean()
    out = []
    for s in SIGNALS:
        rk = C.prank(f[s])
        ok = rk.notna()
        for h in (1, 5, 20):
            for kind in ("lin", "top", "bot"):
                if kind == "lin":
                    pos = 2 * (rk - 0.5)
                elif kind == "top":
                    pos = (rk >= 0.8).astype(float).where(ok)
                else:
                    pos = (rk <= 0.2).astype(float).where(ok)
                pnl = C.overlap_pnl(pos, rx, h)
                held = C.overlap_pnl(pos, pd.Series(1.0, index=f.index), h)
                m = (held.abs() > 1e-12) & rx.notna()
                v = (pnl / held.abs().where(m)) if kind != "lin" else pnl
                v = v[m]
                tid = f"H01_{s}_{kind}_h{h}"
                st = C.rec(tid, f"direzione: {s} {kind} orizzonte {h}g open->open, eccesso sulla deriva (% grezzo)",
                           v.to_numpy(), v.index.values, signal=s, kind=kind, h=h)
                print(C.fmt(tid, st))
                out.append((tid, st["mean"], st["p_two"], st["years_pos"], st["drop_top20"]))
    o = pd.DataFrame(out, columns=["id", "mean", "p2", "yrs", "dt20"]).sort_values("p2")
    print("\n--- piu' significativi ---")
    print(o.head(20).to_string())
    print("n test con p2<0.05:", (o.p2 < 0.05).sum(), "su", len(o))


if __name__ == "__main__":
    main()
