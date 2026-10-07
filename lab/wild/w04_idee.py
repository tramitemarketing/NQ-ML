"""IDEE SELVAGGE, giro 4 (direzioni dichiarate qui prima di guardare).

W20 resistenza ai tondi (Osler 2000: gli ordini limite si ammassano sui numeri tondi e fermano i
    trend): alle 11:30, se il massimo (minimo) della mattina, prezzo grezzo, e' entro 1 tick da un
    multiplo di 25 e il prezzo e' entro 0,1 % da quell'estremo -> CONTRO (short sotto il massimo, long
    sopra il minimo) fino alle 12:30 / 16:00. Controllo: stessa regola con estremi NON su multipli di 25.
W21 Hurst R/S (rendimenti 5 min delle 20 sessioni precedenti): H > quantile 2/3 mobile -> segui la
    prima ora (10:30->16:00); H < quantile 1/3 -> vai contro.
"""
from __future__ import annotations

import numpy as np

from lab.wild import common as C
from lab.wild import features as F
from lab.wild.w01_idee import ev, OUT
import pandas as pd


def hurst_rs(x):
    x = x[np.isfinite(x)]
    n = len(x)
    sizes = [s for s in (8, 16, 32, 64, 128, 256) if s <= n // 2]
    rs = []
    for s in sizes:
        m = n // s
        blk = x[: m * s].reshape(m, s)
        z = np.cumsum(blk - blk.mean(1, keepdims=True), 1)
        R = z.max(1) - z.min(1); Sd = blk.std(1)
        ok = Sd > 0
        rs.append(np.mean(R[ok] / Sd[ok]))
    return np.polyfit(np.log(sizes), np.log(rs), 1)[0]


def main():
    g = C.grid()
    P = g["P"]; S = len(g["sess"]); allS = np.arange(S)
    # ---------------- W20
    hi = P[:, :121].max(1); lo = P[:, :121].min(1); x = P[:, 120]
    on25 = lambda v: np.abs(v - np.round(v / 25) * 25) <= 0.25
    near_hi = (hi - x) <= 0.001 * x; near_lo = (x - lo) <= 0.001 * x
    for kout, nm in ((180, "h60"), (390, "close")):
        side = np.where(near_hi & on25(hi) & ~near_lo, -1.0, np.where(near_lo & on25(lo) & ~near_hi, 1.0, 0.0))
        ev(f"W20_round_extreme_fade_{nm}", f"estremo della mattina su multiplo di 25 e prezzo vicino: contro, "
           f"11:30->{nm}", allS, np.full(S, 120), np.full(S, kout), side)
        side_c = np.where(near_hi & ~on25(hi) & ~near_lo, -1.0, np.where(near_lo & ~on25(lo) & ~near_hi, 1.0, 0.0))
        ev(f"W20c_nonround_extreme_fade_{nm}", f"controllo: estremo NON su multiplo di 25, contro, 11:30->{nm}",
           allS, np.full(S, 120), np.full(S, kout), side_c)
    # ---------------- W21
    r5 = np.diff(P[:, ::5], axis=1)                 # 78 rendimenti 5 min per sessione
    H = np.full(S, np.nan)
    for s in range(20, S):
        H[s] = hurst_rs(r5[s - 20:s].ravel())
    hh, hl = F.roll_q(H, 2 / 3), F.roll_q(H, 1 / 3)
    fh = np.sign(P[:, 60] - P[:, 0])
    ev("W21_hurst_regime_close", "Hurst R/S 20 sessioni prec.: alto -> segui la prima ora, basso -> contro; "
       "10:30->16:00", allS, np.full(S, 60), np.full(S, 390), np.where(H > hh, fh, np.where(H < hl, -fh, 0)))
    ev("W21_hurst_high_follow_close", "solo Hurst alto: segui la prima ora 10:30->16:00",
       allS, np.full(S, 60), np.full(S, 390), np.where(H > hh, fh, 0))
    ev("W21_hurst_low_fade_close", "solo Hurst basso: contro la prima ora 10:30->16:00",
       allS, np.full(S, 60), np.full(S, 390), np.where(H < hl, -fh, 0))
    print("Hurst medio", np.nanmean(H), np.nanpercentile(H, [10, 50, 90]))
    pd.DataFrame(OUT).to_csv(C.__file__.replace("common.py", "wild_results_4.csv"), index=False)


if __name__ == "__main__":
    main()
