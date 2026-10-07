"""Ultime ipotesi e stabilita':
 H36 dollaro 60g -> NQ 20g; H37 spread 10a-3m (livello) -> NQ 20g e sua variazione 40g;
 H38 stabilita' di IC(d40_10y -> NQ 20g) nelle due meta' del discovery (2010-14, 2015-18);
 H39 settimana dopo i giorni di grande movimento del dollaro (|r1|>2 sd250) -> NQ 5g firmato -segno."""
import numpy as np
import pandas as pd
from lab import core
from lab.r4_macro import common as C

if __name__ == "__main__":
    d, bars, daily = C.load()
    kk = C.ext_known(d.index)
    d = d[d["O"].notna()].copy()
    y20, _ = C.fwd(d, 20); y5, _ = C.fwd(d, 5)
    def show(tid, desc, st):
        core.record(C.FAM, tid, desc, "discovery", st)
        print(tid, {k: (round(v, 4) if isinstance(v, float) else v) for k, v in st.items() if k != "years"})
    show("H36_usd60_f20", "IC dollaro 60g -> NQ 20g", C.ic_test(d["r60_USD"], y20))
    sp = (kk["DGS10"] - kk["DGS3MO"])
    show("H37a_spread10y3m_f20", "IC spread 10a-3m (livello) -> NQ 20g", C.ic_test(sp.reindex(d.index), y20))
    show("H37b_dspread40_f20", "IC variazione 40g spread 10a-3m -> NQ 20g", C.ic_test((sp - sp.shift(40)).reindex(d.index), y20))
    k = kk["DGS10"]; d40 = (k - k.shift(40)).reindex(d.index)
    for a, b in (("2010", "2014"), ("2015", "2018")):
        show(f"H38_d40_{a}_{b}", f"IC d40_10y -> NQ 20g solo {a}-{b}", C.ic_test(d40.loc[a:b], y20.loc[a:b]))
    u = np.log(kk["USD"]).diff(); big = (u.abs() > 2 * u.rolling(250).std()).reindex(d.index)
    sg = -np.sign(u.reindex(d.index))
    st = core.day_block_bootstrap((sg * y5)[big].dropna().to_numpy(), C.month_key((sg * y5)[big].dropna().index))
    show("H39_usd_shock_f5", "giorni |r1 dollaro|>2sd250 -> NQ 5g firmato -segno(dollaro)", dict(**st, n_events=int(big.sum())))
