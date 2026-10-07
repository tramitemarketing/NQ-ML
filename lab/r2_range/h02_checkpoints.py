"""H1b/H2 a orari fissi: bilancio del range usato u = (range percorso)/R_hat e posizione nel range.

Dichiarato prima: checkpoint T in {10:30, 11:30, 12:30, 13:30, 14:30} (segnale alla close della barra T-1,
ingresso all'open della barra T). pos = (close - min)/(max - min) del range percorso. Uscite: 60 minuti e 15:59.
Celle di u: [0, 0.5), [0.5, 0.8), [0.8, 1.1), [1.1, inf).
 A) «estremo»: pos >= 0.85 -> short, pos <= 0.15 -> long (fade dell'estremo); specchio = continuazione.
 B) «direzione del giorno»: side = sign(close_T - open 09:30) (continuazione), per cella di u.
Metrica: netto in punti (decisione) e lordo in R_hat (diagnostica). Tutte le celle registrate.
"""
import numpy as np
import pandas as pd

from lab.r2_range import common as C

BINS = [(0, 0.5), (0.5, 0.8), (0.8, 1.1), (1.1, 9)]


def state(M, T):
    j = T - C.M0 - 1
    rr = M["runH"][:, j] - M["runL"][:, j]
    u = rr / M["R_hat"]
    pos = (M["adj_close"][:, j] - M["runL"][:, j]) / np.where(rr > 0, rr, np.nan)
    d = np.sign(M["adj_close"][:, j] - M["adj_open"][:, 0])
    return u, pos, d


if __name__ == "__main__":
    bars, daily, M, F = C.setup_discovery()
    rows = []
    for T in (630, 690, 750, 810, 870):
        u, pos, d = state(M, T)
        for lo, hi in BINS:
            cell = M["ok"] & (u >= lo) & (u < hi)
            for rule in ("A_fade", "B_cont"):
                if rule == "A_fade":
                    side = np.where(pos >= 0.85, -1, np.where(pos <= 0.15, 1, 0))
                else:
                    side = d.astype(int)
                sel = cell & (side != 0)
                si = np.where(sel)[0]
                for hz in (60, "eod"):
                    t = C.sim(M, si, np.full(len(si), T), side[si], m_out=(T + 60 if hz == 60 else None))
                    st = C.evaluate(t, full=False)
                    tid = f"h02_{rule}_T{T}_u{lo}-{hi}_{hz}"
                    C.rec(tid, f"checkpoint {T//60}:{T%60:02d}, u in [{lo},{hi}), regola {rule}, uscita {hz}", st)
                    rows.append(dict(T=T, u=f"{lo}-{hi}", rule=rule, hz=hz, n=st.get("n"), net=st.get("mean"),
                                     p=st.get("p_pos"), gR=st.get("gross_R")))
    df = pd.DataFrame(rows)
    pd.set_option("display.width", 200)
    print(df.to_string())
    print(df.groupby(["rule", "hz", "u"])[["net", "gR"]].mean())
