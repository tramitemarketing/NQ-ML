"""Prior geometrico p_rw = 1/(1+rr_ratio) e sua calibrazione L2 (spec §12-ter): logistica a due parametri
stimata sul solo training della piega; usata come offset (init_score) del boosting."""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression

_EPS = 1e-6


def sigmoid(z) -> np.ndarray:
    """Logistica numericamente stabile: nessun overflow di exp per |z| grande (l'esecuzione gira con -W error)."""
    z = np.asarray(z, dtype=float)
    out = np.empty_like(z)
    pos = z >= 0
    out[pos] = 1.0 / (1.0 + np.exp(-z[pos]))
    ez = np.exp(z[~pos])
    out[~pos] = ez / (1.0 + ez)
    return out


def logit(p) -> np.ndarray:
    p = np.clip(np.asarray(p, dtype=float), _EPS, 1 - _EPS)
    return np.log(p / (1 - p))


def p_rw(df: pd.DataFrame) -> np.ndarray:
    return 1.0 / (1.0 + df["rr_ratio"].to_numpy(dtype=float))


def fit_prior_calibrator(fit_df: pd.DataFrame, label_col: str) -> tuple[float, float]:
    # sklearn >= 1.8 deprecò penalty=None a favore di C=np.inf (stessa logistica senza penalità, nessuna
    # regolarizzazione aggiunta): l'equivalente non penalizzato per questa versione installata (1.9.1).
    x = logit(p_rw(fit_df)).reshape(-1, 1)
    lr = LogisticRegression(C=np.inf, solver="lbfgs", max_iter=1000).fit(x, fit_df[label_col].to_numpy(dtype=int))
    return float(lr.coef_[0, 0]), float(lr.intercept_[0])


def prior_offset(df: pd.DataFrame, a: float, b: float) -> np.ndarray:
    return a * logit(p_rw(df)) + b


def p_l2(df: pd.DataFrame, a: float, b: float) -> np.ndarray:
    return sigmoid(prior_offset(df, a, b))
