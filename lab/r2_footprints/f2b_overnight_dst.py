"""F2b - orologi notturni ed esperimento naturale DST.
Tokyo (nessuna ora legale): apertura 09:00 JST = 19:00 NY in inverno (EST), 20:00 NY in estate (EDT).
Europa: apertura cash 08:00 Londra / 09:00 CET = 03:00 NY normalmente, 04:00 NY nelle settimane di disallineamento.
Impronta = log-rapporto del volume del minuto contro la mediana dei vicini +-10 (come F1)."""
import numpy as np
import pandas as pd

from lab.r2_footprints import common as C
from lab.r2_footprints.f1_clocks import spike_matrix

pd.set_option("display.width", 250)

if __name__ == "__main__":
    D, daily = C.get()
    ok = D["valid"] & D["in_phase"]
    V = np.where(D["has"], D["V0"], np.nan)[ok] + 1.0
    sess = D["sess"][ok]
    usd = D["us_dst"][ok]
    mis = D["lon_minus_ny"][ok] == 4
    lo, hi = C.sm_of("18:30"), C.sm_of("05:00")
    S = spike_matrix(V, lo, hi)
    k = lambda t: C.sm_of(t) - lo
    rows = []
    for t in ["19:00", "20:00", "20:30", "21:30", "02:00", "03:00", "04:00"]:
        for nm, grp in (("EDT", usd), ("EST", ~usd), ("mismatch", mis), ("normal", ~mis)):
            v = S[grp, k(t)]
            rows.append(dict(t=t, grp=nm, mean=np.nanmean(v), n=int(np.isfinite(v).sum())))
    tab = pd.DataFrame(rows).pivot(index="t", columns="grp", values="mean")
    print(tab.round(3).to_string())
    # test registrati: Tokyo 20:00 EDT - EST; 19:00 EST - EDT; Europa 03:00 normal - mismatch; 04:00 mismatch - normal
    for tid, t, g1, g0 in [("tokyo_2000", "20:00", usd, ~usd), ("tokyo_1900", "19:00", ~usd, usd),
                           ("eu_0300", "03:00", ~mis, mis), ("eu_0400", "04:00", mis, ~mis)]:
        a = S[g1, k(t)]
        st = C.rec(f"F2b_{tid}", f"F2b DST: impronta volume alle {t} NY nel gruppo in cui l'orologio estero cade li' "
                   "meno la media dell'altro gruppo", a - np.nanmean(S[g0, k(t)]), sess[g1], unit="log-ratio")
        print(tid, C.fmt(st))
