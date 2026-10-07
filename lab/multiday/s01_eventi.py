"""Screening 1: ipotesi a evento (condizione nota alle 15:59 del giorno t -> posizione da P_t a P_{t+h}).
Metrica primaria (dichiarata prima): rendimento IN ECCESSO sulla deriva media (bp), side*(r_h - mu*h),
CI a blocchi mensili. Ogni riga stampata e' registrata nel ledger.
Griglia fissata prima di guardare: h in {1, 5}; soglie come scritte sotto (una o due per ipotesi)."""
import numpy as np
import pandas as pd

import lab.multiday.common as C
from lab.multiday.common import load_daily, event_test, rec

d, bars = load_daily()
mu = d["r"].mean()
V = d["valid"] & ~d["P_missing"]
c = d["rth_close"]; h_ = d["rth_high"]; l_ = d["rth_low"]; o_ = d["rth_open"]
rc = d["ret_cc_pct"]
sig20 = rc.rolling(20).std()
z = rc / sig20.shift(1)                                  # rendimento di oggi in sigma dei 20 giorni precedenti
atr = d["atr14"].shift(1)                                # ATR noto a ieri
move_atr = d["ret_cc"] / atr
dn = (d["ret_cc"] < 0).astype(int); up = (d["ret_cc"] > 0).astype(int)
def streak(x):
    g = (x != x.shift()).cumsum()
    return x.groupby(g).cumsum() * x
sdn, sup = streak(dn), streak(up)
rng = d["rng"]
nr7 = rng == rng.rolling(7).min()
inside = (h_ < h_.shift(1)) & (l_ > l_.shift(1))
clv = (c - l_) / rng.replace(0, np.nan)
r5 = (c - c.shift(5)) / d["Praw"].shift(5)       # % su raw (adj additivo: corretto in rev3)
r5q_lo = r5 < r5.expanding(250).quantile(0.2).shift(1)   # quintile espandente (niente look-ahead)
r5q_hi = r5 > r5.expanding(250).quantile(0.8).shift(1)
ma50 = c.rolling(50).mean(); dist50 = (c - ma50) / atr
ma200 = c.rolling(200).mean()
hi252 = c.rolling(252).max()
dd252 = (c - hi252) / d["Praw"]                          # drawdown in % (raw)
newhi = c >= hi252
gap = (o_ - c.shift(1)) / atr
volr = d["rth_volume"] / d["rth_volume"].rolling(20).mean().shift(1)
diff = c.diff()
g_ = diff.clip(lower=0).ewm(alpha=1/2, adjust=False).mean(); l2 = (-diff.clip(upper=0)).ewm(alpha=1/2, adjust=False).mean()
rsi2 = 100 - 100 / (1 + g_ / l2)
outside_bear = (h_ > h_.shift(1)) & (l_ < l_.shift(1)) & (clv < 0.25)
outside_bull = (h_ > h_.shift(1)) & (l_ < l_.shift(1)) & (clv > 0.75)
s5 = rc.rolling(5).std(); s60 = rc.rolling(60).std()
volspike = s5 / s60 > 1.75

