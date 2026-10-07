"""Batteria 1: il rendimento di un segmento predice il successivo? (continuazione = side sign(pred)).
Unita' primaria dichiarata PRIMA di guardare: punti per 1 contratto (quella del controller), con la
versione normalizzata per ATR20 (range intera sessione, 20 sessioni precedenti) come controllo, per non
far pesare solo il 2016-2018. Media > 0 = continuazione, < 0 = inversione (test bilaterale sul lordo)."""
import numpy as np, pandas as pd
from lab.cross_session.build_cache import get
from lab.cross_session.common import evaluate, fmt

t = get()
m = t["valid"] & t["in_phase"]
nxt = lambda s: s.shift(-1)          # valore della sessione successiva
prv = lambda s: s.shift(1)

A_sig = t.sig_s02 - t.ent_s18; A = t.ent_s02 - t.ent_s18
E_sig = t.sig_s0830 - t.ent_s02; E = t.ent_s0830 - t.ent_s02
AE_sig = t.sig_s0830 - t.ent_s18
P_sig = t.sig_s0930 - t.ent_s0830; P = t.ent_s0930 - t.ent_s0830
ON_sig = t.sig_s0930 - t.ent_s18
R_sig = t.sig_s16 - t.ent_s0930; R = t.ent_s16 - t.ent_s0930
Q_sig = t.sig_s17 - t.ent_s16; Q = t.sig_s17 - t.ent_s16
H1 = t.ent_s1030 - t.ent_s0930
M30 = t.ent_s10 - t.ent_s0930
r0830_45_sig = t.sig_s0845 - t.ent_s0830; r0845_0930 = t.ent_s0930 - t.ent_s0845
L_sig = t.sig_s0330 - t.ent_s03; L_after = t.ent_s0830 - t.ent_s0330
PL_sig = t.sig_s03 - t.ent_s02; L1 = t.ent_s04 - t.ent_s03
LH_sig = t.sig_s16 - t.ent_s15
ON_full = t.ent_s0930 - t.ent_s18
atr = t.atr20

tests = [
    ("B1_asia_to_eur", "Asia 18-02 -> Europa 02-08:30", A_sig, E),
    ("B1_asiaeur_to_pre", "18-08:30 -> 08:30-09:30", AE_sig, P),
    ("B1_eur_to_pre", "Europa 02-08:30 -> 08:30-09:30", E_sig, P),
    ("B1_on_to_rth", "notte 18-09:30 -> RTH 09:30-16:00", ON_sig, R),
    ("B1_asia_to_rth", "Asia 18-02 -> RTH", A_sig, R),
    ("B1_eur_to_rth", "Europa 02-08:30 -> RTH", E_sig, R),
    ("B1_pre_to_rth", "08:30-09:30 -> RTH", P_sig, R),
    ("B1_pre_to_h1", "08:30-09:30 -> 09:30-10:30", P_sig, H1),
    ("B1_on_to_m30", "notte 18-09:30 -> 09:30-10:00", ON_sig, M30),
    ("B1_0830react_to_0845_0930", "reazione 08:30-08:45 -> 08:45-09:30", r0830_45_sig, r0845_0930),
    ("B1_london30_to_rest", "Londra 03:00-03:30 -> 03:30-08:30", L_sig, L_after),
    ("B1_prelondon_to_london1h", "02:00-03:00 -> 03:00-04:00", PL_sig, L1),
    ("B1_rth_to_post", "RTH -> 16:00-17:00", R_sig, Q),
    ("B1_lasthour_to_post", "15:00-16:00 -> 16:00-17:00", LH_sig, Q),
    ("B1_post_to_nextasia", "16:00-17:00 -> Asia sessione successiva", Q_sig, nxt(A)),
    ("B1_rth_to_nextasia", "RTH -> Asia sessione successiva", R_sig, nxt(A)),
    ("B1_rth_to_nexton", "RTH -> notte successiva 18-09:30", R_sig, nxt(ON_full)),
    ("B1_rth_to_nextrth", "RTH -> RTH successiva", R_sig, nxt(R)),
    ("B1_post_to_nextrth", "16:00-17:00 -> RTH successiva", Q_sig, nxt(R)),
    ("B1_asia_to_pre", "Asia -> 08:30-09:30", A_sig, P),
]
for tid, desc, pred, tgt in tests:
    side = np.sign(pred)
    r = evaluate(tid, desc + " [continuazione, punti, tutte le sessioni]", side * tgt, side, tgt, atr, m)
    print(fmt(tid, r))
