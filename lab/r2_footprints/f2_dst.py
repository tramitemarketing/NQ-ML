"""F2 - esperimento naturale DST (settimane in cui Londra e' 4h avanti a NY invece di 5h) e datazione
dell'impronta delle 15:50 per trimestre."""
import numpy as np
import pandas as pd

from lab.r2_footprints import common as C
from lab.r2_footprints.f1_clocks import spike_matrix

if __name__ == "__main__":
    D, daily = C.get()
    ok = D["valid"] & D["in_phase"]
    V = np.where(D["has"], D["V0"], np.nan)[ok] + 1.0
    R = (D["adj_high"] - D["adj_low"])[ok] + 0.25
    sess = D["sess"][ok]
    mis = D["lon_minus_ny"][ok] == 4
    print("sessioni di disallineamento:", mis.sum(), "su", len(mis))
    lo = C.sm_of("09:20")
    SV, SR = spike_matrix(V, lo, C.sm_of("16:10")), spike_matrix(R, lo, C.sm_of("16:10"))
    k = lambda t: C.sm_of(t) - lo
    rows = []
    for t in ["10:00", "10:30", "11:00", "11:30", "12:00", "12:30", "15:50", "15:45"]:
        for nm, S in (("vol", SV), ("rng", SR)):
            a, b = S[mis, k(t)], S[~mis, k(t)]
            # differenza disallineamento - normale: bootstrap su giorni (due campioni)
            vals = np.concatenate([a - np.nanmean(b), b - np.nanmean(b)])
            st = C.rec(f"F2_{nm}_{t}_mis", f"F2 DST: impronta {nm} alle {t} NY nelle settimane di disallineamento "
                       "Londra-NY (Londra +4h) - media delle settimane normali", a - np.nanmean(b), sess[mis],
                       unit="log-ratio", normal_mean=float(np.nanmean(b)))
            rows.append(dict(t=t, x=nm, normal=np.nanmean(b), mismatch=np.nanmean(a), diff=st["mean"],
                             lo=st["lo"], hi=st["hi"], n_mis=int(np.isfinite(a).sum())))
    print(pd.DataFrame(rows).round(3).to_string())

    # datazione della 15:50: media per trimestre
    q = pd.PeriodIndex(sess, freq="Q")
    s1550 = pd.Series(SV[:, k("15:50")]).groupby(q).mean()
    s1545 = pd.Series(SV[:, k("15:45")]).groupby(q).mean()
    s1100 = pd.Series(SV[:, k("11:00")]).groupby(q).mean()
    print(pd.DataFrame({"v1550": s1550, "v1545": s1545, "v1100": s1100}).round(2).T.to_string())
    C.rec("F2_date_1550", "F2 datazione impronta volume 15:50 per trimestre (descrittivo; media 2017-18 meno 2010-12)",
          SV[:, k("15:50")], sess, unit="log-ratio",
          by_quarter={str(a): round(float(b), 3) for a, b in s1550.items()})
