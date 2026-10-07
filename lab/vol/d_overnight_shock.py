"""Approfondimento B13 (long notte dopo uno shock di volatilita'): sensibilita', beta con CI, anni, placebo.
Ogni vista registrata."""
from __future__ import annotations

import numpy as np
import pandas as pd

from lab import core
from lab.controller import beta_component
from lab.vol import common as C
from lab.vol.b_tests import Ctx
from lab.vol.c_more import overnight_trades


def main():
    X = Ctx()
    f, reg, M, bars = X.f, X.reg, X.M, X.bars
    one = pd.Series(1, index=M["sess"])
    T = overnight_trades(M, f, one)
    sidx = pd.DatetimeIndex(T["session"])
    shock = f["logrv"] - reg["fc"]
    sp = C.rolling_pct_rank(shock, 250, 120).shift(1).reindex(sidx).to_numpy()
    beta = beta_component(bars, T)
    net = T["gross_pts"].to_numpy() - core.COST_RT_POINTS
    atr = reg["atr20"].reindex(sidx).to_numpy()

    def view(tid, desc, m):
        t = T[m].reset_index(drop=True)
        st = X.show(tid, desc, t)
        stb = core.day_block_bootstrap(net[m] - beta[m], T["session"].values[m])
        yb = core.yearly(net[m] - beta[m], T["session"][m])["mean"].round(2).to_dict()
        print(f"    beta-adj CI [{stb['lo']:+.3f};{stb['hi']:+.3f}] p+={stb['p_pos']:.3f}  anni beta-adj {yb}")
        return st, stb

    # sensibilita' della soglia (percentile causale dello shock di ieri)
    for thr in [0.5, 0.6, 0.75, 0.8, 0.9]:
        view(f"B13s_thr{int(thr*100)}", f"long notte se shock di vol del giorno appena chiuso > percentile {thr}", np.nan_to_num(sp, nan=-1) > thr)
    # definizione alternativa: range RTH di oggi / ATR20 (shock in range)
    rr = (f["rth_range_pts"] / f["atr20"])
    rp = C.rolling_pct_rank(rr, 250, 120).shift(1).reindex(sidx).to_numpy()
    view("B13alt_range_shock_top3", "long notte se range RTH del giorno chiuso / ATR20 nel terzile alto (definizione alternativa)", np.nan_to_num(rp, nan=-1) > 2 / 3)
    # placebo: stesso filtro ma notte PRECEDENTE (prima dello shock) -> se positivo, e' solo regime non shock
    # (la notte t-1 -> t precede il giorno t in cui si misura lo shock: uso lo shock di t sulla notte che entra in t)
    sp_same = C.rolling_pct_rank(shock, 250, 120).reindex(sidx).to_numpy()   # shock del giorno t (DOPO la notte): solo placebo, non tradabile
    view("B13plac_night_before_shock", "PLACEBO non tradabile: notte che PRECEDE un giorno con shock nel terzile alto", np.nan_to_num(sp_same, nan=-1) > 2 / 3)
    # in unita' ATR: media netta normalizzata per terzile alto vs resto
    m = np.nan_to_num(sp, nan=-1) > 2 / 3
    r_atr = (T["gross_pts"].to_numpy() - beta) / atr
    st = C.rec("B13_atr_excess_high_minus_rest", "(lordo - beta)/ATR20: media nel terzile alto di shock (in ATR)", r_atr[m], T["session"].values[m])
    st2 = core.day_block_bootstrap(r_atr[~m & np.isfinite(sp)], T["session"].values[~m & np.isfinite(sp)])
    print("ATR beta-adj alto", st, "\nresto", st2)
    # decomposizione: segno del giorno dello shock (shock ribassista vs rialzista)
    dn = (f["rth_ret_pct"] < 0).shift(1).reindex(sidx).fillna(False).to_numpy().astype(bool)
    view("B13_high_down", "long notte, shock alto e giorno chiuso in ribasso", m & dn)
    view("B13_high_up", "long notte, shock alto e giorno chiuso in rialzo", m & ~dn)


if __name__ == "__main__":
    main()
