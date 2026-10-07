"""Definizione pulita della regolarita' (scritta prima di guardare): RTH, barra di segnale fra 09:45 e
14:59 (finestra di 15 minuti interamente in RTH), |close_i - close_{i-15}| >= 3 * sigma60_i * sqrt(15)
(sigma60 = std delle 60 variazioni 1m fino a i-1), lato = verso del movimento, ingresso open i+1,
uscita a 30 minuti, un trade alla volta. Lordo in punti, bilaterale; anche netto per informazione."""
import numpy as np
from lab import core
from lab.micro.common import Data, evaluate, simulate
from lab.micro.candidates import surprise_cont_signals

D = Data()
s, side = surprise_cont_signals(D)
t = simulate(D, s, side, 30, end="rth")
st = evaluate(D, t, "H19_reg_final_net", "regolarita' finale (RTH 09:45-14:59, k15 z3 H30), netto")
tt = t[t.in_phase]
g = core.day_block_bootstrap(tt.gross_pts.to_numpy(), tt.session.to_numpy(), n_boot=10000)
y = core.yearly(tt.gross_pts.to_numpy(), tt.session)
g["years_pos"] = f"{int((y['mean'] > 0).sum())}/{len(y)}"
g["yearly_gross"] = {int(a): round(float(b), 3) for a, b in y["mean"].items()}
g["drop20_gross"] = core.drop_top(tt.gross_pts.to_numpy(), 20)
core.record("micro", "H19_reg_final_gross", "regolarita' finale (RTH 09:45-14:59, k15 z3 H30), LORDO bilaterale", "discovery", g)
print(g)
