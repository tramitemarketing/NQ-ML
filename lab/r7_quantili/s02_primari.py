"""Test primari di r7_quantili (PREREG.md), eseguiti UNA volta dopo il commit di questo file.

A: M1 (QuantReg lineare) contro B0;  B: M2 (LightGBM quantile) contro B0.  Holm k = 2, solo discovery.
Più i controlli e i descrittivi del PREREG (placebo sul calendario, copertura, larghezza delle bande).

Uso: .venv/Scripts/python.exe -m lab.r7_quantili.s02_primari [--placebo 200]
"""
from __future__ import annotations

import argparse
import json
import warnings

import numpy as np
import pandas as pd
from lightgbm import LGBMRegressor
from statsmodels.regression.quantile_regression import QuantReg

from lab import core
from lab.r7_quantili import common as C

FAM = "r7_quantili"
assert C.FEATS == ["l1", "m5", "m22", "lon", "lvxn", "fomc", "cpi", "nfp", "monday"]


def m1(train: pd.DataFrame, test: pd.DataFrame) -> np.ndarray:
    X = np.column_stack([np.ones(len(train)), train[C.FEATS].to_numpy()])
    Xt = np.column_stack([np.ones(len(test)), test[C.FEATS].to_numpy()])
    out = []
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for q in C.QS:
            b = QuantReg(train["y"].to_numpy(), X).fit(q=q, max_iter=5000).params
            out.append(Xt @ b)
    return np.column_stack(out)


def m2(train: pd.DataFrame, test: pd.DataFrame) -> np.ndarray:
    out = []
    for q in C.QS:
        m = LGBMRegressor(objective="quantile", alpha=float(q), num_leaves=7, learning_rate=0.03, n_estimators=300,
                          min_child_samples=50, subsample=0.8, subsample_freq=1, colsample_bytree=1.0,
                          random_state=0, verbose=-1)        # niente vincoli monotoni: addendum 1
        m.fit(train[C.FEATS], train["y"])
        out.append(m.predict(test[C.FEATS]))
    return np.column_stack(out)


