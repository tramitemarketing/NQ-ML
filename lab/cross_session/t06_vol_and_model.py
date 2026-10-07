"""Batteria 6: (a) varianti della regolarita' di volatilita' fra sessioni; (b) modello lineare
walk-forward con tutti i segmenti precedenti per la direzione RTH e per l'Asia successiva."""
import numpy as np, pandas as pd
from lab import core
from lab.cross_session.build_cache import get
from lab.cross_session.common import evaluate, fmt, FAMILY
from lab.cross_session.series import segments, causal_q

t = get(); S = segments(t); m = t["valid"] & t["in_phase"]; atr = t.atr20

def ratio(r):  # range del segmento rispetto alla sua media delle 20 sessioni precedenti
    return r / r.shift(1).rolling(20, min_periods=10).mean()

def volreg(tid, desc, pred_rng, tgt_rng):
    pr, tr = ratio(pred_rng), ratio(tgt_rng)
    sgn = np.sign(pr - pr.shift(1).rolling(250, min_periods=60).median())
    x = (sgn * (tr - 1)).where(m).dropna()
    st = core.day_block_bootstrap(x.to_numpy(), x.index.to_numpy())
    c = pd.concat([np.log(pr), np.log(tr)], axis=1)[m].replace([np.inf, -np.inf], np.nan).dropna().corr(method="spearman").iloc[0, 1]
    yr = core.yearly(x.to_numpy(), x.index)
    core.record(FAMILY, tid, desc, "discovery", st, spearman=float(c), years_pos=f"{(yr['mean']>0).sum()}/{len(yr)}")
    print(f"{tid:34s} mean={st['mean']:+.4f} [{st['lo']:+.4f};{st['hi']:+.4f}] p2={st['p_two']:.4f} rho={c:.3f} anni+={(yr['mean']>0).sum()}/{len(yr)}")

rng = lambda k: t[k + "_hi"] - t[k + "_lo"]
volreg("V33_asiarange_to_eurrange", "regolarita': range Asia (vs media20) predice range Europa (vs media20)", rng("asia"), rng("eur"))
volreg("V33b_prerange_to_rthrange", "regolarita': range 08:30-09:30 predice range RTH", rng("pre"), rng("rth"))
volreg("V34_postrange_to_nextONrange", "regolarita': range 16-17 predice range notte successiva", rng("post"), rng("on").shift(-1))
volreg("V34b_rthrange_to_nextONrange", "regolarita': range RTH predice range notte successiva", rng("rth"), rng("on").shift(-1))

# (b) modello lineare walk-forward (rifit annuale su tutti gli anni precedenti; primo anno fuori)
def wf(tid, desc, X, y, tgt_pts):
    X = X.replace([np.inf, -np.inf], np.nan); df = pd.concat([X, y.rename("y")], axis=1)
    pred = pd.Series(np.nan, index=df.index)
    years = sorted(set(df.index.year))
    for yv in years[1:]:
        tr = df[(df.index.year < yv) & m.reindex(df.index)].dropna()
        te = df[df.index.year == yv].drop(columns="y").dropna()
        if len(tr) < 200 or len(te) == 0: continue
        A = np.c_[np.ones(len(tr)), tr.drop(columns="y").to_numpy()]
        lam = 5.0 * np.eye(A.shape[1]); lam[0, 0] = 0
        b = np.linalg.solve(A.T @ A + lam, A.T @ tr["y"].to_numpy())
        pred.loc[te.index] = np.c_[np.ones(len(te)), te.to_numpy()] @ b
    side = np.sign(pred)
    r = evaluate(tid, desc, side * tgt_pts, side, tgt_pts, atr, m); print(fmt(tid, r))

X = pd.DataFrame({k: S[k] / atr for k in ["A_sig", "E_sig", "P_sig"]})
X["prevR"] = S["R_sig"].shift(1) / atr; X["prevQ"] = S["Q_sig"].shift(1) / atr
X["on_ratio"] = ratio(rng("on"))
wf("V35_ridge_wf_to_rth", "ridge walk-forward (Asia, Europa, pre, RTH prec, 16-17 prec, range notte) -> segno RTH", X, S["R"] / atr, S["R"])
X2 = pd.DataFrame({"R": S["R_sig"] / atr, "Q": S["Q_sig"] / atr, "A": S["A_sig"] / atr, "E": S["E_sig"] / atr,
                   "rr": ratio(rng("rth"))})
wf("V35b_ridge_wf_to_nextasia", "ridge walk-forward (segmenti della sessione) -> segno Asia successiva", X2, S["nA"] / atr, S["nA"])
