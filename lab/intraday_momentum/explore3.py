"""Lotto 3: idee nuove + diagnostica in unita' adimensionali.

H25 fine mese (ribilanciamento): ultimo giorno valido del mese, -segno(rendimento del mese a 15:30) 15:30-16:00.
H28 prima ora -> resto del giorno: segno(09:30->10:30) -> 10:30-16:00.
H31 efficienza del percorso 09:30-15:30 (|mossa netta| / somma |mosse 1m|) alta -> momentum ultima mezz'ora.
H32 posizione nel range alle 15:30: >0,8 long, <0,2 short -> 15:30-16:00.
H33 nuovo massimo/minimo del giorno fra 15:00 e 15:30 -> prosecuzione 15:30-16:00.
H34 uscita alle 16:15 (futures dopo la chiusura cash): segno(rin) 15:30-16:15.
D01 diagnostica: hit rate e lordo in unita' di sigma60 passata dell'ultima mezz'ora (adimensionale), per anno.
"""
import numpy as np
import pandas as pd

from lab import core
from lab.intraday_momentum.common import build, ret, trade, evaluate, rec, FAM

bars, daily = core.load("discovery")
M = build(bars, daily)
ok = M["ok"]
S = M["sess"]
one = pd.Series(1, index=S)


def drift(t0, t1):
    d = trade(M, one, t0, t1)
    return d[d.in_phase]["gross_pts"]


DL = drift(930, 960)
rin = ret(M, 570, 930)

# H25 fine mese
okS = ok[ok]
last_of_month = pd.Series(False, index=S)
lm = okS.index.to_series().groupby(okS.index.to_period("M")).max()
last_of_month[lm.values] = True
first_of_month = okS.index.to_series().groupby(okS.index.to_period("M")).min()
# rendimento del mese: chiusura ultimo giorno del mese precedente -> 15:30 di oggi
pc_month = pd.Series(np.nan, index=S)
for p, d0 in first_of_month.items():
    pc_month[d0] = M["prev_close"][d0]
pc_month = pc_month.ffill()
mtd = (M["adj_close"][929] - pc_month) / M["close"][929]
rec("H25_monthend_rev", "fine mese: -segno(rendimento mese a 15:30) 15:30-16:00 ultimo giorno valido",
    evaluate(trade(M, -np.sign(mtd), 930, 960, last_of_month), DL))
rec("H25_monthend_mom", "fine mese: +segno(rendimento mese a 15:30) 15:30-16:00 (specchio)",
    evaluate(trade(M, np.sign(mtd), 930, 960, last_of_month), DL))

# H28 prima ora -> resto del giorno
rec("H28_firsthour_rest", "segno(09:30->10:30) -> 10:30-16:00",
    evaluate(trade(M, np.sign(ret(M, 570, 630)), 630, 960), drift(630, 960)))

# H31 efficienza del percorso
c = M["adj_close"].loc[:, 570:929]
path = c.diff(axis=1).abs().sum(axis=1)
eff = (c[929] - M["adj_open"][570]).abs() / path
for q in (0.2, 0.3):
    rec(f"H31_eff{q}", f"segno(rin) -> ultima mezz'ora solo se efficienza 09:30-15:30 > {q}",
        evaluate(trade(M, np.sign(rin), 930, 960, eff > q), DL))

# H32 posizione nel range
hi_ = M["adj_close"].loc[:, 570:929].max(axis=1)
lo_ = M["adj_close"].loc[:, 570:929].min(axis=1)
loc = (M["adj_close"][929] - lo_) / (hi_ - lo_)
side = pd.Series(0, index=S).where(~(loc > 0.8), 1).where(~(loc < 0.2), -1)
rec("H32_rangeloc", "posizione nel range 09:30-15:30 >0,8 long / <0,2 short -> 15:30-16:00",
    evaluate(trade(M, side, 930, 960), DL))

# H33 nuovo estremo fra 15:00 e 15:30
h_am = M["adj_close"].loc[:, 570:899].max(axis=1)
l_am = M["adj_close"].loc[:, 570:899].min(axis=1)
h_pm = M["adj_close"].loc[:, 900:929].max(axis=1)
l_pm = M["adj_close"].loc[:, 900:929].min(axis=1)
nh, nl = h_pm > h_am, l_pm < l_am
side = pd.Series(0, index=S).where(~(nh & ~nl), 1).where(~(nl & ~nh), -1)
rec("H33_newext", "nuovo massimo (minimo) del giorno fra 15:00 e 15:30 -> long (short) 15:30-16:00",
    evaluate(trade(M, side, 930, 960), DL))

# H34 uscita alle 16:15: barre fuori RTH fra 16:00 e 16:14
post = bars[(bars.ny_min >= 960) & (bars.ny_min <= 974)].pivot_table(index="session", columns="ny_min", values="adj_close", aggfunc="first").reindex(S)
x1615 = post.ffill(axis=1)[974]
e = M["adj_open"][930]
s = np.sign(rin)
mask = ok & s.ne(0) & x1615.notna()
tr = pd.DataFrame({"session": S[mask.to_numpy()], "side": s[mask].astype(int).to_numpy(),
                   "gross_pts": ((x1615 - e) * s)[mask].to_numpy(), "raw_px": M["close"][930][mask].to_numpy(),
                   "in_phase": M["in_phase"][mask].to_numpy()})
d1615 = ((x1615 - e)[ok & M["in_phase"]]).dropna()
rec("H34_rin_exit1615", "segno(rin) -> 15:30-16:15 (uscita dopo la chiusura cash)", evaluate(tr, d1615))

# D01 diagnostica adimensionale per i predittori principali
y_pts = (M["adj_close"][959] - M["adj_open"][930]).where(ok)
sig_y = y_pts.rolling(60, min_periods=40).std().shift(1)
for nm, x in [("rin", rin), ("rbd", ret(M, "pc", 930)), ("r1", ret(M, "pc", 600))]:
    s = np.sign(x)
    z = (s * y_pts / sig_y)[ok & M["in_phase"] & s.ne(0)].dropna()
    hit = (s * y_pts > 0)[z.index]
    st = core.day_block_bootstrap(z.to_numpy(), z.index.to_numpy())
    st["hit"] = float(hit.mean())
    yz = core.yearly(z.to_numpy(), z.index)
    st["yearly_z"] = {int(k): round(float(v), 3) for k, v in yz["mean"].items()}
    st["years_pos"] = f"{int((yz['mean'] > 0).sum())}/{len(yz)}"
    core.record(FAM, f"D01_z_{nm}", f"lordo segno({nm}) ultima mezz'ora in unita' sigma60 passata (adimensionale)", "discovery", st)
    print(f"D01_z_{nm}: z={st['mean']:+.4f} [{st['lo']:+.4f};{st['hi']:+.4f}] p+={st['p_pos']:.3f} hit={st['hit']:.3f} yrs={st['years_pos']} {st['yearly_z']}")
