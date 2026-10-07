"""r2_autosearch — ricerca massiccia di regole + la stessa pipeline su placebo (piano: s00_piano.py).

Uscite: cache/real_top100.csv, cache/real_lots.csv, cache/placebo_<nullo>.csv, righe nel registro.
Eseguire: .venv/Scripts/python.exe -m lab.r2_autosearch.s01_autosearch
"""
from __future__ import annotations

import os
import sys
import time

os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")

import numpy as np
import pandas as pd

from lab import core
from lab.r2_autosearch import common as cm

N_MIN = 100          # trade minimi in ricerca
BEAM = 10            # coppie estese a triple per cella
PER_CELL = 2         # regole per cella nel portafoglio
TOPK = 100
T_SURV, T_STRONG = 1.645, 3.29
SEARCH_END = pd.Timestamp("2015-12-31")
SEL_START = pd.Timestamp("2016-01-01")

_G = {}


def _setup():
    P = cm.panel()
    sess = P["sessions"]
    M = cm.cond_masks(P["R"], P["dow"])                       # (ns, nT, nC)
    s_idx = np.where(sess <= SEARCH_END)[0]
    v_idx = np.where(sess >= SEL_START)[0]
    feat = cm.cond_feat()
    nC = M.shape[2]
    iu = np.triu_indices(nC)
    allowed = np.zeros((nC, nC), bool)
    allowed[iu] = True
    allowed &= (feat[:, None] != feat[None, :]) | np.eye(nC, dtype=bool)
    _G.update(P=P, M=M, s_idx=s_idx, v_idx=v_idx, feat=feat, allowed=allowed, sess=sess)


def _tstat(S, Q, N, side):
    with np.errstate(invalid="ignore", divide="ignore"):
        mu = S / N
        var = (Q / N - mu ** 2) * N / (N - 1)
        return (side * mu - cm.COST) / np.sqrt(var / N), side * mu - cm.COST


def run_pipeline(Y: np.ndarray, want_lots=False):
    """Y: (ns, nT, nH) rendimenti lordi long. Ritorna (stats, top100 DataFrame, lots)."""
    M, s_idx, v_idx, feat, allowed = _G["M"], _G["s_idx"], _G["v_idx"], _G["feat"], _G["allowed"]
    nC = M.shape[2]
    cells, lots = [], []
    n_rules = 0
    tmax = -np.inf
    n_gt3 = n_gt2 = 0
    for k, T in enumerate(cm.TIMES):
        Ms = M[s_idx, k, :].astype(np.float64)
        for m, h in enumerate(cm.HORIZONS):
            y = Y[s_idx, k, m]
            if not np.isfinite(y).any():
                continue
            ok = np.isfinite(y).astype(float)
            y0 = np.nan_to_num(y)
            Mo = Ms * ok[:, None]
            N = Mo.T @ Mo
            S = Mo.T @ (Mo * y0[:, None])
            Q = Mo.T @ (Mo * (y0 ** 2)[:, None])
            valid = allowed & (N >= N_MIN)
            for side in (1, -1):
                t, mu = _tstat(S, Q, N, side)
                t = np.where(valid, t, -np.inf)
                cand = []          # (t, conds, n, mu)
                tv = t[valid]
                n_rules += tv.size
                n_gt3 += int((tv > 3).sum()); n_gt2 += int((tv > 2).sum())
                # migliori singole/coppie
                flat = np.argsort(t, axis=None)[::-1]
                for f in flat[:PER_CELL]:
                    i, j = divmod(int(f), nC)
                    cand.append((t[i, j], (i,) if i == j else (i, j), N[i, j], mu[i, j]))
                # beam: le migliori coppie (i != j) estese con una terza condizione
                tp = np.where(np.eye(nC, dtype=bool), -np.inf, t)
                seen = set()
                n3 = 0
                best3 = []
                for f in np.argsort(tp, axis=None)[::-1][:BEAM]:
                    i, j = divmod(int(f), nC)
                    if not np.isfinite(tp[i, j]):
                        break
                    w = Mo[:, i] * Mo[:, j]
                    n_ = Mo.T @ w; s_ = Mo.T @ (w * y0); q_ = Mo.T @ (w * y0 ** 2)
                    t3, mu3 = _tstat(s_, q_, n_, side)
                    for c in range(nC):
                        if feat[c] in (feat[i], feat[j]) or n_[c] < N_MIN:
                            continue
                        key = tuple(sorted((i, j, c)))
                        if key in seen:
                            continue
                        seen.add(key)
                        n3 += 1
                        if np.isfinite(t3[c]):
                            best3.append((t3[c], key, n_[c], mu3[c]))
                            if t3[c] > 3: n_gt3 += 1
                            if t3[c] > 2: n_gt2 += 1
                n_rules += n3
                best3.sort(key=lambda r: -r[0])
                cand += best3[:PER_CELL]
                cand.sort(key=lambda r: -r[0])
                cell_best = cand[0][0] if cand else -np.inf
                tmax = max(tmax, cell_best)
                for c_ in cand[:PER_CELL]:
                    cells.append(dict(T=T, h=h, k=k, m=m, side=side, conds=c_[1], t_search=float(c_[0]),
                                      n_search=int(c_[2]), mean_search=float(c_[3])))
                if want_lots:
                    all_t = np.concatenate([tv[np.isfinite(tv)], np.array([b[0] for b in best3])])
                    lots.append(dict(T=T, h=str(h), side=side, n_rules=int(tv.size + n3),
                                     best_t=float(cell_best),
                                     q50=float(np.percentile(all_t, 50)), q95=float(np.percentile(all_t, 95)),
                                     q99=float(np.percentile(all_t, 99)), n_t_gt2=int((all_t > 2).sum()),
                                     n_t_gt3=int((all_t > 3).sum())))
    top = pd.DataFrame(cells).sort_values("t_search", ascending=False).head(TOPK).reset_index(drop=True)
    # selezione 2016-2018, regole congelate
    tsel, msel, nsel = [], [], []
    for r in top.itertuples():
        w = np.ones(len(v_idx), bool)
        for c in r.conds:
            w &= M[v_idx, r.k, c]
        y = Y[v_idx, r.k, r.m][w]
        y = y[np.isfinite(y)]
        net = r.side * y - cm.COST
        if len(net) >= 10:
            tsel.append(net.mean() / (net.std(ddof=1) / np.sqrt(len(net))))
        else:
            tsel.append(np.nan)
        msel.append(net.mean() if len(net) else np.nan)
        nsel.append(len(net))
    top["t_sel"] = tsel; top["mean_sel"] = msel; top["n_sel"] = nsel
    ts = top["t_sel"].fillna(-np.inf)
    stats = dict(S1_max_t_search=float(tmax),
                 S2_n_survivors=int(((ts > T_SURV) & (top["mean_sel"] > 0)).sum()),
                 S3_max_t_sel=float(ts.max()),
                 S4_mean_t_sel=float(top["t_sel"].mean()),
                 S5_n_t_gt3_search=int(n_gt3),
                 n_strong=int((ts > T_STRONG).sum()),
                 n_rules=int(n_rules), n_t_gt2_search=int(n_gt2),
                 top100_mean_t_search=float(top["t_search"].mean()))
    return stats, top, lots


