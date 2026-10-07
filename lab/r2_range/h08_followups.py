"""Approfondimenti post hoc (dichiarati) di due segnali deboli visti in h02 e h03.

(b) da h02: il fade dell'estremo con bilancio alto PERDE -> provo lo specchio: continuazione dall'estremo.
    Checkpoint T in {13:30, 14:00, 14:30, 15:00}; posizione nel range pos >= p0 (long) o <= 1-p0 (short),
    p0 in {0.8, 0.9}; bilancio u_T >= u0, u0 in {0.6, 0.8, 1.0} (controllo: u_T < u0); ingresso all'open di T,
    uscita 15:59, stop in {0.15 R, nessuno}. Diagnostica completa sul punto T=14:30, p0=0.9, u0=0.8, stop 0.15.
    Parentela dichiarata: e' la stessa famiglia del momentum di fine giornata del giro 1 (hivol_last30).
(c) da h03: fade del gap grande in unita' di R_hat. g in {0.4, 0.5, 0.6, 0.75}, uscita in {10:30, 11:00, 12:00,
    13:00}; diagnostica sul punto g=0.5, 12:00. I gap in punti/ATR erano gia' falliti nel giro 1.
"""
import itertools

import numpy as np
import pandas as pd

from lab.r2_range import common as C


def extreme_cont(M, T, p0, u0, grp="high"):
    j = T - C.M0 - 1
    rr = M["runH"][:, j] - M["runL"][:, j]
    u = rr / M["R_hat"]
    pos = (M["adj_close"][:, j] - M["runL"][:, j]) / np.where(rr > 0, rr, np.nan)
    side = np.where(pos >= p0, 1, np.where(pos <= 1 - p0, -1, 0))
    cond = (u >= u0) if grp == "high" else (u < u0)
    sel = M["ok"] & cond & (side != 0)
    si = np.where(sel)[0]
    return si, side[si]


if __name__ == "__main__":
    bars, daily, M, F = C.setup_discovery()
    pd.set_option("display.width", 220)
    rows = []
    for T, p0, u0, grp, stop in itertools.product((810, 840, 870, 900), (0.8, 0.9), (0.6, 0.8, 1.0), ("high", "low"), (0.15, None)):
        si, side = extreme_cont(M, T, p0, u0, grp)
        t = C.sim(M, si, np.full(len(si), T), side, (stop * M["R_hat"][si] if stop else None))
        st = C.evaluate(t, full=True)
        tid = f"h08b_T{T}_p{p0}_u{u0}_{grp}_s{stop}"
        C.rec(tid, f"continuazione dall'estremo alle {T//60}:{T%60:02d}, pos>={p0}, u {'>=' if grp=='high' else '<'} {u0}, stop {stop}R, uscita 15:59", st)
        rows.append(dict(T=T, p0=p0, u0=u0, grp=grp, stop=stop, n=st["n"], net=st["mean"], p=st["p_pos"],
                         gR=st["gross_R"], yrs=st["years_pos"], d20=st["drop20"]))
    df = pd.DataFrame(rows)
    print(df.to_string())
    print(df.groupby(["grp", "u0"])[["net", "gR"]].mean())
    si, side = extreme_cont(M, 870, 0.9, 0.8)
    t = C.sim(M, si, np.full(len(si), 870), side, 0.15 * M["R_hat"][si])
    st = C.evaluate(t, bars, M); print("PUNTO b", C.fmt(st), st["yearly"])
    C.rec("h08b_point_full", "continuazione estremo 14:30, pos>=0.9, u>=0.8, stop 0.15R: diagnostica completa", st)

    rows = []
    O = M["adj_open"][:, 0]
    z = (O - M["prev_close"]) / M["R_hat"]
    for g, T in itertools.product((0.4, 0.5, 0.6, 0.75), (630, 660, 720, 780)):
        si = np.where(M["ok"] & np.isfinite(z) & (np.abs(z) > g))[0]
        t = C.sim(M, si, np.full(len(si), 571), -np.sign(z[si]).astype(int), m_out=np.full(len(si), T))
        st = C.evaluate(t, full=True)
        C.rec(f"h08c_gapfade_g{g}_T{T}", f"fade del gap |z_pc|>{g} R_hat da 09:31 a {T//60}:{T%60:02d}", st)
        rows.append(dict(g=g, T=T, n=st["n"], net=st["mean"], p=st["p_pos"], gR=st["gross_R"], yrs=st["years_pos"],
                         d20=st["drop20"], long=st["long_share"]))
    print(pd.DataFrame(rows).to_string())
    si = np.where(M["ok"] & np.isfinite(z) & (np.abs(z) > 0.5))[0]
    t = C.sim(M, si, np.full(len(si), 571), -np.sign(z[si]).astype(int), m_out=np.full(len(si), 720))
    st = C.evaluate(t, bars, M); print("PUNTO c", C.fmt(st), st["yearly"])
    C.rec("h08c_point_full", "fade gap |z_pc|>0.5 09:31->12:00: diagnostica completa", st)
