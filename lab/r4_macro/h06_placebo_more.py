"""(a) Placebo a spostamento circolare: il segnale d40_10y viene spostato di k sessioni (k = 120..2060, passo 20,
    esclusi |k|<120) rispetto ai rendimenti NQ: stessa persistenza, nessun legame temporale. Distribuzione nulla
    di IC(d40->f20) e dell'EV netto di T1 (long/short a run). Misura quanto e' 'raro' il valore reale.
(b) H28: d40 in VIX basso/alto (VIX solo come controllo, mediana del discovery... mediana ESPANDING per non usare il futuro).
(c) H31: accordo segno momentum tassi 40g e momentum NQ 40g -> NQ 20g.
(d) H32: d40 standardizzato per la vol dei tassi a 250g -> NQ 20g.
(e) H33: variante con la pendenza (d40_T10Y2Y) gia' vista: correlazione con d40_10y."""
import numpy as np
import pandas as pd
from lab import core
from lab.r4_macro import common as C
from lab.r4_macro.h05_trade_d40 import runs

if __name__ == "__main__":
    d, bars, daily = C.load()
    kk = C.ext_known(d.index)
    k = kk["DGS10"]
    d["d40"] = (k - k.shift(40)).reindex(d.index)
    d["d40_slope"] = (kk["T10Y2Y"] - kk["T10Y2Y"].shift(40)).reindex(d.index)
    d = d[d["O"].notna()].copy()
    y20, _ = C.fwd(d, 20)
    real_ic = C.ic_test(d["d40"], y20, n_boot=500)["ic"]
    real_t1 = runs(d, -np.sign(d["d40"]).fillna(0.0))["gross_pts"].sub(core.COST_RT_POINTS).mean()
    sig = d["d40"].to_numpy()
    ics, evs = [], []
    n = len(d)
    for sh in range(120, n - 120, 20):
        ps = pd.Series(np.roll(sig, sh), index=d.index)
        m = pd.concat([ps, y20], axis=1).dropna()
        ics.append(m.corr(method="spearman").iloc[0, 1])
        evs.append(runs(d, -np.sign(ps).fillna(0.0))["gross_pts"].sub(core.COST_RT_POINTS).mean())
    ics, evs = np.array(ics), np.array(evs)
    out = dict(n_placebo=len(ics), real_ic=real_ic, frac_ic_le_real=float((ics <= real_ic).mean()),
               placebo_ic_mean=float(ics.mean()), placebo_ic_sd=float(ics.std()), real_t1=float(real_t1),
               frac_ev_ge_real=float((evs >= real_t1).mean()), placebo_ev_mean=float(evs.mean()), placebo_ev_sd=float(evs.std()))
    core.record(C.FAM, "P1_circshift_d40", "placebo a spostamento circolare del segnale d40_10y (IC f20 ed EV T1)", "discovery", out)
    print(out)
    # (b) VIX
    vmed = d["VIX"].expanding(250).median().shift(1)
    for lab_, msk in (("lowvix", d["VIX"] <= vmed), ("highvix", d["VIX"] > vmed)):
        st = C.ic_test(d["d40"].where(msk), y20, n_boot=2000)
        core.record(C.FAM, f"H28_d40_{lab_}", f"IC d40_10y->NQ20g con {lab_} (mediana espanding del VIX)", "discovery", st)
        print(lab_, round(st["ic"], 3), round(st["lo"], 3), round(st["hi"], 3), st["p_two"], st["years_pos"])
    # (c) accordo
    cc = d["rth_close"]; mom40 = (cc.shift(1) - cc.shift(41))
    agree = np.sign(mom40) == np.sign(d["d40"])
    st = C.cond_mean(y20, agree)
    core.record(C.FAM, "H31_agree_mom", "momentum tassi 40g e NQ 40g concordi -> NQ 20g (diff vs discordi)", "discovery", st)
    print("H31", {k2: (round(v, 4) if isinstance(v, float) else v) for k2, v in st.items()})
    # (d) standardizzato
    sd = (k - k.shift(1)).rolling(250).std().reindex(d.index)
    st = C.ic_test(d["d40"] / (sd * np.sqrt(40)), y20, n_boot=2000)
    core.record(C.FAM, "H32_d40_std_f20", "IC d40_10y / (sd250 d1 x sqrt40) -> NQ 20g", "discovery", st)
    print("H32", round(st["ic"], 3), st["p_two"], st["years_pos"])
    print("corr d40_10y vs d40_slope:", round(d[["d40", "d40_slope"]].corr().iloc[0, 1], 3))
