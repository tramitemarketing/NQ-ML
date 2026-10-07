"""H1 «bilancio del range esaurito»: fade dell'estremo quando il range percorso raggiunge k * R_hat.

Evento (dichiarato prima di guardare): prima barra 1m con chiusura fra 10:00 e 15:00 (minuti 600..899)
in cui il range RTH percorso (max high - min low da 09:30) diventa >= k * R_hat, e la barra stessa ha
fatto il nuovo estremo (nuovo massimo -> fade short; nuovo minimo -> fade long; barra che fa entrambi:
scartata). Ingresso all'open della barra successiva.
Griglia dichiarata: k in {0.5 (controllo: bilancio NON esaurito), 0.75, 1.0, 1.25};
stop in {0.15, 0.30, nessuno} * R_hat oltre l'ingresso; target in {0.25 * R_hat, nessuno};
uscita a tempo in {60 minuti, 15:59}. Primario dichiarato: k=1.0, stop 0.30, nessun target, 15:59.
Specchio = continuazione (lato opposto, stessa geometria). Placebo: stessa regola con R_naive (media20)
e con R_hat rimescolato fra sessioni dello stesso anno (seme 0).
"""
import itertools

import numpy as np
import pandas as pd

from lab.r2_range import common as C


def events(M, R, k, m_lo=600, m_hi=900):
    ok = M["ok"] & np.isfinite(R)
    rr = M["runH"] - M["runL"]
    thr = (k * R)[:, None]
    si_l, m_l, side_l = [], [], []
    a, b = m_lo - C.M0 - 1, m_hi - C.M0          # barre con chiusura in [m_lo, m_hi) -> indice di barra m-1
    for s in np.where(ok)[0]:
        # la barra j chiude al minuto M0+j+1; cerco il primo j in [a, b) con rr>=thr, e rr[j-1]<thr
        x = rr[s] >= thr[s]
        if x[a]:          # gia' esaurito prima delle 10:00: nessun evento "nuovo" nella finestra
            continue
        w = np.where(x[a:b])[0]
        if len(w) == 0:
            continue
        j = a + w[0]
        newH = M["adj_high"][s, j] > M["runH"][s, j - 1]
        newL = M["adj_low"][s, j] < M["runL"][s, j - 1]
        if newH == newL:
            continue
        si_l.append(s); m_l.append(C.M0 + j + 1); side_l.append(-1 if newH else +1)
    return np.array(si_l), np.array(m_l), np.array(side_l)


def run(M, R, k, stop, tgt, horizon, flip=1):
    si, m, sd = events(M, R, k)
    Rh = M["R_hat"][si]
    stop_d = stop * Rh if stop else None
    tgt_d = tgt * Rh if tgt else None
    m_out = m + 60 if horizon == 60 else None
    return C.sim(M, si, m, flip * sd, stop_d, tgt_d, m_out)


if __name__ == "__main__":
    bars, daily, M, F = C.setup_discovery()
    grid = list(itertools.product([0.5, 0.75, 1.0, 1.25], [0.15, 0.30, None], [0.25, None], [60, "eod"]))
    rows = []
    for k, stop, tgt, hz in grid:
        for flip, lab in ((1, "fade"), (-1, "cont")):
            t = run(M, M["R_hat"], k, stop, tgt, hz, flip)
            st = C.evaluate(t, full=False)
            tid = f"h01_{lab}_k{k}_s{stop}_t{tgt}_{hz}"
            C.rec(tid, f"H1 {lab} dell'estremo al primo raggiungimento di range>=k*R_hat (10-15), stop {stop}R, target {tgt}R, uscita {hz}", st)
            rows.append(dict(id=tid, k=k, lab=lab, stop=stop, tgt=tgt, hz=hz, n=st["n"], net=st["mean"],
                             p=st["p_pos"], gross_R=st["gross_R"]))
    df = pd.DataFrame(rows)
    pd.set_option("display.width", 200)
    print(df.to_string())
    # primario con diagnostica completa
    t = run(M, M["R_hat"], 1.0, 0.30, None, "eod")
    st = C.evaluate(t, bars, M)
    print("PRIMARIO", C.fmt(st), st["yearly"])
    C.rec("h01_primary_full", "H1 primario (k=1, stop 0.3R, EOD) diagnostica completa", st)
    # placebo: R_naive e R_hat rimescolato nell'anno
    t = run(M, M["R_naive"], 1.0, 0.30, None, "eod")
    st = C.evaluate(t, full=False); print("NAIVE", C.fmt(st))
    C.rec("h01_placebo_naive", "H1 primario con R_naive (media20) al posto di R_hat", st)
    rng = np.random.default_rng(0)
    Rs = M["R_hat"].copy()
    yrs = M["sess"].year.to_numpy()
    for y in np.unique(yrs):
        ii = np.where((yrs == y) & np.isfinite(Rs))[0]
        Rs[ii] = Rs[rng.permutation(ii)]
    t = run(M, Rs, 1.0, 0.30, None, "eod")
    st = C.evaluate(t, full=False); print("SHUFFLE", C.fmt(st))
    C.rec("h01_placebo_shuffle", "H1 primario con R_hat rimescolato fra sessioni dello stesso anno", st)
