"""r6_gamma: il GEX della sera prima classifica la giornata RTH? Test primari A, B, C (PREREG). Solo discovery.

Definizioni operative fissate qui, prima dell'esecuzione:
- 78 rendimenti log a 5 minuti RTH: dall'open della barra 09:30 ai close delle barre che chiudono a :35 ... 16:00
  (prezzi adj, barra mancante = ultimo close noto).
- VR6 di Lo-MacKinlay (sovrapposto, correzione per campioni finiti):
  s_a^2 = sum(r-mu)^2/(T-1);  s_c^2 = sum_k (somma di 6 rendimenti - 6mu)^2 / m,  m = 6(T-6+1)(1-6/T);
  VR6 = s_c^2 / s_a^2 (m contiene gia' il fattore 6).
- RV = somma dei quadrati dei rendimenti a 5 minuti; controllo ln RV_(t-1) = ln(media delle 5 RV precedenti).
- controlli: ln VXN noto all'apertura (valore di t-1), ln RV_(t-1), VR6_(t-1); GEX noto all'apertura (valore di t-1).
- B: rango percentile del GEX fra i 250 valori precedenti (serve una storia completa di 250 sessioni).
- p unilaterali nel verso di H1 (A: b > 0; B: coefficiente < 0; C: b > 0), OLS con Newey-West a 5 lag.
- differenza fra regimi: A -> b; B -> |coefficiente| (distanza fra rango 0 e rango 1). Soglia 0,10.
- placebo: GEX permutato fra sessioni dello stesso anno (1.000 volte), stessa regressione; per B si permuta il
  rango (equivalente, e non richiede di ricostruire i ranghi mobili); p = quota >= reale nel verso di H1.
"""
import json

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats

from lab import core, extdata, r6_common as RC

FAM = "r6_gamma"
N_PERM = 1000
Q = 6


def rth_matrix(bars, d):
    b = bars[bars["rth"] & bars["session"].isin(d.index.values)]
    col = b["ny_min"].to_numpy() - 570
    si = pd.Index(d.index).get_indexer(pd.DatetimeIndex(b["session"].to_numpy()))
    C = np.full((len(d), 390), np.nan)
    C[si, col] = b["adj_close"].to_numpy()
    O = np.full(len(d), np.nan)
    first = b[b["ny_min"] == 570]
    O[pd.Index(d.index).get_indexer(pd.DatetimeIndex(first["session"].to_numpy()))] = first["adj_open"].to_numpy()
    C = pd.DataFrame(C).ffill(axis=1).to_numpy()
    return O, C


def vr(r: np.ndarray, q: int = Q) -> np.ndarray:
    T = r.shape[1]
    mu = r.mean(1, keepdims=True)
    sa = ((r - mu) ** 2).sum(1) / (T - 1)
    cs = np.cumsum(np.c_[np.zeros(len(r)), r], axis=1)
    sq = cs[:, q:] - cs[:, :-q]                        # somme sovrapposte di q rendimenti (T-q+1)
    m = q * (T - q + 1) * (1 - q / T)
    sc = ((sq - q * mu) ** 2).sum(1) / m
    return sc / sa


def ols(y, X, lags=5):
    X = sm.add_constant(X)
    return sm.OLS(y, X).fit(cov_type="HAC", cov_kwds={"maxlags": lags})


def beta_only(y, X):
    X = np.c_[np.ones(len(y)), X]
    return np.linalg.lstsq(X, y, rcond=None)[0][1]


