"""Sensibilita' di H5_ON (massimo/minimo della notte attraversato in RTH): break / sweep / reentry,
orizzonti 30/60/90/120/fine RTH, finestre orarie 09:35-15:00 e 09:35-12:00 e 10:30-15:00.
Solo lato fade (verso l'interno) riportato come primo, cont nella stessa riga."""
import numpy as np
from lab.micro.common import Data, evaluate_pair
from lab.micro.h05_levels import level_events, levels

D = Data()
L = levels(D)
U, Dn = L["ON"]
names = {0: "sweep", 1: "break", 2: "reentry"}
for (lo, hi) in ((575, 900), (575, 720), (630, 900)):
    ei, es, ek = level_events(D.h, D.l, D.c, D.m, D.scode, U.astype(float), Dn.astype(float), lo, hi)
    ok = D.inph[ei]
    for kind in (0, 1, 2):
        sel = ok & (ek == kind)
        for H in (30, 60, 90, 120, 999):
            if (lo, hi) == (575, 900) and H == 60:
                continue  # gia' registrato in h05
            evaluate_pair(D, ei[sel], es[sel], H, f"H5s_ON_{names[kind]}_{lo}-{hi}_H{H}",
                          f"ON max/min, {names[kind]}, finestra {lo}-{hi} min NY, uscita {H}m", end="rth")
