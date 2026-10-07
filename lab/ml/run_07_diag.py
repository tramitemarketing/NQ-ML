"""Diagnostica: (a) controllo positivo di leakage, (b) placebo target permutato per giorni,
(c) scomposizione IC fra-giorni / dentro-giorno, (d) ablazione feature lente, (e) IC per terzile di vol."""
import numpy as np, pandas as pd
from lab import core
from lab.ml.common import dataset, walk_forward, fit_lgb, ic_boot, _spearman, CACHE
from lab.ml.features import FEATURES
ds = dataset()
yrs = pd.DatetimeIndex(ds.session).year
p30 = pd.read_parquet(CACHE / "preds_h30.parquet")["M1"]
p60 = pd.read_parquet(CACHE / "preds_hor.parquet")["M1_60"]

# (a) controllo positivo: feature che vede il primo minuto del target
leak = ds.copy()
leak["LEAK"] = (leak["pts30"] * 0.1 + np.random.default_rng(0).normal(0, 1, len(leak)) * leak["pts30"].std()) / leak["sig1m"]
pl, _ = walk_forward(leak, fit_lgb, "y30", feats=FEATURES + ["LEAK"])
ev = leak[yrs >= 2012]
r = ic_boot(pl[ev.index], ev.y30, ev.session, n_boot=500)
print("controllo positivo (feature con 10% del target):", r)
core.record("ml", "ml_diag_poscontrol", "Controllo positivo: feature LEAK = 0,1*target + rumore; il WF deve vederla", "discovery", dict(r, n=r["ic_n"]))

# (b) placebo: target permutato a blocchi di giorno (giorni riassegnati a caso)
pla = ds.copy()
sess = pla.session.unique()
rng = np.random.default_rng(1)
perm = dict(zip(sess, rng.permutation(sess)))
key = pla.set_index(["session", "slot"])["y30"]
pla["y30"] = [key.get((perm[s], sl), np.nan) for s, sl in zip(pla.session, pla.slot)]
pp, _ = walk_forward(pla, fit_lgb, "y30")
ev = pla[yrs >= 2012]
r = ic_boot(pp[ev.index], ev.y30, ev.session, n_boot=500)
print("placebo target permutato:", r)
core.record("ml", "ml_diag_placebo", "Placebo: y30 permutato fra giorni (stesso slot); il WF deve dare IC ~0", "discovery", dict(r, n=r["ic_n"]))

# (c) scomposizione
for h, p in ((30, p30), (60, p60)):
    ev = ds[(yrs >= 2012) & np.isfinite(ds[f"y{h}"])].copy()
    ev["p"] = p[ev.index]
    dm = ev.groupby("session")[["p", f"y{h}"]].mean()
    between = ic_boot(dm["p"], dm[f"y{h}"], dm.index, n_boot=1000)
    ev["pw"] = ev["p"] - ev.groupby("session")["p"].transform("mean")
    ev["yw"] = ev[f"y{h}"] - ev.groupby("session")[f"y{h}"].transform("mean")
    within = ic_boot(ev["pw"], ev["yw"], ev.session, n_boot=1000)
    print(f"h{h} fra-giorni IC {between['ic']:+.4f} [{between['ic_lo']:+.4f};{between['ic_hi']:+.4f}]  dentro-giorno IC {within['ic']:+.4f} [{within['ic_lo']:+.4f};{within['ic_hi']:+.4f}]")
    core.record("ml", f"ml_diag_decomp_h{h}", f"Scomposizione IC M1 h{h}: fra giorni (medie giornaliere) e dentro il giorno (demediato)", "discovery",
                dict(n=within["ic_n"], ic_between=between["ic"], ic_between_lo=between["ic_lo"], ic_between_hi=between["ic_hi"],
                     ic_within=within["ic"], ic_within_lo=within["ic_lo"], ic_within_hi=within["ic_hi"]))
    # (e) per terzile di sig_level (vol in bp) -- terzili fissati sul training? qui descrittivo sul periodo WF
    ev["vt"] = pd.qcut(ev["sig_level"], 3, labels=["bassa", "media", "alta"])
    out = {}
    for g, e in ev.groupby("vt"):
        out[str(g)] = round(_spearman(e["p"], e[f"y{h}"]), 4)
    print(f"h{h} IC per terzile di volatilita':", out)
    core.record("ml", f"ml_diag_voltercile_h{h}", f"IC M1 h{h} per terzile di sig_level (descrittivo)", "discovery", dict(n=len(ev), ic_by_tercile=out))

# (d) ablazione: senza feature lente (multi-giorno / regime)
slow = ["r_5d", "r_20d", "vol_regime", "sig_level", "r_yday", "r_yday_cc", "dist_yclose", "pos_yday", "r_on"]
fast = [f for f in FEATURES if f not in slow]
for name, fs in (("solo_veloci", fast), ("solo_lente", slow + ["tod", "dow"])):
    pa, _ = walk_forward(ds, fit_lgb, "y60", feats=fs)
    ev = ds[(yrs >= 2012) & np.isfinite(ds.y60)]
    r = ic_boot(pa[ev.index], ev.y60, ev.session, n_boot=1000)
    print(f"ablazione h60 {name}: IC {r['ic']:+.4f} [{r['ic_lo']:+.4f};{r['ic_hi']:+.4f}] p={r['ic_p_two']:.3f}")
    core.record("ml", f"ml_diag_ablation_{name}_h60", f"Ablazione LGB WF y60 con feature {name}: {fs}", "discovery", dict(r, n=r["ic_n"]))
