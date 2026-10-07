"""Controlli di robustezza sui tre candidati di regolarita' (registrati):
- VR di mezzogiorno con base 15m invece di 5m (il rumore microstrutturale gonfierebbe sum r5^2);
- VR di mezzogiorno con barre ancorate diversamente (ore 12:00-15:00);
- HAR vs media22 con perdita QLIKE (robusta a outlier) invece di MSE su log;
- leverage: versione con rendimento notturno (gap) invece del close-close.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from lab import core
from lab.vol import common as C
from lab.vol.a2_intraday import r5_matrix
from lab.vol.candidates import _rolling_ols_pred


def main():
    bars, daily = core.load("discovery")
    f, R = r5_matrix(bars, daily)
    R = R[R.notna().sum(1) == 78]
    sub = R.loc[:, 36:71]
    r15 = sub.T.groupby(np.arange(36) // 3).sum().T
    R60 = sub.T.groupby(np.arange(36) // 12).sum().T
    q = (R60 ** 2).sum(1) / (r15 ** 2).sum(1) - 1
    st = C.rec("F1_vr_midday_60_15", "VR mezzogiorno 60m/15m (12:30-15:30): robustezza al rumore microstrutturale; atteso <0", q, R.index)
    print("F1", {k: round(v, 4) for k, v in st.items() if isinstance(v, float)}, core.yearly(q, R.index)["mean"].round(3).to_dict())
    sub2 = R.loc[:, 30:65]
    q2 = (sub2.T.groupby(np.arange(36) // 12).sum().T ** 2).sum(1) / (sub2 ** 2).sum(1) - 1
    st = C.rec("F2_vr_1200_1500", "VR 60m/5m ore 12:00-15:00 (ancoraggio spostato di 30m); atteso <0", q2, R.index)
    print("F2", round(st["mean"], 4), round(st["lo"], 4), round(st["hi"], 4))
    # F3 QLIKE: L(rv, h) = rv/h - log(rv/h) - 1 con h = exp(previsione) (bias di Jensen ignorato, uguale per i due)
    y = f["logrv"]
    har = _rolling_ols_pred(y, f[["h1", "h5", "h22"]].shift(1))
    m22 = y.rolling(22).mean().shift(1)
    ok = har.notna() & m22.notna()

    def ql(pred):
        z = np.exp(y - pred)
        return z - np.log(z) - 1
    q3 = ql(m22) - ql(har)
    st = C.rec("F3_har_vs_mean22_qlike", "HAR vs media22 con perdita QLIKE; atteso >0", q3[ok], f.index[ok])
    print("F3", round(st["mean"], 4), round(st["lo"], 4), round(st["hi"], 4), core.yearly(q3[ok], f.index[ok])["mean"].round(3).to_dict())
    # F4 leverage con il rendimento notturno di oggi (noto alle 9:30): residuo HAR x -segno(gap)
    e = y - har
    q4 = e * (-np.sign(f["gap_pct"]))
    m = ok & f["gap_pct"].notna()
    st = C.rec("F4_leverage_gap_sign", "residuo HAR x -segno(gap overnight di oggi); atteso >0", q4[m], f.index[m])
    print("F4", round(st["mean"], 4), round(st["lo"], 4), round(st["hi"], 4))
    # F5 leverage: stabilita' per anno e ampiezza in termini di vol (exp): rapporto RV/previsione dopo giu' vs su
    rprev = f["cc_ret_pct"].shift(1)
    dn, up = ok & (rprev < 0), ok & (rprev > 0)
    print("F5 residuo medio dopo giu' %.3f (x%.2f in varianza), dopo su %.3f (x%.2f)" % (
        e[dn].mean(), np.exp(e[dn].mean()), e[up].mean(), np.exp(e[up].mean())))
    q5 = e * (-np.sign(rprev))
    print("F5 anni", core.yearly(q5[ok & rprev.notna()], f.index[ok & rprev.notna()])["mean"].round(3).to_dict())


if __name__ == "__main__":
    main()
