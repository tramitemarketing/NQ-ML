"""Candidati CONGELATI della famiglia vol (binario «reale ma non incassabile», kind="regularity").

Ogni fn(bars, daily) restituisce una riga per sessione con `gross_pts` = quantita' misurata (NON punti di
prezzo: il nome della colonna e' quello richiesto dal controller). Test del controller: bilaterale sul
lordo, con segno atteso `expected_sign`. Tutte le quantita' usano solo dati <= sessione t (e per le
previsioni solo dati <= t-1). Funzionano su qualunque fase con il warmup dichiarato.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from lab.vol import common as C

HAR_WIN, HAR_MINP = 500, 250


def _rolling_ols_pred(y: pd.Series, X: pd.DataFrame, win=HAR_WIN, minp=HAR_MINP) -> pd.Series:
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


def _rows(q: pd.Series, bars: pd.DataFrame) -> pd.DataFrame:
    q = q[np.isfinite(q)]
    rb = bars[bars["rth"]]
    g = rb.groupby("session")
    t0 = pd.Series(g.apply(lambda x: x.index[0]))
    t1 = pd.Series(g.apply(lambda x: x.index[-1]))
    s = pd.DatetimeIndex(q.index)
    return pd.DataFrame({
        "session": s,
        "entry_ts": t0.reindex(s).to_numpy(),
        "exit_ts": t1.reindex(s).to_numpy(),
        "side": 1,
        "gross_pts": q.to_numpy(float),
    })


def _har(bars, daily):
    f = C.daily_features(bars, daily)
    y = f["logrv"]
    har = _rolling_ols_pred(y, f[["h1", "h5", "h22"]].shift(1))
    return f, y, har


def har_vs_mean22(bars: pd.DataFrame, daily: pd.DataFrame) -> pd.DataFrame:
    """q_t = (logRV_t - media22_{t-1})^2 - (logRV_t - HAR_{t-1})^2. logRV = log somma r5^2 RTH (in %^2).
    HAR = OLS di logRV su (logRV_{t-1}, media5, media22) stimata sulle 500 sessioni valide precedenti."""
    f, y, har = _har(bars, daily)
    m22 = y.rolling(22).mean().shift(1)
    q = (y - m22) ** 2 - (y - har) ** 2
    return _rows(q[har.notna() & m22.notna()], bars)


def leverage_sign(bars: pd.DataFrame, daily: pd.DataFrame) -> pd.DataFrame:
    """q_t = (logRV_t - HAR_{t-1}) * (-segno del rendimento close-close RTH di t-1). >0 = effetto leva."""
    f, y, har = _har(bars, daily)
    rprev = f["cc_ret_pct"].shift(1)
    q = (y - har) * (-np.sign(rprev))
    return _rows(q[har.notna() & rprev.notna()], bars)


def midday_variance_ratio(bars: pd.DataFrame, daily: pd.DataFrame) -> pd.DataFrame:
    """q_t = sum_{h in 12:30,13:30,14:30} R60_h^2 / sum r5^2 (stesse tre ore) - 1, rendimenti log 5m RTH
    su prezzi grezzi. <0 = ritorno alla media fra 5 e 60 minuti nelle ore centrali/pomeridiane."""
    f = C.daily_features(bars, daily)
    b5 = C.bars5_rth(bars)
    lc = np.log(b5["close"]); lo = np.log(b5["open"])
    prev = lc.groupby(level=0).shift(1)
    R = ((lc - prev).fillna(lc - lo) * 100).unstack("k")
    R = R.reindex(f.index)
    R = R[R.notna().sum(axis=1) == 78].loc[:, list(range(78))]
    sub = R.loc[:, 36:71]                                        # barre 12:30 .. 15:29
    grp = np.arange(36) // 12
    R60 = sub.T.groupby(grp).sum().T
    V = (sub ** 2).sum(axis=1)
    q = (R60 ** 2).sum(axis=1) / V - 1
    return _rows(q, bars)


CANDIDATES = [
    dict(
        id="vol_har_vs_mean22",
        description=("Per ogni sessione: errore quadratico della media mobile 22 sessioni di log RV RTH (5m) meno "
                     "errore quadratico di HAR-RV (OLS mobile 500 sessioni su logRV di ieri, media 5, media 22); "
                     "atteso >0: HAR prevede la volatilita' di domani meglio della media semplice"),
        rationale="Persistenza a memoria lunga della volatilita' (Corsi 2009, HAR-RV); fatto documentato su ogni mercato liquido",
        warmup_days=560,
        kind="regularity",
        expected_sign=+1,
        fn=har_vs_mean22,
        discovery=dict(n=1849, mean_net=0.1821, lo=0.1546, hi=0.2105, p_pos=0.0001, p_two=0.0001, years_pos="8/8",
                       note="unita': log(%^2)^2; R2 fuori campione HAR 0,624 vs media22 0,401, RW 0,546, media250 0,070"),
    ),
    dict(
        id="vol_leverage_sign",
        description=("Per ogni sessione: residuo HAR di log RV RTH (previsione con dati fino a t-1) moltiplicato per "
                     "-segno del rendimento close-close RTH di t-1; atteso >0: dopo un ribasso la vol supera la previsione, dopo un rialzo resta sotto"),
        rationale="Effetto leva / feedback di volatilita' (Black 1976, Christie 1982, Bollerslev-Litvinova-Tauchen 2006); asimmetria tipica degli indici azionari",
        warmup_days=560,
        kind="regularity",
        expected_sign=+1,
        fn=leverage_sign,
        discovery=dict(n=1849, mean_net=0.0640, lo=0.0385, hi=0.0888, p_pos=0.0001, p_two=0.0001, years_pos="7/8",
                       note="unita': log(%^2); 2017 negativo (-0,034)"),
    ),
    dict(
        id="vol_midday_variance_ratio",
        description=("Per ogni sessione: somma dei quadrati dei tre rendimenti orari 12:30-15:30 divisa per la somma dei "
                     "quadrati dei 36 rendimenti 5m delle stesse ore, meno 1; atteso <0: ritorno alla media intraday fra 5 e 60 minuti"),
        rationale=("Rendimenti 5m negativamente autocorrelati nelle ore centrali (liquidita' che assorbe gli squilibri, market making); "
                   "il progetto aveva gia' misurato VR<1 a 30-60m. Finestra 12:30-15:30 scelta DOPO aver visto le 7 ore: post hoc dichiarato"),
        warmup_days=0,
        kind="regularity",
        expected_sign=-1,
        fn=midday_variance_ratio,
        discovery=dict(n=2121, mean_net=-0.1168, lo=-0.1448, hi=-0.0881, p_pos=None, p_two=0.0001, years_pos="1/9 (8/9 negativi)",
                       note="adimensionale (VR-1); 2015 +0,009 unico anno non negativo; mattina 9:30-12:30 +0,044"),
    ),
]
