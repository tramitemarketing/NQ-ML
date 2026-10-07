"""F8b - l'irreversibilita' temporale A migliora FUORI CAMPIONE la previsione del log RV di domani?
Base: HAR (lrv, media 5, media 22) + rendimento di oggi e sua parte negativa (effetto leva, gia' noto).
Esteso: base + A. OLS mobile sulle 500 sessioni valide precedenti (min 250), stimata solo su sessioni < t.
Quantita' per sessione: err_base^2 - err_esteso^2 (>0 = A aiuta). Varianti dichiarate: A su 5m e su 1m;
A con z_{t+1} (lag 1) oppure somma dei lag 1..3."""
import numpy as np
import pandas as pd

from lab.r2_footprints import common as C

pd.set_option("display.width", 250)


def irrev(r, lags=(1,)):
    sd = np.nanstd(r, 1, keepdims=True)
    z = r / sd
    out = 0
    for L in lags:
        out = out + np.nanmean(z[:, :-L] ** 2 * z[:, L:], 1) - np.nanmean(z[:, :-L] * z[:, L:] ** 2, 1)
    return out


def table(D, step=5, lags=(1,)):
    a0, b0 = C.sm_of("09:30"), C.sm_of("16:00")
    Cl = D["Cf"][:, a0:b0]
    O0 = D["Of"][:, a0]
    raw0 = D["rawCf"][:, a0]
    r5 = np.diff(np.concatenate([O0[:, None], Cl[:, 4::5]], 1), axis=1) / raw0[:, None] * 1e4
    rs = r5 if step == 5 else np.diff(np.concatenate([O0[:, None], Cl], 1), axis=1) / raw0[:, None] * 1e4
    df = pd.DataFrame({"A": irrev(rs, lags), "lrv": np.log(np.nansum(r5 ** 2, 1)),
                       "ret": (Cl[:, -1] - O0) / raw0 * 1e4}, index=D["sess"])
    df.loc[~D["valid"]] = np.nan
    df = df.dropna()                                        # solo sessioni valide, in ordine
    df["m5"] = df.lrv.rolling(5).mean()
    df["m22"] = df.lrv.rolling(22).mean()
    df["neg"] = np.minimum(df.ret, 0)
    df["y"] = df.lrv.shift(-1)
    df["target_sess"] = pd.Series(df.index, index=df.index).shift(-1)
    return df.dropna()


def oos(df, extra=("A",), win=500, minw=250):
    base = ["lrv", "m5", "m22", "ret", "neg"]
    X0 = np.column_stack([np.ones(len(df))] + [df[c] for c in base])
    X1 = np.column_stack([X0] + [df[c] for c in extra])
    y = df.y.to_numpy()
    e0 = np.full(len(df), np.nan); e1 = e0.copy()
    for t in range(minw + 1, len(df)):
        lo = max(0, t - 1 - win)
        s = slice(lo, t - 1)            # righe con y (= lrv di t) gia' noto: fino a t-2 incluso -> y della riga t-1 e' lrv_t
        b0 = np.linalg.lstsq(X0[s], y[s], rcond=None)[0]
        b1 = np.linalg.lstsq(X1[s], y[s], rcond=None)[0]
        e0[t] = y[t] - X0[t] @ b0
        e1[t] = y[t] - X1[t] @ b1
    return e0, e1


if __name__ == "__main__":
    D, daily = C.get()
    for step in [5, 1]:
        for lags in [(1,), (1, 2, 3)]:
            df = table(D, step, lags)
            e0, e1 = oos(df)
            q = e0 ** 2 - e1 ** 2
            m = np.isfinite(q)
            st = C.rec(f"F8b_oos_A_step{step}_lags{len(lags)}", f"F8b OOS mobile 500: errore^2 HAR+leva meno errore^2 "
                       f"HAR+leva+A (A su {step}m, lag {lags}); >0 = A aiuta", q[m], df.target_sess.to_numpy()[m],
                       unit="log-var^2", r2_gain=float(1 - np.nansum(e1 ** 2) / np.nansum(e0 ** 2)))
            y = pd.Series(q[m]).groupby(pd.DatetimeIndex(df.target_sess.to_numpy()[m]).year).mean()
            print(step, lags, "n", st["n"], "mean", round(st["mean"], 5), (round(st["lo"], 5), round(st["hi"], 5)),
                  "p2", st["p_two"], "gain MSE %", round(100 * (1 - np.nansum(e1 ** 2) / np.nansum(e0 ** 2)), 3),
                  "anni+", f"{(y > 0).sum()}/{len(y)}", "sd(A)", round(df.A.std(), 3))
