"""r3_adaptive D — DIAGNOSTICA POST-HOC (dichiarata tale, scritta dopo s01): in s01 la correlazione mensile
dello spread di famiglia D = lordo(follow) - lordo(fade) fra passato e futuro era la sola statistica con
p < 0,05 (L = 6 e 12, non L = 3 principale). Qui la si traduce in una quantita' misurabile giorno per giorno:
ogni mese, lato di famiglia = segno del lordo medio delle regole follow nelle 21*L sessioni precedenti
(fade = specchio esatto sul lordo); misura = lordo medio giornaliero della famiglia scelta (punti lordi,
1 contratto diviso fra tutte le regole della famiglia). Test bilaterale sul lordo per giorno,
anni, senza i 20 migliori, placebo segno-per-giorno (500). Nessun costo: e' una regolarita'.
"""
import numpy as np
import pandas as pd

from lab import core
from lab.r3_adaptive import common as c
from lab.r3_adaptive import s02_meta as m


def daily_D(S, sign_day=None):
    gross, net, traded = c.gross_net(S["SIDE"], S["GR"], sign_day)
    fol = S["fol"]
    with np.errstate(invalid="ignore", divide="ignore"):
        gf = (gross * traded)[:, fol].sum(1) / traded[:, fol].sum(1)
    return np.nan_to_num(gf)          # fade = -follow esattamente sul lordo -> D = 2*gf; uso gf (famiglia trend)


def family_switch(S, x, L):
    pid = S["pids"]["month"]
    starts = np.r_[0, np.flatnonzero(np.diff(pid)) + 1]
    cs = np.r_[0, np.cumsum(x)]
    w = 21 * L
    side = np.full(len(starts), np.nan)
    ok = starts >= w
    side[ok] = np.sign(cs[starts[ok]] - cs[starts[ok] - w])
    return side[pid] * x


if __name__ == "__main__":
    S = m.setup()
    sess = S["sess"]
    mall = sess >= c.SEARCH[0]
    x = daily_D(S)
    rng = np.random.default_rng(777)
    signs = [rng.choice([-1.0, 1.0], size=len(sess)) for _ in range(500)]
    for L in (3, 6, 12):
        y = family_switch(S, x, L)[mall]
        d = sess[mall]
        st = core.day_block_bootstrap(y, d.values)
        yr = core.yearly(y, d)
        pm = np.array([np.nanmean(family_switch(S, daily_D(S, s), L)[mall]) for s in signs])
        p_pl = (np.abs(pm) >= abs(st["mean"])).mean()
        print(f"L={L}: mean {st['mean']:+.3f} [{st['lo']:+.3f};{st['hi']:+.3f}] p2 {st['p_two']:.3f}  placebo p2 {p_pl:.3f}"
              f"  anni+ {(yr['mean']>0).sum()}/{len(yr)}  senza top20 {core.drop_top(y):+.3f}")
        print("   ", yr["mean"].round(2).to_dict())
        core.record(c.FAM, f"D_famswitch_L{L}", f"POST-HOC: segui la famiglia (trend/MR) che ha vinto nelle 21*{L} sessioni precedenti, lordo",
                    "discovery", st, p_placebo=float(p_pl), years_pos=f"{(yr['mean']>0).sum()}/{len(yr)}",
                    drop20=core.drop_top(y), kind="posthoc_regularity")
