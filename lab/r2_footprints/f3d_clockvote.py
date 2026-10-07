"""F3d - (post hoc, dopo F3c) voto dei minuti-orologio di chiusura: v = somma dei segni dei rendimenti delle barre
15:45, 15:50, 15:55, 15:59. Se |v| >= soglia, alla chiusura della 15:59 si entra (open 16:00) nel verso di v.
Griglia dichiarata PRIMA di guardare: soglia {3, 4}, uscita {16:14, 16:59}. Netto 0,75.
Variante 2: entrata alla 15:46 nel verso della barra 15:45 (primo minuto-orologio), uscita 15:59 / 16:14."""
import numpy as np
import pandas as pd

from lab.r2_footprints import common as C

pd.set_option("display.width", 250)

if __name__ == "__main__":
    D, daily = C.get()
    ok = D["valid"] & D["in_phase"]
    drift = C.drift_per_sm(D, ok)
    Cf = D["Cf"]
    r = lambda t: np.sign(Cf[:, C.sm_of(t)] - Cf[:, C.sm_of(t) - 1])
    v = r("15:45") + r("15:50") + r("15:55") + r("15:59")
    rows = np.arange(len(D["sess"]))
    res = []
    for thr in [3, 4]:
        for ex in ["16:14", "16:59"]:
            m = ok & (np.abs(v) >= thr)
            t = C.trade(D, rows[m], np.full(m.sum(), C.sm_of("15:59")), np.full(m.sum(), C.sm_of(ex)),
                        np.sign(v[m]).astype(int), drift)
            st = C.full_report(f"F3d_vote{thr}_{ex}", f"F3d voto minuti-orologio |v|>={thr}, open 16:00 -> close {ex}, netto", t)
            res.append(dict(id=f"vote{thr}_{ex}", n=st["n"], gross=st["mean"] + C.COST, net=st["mean"], p=st["p_pos"],
                            yrs=st["years_pos"], d20=st["drop20"], mb=st["minus_beta"]))
    s = r("15:45")
    for ex in ["15:59", "16:14"]:
        m = ok & (s != 0)
        t = C.trade(D, rows[m], np.full(m.sum(), C.sm_of("15:45")), np.full(m.sum(), C.sm_of(ex)), s[m].astype(int), drift)
        st = C.full_report(f"F3d_1545_{ex}", f"F3d segno barra 15:45, open 15:46 -> close {ex}, netto", t)
        res.append(dict(id=f"1545_{ex}", n=st["n"], gross=st["mean"] + C.COST, net=st["mean"], p=st["p_pos"],
                        yrs=st["years_pos"], d20=st["drop20"], mb=st["minus_beta"]))
    print(pd.DataFrame(res).round(3).to_string())
