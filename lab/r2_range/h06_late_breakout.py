"""H2 «range sotto il previsto a meta' giornata -> rottura tardiva».

Dichiarato prima: checkpoint T in {12:00, 13:00, 14:00}; u_T = range percorso fino a T / R_hat.
Gruppo «compresso»: u_T < u0, u0 in {0.4, 0.5, 0.6}; gruppo di controllo: u_T >= u0.
Evento: prima barra con chiusura fra T e 15:30 che fa un nuovo massimo o minimo della giornata di
almeno 1 tick (barra che fa entrambi: scartata). Ingresso all'open della barra successiva.
Regole: rottura (nel verso) e fade; stop in {0.15, 0.30} * R_hat; uscita 15:59.
Regolarita' collegata: il range del resto del giorno (T->16:00) / R_hat e' piu' grande del previsto?
(misurato come rapporto (range finale - range a T)/R_hat nei due gruppi; solo descrittivo).
"""
import itertools

import numpy as np
import pandas as pd

from lab.r2_range import common as C


def events(M, T, m_hi=930):
    a, b = T - C.M0, m_hi - C.M0
    si_l, m_l, d_l = [], [], []
    for s in np.where(M["ok"])[0]:
        H0, L0 = M["runH"][s, a - 1], M["runL"][s, a - 1]
        up = M["adj_high"][s, a:b] >= H0 + C.TICK
        dn = M["adj_low"][s, a:b] <= L0 - C.TICK
        iu = np.argmax(up) if up.any() else 10**6
        idn = np.argmax(dn) if dn.any() else 10**6
        if iu == idn:
            continue
        j = min(iu, idn)
        si_l.append(s); m_l.append(T + j + 1); d_l.append(1 if iu < idn else -1)
    return np.array(si_l), np.array(m_l), np.array(d_l)


if __name__ == "__main__":
    bars, daily, M, F = C.setup_discovery()
    rows = []
    for T in (720, 780, 840):
        si, m, d = events(M, T)
        u = (M["runH"][si, T - C.M0 - 1] - M["runL"][si, T - C.M0 - 1]) / M["R_hat"][si]
        for u0, grp, rule, stop in itertools.product((0.4, 0.5, 0.6), ("low", "high"), ("brk", "fade"), (0.15, 0.30)):
            sel = (u < u0) if grp == "low" else (u >= u0)
            side = d[sel] if rule == "brk" else -d[sel]
            t = C.sim(M, si[sel], m[sel], side, stop * M["R_hat"][si[sel]])
            st = C.evaluate(t, full=False)
            tid = f"h06_T{T}_u{u0}_{grp}_{rule}_s{stop}"
            C.rec(tid, f"rottura tardiva dopo {T//60}:00, u_T {'<' if grp=='low' else '>='} {u0}, {rule}, stop {stop}R, uscita 15:59", st)
            rows.append(dict(T=T, u0=u0, grp=grp, rule=rule, stop=stop, n=st["n"], net=st["mean"], p=st["p_pos"], gR=st["gross_R"]))
        # descrittivo: range residuo
        j = T - C.M0 - 1
        ok = M["ok"]
        uT = (M["runH"][ok, j] - M["runL"][ok, j]) / M["R_hat"][ok]
        ext = (M["runH"][ok, -1] - M["runL"][ok, -1]) / M["R_hat"][ok] - uT
        for u0 in (0.4, 0.5, 0.6):
            print(T, u0, "estensione residua media: compressi %.3f  altri %.3f" % (ext[uT < u0].mean(), ext[uT >= u0].mean()))
    pd.set_option("display.width", 200)
    df = pd.DataFrame(rows)
    print(df.to_string())
    print(df.groupby(["grp", "rule"])[["net", "gR"]].mean())
