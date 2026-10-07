"""F6b approfondimento - la direzione nei minuti di fetta (:00/:15/:30/:45) segue il trend precedente?
Controlli: in unita' di segno (hit rate, immune alla volatilita' del minuto), per anno, per minuto dell'ora,
escludendo gli orari di notizie (10:00, 10:30, 14:00), finestre di trend {30, 60, 120}."""
import numpy as np
import pandas as pd

from lab.r2_footprints import common as C

pd.set_option("display.width", 250)

if __name__ == "__main__":
    D, daily = C.get()
    ok = D["valid"] & D["in_phase"]
    sess = D["sess"][ok]
    a0, b0 = C.sm_of("09:30"), C.sm_of("16:00")
    Cp = D["Cf"][ok][:, a0 - 121:b0]           # Cp[:, 121 + k] = close della barra k (09:30+k); Cp[:,120] = 09:29
    dC = np.diff(Cp, axis=1)[:, 120:]          # rendimento della barra k
    nk = b0 - a0
    kk = np.arange(nk)
    mo = (kk + 30) % 60
    hhmm = np.array([f"{(570 + k) // 60:02d}:{(570 + k) % 60:02d}" for k in kk])
    base = (kk >= 35) & (kk < 370) & ~np.isin(hhmm, ["11:30", "15:00"])
    news = np.isin(hhmm, ["10:00", "10:30", "14:00"])
    res = []
    for L in [30, 60, 120]:
        tr = Cp[:, 120 + kk] - Cp[:, 120 + kk - L]          # close barra k-1 meno close barra k-1-L
        for unit in ["pts", "sign"]:
            x = dC if unit == "pts" else np.sign(dC)
            prod = np.sign(tr) * x
            for nm, grp in (("q15", base & (mo % 15 == 0) & ~news), ("q30", base & (mo % 30 == 0) & ~news),
                            ("h00", base & (mo == 0) & ~news)):
                oth = base & (mo % 5 != 0)
                v = np.nanmean(prod[:, grp], 1) - np.nanmean(prod[:, oth], 1)
                st = C.rec(f"F6b2_L{L}_{unit}_{nm}", f"F6b2 sign(trend {L}m) x {unit} del minuto {nm} (senza 10:00/10:30/"
                           "14:00) meno minuti non multipli di 5", v, sess, unit=unit)
                y = pd.Series(v).groupby(sess.year).mean()
                res.append(dict(L=L, unit=unit, g=nm, mean=st["mean"], lo=st["lo"], hi=st["hi"], p=st["p_two"],
                                yrs=f"{(y > 0).sum()}/9", lvl_oth=np.nanmean(prod[:, oth])))
    print(pd.DataFrame(res).round(4).to_string())
    # profilo per minuto dell'ora (L=60, segno)
    tr = Cp[:, 120 + kk] - Cp[:, 120 + kk - 60]
    prod = np.sign(tr) * np.sign(dC)
    prof = pd.Series(np.nanmean(np.where(base & ~news, prod, np.nan), 0)).groupby(mo).mean()
    print("hit-rate netto (segno) per minuto dell'ora, L=60:")
    print(prof.round(4).to_string())
    # anno per anno del principale (L=60 segno q15)
    grp = base & (mo % 15 == 0) & ~news
    oth = base & (mo % 5 != 0)
    v = np.nanmean(prod[:, grp], 1) - np.nanmean(prod[:, oth], 1)
    print(pd.Series(v).groupby(sess.year).agg(["mean", "count"]).round(4).T)