def placebo_Y(null: str, rep: int) -> np.ndarray:
    Y = _G["P"]["G"]
    rng = np.random.default_rng(10_000 + rep if null == "sign" else 20_000 + rep)
    ns = Y.shape[0]
    if null == "sign":
        s = rng.choice([-1.0, 1.0], size=ns)
        return Y * s[:, None, None]
    # blocchi di 20 sessioni, permutati separatamente dentro ricerca e selezione
    out = Y.copy()
    for idx in (_G["s_idx"], _G["v_idx"]):
        blocks = [idx[i:i + 20] for i in range(0, len(idx), 20)]
        order = rng.permutation(len(blocks))
        new = np.concatenate([blocks[o] for o in order])
        out[idx] = Y[new]
    return out


def _worker(args):
    null, rep = args
    st, top, _ = run_pipeline(placebo_Y(null, rep))
    st.update(null=null, rep=rep, best_rule_t_sel=float(top["t_sel"].iloc[0]) if len(top) else np.nan)
    return st


def main():
    t0 = time.time()
    _setup()
    names = cm.cond_names()
    st, top, lots = run_pipeline(_G["P"]["G"], want_lots=True)
    top["rule"] = top["conds"].apply(lambda cs: " & ".join(names[c] for c in cs))
    top.drop(columns="conds").to_csv(cm.CACHE / "real_top100.csv", index=False)
    pd.DataFrame(lots).to_csv(cm.CACHE / "real_lots.csv", index=False)
    print("REALE", st, f"{time.time()-t0:.0f}s", flush=True)

    from multiprocessing import Pool
    n_rep = {"sign": 500, "block": 200}
    res = {}
    with Pool(30, initializer=_setup) as pool:
        for null in ("sign", "block"):
            out = pool.map(_worker, [(null, r) for r in range(n_rep[null])], chunksize=2)
            df = pd.DataFrame(out)
            df.to_csv(cm.CACHE / f"placebo_{null}.csv", index=False)
            res[null] = df
            print(null, f"{time.time()-t0:.0f}s", flush=True)

    # --------------------------------------------------------------- registro
    for L in lots:
        core.record(cm.FAM, f"lot_T{L['T']}_h{L['h']}_s{L['side']:+d}",
                    f"lotto di ricerca 2010-06..2015-12: T={L['T']} h={L['h']} lato={L['side']} "
                    f"(singole+coppie complete, triple via beam {BEAM})", "discovery",
                    {"n": L["n_rules"]}, kind="search_lot", **{k: v for k, v in L.items() if k not in ("T", "h", "side")})
    for r in top.itertuples():
        core.record(cm.FAM, f"sel_T{r.T}_h{r.h}_s{r.side:+d}_{r.rule}",
                    f"TOP100 della ricerca valutata in selezione 2016-2018: T={r.T} h={r.h} lato={r.side} {r.rule}",
                    "discovery", {"n": int(r.n_sel), "mean": float(r.mean_sel)}, kind="selection_eval",
                    t_search=r.t_search, n_search=r.n_search, mean_search=r.mean_search, t_sel=r.t_sel)
    summ = {}
    for null, df in res.items():
        d = {}
        for s in ("S1_max_t_search", "S2_n_survivors", "S3_max_t_sel", "S4_mean_t_sel", "S5_n_t_gt3_search"):
            d[s] = dict(real=st[s], p=float((df[s] >= st[s]).mean()),
                        q50=float(df[s].median()), q95=float(df[s].quantile(0.95)), max=float(df[s].max()))
        summ[null] = d
        core.record(cm.FAM, f"placebo_{null}", f"pipeline intera ripetuta su {len(df)} placebo ({null})",
                    "discovery", {"n": len(df)}, kind="placebo_summary", summary=d)
    core.record(cm.FAM, "real_pipeline", "pipeline reale: statistiche S1..S5", "discovery",
                {"n": st["n_rules"]}, kind="real_summary", **st)
    import json
    print(json.dumps(summ, indent=1))


if __name__ == "__main__":
    main()
