"""F5 - giorni di obbligo: fine mese / fine trimestre (ribilanciamento dei fondi bilanciati e pensione:
Harvey-Mazzoleni-Melone 2022, quando le azioni hanno fatto meglio nel mese i fondi VENDONO azioni negli ultimi
giorni), opex (terzo venerdi') e quadruple witching.
Unita': punti lordi (regolarita') e netti (tradeable), rendimenti che attraversano la notte da adj."""
import numpy as np
import pandas as pd

from lab.r2_footprints import common as C

pd.set_option("display.width", 250)

if __name__ == "__main__":
    D, daily = C.get()
    ok = D["valid"] & D["in_phase"]
    sess = D["sess"]
    P = lambda t: D["Cf"][:, C.sm_of(t)]
    c16 = P("15:59")
    o930 = D["Of"][:, C.sm_of("09:30")]
    df = pd.DataFrame({"s": sess, "ok": ok, "c16": c16, "o930": o930, "raw": D["rawCf"][:, C.sm_of("15:59")]})
    df = df[df.ok].reset_index(drop=True)
    ym = df.s.dt.to_period("M")
    df["last"] = ym != ym.shift(-1)                   # ultima sessione valida del mese
    df["rank_from_end"] = df.groupby(ym).cumcount(ascending=False)   # 0 = ultimo giorno
    df["rank_from_start"] = df.groupby(ym).cumcount()
    # close del mese precedente
    mclose = df.groupby(ym)["c16"].last().shift(1)
    df["prev_mclose"] = ym.map(mclose).to_numpy()
    res = []

    def rep(tid, desc, g, days, net=False):
        t = pd.DataFrame({"session": days, "gross_pts": g})
        st = C.full_report(tid, desc, t, net=net)
        res.append(dict(id=tid, n=st["n"], mean=st["mean"], lo=st["lo"], hi=st["hi"], p2=st["p_two"],
                        ppos=st["p_pos"], yrs=st["years_pos"], d20=st["drop20"]))

    # A) rendimento del mese fino a k giorni dalla fine -> rendimento degli ultimi k giorni (close->close)
    for k in [1, 2, 3, 5]:
        a = df[df.rank_from_end == k].set_index(df[df.rank_from_end == k].s.dt.to_period("M"))
        e = df[df["last"]].set_index(df[df["last"]].s.dt.to_period("M"))
        j = a.join(e[["c16", "s"]], rsuffix="_end").dropna()
        mtd = j.c16 - j.prev_mclose
        fut = j.c16_end - j.c16
        g = -np.sign(mtd) * fut
        rep(f"F5_rebal_mtd_last{k}d", f"F5 fine mese: -sign(rendimento del mese fino al close di {k} sedute dalla fine) x "
            f"(close ultimo giorno - close di {k} sedute prima), lordo punti", g.to_numpy(), j.s_end.to_numpy())
        # solo trimestri
        qm = j.index.month.isin([3, 6, 9, 12])
        rep(f"F5_rebal_mtd_last{k}d_qtr", f"F5 fine trimestre (idem, solo mar/giu/set/dic)", g[qm].to_numpy(),
            j.s_end[qm].to_numpy())
    # B) inversione a inizio mese successivo: sign(mtd del mese scorso) x rendimento primi 2 giorni
    f = df[df.rank_from_start == 1].copy()                  # close del 2o giorno
    f0 = df.groupby(ym)["o930"].first()
    j = f.set_index(f.s.dt.to_period("M"))
    mtd_prev = (j.prev_mclose - j.index.map(lambda p: df.loc[ym == p - 1, "c16"].iloc[0] if (ym == p - 1).any() else np.nan))
    g = np.sign(mtd_prev) * (j.c16 - j.prev_mclose)
    m = np.isfinite(g)
    rep("F5_rebal_nextmonth_2d", "F5 inizio mese: sign(rendimento del mese scorso) x (close 2o giorno - close fine mese)",
        g[m].to_numpy(), j.s[m].to_numpy())
    # C) intraday ultimo giorno del mese: -sign(mtd) x (16:00 - 15:45), e x (16:00 - 14:00)
    e = df[df["last"]].copy()
    rows = np.searchsorted(sess, e.s)
    mtd = e.c16.to_numpy() - e.prev_mclose.to_numpy()      # include il giorno: uso 15:44 per causalita'
    for a in ["14:00", "15:00", "15:45", "15:50"]:
        pa = D["Cf"][rows, C.sm_of(a) - 1]
        mtd_a = pa - e.prev_mclose.to_numpy()
        g = -np.sign(mtd_a) * (D["Cf"][rows, C.sm_of("15:59")] - pa)
        m = np.isfinite(g)
        rep(f"F5_eom_intraday_{a}", f"F5 ultimo giorno del mese: -sign(mtd fino alle {a}) x (16:00 - {a}), lordo",
            g[m], e.s.to_numpy()[m])
    print(pd.DataFrame(res).round(3).to_string())

    # D) opex: volatilita' realizzata RTH e autocorrelazione 5m il terzo venerdi' vs altri venerdi'
    a, b = C.sm_of("09:30"), C.sm_of("16:00")
    C5 = D["Cf"][:, a:b:5]
    r5 = np.diff(C5, axis=1) / D["rawCf"][:, a:a + 1] * 1e4
    rv = np.log(np.nansum(r5 ** 2, axis=1))
    ac = np.array([np.corrcoef(x[:-1], x[1:])[0, 1] if np.isfinite(x).all() else np.nan for x in r5])
    s = pd.DatetimeIndex(sess)
    fri = (s.dayofweek == 4) & ok
    third = fri & (s.day >= 15) & (s.day <= 21)
    quad = third & s.month.isin([3, 6, 9, 12])
    rvs = pd.Series(rv).rolling(20, min_periods=10).mean().shift(1).to_numpy()   # livello causale
    for nm, grp in (("opex", third & ~quad), ("quad", quad)):
        other = fri & ~third
        v = (rv - rvs)[grp]
        st = C.rec(f"F5_{nm}_logrv_vs_fri", f"F5 {nm}: log RV RTH 5m - media log RV 20 sessioni prec., meno lo stesso "
                   f"negli altri venerdi' ({np.nanmean((rv - rvs)[other]):.3f})",
                   v - np.nanmean((rv - rvs)[other]), sess[grp], unit="log")
        st2 = C.rec(f"F5_{nm}_ac5m_vs_fri", f"F5 {nm}: autocorrelazione dei rendimenti 5m RTH meno gli altri venerdi' "
                    f"({np.nanmean(ac[other]):.3f}) (gamma dei dealer -> rientro)", ac[grp] - np.nanmean(ac[other]),
                    sess[grp], unit="corr")
        print(nm, "logRV", round(st["mean"], 3), (round(st["lo"], 3), round(st["hi"], 3)), "AC5m", round(st2["mean"], 3),
              (round(st2["lo"], 3), round(st2["hi"], 3)), "n", st["n"])
