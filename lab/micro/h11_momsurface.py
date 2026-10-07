"""H1-bis: superficie di sensibilita' della continuazione dopo movimenti estremi, normalizzati sul
range RTH medio delle 20 sessioni precedenti (ADR20, niente effetto ora-del-giorno della sigma60).
Segnale RTH 09:35-15:00, finestra del movimento interamente in RTH, ingresso alla barra dopo.
Griglia k x soglia x H; lato riportato come 'fade' (contro) e 'cont' (a favore) nella stessa riga."""
import numpy as np
import pandas as pd
from lab.micro.common import Data, evaluate_pair


def adr20(D):
    d = D.daily.reindex(pd.DatetimeIndex(pd.unique(D.sess)))
    rr = (d["rth_high"] - d["rth_low"]).where(d["valid"])
    a = rr.rolling(20, min_periods=10).mean().shift(1).to_numpy()
    return a[D.scode]


if __name__ == "__main__":
    D = Data()
    n = len(D.c); idx = np.arange(n)
    A = adr20(D)
    for k in (5, 15, 30, 60):
        prev = np.clip(idx - k, 0, None)
        mv = D.c - D.c[prev]
        ok = (D.scode[prev] == D.scode) & (D.m - k >= 570) & D.rth & (D.m >= 575) & (D.m < 900) & D.inph & np.isfinite(A)
        zz = mv / A
        for x in (0.10, 0.15, 0.20, 0.30):
            hit = ok & (np.abs(zz) >= x)
            s = idx[hit]
            side = -np.sign(mv[s]).astype(int)
            for H in (30, 60, 120, 999):
                evaluate_pair(D, s, side, H, f"H1b_k{k}_x{x:.2f}_H{H}",
                              f"|mov {k}m|/ADR20>={x}, RTH, uscita {H if H<999 else 'fine RTH'}m", end="rth")
