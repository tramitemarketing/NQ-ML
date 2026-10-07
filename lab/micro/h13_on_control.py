"""Controllo per H5_ON: l'effetto e' del livello notturno o e' il generico ritorno del primo movimento
RTH? (1) fade di segno(close - open RTH) a orari fissi 09:45/10:00/10:15, uscita 120m, tutti i giorni.
(2) stesso timing degli eventi ON-break 09:35-12:00 ma lato = fade del movimento dall'open RTH
    (coincide quasi sempre col lato ON: si misura quanta parte del segnale e' spiegata).
(3) eventi ON-break per profondita' della notte: range notturno piccolo vs grande (terzili)."""
import numpy as np
import pandas as pd
from lab.micro.common import Data, evaluate_pair, evaluate, simulate
from lab.micro.h05_levels import level_events, levels
from lab.micro.h11_momsurface import adr20

D = Data()
idx = np.arange(len(D.c))
i930 = np.full(D.scode.max() + 1, -1); w = np.nonzero(D.m == 570)[0]; i930[D.scode[w]] = w
ro = np.where(i930[D.scode] >= 0, D.o[np.maximum(i930[D.scode], 0)], np.nan)
for mm in (584, 599, 614):
    sel = (D.m == mm) & D.inph & np.isfinite(ro) & (D.c != ro)
    s = idx[sel]
    evaluate_pair(D, s, -np.sign(D.c[s] - ro[s]).astype(int), 120, f"H5c_openfade_{mm}_H120",
                  f"controllo: fade di segno(close-open RTH) alla barra minuto {mm}, uscita 120m, tutti i giorni", end="rth")
L = levels(D); U, Dn = L["ON"]
ei, es, ek = level_events(D.h, D.l, D.c, D.m, D.scode, U.astype(float), Dn.astype(float), 575, 720)
ok = D.inph[ei] & (ek == 1)
s = ei[ok]; side_on = es[ok]
side_open = -np.sign(D.c[s] - ro[s]).astype(int)
print("concordanza lato ON vs lato open-fade:", np.mean(side_on == side_open))
# eventi discordi soli
disc = side_on != side_open
evaluate_pair(D, s[disc], side_on[disc], 120, "H5c_ONbreak_discordant_H120",
              "ON break 09:35-12:00 dove il lato ON e' opposto al fade del movimento dall'open, uscita 120m", end="rth")
evaluate_pair(D, s[~disc], side_on[~disc], 120, "H5c_ONbreak_concordant_H120",
              "ON break 09:35-12:00 con lato ON = fade del movimento dall'open, uscita 120m", end="rth")
# terzili del range notturno relativo ad ADR20
A = adr20(D)
onr = (U - Dn)[D.scode[s]] / A[s]
q = np.nanquantile(onr, [1/3, 2/3])
for j, (a, b) in enumerate(((-np.inf, q[0]), (q[0], q[1]), (q[1], np.inf))):
    m = (onr > a) & (onr <= b)
    evaluate_pair(D, s[m], side_on[m], 120, f"H5c_ONbreak_onrange_t{j+1}_H120",
                  f"ON break 09:35-12:00, terzile {j+1} di range notturno/ADR20, uscita 120m", end="rth")
