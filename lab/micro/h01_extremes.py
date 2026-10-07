"""H1/H2/H22: overreaction o continuazione dopo movimenti estremi di k minuti (k=1,5,15),
misurati in multipli della volatilita' recente (std 1m delle 60 barre precedenti * sqrt(k)).
Lato 'fade' = contro il movimento. Due fasce: RTH (ingresso 09:35-15:00, uscita entro 15:59) e ETH
(18:05-08:29). Un test per (k, soglia, H, fascia), fade e continuazione nella stessa riga."""
import numpy as np
from lab.micro.common import Data, evaluate_pair

D = Data()
n = len(D.c)
idx = np.arange(n)
res = {}
for k in (1, 5, 15):
    prev = idx - k
    ok = (prev >= 0)
    prev = np.clip(prev, 0, None)
    move = D.c - D.c[prev]
    same = D.scode[prev] == D.scode
    z = move / (D.sig60 * np.sqrt(k))
    for band in ("RTH", "ETH"):
        if band == "RTH":
            bm = D.rth & (D.m >= 575) & (D.m < 900)
            end = "rth"
        else:
            bm = (~D.rth) & ((D.m >= 1085) | (D.m < 509))
            end = "session"
        for thr in (3, 4, 6):
            sel = ok & same & bm & D.inph & np.isfinite(z) & (np.abs(z) >= thr) & (D.sig60 > 0)
            sig = idx[sel]
            side = -np.sign(move[sel]).astype(int)
            for H in (5, 15, 30, 60):
                tid = f"H1_ext_k{k}_{band}_z{thr}_H{H}"
                evaluate_pair(D, sig, side, H, tid,
                              f"movimento {k}m |z|>={thr} (sigma60 1m), {band}, uscita a {H}m", end=end)
