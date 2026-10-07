"""F7 tempo del volume e F8 irreversibilita' temporale.
F7: barre di volume RTH (soglia = volume RTH medio delle 20 sessioni PRECEDENTI / 78, aggregando barre 1m) contro
    barre di tempo 5m: curtosi in eccesso dei rendimenti standardizzati per giorno, autocorrelazione lag 1.
F8: per sessione, sui rendimenti 5m RTH standardizzati: A = mean(z_t^2 z_{t+1}) - mean(z_t z_{t+1}^2)
    (asimmetria temporale; 0 per una serie reversibile). Predice (i) il log RV di domani oltre all'HAR
    e al rendimento di oggi, (ii) la direzione dell'RTH di domani (sign(A) x rendimento RTH di domani, punti)?"""
import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy.stats import kurtosis

from lab.r2_footprints import common as C

pd.set_option("display.width", 250)

if __name__ == "__main__":
    D, daily = C.get()
    ok = D["valid"] & D["in_phase"]
    sess = D["sess"]
    a0, b0 = C.sm_of("09:30"), C.sm_of("16:00")
    V = D["V0"][:, a0:b0]
    Cl = D["Cf"][:, a0:b0]
    O0 = D["Of"][:, a0]
    # ---------- F7
    vol20 = pd.Series(np.where(D["valid"], V.sum(1), np.nan)).shift(1).rolling(20, min_periods=10).mean().to_numpy()
    kt, kv, act, acv, nvb = [], [], [], [], []
    for r in np.where(ok & np.isfinite(vol20))[0]:
        thr = vol20[r] / 78
        cv = np.cumsum(V[r])
        idx = np.searchsorted(cv, np.arange(1, int(cv[-1] // thr) + 1) * thr)   # barra 1m in cui si chiude la barra di volume
        idx = np.unique(np.minimum(idx, len(cv) - 1))
        pv = np.concatenate([[O0[r]], Cl[r, idx]])
        rv = np.diff(pv)
        pt = np.concatenate([[O0[r]], Cl[r, 4::5]])
        rt = np.diff(pt)
        if len(rv) < 20 or np.std(rv) == 0 or np.std(rt) == 0:
            continue
        zv, zt = rv / rv.std(), rt / rt.std()
        kv.append(zv); kt.append(zt)
        acv.append(np.corrcoef(zv[:-1], zv[1:])[0, 1]); act.append(np.corrcoef(zt[:-1], zt[1:])[0, 1])
        nvb.append(len(rv))
    kv_all, kt_all = np.concatenate(kv), np.concatenate(kt)
    print("F7 curtosi eccesso pooled: volume", round(kurtosis(kv_all), 3), "tempo", round(kurtosis(kt_all), 3),
          "| barre di volume/giorno", round(np.mean(nvb), 1))
    days_ok = sess[ok & np.isfinite(vol20)][:len(kv)]
    kd = np.array([kurtosis(a) for a in kv]) - np.array([kurtosis(b) for b in kt])
    st = C.rec("F7_kurt_vol_minus_time", "F7 curtosi eccesso giornaliera: barre di volume (~78/g) meno barre 5m", kd, days_ok,
               unit="kurtosis", pooled_vol=float(kurtosis(kv_all)), pooled_time=float(kurtosis(kt_all)))
    print("  per giorno diff", round(st["mean"], 3), (round(st["lo"], 3), round(st["hi"], 3)))
    st = C.rec("F7_ac1_vol_minus_time", "F7 autocorrelazione lag1: barre di volume meno barre 5m", np.array(acv) - np.array(act),
               days_ok, unit="corr", ac_vol=float(np.nanmean(acv)), ac_time=float(np.nanmean(act)))
    print("  AC1 volume", round(np.nanmean(acv), 4), "tempo", round(np.nanmean(act), 4), "diff CI", (round(st["lo"], 4), round(st["hi"], 4)))

    # ---------- F8
    raw0 = D["rawCf"][:, a0]
    r5 = np.diff(np.concatenate([O0[:, None], Cl[:, 4::5]], 1), axis=1) / raw0[:, None] * 1e4
    sd = np.nanstd(r5, 1, keepdims=True)
    z = r5 / sd
    A = np.nanmean(z[:, :-1] ** 2 * z[:, 1:], 1) - np.nanmean(z[:, :-1] * z[:, 1:] ** 2, 1)
    logrv = np.log(np.nansum(r5 ** 2, 1))
    ret = (Cl[:, -1] - O0) / raw0 * 1e4
    df = pd.DataFrame({"A": A, "lrv": logrv, "ret": ret, "ok": D["valid"], "inp": D["in_phase"],
                       "pts": Cl[:, -1] - O0}, index=sess)
    df.loc[~df.ok, ["A", "lrv", "ret", "pts"]] = np.nan
    df["m5"] = df.lrv.rolling(5, min_periods=3).mean()
    df["m22"] = df.lrv.rolling(22, min_periods=10).mean()
    df["y"] = df.lrv.shift(-1)
    df["neg"] = np.minimum(df.ret, 0)
    df["pts_next"] = df.pts.shift(-1)
    df["next_sess"] = pd.Series(sess, index=sess).shift(-1)
    d = df[df.inp].dropna(subset=["A", "lrv", "m5", "m22", "y", "ret"])
    X = sm.add_constant(d[["lrv", "m5", "m22", "ret", "neg", "A"]])
    fit = sm.OLS(d.y, X).fit(cov_type="HAC", cov_kwds={"maxlags": 5})
    print(fit.summary().tables[1])
    C.rec("F8_A_predicts_logrv", "F8 coefficiente di A (irreversibilita' 5m di oggi) nel HAR del log RV di domani, "
          "controllando rendimento e parte negativa (t HAC)", np.array([fit.params["A"]]), np.array([d.index[0]]),
          t_hac=float(fit.tvalues["A"]), n_obs=int(len(d)))
    # direzione
    dd = df[df.inp].dropna(subset=["A", "pts_next"])
    for q in [0.0, 0.5]:
        thr = dd.A.abs().shift(1).rolling(250, min_periods=100).quantile(q) if q > 0 else 0
        m = dd.A.abs() > thr
        g = np.sign(dd.A[m]) * dd.pts_next[m]
        st = C.full_report(f"F8_signA_next_rth_q{q}", f"F8 sign(A di oggi) x rendimento RTH di domani 09:30-16:00, lordo "
                           f"punti, |A| > quantile causale {q}", pd.DataFrame({"session": dd.next_sess[m].to_numpy(),
                                                                               "gross_pts": g.to_numpy()}), net=False)
        print("F8 dir q", q, C.fmt(st))
    # A e la direzione di OGGI (descrittivo: A e' un proxy del trend?)
    print("corr(A, ret oggi)", round(d.A.corr(d.ret), 3), "corr(A, ret domani)", round(dd.A.corr(dd.pts_next), 3))