tests = [
  # id, descrizione, maschera, side
  ("H01a_z<-2_long", "rendimento di oggi < -2 sigma20 -> long (reversal)", z < -2, +1),
  ("H01b_z<-1.5_long", "rendimento di oggi < -1.5 sigma20 -> long", z < -1.5, +1),
  ("H01c_z>2_short", "rendimento di oggi > +2 sigma20 -> short (reversal)", z > 2, -1),
  ("H01d_z>1.5_short", "rendimento di oggi > +1.5 sigma20 -> short", z > 1.5, -1),
  ("H02a_atr<-1.5_long", "close-to-close < -1.5 ATR14 -> long", move_atr < -1.5, +1),
  ("H02b_atr>1.5_short", "close-to-close > +1.5 ATR14 -> short", move_atr > 1.5, -1),
  ("H03a_3dn_long", ">=3 chiusure consecutive in calo -> long", sdn >= 3, +1),
  ("H03b_4dn_long", ">=4 chiusure consecutive in calo -> long", sdn >= 4, +1),
  ("H03c_3up_short", ">=3 chiusure consecutive in rialzo -> short", sup >= 3, -1),
  ("H03d_4up_short", ">=4 chiusure consecutive in rialzo -> short", sup >= 4, -1),
  ("H06a_nr7_long", "NR7 (range minimo di 7) -> long (direzione, controllo)", nr7, +1),
  ("H06b_inside_long", "inside day -> long (direzione, controllo)", inside, +1),
  ("H07a_clv>0.9_long", "chiusura nel 10% alto del range -> long (continuazione)", clv > 0.9, +1),
  ("H07b_clv<0.1_long", "chiusura nel 10% basso del range -> long (reversal IBS)", clv < 0.1, +1),
  ("H07c_clv>0.9_short", "chiusura nel 10% alto del range -> short (reversal IBS)", clv > 0.9, -1),
  ("H08a_w_lo_long", "rendimento 5 giorni nel quintile basso -> long (reversal settimanale)", r5q_lo, +1),
  ("H08b_w_hi_short", "rendimento 5 giorni nel quintile alto -> short", r5q_hi, -1),
  ("H09a_ma50<-3atr_long", "close sotto MA50 di oltre 3 ATR -> long", dist50 < -3, +1),
  ("H09b_ma50>3atr_short", "close sopra MA50 di oltre 3 ATR -> short", dist50 > 3, -1),
  ("H10a_dd>10_long", "drawdown dal massimo a 252g > 10% -> long", dd252 < -0.10, +1),
  ("H10b_dd>5_long", "drawdown dal massimo a 252g > 5% -> long", dd252 < -0.05, +1),
  ("H11a_gapdn_long", "gap RTH < -1 ATR, a fine giornata -> long", gap < -1, +1),
  ("H11b_gapup_short", "gap RTH > +1 ATR, a fine giornata -> short", gap > 1, -1),
  ("H12a_newhi_long", "chiusura su nuovo massimo 252g -> long (momentum 52w)", newhi, +1),
  ("H14a_rsi2<10_ma200_long", "RSI(2)<10 e close>MA200 -> long (Connors)", (rsi2 < 10) & (c > ma200), +1),
  ("H14b_rsi2<10_long", "RSI(2)<10 -> long", rsi2 < 10, +1),
  ("H14c_rsi2>90_short", "RSI(2)>90 -> short", rsi2 > 90, -1),
  ("H15a_volspike_long", "sigma5/sigma60 > 1.75 -> long (premio di paura)", volspike, +1),
  ("H17a_vol2x_dn_long", "volume RTH > 2x media20 e giorno in calo -> long", (volr > 2) & (d["ret_cc"] < 0), +1),
  ("H17b_vol2x_up_short", "volume RTH > 2x media20 e giorno in rialzo -> short", (volr > 2) & (d["ret_cc"] > 0), -1),
  ("H18a_outside_bear_long", "outside day chiuso nel quarto basso -> long", outside_bear, +1),
  ("H18b_outside_bull_short", "outside day chiuso nel quarto alto -> short", outside_bull, -1),
]

ONLY = {"H08a_w_lo_long", "H08b_w_hi_short"}   # rev3: rieseguo solo i test toccati dal bug del % su adj
C.REV = 3
rows = []
for tid, desc, m, side in [t for t in tests if t[0] in ONLY]:
    for h in (1, 5):
        st = event_test(d, m, h, side, mu, valid=V)
        rec(f"{tid}_h{h}", f"{desc}; tenuta {h} giorni (P 16:00 -> P 16:00)", st)
        rows.append(dict(id=f"{tid}_h{h}", **{k: st[k] for k in ("n", "mean_raw_bp", "mean", "lo", "hi", "p_two", "years_pos_exc", "mean_pts")}))
out = pd.DataFrame(rows).set_index("id")
pd.set_option("display.width", 200)
print(f"mu = {mu*1e4:.2f} bp/giorno")
print(out.round(2).to_string())
