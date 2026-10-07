"""H5 sorpresa di volatilita' della prima ora e direzione del resto del giorno.

Dichiarato prima: S = range 09:30-10:29 / R_hat; percentile causale di S sulle 250 sessioni precedenti
(min 100). Ingresso all'open delle 10:30, uscite 12:00 e 15:59. Soglie q in {0.20, 0.33}.
Regole: lev  = short se pct(S) > 1-q, long se pct(S) < q  (effetto leva: sorpresa di vol -> ribasso)
        levS = solo la gamba short di lev
        contH= side = segno del rendimento 09:30->10:29 se pct(S) > 1-q   (fadeH = specchio esatto)
        contL= side = segno del rendimento 09:30->10:29 se pct(S) < q
Nessuno stop (lordo simmetrico: gli specchi sono i negativi). Diagnostica: beta per le regole sbilanciate.
"""
import numpy as np
import pandas as pd

from lab.r2_range import common as C


def pct_causal(x, win=250, minp=100):
    out = np.full(len(x), np.nan)
    for i in range(len(x)):
        p = x[max(0, i - win):i]; p = p[np.isfinite(p)]
        if len(p) >= minp and np.isfinite(x[i]):
            out[i] = (p < x[i]).mean()
    return out


def surprise(M, T=630):
    j = T - C.M0 - 1
    S = (M["runH"][:, j] - M["runL"][:, j]) / M["R_hat"]
    S = np.where(M["ok"], S, np.nan)
    d = np.sign(M["adj_close"][:, j] - M["adj_open"][:, 0]).astype(int)
    return S, pct_causal(S), d


if __name__ == "__main__":
    bars, daily, M, F = C.setup_discovery()
    S, P, d = surprise(M)
    rows = []
    for q in (0.20, 0.33):
        hi, lo = P > 1 - q, P < q
        rules = {"lev": np.where(hi, -1, np.where(lo, 1, 0)), "levS": np.where(hi, -1, 0),
                 "contH": np.where(hi, d, 0), "contL": np.where(lo, d, 0)}
        for name, side in rules.items():
            si = np.where(M["ok"] & (side != 0))[0]
            for T in (720, 960):
                t = C.sim(M, si, np.full(len(si), 630), side[si], m_out=np.full(len(si), T))
                full = name in ("lev", "levS")
                st = C.evaluate(t, bars if full else None, M if full else None, full=full)
                tid = f"h05_{name}_q{q}_T{T}"
                C.rec(tid, f"sorpresa di vol prima ora, regola {name}, q={q}, 10:30->{T//60}:{T%60:02d}", st)
                rows.append(dict(rule=name, q=q, T=T, n=st["n"], net=st["mean"], p_two=st["p_two"], gR=st["gross_R"],
                                 nmb=st.get("net_minus_beta")))
    pd.set_option("display.width", 200)
    print(pd.DataFrame(rows).to_string())
