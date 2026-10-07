"""Approfondimento del grappolo 'weekend' (V5, V23, V6b): sensibilita' a predittore e uscita,
placebo sugli altri giorni, anno per anno. Tutto registrato."""
import numpy as np, pandas as pd
from lab import core
from lab.cross_session.build_cache import get
from lab.cross_session.common import evaluate, fmt
from lab.cross_session.series import segments

t = get(); S = segments(t); m = t["valid"] & t["in_phase"]; atr = t.atr20
mon = t.dow == 0
def run(tid, desc, side, tgt, show_year=False):
    r = evaluate(tid, desc, side * tgt, side, tgt, atr, m); print(fmt(tid, r))
    if show_year:
        g = (side * tgt)[m & side.notna() & tgt.notna() & (side != 0)]
        print(core.yearly(g.to_numpy() - 0.75, g.index).round(2).T.to_string())
    return r
friR = S["R_sig"].shift(1)
fri_close = t.sig_s17.shift(1); gap = t.ent_s18 - fri_close
fri_full = t.sig_s17.shift(1) - t.ent_s18.shift(1)
print("corr sign(friR), sign(gap) lunedi':", np.corrcoef(np.sign(friR[mon & m].fillna(0)), np.sign(gap[mon & m].fillna(0)))[0, 1].round(3))
print("corr gap/friR:", pd.concat([friR, gap], axis=1)[mon & m].corr().iloc[0, 1].round(3))
exits = {"20": t.ent_s20, "00": t.ent_s00, "02": t.ent_s02, "0830": t.ent_s0830, "0930": t.ent_s0930}
for k, x in exits.items():
    run(f"W1_friRTH_monasia_to{k}", f"lunedi': sign(RTH venerdi') da 18:00 a {k}", np.sign(friR).where(mon), x - t.ent_s18, show_year=(k == "02"))
run("W2_frifull_monasia_to02", "lunedi': sign(sessione intera venerdi' 18-17) da 18:00 a 02:00", np.sign(fri_full).where(mon), S["A"])
run("W3_friRTH_plus_gap_monasia", "lunedi': sign(RTH venerdi' + gap weekend) da 18:00 prima barra... uso ingresso 18:00 e segnale fino a Fri16", np.sign(friR).where(mon), S["A"])
# placebo: stessa regola nelle altre notti (mar-ven)
run("W4_placebo_prevRTH_asia_tuefri", "placebo: mar-ven, sign(RTH precedente) su Asia 18-02", np.sign(friR).where(~mon), S["A"])
# ingresso realistico dopo lo spread di apertura domenicale: 18:05 non disponibile -> uso 20:00->02:00
run("W5_friRTH_monasia_20to02", "lunedi': sign(RTH venerdi') da 20:00 a 02:00", np.sign(friR).where(mon), t.ent_s02 - t.ent_s20)
