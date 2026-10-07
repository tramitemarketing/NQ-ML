"""C03: gli analoghi come strategia (esecuzione realistica) e analoghi a scala di giorni. Dichiarato prima:

Parte 1 — configurazione canonica fissata a priori (non scelta sui risultati): W=90, rep=ctx, K=25.
  Segnale alla chiusura della barra 10:59, lato = segno della media di y degli analoghi, ingresso all'open
  della barra 11:00, uscita alla close della barra 15:59. Filtri di affidabilita' dichiarati: agree >= 0,2 / 0,4
  (|media dei segni| dei 25 analoghi). Netto in punti, beta, anni, senza i 20 migliori.
Parte 1b — la configurazione scelta dalla selezione interna di A02 (W=60, shape, K=100, segno NEGATIVO scelto
  su 2011-14): valutata come trade SOLO su 2015-2018 (ingresso 10:30, uscita 15:59).
Parte 2 — analoghi di giorni: vettore = ultimi 5 giorni (rendimento RTH, notte) in unita' sigmaD, piu'
  log(range RTH / media range 20) degli ultimi 5 giorni. Esito: RTH open->close di oggi in unita' sigmaD
  (ingresso all'open 09:30: il vettore usa solo sessioni precedenti). K in {25, 50, 100}; placebo casuale (100)."""
import numpy as np
import pandas as pd

from lab import core
from lab.r2_analog import common as C

bars, daily, M = C.setup_discovery()
ok = M["ok"]; sess = M["sess"].to_numpy(); inph = M["in_phase"]


def trade_eval(si, side, o, tid, desc):
    t = C.trades_frame(M, si, side, o["m_in"], o["m_out"], side * o["pts"][si])
    st = C.evaluate_trades(bars, t)
    print(tid, C.fmt(st), st["yearly"])
    C.rec(tid, desc, st)
    return st


# Parte 1
W = 90
o = C.outcome(M, W)
NN = C.neighbors(C.distance_matrix(C.features(M, W, "ctx"), "ctx"), ok, 100)
pred = C.agg(NN, 25, o["y"]); agr = C.agg(NN, 25, o["y"], "agree")
base = ok & inph & np.isfinite(pred) & np.isfinite(o["pts"]) & (pred != 0)
for thr in (0.0, 0.2, 0.4):
    m = base & (agr >= thr)
    si = np.where(m)[0]
    trade_eval(si, np.sign(pred[si]).astype(int), o, f"c03_canon_W90_ctx_K25_agree{thr}",
               f"trade analoghi canonico W=90 ctx K=25, lato=segno media analoghi, 11:00->15:59, agree>={thr}")
    # accuratezza di segno in funzione dell'accordo (diagnostica)
# Parte 1b
W = 60
o60 = C.outcome(M, W)
NN6 = C.neighbors(C.distance_matrix(C.features(M, W, "shape"), "shape"), ok, 100)
p6 = C.agg(NN6, 100, o60["y"])
m = ok & inph & np.isfinite(p6) & (p6 != 0) & (M["year"] >= 2015)
si = np.where(m)[0]
trade_eval(si, -np.sign(p6[si]).astype(int), o60, "c03_selA_W60_shape_K100_neg_B",
           "config scelta in A (2011-14) da A02: W60 shape K100 segno opposto; trade 10:30->15:59 solo 2015-18")

# Parte 2: analoghi di giorni
dm = daily.reindex(M["sess"])
rng_d = (dm["rth_high"] - dm["rth_low"]).to_numpy()
rth_ret = np.log(M["C"][:, -1] / M["O"][:, 0]) / M["sD"]
n = len(ok)
idx = np.where(ok)[0]
lr = np.full(n, np.nan)
for j, i in enumerate(idx):
    if j >= 20:
        lr[i] = np.log(rng_d[i] / np.mean(rng_d[idx[j - 20:j]]))
F = np.full((n, 15), np.nan)
for j, i in enumerate(idx):
    if j < 25:
        continue
    prev = idx[j - 5:j][::-1]
    F[i] = np.r_[rth_ret[prev] * M["sD"][prev] / M["sD"][i], M["night"][prev] * M["sD"][prev] / M["sD"][i], lr[prev]]
okF = ok & np.isfinite(F).all(1)
D = C.distance_matrix(np.where(np.isfinite(F), F, 0), "path")
NNd = C.neighbors(D, okF, 100)
y = rth_ret
ptsd = M["AC"][:, -1] - M["AO"][:, 0]
rng = np.random.default_rng(3)
PL = [C.random_neighbors(okF, 100, rng) for _ in range(100)]
for K in (25, 50, 100):
    p = C.agg(NNd, K, y)
    mm = okF & inph & np.isfinite(p) & np.isfinite(y)
    st = C.ic_stats(p, y, sess, mm)
    pl = []
    for P in PL:
        pp = C.agg(P, K, y); pl.append(np.corrcoef(pp[mm], y[mm])[0, 1])
    st["plac_pct"] = float((np.array(pl) < st["ic"]).mean())
    print("days K", K, C.fmt(st))
    C.rec(f"c03_days_K{K}", f"analoghi di giorni (5 giorni: RTH, notte, log range rel.) -> RTH open-close oggi; K={K}; vs 100 placebo", st)
    si = np.where(mm & (p != 0))[0]
    side = np.sign(p[si]).astype(int)
    t = C.trades_frame(M, si, side, 570, 960, side * ptsd[si])
    st2 = C.evaluate_trades(bars, t)
    print("   trade", C.fmt(st2), st2["yearly"])
    C.rec(f"c03_days_K{K}_trade", f"trade analoghi di giorni K={K}: lato=segno previsione, 09:30->15:59", st2)
