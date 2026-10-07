"""Seconda tornata: (A) VR per regime, placebo dello shock, VR di mezzogiorno aggregato;
(B) notte condizionata alla vol (premio per il rischio overnight). Tutto registrato."""
from __future__ import annotations

import numpy as np
import pandas as pd

from lab import core
from lab.vol import common as C
from lab.vol import strategies as S
from lab.vol.a2_intraday import r5_matrix
from lab.vol.b_tests import Ctx, terc


def overnight_trades(M, f, side: pd.Series):
    """Long/short dal close RTH (15:59) di t-1 all'open 9:30 di t, prezzi adj. session = t."""
    rows = []
    sd = side.reindex(M["sess"]).fillna(0).to_numpy()
    for i in range(1, len(M["sess"])):
        if sd[i] == 0:
            continue
        s, sp = M["sess"][i], M["sess"][i - 1]
        # salta se tra le due sessioni valide c'e' un buco (> 4 giorni): notte non contigua
        if (s - sp).days > 4:
            continue
        g = f.at[s, "rth_open"] - f.at[sp, "rth_close"]
        rows.append((s, S._ts(M, i - 1, 389), S._ts(M, i, 0), int(sd[i]), sd[i] * g))
    return S.mk(rows)


def main():
    X = Ctx()
    f, reg, M, bars, daily = X.f, X.reg, X.M, X.bars, X.daily
    vt = terc(reg["pct"])
    # ---------- A: VR per regime
    _, R = r5_matrix(bars, daily)
    R = R[R.notna().sum(1) == 78]
    rv = (R ** 2).sum(1)
    R30 = R.T.groupby(np.arange(78) // 6).sum().T
    vr = (R30 ** 2).sum(1) / rv - 1
    k = vt.reindex(R.index)
    for lab in ["low", "high"]:
        m = (k == lab).to_numpy()
        st = C.rec(f"A15_vr30_regime_{lab}", f"VR(30m/5m)-1 giornaliero nei giorni a vol prevista {lab}; esplorativo", vr[m], R.index[m])
        print("A15", lab, round(st["mean"], 4), round(st["lo"], 4), round(st["hi"], 4))
    # A8m: VR di mezzogiorno aggregato (12:30-15:30, tre ore): sum R60^2 / sum r5^2 - 1
    R60 = R.T.groupby(np.arange(78) // 12).sum().T
    V60 = (R ** 2).T.groupby(np.arange(78) // 12).sum().T
    q = (R60[[3, 4, 5]] ** 2).sum(1) / V60[[3, 4, 5]].sum(1) - 1
    st = C.rec("A8m_vr_midday_3h", "VR 60m/5m aggregato sulle ore 12:30-15:30: sum R60^2/sum r5^2 - 1; atteso <0 (post hoc: scelto dopo A8_h*)", q, R.index)
    print("A8m", st["mean"], st["lo"], st["hi"], core.yearly(q, R.index)["mean"].round(3).to_dict())
    q0 = (R60[[0, 1, 2]] ** 2).sum(1) / V60[[0, 1, 2]].sum(1) - 1
    st = C.rec("A8am_vr_morning_3h", "VR 60m/5m aggregato 9:30-12:30 (confronto); atteso ~0", q0, R.index)
    print("A8am", st["mean"], st["lo"], st["hi"])
    # A8m per regime
    for lab in ["low", "high"]:
        m = (k == lab).to_numpy()
        st = C.rec(f"A8m_regime_{lab}", f"VR mezzogiorno per vol prevista {lab}", q[m], R.index[m])
        print("A8m", lab, round(st["mean"], 4), round(st["lo"], 4), round(st["hi"], 4))
    # A6c placebo: livello di |r5| nei 60m PRIMA dello shock (se prima era gia' alto, A6 e' solo livello del giorno)
    A = R.abs()
    base = A.rolling(20, min_periods=15).median().shift(1)
    Av, Bv = A.to_numpy(), base.to_numpy()
    rows = []
    for i in range(len(A)):
        for kk in range(12, 78 - 12):
            if np.isfinite(Bv[i, kk]) and Av[i, kk] > 4 * Bv[i, kk]:
                pre = np.log(Av[i, kk - 12:kk].mean() / Bv[i, kk - 12:kk].mean())
                post = np.log(Av[i, kk + 1:kk + 13].mean() / Bv[i, kk + 1:kk + 13].mean())
                rows.append((A.index[i], post - pre))
    ev = pd.DataFrame(rows, columns=["d", "q"])
    ev = ev[np.isfinite(ev.q)]
    st = C.rec("A6c_shock_post_minus_pre", "dopo |r5|>4x baseline: log vol 60m dopo - log vol 60m prima (relativi a baseline); atteso >0", ev.q, ev.d)
    print("A6c", st)
    print("A6c anni", core.yearly(ev.q, ev.d)["mean"].round(3).to_dict())

    # ---------- B12/B13: notte condizionata alla vol
    one = pd.Series(1, index=M["sess"])
    t = overnight_trades(M, f, one)
    X.show("B12_long_overnight_all", "long notte (15:59 t-1 -> 9:30 t), tutti (riferimento passivo)", t)
    X.split("B12_long_overnight_vol", "long notte per terzile di vol prevista (premio per il rischio notturno)", t, vt)
    shock = (f["logrv"] - reg["fc"])
    sq = terc(C.rolling_pct_rank(shock, 250, 120).shift(1))   # shock del giorno t-1, noto alle 16:00 di t-1
    X.split("B13_long_overnight_after_shock", "long notte per terzile di shock di vol del giorno appena chiuso", t, sq)
    down = (f["rth_ret_pct"] < 0).shift(1)
    kk = (down.reindex(pd.DatetimeIndex(t["session"])).fillna(False).to_numpy().astype(bool)) & \
         (vt.reindex(pd.DatetimeIndex(t["session"])).to_numpy() == "high")
    X.show("B13b_long_overnight_down_highvol", "long notte dopo giorno RTH in ribasso con vol prevista alta", t[kk].reset_index(drop=True))


if __name__ == "__main__":
    main()
