"""Test primari di r7_opzioni (PREREG.md), eseguiti UNA volta dopo il commit di questo file e solo se il
Passo 0 non chiude la famiglia (>= 150 venerdì utilizzabili e MDE80 entro l'effetto plausibile).

A: pendenza di r = (|F_T - K| - mid)/mid su s = ln(E|F_T - F0| / mid)   (regolarità, lordo a mid, HAC 4 lag)
B: long straddle all'ask se s̃ > 0, short al bid altrimenti; s̃ = s - mediana di s sui 52 venerdì utilizzabili
   precedenti (almeno 10: nel 2012 la finestra si riempie). Netto in punti; beta = «vendi sempre».
Holm k = 2.

Uso: .venv/Scripts/python.exe -m lab.r7_opzioni.s02_primari
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
import statsmodels.api as sm

from lab import core
from lab.r7_opzioni import common as C

FAM = "r7_opzioni"


def ols_hac(y: np.ndarray, x: np.ndarray) -> tuple[float, float]:
    m = sm.OLS(y, sm.add_constant(x)).fit(cov_type="HAC", cov_kwds={"maxlags": 4})
    return float(m.params[1]), float(m.tvalues[1])


def main() -> None:
    bars, _ = core.load("discovery")
    P = C.build_days(bars, C.load_defs(), C.load_tbbo())
    P = P[(P.index >= pd.Timestamp("2012-01-01")) & np.isfinite(P["f_t"])].copy()
    P["fc"] = C.forecasts(P.index)
    P = P[np.isfinite(P["fc"])]
    P["s"] = np.log(P["fc"] / P["mid"])
    payoff = (P["f_t"] - P["k"]).abs()
    P["r"] = (payoff - P["mid"]) / P["mid"]
    n = len(P)
    print("venerdì nel test:", n)

    # A
    b, tv = ols_hac(P["r"].to_numpy(), P["s"].to_numpy())
    from scipy.stats import norm
    pA = float(1 - norm.cdf(tv))
    h1 = P[P.index < pd.Timestamp("2016-01-01")]
    h2 = P[P.index >= pd.Timestamp("2016-01-01")]
    halves = [ols_hac(h["r"].to_numpy(), h["s"].to_numpy()) for h in (h1, h2)]
    rng = np.random.default_rng(0)
    yrs = P.index.year.to_numpy()
    sims = []
    for _ in range(1000):
        s_perm = P["s"].to_numpy().copy()
        for yy in np.unique(yrs):
            m = yrs == yy
            s_perm[m] = rng.permutation(s_perm[m])
        sims.append(ols_hac(P["r"].to_numpy(), s_perm)[0])
    pct = float((np.array(sims) < b).mean() * 100)

    # B
    s_hist = P["s"]
    med = s_hist.shift(1).rolling(52, min_periods=10).median()
    P["s_t"] = P["s"] - med
    Bd = P[np.isfinite(P["s_t"])].copy()
    long_ = Bd["s_t"] > 0
    pay = (Bd["f_t"] - Bd["k"]).abs()
    cost_long = Bd["C_ask"] + Bd["P_ask"]
    cost_short = Bd["C_bid"] + Bd["P_bid"]
    Bd["net"] = np.where(long_, pay - cost_long, cost_short - pay) - C.FEE_PTS
    Bd["short_always"] = cost_short - pay - C.FEE_PTS
    stB = core.day_block_bootstrap(Bd["net"].to_numpy(), Bd.index)
    stBeta = core.day_block_bootstrap((Bd["net"] - Bd["short_always"]).to_numpy(), Bd.index)
    yB = core.yearly(Bd["net"].to_numpy(), Bd.index)
    dropB = core.drop_top(Bd["net"].to_numpy(), 20)

    # Holm k = 2
    ps = sorted([(pA, "A"), (stB["p_pos"], "B")])
    holm, run = {}, 0.0
    for i, (p, k) in enumerate(ps):
        run = max(run, min(1.0, (2 - i) * p))
        holm[k] = run
    alphaB = 0.05  # soglia sul p di Holm
    critA = {"holm": holm["A"] < 0.05, "meta": all(np.sign(x[0]) == np.sign(b) and x[1] * np.sign(b) >= 1 for x in halves),
             "placebo95": pct >= 95}
    critB = {"c1_netto": stB["mean"] > 0 and holm["B"] < alphaB,
             "c2_beta": stBeta["mean"] > 0 and min(1.0, 2 * stBeta["p_pos"]) < alphaB,
             "c3_anni": int((yB["mean"] > 0).sum()) >= 4,
             "c4_droptop": dropB > 0}
    passA, passB = all(critA.values()), all(critB.values())
    print(f"A: pendenza {b:.4f} (t HAC {tv:.2f}), p {pA:.4f}, Holm {holm['A']:.4f}; metà {halves}; "
          f"placebo percentile {pct:.1f} -> {'PASS' if passA else 'FAIL'}")
    print(f"B: netto {stB['mean']:.3f} punti [{stB['lo']:.3f}; {stB['hi']:.3f}], p {stB['p_pos']:.4f}, Holm {holm['B']:.4f}; "
          f"contro «vendi sempre» {stBeta['mean']:.3f} (p {stBeta['p_pos']:.4f}); vendi sempre da solo "
          f"{Bd['short_always'].mean():.3f}; long {int(long_.sum())}/{len(Bd)}; anni {yB['mean'].round(2).to_dict()}; "
          f"senza i 20 migliori {dropB:.3f} -> {'PASS' if passB else 'FAIL'}")
    core.record(FAM, "primary_A", "pendenza del rendimento dello straddle su s (HAC 4 lag)", "discovery",
                {"n": n, "slope": b, "t": tv, "p": pA, "holm": holm["A"], "placebo_pct": pct},
                halves=halves, crit=critA, verdict="PASS" if passA else "FAIL")
    core.record(FAM, "primary_B", "long/short straddle su s̃, netto in punti", "discovery",
                {k: stB[k] for k in ("n", "n_days", "mean", "lo", "hi", "p_two", "p_pos")},
                holm=holm["B"], beta_adj=stBeta, short_always_mean=float(Bd["short_always"].mean()),
                years=yB["mean"].round(4).to_dict(), drop_top20=dropB, crit=critB, verdict="PASS" if passB else "FAIL")
    out = {"n": n, "A": {"slope": b, "t": tv, "p": pA, "holm": holm["A"], "halves": halves, "placebo_pct": pct,
                         "crit": critA, "pass": passA},
           "B": {"stat": stB, "beta_adj": stBeta, "short_always": float(Bd["short_always"].mean()),
                 "years": yB["mean"].to_dict(), "drop_top20": dropB, "crit": critB, "pass": passB}}
    (core.ROOT / "lab" / FAM / "results.json").write_text(json.dumps(out, indent=1, default=float), encoding="utf-8")


if __name__ == "__main__":
    main()