def shuffle_events(t: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    """Placebo: ogni data di evento spostata a una sessione valida a caso dello stesso mese."""
    t = t.copy()
    month = t.index.to_period("M")
    for c in ("fomc", "cpi", "nfp"):
        new = np.zeros(len(t))
        for per, idx in pd.Series(np.arange(len(t)), index=month).groupby(level=0):
            k = int(t[c].to_numpy()[idx.to_numpy()].sum())
            if k:
                new[rng.choice(idx.to_numpy(), size=k, replace=False)] = 1
        t[c] = new
    return t


def coverage(y: np.ndarray, q: np.ndarray) -> np.ndarray:
    return (y[:, None] <= q).mean(axis=0)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--placebo", type=int, default=200)
    a = ap.parse_args()
    t = C.table("discovery")
    q0 = C.walk_forward(t, C.b0)
    y = t.loc[q0.index, "y"].to_numpy()
    days = q0.index
    l0 = C.pinball(y, q0.to_numpy())
    ev = (t.loc[days, ["fomc", "cpi", "nfp"]].sum(axis=1) > 0).to_numpy()
    res = {}
    for name, model in (("M1", m1), ("M2", m2)):
        q = C.walk_forward(t, model)
        d = l0 - C.pinball(y, q.to_numpy())
        st = core.day_block_bootstrap(d, days)
        yr = pd.Series(d, index=days).groupby(days.year).mean()
        halves = (float(d[days < pd.Timestamp("2016-01-01")].mean()), float(d[days >= pd.Timestamp("2016-01-01")].mean()))
        cov = coverage(y, q.to_numpy())
        cov0 = coverage(y, q0.to_numpy())
        cov95_ev, cov95_ev0 = float((y[ev] <= q.to_numpy()[ev, -1]).mean()), float((y[ev] <= q0.to_numpy()[ev, -1]).mean())
        w = q.to_numpy()[:, -1] - q.to_numpy()[:, 0]
        w0 = q0.to_numpy()[:, -1] - q0.to_numpy()[:, 0]
        res[name] = {"stat": st, "years": yr.round(6).to_dict(), "halves": halves,
                     "rel": float(d.mean() / l0.mean()), "cov": dict(zip(C.QS.round(2).tolist(), cov.round(4).tolist())),
                     "cov_b0": dict(zip(C.QS.round(2).tolist(), cov0.round(4).tolist())),
                     "cov95_event": cov95_ev, "cov95_event_b0": cov95_ev0,
                     "width_event": float(w[ev].mean()), "width_noevent": float(w[~ev].mean()),
                     "width_event_b0": float(w0[ev].mean()), "width_noevent_b0": float(w0[~ev].mean()),
                     "d": d, "q": q.to_numpy()}
    # Holm k = 2 sui p unilaterali
    ps = sorted((res[k]["stat"]["p_pos"], k) for k in res)
    holm = {}
    run = 0.0
    for i, (p, k) in enumerate(ps):
        run = max(run, min(1.0, (2 - i) * p))
        holm[k] = run
    verdicts = {}
    for k, r in res.items():
        yrs_pos = sum(v > 0 for v in r["years"].values())
        crit = {"c1_holm": holm[k] < 0.05,
                "c2_anni_meta": yrs_pos >= 4 and min(r["halves"]) > 0,
                "c3_rel_2pct": r["rel"] >= 0.02,
                "c4_calibrazione": all(abs(r["cov"][float(round(qq, 2))] - qq) <= 0.025 for qq in C.QS),
                "c5_eventi": r["cov95_event"] >= r["cov95_event_b0"]}
        verdicts[k] = {"crit": crit, "pass": all(crit.values()), "holm": holm[k], "years_pos": yrs_pos}
        s = r["stat"]
        core.record(FAM, f"primary_{'A' if k == 'M1' else 'B'}_{k}",
                    f"{k} contro B0, pinball media su 7 quantili, walk-forward 2013-2018", "discovery",
                    {kk: s[kk] for kk in ("n", "n_days", "mean", "lo", "hi", "p_two", "p_pos")},
                    holm=holm[k], rel=r["rel"], years=r["years"], halves=r["halves"], cov=r["cov"],
                    cov95_event=r["cov95_event"], cov95_event_b0=r["cov95_event_b0"], crit=crit,
                    verdict="PASS" if verdicts[k]["pass"] else "FAIL")
        print(f"\n== {k}: d medio {s['mean']:.5f} [{s['lo']:.5f}; {s['hi']:.5f}], p {s['p_pos']:.4f}, Holm {holm[k]:.4f}, "
              f"relativo {100 * r['rel']:.2f} %")
        print(f"   anni {r['years']}; metà {r['halves']}")
        print(f"   copertura {r['cov']}")
        print(f"   copertura B0 {r['cov_b0']}")
        print(f"   q95 nei giorni di evento: {r['cov95_event']:.3f} (B0 {r['cov95_event_b0']:.3f})")
        print(f"   larghezza 5-95: evento {r['width_event']:.3f} / no {r['width_noevent']:.3f} "
              f"(B0 {r['width_event_b0']:.3f} / {r['width_noevent_b0']:.3f})")
        print(f"   criteri {crit} -> {'PASS' if verdicts[k]['pass'] else 'FAIL'}")
        qq = res[k]["q"]
        for c in ("fomc", "cpi", "nfp"):
            m_ = (t.loc[days, c] == 1).to_numpy()
            print(f"   q95 copertura {c} (n {m_.sum()}): {float((y[m_] <= qq[m_, -1]).mean()):.3f} "
                  f"(B0 {float((y[m_] <= q0.to_numpy()[m_, -1]).mean()):.3f})")
    # descrittivo: importanza (gain) delle feature di M2 stimato su tutto il discovery, quantile 0,95
    imp = LGBMRegressor(objective="quantile", alpha=0.95, num_leaves=7, learning_rate=0.03, n_estimators=300,
                        min_child_samples=50, subsample=0.8, subsample_freq=1, colsample_bytree=1.0,
                        random_state=0, verbose=-1, importance_type="gain").fit(t[C.FEATS], t["y"])
    gain = dict(zip(C.FEATS, (imp.feature_importances_ / imp.feature_importances_.sum()).round(4).tolist()))
    print("importanza (gain) M2 q0,95:", gain)
    core.record(FAM, "descr_importanza_M2_q95", "importanza gain delle feature, M2 q0,95, tutto il discovery",
                "discovery", gain)
    # placebo sul calendario (controllo, non promuove nulla)
    rng = np.random.default_rng(0)
    for k, model in (("M1", m1), ("M2", m2)):
        real = float(res[k]["d"].mean())
        sims = []
        for i in range(a.placebo):
            tp = shuffle_events(t, rng)
            qp = C.walk_forward(tp, model)
            sims.append(float((l0 - C.pinball(y, qp.to_numpy())).mean()))
        sims = np.array(sims)
        p = (1 + (sims >= real).sum()) / (1 + len(sims))
        print(f"placebo calendario {k}: reale {real:.5f}, placebo mediana {np.median(sims):.5f}, p {p:.3f}")
        core.record(FAM, f"control_placebo_calendario_{k}", f"{k}: eventi spostati a caso nello stesso mese",
                    "discovery", {"real": real, "placebo_median": float(np.median(sims)), "p": float(p),
                                  "n": len(sims)})
    best = [k for k in verdicts if verdicts[k]["pass"]]
    if best:
        best = max(best, key=lambda k: res[k]["stat"]["mean"])
    print("\ncandidato:", best or "nessuno")
    out = {k: {kk: vv for kk, vv in res[k].items() if kk not in ("d", "q")} | verdicts[k] for k in res}
    out["candidato"] = best or None
    (C.ROOT / "lab" / FAM / "results.json").write_text(json.dumps(out, indent=1, default=float), encoding="utf-8")


if __name__ == "__main__":
    main()
