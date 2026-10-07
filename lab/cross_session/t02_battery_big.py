"""Batteria 2: stesse 20 coppie della batteria 1, solo quando |pred|/ATR20 supera il proprio
67-esimo percentile CAUSALE (250 sessioni precedenti, min 60). Continuazione = side sign(pred)."""
import numpy as np, pandas as pd
from lab.cross_session.build_cache import get
from lab.cross_session.common import evaluate, fmt
from lab.cross_session.series import segments, PAIRS, causal_q

t = get(); S = segments(t); m = t["valid"] & t["in_phase"]; atr = t.atr20
for name, p, y in PAIRS:
    z = (S[p] / atr).abs()
    big = z > causal_q(z)
    side = np.sign(S[p]).where(big)
    r = evaluate("B2_" + name, f"{p}->{y} solo |pred|/ATR > q67 causale [continuazione, punti]",
                 side * S[y], side, S[y], atr, m)
    print(fmt("B2_" + name, r))
