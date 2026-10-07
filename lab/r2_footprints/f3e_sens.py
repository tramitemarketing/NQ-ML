"""F3e - sensibilita' del candidato close_clock_continuation: orizzonte {10, 15, 20} minuti, sottoperiodi
2010-13 / 2014-18, e placebo con le stesse 4 posizioni relative spostate di un'ora (14:45, 14:50, 14:55, 14:59)."""
import numpy as np
import pandas as pd

from lab.r2_footprints import common as C
from lab.r2_footprints.f3b_magnitude import sigma1m

if __name__ == "__main__":
    D, daily = C.get()
    ok = D["valid"] & D["in_phase"]
    sess = D["sess"][ok]
    sig = sigma1m(D, D["valid"])[ok]
    Cf = D["Cf"][ok]

    def q(mins, H):
        xs = [np.sign(Cf[:, C.sm_of(m)] - Cf[:, C.sm_of(m) - 1]) * (Cf[:, C.sm_of(m) + H] - Cf[:, C.sm_of(m)]) for m in mins]
        return np.nanmean(np.column_stack(xs), 1) / sig

    close = ["15:45", "15:50", "15:55", "15:59"]
    for H in [10, 15, 20]:
        v = q(close, H)
        st = C.rec(f"F3e_close_H{H}", f"F3e barre-orologio di chiusura, orizzonte {H} minuti, sigma", v, sess, unit="sigma1m")
        print("H", H, C.fmt(st))
    v = q(close, 15)
    for nm, mk in (("2010-13", sess.year <= 2013), ("2014-18", sess.year >= 2014), ("2016-18", sess.year >= 2016)):
        st = C.rec(f"F3e_close_{nm}", f"F3e candidato (H=15) nel sottoperiodo {nm}", v[mk], sess[mk], unit="sigma1m")
        print(nm, C.fmt(st))
    for shift_nm, mins in (("1h_before", ["14:45", "14:50", "14:55", "14:59"]), ("2h_before", ["13:45", "13:50", "13:55", "13:59"])):
        v = q(mins, 15)
        st = C.rec(f"F3e_placebo_{shift_nm}", f"F3e placebo: stesse posizioni {mins}, H=15", v, sess, unit="sigma1m")
        print(shift_nm, C.fmt(st))
