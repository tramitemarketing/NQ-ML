"""H5_ON rottura (close oltre il max/min della notte), finestra 09:35-12:00, fade.
(a) coerenza: stessa regola sui livelli PD e PW a 120m;
(b) uscite a bracket in unita' di ADR20 (stop x target), limite 120m, per troncare le code;
(c) ingresso ritardato: solo se entro 120m (niente) -> gia' coperto; qui solo (a) e (b)."""
import numpy as np
from lab.micro.common import Data, evaluate_pair
from lab.micro.h05_levels import level_events, levels
from lab.micro.h11_momsurface import adr20

D = Data()
A = adr20(D)
L = levels(D)
for lv in ("PD", "PW"):
    U, Dn = L[lv]
    ei, es, ek = level_events(D.h, D.l, D.c, D.m, D.scode, U.astype(float), Dn.astype(float), 575, 720)
    sel = D.inph[ei] & (ek == 1)
    evaluate_pair(D, ei[sel], es[sel], 120, f"H14_{lv}_break_575-720_H120",
                  f"{lv} break 09:35-12:00, fade, uscita 120m", end="rth")
U, Dn = L["ON"]
ei, es, ek = level_events(D.h, D.l, D.c, D.m, D.scode, U.astype(float), Dn.astype(float), 575, 720)
sel = D.inph[ei] & (ek == 1) & np.isfinite(A[ei])
s, sd = ei[sel], es[sel]
a = A[s]
for st in (0.15, 0.25, 0.40):
    for tg in (0.15, 0.25, 0.40):
        evaluate_pair(D, s, sd, 120, f"H14_ONbreak_bracket_s{st}_t{tg}",
                      f"ON break 09:35-12:00 fade, stop {st} ADR20, target {tg} ADR20 (trade-through), limite 120m",
                      stop=st * a, tgt=tg * a, end="rth")
