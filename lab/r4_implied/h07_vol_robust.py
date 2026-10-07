"""H07: robustezza delle regolarita' di vol con l'implicita (H02) e di H05C (VVIX -> |sorpresa|).
- finestra OLS 250 / 1000; VIX al posto di VXN; implicita in livello invece che log;
- placebo: implicita ritardata di 5 sessioni (informazione vecchia: il guadagno deve calare);
- bootstrap a blocchi mobili di 20 sessioni (le serie q sono autocorrelate);
- anno per anno e senza i 20 giorni migliori."""
from __future__ import annotations

import numpy as np
import pandas as pd

from lab import core
from lab.r4_implied import common as C
from lab.r4_implied.h06_tails_check import mbb_p
from lab.vol.candidates import _rolling_ols_pred


def main():
    f = C.load_features()
    y = f["logrv"]
    Xh = f[["h1", "h5", "h22"]].shift(1)
    f["lon"] = np.log(f["on_range_pct"])

    def q(base, aug, target=y):
        m = base.notna() & aug.notna() & target.notna()
        return ((target - base) ** 2 - (target - aug) ** 2)[m]

    def show(tid, desc, v, **ex):
        st = C.rec(tid, desc, v.to_numpy(), v.index.values, **ex)
        mean, lo, hi, p = mbb_p(v.to_numpy(), block=20)
        core.record(C.FAM, tid + "_mbb20", desc + " [bootstrap a blocchi mobili 20]", "discovery",
                    {"n": int(len(v)), "mean": mean, "lo": lo, "hi": hi, "p_two": p})
        print(C.fmt(tid, st), f"| mbb20 p={p:.4f} [{lo:+.4f};{hi:+.4f}]")
        return st

    for win in (250, 1000):
        b = _rolling_ols_pred(y, Xh, win=win, minp=min(250, win))
        a = _rolling_ols_pred(y, pd.concat([Xh, f[["iv_log"]]], axis=1), win=win, minp=min(250, win))
        show(f"H07_har_plus_iv_win{win}", f"HAR+iv vs HAR, OLS mobile {win}", q(b, a), win=win)
    base = f["har"]
    f["ivvix_log"] = np.log(f["VIX"] ** 2 / 252)
    a = _rolling_ols_pred(y, pd.concat([Xh, f[["ivvix_log"]]], axis=1))
    show("H07_har_plus_vix", "HAR+log VIX^2 vs HAR (VIX al posto di VXN)", q(base, a))
    f["iv_lvl"] = f["VXN"] ** 2 / 252
    a = _rolling_ols_pred(y, pd.concat([Xh, f[["iv_lvl"]]], axis=1))
    show("H07_har_plus_ivlevel", "HAR + VXN^2/252 in livello vs HAR", q(base, a))
    f["iv_lag5"] = f["iv_log"].shift(5)
    a = _rolling_ols_pred(y, pd.concat([Xh, f[["iv_lag5"]]], axis=1))
    show("H07_placebo_iv_lag5", "placebo: HAR + iv di 5 sessioni prima vs HAR (atteso: guadagno molto minore)", q(base, a))
    a_iv = _rolling_ols_pred(y, pd.concat([Xh, f[["iv_log"]]], axis=1))
    show("H07_main_har_plus_iv", "principale: HAR + log(VXN^2/252) vs HAR, win 500 (= H02_har_plus_ivxn)", q(base, a_iv))
    Xon = pd.concat([Xh, f[["lon"]]], axis=1)
    b_on = _rolling_ols_pred(y, Xon)
    a_on = _rolling_ols_pred(y, pd.concat([Xon, f[["iv_log"]]], axis=1))
    show("H07_on_plus_iv", "HAR+range notturno + iv vs HAR+range notturno (= H02_har_on_plus_iv)", q(b_on, a_on))
    # VVIX -> |sorpresa|
    absur = (y - a_iv).abs()
    lv = np.log(f["VVIX"])
    zz = (lv - lv.rolling(250, min_periods=120).mean().shift(1)) / lv.rolling(250, min_periods=120).std().shift(1)
    v = (zz * (absur - absur.expanding().mean().shift(1))).dropna()
    show("H07_vvix_abs_surprise", "z(VVIX)*(|logRV-HAR_iv| - media) (= H05C)", v)
    # VVIX come regressore della varianza del residuo: aggiunge a un modello di |residuo| con |residui| passati?
    past = absur.shift(1).rolling(22, min_periods=10).mean()
    ab = _rolling_ols_pred(absur, past.to_frame("p"))
    aa = _rolling_ols_pred(absur, pd.concat([past.rename("p"), lv.rename("lv")], axis=1))
    show("H07_vvix_adds_to_abs_resid_model", "|residuo HAR_iv|: media 22 dei |residui| passati + log VVIX vs solo media 22; guadagno MSE", q(ab, aa, absur))
    # anno per anno del principale
    qq = q(base, a_iv)
    print(core.yearly(qq.to_numpy(), qq.index))


if __name__ == "__main__":
    main()
