"""Binario B: direzione condizionata al regime di volatilita' (discovery). Ogni vista e' registrata.
Unita' primaria: punti netti per contratto (costi 0,75). Diagnostica: netto in ATR20, beta del controller."""
from __future__ import annotations

import numpy as np
import pandas as pd

from lab import core
from lab.controller import beta_component
from lab.vol import common as C
from lab.vol import strategies as S


def terc(p):
    return pd.cut(p, [-0.01, 1 / 3, 2 / 3, 1.01], labels=["low", "mid", "high"])


class Ctx:
    def __init__(self):
        self.bars, self.daily = core.load("discovery")
        self.f = C.daily_features(self.bars, self.daily)
        self.M = S.rth_matrix(self.bars, self.daily)
        self.reg = S.regime(self.daily, self.bars, self.f)
        self.out = []

    def show(self, tid, desc, t, extra_rec=True):
        if len(t) == 0:
            print(tid, "vuoto"); return None
        st = C.trade_stats(t, atr=self.reg["atr20"])
        beta = beta_component(self.bars, t)
        net = t["gross_pts"].to_numpy() - core.COST_RT_POINTS
        stb = core.day_block_bootstrap(net - beta, t["session"].values)
        st["beta_adj_mean"] = stb["mean"]
        st["beta_mean"] = float(np.mean(beta))
        core.record(C.FAM, tid, desc, "discovery", st)
        print(f"{tid:34s} n={st['n']:5d} net={st['mean']:+7.3f} [{st['lo']:+7.3f};{st['hi']:+7.3f}] p+={st['p_pos']:.3f} "
              f"gross={st['gross_mean']:+7.3f} atr={st.get('net_atr_mean', np.nan):+.4f} yrs={st['years_pos']} "
              f"dt20={st['drop_top20']:+.3f} long={st['long_share']:.2f} betaadj={stb['mean']:+.3f}")
        self.out.append((tid, st))
        return st

    def split(self, tid, desc, t, key: pd.Series):
        """key: Serie indicizzata per sessione con etichette (es. terzili)."""
        k = key.reindex(pd.DatetimeIndex(t["session"])).to_numpy()
        for lab in ["low", "mid", "high"]:
            self.show(f"{tid}_{lab}", f"{desc} | sottoinsieme {lab}", t[k == lab].reset_index(drop=True))


def flip(t):
    t = t.copy(); t["side"] = -t["side"]; t["gross_pts"] = -t["gross_pts"]; return t


