"""F3c - placebo per la continuazione dell'ultimo minuto (settlement 15:59): la stessa misura
sign(r barra m) x (C[m+15] - C[m]) su OGNI minuto m 10:00-15:44 (distribuzione dei placebo) e sugli altri
minuti di fine giornata. Unita': punti e unita' di sigma1m (per confrontare minuti a volatilita' diversa)."""
import numpy as np
import pandas as pd

from lab.r2_footprints import common as C
from lab.r2_footprints.f3b_magnitude import sigma1m

pd.set_option("display.width", 250)

if __name__ == "__main__":
    D, daily = C.get()
    ok = D["valid"] & D["in_phase"]
    sess = D["sess"][ok]
    sig = sigma1m(D, D["valid"])[ok]
    Cf = D["Cf"][ok]
    out = []
    for m in range(C.sm_of("10:00"), C.sm_of("16:00")):
        s = np.sign(Cf[:, m] - Cf[:, m - 1])
        g = s * (Cf[:, m + 15] - Cf[:, m])
        out.append(dict(m=m, t=f"{(1080 + m) // 60 % 24:02d}:{(1080 + m) % 60:02d}", pts=np.nanmean(g),
                        sig=np.nanmean(g / sig)))
    o = pd.DataFrame(out)
    pl = o[o.t < "15:45"]
    print("placebo 10:00-15:44: media pts", round(pl.pts.mean(), 3), "sd", round(pl.pts.std(), 3),
          "| sigma: media", round(pl.sig.mean(), 4), "sd", round(pl.sig.std(), 4))
    print(o[o.t >= "15:40"].round(4).to_string())
    rank = (pl.sig >= o.loc[o.t == "15:59", "sig"].iloc[0]).mean()
    C.rec("F3c_placebo_1559", "F3c placebo: frazione dei 345 minuti 10:00-15:44 con continuazione (sigma) >= quella della "
          "barra 15:59; descrittivo", pl.sig.to_numpy(), np.array([sess[0]] * len(pl)), frac_ge=float(rank),
          val_1559=float(o.loc[o.t == "15:59", "sig"].iloc[0]))
    print("frazione placebo >= 15:59:", rank)
    print("top 10 minuti placebo (sigma):")
    print(pl.sort_values("sig", ascending=False).head(10).round(4).to_string())
    # 15:59 anno per anno in sigma e in punti, e sottoperiodi della 15:50
    m = C.sm_of("15:59")
    g = np.sign(Cf[:, m] - Cf[:, m - 1]) * (Cf[:, C.sm_of("16:14")] - Cf[:, m])
    print(pd.DataFrame({"pts": g, "sig": g / sig}).groupby(sess.year).mean().round(3).T)
    st = C.rec("F3c_1559_sigma", "F3c sign(r barra 15:59) x (C 16:14 - C 15:59) in unita' sigma1m", g / sig, sess, unit="sigma1m")
    print("15:59 in sigma:", C.fmt(st))
    m0 = C.sm_of("15:51")
    g2 = np.sign(Cf[:, m0] - Cf[:, m0 - 2]) * (Cf[:, C.sm_of("15:59")] - Cf[:, m0])
    y = pd.Series(g2 / sig).groupby(sess.year).mean()
    print("15:50-15:52 -> 16:00 in sigma per anno:", y.round(3).to_dict())
    for nm, mk in (("2010-13", sess.year <= 2013), ("2014-18", sess.year >= 2014)):
        st = C.rec(f"F3c_imb1550_{nm}", f"F3c sign(15:50->15:52) x (16:00 - 15:52) in sigma, {nm} (la 15:50 cresce nel tempo)",
                   (g2 / sig)[mk], sess[mk], unit="sigma1m")
        print(nm, C.fmt(st))
