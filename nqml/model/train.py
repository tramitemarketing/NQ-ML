"""LightGBM con vincoli monotoni, griglia piccola, forward selection delle esplorative, calibrazione isotonica (spec §8)."""
from __future__ import annotations

import itertools
import json
from dataclasses import dataclass
from pathlib import Path

import joblib
import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import brier_score_loss

from nqml.model.prior import prior_offset, sigmoid

MIN_BRIER_GAIN = 1e-4


@dataclass
class FittedModel:
    booster: lgb.Booster
    calibrator: IsotonicRegression | None
    features: list[str]
    params: dict
    best_iteration: int
    val_brier: float
    n_val_es: int = 0
    n_val_cal: int = 0
    offset: tuple[float, float] | None = None       # (a, b) della L2: p = sigmoide(raw alberi + a·logit(p_rw) + b)


def lgb_params(cfg: dict, num_leaves: int, min_data_in_leaf: int, features: list[str], monotone: dict) -> dict:
    m = cfg["model"]
    return {
        "objective": "binary", "metric": "binary_logloss",
        "learning_rate": m["learning_rate"], "feature_fraction": m["feature_fraction"],
        "num_leaves": num_leaves, "min_data_in_leaf": min_data_in_leaf,
        "monotone_constraints": [int(monotone.get(f, 0)) for f in features],
        "seed": m["seed"], "feature_fraction_seed": m["seed"],
        "deterministic": True, "force_col_wise": True, "num_threads": 1, "verbose": -1,
    }


def fit_lgbm(X_fit: pd.DataFrame, y_fit, X_val: pd.DataFrame, y_val, params: dict, cfg: dict,
            init_fit=None, init_val=None) -> lgb.Booster:
    m = cfg["model"]
    dtrain = lgb.Dataset(X_fit, label=np.asarray(y_fit), init_score=init_fit, free_raw_data=False)
    dval = lgb.Dataset(X_val, label=np.asarray(y_val), init_score=init_val, reference=dtrain, free_raw_data=False)
    callbacks = [lgb.early_stopping(m["early_stopping_rounds"], verbose=False)] if m["max_rounds"] > 0 else []
    return lgb.train(params, dtrain, num_boost_round=m["max_rounds"], valid_sets=[dval], callbacks=callbacks)


def fit_calibrator(p_val, y_val) -> IsotonicRegression:
    return IsotonicRegression(y_min=0.0, y_max=1.0, out_of_bounds="clip").fit(np.asarray(p_val), np.asarray(y_val))


def split_val(val_df: pd.DataFrame, split: float) -> tuple[pd.DataFrame, pd.DataFrame]:
    v = val_df.sort_values("session_date", kind="stable")
    dates = pd.to_datetime(v["session_date"]).dt.date.to_numpy()
    cut = int(round(len(v) * split))
    while 0 < cut < len(v) and dates[cut] == dates[cut - 1]:
        cut += 1
    if cut == 0 or cut == len(v):
        raise ValueError(f"split_val: la validazione ({len(v)} righe, {len(set(dates))} giorni) non si divide in due parti "
                         f"non vuote con split={split}: servono almeno 2 giorni distinti per separare early-stopping e calibrazione")
    return v.iloc[:cut], v.iloc[cut:]


def save_model(model: "FittedModel", dir: Path, k: int) -> None:
    dir = Path(dir); dir.mkdir(parents=True, exist_ok=True)
    model.booster.save_model(str(dir / f"fold_{k}.txt"), num_iteration=max(model.best_iteration, 0) or None)
    (dir / f"fold_{k}_features.json").write_text(json.dumps(model.features), encoding="utf-8")
    if model.offset is not None:
        (dir / f"fold_{k}_offset.json").write_text(json.dumps({"a": model.offset[0], "b": model.offset[1]}), encoding="utf-8")
    else:
        joblib.dump(model.calibrator, dir / f"fold_{k}_calibrator.joblib")


def predict_tree_raw(model: FittedModel, X: pd.DataFrame) -> np.ndarray:
    if model.best_iteration <= 0:
        return np.zeros(len(X))
    return model.booster.predict(X[model.features], num_iteration=model.best_iteration, raw_score=True)


def predict_raw(model: FittedModel, X: pd.DataFrame) -> np.ndarray:
    if model.offset is not None:
        return sigmoid(predict_tree_raw(model, X) + prior_offset(X, *model.offset))
    return model.booster.predict(X[model.features], num_iteration=model.best_iteration)


def predict_p(model: FittedModel, X: pd.DataFrame) -> np.ndarray:
    raw = predict_raw(model, X)
    return raw if model.calibrator is None else model.calibrator.predict(raw)


def _fit_eval(fit_df, val_df, features, label_col, num_leaves, min_data, cfg, offset=None):
    params = lgb_params(cfg, num_leaves, min_data, features, cfg["model"].get("monotone", {}))
    if offset is None:
        b = fit_lgbm(fit_df[features], fit_df[label_col], val_df[features], val_df[label_col], params, cfg)
        p_val = b.predict(val_df[features], num_iteration=b.best_iteration)
    else:
        params = {**params, "boost_from_average": False}
        b = fit_lgbm(fit_df[features], fit_df[label_col], val_df[features], val_df[label_col], params, cfg,
                     init_fit=prior_offset(fit_df, *offset), init_val=prior_offset(val_df, *offset))
        best_it = int(b.best_iteration or 0)
        raw = b.predict(val_df[features], num_iteration=best_it, raw_score=True) if best_it > 0 else np.zeros(len(val_df))
        p_val = sigmoid(raw + prior_offset(val_df, *offset))
    return b, params, float(brier_score_loss(val_df[label_col], p_val)), p_val


def fit_fold_model(fit_df: pd.DataFrame, val_df: pd.DataFrame, core: list[str], exploratory: list[str],
                   label_col: str, cfg: dict, offset: tuple[float, float] | None = None) -> FittedModel:
    m = cfg["model"]
    if offset is None:
        val_es, val_cal = split_val(val_df, m["calibration_split"])
    else:
        val_es, val_cal = val_df, val_df.iloc[0:0]          # spec §12-ter: validazione intera, nessun calibratore
    best = None
    for nl, md in itertools.product(m["num_leaves_grid"], m["min_data_in_leaf_grid"]):
        b, params, brier, p_val = _fit_eval(fit_df, val_es, list(core), label_col, nl, md, cfg, offset)
        if best is None or brier < best[2]:
            best = (b, params, brier, p_val, list(core), nl, md)
    b, params, brier, p_val, feats, nl, md = best
    for f in exploratory:
        cand = feats + [f]
        b2, params2, brier2, p2 = _fit_eval(fit_df, val_es, cand, label_col, nl, md, cfg, offset)
        if brier2 < brier - MIN_BRIER_GAIN:
            b, params, brier, p_val, feats = b2, params2, brier2, p2, cand
    best_it = int(b.best_iteration or 0)
    if offset is not None:
        return FittedModel(booster=b, calibrator=None, features=feats, params=params, best_iteration=best_it,
                           val_brier=brier, n_val_es=len(val_es), n_val_cal=0, offset=tuple(offset))
    p_cal = b.predict(val_cal[feats], num_iteration=b.best_iteration)
    cal = fit_calibrator(p_cal, val_cal[label_col])
    return FittedModel(booster=b, calibrator=cal, features=feats, params=params,
                       best_iteration=best_it, val_brier=brier, n_val_es=len(val_es), n_val_cal=len(val_cal))
