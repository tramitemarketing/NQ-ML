"""Batteria 3: condizioni di range, posizione, calendario, volume (tabella per sessione)."""
import numpy as np, pandas as pd
from lab import core
from lab.cross_session.build_cache import get
from lab.cross_session.common import evaluate, fmt, FAMILY
from lab.cross_session.series import segments, causal_q

t = get(); S = segments(t); m = t["valid"] & t["in_phase"]; atr = t.atr20
on_rng = t.on_hi - t.on_lo
on_ratio = on_rng / on_rng.shift(1).rolling(20, min_periods=10).mean()
rth_ratio = t.range_rth / t.atr20_rth

def run(tid, desc, side, tgt):
    r = evaluate(tid, desc, side * tgt, side, tgt, atr, m); print(fmt(tid, r)); return r

# V1 regolarita': range notturno (rispetto alla sua media 20) predice il range RTH (rispetto alla sua)
sgn = np.sign(on_ratio - on_ratio.shift(1).rolling(250, min_periods=60).median())
x = (sgn * (rth_ratio - 1)).where(m)
st = core.day_block_bootstrap(x.dropna().to_numpy(), x.dropna().index.to_numpy())
c = pd.concat([np.log(on_ratio), np.log(rth_ratio)], axis=1)[m].dropna().corr(method="spearman").iloc[0, 1]
yr = core.yearly(x.dropna().to_numpy(), x.dropna().index)
core.record(FAMILY, "V1_onrange_predicts_rthrange", "regolarita': sign(on_ratio - mediana causale) * (range RTH/ATR20rth - 1)",
            "discovery", st, spearman=float(c), years_pos=f"{(yr['mean']>0).sum()}/{len(yr)}")
print("V1", st, "spearman", round(c, 3), "anni", (yr['mean'] > 0).sum())

# V2 notte ampia -> RTH continua la direzione della notte
big = on_ratio > causal_q(on_ratio)
run("V2_wideON_dir_to_rth", "notte ampia (on_ratio>q67 causale): side sign(18-09:30) su RTH", np.sign(S["ON_sig"]).where(big), S["R"])
small = on_ratio < causal_q(on_ratio, 0.33)
run("V2b_narrowON_dir_to_rth", "notte stretta (on_ratio<q33 causale): side sign(notte) su RTH", np.sign(S["ON_sig"]).where(small), S["R"])

# V3 posizione dell'apertura RTH nel range notturno
pos = (t.sig_s0930 - t.on_lo) / on_rng
side3 = pd.Series(np.where(pos > 0.8, 1.0, np.where(pos < 0.2, -1.0, np.nan)), index=t.index)
run("V3_openpos_extreme_to_rth", "apertura RTH nel 20% alto (long) / basso (short) del range notturno -> RTH", side3, S["R"])
run("V3_openpos_extreme_to_h1", "idem -> 09:30-10:30", side3, S["H1"])

# V5 gap del weekend (ven 16:59 -> dom 18:00): continuazione nella notte asiatica del lunedi'
fri_close = t.sig_s17.shift(1)
gap = t.ent_s18 - fri_close
mon = t.dow == 0
run("V5_weekendgap_cont_asia", "lunedi': side sign(gap weekend) su Asia 18-02", np.sign(gap).where(mon & (gap.abs() > 0)), S["A"])
run("V5b_weekendgap_cont_rth", "lunedi': side sign(gap weekend) su RTH", np.sign(gap).where(mon & (gap.abs() > 0)), S["R"])
# V6 notte del lunedi' (Asia) -> RTH del lunedi'
run("V6_monday_asia_to_rth", "lunedi': side sign(Asia) su RTH", np.sign(S["A_sig"]).where(mon), S["R"])
run("V6b_monday_on_to_rth", "lunedi': side sign(notte 18-09:30) su RTH", np.sign(S["ON_sig"]).where(mon), S["R"])
# V7 Asia ed Europa concordi -> RTH
agree = np.sign(S["A_sig"]) == np.sign(S["E_sig"])
run("V7_asia_eur_agree_to_rth", "Asia e Europa stesso segno: side quel segno su RTH", np.sign(S["A_sig"]).where(agree), S["R"])
run("V7b_asia_eur_disagree_eur_to_rth", "Asia/Europa discordi: side sign(Europa) su RTH", np.sign(S["E_sig"]).where(~agree), S["R"])
# V10 chiusura RTH vicino agli estremi -> Asia successiva
cpos = (t.sig_s16 - t.rth_lo) / t.range_rth
side10 = pd.Series(np.where(cpos > 0.85, 1.0, np.where(cpos < 0.15, -1.0, np.nan)), index=t.index)
run("V10_rthclose_extreme_to_nextasia", "chiusura RTH nel 15% alto/basso del range: side su Asia successiva", side10, S["nA"])
run("V10b_rthclose_extreme_to_post", "idem su 16:00-17:00", side10, S["Q"])
# V11 stagione degli utili (mesi 1,4,7,10 dal giorno 15 al 15 del mese successivo circa): dopo-chiusura -> notte
mo = t.index.month; dd = t.index.day
earn = ((np.isin(mo, [1, 4, 7, 10]) & (dd >= 15)) | (np.isin(mo, [2, 5, 8, 11]) & (dd <= 10)))
earn = pd.Series(earn, index=t.index)
zq = (S["Q_sig"] / atr).abs()
bigq = zq > causal_q(zq)
run("V11_earnings_post_to_nextasia", "stagione utili: side sign(16-17) su Asia successiva", np.sign(S["Q_sig"]).where(earn), S["nA"])
run("V11b_earnings_bigpost_to_nextasia", "stagione utili e |16-17| > q67 causale: side su Asia successiva", np.sign(S["Q_sig"]).where(earn & bigq), S["nA"])
run("V11c_earnings_bigpost_to_nextrth", "stagione utili e |16-17| grande: side su RTH successiva", np.sign(S["Q_sig"]).where(earn & bigq), S["nR"])
# V13 venerdi' del lavoro (primo venerdi' del mese, approssimato): reazione 08:30-08:45 -> 08:45-09:30 e -> 09:30-10:30
nfp = pd.Series((t.dow == 4) & (dd <= 7), index=t.index)
run("V13_nfp_react_to_0845_0930", "primo venerdi': side sign(08:30-08:45) su 08:45-09:30", np.sign(S["r0830_sig"]).where(nfp), S["r0845_0930"])
run("V13b_nfp_react_to_h1", "primo venerdi': side sign(08:30-08:45) su 09:30-10:30", np.sign(S["r0830_sig"]).where(nfp), S["H1"])
# V17 volume notturno alto -> la direzione della notte e' piu' informativa per RTH
onv = t.on_vol / t.on_vol.shift(1).rolling(20, min_periods=10).mean()
hv = onv > causal_q(onv)
run("V17_highvolON_dir_to_rth", "volume notturno > q67 causale: side sign(notte) su RTH", np.sign(S["ON_sig"]).where(hv), S["R"])
run("V17b_highvolON_dir_to_h1", "volume notturno alto: side sign(notte) su 09:30-10:30", np.sign(S["ON_sig"]).where(hv), S["H1"])
