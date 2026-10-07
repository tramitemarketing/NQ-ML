"""H36 calamita dei numeri tondi (prezzi grezzi): alla chiusura di una barra RTH (09:35-15:00) con il
livello tondo piu' vicino (multiplo di 100, oppure 50) a distanza d in (1 tick, 0,05*ADR20] e NON
ancora toccato nella sessione, si entra VERSO il livello; target = il livello (trade-through), stop =
stessa distanza dal lato opposto, limite 30m. Placebo: livelli spostati di +23 / +37 punti.
H39 esaurimento: 3 barre 1m RTH grandi (|corpo| >= 1.5 sigma60) nello stesso verso con volume
decrescente -> fade, uscita 30m."""
import numpy as np
from numba import njit
from lab.micro.common import Data, evaluate_pair, evaluate, simulate
from lab.micro.h11_momsurface import adr20


@njit(cache=True)
def magnet_events(rh, rl, rc, scode, m, A, S, off, frac):
    n = len(rc)
    out = np.empty(n, np.int64); side = np.empty(n, np.int64); dist = np.empty(n)
    k = 0
    cur = -1
    hi = -1e18; lo = 1e18
    for i in range(n):
        if scode[i] != cur:
            cur = scode[i]; hi = -1e18; lo = 1e18
        if rh[i] > hi: hi = rh[i]
        if rl[i] < lo: lo = rl[i]
        if m[i] < 575 or m[i] >= 900 or A[i] != A[i]:
            continue
        up = np.ceil((rc[i] - off) / S) * S + off
        dn = np.floor((rc[i] - off) / S) * S + off
        du = up - rc[i]; dd = rc[i] - dn
        lim = frac * A[i]
        if du > 0.25 and du <= lim and up > hi:
            out[k] = i; side[k] = 1; dist[k] = du; k += 1
        elif dd > 0.25 and dd <= lim and dn < lo:
            out[k] = i; side[k] = -1; dist[k] = dd; k += 1
    return out[:k], side[:k], dist[:k]


if __name__ == "__main__":
    D = Data()
    A = adr20(D)
    for S, off, tag in ((100, 0.0, "r100"), (100, 23.0, "p100_23"), (100, 37.0, "p100_37"), (50, 0.0, "r50"), (50, 23.0, "p50_23")):
        ei, sd, dist = magnet_events(D.rh, D.rl, D.rc, D.scode, D.m, A, float(S), off, 0.05)
        ok = D.inph[ei]
        t = simulate(D, ei[ok], sd[ok], 30, stop=dist[ok], tgt=dist[ok], end="rth")
        evaluate(D, t, f"H36_magnet_{tag}", f"calamita livello {S} off {off}: verso il livello, target=livello, stop simmetrico, 30m")
    # H39
    idx = np.arange(len(D.c)); body = D.c - D.o
    big = np.abs(body) >= 1.5 * D.sig60
    sg = np.sign(body)
    c3 = big & np.r_[False, big[:-1]] & np.r_[False, False, big[:-2]]
    same = (sg == np.r_[0, sg[:-1]]) & (sg == np.r_[0, 0, sg[:-2]])
    vdec = (D.v < np.r_[np.inf, D.v[:-1]]) & (np.r_[np.inf, D.v[:-1]] < np.r_[np.inf, np.inf, D.v[:-2]])
    ss = D.scode == np.r_[-1, -1, D.scode[:-2]]
    sel = c3 & same & vdec & ss & D.rth & (D.m >= 575) & (D.m < 900) & D.inph & (sg != 0)
    evaluate_pair(D, idx[sel], -sg[sel].astype(int), 30, "H39_exhaust_H30",
                  "3 barre grandi stesso verso con volume decrescente, RTH, fade, uscita 30m", end="rth")
