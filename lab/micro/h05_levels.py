"""H5/H6/H7: livelli di riferimento noti prima dell'apertura (prezzi adj, coerenti con le barre adj):
  PD = massimo/minimo RTH della sessione precedente; ON = massimo/minimo della notte (18:00-09:29);
  PW = massimo/minimo RTH della settimana solare precedente.
Durante la RTH (09:35-15:00), primo attraversamento del livello (close precedente dentro, high/low oltre):
  'break' = la barra chiude oltre di >= 1 tick; 'sweep' = supera ma chiude dentro.
  'reentry' = dopo un break, prima barra (entro 30) che richiude dentro.
fade = verso l'interno del range (short al massimo, long al minimo)."""
import numpy as np
import pandas as pd
from numba import njit
from lab.micro.common import Data, evaluate_pair


@njit(cache=True)
def level_events(h, l, c, m, scode, U, Dn, lo_m, hi_m):
    n = len(c)
    out_i = np.empty(4 * (scode.max() + 1), np.int64)
    out_side = np.empty_like(out_i)   # lato fade
    out_kind = np.empty_like(out_i)   # 0 sweep, 1 break, 2 reentry
    k = 0
    i = 1
    while i < n:
        s = scode[i]
        j0 = i
        while i < n and scode[i] == s:
            i += 1
        for lv, sgn in ((U[s], 1), (Dn[s], -1)):
            if lv != lv:
                continue
            done = False
            for j in range(j0 + 1, i):
                if m[j] < lo_m or m[j] >= hi_m:
                    continue
                inside_prev = (c[j - 1] <= lv) if sgn > 0 else (c[j - 1] >= lv)
                if not inside_prev:
                    # gia' oltre: il livello non e' 'nuovo' in questo tratto; si salta la sessione
                    if m[j] == lo_m:
                        break
                    continue
                cross = (h[j] > lv) if sgn > 0 else (l[j] < lv)
                if not cross:
                    continue
                brk = (c[j] >= lv + 0.25) if sgn > 0 else (c[j] <= lv - 0.25)
                out_i[k] = j; out_side[k] = -sgn; out_kind[k] = 1 if brk else 0; k += 1
                if brk:
                    for q in range(j + 1, min(j + 31, i)):
                        if m[q] >= hi_m:
                            break
                        back = (c[q] <= lv) if sgn > 0 else (c[q] >= lv)
                        if back:
                            out_i[k] = q; out_side[k] = -sgn; out_kind[k] = 2; k += 1
                            break
                done = True
                break
    return out_i[:k], out_side[:k], out_kind[:k]


def levels(D: Data):
    d = D.daily.copy()
    d = d[d["valid"] | True]
    sess = pd.DatetimeIndex(pd.unique(D.sess))
    d = d.reindex(sess)
    pdh = d["rth_high"].where(d["valid"]).ffill().shift(1)
    pdl = d["rth_low"].where(d["valid"]).ffill().shift(1)
    # notte: barre della sessione prima delle 09:30 (ny_min<570 o >=1080)
    b = pd.DataFrame({"s": D.scode, "h": D.h, "l": D.l, "m": D.m})
    on = b[(b.m < 570) | (b.m >= 1080)].groupby("s").agg(h=("h", "max"), l=("l", "min"))
    onh = on["h"].reindex(range(len(sess))).to_numpy()
    onl = on["l"].reindex(range(len(sess))).to_numpy()
    wk = d[["rth_high", "rth_low"]].copy()
    wk["w"] = sess.to_period("W-FRI")
    wagg = wk.groupby("w").agg(h=("rth_high", "max"), l=("rth_low", "min"))
    prevw = wagg.shift(1)
    pwh = prevw["h"].reindex(wk["w"]).to_numpy()
    pwl = prevw["l"].reindex(wk["w"]).to_numpy()
    return {"PD": (pdh.to_numpy(), pdl.to_numpy()), "ON": (onh, onl), "PW": (pwh, pwl)}


if __name__ == "__main__":
    D = Data()
    L = levels(D)
    names = {0: "sweep", 1: "break", 2: "reentry"}
    for lv, (U, Dn) in L.items():
        ei, es, ek = level_events(D.h, D.l, D.c, D.m, D.scode, U.astype(float), Dn.astype(float), 575, 900)
        ok = D.inph[ei]
        for kind in (0, 1, 2):
            sel = ok & (ek == kind)
            for H in (15, 60):
                evaluate_pair(D, ei[sel], es[sel], H, f"H5_{lv}_{names[kind]}_H{H}",
                              f"livello {lv} (max/min), primo attraversamento RTH 09:35-15:00, {names[kind]}, fade verso l'interno, uscita {H}m",
                              end="rth")