if __name__ == "__main__":
    bars, daily = core.load("discovery", warmup_days=5)
    d = daily[daily["valid"]]
    O, C = rth_matrix(bars, d)
    lc = np.log(C)
    p5 = np.c_[np.log(O), lc[:, 4::5]]                  # 09:30 open, poi close alle 09:35 ... 16:00
    r5 = np.diff(p5, axis=1)
    assert r5.shape[1] == 78
    r1 = np.diff(np.c_[np.log(O), lc], axis=1)
    df = pd.DataFrame(index=d.index)
    df["VR6"] = vr(r5)
    df["AC1"] = [np.corrcoef(x[1:], x[:-1])[0, 1] for x in r1]
    df["RV"] = (r5 ** 2).sum(1)
    df["lnRV_l"] = np.log(df["RV"].rolling(5).mean().shift(1))
    df["VR6_l"] = df["VR6"].shift(1)
    ext = extdata.known_at_open(d.index)
    df["lnVXN"] = np.log(ext["VXN"])
    df["GEX"] = ext["GEX"]
    df["neg"] = (df["GEX"] < 0).astype(float).where(df["GEX"].notna())   # senza GEX: escluso, non «positivo»
    df["rank"] = df["GEX"].rolling(251, min_periods=251).apply(lambda x: (x[:-1] < x[-1]).mean(), raw=True)
    df["in_phase"] = d["in_phase"]
    df["year"] = df.index.year
    ctrl = ["lnVXN", "lnRV_l", "VR6_l"]

    tests = {"A": ("VR6", "neg", +1), "B": ("VR6", "rank", -1), "C": ("AC1", "neg", +1)}
    res, pvals = {}, {}
    rng = np.random.default_rng(3)
    for name, (yv, xv, sgn) in tests.items():
        s = df[df["in_phase"]].dropna(subset=[yv, xv] + ctrl)
        fit = ols(s[yv].to_numpy(), s[[xv] + ctrl].to_numpy())
        b, t = fit.params[1], fit.tvalues[1]
        p = float(stats.norm.sf(sgn * t))
        pvals[name] = p
        halves = {}
        for k in RC.HALVES:
            sh = s[RC.half_of(s.index) == k]
            fh = ols(sh[yv].to_numpy(), sh[[xv] + ctrl].to_numpy())
            halves[k] = {"b": float(fh.params[1]), "t": float(fh.tvalues[1]), "n": len(sh)}
        # placebo: permutazione del GEX dentro l'anno (l'indicatore/rango si ricalcola dalla serie permutata)
        perm = []
        g = s["GEX"].to_numpy()
        yrs = s["year"].to_numpy()
        Xc = s[ctrl].to_numpy()
        for _ in range(N_PERM):
            gp = g.copy()
            for y in np.unique(yrs):
                ix = np.where(yrs == y)[0]
                gp[ix] = g[rng.permutation(ix)]
            if xv == "neg":
                x = (gp < 0).astype(float)
            else:
                x = s[xv].to_numpy().copy()
                for y in np.unique(yrs):
                    ix = np.where(yrs == y)[0]
                    x[ix] = s[xv].to_numpy()[rng.permutation(ix)]
            perm.append(beta_only(s[yv].to_numpy(), np.c_[x, Xc]))
        perm = np.array(perm)
        p_plac = float((1 + np.sum(sgn * perm >= sgn * b)) / (N_PERM + 1))
        res[name] = {"y": yv, "x": xv, "H1_sign": sgn, "b": float(b), "t": float(t), "p_one": p, "n": len(s),
                     "halves": halves, "placebo_p": p_plac,
                     "placebo_pct": np.percentile(perm, [5, 50, 95]).round(4).tolist()}
        core.record(FAM, name, f"{yv} ~ {xv} + controlli (Newey-West 5), primario", "discovery",
                    {"b": float(b), "t": float(t), "p_one": p, "n": len(s)}, halves=halves, placebo_p=p_plac)
    ph = RC.holm(pvals)
    for k in res:
        res[k]["p_holm"] = ph[k]
    passes = {}
    for k in ("A", "B"):
        r = res[k]
        sgn = r["H1_sign"]
        diff = r["b"] if k == "A" else abs(r["b"])
        passes[k] = {"holm": r["p_holm"] < 0.05,
                     "same_sign_t1_halves": all(sgn * r["halves"][h]["t"] >= 1 for h in RC.HALVES),
                     "placebo95": r["placebo_p"] <= 0.05,
                     "regime_diff_ge_0.10": (sgn * r["b"] > 0) and diff >= 0.10}
    res["GO_checks"] = passes
    res["GO"] = any(all(v.values()) for v in passes.values())
    # descrittivo: VR6 medio per terzile di GEX x terzile di VXN
    s = df[df["in_phase"]].dropna(subset=["VR6", "GEX", "lnVXN"])
    tab = s.groupby([pd.qcut(s["GEX"], 3, labels=["GEX basso", "GEX medio", "GEX alto"]),
                     pd.qcut(s["lnVXN"], 3, labels=["VXN basso", "VXN medio", "VXN alto"])], observed=True)["VR6"].mean()
    res["descr_VR6_terzili"] = tab.unstack().round(3).to_dict()
    res["descr_VR6_mean"] = float(s["VR6"].mean())
    print(json.dumps(res, indent=1, default=str))
    (core.ROOT / "lab" / FAM / "results.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
