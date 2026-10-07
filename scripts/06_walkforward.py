"""Walk-forward: modello A + baselines + sanity per finestra. Nessuna rete. Cassaforte esclusa.
Uso: .venv\\Scripts\\python scripts\\06_walkforward.py [--version 1a|1b|1c_A|1c_B] [--subset PATH] [--tag NAME] [--seed N]"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import brier_score_loss

from nqml.config import config_hash, git_commit, load_config
from nqml.features.build import feature_set
from nqml.model.baselines import apply_c_opt, fit_c_opt, rule_list
from nqml.model.decision import costs_in_r, ev_r, take
from nqml.model.prior import fit_prior_calibrator, p_l2
from nqml.model.sanity import context_only_predict, model_metrics, shuffle_test_auc, shuffle_test_aucs
from nqml.model.train import fit_fold_model, predict_p, save_model
from nqml.model.walkforward import assert_no_vault, fold_slices, make_folds, trading_dates

PRED_COLS = ["event_id", "session_date", "fold", "side", "va_type", "entry_ts", "exit_ts", "exit_reason",
             "entry_price_raw", "exit_price_raw", "stop_price", "stop_dist_pts", "rr_ratio", "costs_r",
             "p", "ev_r", "take_A", "take_B0", "take_C", "take_Copt", "realized_R", "pnl_usd", "label",
             "p_context", "p_rw"]


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    cfg = load_config("config.yaml")
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", default=cfg["features"]["version"])
    ap.add_argument("--subset", default=None)
    ap.add_argument("--tag", default=None)
    ap.add_argument("--seed", type=int, default=None)
    args = ap.parse_args()
    if args.seed is not None:
        cfg["model"]["seed"] = int(args.seed)
    version = args.version
    tag = args.tag or version
    fs = feature_set(version)

    t0 = time.time()
    feats = pd.read_parquet(Path(cfg["features"]["features_dir"]) / f"features_{fs['file']}.parquet")
    labels = pd.read_parquet(Path(cfg["labels"]["labels_dir"]) / "labels.parquet")
    days = pd.read_parquet(Path(cfg["data"]["events_dir"]) / "days.parquet")
    df = feats.merge(labels.drop(columns=["side", "stop_price"]), on="event_id", how="inner")
    df["stop_dist_pts"] = (df["entry_ref_price"] - df["stop_price"]).abs()
    df["costs_r"] = costs_in_r(df["stop_dist_pts"].to_numpy(), cfg)
    vault = dt.date.fromisoformat(cfg["vault"]["start"])
    df = df[pd.to_datetime(df["session_date"]).dt.date < vault].copy()
    assert_no_vault(df, cfg)
    print(f"eventi con feature+label fuori cassaforte: {len(df)} (caricati in {time.time()-t0:.0f}s)")

    feats_scope = feats[pd.to_datetime(feats["session_date"]).dt.date < vault]
    keep = None
    if args.subset:
        keep = set(pd.to_datetime(pd.read_parquet(args.subset)["session_date"]).dt.date)
        df = df[pd.to_datetime(df["session_date"]).dt.date.isin(keep)].copy()
        feats_scope = feats_scope[pd.to_datetime(feats_scope["session_date"]).dt.date.isin(keep)]
        print(f"eventi nel sottoinsieme: {len(df)}")

    assert len(df) == len(feats_scope), (
        f"il merge con le label ha perso righe: df={len(df)} feats_fuori_cassaforte_e_nel_subset={len(feats_scope)}")

    folds = make_folds(trading_dates(days, cfg), cfg)
    model_dir = Path(cfg["model"]["model_dir"])
    models_dir = model_dir / f"models_{tag}"
    models_dir.mkdir(parents=True, exist_ok=True)
    preds, sanity = [], []
    for f in folds:
        tf = time.time()
        fit, val, test = fold_slices(df, f)
        offset = None
        if fs["offset"]:
            offset = fit_prior_calibrator(fit, "label")            # solo fit_df (spec §12-ter)
        A = fit_fold_model(fit, val, fs["core"], fs["exploratory"], "label", cfg, offset=offset)
        p = predict_p(A, test)
        p_context = context_only_predict(fit, val, test, "label", cfg, offset=offset)
        ev = ev_r(p, test["rr_ratio"].to_numpy(), test["costs_r"].to_numpy())
        out = test.copy()
        out["fold"], out["p"], out["ev_r"] = f.k, p, ev
        out["take_A"] = take(ev, cfg["decision"]["margin_r"])
        out["take_B0"] = True
        out["take_C"] = rule_list(test, cfg["baselines"]["rules_by_version"][version])
        c_opt = fit_c_opt(pd.concat([fit, val]), cfg, version)
        out["take_Copt"] = apply_c_opt(test, c_opt)
        out["p_context"] = p_context
        out["p_rw"] = 1.0 / (1.0 + out["rr_ratio"])
        if offset is not None:
            out["p_l2"] = p_l2(test, *offset)
        pred_cols = PRED_COLS + (["p_l2"] if offset is not None else [])
        preds.append(out[pred_cols])

        mA = model_metrics(test["label"], p)
        brier_context = float(brier_score_loss(test["label"], p_context))
        if offset is not None:
            aucs = shuffle_test_aucs(fit, val, test, fs["core"], "label", cfg, seeds=[0, 1, 2, 3, 4],
                                      offset=offset, refit_offset=True)
            aucs_fixed = shuffle_test_aucs(fit, val, test, fs["core"], "label", cfg, seeds=[0, 1, 2, 3, 4],
                                            offset=offset, refit_offset=False)
            shuffle_kw = dict(auc_shuffle=float(np.mean(aucs)), auc_shuffle_seeds=aucs,
                               auc_shuffle_fixed_offset_seeds=aucs_fixed, l2_a=offset[0], l2_b=offset[1])
        else:
            shuffle_kw = dict(auc_shuffle=shuffle_test_auc(fit, val, test, fs["core"], "label", cfg,
                                                            seed=cfg["model"]["seed"]))
        s = dict(fold=f.k, n_fit=len(fit), n_val=len(val), n_test=len(test),
                 n_val_es=A.n_val_es, n_val_cal=A.n_val_cal,
                 features_A=A.features, params_A=A.params,
                 best_iteration=A.best_iteration, val_brier=A.val_brier, auc_A=mA["auc"], brier_A=mA["brier"],
                 brier_context=brier_context,
                 **shuffle_kw,
                 c_opt_params=c_opt, positives_test=float(test["label"].mean()),
                 test_start=str(f.test_start), test_end=str(f.test_end))
        sanity.append(s)
        save_model(A, models_dir, f.k)
        if offset is not None:
            shuffle_txt = f"l2 a={s['l2_a']:.3f} b={s['l2_b']:.3f} | shuffle media(5 seed) {s['auc_shuffle']:.3f}"
        else:
            shuffle_txt = f"shuffle auc {s['auc_shuffle']:.3f}"
        print(f"fold {f.k} {f.test_start}..{f.test_end}: fit {len(fit)} val {len(val)} (es {A.n_val_es} cal {A.n_val_cal}) test {len(test)} | "
              f"A auc {mA['auc']:.3f} brier {mA['brier']:.4f} | contesto brier {s['brier_context']:.4f} | "
              f"{shuffle_txt} | take_A {int(out['take_A'].sum())} C {int(out['take_C'].sum())} "
              f"C-opt {int(out['take_Copt'].sum())} | feature {len(A.features)} | {time.time()-tf:.0f}s")

    pred = pd.concat(preds, ignore_index=True)
    pred.to_parquet(model_dir / f"predictions_{tag}.parquet", index=False)
    sanity_out = {"seed": cfg["model"]["seed"], "version": version, "subset": args.subset, "tag": tag,
                  "n_events": len(df), "config_hash": config_hash(), "commit": git_commit(), "folds": sanity}
    (model_dir / f"sanity_{tag}.json").write_text(json.dumps(sanity_out, indent=2, default=str), encoding="utf-8")
    print(f"predizioni {len(pred)} su {len(folds)} finestre; take_A totali {int(pred['take_A'].sum())}; {time.time()-t0:.0f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
