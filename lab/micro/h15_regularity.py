"""Binario 'regolarita'': continuazione lorda dopo movimenti estremi (H1). Tutte le ore di sessione
tranne 15:00-18:05 (fine RTH e chiusura), segnale |mov k m| >= z * sigma60 * sqrt(k), lato = verso del
movimento, uscita a H minuti, non sovrapposti. Lordo in punti, test bilaterale. Tre varianti fissate
prima di guardare (k,z,H) = (15,3,30), (5,4,30), (1,4,15); poi per anno."""
import numpy as np
from lab.micro.common import Data, fwd_regularity, simulate
from lab import core

D = Data()
n = len(D.c); idx = np.arange(n)
band = ((D.m >= 1085) | (D.m < 900)) & D.inph
for k, z, H in ((15, 3, 30), (5, 4, 30), (1, 4, 15)):
    prev = np.clip(idx - k, 0, None)
    mv = D.c - D.c[prev]
    zz = mv / (D.sig60 * np.sqrt(k))
    sel = band & (D.scode[prev] == D.scode) & np.isfinite(zz) & (np.abs(zz) >= z)
    s = idx[sel]
    st = fwd_regularity(D, s, np.sign(mv[s]).astype(int), H, f"H15_reg_cont_k{k}_z{z}_H{H}",
                        f"regolarita': continuazione lorda dopo |mov {k}m|>={z} sigma, tutte le ore tranne 15:00-18:05, H={H}m")
    t = simulate(D, s, np.sign(mv[s]).astype(int), H, end="session", nonoverlap=True)
    t = t[t.in_phase]
    y = core.yearly(t.gross_pts.to_numpy(), t.session)
    print(y.round(3).T.to_string())
    print("drop20 lordo", core.drop_top(t.gross_pts.to_numpy(), 20), "RTH share", np.mean(D.rth[t.entry_i]))