def main():
    X = Ctx()
    f, reg, M, bars, daily = X.f, X.reg, X.M, X.bars, X.daily
    vt = terc(reg["pct"])                          # terzili di vol prevista (causali)

    # ---- B1 rottura IB 60m, condizionata al regime
    t = S.ib_breakout(bars, daily, 60, M=M)
    X.show("B1_ib60_breakout_all", "rottura IB 60m, uscita 15:59, tutti i giorni (riferimento, ORB-like dichiarato)", t)
    X.split("B1_ib60_breakout_vol", "rottura IB 60m per terzile di vol prevista", t, vt)
    k = vt.reindex(pd.DatetimeIndex(t["session"])).to_numpy()
    comb = pd.concat([t[k == "high"], flip(t[k == "low"])]).sort_values("entry_ts").reset_index(drop=True)
    X.show("B1s_breakout_high_fade_low", "breakout IB60 se vol prevista alta, fade se bassa (ipotesi del brief)", comb)

    # ---- B2 direzione prima ora, condizionata a range prima ora / ATR20
    t = S.first_hour_follow(bars, daily, 60, M=M)
    ibr = pd.Series(np.nanmax(M["high"][:, :60], 1) - np.nanmin(M["low"][:, :60], 1), index=M["sess"])
    ratio = ibr / reg["atr20"].reindex(M["sess"])
    rr = terc(C.rolling_pct_rank(ratio, 250, 120))
    X.show("B2_firsthour_follow_all", "segui la direzione 9:30-10:30 dalle 10:30 alle 15:59, tutti", t)
    X.split("B2_firsthour_follow_ibratio", "segui prima ora, per terzile di range IB/ATR20 (percentile causale)", t, rr)
    X.split("B2b_firsthour_follow_vol", "segui prima ora, per terzile di vol prevista", t, vt)

    # ---- B3 compressione -> rottura del range di ieri
    t = S.prior_range_breakout(bars, daily, M=M)
    comp = (f["rv"].rolling(5).mean() / f["rv"].rolling(60).mean())
    cp = C.rolling_pct_rank(comp, 250, 120).shift(1)       # nota a fine t-1
    cq = terc(cp)
    X.show("B3_prior_range_breakout_all", "rottura massimo/minimo RTH di ieri (apertura dentro), uscita 15:59, tutti", t)
    X.split("B3_prior_range_breakout_comp", "rottura range di ieri per terzile di compressione RV5/RV60 (low=compresso)", t, cq)
    rng = f["rth_range_pts"]
    nr7 = (rng <= rng.rolling(7).min()).shift(1).fillna(False)
    kk = nr7.reindex(pd.DatetimeIndex(t["session"])).to_numpy().astype(bool)
    X.show("B3b_prior_range_breakout_nr7", "rottura range di ieri solo dopo un NR7 (Crabel)", t[kk].reset_index(drop=True))

    # ---- B8 riferimento beta: long RTH sempre e per regime
    ones = pd.Series(1, index=M["sess"])
    t = S.rth_day(bars, daily, ones, M=M)
    X.show("B8_long_rth_all", "long 9:30->15:59 tutti i giorni (riferimento passivo)", t)
    X.split("B8_long_rth_vol", "long RTH per terzile di vol prevista (vol timing, Moreira-Muir)", t, vt)

    # ---- B4 dopo shock di vol: long il giorno dopo
    shock = (f["logrv"] - reg["fc"])          # residuo di ieri al t (noto a fine t)
    sp = C.rolling_pct_rank(shock, 250, 120).shift(1)
    sq = terc(sp)
    X.split("B4_long_after_volshock", "long RTH per terzile di shock di vol di ieri (logRV - previsione)", t, sq)
    s2 = (f["cc_ret_pct"] / np.sqrt(np.exp(reg["fc"]))).shift(1)   # rendimento di ieri in sigma previste
    side = pd.Series(np.where(s2 < -1.5, 1, 0), index=f.index)
    X.show("B4b_long_after_down15sig", "long RTH dopo giorno c-c < -1,5 sigma previste (premio per il rischio)", S.rth_day(bars, daily, side, M=M))

    # ---- B5 reversal c-c condizionato alla vol
    side = -np.sign(f["cc_ret_pct"]).shift(1)
    t = S.rth_day(bars, daily, side, M=M)
    X.show("B5_reversal_all", "fade del rendimento c-c di ieri (RTH open->close), tutti", t)
    X.split("B5_reversal_vol", "fade c-c di ieri per terzile di vol prevista", t, vt)

    # ---- B6 intraday momentum (Gao et al.) condizionato alla vol
    pc = f["rth_close"].shift(1)
    j30 = 30
    first30 = pd.Series(M["close_ff"][:, j30 - 1], index=M["sess"])
    off = f["rth_open"] - f["raw_open"]
    r_f30 = first30 + off.reindex(M["sess"]) - pc.reindex(M["sess"])      # adj: da close di ieri alle 9:59
    side = np.sign(r_f30)
    t = S.window_trade(bars, daily, side, 930, 960, M=M)
    X.show("B6_gao_all", "segno(close ieri->9:59) -> trade 15:30-15:59 (Gao 2018), tutti [sovrapposto a famiglia intraday_momentum]", t)
    X.split("B6_gao_vol", "Gao per terzile di vol prevista", t, vt)

    # ---- B7 fade di mezzogiorno (VR<1 12:30-15:30)
    r_mid = pd.Series(M["close_ff"][:, 239] - M["open"][:, 180], index=M["sess"])   # 12:30->13:29
    side = -np.sign(r_mid)
    t = S.window_trade(bars, daily, side, 810, 870, M=M)
    X.show("B7_midday_fade_all", "fade del movimento 12:30-13:29, tenuto 13:30-14:29 (da VR<1 di mezzogiorno)", t)
    X.split("B7_midday_fade_vol", "fade di mezzogiorno per terzile di vol prevista", t, vt)

    # ---- B9 gap fade condizionato
    gs = f["gap_pct"] / np.sqrt(np.exp(reg["fc"]))
    side = pd.Series(np.where(np.abs(gs) > 0.5, -np.sign(gs), 0), index=f.index)
    t = S.rth_day(bars, daily, side, M=M)
    X.show("B9_gapfade_05sig_all", "fade del gap > 0,5 sigma previste, open->close (gap gia' schermato dal progetto)", t)
    X.split("B9_gapfade_vol", "gap fade per terzile di vol prevista", t, vt)

    # ---- B10 direzione overnight con notte agitata
    ondir = np.sign(f["rth_open"] - f["glbx_open"])
    onr = np.log(f["on_range_pct"]) - 0.5 * reg["fc"]
    oq = terc(C.rolling_pct_rank(onr, 250, 120))
    t = S.rth_day(bars, daily, ondir, M=M)
    X.split("B10_on_follow_onsurprise", "segui la direzione overnight (glbx open->9:30) in RTH, per terzile di range notturno sorprendente", t, oq)

    # ---- B11 ultima ora nel verso del giorno se vol realizzata oggi >> prevista
    rday = pd.Series(M["close_ff"][:, 329] - M["open"][:, 0], index=M["sess"])
    side = np.sign(rday)
    t = S.window_trade(bars, daily, side, 900, 960, M=M)
    ir = pd.Series(np.nanmax(M["high"][:, :330], 1) - np.nanmin(M["low"][:, :330], 1), index=M["sess"]) / reg["atr20"].reindex(M["sess"])
    iq = terc(C.rolling_pct_rank(ir, 250, 120))
    X.show("B11_lasthour_follow_all", "segui la direzione 9:30-14:59 nell'ultima ora, tutti", t)
    X.split("B11_lasthour_follow_rangeratio", "ultima ora per terzile di range 9:30-14:59 / ATR20", t, iq)


if __name__ == "__main__":
    main()
