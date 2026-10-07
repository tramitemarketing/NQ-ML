"""Lotto vario:
 H32  Gao-Han-Li-Zhou (2018) intraday momentum: lato = segno(close RTH di ieri -> 10:00 di oggi, adj),
      long/short 15:30 -> 15:59. Variante di un'idea gia' schermata (ultima ora): dichiarato.
 H33  chiusura MOC: lato = segno(open RTH -> 15:49), trade 15:50 -> 15:59.
 H25  stagionalita' per minuto dell'ora (RTH): long all'open dei minuti :00 e :30 per 5 minuti
      (regolarita': lordo), e long ai minuti :55-:59 contro :00-:04 (placebo implicito).
 H34  inversione dopo 'sweep' del massimo/minimo della prima ora? -> CHIUSO nel progetto, non rifatto.
 H35  barre 'outside' 1m (range che ingloba le 5 barre precedenti) in RTH: fade/cont del corpo."""
import numpy as np
import pandas as pd
from lab.micro.common import Data, evaluate_pair, fwd_regularity

D = Data()
n = len(D.c); idx = np.arange(n)


def at_minute(mm):
    a = np.full(D.scode.max() + 1, -1, np.int64)
    w = np.nonzero(D.m == mm)[0]
    a[D.scode[w]] = w
    return a

# H32
i959 = at_minute(959); i1000 = at_minute(599); i1529 = at_minute(929); i930 = at_minute(570)
S = D.scode.max() + 1
prev_close = np.full(S, np.nan)
for s in range(1, S):
    if i959[s - 1] >= 0:
        prev_close[s] = D.c[i959[s - 1]]
ok = (i1000 >= 0) & (i1529 >= 0) & np.isfinite(prev_close)
sig = i1529[ok]; mv = D.c[i1000[ok]] - prev_close[ok]
g = D.inph[sig] & (mv != 0)
evaluate_pair(D, sig[g], np.sign(mv[g]).astype(int), 29, "H32_gao_momentum",
              "lato=segno(close RTH ieri->10:00), ingresso 15:30 uscita 15:59 [lato dato=continuazione, 'fade'=momentum]", end="rth")
# H33
i1549 = at_minute(949)
ok = (i1549 >= 0) & (i930 >= 0)
sig = i1549[ok]; mv = D.c[sig] - D.o[i930[ok]]
g = D.inph[sig] & (mv != 0)
evaluate_pair(D, sig[g], np.sign(mv[g]).astype(int), 9, "H33_moc_momentum",
              "lato=segno(open RTH->15:49), ingresso 15:50 uscita 15:59 [lato dato=momentum]", end="rth")
# H25 regolarita' minuto dell'ora
for mm, tag in ((59, "min00"), (29, "min30"), (54, "min55")):
    sel = D.rth & D.inph & ((D.m % 60) == mm) & (D.m >= 570) & (D.m < 950)
    fwd_regularity(D, idx[sel], 1, 5, f"H25_long5_{tag}", f"long 5 minuti dall'open del minuto {tag} (RTH), lordo", end="rth")
# H35 outside bars
hh5 = pd.Series(D.h).rolling(5).max().shift(1).to_numpy()
ll5 = pd.Series(D.l).rolling(5).min().shift(1).to_numpy()
same5 = D.scode[np.clip(idx - 5, 0, None)] == D.scode
body = D.c - D.o
sel = same5 & (D.h > hh5) & (D.l < ll5) & D.rth & (D.m >= 575) & (D.m < 900) & D.inph & (body != 0)
for H in (15, 60):
    evaluate_pair(D, idx[sel], -np.sign(body[sel]).astype(int), H, f"H35_outside5_H{H}",
                  f"barra 1m che ingloba le 5 precedenti, RTH, fade corpo, uscita {H}m", end="rth")
