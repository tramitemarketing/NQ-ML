"""H08: reversal di breve condizionato all'implicita (Nagel 2012: i profitti del reversal crescono col VIX,
fornitura di liquidita' quando e' scarsa). Punti netti, 1 contratto, ingresso all'apertura RTH di S.
  rev_oo  : lato = -segno(rendimento close->close RTH di S-1), open S -> open S+1 (attraversa la notte: beta!)
  rev_rth : idem ma open S -> close S (solo RTH)
  shock   : rendimento RTH di S-1 < -k*sigma_imp(S-1) -> long; > +k -> short (k=1, 1.5), open S -> close S e 5 giorni
Regimi: tutti, VXN top/bot quintile, VRP top quintile."""
from __future__ import annotations

import numpy as np
import pandas as pd

from lab import core
from lab.r4_implied import common as C


def main():
    f = C.load_features()
    cc = f["rth_close"] - f["rth_close"].shift(1)
    side = -np.sign(cc.shift(0))         # rendimento di S-1 (close S-2 -> close S-1) e' cc.shift(1) visto da S
    side = -np.sign(cc.shift(1))
    oo = f["oo1_pts"]
    rth = f["rth_close"] - f["rth_open"]
    drift_oo = oo.mean(); drift_rth = rth.mean()
    regimes = {"all": pd.Series(True, index=f.index)}
    for s in ("vxn_s", "vrp_har_s"):
        rk = C.prank(f[s])
        regimes[f"{s}_top"] = rk >= 0.8
        regimes[f"{s}_bot"] = rk <= 0.2
    for nm, mv, dr in (("rev_oo", oo, drift_oo), ("rev_rth", rth, drift_rth)):
        for gn, g in regimes.items():
            m = g & mv.notna() & side.notna() & (side != 0)
            net = side[m] * mv[m] - core.COST_RT_POINTS
            beta = side[m] * dr
            tid = f"H08_{nm}_{gn}"
            st = C.rec(tid, f"reversal 1g {nm} nel regime {gn}; punti netti", net.to_numpy(), net.index.values,
                       long_share=float((side[m] > 0).mean()), beta_adj_mean=float((net - beta).mean()))
            print(C.fmt(tid, st), f"long={float((side[m]>0).mean()):.2f} netto-beta={float((net-beta).mean()):+.2f}")
    # shock rispetto alla sigma implicita del giorno dello shock
    rprev = (f["rth_close"] - f["rth_open"]).shift(1)
    sig_prev = (f["VXN"] / 100 / np.sqrt(252) * f["raw_open"]).shift(1)
    o = f["rth_open"]
    oo5 = o.shift(-5) - o
    for k in (1.0, 1.5):
        sd = pd.Series(0.0, index=f.index)
        sd[rprev < -k * sig_prev] = 1.0
        sd[rprev > k * sig_prev] = -1.0
        for hn, mv, dr in (("rth", rth, drift_rth), ("oo5", oo5, oo5.mean())):
            m = (sd != 0) & mv.notna()
            net = sd[m] * mv[m] - core.COST_RT_POINTS
            beta = sd[m] * dr
            tid = f"H08_shock_k{k}_{hn}"
            st = C.rec(tid, f"contro-shock: RTH di ieri oltre {k} sigma implicita -> lato opposto, {hn}; punti netti (5g sovrapposti per evento)",
                       net.to_numpy(), net.index.values, k=k, long_share=float((sd[m] > 0).mean()),
                       beta_adj_mean=float((net - beta).mean()))
            print(C.fmt(tid, st), f"long={float((sd[m]>0).mean()):.2f} netto-beta={float((net-beta).mean()):+.2f}")


if __name__ == "__main__":
    main()
