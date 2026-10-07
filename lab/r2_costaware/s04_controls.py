"""Batteria 3: controlli sull'orizzonte 'close' (l'unico che non seleziona solo il 2018).
(a) il filtro aggiunge qualcosa? m = 0 (sempre, primo slot) contro m = 1/1,5/2 (gia' in B2)
(b) specchio: lato opposto, stessi trade
(c) filtro senza segnale: stessi trade, lato casuale (hash della sessione) -> quanto vale il solo filtro di volatilita'
(d) placebo per permutazione: COMP rimescolato fra sessioni dentro lo slot, pendenza causale ristimata, stessa regola (100)
(e) sensibilita' dichiarata nel PIANO: sigma con moltiplicatore HAR
"""
import hashlib

import numpy as np
import pandas as pd

from lab import core
from lab.r2_costaware.common import load_panel, rule_trades, evaluate, rec, fmt, COST
from lab.vol.candidates import _har

ds = load_panel()
bars, daily = core.load("discovery")

for sig in ["COMP2", "COMP3"]:
    # (a) m = 0
    t0 = rule_trades(ds, sig, "close", 0.0)
    s = evaluate(t0)
    rec(f"B3a_{sig}_close_m0", f"Controllo: {sig} a chiusura SENZA filtro di costo (primo slot utile, di fatto 10:00)", s)
    print(f"{sig} m=0: {fmt(s)}\n   {s['years']}")
    for m in [1.0, 1.5, 2.0]:
        t = rule_trades(ds, sig, "close", m)
        # (b) specchio
        tm = t.copy(); tm["side"] = -tm["side"]; tm["gross_pts"] = -tm["gross_pts"]; tm["gross_vol"] = -tm["gross_vol"]
        s = evaluate(tm)
        rec(f"B3b_{sig}_close_m{m}_mirror", f"Specchio (lato opposto) della regola {sig} close m={m}", s)
        print(f"{sig} m={m} SPECCHIO: {fmt(s)}")
        # (c) lato casuale dall'hash della sessione, stessi trade
        hs = np.array([1 if int(hashlib.md5(str(d)[:10].encode()).hexdigest(), 16) % 2 else -1
                       for d in t["session"]])
        tr = t.copy(); tr["gross_pts"] = tr["gross_pts"] * tr["side"] * hs; tr["gross_vol"] = tr["gross_vol"] * tr["side"] * hs
        tr["side"] = hs
        s = evaluate(tr)
        rec(f"B3c_{sig}_close_m{m}_randside", f"Stessi trade della regola {sig} close m={m} con lato casuale (hash data)", s)
        print(f"{sig} m={m} LATO CASUALE: {fmt(s)}")

# (d) permutazione (solo COMP2 m=1, la regola migliore della griglia per p; dichiarato qui)
real = evaluate(rule_trades(ds, "COMP2", "close", 1.0), beta=False)
rng = np.random.default_rng(0)
means, ps = [], []
for i in range(100):
    d2 = ds.copy()
    for sl, g in d2.groupby("slot"):
        # permuta le sessioni: tutte le righe dello slot ricevono il COMP di un'altra sessione
        d2.loc[g.index, "COMP2"] = rng.permutation(g["COMP2"].to_numpy())
    s = evaluate(rule_trades(d2, "COMP2", "close", 1.0), beta=False)
    means.append(s.get("mean", np.nan)); ps.append(s.get("p_pos", np.nan))
means, ps = np.array(means), np.array(ps)
st = {"n_perm": 100, "real_mean": real["mean"], "real_p": real["p_pos"],
      "perm_p_value": float((means >= real["mean"]).mean()), "perm_mean_avg": float(np.nanmean(means)),
      "perm_mean_p95": float(np.nanpercentile(means, 95)), "frac_perm_p_lt_005": float((ps < 0.05).mean())}
rec("B3d_COMP2_close_m1_permutation", "Placebo per permutazione di COMP2 fra sessioni dentro lo slot (100), regola close m=1", st)
print("PERMUTAZIONE", st)

# (e) moltiplicatore HAR su sigma
f, y, har = _har(bars, daily)
rv = np.exp(y)
base = np.log(rv.rolling(20).mean().shift(1))
mult = np.sqrt(np.exp(har - base))           # >1 se HAR prevede piu' vol della media dei 20 giorni passati
mm = mult.reindex(pd.DatetimeIndex(ds["session"])).to_numpy()
print("molt. HAR: mediana", np.nanmedian(mm), "quota NaN", np.isnan(mm).mean())
for sig in ["COMP2", "COMP3"]:
    for m in [1.0, 1.5, 2.0]:
        t = rule_trades(ds, sig, "close", m, sig_mult=mm)
        s = evaluate(t)
        rec(f"B3e_{sig}_close_m{m}_HAR", f"Sensibilita' dichiarata: regola {sig} close m={m} con sigma x moltiplicatore HAR", s)
        print(f"{sig} m={m} HAR: {fmt(s)}\n   {s['years']}")
