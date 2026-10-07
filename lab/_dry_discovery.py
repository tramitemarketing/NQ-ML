import time, pandas as pd, numpy as np
from lab import core, controller
cs=controller.all_candidates()
cache={}
for c in cs:
    w=int(c.get('warmup_days',0)); t0=time.time()
    b,d=core.load('discovery',warmup_days=w)
    t=c['fn'](b.copy(),d.copy()); t['session']=pd.to_datetime(t['session'])
    t=t[t.session.isin(d.index[d.in_phase])]
    g=t.gross_pts.to_numpy(float)
    net = g if c.get('kind')=='regularity' else g-core.COST_RT_POINTS
    st=core.day_block_bootstrap(net,t.session.values,2000)
    print(f"{c['id']:<40} n={st['n']:>6} mean={st['mean']:+.4f} [{st['lo']:+.4f},{st['hi']:+.4f}] declared={c.get('discovery')} {time.time()-t0:.0f}s", flush=True)
