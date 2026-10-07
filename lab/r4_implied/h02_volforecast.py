"""H02: la vol implicita aggiunge informazione all'HAR per prevedere la volatilita' di S? (regolarita')
Tutte le previsioni: OLS mobile sulle 500 sessioni precedenti (min 250), regressori noti all'apertura di S
(HAR: logRV <= S-1; implicita: chiusura CBOE di S-1). Statistica per sessione:
  q = (y - prev_base)^2 - (y - prev_aumentata)^2   atteso >0 (guadagno di MSE fuori campione)."""
from __future__ import annotations

import numpy as np
import pandas as pd

from lab.r4_implied import common as C
from lab.vol.candidates import _rolling_ols_pred


def main():
    f = C.load_features()
    f["ts3_log"] = np.log(f["ts_3m_s"])
    f["ts9_log"] = np.log(f["ts_9d_s"])
    f["vvix_log"] = np.log(f["VVIX"])
    f["skew_x"] = f["SKEW"]
    f["iv9_log"] = np.log(f["VIX9D"] ** 2 / 252)
    f["ivvix_log"] = np.log(f["VIX"] ** 2 / 252)
    har = ["h1", "h5", "h22"]
    Xh = f[har].shift(1)
    y = f["logrv"]
    base = f["har"]

    def q_of(y, b, a):
        m = b.notna() & a.notna() & y.notna()
        return ((y - b) ** 2 - (y - a) ** 2)[m]

    def aug(extra, target=y, xbase=Xh):
        X = pd.concat([xbase, f[extra]], axis=1)
        return _rolling_ols_pred(target, X)

    tests = []
    # 1 iv aggiunta a HAR
    p_iv = aug(["iv_log"])
    tests.append(("H02_har_plus_ivxn", "logRV: HAR + log(VXN^2/252) vs HAR", q_of(y, base, p_iv)))
    # 2 solo implicita vs HAR
    p_ivonly = _rolling_ols_pred(y, f[["iv_log"]])
    tests.append(("H02_ivonly_vs_har", "logRV: solo log VXN^2 vs HAR (atteso <0 se HAR migliore)", q_of(y, base, p_ivonly)))
    # 3 + term structure
    p_ts = aug(["iv_log", "ts9_log", "ts3_log"])
    tests.append(("H02_iv_plus_ts_vs_iv", "logRV: HAR+iv+log(VIX9D/VIX)+log(VIX/VIX3M) vs HAR+iv", q_of(y, p_iv, p_ts)))
    p_9d = aug(["iv_log", "iv9_log"])
    tests.append(("H02_iv_plus_iv9d_vs_iv", "logRV: HAR+iv+log VIX9D^2 vs HAR+iv", q_of(y, p_iv, p_9d)))
    p_vvix = aug(["iv_log", "vvix_log"])
    tests.append(("H02_iv_plus_vvix_vs_iv", "logRV: HAR+iv+log VVIX vs HAR+iv", q_of(y, p_iv, p_vvix)))
    p_skew = aug(["iv_log", "skew_x"])
    tests.append(("H02_iv_plus_skew_vs_iv", "logRV: HAR+iv+SKEW vs HAR+iv", q_of(y, p_iv, p_skew)))
    p_vix = aug(["iv_log", "ivvix_log"])
    tests.append(("H02_iv_plus_vix_vs_iv", "logRV: HAR+VXN+VIX vs HAR+VXN", q_of(y, p_iv, p_vix)))
    # overnight range aggiunto (regolarita' confermata del giro 1) - l'implicita aggiunge anche dopo?
    f["lon"] = np.log(f["on_range_pct"])
    Xh_on = pd.concat([Xh, f[["lon"]]], axis=1)
    p_on = _rolling_ols_pred(y, Xh_on)
    p_on_iv = _rolling_ols_pred(y, pd.concat([Xh_on, f[["iv_log"]]], axis=1))
    tests.append(("H02_har_on_plus_iv", "logRV: HAR+range notturno+iv vs HAR+range notturno (iv nota dall'apertura)", q_of(y, p_on, p_on_iv)))
    # log range RTH come target
    yr = f["lograng"]
    Xr = pd.concat([f["lograng"].shift(1), f["lograng"].rolling(5).mean().shift(1), f["lograng"].rolling(22).mean().shift(1)], axis=1)
    Xr.columns = ["r1", "r5", "r22"]
    pr = _rolling_ols_pred(yr, Xr)
    pr_iv = _rolling_ols_pred(yr, pd.concat([Xr, f[["iv_log"]]], axis=1))
    tests.append(("H02_range_har_plus_iv", "log range RTH: HAR-range + iv vs HAR-range", q_of(yr, pr, pr_iv)))
    # 5 sessioni avanti: media logRV S..S+4
    y5 = pd.concat([y.shift(-j) for j in range(5)], axis=1).mean(axis=1)
    # attenzione: la regressione mobile su y5 usa target futuri fino a t+4 -> stima solo con target maturati
    y5_lag = y5.copy()
    X5 = Xh
    # target maturati: per prevedere a t uso le righe <= t-5 (shift del target di 5 al fitting)
    def roll_pred_h(target, X, h):
        Xv = np.column_stack([np.ones(len(X)), X.to_numpy()]); yv = target.to_numpy()
        ok = np.isfinite(Xv).all(1) & np.isfinite(yv); out = np.full(len(yv), np.nan)
        for t in range(len(yv)):
            if not np.isfinite(Xv[t]).all():
                continue
            hi = t - h + 1  # righe con target interamente <= t-1
            lo = max(0, hi - 500)
            if hi <= lo:
                continue
            m = ok[lo:hi]
            if m.sum() < 250:
                continue
            b, *_ = np.linalg.lstsq(Xv[lo:hi][m], yv[lo:hi][m], rcond=None)
            out[t] = Xv[t] @ b
        return pd.Series(out, index=target.index)
    p5 = roll_pred_h(y5, Xh, 5)
    p5_iv = roll_pred_h(y5, pd.concat([Xh, f[["iv_log"]]], axis=1), 5)
    tests.append(("H02_week_har_plus_iv", "media logRV S..S+4: HAR + iv vs HAR (fit su target maturati)", q_of(y5, p5, p5_iv)))
    # gap implicita-prevista predice la sorpresa? corr per sessione: z(vrp) * (y - har)
    sur = y - base
    v = f["vrp_har_s"]
    z = (v - v.rolling(250, min_periods=120).mean().shift(1)) / v.rolling(250, min_periods=120).std().shift(1)
    tests.append(("H02_vrp_predicts_surprise", "z(VRP_har, 250 causale) * (logRV - HAR): >0 = quando l'implicita supera la previsione la vol sorprende in alto",
                  (z * sur).dropna()))
    for tid, desc, q in tests:
        st = C.rec(tid, desc, q.to_numpy(), q.index.values)
        extra = ""
        print(C.fmt(tid, st))
    # R2 fuori campione
    m = base.notna() & p_iv.notna()
    sst = ((y[m] - y[m].mean()) ** 2).sum()
    for nm, p in [("HAR", base), ("HAR+iv", p_iv), ("iv", p_ivonly), ("HAR+iv+ts", p_ts), ("HAR+on", p_on), ("HAR+on+iv", p_on_iv)]:
        mm = m & p.notna()
        print(nm, "R2oos", 1 - ((y[mm] - p[mm]) ** 2).sum() / ((y[mm] - y[mm].mean()) ** 2).sum())


if __name__ == "__main__":
    main()
