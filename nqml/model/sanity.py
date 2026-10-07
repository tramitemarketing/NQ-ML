"""Controlli anti-inganno (spec §9.3): shuffle test e modello solo-contesto."""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.metrics import brier_score_loss, roc_auc_score

from nqml.features.build import CONTEXT_ONLY_1A
from nqml.model.train import fit_fold_model, predict_p, predict_raw, predict_tree_raw


def model_metrics(y, p) -> dict:
    return {"auc": float(roc_auc_score(y, p)), "brier": float(brier_score_loss(y, p))}


def shuffle_test_aucs(fit_df, val_df, test_df, features, label_col, cfg, seeds, offset=None,
                      refit_offset: bool = True) -> list[float]:
    """AUC sul test di modelli addestrati su label mescolate (fit e validazione), uno per seed.
    Con offset: si valuta il solo punteggio degli alberi. `refit_offset=True` (emendamento §12-ter, 2026-09-22) rifitta
    L2 sulle label mescolate, cosi' l'offset e' ~costante e il null e' pulito (atteso ~0.5); con `refit_offset=False`
    l'offset resta quello vero e gli alberi imparano a cancellarlo (punteggio anti-correlato: variante solo riportata)."""
    from nqml.model.prior import fit_prior_calibrator
    out = []
    for seed in seeds:
        rng = np.random.default_rng(seed)
        fit2, val2 = fit_df.copy(), val_df.copy()
        fit2[label_col] = rng.permutation(fit2[label_col].to_numpy())
        val2[label_col] = rng.permutation(val2[label_col].to_numpy())
        off = fit_prior_calibrator(fit2, label_col) if (offset is not None and refit_offset) else offset
        m = fit_fold_model(fit2, val2, core=list(features), exploratory=[], label_col=label_col, cfg=cfg, offset=off)
        score = predict_tree_raw(m, test_df) if off is not None else predict_raw(m, test_df)   # con offset: solo gli alberi
        out.append(float(roc_auc_score(test_df[label_col], score)) if np.ptp(score) > 0 else 0.5)
    return out


def shuffle_test_auc(fit_df, val_df, test_df, features, label_col, cfg, seed: int) -> float:
    return shuffle_test_aucs(fit_df, val_df, test_df, features, label_col, cfg, seeds=[seed])[0]


def context_only_predict(fit_df, val_df, test_df, label_col, cfg, offset=None) -> np.ndarray:
    m = fit_fold_model(fit_df, val_df, core=list(CONTEXT_ONLY_1A), exploratory=[], label_col=label_col, cfg=cfg, offset=offset)
    return predict_p(m, test_df)


def context_only_brier(fit_df, val_df, test_df, label_col, cfg) -> float:
    return float(brier_score_loss(test_df[label_col], context_only_predict(fit_df, val_df, test_df, label_col, cfg)))
