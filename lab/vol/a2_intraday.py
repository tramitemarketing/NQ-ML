"""Binario A, parte intraday: profilo a U, leverage intraday, volatilita' dopo shock, range vs moto
browniano, variance ratio. Segni attesi dichiarati nelle descrizioni prima di eseguire."""
from __future__ import annotations

import numpy as np
import pandas as pd

from lab import core
from lab.vol import common as C


def r5_matrix(bars, daily):
    f = C.daily_features(bars, daily)
    b5 = C.bars5_rth(bars)
    lc = np.log(b5["close"]); lo = np.log(b5["open"])
    prev = lc.groupby(level=0).shift(1)
    r = ((lc - prev).fillna(lc - lo) * 100).unstack("k")
    r = r.reindex(f.index)
    r = r.loc[:, list(range(78))]
    return f, r


def main():
    bars, daily = core.load("discovery")
    f, R = r5_matrix(bars, daily)
    R = R[R.notna().sum(1) == 78]
    A = R.abs()
    days = R.index
    res = {}
    # A4 profilo a U
    mid = A.loc[:, 30:53].mean(1)
    q = np.log(A.loc[:, 0:5].mean(1) / mid)
    res["A4a"] = C.rec("A4a_ushape_open", "log(|r5| medio 9:30-10:00 / |r5| medio 12:00-14:00); atteso >0", q, days)
    q = np.log(A.loc[:, 72:77].mean(1) / mid)
    res["A4b"] = C.rec("A4b_ushape_close", "log(|r5| medio 15:30-16:00 / |r5| medio 12:00-14:00); atteso >0", q, days)
    prof = A.median(0)
    print("profilo mediano |r5| (ogni 6 barre):", (prof.iloc[::6] / prof.loc[30:53].mean()).round(2).to_dict())

    # A5 leverage intraday a 30m
    R30 = R.T.groupby(np.arange(78) // 6).sum().T              # 13 blocchi
    V30 = (R ** 2).T.groupby(np.arange(78) // 6).sum().T
    rows = []
    for j in range(1, 12):  # blocchi 1..11 -> successivo; escludo il primo (apertura) come segnale
        qj = -np.sign(R30[j]) * np.log(V30[j + 1] / V30[j])
        rows.append(pd.DataFrame({"q": qj, "d": days}))
    L5 = pd.concat(rows)
    L5 = L5[np.isfinite(L5.q)]
    res["A5"] = C.rec("A5_intraday_leverage30", "-segno(R 30m) x log(RV 30m successivi / RV 30m correnti), blocchi 10:00-15:30; atteso >0", L5.q, L5.d)

    # A6 shock: |r5| > 4 x baseline causale (mediana |r5| stesso k nelle 20 sessioni precedenti)
    base = A.rolling(20, min_periods=15).median().shift(1)
    ev_rows, ev_rows2 = [], []
    Av, Bv = A.to_numpy(), base.to_numpy()
    for i in range(len(A)):
        for k in range(0, 78 - 24):
            if np.isfinite(Bv[i, k]) and Av[i, k] > 4 * Bv[i, k]:
                nxt = Av[i, k + 1:k + 13].mean() / Bv[i, k + 1:k + 13].mean()
                nxt2 = Av[i, k + 13:k + 25].mean() / Bv[i, k + 13:k + 25].mean()
                ev_rows.append((days[i], np.log(nxt), np.log(nxt2)))
    ev = pd.DataFrame(ev_rows, columns=["d", "q1", "q2"])
    ev = ev[np.isfinite(ev.q1) & np.isfinite(ev.q2)]
    res["A6a"] = C.rec("A6a_shock_vol_next60", "dopo |r5|>4x baseline causale: log(|r5| medio nei 60m dopo / baseline stessa ora); atteso >0", ev.q1, ev.d)
    res["A6b"] = C.rec("A6b_shock_vol_60_120", "come A6a ma 60-120m dopo; atteso >0 (decadimento)", ev.q2, ev.d)
    # placebo: stessa quantita' su tutte le barre (livello medio del giorno rispetto alla baseline)
    # A7 range vs browniano: range^2 / RV5 - 4 ln 2 ; atteso <0 (ritorno alla media intraday)
    rv = (R ** 2).sum(1)
    rng = f.loc[days, "raw_high"] - f.loc[days, "raw_low"]
    rng_pct = np.log(f.loc[days, "raw_high"] / f.loc[days, "raw_low"]) * 100
    q = rng_pct ** 2 / rv - 4 * np.log(2)
    res["A7"] = C.rec("A7_range_vs_brownian", "range RTH^2 / RV(5m) - 4ln2 (Parkinson): atteso <0 (VR<1)", q, days)
    # A7b: stesso con RV a 30m (meno rumore microstrutturale)
    rv30 = (R30 ** 2).sum(1)
    q = rng_pct ** 2 / rv30 - 4 * np.log(2)
    res["A7b"] = C.rec("A7b_range_vs_brownian_rv30", "range RTH^2 / RV(30m) - 4ln2; esplorativo (segno atteso <0)", q, days)
    # A7c: MFE+MAE nella prima ora dal prezzo d'apertura, in unita' di sigma della prima ora (RV 5m della prima ora)
    # quantita': (max escursione su - max escursione giu') relativa: simmetria -> atteso 0 ; qui atteso: |.| non misurato
    # A8 variance ratio giornaliero 30m vs 5m
    q = rv30 / rv - 1
    res["A8"] = C.rec("A8_vr_30m_5m_daily", "VR(6) giornaliero: sum R30^2 / sum r5^2 - 1; atteso <0", q, days)
    R60 = R.T.groupby(np.arange(78) // 12).sum().T
    V60 = (R ** 2).T.groupby(np.arange(78) // 12).sum().T
    for h in range(7):
        qh = R60[h] ** 2 / V60[h] - 1
        lab = ["9:30", "10:30", "11:30", "12:30", "13:30", "14:30", "15:30(30m)"][h]
        res[f"A8_h{h}"] = C.rec(f"A8_vr_hour{h}", f"VR per ora {lab}: R60^2/sum r5^2 - 1; esplorativo, atteso <0", qh, days)
    for k, v in res.items():
        print(f"{k:8s} n={v['n']:6d} mean={v['mean']:+.4f} [{v['lo']:+.4f};{v['hi']:+.4f}] p2={v['p_two']:.4f}")
    print("A8 per anno", core.yearly(rv30 / rv - 1, days)["mean"].round(4).to_dict())
    print("A7 per anno", core.yearly(rng_pct ** 2 / rv - 4 * np.log(2), days)["mean"].round(4).to_dict())
    print("A6a per anno", core.yearly(ev.q1, ev.d)["mean"].round(3).to_dict(), "n ev", len(ev))


if __name__ == "__main__":
    main()
