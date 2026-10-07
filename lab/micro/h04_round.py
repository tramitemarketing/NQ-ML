"""H4 numeri tondi (Osler 2003) sui prezzi GREZZI. Livelli L = k*S + off.
Evento alla chiusura della barra i: la barra tocca un livello non toccato prima nella sessione
(prima volta nella sessione) arrivando da sotto (high >= L > close[i-1]) o da sopra.
  - 'reject': la barra tocca ma chiude dal lato di provenienza  -> fade = rimbalzo (barriera)
  - 'break' : la barra chiude oltre il livello di >= 1 tick         -> fade = rientro; cont = rottura
Placebo: stessi eventi su livelli spostati (off non tondi). Il confronto tondo-placebo e' il test."""
import numpy as np
import pandas as pd
from numba import njit
from lab.micro.common import Data, evaluate_pair


@njit(cache=True)
def events(rh, rl, rc, scode, S, off):
    n = len(rc)
    ev_i = np.empty(n, np.int64); ev_dir = np.empty(n, np.int64); ev_kind = np.empty(n, np.int64)
    k = 0
    touched = {-1.0}
    cur = -1
    for i in range(1, n):
        if scode[i] != cur:
            cur = scode[i]
            touched = {-1.0}
            continue
        pc = rc[i - 1]
        L = np.ceil((pc - off) / S) * S + off
        if L == pc:
            L += S
        if rh[i] >= L and L not in touched:
            touched.add(L)
            ev_i[k] = i; ev_dir[k] = 1; ev_kind[k] = 1 if rc[i] >= L + 0.25 else 0; k += 1
        L2 = np.floor((pc - off) / S) * S + off
        if L2 == pc:
            L2 -= S
        if rl[i] <= L2 and L2 not in touched:
            touched.add(L2)
            ev_i[k] = i; ev_dir[k] = -1; ev_kind[k] = 1 if rc[i] <= L2 - 0.25 else 0; k += 1
    return ev_i[:k], ev_dir[:k], ev_kind[:k]


if __name__ == "__main__":
    D = Data()
    bm = {"RTH": D.rth & (D.m >= 575) & (D.m < 900), "ETH": (~D.rth) & ((D.m >= 1085) | (D.m < 509))}
    ends = {"RTH": "rth", "ETH": "session"}
    for S, offs in ((100, (0.0, 23.0, 61.0)), (50, (0.0, 17.0, 33.0))):
        for off in offs:
            ei, ed, ek = events(D.rh, D.rl, D.rc, D.scode, float(S), off)
            tag = "round" if off == 0 else f"plac{int(off)}"
            for band in ("RTH", "ETH"):
                ok = bm[band][ei] & D.inph[ei]
                for kind, kname in ((0, "reject"), (1, "break")):
                    sel = ok & (ek == kind)
                    # fade: reject -> contro la direzione di arrivo; break -> contro la rottura
                    side = -ed[sel]
                    for H in (15, 60):
                        evaluate_pair(D, ei[sel], side, H, f"H4_{kname}_S{S}_{tag}_{band}_H{H}",
                                      f"livello {S} off {off} ({tag}), primo tocco in sessione, {kname}, {band}, uscita {H}m",
                                      end=ends[band])
