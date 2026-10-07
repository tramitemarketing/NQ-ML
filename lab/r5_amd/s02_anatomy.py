"""Anatomia di P0 (descrittiva, registrata): lordo, R lordo, coda destra (quanti 10R+), peso del costo."""
import numpy as np
from lab import core
from lab.r5_amd import common as C

if __name__ == "__main__":
    bars, daily = core.load("discovery")
    D = C.Data(bars, daily)
    for tid, kw in [("P0", {}), ("C1", dict(require_ob=False))]:
        t = C.simulate(D, **kw)
        g = t.gross_pts.to_numpy()
        R = t.R.to_numpy()
        sg = core.day_block_bootstrap(g, t.session.values)
        sR = core.day_block_bootstrap(R, t.session.values)
        cost_R = float(np.median(core.COST_RT_POINTS / t.risk))
        q = {f"R>={k}": float((R >= k).mean()) for k in (2, 5, 10)}
        mx = float(R.max())
        core.record(C.FAM, f"A_{tid}_gross", f"anatomia {tid}: lordo punti e R lordo", "discovery", sg,
                    R_mean=sR["mean"], R_lo=sR["lo"], R_hi=sR["hi"], R_p_two=sR["p_two"], cost_R_med=cost_R, R_max=mx, **q)
        print(f"{tid}: lordo {sg['mean']:+.2f} [{sg['lo']:+.2f};{sg['hi']:+.2f}] p2 {sg['p_two']:.3f} | "
              f"R lordo {sR['mean']:+.3f} [{sR['lo']:+.3f};{sR['hi']:+.3f}] | costo mediano {cost_R:.2f}R | "
              f"{ {k: round(v,3) for k,v in q.items()} } R max {mx:.1f} | rischio mediano {t.risk.median():.1f} pt")
        # rischio piccolo vs grande
        big = t.risk >= t.risk.median()
        for nm, m in (("rischio<med", ~big), ("rischio>=med", big)):
            s = core.day_block_bootstrap(t.gross_pts[m].to_numpy() - core.COST_RT_POINTS, t.session[m].values)
            print(f"   {nm}: n {s['n']} netto {s['mean']:+.2f} [{s['lo']:+.2f};{s['hi']:+.2f}]")
            core.record(C.FAM, f"A_{tid}_{nm}", f"anatomia {tid} per dimensione del rischio", "discovery", s)
