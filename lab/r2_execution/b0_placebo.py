"""B0 - placebo: lato e istante casuali (seme fisso). Nessun segnale -> l'AGG lordo atteso e' ~0; la
domanda e' quanto costa/rende la sola esecuzione passiva (selezione avversa pura) e se il simulatore
e' ottimista. Se un placebo passivo risultasse profittevole, il simulatore sarebbe sospetto."""
import numpy as np

from lab.r2_execution.common import load, compare, summarize, xi_after

D, B = load()
rng = np.random.default_rng(7)
n = len(D.c)
sig60 = D.sig60


def placebo(win, p, seed):
    r = np.random.default_rng(seed)
    lo, hi = win
    m = D.m
    if lo < hi:
        ok = (m >= lo) & (m < hi)
    else:
        ok = (m >= lo) | (m < hi)
    ok &= np.isfinite(sig60) & (sig60 > 0)
    idx = np.nonzero(ok & (r.random(n) < p))[0]
    side = np.where(r.random(len(idx)) < 0.5, 1, -1)
    return idx, side


for wname, win in [("rth", (585, 900)), ("eth", (1200, 450))]:
    s, sd = placebo(win, 1 / 30, 11)
    for H in (15, 60):
        xi = xi_after(D, s, H)
        for oname, off in [("0", 0.0), ("2t", 0.5), ("s5h", 0.5 * sig60[s] * np.sqrt(5))]:
            for N in (5, 15):
                if N > H:
                    continue
                t = compare(D, B, s, sd, xi, off, N)
                summarize(t, f"B0_{wname}_H{H}_off{oname}_N{N}",
                          f"placebo lato casuale {wname}, uscita a tempo {H}m, limite off={oname}, attesa {N}m")
