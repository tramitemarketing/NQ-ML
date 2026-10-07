"""Approfondimento: grande movimento 08:30-09:30 -> inversione all'apertura RTH (B2_pre_to_h1).
Side = -sign(pre) (fade). Soglie causali su |pre|/ATR20; uscite 10:00 / 10:30 / 12:00."""
import numpy as np, pandas as pd
from lab import core
from lab.cross_session.build_cache import get
from lab.cross_session.common import evaluate, fmt
from lab.cross_session.series import segments, causal_q

t = get(); S = segments(t); m = t["valid"] & t["in_phase"]; atr = t.atr20
z = (S["P_sig"] / atr).abs()
exits = {"10": t.ent_s10, "1030": t.ent_s1030, "12": t.ent_s12}
for q in (0.5, 0.67, 0.8, 0.9):
    big = z > causal_q(z, q)
    for k, x in exits.items():
        tgt = x - t.ent_s0930
        side = -np.sign(S["P_sig"]).where(big)
        r = evaluate(f"F1_prefade_q{int(q*100)}_to{k}", f"fade di 08:30-09:30 se |pre|/ATR>q{int(q*100)} causale, 09:30->{k}", side * tgt, side, tgt, atr, m)
        print(fmt(f"F1_prefade_q{int(q*100)}_to{k}", r))
