"""Batteria 5: momentum intraday (Gao-Han-Li-Zhou 2018, con la notte dentro), weekend, Asia fine,
apertura della Cina, inversione della notte rispetto al giorno prima."""
import numpy as np, pandas as pd
from lab.cross_session.build_cache import get
from lab.cross_session.common import evaluate, fmt
from lab.cross_session.series import segments, causal_q

t = get(); S = segments(t); m = t["valid"] & t["in_phase"]; atr = t.atr20
prev_rth_close = t.ent_s16.shift(1)   # prezzo alle 16:00 della sessione precedente
def run(tid, desc, side, tgt):
    r = evaluate(tid, desc, side * tgt, side, tgt, atr, m); print(fmt(tid, r)); return r

last30 = t.ent_s16 - t.ent_s1530
# V19 Gao et al.: rendimento dalla chiusura RTH precedente alle 10:00 -> ultima mezz'ora 15:30-16:00
f30 = t.sig_s10 - prev_rth_close
run("V19_gao_prevclose_to10_to_last30", "sign(16:00 prec -> 10:00) su 15:30-16:00 (momentum intraday con notte)", np.sign(f30), last30)
run("V19b_on_to_last30", "sign(notte 18-09:30) su 15:30-16:00", np.sign(S["ON_sig"]), last30)
run("V19c_first30_to_last30", "sign(09:30-10:00) su 15:30-16:00", np.sign(t.sig_s10 - t.ent_s0930), last30)
f1530 = t.sig_s1530 - t.ent_s1530  # placeholder non usato
run("V19d_prevclose_to1530_to_last30", "sign(16:00 prec -> 15:30) su 15:30-16:00", np.sign(t.sig_s1530 - prev_rth_close), last30)
# V20 Europa -> ultima mezz'ora
run("V20_eur_to_last30", "sign(Europa 02-08:30) su 15:30-16:00", np.sign(S["E_sig"]), last30)
# V23 venerdi' RTH -> notte asiatica del lunedi' (weekend)
mon = t.dow == 0
run("V23_friRTH_to_monasia", "lunedi': sign(RTH del venerdi') su Asia del lunedi'", np.sign(S["R_sig"].shift(1)).where(mon), S["A"])
# V26 la notte rovescia il giorno prima: la RTH segue la notte?
rev = np.sign(S["ON_sig"]) != np.sign(S["R_sig"].shift(1))
run("V26_ON_reverses_prevday_to_rth", "notte di segno opposto alla RTH precedente: side sign(notte) su RTH", np.sign(S["ON_sig"]).where(rev), S["R"])
run("V26b_ON_confirms_prevday_to_rth", "notte stesso segno della RTH precedente: side sign(notte) su RTH", np.sign(S["ON_sig"]).where(~rev), S["R"])
# V18 fine Asia (00:00-02:00) -> Europa
run("V18_lateasia_to_eur", "sign(00:00-02:00) su 02:00-08:30", np.sign(t.sig_s02 - t.ent_s00), S["E"])
# V29 apertura della Cina (21:30 NY): 21:30-22:30 -> 22:30-02:00
run("V29_chinaopen_to_restasia", "sign(21:30-22:30) su 22:30-02:00", np.sign(t.sig_s2230 - t.ent_s2130), t.ent_s02 - t.ent_s2230)
# V30 prima ora Globex (18-19... uso 18-20) -> resto Asia
run("V30_firstglobex_to_restasia", "sign(18:00-20:00) su 20:00-02:00", np.sign(t.sig_s20 - t.ent_s18), t.ent_s02 - t.ent_s20)
# V31 tutta la notte fino alle 08:30 -> finestra 08:30-10:00 (dati macro + apertura)
run("V31_on0830_to_0830_1000", "sign(18:00-08:30) su 08:30-10:00", np.sign(S["AE_sig"]), t.ent_s10 - t.ent_s0830)
# V32 inversione della RTH precedente nella mattina europea (chi e' rimasto sbilanciato ribilancia a Londra?)
run("V32_prevrth_to_eur", "sign(RTH precedente) su Europa 02-08:30", np.sign(S["R_sig"].shift(1)), S["E"])
