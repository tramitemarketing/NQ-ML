"""B4 - rottura e ritest: dopo la prima rottura (close oltre il livello di >= 1 tick, close precedente
dentro) si entra NEL VERSO della rottura con un limite AL LIVELLO rotto (ritest) o a meta' strada
fra close e livello. AGG di confronto = rottura a mercato. Livelli: massimo/minimo RTH di ieri (PD),
della notte 18:00-09:29 (ON), della prima ora 09:30-10:29 (IB). Eventi: PD e ON 09:35-14:59, IB
10:30-14:59 (definizione degli eventi = quella del giro 1, _on_break_events, lato invertito).
Griglia dichiarata: L {livello, meta'}, N {15, 60}, uscita {60 m, 15:59}, niente stop; piu' una
variante con stop sig60*sqrt15 dal fill (N 60, uscita 15:59)."""
import numpy as np
import pandas as pd

from lab.r2_execution.common import load, compare, summarize, xi_after, xi_at_minute
from lab.micro.candidates import overnight_range, _on_break_events

D, B = load()
ns = int(D.scode.max()) + 1
b = pd.DataFrame({"s": D.scode, "h": D.h, "l": D.l, "m": D.m, "rth": D.rth})
r = b[b.rth].groupby("s").agg(h=("h", "max"), l=("l", "min")).reindex(range(ns))
PDU = r["h"].shift(1).to_numpy(float); PDD = r["l"].shift(1).to_numpy(float)
ONU, OND = overnight_range(D)
ib = b[(b.m >= 570) & (b.m < 630)].groupby("s").agg(h=("h", "max"), l=("l", "min")).reindex(range(ns))
IBU, IBD = ib["h"].to_numpy(float), ib["l"].to_numpy(float)

LV = {"PD": (PDU, PDD, 575, 900), "ON": (ONU, OND, 575, 900), "IB": (IBU, IBD, 630, 900)}
for ln, (U, Dn, lo, hi) in LV.items():
    ei, es = _on_break_events(D.h, D.l, D.c, D.m, D.scode, U, Dn, lo, hi)
    side = -es                                    # continuazione
    lvl = np.where(side > 0, U[D.scode[ei]], Dn[D.scode[ei]])
    dist = np.abs(D.c[ei] - lvl)                  # distanza close-livello (>= 1 tick)
    xs = {"H60": xi_after(D, ei, 60), "close": xi_at_minute(D, ei, 960)}
    for Ln, off in (("lvl", dist), ("half", dist / 2)):
        for N in (15, 60):
            for xn, xi in xs.items():
                t = compare(D, B, ei, side, xi, off, N)
                summarize(t, f"B4_{ln}_{Ln}_N{N}_{xn}", f"rottura {ln} continuazione, limite al {Ln}, attesa {N}m, uscita {xn}")
        t = compare(D, B, ei, side, xs["close"], off, 60, stop=D.sig60[ei] * np.sqrt(15))
        summarize(t, f"B4_{ln}_{Ln}_N60_close_stop", f"rottura {ln} continuazione, limite al {Ln}, attesa 60m, uscita 15:59, stop sig60*sqrt15")
