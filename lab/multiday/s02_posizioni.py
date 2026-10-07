"""Screening 2: strategie a posizione continua (TSMOM, gestione della volatilita', filtro MA200,
turn-of-month) e regolarita' (autocorrelazione / variance ratio, espansione del range dopo NR7/inside).
Posizione decisa con info fino alle 15:59 di t, tenuta da P_t a P_{t+1}; costi 0,75 punti a/r sul
cambio di posizione. Confronto dichiarato prima: Sharpe della strategia vs buy-and-hold (differenza con CI
a blocchi mobili di 21 giorni) e EV in eccesso = pos*(r - mu) con CI a blocchi mensili."""
import numpy as np
import pandas as pd

from lab import core
from lab.multiday.common import load_daily, position_eval, sharpe_diff_boot, boot, years_pos, rec, sharpe

d, bars = load_daily()
mu = d["r"].mean()
r = d["r"]
c = d["rth_close"]
rows = []
bh = position_eval(d, pd.Series(1.0, index=d.index), mu)
START = d.index[260]           # stesso periodo di confronto per tutti (dopo il lookback piu' lungo)


def evaluate(tid, desc, pos):
    pe = position_eval(d, pos, mu)
    pe = pe[pe.index >= START]
    b = bh.loc[pe.index]
    sd = sharpe_diff_boot(pe["pnl"], b["pnl"])
    st = boot(pe["exc"].to_numpy() * 1e4, pe.index)
    yr = pd.DataFrame({"s": pe["pnl"], "b": b["pnl"]}).groupby(pe.index.year).apply(lambda g: sharpe(g["s"]) - sharpe(g["b"]))
    out = dict(st, unit="bp/giorno eccesso pos*(r-mu)", sr=sd["sr_a"], sr_bh=sd["sr_b"], dsr=sd["diff"], dsr_lo=sd["lo"],
               dsr_hi=sd["hi"], dsr_p_pos=sd["p_pos"], mean_pos=float(pe["pos"].mean()), years_dsr_pos=f"{int((yr>0).sum())}/{len(yr)}",
               years_exc_pos=years_pos(pe["exc"], pe.index), pts_net_per_day=float(pe["pts"].mean()),
               turnover=float(pe["pos"].diff().abs().mean()))
    rec(tid, desc, out)
    rows.append(dict(id=tid, **{k: out[k] for k in ("mean", "lo", "hi", "sr", "sr_bh", "dsr", "dsr_lo", "dsr_hi", "mean_pos", "years_dsr_pos", "years_exc_pos", "turnover")}))


# --- H04 TSMOM (Moskowitz-Ooi-Pedersen): segno del rendimento passato su L settimane, ribilancio giornaliero
for L in (1, 2, 4, 8, 12):
    past = c / c.shift(5 * L) - 1
    evaluate(f"H04_tsmom_{L}w_ls", f"TSMOM long/short: segno rendimento {L} settimane", np.sign(past))
    evaluate(f"H04_tsmom_{L}w_lf", f"TSMOM long/flat: long se rendimento {L} settimane > 0", (past > 0).astype(float))
# --- H05 Moreira-Muir: esposizione long = k / varianza realizzata (21 giorni), k tale che media esposizione ~1
#     (k fissato sulla media ESPANDENTE, niente look-ahead), tetto a 2x
for win, cap in ((21, 2.0), (21, 3.0), (63, 2.0)):
    var = r.rolling(win).var()
    raw = 1 / var
    w = (raw / raw.expanding(60).mean().shift(1)).clip(upper=cap)
    evaluate(f"H05_mm_var{win}_cap{cap}", f"Moreira-Muir: long x 1/varianza {win}g normalizzata (media espandente), tetto {cap}x", w)
    sd = r.rolling(win).std(); raw2 = 1 / sd
    w2 = (raw2 / raw2.expanding(60).mean().shift(1)).clip(upper=cap)
    evaluate(f"H05_vt_sd{win}_cap{cap}", f"Volatility targeting: long x 1/sigma {win}g normalizzata, tetto {cap}x", w2)
