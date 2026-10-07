import datetime as dt

import numpy as np
import pandas as pd

from nqml.config import load_config
from nqml.model.sanity import context_only_brier, context_only_predict, model_metrics, shuffle_test_auc
from test_train import _synthetic, _synthetic_rr, CFG_FAST


def test_model_metrics():
    m = model_metrics(np.array([0, 1, 1, 0]), np.array([0.1, 0.9, 0.8, 0.2]))
    assert m["auc"] == 1.0 and abs(m["brier"] - np.mean([0.01, 0.01, 0.04, 0.04])) < 1e-12


def test_shuffle_test_destroys_signal():
    fit, val, test = _synthetic(2000, 0), _synthetic(600, 1), _synthetic(1000, 2)
    val["session_date"] = [dt.date(2024, 1, 1) + dt.timedelta(days=i // 10) for i in range(len(val))]
    cfg = {**CFG_FAST, "model": {**CFG_FAST["model"], "monotone": {}}}
    auc = shuffle_test_auc(fit, val, test, ["x1", "x2"], "label", cfg, seed=0)
    assert 0.42 < auc < 0.58


def test_context_only_uses_only_context_features():
    fit, val, test = _synthetic(2000, 0), _synthetic(600, 1), _synthetic(1000, 2)
    for df in (fit, val, test):        # le colonne di contesto della 1a, riempite con rumore
        for c in ("va_type", "minutes_since_open", "bars_in_profile", "open_vs_on_va", "stop_dist_atr", "rr_ratio"):
            df[c] = np.random.default_rng(1).normal(size=len(df))
    val["session_date"] = [dt.date(2024, 1, 1) + dt.timedelta(days=i // 10) for i in range(len(val))]
    cfg = {**CFG_FAST, "model": {**CFG_FAST["model"], "monotone": {}}}
    b = context_only_brier(fit, val, test, "label", cfg)
    assert 0.2 < b < 0.3            # nessun segnale nel contesto sintetico: Brier vicino a p(1-p)


def test_context_only_predict_shape_and_range():
    fit, val, test = _synthetic(2000, 0), _synthetic(600, 1), _synthetic(1000, 2)
    for df in (fit, val, test):
        for c in ("va_type", "minutes_since_open", "bars_in_profile", "open_vs_on_va", "stop_dist_atr", "rr_ratio"):
            df[c] = np.random.default_rng(1).normal(size=len(df))
    val["session_date"] = [dt.date(2024, 1, 1) + dt.timedelta(days=i // 10) for i in range(len(val))]
    cfg = {**CFG_FAST, "model": {**CFG_FAST["model"], "monotone": {}, "calibration_split": 0.5}}
    p = context_only_predict(fit, val, test, "label", cfg)
    assert p.shape == (1000,) and p.min() >= 0 and p.max() <= 1


def test_shuffle_test_aucs_with_offset_measures_trees_only():
    from nqml.model.prior import fit_prior_calibrator
    from nqml.model.sanity import shuffle_test_aucs
    fit, val, test = _synthetic_rr(2000, 40), _synthetic_rr(600, 41), _synthetic_rr(800, 42)
    a, b = fit_prior_calibrator(fit, "label")
    cfg = {**CFG_FAST, "model": {**CFG_FAST["model"], "monotone": {}}}
    aucs = shuffle_test_aucs(fit, val, test, ["x1", "x2"], "label", cfg, seeds=[0, 1, 2], offset=(a, b))
    assert len(aucs) == 3 and all(0.3 < x < 0.7 for x in aucs)             # alberi su label mescolate: ~0.5, non il 0.77 del prior


def test_shuffle_refit_offset_gives_a_clean_null_while_fixed_offset_is_anticorrelated():
    """Emendamento §12-ter (2026-09-22): con offset informativo e label mescolate gli alberi cancellano l'offset;
    rifittare L2 sulle label mescolate ripristina il null ~0.5."""
    from nqml.model.prior import fit_prior_calibrator, logit, sigmoid
    from nqml.model.sanity import shuffle_test_aucs
    rng = np.random.default_rng(77)
    n = 3000
    df = pd.DataFrame({"x1": rng.normal(size=n), "x2": rng.normal(size=n)})
    df["rr_ratio"] = np.exp(rng.normal(np.log(1.9), 0.6, size=n))
    df["x2"] = -logit(1 / (1 + df["rr_ratio"])) + rng.normal(0, 0.3, size=n)       # feature non vincolata correlata al prior
    df["label"] = (rng.uniform(size=n) < sigmoid(1.5 * logit(1 / (1 + df["rr_ratio"])))).astype(int)
    df["session_date"] = [dt.date(2024, 1, 1) + dt.timedelta(days=i // 10) for i in range(n)]
    fit, val, test = df.iloc[:2000], df.iloc[2000:2500], df.iloc[2500:]
    a, b = fit_prior_calibrator(fit, "label")
    cfg = {**CFG_FAST, "model": {**CFG_FAST["model"], "monotone": {}}}
    clean = shuffle_test_aucs(fit, val, test, ["x1", "x2"], "label", cfg, seeds=[0, 1, 2], offset=(a, b), refit_offset=True)
    fixed = shuffle_test_aucs(fit, val, test, ["x1", "x2"], "label", cfg, seeds=[0, 1, 2], offset=(a, b), refit_offset=False)
    assert 0.4 < np.mean(clean) < 0.6                                   # null pulito
    assert np.mean(fixed) < np.mean(clean) - 0.05                        # offset fisso: gli alberi lo cancellano -> anti-correlazione
