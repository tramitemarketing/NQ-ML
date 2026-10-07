"""r2_autosearch — DIAGNOSTICA POST-HOC (dichiarata tale: decisa dopo aver visto s01/s02, non cambia la
regola di decisione sui candidati del piano).

Domanda: S5 (numero di regole con t_ricerca > 3) e' piu' alto nel reale che nella mediana dei placebo
(p 0,09 segno / 0,03 blocchi). Le regole con t > 3 in ricerca reggono in selezione meglio che nei placebo?
Per ogni regola SINGOLA o COPPIA (enumerazione completa) con t_ricerca > 3: t e media netta sul 2016-2018.
D1 = quante, D2 = t_sel medio, D3 = quota con media netta > 0, D4 = quota con t_sel > 1,645.
Stessa cosa su 200 placebo per nullo. Poi: da dove viene l'eccesso (celle).
"""
from __future__ import annotations

import os

os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")

import json

import numpy as np
import pandas as pd

from lab import core
from lab.r2_autosearch import common as cm
from lab.r2_autosearch import s01_autosearch as s


def _mats(Ms, y):
    ok = np.isfinite(y).astype(float)
    y0 = np.nan_to_num(y)
    Mo = Ms * ok[:, None]
    return Mo.T @ Mo, Mo.T @ (Mo * y0[:, None]), Mo.T @ (Mo * (y0 ** 2)[:, None])


def diag(Y, detail=False):
    G = s._G
    M, s_idx, v_idx, allowed = G["M"], G["s_idx"], G["v_idx"], G["allowed"]
    tsel_all, rows = [], []
    for k, T in enumerate(cm.TIMES):
        Ms = M[s_idx, k, :].astype(float); Mv = M[v_idx, k, :].astype(float)
        for m, h in enumerate(cm.HORIZONS):
            y = Y[s_idx, k, m]
            if not np.isfinite(y).any():
                continue
            N, S, Q = _mats(Ms, y)
            Nv, Sv, Qv = _mats(Mv, Y[v_idx, k, m])
            for side in (1, -1):
                t, _ = s._tstat(S, Q, N, side)
                sel = allowed & (N >= s.N_MIN) & (t > 3)
                if not sel.any():
                    continue
                tv, muv = s._tstat(Sv, Qv, Nv, side)
                x = np.where(Nv[sel] >= 10, tv[sel], np.nan)
                tsel_all.append(np.column_stack([x, muv[sel]]))
                if detail:
                    rows.append(dict(T=T, h=str(h), side=side, n_gt3=int(sel.sum()),
                                     mean_t_sel=float(np.nanmean(x)), frac_pos=float((muv[sel] > 0).mean())))
    a = np.vstack(tsel_all) if tsel_all else np.zeros((0, 2))
    out = dict(D1=len(a), D2=float(np.nanmean(a[:, 0])) if len(a) else np.nan,
               D3=float((a[:, 1] > 0).mean()) if len(a) else np.nan,
               D4=float((a[:, 0] > 1.645).mean()) if len(a) else np.nan)
    return out, rows


def _w(args):
    null, rep = args
    o, _ = diag(s.placebo_Y(null, rep))
    o.update(null=null, rep=rep)
    return o


def main():
    s._setup()
    real, rows = diag(s._G["P"]["G"], detail=True)
    print("REALE", real)
    print(pd.DataFrame(rows).sort_values("n_gt3", ascending=False).head(15).round(2).to_string())
    from multiprocessing import Pool
    with Pool(30, initializer=s._setup) as pool:
        out = pool.map(_w, [(n, r) for n in ("sign", "block") for r in range(200)], chunksize=2)
    df = pd.DataFrame(out)
    df.to_csv(cm.CACHE / "diag_placebo.csv", index=False)
    summ = {}
    for null, d in df.groupby("null"):
        summ[null] = {k: dict(real=real[k], p_ge=float((d[k] >= real[k]).mean()),
                              q05=float(d[k].quantile(0.05)), q50=float(d[k].median()),
                              q95=float(d[k].quantile(0.95))) for k in ("D1", "D2", "D3", "D4")}
    print(json.dumps(summ, indent=1))
    core.record(cm.FAM, "diag_posthoc_tgt3", "POST-HOC: regole singole/coppie con t_ricerca>3, tenuta in "
                "selezione 2016-18, reale vs 200+200 placebo", "discovery", {"n": real["D1"]},
                kind="posthoc_diag", real=real, summary=summ, cells=rows)


if __name__ == "__main__":
    main()
