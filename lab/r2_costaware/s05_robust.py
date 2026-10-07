"""Batteria 4: robustezza della regola COMP2 -> chiusura e misure di regolarita'.
(a) permutazione confrontata sul p (non sulla media, che con n piccolo e' instabile)
(b) un solo istante di decisione (10:00, 12:00, 14:00) con m = 1
(c) parametri di costruzione: minimo sessioni per la pendenza 500; pendenza fissa = 1 (niente stima)
(d) concentrazione: quota del totale dovuta ai 20 migliori, per anno
(e) regolarita' in unita' vol: una riga al giorno (media sugli slot di segno(COMP2)*y_close), e per terzile di sigma
"""
import numpy as np
import pandas as pd

from lab import core
from lab.r2_costaware.common import load_panel, rule_trades, evaluate, rec, fmt, causal_slope, COST

ds = load_panel()

# (a) permutazione sul p
real = evaluate(rule_trades(ds, "COMP2", "close", 1.0), beta=False)
rng = np.random.default_rng(1)
ps, ns = [], []
for i in range(200):
    d2 = ds.copy()
    for sl, g in d2.groupby("slot"):
        d2.loc[g.index, "COMP2"] = rng.permutation(g["COMP2"].to_numpy())
    s = evaluate(rule_trades(d2, "COMP2", "close", 1.0), beta=False)
    ps.append(s.get("p_pos", 1.0) if s.get("n", 0) >= 30 else 1.0); ns.append(s.get("n", 0))
ps = np.array(ps)
st = {"n_perm": 200, "real_p": real["p_pos"], "perm_rank_p": float((ps <= real["p_pos"]).mean()),
      "perm_median_n": float(np.median(ns))}
rec("B4a_COMP2_close_m1_perm_p", "Permutazione (200) di COMP2 fra sessioni dentro lo slot: rango del p reale fra i p permutati", st)
print("PERM p", st)

# (b) un solo istante
for sl in [600, 720, 840]:
    d = ds[ds["slot"] == sl].reset_index(drop=True)
    t = rule_trades(d, "COMP2", "close", 1.0)
    s = evaluate(t)
    rec(f"B4b_COMP2_close_m1_slot{sl}", f"Regola COMP2 close m=1 con un solo istante di decisione (minuto NY {sl})", s)
    print(f"slot {sl}: {fmt(s)}\n   {s['years']}")

# (c) costruzione
b500 = causal_slope(ds, "COMP2", "close", min_sess=500)
t = rule_trades(ds, "COMP2", "close", 1.0, slope=b500)
s = evaluate(t); rec("B4c_COMP2_close_m1_minsess500", "Regola COMP2 close m=1, pendenza con minimo 500 sessioni", s)
print(f"min500: {fmt(s)}\n   {s['years']}")
bfix = np.full(len(ds), 0.05)
for m in [1.0, 2.0]:
    t = rule_trades(ds, "COMP2", "close", m, slope=bfix)
    s = evaluate(t); rec(f"B4c_COMP2_close_m{m}_bfix005", f"Regola COMP2 close m={m}, pendenza FISSA 0,05 (nessuna stima)", s)
    print(f"bfix m={m}: {fmt(s)}\n   {s['years']}")

# (d) concentrazione
t = rule_trades(ds, "COMP2", "close", 1.0)
net = t["gross_pts"].to_numpy() - COST
o = np.argsort(net)[::-1]
print("totale netto", net.sum().round(1), "top20", net[o[:20]].sum().round(1), "anni dei top20",
      pd.DatetimeIndex(t["session"].to_numpy()[o[:20]]).year.value_counts().to_dict())
print("peggiori 20", net[o[-20:]].sum().round(1))
rec("B4d_COMP2_close_m1_concentration", "Concentrazione: somma netta totale vs 20 migliori", {"total": float(net.sum()),
    "top20": float(net[o[:20]].sum()), "bottom20": float(net[o[-20:]].sum()), "n": len(net)})

# (e) regolarita' giornaliera in unita' vol
ok = np.isfinite(ds["COMP2"]) & np.isfinite(ds["y_close"]) & (ds["COMP2"] != 0)
d = ds[ok].copy()
d["q"] = np.sign(d["COMP2"]) * d["y_close"]
day = d.groupby("session")["q"].mean()
st = core.day_block_bootstrap(day.to_numpy(), day.index.values)
yr = core.yearly(day.to_numpy(), day.index)
rec("B4e_COMP2_close_daily_vol", "Regolarita': media giornaliera sugli slot di segno(COMP2)*y_close (unita' vol)", st,
    years={int(k): round(float(v), 4) for k, v in yr["mean"].items()}, years_pos=f"{int((yr['mean']>0).sum())}/{len(yr)}")
print("REG giornaliera", st, yr["mean"].round(3).to_dict())
# centrata: segno di (COMP2 - mediana passata) per togliere lo sbilanciamento long di z_20d
med = ds["COMP2"].shift(1).rolling(3000, min_periods=1000).median()
d = ds.assign(c=ds["COMP2"] - med)
ok = np.isfinite(d["c"]) & np.isfinite(d["y_close"]) & (d["c"] != 0)
d = d[ok]
d["q"] = np.sign(d["c"]) * d["y_close"]
day = d.groupby("session")["q"].mean()
st = core.day_block_bootstrap(day.to_numpy(), day.index.values)
yr = core.yearly(day.to_numpy(), day.index)
rec("B4e_COMP2c_close_daily_vol", "Regolarita' CENTRATA: segno(COMP2 - mediana 3000 passata)*y_close, media giornaliera, unita' vol", st,
    years={int(k): round(float(v), 4) for k, v in yr["mean"].items()}, years_pos=f"{int((yr['mean']>0).sum())}/{len(yr)}",
    long_share=float((d["c"] > 0).mean()))
print("REG centrata", st, yr["mean"].round(3).to_dict(), "long", (d["c"] > 0).mean())
# per terzile di sigma (punti) della regola: il vantaggio in vol e' costante? in punti cresce?
t = rule_trades(ds, "COMP2", "close", 0.0)
t["ter"] = pd.qcut(t["sigma"], 3, labels=False)
for k, g in t.groupby("ter"):
    s1 = core.day_block_bootstrap(g["gross_vol"].to_numpy(), g["session"].values)
    s2 = core.day_block_bootstrap(g["gross_pts"].to_numpy() - COST, g["session"].values)
    rec(f"B4e_COMP2_close_m0_sigter{k}", f"COMP2 close senza filtro, terzile {k} di sigma in punti: unita' vol e netto punti", s1,
        net_mean=s2["mean"], net_lo=s2["lo"], net_hi=s2["hi"], sigma_med=float(g["sigma"].median()),
        years=pd.DatetimeIndex(g["session"]).year.value_counts().sort_index().to_dict())
    print(f"terzile {k}: sigma~{g['sigma'].median():.1f} vol={s1['mean']:+.4f} [{s1['lo']:+.3f};{s1['hi']:+.3f}] "
          f"net={s2['mean']:+.2f} [{s2['lo']:+.2f};{s2['hi']:+.2f}] anni={pd.DatetimeIndex(g['session']).year.value_counts().sort_index().to_dict()}")
