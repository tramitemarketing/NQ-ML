"""H0: qualita' della previsione del range (verifica dello strumento, non un'ipotesi di trading).
R2 fuori campione (rolling) di log range RTH: R_hat contro naive media20; calibrazione del rapporto."""
import numpy as np

from lab.r2_range import common as C

bars, daily, M, F = C.setup_discovery()
f = F[F["R_hat"].notna() & F["R_naive"].notna()]
y = np.log(f["rng_pts"])
for name in ("R_hat", "R_naive"):
    e = y - np.log(f[name])
    r2 = 1 - ((e - 0) ** 2).sum() / ((y - y.mean()) ** 2).sum()
    ratio = f["rng_pts"] / f[name]
    st = {"n": len(f), "r2_oos_log": float(r2), "ratio_mean": float(ratio.mean()), "ratio_median": float(ratio.median()),
          "corr_log": float(np.corrcoef(y, np.log(f[name]))[0, 1])}
    print(name, st)
    C.rec(f"h00_forecast_{name}", f"qualita' previsione range RTH ({name}): R2 oos su log range, calibrazione", st)
# frazione di range gia' percorso a varie ore (media), per tarare le soglie
ok = M["ok"]
for hh in (600, 630, 690, 750, 810, 870, 930, 959):
    used = (M["runH"][ok, hh - C.M0] - M["runL"][ok, hh - C.M0]) / M["R_hat"][ok]
    print(hh // 60, hh % 60, "used/R_hat: mediana %.2f  p80 %.2f  p20 %.2f" % tuple(np.percentile(used, [50, 80, 20])))
