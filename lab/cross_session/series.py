"""Serie di segmento (stesse definizioni della batteria 1)."""
import numpy as np, pandas as pd

def segments(t):
    nxt = lambda s: s.shift(-1)
    S = {}
    S["A_sig"] = t.sig_s02 - t.ent_s18; S["A"] = t.ent_s02 - t.ent_s18
    S["E_sig"] = t.sig_s0830 - t.ent_s02; S["E"] = t.ent_s0830 - t.ent_s02
    S["AE_sig"] = t.sig_s0830 - t.ent_s18
    S["P_sig"] = t.sig_s0930 - t.ent_s0830; S["P"] = t.ent_s0930 - t.ent_s0830
    S["ON_sig"] = t.sig_s0930 - t.ent_s18; S["ON"] = t.ent_s0930 - t.ent_s18
    S["R_sig"] = t.sig_s16 - t.ent_s0930; S["R"] = t.ent_s16 - t.ent_s0930
    S["Q_sig"] = t.sig_s17 - t.ent_s16; S["Q"] = t.sig_s17 - t.ent_s16
    S["H1"] = t.ent_s1030 - t.ent_s0930; S["M30"] = t.ent_s10 - t.ent_s0930
    S["r0830_sig"] = t.sig_s0845 - t.ent_s0830; S["r0845_0930"] = t.ent_s0930 - t.ent_s0845
    S["L_sig"] = t.sig_s0330 - t.ent_s03; S["L_after"] = t.ent_s0830 - t.ent_s0330
    S["PL_sig"] = t.sig_s03 - t.ent_s02; S["L1"] = t.ent_s04 - t.ent_s03
    S["LH_sig"] = t.sig_s16 - t.ent_s15
    S["nA"] = nxt(S["A"]); S["nON"] = nxt(S["ON"]); S["nR"] = nxt(S["R"])
    return S

PAIRS = [
    ("asia_to_eur", "A_sig", "E"), ("asiaeur_to_pre", "AE_sig", "P"), ("eur_to_pre", "E_sig", "P"),
    ("on_to_rth", "ON_sig", "R"), ("asia_to_rth", "A_sig", "R"), ("eur_to_rth", "E_sig", "R"),
    ("pre_to_rth", "P_sig", "R"), ("pre_to_h1", "P_sig", "H1"), ("on_to_m30", "ON_sig", "M30"),
    ("0830react_to_0845_0930", "r0830_sig", "r0845_0930"), ("london30_to_rest", "L_sig", "L_after"),
    ("prelondon_to_london1h", "PL_sig", "L1"), ("rth_to_post", "R_sig", "Q"), ("lasthour_to_post", "LH_sig", "Q"),
    ("post_to_nextasia", "Q_sig", "nA"), ("rth_to_nextasia", "R_sig", "nA"), ("rth_to_nexton", "R_sig", "nON"),
    ("rth_to_nextrth", "R_sig", "nR"), ("post_to_nextrth", "Q_sig", "nR"), ("asia_to_pre", "A_sig", "P"),
]

def causal_q(x, q=0.67, win=250, minp=60):
    return x.shift(1).rolling(win, min_periods=minp).quantile(q)
