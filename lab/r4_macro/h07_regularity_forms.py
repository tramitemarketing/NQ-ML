"""Sensibilita' della forma giornaliera (righe non sovrapposte, adatte al bootstrap per giorno del controller):
 R1 = -segno(d{L}_10y) x ret open->open 1g in bp, per L = 20, 30, 40, 60 (superficie, non selezione nuova);
 R2 = -clip(d40/(sd250*sqrt40), -2, 2) x ret 1g in bp (segnale continuo);
 R3 = come R1 (L=40) ma solo la parte RTH (open->close) e solo la parte notturna (close->open successivo)."""
import numpy as np
import pandas as pd
from lab import core
from lab.r4_macro import common as C

if __name__ == "__main__":
    d, bars, daily = C.load()
    k = C.ext_known(d.index)["DGS10"]
    d = d[d["O"].notna()].copy()
    r1 = (d["O"].shift(-1) - d["O"]) / d["Oraw"] * 1e4
    rth = (d["rth_close"] - d["O"]) / d["Oraw"] * 1e4
    night = (d["O"].shift(-1) - d["rth_close"]) / d["Oraw"] * 1e4

    def go(tid, desc, g):
        g = g.dropna()
        st = core.day_block_bootstrap(g.to_numpy(), g.index.to_numpy())
        yy = g.groupby(g.index.year).mean()
        out = dict(**st, years_pos=f"{int((yy > 0).sum())}/{len(yy)}")
        core.record(C.FAM, tid, desc, "discovery", out, years={int(a): round(float(b), 2) for a, b in yy.items()})
        print(tid, round(st["mean"], 2), [round(st["lo"], 2), round(st["hi"], 2)], st["p_two"], out["years_pos"], yy.round(1).to_dict())

    for L in (20, 30, 40, 60):
        s = -np.sign((k - k.shift(L)).reindex(d.index))
        go(f"R1_L{L}", f"-segno(d{L}_10y) x ret open->open 1g (bp)", s * r1)
    d40 = (k - k.shift(40)).reindex(d.index)
    sd = (k - k.shift(1)).rolling(250).std().reindex(d.index)
    z = (d40 / (sd * np.sqrt(40))).clip(-2, 2)
    go("R2_z40", "-clip(z d40,-2,2) x ret 1g (bp)", -z * r1)
    s40 = -np.sign(d40)
    go("R3a_L40_rth", "-segno(d40_10y) x ret RTH open->close (bp)", s40 * rth)
    go("R3b_L40_night", "-segno(d40_10y) x ret close RTH->open RTH successivo (bp)", s40 * night)
