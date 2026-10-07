"""A02: selezione interna per la direzione. Per tutte le 60 configurazioni di A01: IC su 2011-2014 (A) e
su 2015-2018 (B). Regola dichiarata: si sceglie in A la configurazione con |IC| massimo (col suo segno) e si
guarda B senza ritocchi. In piu': quante configurazioni hanno lo stesso segno in A e B (atteso ~50 %% se rumore),
e la stessa statistica sui placebo (200 griglie di analoghi casuali)."""
import numpy as np
import pandas as pd

from lab.r2_analog import common as C

bars, daily, M = C.setup_discovery()
ok = M["ok"]; sess = M["sess"].to_numpy(); yr = M["year"]
A = yr <= 2014; B = yr >= 2015
rows = []
for W in C.WINDOWS:
    y = C.outcome(M, W)["y"]
    for rep in C.REPS:
        D = C.distance_matrix(C.features(M, W, rep), rep)
        NN = C.neighbors(D, ok, 100)
        base = ok & M["in_phase"] & (NN[:, 0] >= 0) & np.isfinite(y)
        for K in C.KS:
            p = C.agg(NN, K, y)
            ra = np.corrcoef(p[base & A], y[base & A])[0, 1]
            rb = np.corrcoef(p[base & B], y[base & B])[0, 1]
            rows.append(dict(W=W, rep=rep, K=K, icA=ra, icB=rb))
df = pd.DataFrame(rows)
print(df.round(4).to_string())
same = float((np.sign(df.icA) == np.sign(df.icB)).mean())
best = df.iloc[df.icA.abs().argmax()]
print("stesso segno A/B:", same, " migliore in A:", best.to_dict())
st = {"n_configs": len(df), "same_sign_share": same, "best_cfg": f"W{best.W}_{best.rep}_K{best.K}",
      "best_icA": float(best.icA), "best_icB": float(best.icB),
      "corr_icA_icB": float(np.corrcoef(df.icA, df.icB)[0, 1])}
# placebo: stessa statistica con analoghi casuali
rng = np.random.default_rng(7)
same_pl, corr_pl, bestB_pl = [], [], []
for r in range(100):
    P = C.random_neighbors(ok, 100, rng)
    rr = []
    for W in C.WINDOWS:
        y = C.outcome(M, W)["y"]
        base = ok & M["in_phase"] & (P[:, 0] >= 0) & np.isfinite(y)
        for K in C.KS:
            p = C.agg(P, K, y)
            rr.append((np.corrcoef(p[base & A], y[base & A])[0, 1], np.corrcoef(p[base & B], y[base & B])[0, 1]))
    rr = np.array(rr)
    same_pl.append((np.sign(rr[:, 0]) == np.sign(rr[:, 1])).mean())
    corr_pl.append(np.corrcoef(rr[:, 0], rr[:, 1])[0, 1])
    j = np.abs(rr[:, 0]).argmax()
    bestB_pl.append(rr[j, 1] * np.sign(rr[j, 0]))
st["plac_same_sign_mean"] = float(np.mean(same_pl))
st["plac_corr_mean"] = float(np.mean(corr_pl))
st["best_B_signed"] = float(best.icB * np.sign(best.icA))
st["plac_best_B_signed_pct"] = float((np.array(bestB_pl) < st["best_B_signed"]).mean())
print(st)
C.rec("a02_direction_split", "selezione interna direzione: migliore config analoghi su 2011-14 verificata su 2015-18; "
      "concordanza di segno delle 60 config vs placebo", st)
