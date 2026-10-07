import numpy as np
import pandas as pd
from sklearn.metrics import brier_score_loss

from nqml.model.prior import fit_prior_calibrator, logit, p_l2, p_rw, prior_offset, sigmoid


def _df(n, a, b, seed):
    rng = np.random.default_rng(seed)
    rr = np.exp(rng.normal(np.log(1.9), 0.5, size=n))                     # rr_ratio attorno alla mediana reale 1.92
    prw = 1 / (1 + rr)
    y = (rng.uniform(size=n) < sigmoid(a * logit(prw) + b)).astype(int)
    return pd.DataFrame({"rr_ratio": rr, "label": y})


def test_p_rw_and_logit_roundtrip():
    df = pd.DataFrame({"rr_ratio": [1.0, 3.0]})
    assert np.allclose(p_rw(df), [0.5, 0.25]) and np.allclose(sigmoid(logit(p_rw(df))), [0.5, 0.25])


def test_fit_prior_calibrator_recovers_a_and_b():
    df = _df(40000, 1.1, -0.2, 0)
    a, b = fit_prior_calibrator(df, "label")
    assert abs(a - 1.1) < 0.08 and abs(b + 0.2) < 0.08


def test_identity_when_prior_is_calibrated_and_l2_never_worse_in_sample():
    df = _df(40000, 1.0, 0.0, 1)
    a, b = fit_prior_calibrator(df, "label")
    assert abs(a - 1.0) < 0.08 and abs(b) < 0.08
    df2 = _df(40000, 1.2, -0.3, 2)
    a2, b2 = fit_prior_calibrator(df2, "label")
    assert brier_score_loss(df2["label"], p_l2(df2, a2, b2)) <= brier_score_loss(df2["label"], p_rw(df2)) + 1e-12
    assert np.allclose(sigmoid(prior_offset(df2, a2, b2)), p_l2(df2, a2, b2))


def test_sigmoid_is_stable_for_extreme_arguments():
    z = np.array([-1000.0, -50.0, 0.0, 50.0, 1000.0])
    out = sigmoid(z)                                                        # nessun RuntimeWarning (la suite gira con -W error)
    assert np.allclose(out, [0.0, 0.0, 0.5, 1.0, 1.0], atol=1e-12) and np.all(np.isfinite(out))
    assert np.isclose(sigmoid(np.array([0.3]))[0], 1 / (1 + np.exp(-0.3)))
