"""F3b - le continuazioni trovate in F3 scalano con l'ampiezza del segnale? (griglia dichiarata: quantili
causali {0.5, 0.7, 0.9} di |z| sulle 250 sessioni precedenti, z = segnale / sigma1m delle 20 sessioni precedenti).
Esecuzione realistica: segnale alla chiusura della barra, ingresso all'OPEN della barra successiva, netto 0,75."""
import numpy as np
import pandas as pd

from lab.r2_footprints import common as C

pd.set_option("display.width", 250)


def sigma1m(D, ok):
    """std dei rendimenti 1m RTH per sessione, poi media delle 20 sessioni PRECEDENTI (valide)."""
    a, b = C.sm_of("09:30"), C.sm_of("16:00")
    r = np.diff(D["Cf"][:, a:b], axis=1)
    s = pd.Series(np.nanstd(r, axis=1))
    s[~ok] = np.nan
    return s.shift(1).rolling(20, min_periods=10).mean().to_numpy()


def causal_q(x, q, win=250, minp=100):
    return pd.Series(x).shift(1).rolling(win, min_periods=minp).quantile(q).to_numpy()


if __name__ == "__main__":
    D, daily = C.get()
    ok = D["valid"] & D["in_phase"]
    sig1 = sigma1m(D, D["valid"])
    drift = C.drift_per_sm(D, ok)
    P = lambda t: D["Cf"][:, C.sm_of(t)]
    rows_all = np.arange(len(D["sess"]))
    specs = {
        # nome: (segnale, barra del segnale, barra di uscita, durata del segnale in minuti)
        "settle1559_to1614": (P("15:59") - P("15:58"), "15:59", "16:14", 1),
        "settle1559_to1659": (P("15:59") - P("15:58"), "15:59", "16:59", 1),
        "imb1550_to1559": (P("15:54") - P("15:49"), "15:54", "15:59", 5),
        "last5_to1614": (P("15:59") - P("15:54"), "15:59", "16:14", 5),
        "last15_to1659": (P("15:59") - P("15:44"), "15:59", "16:59", 15),
    }
    out = []
    for name, (s, ts, te, dur) in specs.items():
        z = s / (sig1 * np.sqrt(dur))
        az = np.abs(z)
        for q in [0.0, 0.5, 0.7, 0.9]:
            thr = causal_q(np.where(ok, az, np.nan), q) if q > 0 else np.zeros(len(az))
            m = ok & np.isfinite(z) & (az > thr) & (z != 0)
            i = np.full(m.sum(), C.sm_of(ts)); j = np.full(m.sum(), C.sm_of(te))
            t = C.trade(D, rows_all[m], i, j, np.sign(z[m]).astype(int), drift)
            st = C.full_report(f"F3b_{name}_q{q}", f"F3b {name}: segue il segno del segnale se |z|>quantile causale {q}; "
                               f"ingresso open barra dopo {ts}, uscita close {te}, NETTO 0,75", t, net=True)
            sg = (t["gross_pts"] / (sig1[t["row"]] * np.sqrt(C.sm_of(te) - C.sm_of(ts)))).mean()
            out.append(dict(id=name, q=q, n=st["n"], gross=st["mean"] + C.COST, net=st["mean"], lo=st["lo"],
                            p=st["p_pos"], yrs=st["years_pos"], d20=st["drop20"], mb=st.get("minus_beta"),
                            gross_sigma=sg))
    print(pd.DataFrame(out).round(3).to_string())
