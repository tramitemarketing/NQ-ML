"""Binario A: regolarita' di volatilita' (discovery). Ogni test registrato.

Ogni regolarita' e' una quantita' per sessione con SEGNO ATTESO dichiarato qui sotto PRIMA di eseguire.
Previsioni HAR: stimate su finestra mobile delle 500 sessioni precedenti (causale, nessun look-ahead).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from lab import core
from lab.vol import common as C

WIN = 500


def rolling_ols_pred(y: pd.Series, X: pd.DataFrame, win=WIN, minp=250) -> pd.Series:
    """Previsione di y_t con OLS su (X_s, y_s), s in [t-win, t-1]; X_t gia' noto a t (deve essere laggato fuori)."""
    Xv = np.column_stack([np.ones(len(X)), X.to_numpy()])
    yv = y.to_numpy()
    ok = np.isfinite(Xv).all(1) & np.isfinite(yv)
    out = np.full(len(yv), np.nan)
    for t in range(len(yv)):
        if not np.isfinite(Xv[t]).all():
            continue
        lo = max(0, t - win)
        m = ok[lo:t]
        if m.sum() < minp:
            continue
        b, *_ = np.linalg.lstsq(Xv[lo:t][m], yv[lo:t][m], rcond=None)
        out[t] = Xv[t] @ b
    return pd.Series(out, index=y.index)


