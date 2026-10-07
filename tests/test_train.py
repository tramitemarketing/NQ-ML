import datetime as dt

import numpy as np
import pandas as pd
import pytest
from sklearn.metrics import roc_auc_score

from nqml.config import load_config
from nqml.model.prior import fit_prior_calibrator, p_l2
from nqml.model.train import fit_fold_model, predict_p, predict_raw, predict_tree_raw, split_val, save_model

CFG = load_config("config.yaml")
CFG_FAST = {**CFG, "model": {**CFG["model"], "max_rounds": 300, "early_stopping_rounds": 30}}


def _synthetic(n, seed):
    rng = np.random.default_rng(seed)
    x1, x2, x3 = rng.normal(size=n), rng.normal(size=n), rng.normal(size=n)
    logit = 1.5 * x1 - 1.0 * x2
    y = (rng.uniform(size=n) < 1 / (1 + np.exp(-logit))).astype(int)
    return pd.DataFrame({"x1": x1, "x2": x2, "x3": x3, "label": y})


def _synthetic_rr(n, seed):
    df = _synthetic(n, seed)
    rng = np.random.default_rng(seed + 100)
    df["rr_ratio"] = np.exp(rng.normal(np.log(1.9), 0.5, size=n))
    df["session_date"] = [dt.date(2024, 1, 1) + dt.timedelta(days=i // 10) for i in range(n)]
    return df


def test_fit_fold_model_learns_and_respects_monotone_constraints():
    fit, val, test = _synthetic(3000, 0), _synthetic(800, 1), _synthetic(1000, 2)
    val["session_date"] = [dt.date(2024, 1, 1) + dt.timedelta(days=i // 10) for i in range(len(val))]
    cfg = {**CFG_FAST, "model": {**CFG_FAST["model"], "monotone": {"x1": 1, "x2": -1}}}
    m = fit_fold_model(fit, val, core=["x1", "x2"], exploratory=["x3"], label_col="label", cfg=cfg)
    assert m.features[:2] == ["x1", "x2"] and m.best_iteration > 0
    p = predict_p(m, test)
    assert roc_auc_score(test["label"], p) > 0.8 and p.min() >= 0 and p.max() <= 1
    # monotonia: x1 crescente (x2 fisso) non fa mai scendere la probabilita' grezza
    grid = pd.DataFrame({"x1": np.linspace(-2, 2, 41), "x2": 0.0, "x3": 0.0})
    raw = predict_raw(m, grid)
    assert np.all(np.diff(raw) >= -1e-9)
    grid2 = pd.DataFrame({"x1": 0.0, "x2": np.linspace(-2, 2, 41), "x3": 0.0})
    assert np.all(np.diff(predict_raw(m, grid2)) <= 1e-9)


def test_exploratory_signal_feature_is_kept_and_noise_is_optional():
    fit, val = _synthetic(3000, 3), _synthetic(800, 4)
    val["session_date"] = [dt.date(2024, 1, 1) + dt.timedelta(days=i // 10) for i in range(len(val))]
    cfg = {**CFG_FAST, "model": {**CFG_FAST["model"], "monotone": {}}}
    m = fit_fold_model(fit, val, core=["x1"], exploratory=["x3", "x2"], label_col="label", cfg=cfg)
    assert "x2" in m.features                      # segnale vero: migliora il Brier di validazione, viene tenuto
    assert set(m.features) <= {"x1", "x2", "x3"} and m.features[0] == "x1"


def test_calibrator_is_monotone_and_val_brier_recorded():
    fit, val = _synthetic(2000, 5), _synthetic(600, 6)
    val["session_date"] = [dt.date(2024, 1, 1) + dt.timedelta(days=i // 10) for i in range(len(val))]
    cfg = {**CFG_FAST, "model": {**CFG_FAST["model"], "monotone": {}}}
    m = fit_fold_model(fit, val, core=["x1", "x2"], exploratory=[], label_col="label", cfg=cfg)
    xs = np.linspace(0, 1, 101)
    assert np.all(np.diff(m.calibrator.predict(xs)) >= -1e-12) and 0 < m.val_brier < 0.25


def test_split_val_by_date_without_breaking_a_day():
    df = pd.DataFrame({"session_date": [dt.date(2024, 1, 2)] * 3 + [dt.date(2024, 1, 3)] * 3 + [dt.date(2024, 1, 4)] * 4, "x": range(10)})
    es, cal = split_val(df, 0.5)
    assert len(es) == 6 and len(cal) == 4                              # il taglio cade al cambio di giorno dopo la quota
    assert es["session_date"].max() < cal["session_date"].min()
    es2, cal2 = split_val(df, 0.3)
    assert len(es2) == 3 and len(cal2) == 7


def test_split_val_refuses_a_single_day_validation():
    one_day = pd.DataFrame({"session_date": [dt.date(2024, 1, 2)] * 10, "x": range(10)})
    with pytest.raises(ValueError, match="2 giorni distinti"):
        split_val(one_day, 0.5)                                         # la calibrazione resterebbe vuota


def test_fit_fold_model_uses_separate_calibration_half(tmp_path):
    fit, val = _synthetic(2000, 5), _synthetic(600, 6)
    val["session_date"] = [dt.date(2024, 1, 1) + dt.timedelta(days=i // 10) for i in range(len(val))]
    cfg = {**CFG_FAST, "model": {**CFG_FAST["model"], "monotone": {}, "calibration_split": 0.5}}
    m = fit_fold_model(fit, val, core=["x1", "x2"], exploratory=[], label_col="label", cfg=cfg)
    assert m.n_val_es == 300 and m.n_val_cal == 300
    save_model(m, tmp_path, 3)
    assert (tmp_path / "fold_3.txt").exists() and (tmp_path / "fold_3_features.json").exists() and (tmp_path / "fold_3_calibrator.joblib").exists()


def test_offset_mode_nests_the_calibrated_prior_with_zero_rounds():
    fit, val, test = _synthetic_rr(3000, 10), _synthetic_rr(800, 11), _synthetic_rr(500, 12)
    a, b = fit_prior_calibrator(fit, "label")
    # LightGBM 4.7.0 rifiuta sia num_boost_round=0 (ValueError) sia learning_rate=0.0 esatto (Config
    # richiede learning_rate > 0.0 anche durante la costruzione del Dataset): variante che funziona per
    # la sola nesting-TEST, un albero con learning_rate 1e-300 (> 0, passa la validazione): LightGBM arrotonda a 0
    # le foglie con |valore| <= kZeroThreshold (1e-35) in Tree::Shrinkage, quindi l'albero ESISTE e contribuisce
    # esattamente 0 — il test passa per il percorso di produzione, non per la scorciatoia best_iteration <= 0.
    cfg = {**CFG_FAST, "model": {**CFG_FAST["model"], "monotone": {}, "max_rounds": 1, "learning_rate": 1e-300}}
    m = fit_fold_model(fit, val, core=["x1", "x2"], exploratory=[], label_col="label", cfg=cfg, offset=(a, b))
    assert m.calibrator is None and m.offset == (a, b) and m.n_val_cal == 0 and m.n_val_es == len(val)
    assert m.best_iteration == 1 and m.booster.num_trees() == 1              # l'albero c'e': niente scorciatoia
    assert np.allclose(predict_tree_raw(m, test), 0.0, atol=1e-12)
    assert np.allclose(predict_p(m, test), p_l2(test, a, b), atol=1e-9)         # 0 alberi ⇒ p ≡ L2


def test_offset_mode_learns_beyond_the_prior_and_keeps_old_path_unchanged():
    fit, val, test = _synthetic_rr(3000, 20), _synthetic_rr(800, 21), _synthetic_rr(1000, 22)
    a, b = fit_prior_calibrator(fit, "label")
    cfg = {**CFG_FAST, "model": {**CFG_FAST["model"], "monotone": {"x1": 1, "x2": -1}}}
    m = fit_fold_model(fit, val, core=["x1", "x2"], exploratory=[], label_col="label", cfg=cfg, offset=(a, b))
    assert m.best_iteration > 0
    from sklearn.metrics import brier_score_loss
    assert brier_score_loss(test["label"], predict_p(m, test)) < brier_score_loss(test["label"], p_l2(test, a, b))
    m_old = fit_fold_model(fit, val, core=["x1", "x2"], exploratory=[], label_col="label", cfg=cfg)
    assert m_old.calibrator is not None and m_old.offset is None and m_old.n_val_cal > 0


def test_save_model_with_offset_writes_offset_json(tmp_path):
    fit, val = _synthetic_rr(1500, 30), _synthetic_rr(400, 31)
    a, b = fit_prior_calibrator(fit, "label")
    cfg = {**CFG_FAST, "model": {**CFG_FAST["model"], "monotone": {}}}
    m = fit_fold_model(fit, val, core=["x1"], exploratory=[], label_col="label", cfg=cfg, offset=(a, b))
    save_model(m, tmp_path, 3)
    import json
    assert json.loads((tmp_path / "fold_3_offset.json").read_text())["a"] == a
    assert not (tmp_path / "fold_3_calibrator.joblib").exists()
