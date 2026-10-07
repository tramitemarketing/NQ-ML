"""F9 - flussi forzati a frequenza giornaliera.
(a) ribilanciamento di fine mese (Harvey-Mazzoleni-Melone): per OGNI sessione fra le ultime K del mese,
    gross = -sign(rendimento del mese fino al close di ieri) x rendimento di oggi (close->close 16:00, adj, punti);
    scomposto in notte (16:00 ieri -> 09:30) e RTH (09:30 -> 16:00). Inversione nei primi 2 giorni del mese dopo.
    Griglia dichiarata K {2,3,5}.
(b) fondi a volatilita' obiettivo / risk parity: dopo uno shock di volatilita' (RV5/RV22 dei rendimenti giornalieri
    close->close sopra il quantile causale q), i fondi riducono l'esposizione il giorno dopo -> rendimento RTH di domani
    negativo? gross = -(RTH di domani) (short), confrontato con -(RTH) incondizionato (beta). q {0.5,0.7,0.9}."""
import numpy as np
import pandas as pd

from lab.r2_footprints import common as C
from lab.r2_footprints.f3b_magnitude import causal_q

pd.set_option("display.width", 250)

if __name__ == "__main__":
    D, daily = C.get()
    okv = D["valid"]
    c16 = D["Cf"][:, C.sm_of("15:59")]
    o930 = D["Of"][:, C.sm_of("09:30")]
    raw = D["rawCf"][:, C.sm_of("15:59")]
    df = pd.DataFrame({"c16": c16, "o930": o930, "raw": raw, "inp": D["in_phase"]}, index=D["sess"])[okv]
    df["prev"] = df.c16.shift(1)
    df["ret"] = df.c16 - df.prev
    df["night"] = df.o930 - df.prev
    df["rth"] = df.c16 - df.o930
    ym = df.index.to_period("M")
    df["rank_end"] = df.groupby(ym).cumcount(ascending=False)
    df["rank_start"] = df.groupby(ym).cumcount()
    mend = df.groupby(ym).c16.last()
    df["prev_mclose"] = ym.map(mend.shift(1)).to_numpy()
    df["mtd_prev"] = df.prev - df.prev_mclose            # mese fino al close di ieri
    lastm = ym.map(mend.shift(1) - mend.shift(2)).to_numpy()  # rendimento del mese scorso intero
    df["lastm"] = lastm
    res = []

    def rep(tid, desc, g, days, **kw):
        m = np.isfinite(g)
        t = pd.DataFrame({"session": np.asarray(days)[m], "gross_pts": np.asarray(g)[m]})
        st = C.full_report(tid, desc, t, net=False, **kw)
        res.append(dict(id=tid, n=st["n"], mean=st["mean"], lo=st["lo"], hi=st["hi"], p2=st["p_two"],
                        yrs=st["years_pos"], d20=st["drop20"]))
        return st

    d = df[df.inp]
    for K in [2, 3, 5]:
        s = d[(d.rank_end < K) & (d.rank_end >= 0) & (d.index.to_period("M") != d.index[0].to_period("M"))]
        side = -np.sign(s.mtd_prev)
        for part in ["ret", "night", "rth"]:
            rep(f"F9a_eom_K{K}_{part}", f"F9a ultime {K} sessioni del mese: -sign(mtd a ieri) x {part} di oggi, punti",
                (side * s[part]).to_numpy(), s.index)
        rep(f"F9a_eom_K{K}_ret_pct", f"F9a idem in % (rendimento/prezzo grezzo x100)", (side * s.ret / s.raw * 100).to_numpy(),
            s.index)
    s = d[d.rank_start < 2]
    rep("F9a_bom_2d_ret", "F9a prime 2 sessioni del mese: sign(rendimento del mese scorso) x rendimento di oggi, punti",
        (np.sign(s.lastm) * s.ret).to_numpy(), s.index)
    # (b) vol target
    rpct = df.ret / df.raw.shift(1) * 100
    rv5 = rpct.pow(2).rolling(5).mean() ** 0.5
    rv22 = rpct.pow(2).rolling(22).mean() ** 0.5
    ratio = (rv5 / rv22).to_numpy()
    nxt_rth = df.rth.shift(-1).to_numpy()
    nxt_night = df.night.shift(-1).to_numpy()
    nxt_sess = pd.Series(df.index, index=df.index).shift(-1).to_numpy()
    inp = df.inp.to_numpy()
    base_rth = -np.nanmean(nxt_rth[inp])
    for q in [0.5, 0.7, 0.9]:
        thr = causal_q(np.where(inp, ratio, np.nan), q)
        m = inp & np.isfinite(ratio) & (ratio > thr) & np.isfinite(nxt_rth)
        rep(f"F9b_voltarget_q{q}_rth", f"F9b shock di vol (RV5/RV22 > q causale {q}): short RTH di domani, lordo punti; "
            f"incondizionato {base_rth:.3f}", -nxt_rth[m], nxt_sess[m], uncond=base_rth)
        rep(f"F9b_voltarget_q{q}_night", f"F9b idem sulla notte di domani (16:00 -> 09:30)", -nxt_night[m], nxt_sess[m])
    print(pd.DataFrame(res).round(3).to_string())
