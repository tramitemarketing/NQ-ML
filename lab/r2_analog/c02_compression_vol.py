"""C02: la compressibilita' della mattina predice la vol del pomeriggio? (seguito di C01-P3, dichiarato prima)
Misure di complessita' sui rendimenti 1m 09:30-11:59 (150 barre), tutte note alle 12:00:
  lz_sign : LZ76 della stringa dei segni (-,0,+) normalizzata n/log2 n   (quella di C01)
  lz_bin  : LZ76 dei segni con 0 assegnato al segno precedente (toglie la discretezza del tick)
  pe3     : entropia di permutazione d'ordine 3 (pattern ordinali, ties rotti dall'ordine)
  zero    : quota di barre 1m con rendimento esattamente 0 (controllo: discretezza)
Esito: lrv del pomeriggio 12:00-16:00 (W=150). Benchmark = vol_bench_X esteso (A04) + zero + rho mattina.
q = (lrv - bench)^2 - (lrv - bench+misura)^2, OLS mobile 500 sessioni. Piu' correlazioni parziali in campione."""
import numpy as np
import pandas as pd

from lab import core
from lab.r2_analog import common as C
lz76 = C.lz76

bars, daily, M = C.setup_discovery()
ok = M["ok"]; sess = M["sess"].to_numpy(); n = len(ok)
W = 150
r1 = np.diff(np.log(np.column_stack([M["O"][:, :1], M["C"][:, :150]])), axis=1)
lz_s = np.full(n, np.nan); lz_b = np.full(n, np.nan); pe = np.full(n, np.nan)
zero = (r1 == 0).mean(1)
norm = 150 / np.log2(150)
for i in np.where(ok)[0]:
    s = np.sign(r1[i]).astype(int)
    lz_s[i] = lz76(s.tolist()) / norm
    b = s.copy()
    for k in range(len(b)):
        if b[k] == 0:
            b[k] = b[k - 1] if k > 0 and b[k - 1] != 0 else 1
    lz_b[i] = lz76(b.tolist()) / norm
    x = np.cumsum(r1[i])
    pat = np.argsort(np.column_stack([x[:-2], x[1:-1], x[2:]]), axis=1, kind="stable")
    code = pat[:, 0] * 9 + pat[:, 1] * 3 + pat[:, 2]
    p = np.bincount(code, minlength=27); p = p[p > 0] / p.sum()
    pe[i] = -(p * np.log2(p)).sum() / np.log2(6)
o = C.outcome(M, W); lrv = o["lrv"]
r5 = M["r5"]
rho_m = (r5[:, :29] * r5[:, 1:30]).sum(1) / (r5[:, :30] ** 2).sum(1)
Xe = np.column_stack([C.vol_bench_X(M, W, extended=True), zero, rho_m])
be = C.roll_pred(lrv, Xe, ok)
for nm, v in (("lz_sign", lz_s), ("lz_bin", lz_b), ("pe3", pe)):
    aug = C.roll_pred(lrv, np.column_stack([Xe, v]), ok)
    m = ok & M["in_phase"] & np.isfinite(aug) & np.isfinite(be)
    q = (lrv - be) ** 2 - (lrv - aug) ** 2
    st = core.day_block_bootstrap(q[m], sess[m], n_boot=2000)
    yrs = pd.Series(q[m]).groupby(M["year"][m]).mean()
    st["years_pos"] = f"{int((yrs > 0).sum())}/{len(yrs)}"
    mm = ok & M["in_phase"] & np.isfinite(Xe).all(1) & np.isfinite(v) & np.isfinite(lrv)
    Z = np.column_stack([np.ones(mm.sum()), Xe[mm]])
    ra = v[mm] - Z @ np.linalg.lstsq(Z, v[mm], rcond=None)[0]
    rb = lrv[mm] - Z @ np.linalg.lstsq(Z, lrv[mm], rcond=None)[0]
    st["pcorr_insample"] = float(np.corrcoef(ra, rb)[0, 1])
    st["raw_corr"] = float(np.corrcoef(v[mm], lrv[mm])[0, 1])
    st["corr_with_zero"] = float(np.corrcoef(v[mm], zero[mm])[0, 1])
    pcy = {}
    for y in sorted(set(M["year"][mm])):
        s = M["year"][mm] == y
        pcy[int(y)] = round(float(np.corrcoef(ra[s], rb[s])[0, 1]), 3)
    st["pcorr_yearly"] = pcy
    print(nm, C.fmt(st), st["pcorr_insample"], st["raw_corr"], st["corr_with_zero"], pcy)
    C.rec(f"c02_{nm}_lrv150", f"complessita' {nm} dei segni 1m 09:30-12 -> vol pomeriggio, oltre benchmark esteso+zero+rho (OOS)", st)
