"""H04: approfondimento di "VIX9D/VIX basso -> deriva RTH positiva" (spunto da H01/H03, quindi gia' selezionato:
ogni numero qui e' condizionato a quella scelta). Punti NQ, 09:30 -> 16:00, ingresso all'apertura.
Controlli: soglie, regime di vol realizzata (HAR), VXN basso, placebo del segnale ritardato, lato opposto,
netto e beta (deriva RTH media del campione), anni, senza i 20 migliori, unita' in %."""
from __future__ import annotations

import numpy as np
import pandas as pd

from lab import core
from lab.r4_implied import common as C


def main():
    f = C.load_features()
    rth = f["rth_close"] - f["rth_open"]
    rth_pct = rth / f["raw_open"] * 100
    drift = rth.mean(); drift_pct = rth_pct.mean()
    print(f"deriva RTH media: {drift:+.3f} punti, {drift_pct:+.4f} %")
    rk9 = C.prank(f["ts_9d_s"])
    rkh = C.prank(f["har"])
    rkv = C.prank(f["vxn_s"])
    rk3 = C.prank(f["ts_3m_s"])

    def go(tid, desc, m, unit="pts", side=1.0, **ex):
        m = m.fillna(False) & rth.notna()
        v = (rth if unit == "pts" else rth_pct)[m] * side
        base = (drift if unit == "pts" else drift_pct) * side
        net = v - (core.COST_RT_POINTS if unit == "pts" else 0.0)
        st = C.rec(tid, desc, net.to_numpy(), v.index.values, unit=unit,
                   beta_adj_mean=float((net - base).mean()), **ex)
        stb = core.day_block_bootstrap((net - base).to_numpy(), v.index.values)
        print(C.fmt(tid, st), f"| netto-beta {stb['mean']:+.3f} p_pos={stb['p_pos']:.4f}")
        return st

    for q in (0.1, 0.2, 0.3, 0.4, 0.5):
        go(f"H04_ts9d_bot{q}_net", f"long RTH se rank250(VIX9D/VIX) <= {q}; punti netti", rk9 <= q, q=q)
    for q in (0.2,):
        go(f"H04_ts9d_top{q}_short_net", "short RTH se rank >= 0.8; punti netti (specchio)", rk9 >= 1 - q, side=-1.0)
    go("H04_ts9d_bot0.2_pct", "long RTH se rank <= 0.2; lordo in % (unita' scale-free)", rk9 <= 0.2, unit="pct")
    for th in (0.85, 0.90, 0.95):
        go(f"H04_ts9d_raw_lt{th}", f"long RTH se VIX9D/VIX < {th} (soglia assoluta); punti netti", f["ts_9d_s"] < th, th=th)
    # vol realizzata prevista bassa (HAR) e VXN basso: e' lo stesso effetto?
    go("H04_harlow_net", "long RTH se rank250(HAR previsto) <= 0.2; punti netti", rkh <= 0.2)
    go("H04_vxnlow_net", "long RTH se rank250(VXN) <= 0.2; punti netti", rkv <= 0.2)
    go("H04_ts3m_bot_net", "long RTH se rank250(VIX/VIX3M) <= 0.2; punti netti", rk3 <= 0.2)
    for lab_, cond in [("harlow", rkh <= 0.33), ("harmid", (rkh > 0.33) & (rkh <= 0.67)), ("harhigh", rkh > 0.67)]:
        go(f"H04_ts9d_bot_in_{lab_}", f"long RTH se rank VIX9D/VIX <= 0.2 dentro il terzile HAR {lab_}", (rk9 <= 0.2) & cond)
        go(f"H04_ts9d_notbot_in_{lab_}", f"long RTH se rank VIX9D/VIX > 0.2 dentro il terzile HAR {lab_} (confronto)", (rk9 > 0.2) & cond)
    # placebo: segnale ritardato di k sessioni (se l'effetto e' un regime lento, sopravvive; se e' informazione fresca, no)
    for k in (5, 20, 60):
        go(f"H04_ts9d_bot_lag{k}", f"placebo: long RTH se rank VIX9D/VIX di {k} sessioni prima <= 0.2", rk9.shift(k) <= 0.2, lag=k)
    # regressione: rendimento RTH % su rank9 controllando rank HAR, rank VXN
    import statsmodels.api as sm
    d = pd.DataFrame({"y": rth_pct, "r9": rk9, "rh": rkh, "rv": rkv, "r3": rk3}).dropna()
    X = sm.add_constant(d[["r9", "rh", "rv", "r3"]])
    res = sm.OLS(d["y"], X).fit(cov_type="HAC", cov_kwds={"maxlags": 5})
    print(res.summary().tables[1])
    core.record(C.FAM, "H04_ols_rth_on_ranks", "OLS rendimento RTH % su rank(VIX9D/VIX), rank(HAR), rank(VXN), rank(VIX/VIX3M), HAC",
                "discovery", {"n": int(res.nobs), "coef_r9": float(res.params["r9"]), "t_r9": float(res.tvalues["r9"]),
                              "coef_rh": float(res.params["rh"]), "t_rh": float(res.tvalues["rh"]),
                              "coef_rv": float(res.params["rv"]), "t_rv": float(res.tvalues["rv"])})


if __name__ == "__main__":
    main()
