"""Backtest + report OOS, versionato per tag. Nessuna rete. Ogni sguardo all'OOS va registrato in oos_looks.md.
Uso: .venv\\Scripts\\python scripts\\07_backtest_report.py [--tag TAG] [--compare-with TAG_A]"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.metrics import brier_score_loss, roc_auc_score

from nqml.backtest.engine import simulate_one_position
from nqml.backtest.metrics import block_bootstrap_ci, diff_mean_r_stat, fold_sign_consistency, mean_r_stat, per_day_table, summarize
from nqml.backtest.stress import revalue, stress_scenarios, stress_table
from nqml.config import load_config
from nqml.features.build import feature_set
from nqml.model.walkforward import assert_no_vault, make_folds, trading_dates
from nqml.report.compare import paired_brier_ci
from nqml.report.render import render_report, save_figures

STRATS = {"A": "take_A", "B0": "take_B0", "C": "take_C", "Copt": "take_Copt"}


def _sample_fraction(cfg: dict) -> float:
    """Quota effettiva del campionamento 1b-S (spec §12-bis), dallo stesso file usato da 08 per pianificare."""
    sampled = pd.read_parquet(Path(cfg["tick"]["tick_dir"]) / "sampled_days.parquet")
    return float(sampled.groupby("month")["n_selected_in_month"].first().sum() / sampled.groupby("month")["n_valid_in_month"].first().sum())


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    cfg = load_config("config.yaml")
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default=cfg["features"]["version"])
    ap.add_argument("--compare-with", default=None)
    ap.add_argument("--notes", default=None, help="markdown inserito verbatim come sezione 'Note sulla milestone'")
    args = ap.parse_args()
    tag = args.tag

    t0 = time.time()
    model_dir = Path(cfg["model"]["model_dir"])
    pred = pd.read_parquet(model_dir / f"predictions_{tag}.parquet")
    sanity_json = json.load(open(model_dir / f"sanity_{tag}.json", encoding="utf-8"))
    version = sanity_json["version"]
    ALL = feature_set(version)["all"]
    feats = pd.read_parquet(Path(cfg["features"]["features_dir"]) / f"features_{feature_set(version)['file']}.parquet")
    pred = pred.merge(feats[["event_id"] + [c for c in ALL if c not in pred.columns]], on="event_id", how="left")
    assert_no_vault(pred, cfg)
    sanity = sanity_json["folds"]
    days = pd.read_parquet(Path(cfg["data"]["events_dir"]) / "days.parquet")
    folds = make_folds(trading_dates(days, cfg), cfg)
    test_days = [d for d in trading_dates(days, cfg) if any(f.test_start <= d <= f.test_end for f in folds)]
    n_days = len(test_days)
    pv = cfg["instrument"]["point_value_usd"]
    bn, bs = cfg["backtest"]["bootstrap_n"], cfg["backtest"]["bootstrap_seed"]

    sims = {k: simulate_one_position(pred, col) for k, col in STRATS.items()}
    taken = {k: s[s["status"] == "taken"] for k, s in sims.items()}
    engine_counts = {k: s["status"].value_counts().to_dict() for k, s in sims.items()}
    summary = {k: summarize(t, n_days, pv, days=test_days) for k, t in taken.items()}
    tab = per_day_table(taken, test_days)
    ci = {k: block_bootstrap_ci(tab, mean_r_stat(k), bn, bs) for k in STRATS}
    diffs = {k: {"point": mean_r_stat("A")(tab) - mean_r_stat(k)(tab), "ci": block_bootstrap_ci(tab, diff_mean_r_stat("A", k), bn, bs)}
             for k in ("B0", "C", "Copt")}
    fold_signs = fold_sign_consistency(pred, "take_A", "take_B0")
    st = stress_table(taken["A"], n_days, cfg, days=test_days)
    slip2 = float(st.loc[st["name"] == "slip_2", "mean_R"].iloc[0])

    # C1: prior geometrico p_rw = 1/(1+rr_ratio), persistito da 06 — verifichiamo, non lo sovrascriviamo (Minor 8).
    expected_p_rw = 1.0 / (1.0 + pred["rr_ratio"])
    assert np.allclose(pred["p_rw"].to_numpy(), expected_p_rw.to_numpy(), atol=1e-12), \
        "p_rw persistito da 06 non coincide con 1/(1+rr_ratio): guardia Minor 8 fallita"
    prior_by_fold = {}
    for k, g in pred.groupby("fold"):
        prior_by_fold[int(k)] = dict(
            auc_A=float(roc_auc_score(g["label"], g["p"])), brier_A=float(brier_score_loss(g["label"], g["p"])),
            auc_rw=float(roc_auc_score(g["label"], g["p_rw"])), brier_rw=float(brier_score_loss(g["label"], g["p_rw"])),
        )
    auc_A_pooled = float(roc_auc_score(pred["label"], pred["p"]))
    brier_A_pooled = float(brier_score_loss(pred["label"], pred["p"]))
    auc_rw_pooled = float(roc_auc_score(pred["label"], pred["p_rw"]))
    brier_rw_pooled = float(brier_score_loss(pred["label"], pred["p_rw"]))
    base_rate = float(pred["label"].mean())
    brier_base_pooled = float(brier_score_loss(pred["label"], np.full(len(pred), base_rate)))
    brier_folds_A_better = sum(1 for s in sanity if s["brier_A"] < s["brier_context"])
    prior = dict(pooled=dict(auc_A=auc_A_pooled, brier_A=brier_A_pooled, auc_rw=auc_rw_pooled, brier_rw=brier_rw_pooled,
                              brier_base=brier_base_pooled), by_fold=prior_by_fold)

    pred["p_bin"] = pd.qcut(pred["p"], 10, labels=False, duplicates="drop")
    calib = [[int(b), float(g["p"].mean()), float(g["label"].mean()), int(len(g))] for b, g in pred.groupby("p_bin")]
    tA = taken["A"].copy()
    tA["va_type"] = tA["va_type"].map({0: "ON", 1: "DEV"})
    hour = pd.DatetimeIndex(tA["entry_ts"]).tz_convert("America/New_York")
    tA["fascia"] = pd.cut(hour.hour * 60 + hour.minute, [0, 630, 720, 840, 930, 1440], labels=["09:30-10:30", "10:30-12:00", "12:00-14:00", "14:00-15:30", "altro"])
    decomposition = {}
    for name in ("va_type", "side", "fascia"):
        g = tA.groupby(name, observed=True)["realized_R"]
        decomposition[name] = [[str(k), int(v.size), float((v > 0).mean()), float(v.mean())] for k, v in g]

    boosters = {s["fold"]: lgb.Booster(model_file=str(model_dir / f"models_{tag}" / f"fold_{s['fold']}.txt")) for s in sanity}
    features_by_fold = {s["fold"]: s["features_A"] for s in sanity}
    # spec §11.1 «dalla 1b»: bootstrap appaiato per evento di Brier(A) − Brier(contesto), CI che esclude 0 (Important 2).
    brier_A_vs_context = paired_brier_ci(pred, "p", "p_context", bn, bs)
    res = dict(
        tag=tag, version=version,
        mean_R_A=summary["A"]["mean_R"], ci_A=ci["A"], mean_R_A_slip2=slip2, n_A=summary["A"]["n"],
        diff_ci={k: v["ci"] for k, v in diffs.items()}, fold_signs=fold_signs,
        shuffle_aucs=[s["auc_shuffle"] for s in sanity], brier_A_mean=float(np.mean([s["brier_A"] for s in sanity])),
        brier_context_mean=float(np.mean([s["brier_context"] for s in sanity])), brier_A_vs_context=brier_A_vs_context,
        summary=summary, ci=ci, diffs=diffs, stress=st, sanity=sanity, calib=calib, decomposition=decomposition,
        features_by_fold=features_by_fold, folds={f.k: f"{f.test_start}..{f.test_end}" for f in folds},
        engine_counts=engine_counts, n_days=n_days,
        prior=prior, brier_A_pooled=brier_A_pooled, brier_rw_pooled=brier_rw_pooled, auc_A_pooled=auc_A_pooled,
        auc_rw_pooled=auc_rw_pooled, brier_base_pooled=brier_base_pooled, brier_folds_A_better=brier_folds_A_better,
    )
    if "p_l2" in pred.columns:
        # 1c (spec §12-ter): prior calibrato L2 sul solo fit_df, persistito da 06 — confronto descrittivo nel report.
        res["brier_l2_pooled"] = float(brier_score_loss(pred["label"], pred["p_l2"]))
    if feature_set(version)["has_orderflow"] and version.startswith("1c"):
        # M3d/M3e (§12-ter riga D): su un sottoinsieme campionato le feature order-flow esistono solo sui giorni S,
        # quindi la soglia dei trade e' 300 * quota (non 300) e va segnalata la diluizione delle tick sul test.
        frac_of = _sample_fraction(cfg)
        res["trade_threshold"] = 300 * frac_of
        res["trade_threshold_fraction"] = frac_of
        res["tick_nan_test"] = int(pred["delta_excursion"].isna().sum())
        res["n_test_total"] = int(len(pred))
    if sanity_json.get("subset"):
        # anche l'esecuzione 1a_S (senza --compare-with) è su un sottoinsieme campionato: la nota di diluizione
        # deve comparire anche nel suo report (Important 4 / Task 11).
        res["fraction"] = _sample_fraction(cfg)
    if args.notes:
        res["notes_md"] = Path(args.notes).read_text(encoding="utf-8")

    if args.compare_with:
        from nqml.report.compare import decision_overlap, evaluate_paired_criteria, paired_frame, paired_mean_r, render_comparison
        pred_a = pd.read_parquet(model_dir / f"predictions_{args.compare_with}.parquet")
        pf = paired_frame(pred_a, pred)
        fraction = _sample_fraction(cfg)
        by_fold = []
        for k, g in pf.groupby("fold"):
            by_fold.append(dict(fold=int(k), auc_a=float(roc_auc_score(g["label"], g["p_a"])), auc_b=float(roc_auc_score(g["label"], g["p_b"])),
                                auc_rw=float(roc_auc_score(g["label"], g["p_rw_b"])), brier_a=float(brier_score_loss(g["label"], g["p_a"])),
                                brier_b=float(brier_score_loss(g["label"], g["p_b"])), brier_rw=float(brier_score_loss(g["label"], g["p_rw_b"]))))
        cmp = dict(brier_b_vs_a=paired_brier_ci(pf, "p_b", "p_a", bn, bs), brier_b_vs_rw=paired_brier_ci(pf, "p_b", "p_rw_b", bn, bs),
                   brier_a_vs_rw=paired_brier_ci(pf, "p_a", "p_rw_a", bn, bs),
                   brier_b_vs_context=paired_brier_ci(pf, "p_b", "p_context_b", bn, bs),
                   brier_a_vs_context=paired_brier_ci(pf, "p_a", "p_context_a", bn, bs),
                   mean_r=paired_mean_r(pf, test_days, bn, bs), overlap=decision_overlap(pf), by_fold=by_fold)
        cmp["criteria"] = evaluate_paired_criteria(cmp, fraction, summary["A"]["n"])
        res["comparison_md"] = render_comparison(cmp, args.compare_with, args.tag)
        res["fraction"] = fraction

    fig_dir = Path(cfg["backtest"]["reports_dir"]) / f"figures_{tag}"
    res["figures"] = [Path(p).as_posix() for p in save_figures(pred, taken, res, boosters, features_by_fold, fig_dir, cfg)]
    md = render_report(res, cfg)
    out = Path(cfg["backtest"]["reports_dir"]) / f"oos_report_{tag}.md"
    out.write_text(md, encoding="utf-8")
    print(md)
    print(f"scritto {out} in {time.time()-t0:.0f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