def main():
    bars, daily = core.load("discovery")
    f = C.daily_features(bars, daily)
    y = f["logrv"]
    L = f[["h1", "h5", "h22"]].shift(1)
    har = rolling_ols_pred(y, L)
    m22 = f["logrv"].rolling(22).mean().shift(1)
    rw = f["logrv"].shift(1)
    # media semplice "piatta" di lungo periodo (250)
    m250 = f["logrv"].rolling(250).mean().shift(1)
    ok = har.notna() & m22.notna() & m250.notna()
    days = f.index[ok]
    res = {}

    def r2(pred):
        e = (y[ok] - pred[ok])
        return 1 - (e ** 2).sum() / ((y[ok] - y[ok].mean()) ** 2).sum()

    print("R2 OOS: HAR %.3f  mean22 %.3f  RW %.3f  mean250 %.3f" % (r2(har), r2(m22), r2(rw), r2(m250)))
    # A1: HAR vs media 22 (atteso > 0)
    q = (y - m22) ** 2 - (y - har) ** 2
    res["A1"] = C.rec("A1_har_vs_mean22", "HAR-RV (rolling 500) vs media 22 sessioni: differenza di errore quadratico su log RV RTH 5m; atteso >0",
                      q[ok], days, r2_har=r2(har), r2_mean22=r2(m22), r2_rw=r2(rw), r2_mean250=r2(m250))
    q = (y - rw) ** 2 - (y - har) ** 2
    res["A1b"] = C.rec("A1b_har_vs_rw", "HAR vs random walk (logRV di ieri); atteso >0", q[ok], days)
    q = (y - m250) ** 2 - (y - har) ** 2
    res["A1c"] = C.rec("A1c_har_vs_mean250", "HAR vs media 250 sessioni; atteso >0", q[ok], days)

    # A2: HAR + range overnight (noto alle 9:30) -> RV RTH ; atteso >0
    Xon = L.copy()
    Xon["lon"] = np.log(f["on_range_pct"])      # della sessione t, noto alle 9:29
    Xon["lon_prev_ratio"] = np.nan
    Xon = Xon.drop(columns=["lon_prev_ratio"])
    har_on = rolling_ols_pred(y, Xon)
    ok2 = ok & har_on.notna()
    q = (y - har) ** 2 - (y - har_on) ** 2
    res["A2"] = C.rec("A2_overnight_range_adds", "log range overnight (18:00-9:29) aggiunto a HAR per prevedere log RV RTH; guadagno di MSE; atteso >0",
                      q[ok2], f.index[ok2], r2_har_on=r2(har_on))
    print("R2 HAR+ON", r2(har_on))
    # A2b: range del giorno (log range RTH) previsto da range notturno (vs HAR sul range)
    yr_ = f["lograng"]
    Lr = pd.DataFrame({"r1": yr_, "r5": yr_.rolling(5).mean(), "r22": yr_.rolling(22).mean()}).shift(1)
    har_r = rolling_ols_pred(yr_, Lr)
    Lr2 = Lr.copy(); Lr2["lon"] = np.log(f["on_range_pct"])
    har_r2 = rolling_ols_pred(yr_, Lr2)
    ok3 = har_r.notna() & har_r2.notna()
    q = (yr_ - har_r) ** 2 - (yr_ - har_r2) ** 2
    res["A2b"] = C.rec("A2b_range_from_on_range", "log range RTH: HAR sul range + log range overnight vs solo HAR sul range; atteso >0", q[ok3], f.index[ok3])
    e_r = yr_ - har_r2
    print("R2 range HARr %.3f HARr+ON %.3f" % (1 - ((yr_ - har_r)[ok3] ** 2).sum() / ((yr_[ok3] - yr_[ok3].mean()) ** 2).sum(),
                                               1 - ((e_r[ok3]) ** 2).sum() / ((yr_[ok3] - yr_[ok3].mean()) ** 2).sum()))

    # A3: leverage effect: residuo HAR di oggi * (-segno del rendimento close-close di ieri); atteso >0
    e = y - har
    rprev = f["cc_ret_pct"].shift(1)
    q = e * (-np.sign(rprev))
    ok4 = ok & rprev.notna()
    res["A3"] = C.rec("A3_leverage_sign", "leverage: residuo HAR(logRV_t) x (-segno rendimento c-c di t-1); atteso >0", q[ok4], f.index[ok4])
    # A3b: HAR asimmetrico (termine r- di ieri) guadagno MSE
    Xa = L.copy(); Xa["rneg"] = np.minimum(f["cc_ret_pct"], 0).shift(1); Xa["rpos"] = np.maximum(f["cc_ret_pct"], 0).shift(1)
    har_a = rolling_ols_pred(y, Xa)
    ok5 = ok & har_a.notna()
    q = (y - har) ** 2 - (y - har_a) ** 2
    res["A3b"] = C.rec("A3b_asym_har_gain", "HAR + r-(t-1), r+(t-1): guadagno di MSE su log RV; atteso >0", q[ok5], f.index[ok5], r2_har_asym=r2(har_a))
    # A3c: effetto grezzo: residuo medio dopo giorni down (quantita' = residuo solo nei giorni dopo un ribasso > 1%)
    mdown = ok4 & (rprev < -1.0)
    res["A3c"] = C.rec("A3c_resid_after_down1pct", "residuo HAR dopo giorni c-c < -1%; atteso >0", e[mdown], f.index[mdown])
    mup = ok4 & (rprev > 1.0)
    res["A3d"] = C.rec("A3d_resid_after_up1pct", "residuo HAR dopo giorni c-c > +1%; atteso <0 (leverage asimmetrico)", e[mup], f.index[mup])

    # A9: giorno della settimana nei residui HAR (lunedi' atteso <0: meno informazione nel weekend? dichiarato esplorativo)
    for dw, nm in enumerate(["lun", "mar", "mer", "gio", "ven"]):
        m = ok & (f["dow"] == dw)
        res[f"A9_{nm}"] = C.rec(f"A9_dow_resid_{nm}", f"residuo HAR medio il {nm}; esplorativo, segno non dichiarato", e[m], f.index[m])

    # A13: sorpresa di volume di ieri -> RV oggi oltre HAR
    lv = np.log(f["rth_volume"])
    Xv = L.copy(); Xv["vs"] = (lv - lv.rolling(22).mean()).shift(1)
    har_v = rolling_ols_pred(y, Xv)
    ok6 = ok & har_v.notna()
    q = (y - har) ** 2 - (y - har_v) ** 2
    res["A13"] = C.rec("A13_volume_surprise_gain", "HAR + sorpresa log volume RTH di ieri: guadagno MSE; atteso >0", q[ok6], f.index[ok6])

    # A14: |gap| overnight (noto alle 9:30) oltre HAR+ON range
    Xg = Xon.copy(); Xg["ag"] = np.log(np.abs(f["gap_pct"]) + 0.01)
    har_g = rolling_ols_pred(y, Xg)
    ok7 = ok2 & har_g.notna()
    q = (y - har_on) ** 2 - (y - har_g) ** 2
    res["A14"] = C.rec("A14_absgap_over_on", "|gap| aggiunto a HAR+range overnight: guadagno MSE; atteso >0", q[ok7], f.index[ok7])

    # A12: compressione 5d/60d -> RV dei 5 giorni successivi sopra la media 5d (ritorno verso 60d)
    rv5 = f["rv"].rolling(5).mean(); rv60 = f["rv"].rolling(60).mean()
    fut5 = f["rv"][::-1].rolling(5).mean()[::-1].shift(-1)   # media delle 5 sessioni successive (misura, non segnale)
    comp = (rv5 / rv60)
    m = comp.notna() & fut5.notna() & (comp < comp.rolling(250, min_periods=120).quantile(0.2).shift(1))
    q = np.log(fut5 / rv5)
    res["A12"] = C.rec("A12_compression_expansion", "giorni con RV5/RV60 nel quintile basso (soglia causale): log(RV media 5 sessioni dopo / RV5); atteso >0", q[m], f.index[m])

    for k, v in res.items():
        print(f"{k:8s} n={v['n']:5d} mean={v['mean']:+.4f} [{v['lo']:+.4f};{v['hi']:+.4f}] p2={v['p_two']:.4f}")
    # stabilita' per anno delle principali
    for nm, qq, mm in [("A1", (y - m22) ** 2 - (y - har) ** 2, ok), ("A2", (y - har) ** 2 - (y - har_on) ** 2, ok2),
                       ("A3", e * (-np.sign(rprev)), ok4), ("A3b", (y - har) ** 2 - (y - har_a) ** 2, ok5)]:
        print(nm, core.yearly(qq[mm], f.index[mm])["mean"].round(4).to_dict())


if __name__ == "__main__":
    main()
