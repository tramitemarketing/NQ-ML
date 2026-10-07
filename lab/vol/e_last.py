"""Ultime due ipotesi B: IB stretta -> espansione (rottura IB per range IB/ATR); fade di mezzogiorno solo
sui movimenti grandi rispetto alla vol prevista. Registrate."""
from __future__ import annotations

import numpy as np
import pandas as pd

from lab.vol import common as C
from lab.vol import strategies as S
from lab.vol.b_tests import Ctx, terc


def main():
    X = Ctx()
    f, reg, M, bars, daily = X.f, X.reg, X.M, X.bars, X.daily
    t = S.ib_breakout(bars, daily, 60, M=M)
    ibr = pd.Series(np.nanmax(M["high"][:, :60], 1) - np.nanmin(M["low"][:, :60], 1), index=M["sess"])
    rr = terc(C.rolling_pct_rank(ibr / reg["atr20"].reindex(M["sess"]), 250, 120))
    X.split("B15_ib60_breakout_ibratio", "rottura IB 60m per terzile di range IB/ATR20 (IB stretta = low -> espansione attesa)", t, rr)
    # B17: fade di mezzogiorno se |mossa 12:30-13:29| > 1 sigma oraria prevista
    sig_day_pts = np.sqrt(np.exp(reg["fc"])) / 100 * f["raw_open"]          # sigma giornaliera prevista in punti
    sig_h = (sig_day_pts / np.sqrt(6.5)).reindex(M["sess"])
    r_mid = pd.Series(M["close_ff"][:, 239] - M["open"][:, 180], index=M["sess"])
    side = pd.Series(np.where(np.abs(r_mid) > sig_h, -np.sign(r_mid), 0), index=M["sess"])
    X.show("B17_midday_fade_big", "fade 13:30-14:29 del movimento 12:30-13:29 se > 1 sigma oraria prevista", S.window_trade(bars, daily, side, 810, 870, M=M))
    side2 = pd.Series(np.where(np.abs(r_mid) > sig_h, -np.sign(r_mid), 0), index=M["sess"])
    X.show("B17b_midday_fade_big_to_close", "come B17 ma tenuto fino alle 15:59", S.window_trade(bars, daily, side2, 810, 960, M=M))


if __name__ == "__main__":
    main()
