"""H3 apertura lontana dal centro del range previsto.

Dichiarato prima: z_pc = (open RTH - close RTH di ieri)/R_hat (gap in unita' di range previsto);
z_on = (open RTH - centro del range notturno)/R_hat. Segnale noto alla close della barra 09:30, ingresso
all'open delle 09:31. Regola fade: side = -sign(z) se |z| > g, g in {0.15, 0.30, 0.50}.
Uscite: 10:30, 12:00, 15:59. Nessuno stop (specchio = esatto negativo del lordo: il test e' bilaterale).
Regolarita' misurata anche come regressione: pendenza di rendimento 09:31->uscita (in R_hat) su z.
Nota: i gap sono gia' stati esplorati nel giro 1 (in punti/ATR); qui l'unita' e' R_hat: variante dichiarata.
"""
import numpy as np
import pandas as pd

from lab.r2_range import common as C

if __name__ == "__main__":
    bars, daily, M, F = C.setup_discovery()
    O = M["adj_open"][:, 0]
    zs = {"pc": (O - M["prev_close"]) / M["R_hat"], "on": (O - M["on_mid"]) / M["R_hat"]}
    rows = []
    for zn, z in zs.items():
        for g in (0.15, 0.30, 0.50):
            sel = M["ok"] & np.isfinite(z) & (np.abs(z) > g)
            si = np.where(sel)[0]
            side = -np.sign(z[si]).astype(int)
            for T in (630, 720, 960):
                t = C.sim(M, si, np.full(len(si), 571), side, m_out=np.full(len(si), T))
                st = C.evaluate(t, full=False)
                tid = f"h03_fade_{zn}_g{g}_T{T}"
                C.rec(tid, f"fade della posizione d'apertura z_{zn} (|z|>{g}) da 09:31 a {T//60}:{T%60:02d}", st)
                rows.append(dict(z=zn, g=g, T=T, n=st["n"], net=st["mean"], p_two=st["p_two"], gR=st["gross_R"]))
        # regressione continua (tutte le sessioni)
        sel = M["ok"] & np.isfinite(z)
        si = np.where(sel)[0]
        for T in (630, 720, 960):
            r = (M["adj_close"][si, T - C.M0 - 1] - M["adj_open"][si, 1]) / M["R_hat"][si]
            q = -np.sign(z[si]) * r   # fade lordo in R per ogni sessione
            st = C.core.day_block_bootstrap(q, M["sess"][si].values, n_boot=4000)
            slope = np.polyfit(z[si], r, 1)[0]
            st["slope"] = float(slope)
            C.rec(f"h03_reg_{zn}_T{T}", f"regolarita': -sign(z_{zn}) * rendimento 09:31->{T} in R_hat, tutte le sessioni", st)
            rows.append(dict(z=zn, g="all_R", T=T, n=st["n"], net=st["mean"], p_two=st["p_two"], gR=slope))
    pd.set_option("display.width", 200)
    print(pd.DataFrame(rows).to_string())
