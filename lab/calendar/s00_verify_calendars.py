"""Verifica dei calendari (nessun rendimento guardato): FOMC e NFP contro il picco di volume."""
import numpy as np, pandas as pd
from lab import core
from lab.calendar.common import *

bars, daily = core.load("discovery")
px = Px(bars, daily)
S = px.sessions
V = px.V
# ---- FOMC: volume nei 10 minuti dopo l'ora del comunicato / mediana dei 10 minuti precedenti
fd = fomc_dates()
fd = fd[(fd >= S[0]) & (fd <= S[-1])]
res = []
for d in fd:
    i = S.get_loc(d)
    h, m = fomc_time_ny(d)
    t = hm(h, m)
    after = V[i, t:t + 10].mean(); before = V[i, t - 30:t].mean()
    # confronto con lo stesso minuto negli altri mercoledi'
    res.append((d.date(), h, m, after / max(before, 1)))
r = pd.DataFrame(res, columns=["d", "h", "m", "ratio"])
print(r.to_string())
print("FOMC con ratio<2:", (r.ratio < 2).sum(), "/", len(r))
# ---- detection (b): mercoledi' con il massimo rapporto volume 14:00(14:15)/prima
det = []
for i, s in enumerate(S):
    for (h, m) in [(14, 0), (14, 15), (12, 30)]:
        t = hm(h, m)
        a = V[i, t:t + 5].mean(); b_ = V[i, t - 30:t].mean()
        if b_ > 0 and a / b_ > 4:
            det.append((s.date(), h, m, a / b_))
det = pd.DataFrame(det, columns=["d", "h", "m", "ratio"])
fset = set(fd.date)
print("rilevati (ratio>4) non in lista FOMC:")
print(det[~det.d.isin(fset)].to_string())
print("FOMC in lista rilevati:", det.d.isin(fset).sum())
# ---- NFP: rapporto volume 8:30-8:35 / 8:00-8:30
nf = nfp_dates(2010, 2018)
nf = nf[(nf >= S[0]) & (nf <= S[-1])]
t = hm(8, 30)
ratio = pd.Series(V[:, t:t + 5].mean(1) / np.maximum(V[:, t - 30:t].mean(1), 1), index=S)
fr = ratio[S.dayofweek == 4]
print("NFP da regola: ratio mediano", ratio.reindex(nf).median(), "min", ratio.reindex(nf).min())
print(ratio.reindex(nf).sort_values().head(8))
print("venerdi' non-NFP con ratio > mediana NFP/2:")
thr = ratio.reindex(nf).median() / 2
print(fr[(fr > thr) & ~fr.index.isin(nf)].sort_values(ascending=False).head(15))
# ---- festivita': sessioni con meno di 300 barre RTH vs calendario
hol = exchange_holidays(2010, 2018)
inv = daily.index[~daily.valid]
print("invalid non festivi:", [d.date() for d in inv if d.date() not in hol])
tc = trading_calendar(2010, 2018)
tc = tc[(tc >= S[0]) & (tc <= S[-1])]
print("giorni di borsa previsti senza sessione:", [d.date() for d in tc if d not in S])
