"""Controlli finali sui due candidati possibili (tutti registrati).

A) rottura banda pc +/- 0.9 R_hat (centro del plateau h in {0.75, 0.9, 1.0} di h07), stop 0.2 R, 09:45-15:00, uscita 15:59.
   - anni in unita' di R (lordo/R), costo 1,25 punti, ingresso ritardato di 1 minuto, trigger su CHIUSURA oltre la
     banda invece del tocco, solo mattina (<12:00) / solo pomeriggio, senza il 2018.
B) regolarita' gap in unita' di R: q = -sign(z_pc) * (P 11:59 close - P 09:31 open)/R_hat per |z_pc| > 0.5.
   - bilaterale sul lordo in R, anni, drop20 in R, senza il 2018, soglie 0.4/0.6.
"""
import numpy as np
import pandas as pd

from lab import core
from lab.r2_range import common as C
from lab.r2_range.h04_bands import touches


def touches_close(M, R, h, m_lo=585, m_hi=900):
    A = M["prev_close"]
    ok = M["ok"] & np.isfinite(R) & np.isfinite(A)
    up = (A + h * R)[:, None]; dn = (A - h * R)[:, None]
    a, b = m_lo - C.M0 - 1, m_hi - C.M0
    Cs = M["adj_close"][:, a:b]
    pre_u = M["runH"][:, a - 1] >= up[:, 0] + C.TICK
    pre_d = M["runL"][:, a - 1] <= dn[:, 0] - C.TICK
    si_l, m_l, s_l = [], [], []
    for s in np.where(ok)[0]:
        cu = Cs[s] > up[s]; cd = Cs[s] < dn[s]
        iu = np.argmax(cu) if (cu.any() and not pre_u[s]) else 10**6
        idn = np.argmax(cd) if (cd.any() and not pre_d[s]) else 10**6
        if iu == idn:
            continue
        j = min(iu, idn)
        si_l.append(s); m_l.append(C.M0 + a + j + 1); s_l.append(1 if iu < idn else -1)
    return np.array(si_l), np.array(m_l), np.array(s_l)


def show(tag, st):
    print(tag, C.fmt(st), st.get("yearly", ""))


if __name__ == "__main__":
    import sys
    REST = "--rest" in sys.argv   # la prima esecuzione si e' interrotta dopo "pomeriggio": --rest riprende senza duplicare il registro
    bars, daily, M, F = C.setup_discovery()
    H, S = 0.9, 0.2
    si, m, d = touches(M, M["R_hat"], "pc", H)
    t = C.sim(M, si, m, d, S * M["R_hat"][si])
    if REST:
        _orig = C.rec
        C.rec = lambda tid, desc, st, **k: _orig(tid, desc, st, **k) if (tid.startswith("h09A_senza") or tid.startswith("h09B")) else st
    st = C.evaluate(t, bars, M); show("A base", st)
    C.rec("h09A_base", "A: rottura banda pc +/-0.9R, stop 0.2R, 09:45-15:00 -> 15:59, diagnostica completa", st)
    gR = t["gross_pts"] / t["R"]
    stR = core.day_block_bootstrap(gR.to_numpy(), t["session"].to_numpy(), n_boot=4000)
    stR["yearly"] = core.yearly(gR.to_numpy(), t["session"])["mean"].round(3).to_dict()
    stR["drop20"] = core.drop_top(gR.to_numpy(), 20)
    show("A lordo in R", stR); C.rec("h09A_grossR", "A: lordo in unita' di R_hat", stR)
    net125 = t["gross_pts"] - 1.25
    s2 = core.day_block_bootstrap(net125.to_numpy(), t["session"].to_numpy(), n_boot=4000)
    show("A costo 1.25", s2); C.rec("h09A_cost125", "A: netto con costo 1,25 punti", s2)
    t2 = C.sim(M, si, m + 1, d, S * M["R_hat"][si])
    s2 = C.evaluate(t2, full=True); show("A ritardo 1m", s2); C.rec("h09A_delay1", "A: ingresso 1 minuto dopo", s2)
    si2, m2, d2 = touches_close(M, M["R_hat"], H)
    t2 = C.sim(M, si2, m2, d2, S * M["R_hat"][si2])
    s2 = C.evaluate(t2, full=True); show("A trigger close", s2); C.rec("h09A_closetrig", "A: trigger su chiusura oltre la banda", s2)
    for lab, msk in (("mattina", t["m_in"] < 720), ("pomeriggio", t["m_in"] >= 720),
                     ("senza2018", pd.DatetimeIndex(t["session"]).year != 2018)):
        s2 = C.evaluate(t[np.asarray(msk)], full=True); show("A " + lab, s2)
        C.rec(f"h09A_{lab}", f"A: sottoinsieme {lab}", s2)

    O = M["adj_open"][:, 0]
    z = (O - M["prev_close"]) / M["R_hat"]
    for g in (0.4, 0.5, 0.6):
        sel = np.where(M["ok"] & np.isfinite(z) & (np.abs(z) > g))[0]
        q = -np.sign(z[sel]) * (M["adj_close"][sel, 719 - C.M0] - M["adj_open"][sel, 1]) / M["R_hat"][sel]
        days = M["sess"][sel].values
        st = core.day_block_bootstrap(q, days, n_boot=4000)
        st["yearly"] = core.yearly(q, days)["mean"].round(3).to_dict()
        st["drop20"] = core.drop_top(q, 20)
        y = pd.DatetimeIndex(days).year != 2018
        st["no2018"] = core.day_block_bootstrap(q[y], days[y], n_boot=4000)["mean"]
        show(f"B g={g}", st); print("   senza 2018", st["no2018"])
        C.rec(f"h09B_g{g}", f"B: regolarita' fade gap |z_pc|>{g}, lordo in R 09:31->12:00", st)