# --- H19 filtro di trend Faber: long se close > MA200 (o MA100), altrimenti flat
for n in (100, 200):
    evaluate(f"H19_ma{n}_lf", f"long se close > MA{n}, flat altrimenti", (c > c.rolling(n).mean()).astype(float))
# --- H20 turn-of-month: long dall'ultima sessione del mese (-1) alla terza del mese successivo
idx = d.index
mon = pd.Series(idx.year * 12 + idx.month, index=idx)
rank_fwd = mon.groupby(mon).cumcount()                         # 0 = prima sessione del mese
rank_bwd = mon.groupby(mon).cumcount(ascending=False)          # 0 = ultima sessione del mese
# posizione tenuta da P_t a P_{t+1}: long se t e' la penultima o ultima o fra le prime 3 (t+1 in [ultimo, +3])
tom = ((rank_bwd <= 1) | (rank_fwd <= 2)).astype(float)
evaluate("H20_tom_lf", "turn-of-month: long da P della penultima sessione a P della terza del mese", tom)

out = pd.DataFrame(rows).set_index("id")
pd.set_option("display.width", 220)
print(out.round(3).to_string())

# --- H16 regolarita': autocorrelazione dei rendimenti giornalieri e variance ratio
rr = r.dropna()
for lag in (1, 2, 5):
    x = rr.to_numpy(); prod = (x[lag:] - x.mean()) * (x[:-lag] - x.mean()) / x.var()
    st = boot(prod, rr.index[lag:])
    rec(f"H16_autocorr_lag{lag}", f"autocorrelazione rendimenti giornalieri a lag {lag} (regolarita')", st)
    print(f"autocorr lag {lag}: {st['mean']:.3f} [{st['lo']:.3f}, {st['hi']:.3f}] p={st['p_two']:.3f}")
for q in (5, 10, 20):
    rq = rr.rolling(q).sum().iloc[q - 1::q]
    vr = rq.var() / (q * rr.var())
    # bootstrap a blocchi mensili del VR
    mk = rr.index.year * 100 + rr.index.month
    groups = [g.to_numpy() for _, g in rr.groupby(mk)]
    rng = np.random.default_rng(0); vrs = []
    for _ in range(2000):
        s = np.concatenate([groups[i] for i in rng.integers(0, len(groups), len(groups))])
        sq = pd.Series(s).rolling(q).sum().iloc[q - 1::q]
        vrs.append(sq.var() / (q * s.var()))
    lo, hi = np.percentile(vrs, [2.5, 97.5])
    rec(f"H16_vr_q{q}", f"variance ratio VR({q}) dei rendimenti giornalieri (regolarita')", dict(n=len(rr), mean=float(vr), lo=float(lo), hi=float(hi)))
    print(f"VR({q}) = {vr:.3f} [{lo:.3f}, {hi:.3f}]")

# --- H06 regolarita': range del giorno dopo in unita' di ATR, dopo NR7 / inside day vs gli altri giorni
rng_ = d["rng"]; atr = d["atr14"]
nxt = (rng_.shift(-1) / atr)
V = d["valid"] & d["valid"].shift(-1, fill_value=False)
base = nxt[V].mean()
nr7 = rng_ == rng_.rolling(7).min()
inside = (d["rth_high"] < d["rth_high"].shift(1)) & (d["rth_low"] > d["rth_low"].shift(1))
for nm, m in (("nr7", nr7), ("inside", inside)):
    mm = m & V & nxt.notna()
    st = boot((nxt[mm] - base).to_numpy(), d.index[mm])
    # contro il ragionamento naturale: un range piccolo abbassa l'ATR -> confronto anche con il range di oggi
    ratio_today = (rng_[mm] / atr[mm]).mean()
    rec(f"H06_{nm}_range_next", f"{nm}: range RTH del giorno dopo / ATR14 meno la media incondizionata (regolarita')", st,
        base=float(base), ratio_today=float(ratio_today))
    print(f"{nm}: range dopo/ATR - base = {st['mean']:.3f} [{st['lo']:.3f}, {st['hi']:.3f}] (base {base:.3f}, oggi {ratio_today:.3f}) n={st['n']}")
