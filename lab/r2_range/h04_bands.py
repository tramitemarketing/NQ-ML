"""H4 bande di volatilita' prevista come livelli.

Dichiarato prima: bande = ancora +/- h * R_hat, ancora in {open RTH 09:30, close RTH di ieri},
h in {0.35, 0.50, 0.75}. Evento = prima barra con chiusura fra 09:45 e 15:00 il cui high supera la banda
alta di almeno 1 tick (o il low la banda bassa); barra che tocca entrambe: scartata. Una sola volta al giorno
(il primo tocco). Ingresso all'open della barra successiva.
Regole: fade (contro la banda) e rottura (nel verso della banda), stop in {0.10, 0.20} * R_hat,
target in {0.25 * R_hat, nessuno}, uscita in {60 minuti, 15:59}.
Placebo: stesse bande con R_hat rimescolato fra le sessioni dello stesso anno (seme 0), primario solo.
Primario dichiarato: ancora open, h=0.5, fade, stop 0.2, nessun target, 60 minuti.
"""
import itertools

import numpy as np
import pandas as pd

from lab.r2_range import common as C


def touches(M, R, anchor, h, m_lo=585, m_hi=900):
    A = M["adj_open"][:, 0] if anchor == "open" else M["prev_close"]
    ok = M["ok"] & np.isfinite(R) & np.isfinite(A)
    up = (A + h * R)[:, None]; dn = (A - h * R)[:, None]
    a, b = m_lo - C.M0 - 1, m_hi - C.M0
    Hs, Ls = M["adj_high"][:, a:b], M["adj_low"][:, a:b]
    tu = Hs >= up + C.TICK
    td = Ls <= dn - C.TICK
    # esclude se la banda e' gia' stata superata prima delle 09:45 (dall'inizio della RTH)
    pre_u = (M["runH"][:, a - 1:a] >= up + C.TICK)[:, 0]
    pre_d = (M["runL"][:, a - 1:a] <= dn - C.TICK)[:, 0]
    si_l, m_l, s_l = [], [], []
    for s in np.where(ok)[0]:
        iu = np.argmax(tu[s]) if (tu[s].any() and not pre_u[s]) else 10**6
        idn = np.argmax(td[s]) if (td[s].any() and not pre_d[s]) else 10**6
        if iu == idn:
            continue
        j = min(iu, idn)
        si_l.append(s); m_l.append(C.M0 + a + j + 1); s_l.append(+1 if iu < idn else -1)   # verso della banda
    return np.array(si_l), np.array(m_l), np.array(s_l)


def run(M, R, anchor, h, rule, stop, tgt, hz):
    si, m, d = touches(M, R, anchor, h)
    side = -d if rule == "fade" else d
    Rh = M["R_hat"][si]
    return C.sim(M, si, m, side, stop * Rh, (tgt * Rh if tgt else None), (m + 60 if hz == 60 else None))


if __name__ == "__main__":
    bars, daily, M, F = C.setup_discovery()
    rows = []
    for anchor, h, rule, stop, tgt, hz in itertools.product(["open", "pc"], [0.35, 0.5, 0.75], ["fade", "brk"],
                                                            [0.10, 0.20], [0.25, None], [60, "eod"]):
        t = run(M, M["R_hat"], anchor, h, rule, stop, tgt, hz)
        st = C.evaluate(t, full=False)
        tid = f"h04_{anchor}_h{h}_{rule}_s{stop}_t{tgt}_{hz}"
        C.rec(tid, f"banda {anchor} +/- {h}*R_hat, primo tocco 09:45-15:00, {rule}, stop {stop}R, target {tgt}R, uscita {hz}", st)
        rows.append(dict(anchor=anchor, h=h, rule=rule, stop=stop, tgt=tgt, hz=hz, n=st["n"], net=st["mean"],
                         p=st["p_pos"], gR=st["gross_R"]))
    df = pd.DataFrame(rows)
    pd.set_option("display.width", 200)
    print(df.to_string())
    print(df.groupby(["anchor", "rule", "h"])[["net", "gR"]].mean())
    t = run(M, M["R_hat"], "open", 0.5, "fade", 0.2, None, 60)
    st = C.evaluate(t, bars, M); print("PRIMARIO", C.fmt(st), st["yearly"])
    C.rec("h04_primary_full", "H4 primario (open +/- 0.5R, fade, stop 0.2R, 60m) diagnostica completa", st)
    rng = np.random.default_rng(0)
    Rs = M["R_hat"].copy(); yrs = M["sess"].year.to_numpy()
    for y in np.unique(yrs):
        ii = np.where((yrs == y) & np.isfinite(Rs))[0]
        Rs[ii] = Rs[rng.permutation(ii)]
    t = run(M, Rs, "open", 0.5, "fade", 0.2, None, 60)
    st = C.evaluate(t, full=False); print("SHUFFLE", C.fmt(st))
    C.rec("h04_placebo_shuffle", "H4 primario con R_hat rimescolato nell'anno", st)
