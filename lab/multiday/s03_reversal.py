"""Approfondimento: il tema emerso dagli screening 1-2 e' il REVERSAL a 1-4 settimane
(TSMOM a 1-2 settimane significativamente NEGATIVO; comprare dopo i ribassi batte la deriva; VR(20) < 1).
Qui una sola famiglia di regole, griglia dichiarata prima:
 A) contrarian a posizione continua: pos_t = -sign(rendimento k giorni) con k in {5, 10, 15, 20};
    misurato long/short, sola gamba long (long/flat), sola gamba short (short/flat).
 B) dip-buy a evento: long se il rendimento a k giorni < -thr * sigma20 * sqrt(k), k in {1, 5, 10},
    thr in {1, 1.5, 2}, tenuta h in {5, 10}, trade NON sovrapposti.
Metriche: eccesso sulla deriva (bp), anni positivi, e per A la differenza di Sharpe vs buy-and-hold."""
import numpy as np
import pandas as pd

from lab import core
import lab.multiday.common as C
C.REV = 3   # rev3: B corretto (rendimento % su prezzo raw)
from lab.multiday.common import (load_daily, position_eval, sharpe_diff_boot, boot, years_pos, rec, sharpe, fwd)

d, bars = load_daily()
mu = d["r"].mean()
c = d["rth_close"]
rc = d["ret_cc_pct"]
sig20 = rc.rolling(20).std()
bh = position_eval(d, pd.Series(1.0, index=d.index), mu)
START = d.index[260]
pd.set_option("display.width", 220)

rowsA = []
for k in ():   # A gia' registrato in rev2 (usa solo il segno: non toccato dal bug)
    past = c / c.shift(k) - 1
    s = -np.sign(past)
    for leg, pos in (("ls", s), ("long", s.clip(lower=0)), ("short", s.clip(upper=0))):
        pe = position_eval(d, pos, mu)
        pe = pe[pe.index >= START]
        b = bh.loc[pe.index]
        sd = sharpe_diff_boot(pe["pnl"], b["pnl"], n_boot=2000)
        st = boot(pe["exc"].to_numpy() * 1e4, pe.index)
        stn = boot(pe["pnl"].to_numpy() * 1e4, pe.index)
        out = dict(st, unit="bp/giorno eccesso", net_raw_bp=stn["mean"], net_raw_lo=stn["lo"], sr=sd["sr_a"], dsr=sd["diff"],
                   dsr_lo=sd["lo"], dsr_hi=sd["hi"], mean_pos=float(pe["pos"].mean()),
                   years_exc_pos=years_pos(pe["exc"], pe.index), years_net_pos=years_pos(pe["pnl"], pe.index),
                   pts_net_day=float(pe["pts"].mean()))
        rec(f"A_contra_k{k}_{leg}", f"contrarian: pos = -sign(rendimento {k} giorni), gamba {leg}, ribilancio giornaliero", out)
        rowsA.append(dict(id=f"k{k}_{leg}", **{x: out[x] for x in ("mean", "lo", "hi", "net_raw_bp", "net_raw_lo", "sr", "dsr", "dsr_lo", "mean_pos", "years_exc_pos", "years_net_pos", "pts_net_day")}))
if rowsA: print(pd.DataFrame(rowsA).set_index("id").round(2).to_string())


def nonoverlap(mask: pd.Series, h: int) -> pd.Series:
    m = mask.fillna(False).to_numpy()
    keep = np.zeros_like(m)
    nxt = -1
    for i in range(len(m)):
        if m[i] and i >= nxt:
            keep[i] = True
            nxt = i + h
    return pd.Series(keep, index=mask.index)


V = d["valid"]
rowsB = []
for k in (1, 5, 10):
    zk = ((c - c.shift(k)) / d["Praw"].shift(k)) / (sig20.shift(1) * np.sqrt(k))   # % su prezzo RAW (adj e' additivo)
    for thr in (1.0, 1.5, 2.0):
        for h in (5, 10):
            m = nonoverlap((zk < -thr) & V, h)
            pct, pts = fwd(d, h)
            ok = m & pct.notna()
            idx = d.index[ok]
            exc = (pct[ok] - mu * h).to_numpy() * 1e4
            atrn = (pts[ok] / d["atr14"][ok]).to_numpy()
            atr_base = (pts / d["atr14"]).mean()
            st = boot(exc, idx)
            sa = boot(atrn - atr_base, idx)
            net = pts[ok].to_numpy() - core.COST_RT_POINTS
            out = dict(st, unit="bp eccesso per trade", h=h, k=k, thr=thr, exc_atr=sa["mean"], exc_atr_lo=sa["lo"],
                       years_exc_pos=years_pos(exc, idx), net_pts=float(net.mean()), net_pts_drop20=core.drop_top(net),
                       years_net_pos=years_pos(net, idx), frac_2011_15_18=float(np.isin(idx.year, [2011, 2015, 2018]).mean()))
            rec(f"B_dip_k{k}_thr{thr}_h{h}", f"dip-buy: rendimento {k}g < -{thr} sigma20*sqrt(k), long {h} giorni, non sovrapposti", out)
            rowsB.append(dict(id=f"k{k}_t{thr}_h{h}", **{x: out[x] for x in ("n", "mean", "lo", "hi", "p_pos", "exc_atr", "exc_atr_lo", "years_exc_pos", "net_pts", "net_pts_drop20", "years_net_pos", "frac_2011_15_18")}))
print(pd.DataFrame(rowsB).set_index("id").round(2).to_string())
