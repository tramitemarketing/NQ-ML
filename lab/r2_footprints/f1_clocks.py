"""F1 - orologi istituzionali: impronta di volume e volatilita' al minuto, per anno.
spike(m) = log(x_m) - log(mediana di x sui minuti m-10..m+10 esclusi m-1..m+1), x = volume o range H-L (+1 tick).
"""
import numpy as np
import pandas as pd

from lab.r2_footprints import common as C


def spike_matrix(X: np.ndarray, lo: int, hi: int) -> np.ndarray:
    """Per ogni minuto in [lo, hi) il log-rapporto contro la mediana dei vicini."""
    L = np.log(X)
    out = np.full((X.shape[0], hi - lo), np.nan)
    for k, m in enumerate(range(lo, hi)):
        nb = [j for j in range(m - 10, m + 11) if abs(j - m) > 1 and 0 <= j < X.shape[1]]
        out[:, k] = L[:, m] - np.nanmedian(L[:, nb], axis=1)
    return out


if __name__ == "__main__":
    D, daily = C.get()
    ok = D["valid"] & D["in_phase"]
    V = np.where(D["has"], D["V0"], np.nan)[ok] + 1.0
    R = (D["adj_high"] - D["adj_low"])[ok] + 0.25
    sess = D["sess"][ok]
    yrs = sess.year.to_numpy()
    lo, hi = C.sm_of("09:20"), C.sm_of("16:59") + 1
    SV, SR = spike_matrix(V, lo, hi), spike_matrix(R, lo, hi)
    mins = [f"{(1080 + lo + k) // 60 % 24:02d}:{(1080 + lo + k) % 60:02d}" for k in range(hi - lo)]
    prof = pd.DataFrame({"vol": np.nanmean(SV, 0), "rng": np.nanmean(SR, 0)}, index=mins)
    print("Top 25 spike di volume (media 2010-18):")
    print(prof.sort_values("vol", ascending=False).head(25).round(3))
    print("Top 15 spike di range:")
    print(prof.sort_values("rng", ascending=False).head(15).round(3))

    targets = ["09:30", "10:00", "10:30", "11:00", "11:30", "12:00", "12:30", "13:00", "14:00", "15:00",
               "15:45", "15:50", "15:55", "15:59", "16:14"]
    rows = []
    for t in targets:
        k = mins.index(t)
        for nm, S in (("vol", SV), ("rng", SR)):
            st = C.rec(f"F1_{nm}_{t}", f"F1 impronta {nm} al minuto {t} NY: log(x)/mediana vicini +-10 (escl. +-1), "
                       "sessioni valide 2010-18", S[:, k], sess, unit="log-ratio")
            y = pd.Series(S[:, k]).groupby(yrs).mean()
            rows.append(dict(t=t, x=nm, mean=st["mean"], lo=st["lo"], hi=st["hi"],
                             **{str(a): round(b, 2) for a, b in y.items()}))
    pd.set_option("display.width", 250)
    print(pd.DataFrame(rows).round(3).to_string())
    prof.to_csv(C.HERE / "cache" / "f1_profile.csv")
