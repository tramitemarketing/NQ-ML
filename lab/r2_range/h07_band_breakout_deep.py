"""Approfondimento (post hoc, dichiarato) della rottura della banda chiusura-di-ieri +/- h*R_hat (da h04).

In h04 la sola combinazione con p < 0,01 era: ancora = close RTH di ieri, h = 0,75, rottura, uscita 15:59
(stop 0,1 e 0,2 R). Qui, griglia di sensibilita' dichiarata PRIMA di guardarla:
  h in {0.5, 0.6, 0.75, 0.9, 1.0, 1.25}; stop in {0.1, 0.2, 0.3, nessuno}; fine finestra in {14:00, 15:00}.
Controlli sul punto h=0.75, stop 0.2, finestra 15:00: diagnostica completa (anni, drop20, beta),
specchio (fade con stessa geometria), placebo con R_naive e con R_hat rimescolato (5 semi),
split per regime di R_hat (terzili causali R_pct), split meta' long/short, netto in R_hat.
"""
import itertools

import numpy as np
import pandas as pd

from lab.r2_range import common as C
from lab.r2_range.h04_bands import touches


def run(M, R, h, rule, stop, m_hi=900, anchor="pc"):
    si, m, d = touches(M, R, anchor, h, m_hi=m_hi)
    side = -d if rule == "fade" else d
    Rh = M["R_hat"][si]
    return C.sim(M, si, m, side, (stop * Rh if stop else None), None, None)


if __name__ == "__main__":
    bars, daily, M, F = C.setup_discovery()
    rows = []
    for h, stop, mh in itertools.product([0.5, 0.6, 0.75, 0.9, 1.0, 1.25], [0.1, 0.2, 0.3, None], [840, 900]):
        t = run(M, M["R_hat"], h, "brk", stop, mh)
        st = C.evaluate(t, full=True)
        tid = f"h07_pc_brk_h{h}_s{stop}_w{mh}"
        C.rec(tid, f"rottura banda close ieri +/- {h}R_hat, primo tocco 09:45-{mh//60}:00, stop {stop}R, uscita 15:59", st)
        rows.append(dict(h=h, stop=stop, win=mh, n=st["n"], net=st["mean"], p=st["p_pos"], gR=st["gross_R"],
                         yrs=st["years_pos"], d20=st["drop20"], long=st["long_share"]))
    pd.set_option("display.width", 220)
    print(pd.DataFrame(rows).to_string())

    t = run(M, M["R_hat"], 0.75, "brk", 0.2)
    st = C.evaluate(t, bars, M)
    print("PUNTO", C.fmt(st), st["yearly"])
    C.rec("h07_point_full", "rottura banda pc +/- 0.75R, stop 0.2R, 09:45-15:00 -> 15:59: diagnostica completa", st)
    print(t["how"].value_counts().to_dict())
    for sd in (1, -1):
        tt = t[t["side"] == sd]
        s2 = C.evaluate(tt, full=True); print("lato", sd, C.fmt(s2))
        C.rec(f"h07_point_side{sd}", f"punto h07, solo lato {sd}", s2)
    for lo, hi in ((0, 1 / 3), (1 / 3, 2 / 3), (2 / 3, 1.01)):
        rp = M["R_pct"][t["si"].to_numpy()]
        tt = t[(rp >= lo) & (rp < hi)]
        s2 = C.evaluate(tt, full=True); print("regime", round(lo, 2), C.fmt(s2), s2.get("yearly"))
        C.rec(f"h07_point_regime{lo:.2f}", f"punto h07, terzile di regime R_pct [{lo:.2f},{hi:.2f})", s2)
    t2 = run(M, M["R_hat"], 0.75, "fade", 0.2)
    s2 = C.evaluate(t2, full=True); print("SPECCHIO fade", C.fmt(s2))
    C.rec("h07_point_mirror", "punto h07 specchio (fade, stop 0.2R)", s2)
    t2 = run(M, M["R_naive"], 0.75, "brk", 0.2)
    s2 = C.evaluate(t2, full=True); print("NAIVE", C.fmt(s2))
    C.rec("h07_point_naive", "punto h07 con R_naive (media20) per bande e stop", s2)
    yrs = M["sess"].year.to_numpy()
    for seed in range(5):
        rng = np.random.default_rng(seed)
        Rs = M["R_hat"].copy()
        for y in np.unique(yrs):
            ii = np.where((yrs == y) & np.isfinite(Rs))[0]
            Rs[ii] = Rs[rng.permutation(ii)]
        t2 = run(M, Rs, 0.75, "brk", 0.2)
        s2 = C.evaluate(t2, full=False); print("SHUFFLE", seed, C.fmt(s2))
        C.rec(f"h07_point_shuffle{seed}", f"punto h07 con R_hat rimescolato nell'anno, seme {seed}", s2)
