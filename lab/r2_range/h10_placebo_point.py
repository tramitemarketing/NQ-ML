"""Placebo sul punto scelto (h=0.9, stop 0.2R): R_hat rimescolato nell'anno (10 semi), R_naive, ancora = open RTH
invece della chiusura di ieri, specchio (fade stessa geometria). Registrati tutti."""
import numpy as np

from lab.r2_range import common as C
from lab.r2_range.h04_bands import touches


def run(M, R, anchor="pc", flip=1, h=0.9, stop=0.2):
    si, m, d = touches(M, R, anchor, h)
    return C.sim(M, si, m, flip * d, stop * M["R_hat"][si])


if __name__ == "__main__":
    bars, daily, M, F = C.setup_discovery()
    yrs = M["sess"].year.to_numpy()
    res = []
    for seed in range(10):
        rng = np.random.default_rng(100 + seed)
        Rs = M["R_hat"].copy()
        for y in np.unique(yrs):
            ii = np.where((yrs == y) & np.isfinite(Rs))[0]
            Rs[ii] = Rs[rng.permutation(ii)]
        st = C.evaluate(run(M, Rs), full=False)
        C.rec(f"h10_shuffle{seed}", f"punto h=0.9 con R_hat rimescolato nell'anno, seme {100+seed}", st)
        res.append(st["mean"]); print("shuffle", seed, C.fmt(st))
    print("media placebo rimescolati", np.mean(res), "quanti >= 3.11:", int(np.sum(np.array(res) >= 3.112)))
    for tag, t in (("naive", run(M, M["R_naive"])), ("open", run(M, M["R_hat"], "open")), ("specchio", run(M, M["R_hat"], flip=-1))):
        st = C.evaluate(t, full=True); print(tag, C.fmt(st))
        C.rec(f"h10_{tag}", f"punto h=0.9 stop 0.2R variante {tag}", st)
