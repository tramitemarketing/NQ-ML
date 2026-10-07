"""PLACEBO: calibrazione del caso per l'intero laboratorio.

Regole che per costruzione non hanno senso economico (cifre della data, numeri primi, hash, fasi
lunari, semi fissi) ma con la STESSA struttura dei test veri: 1-3 trade al giorno in RTH, orizzonti
15 / 60 minuti / fino alla chiusura, costi 0,75 punti, bootstrap a blocchi per giorno (10.000, seme 0),
e i 4 criteri del PROTOCOLLO applicati al discovery (p<0,05; netto del beta > 0; >= 6/9 anni
positivi; senza i 20 migliori > 0). Unita': punti netti, dichiarata prima.

Batteria A (126 regole strutturate) + batteria B (400 regole a caso con seme fisso):
  B1 200 a lato casuale (hash della data) = nullo simmetrico puro
  B2 100 solo long, B3 100 solo short = la lezione del beta.
Tutto registrato con test_id «placebo_*».
"""
from __future__ import annotations

import hashlib
import json
import sys

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from scipy import stats as sps

from lab import core
from lab.wild import common as C


def h64(*parts) -> int:
    return int(hashlib.md5("|".join(map(str, parts)).encode()).hexdigest()[:15], 16)


def moon_phase(sessions) -> np.ndarray:
    """Fase lunare 0..1 (0 = luna nuova) calcolata dal novilunio di riferimento 2000-01-06 18:14 UTC."""
    ref = pd.Timestamp("2000-01-06 18:14")
    days = (pd.DatetimeIndex(sessions) + pd.Timedelta(hours=12) - ref) / pd.Timedelta(days=1)
    return np.mod(days / 29.530588853, 1.0)


PRIMES = np.array([p for p in range(2, 391) if all(p % q for q in range(2, int(p ** 0.5) + 1))])


def main():
    g = C.grid()
    sess = g["sess"]
    S = len(sess)
    dates = [d.strftime("%Y%m%d") for d in sess]
    digsum = np.array([sum(int(c) for c in x) for x in dates])
    dom = sess.day.to_numpy(); doy = sess.dayofyear.to_numpy()
    moon = moon_phase(sess)
    isprime = np.isin(dom, PRIMES)
    hsh = lambda salt: np.array([h64(x, salt) for x in dates], dtype=np.int64)

    FILTERS = {
        "all": np.ones(S, bool),
        "digsum_even": digsum % 2 == 0,
        "digsum_odd": digsum % 2 == 1,
        "dom_prime": isprime,
        "hash3": hsh("f4") % 3 == 0,
        "moon_waxing": moon < 0.5,
        "moon_full": (moon > 0.4) & (moon < 0.6),
        "doy_mod4": doy % 4 == 0,
        "dom_fibo": np.isin(dom, [1, 2, 3, 5, 8, 13, 21]),
        "hash2": hsh("f9") % 2 == 0,
    }
    HORIZ = {"h15": 15, "h60": 60, "hclose": None}
    SIDES = ["long", "short", "hash", "moon"]
    MINS = ["seedfix", "hashday", "moonmin", "primefix"]

    rules = []   # (test_id, desc, s_idx, k_in, k_out, side)
    ridx = 0
    for fname, fmask in FILTERS.items():
        for sname in SIDES:
            for hname, h in HORIZ.items():
                mname = MINS[ridx % 4]
                sidx = np.flatnonzero(fmask)
                hmax = 15 if h is None else h
                span = C.NMIN - hmax            # ingresso in [0, span]
                if mname == "seedfix":
                    k = np.full(len(sidx), np.random.default_rng(ridx).integers(0, span + 1))
                elif mname == "hashday":
                    k = np.array([h64(dates[i], "min", ridx) % (span + 1) for i in sidx])
                elif mname == "moonmin":
                    k = (moon[sidx] * span).astype(int)
                else:
                    pr = PRIMES[PRIMES <= span]
                    k = np.full(len(sidx), pr[np.random.default_rng(ridx).integers(0, len(pr))])
                kout = np.full(len(sidx), C.NMIN) if h is None else k + h
                if sname == "long":
                    sd = np.ones(len(sidx))
                elif sname == "short":
                    sd = -np.ones(len(sidx))
                elif sname == "hash":
                    sd = np.array([1.0 if h64(dates[i], "side", ridx) % 2 else -1.0 for i in sidx])
                else:
                    sd = np.where(moon[sidx] < 0.5, 1.0, -1.0)
                tid = f"placebo_A{ridx:03d}_{fname}_{sname}_{mname}_{hname}"
                desc = (f"PLACEBO strutturato: giorni={fname}, lato={sname}, minuto={mname}, "
                        f"orizzonte={hname}; nessun senso economico per costruzione")
                rules.append((tid, desc, sidx, k, kout, sd, sname))
                ridx += 1

    # minuti primi, 3 trade al giorno scelti dall'hash della data
    for hname, h in (("h15", 15), ("h60", 60)):
        for sname in ("long", "short", "hash"):
            pr = PRIMES[PRIMES <= C.NMIN - h]
            s_l, k_l, sd_l = [], [], []
            for i in range(S):
                picks = sorted({pr[h64(dates[i], "pm", j, hname) % len(pr)] for j in range(3)})
                # niente sovrapposizioni: tieni i minuti distanti almeno h
                last = -10 ** 6
                for kk in picks:
                    if kk - last >= h:
                        s_l.append(i); k_l.append(kk); last = kk
                        if sname == "long":
                            sd_l.append(1.0)
                        elif sname == "short":
                            sd_l.append(-1.0)
                        else:
                            sd_l.append(1.0 if h64(dates[i], "pms", kk) % 2 else -1.0)
            s_l = np.array(s_l); k_l = np.array(k_l)
            tid = f"placebo_A{ridx:03d}_primeminutes3_{sname}_{hname}"
            rules.append((tid, f"PLACEBO: fino a 3 ingressi al giorno in minuti primi scelti dall'hash "
                               f"della data, lato={sname}, orizzonte={hname}", s_l, k_l, k_l + h,
                          np.array(sd_l), sname))
            ridx += 1

    # batteria B: 400 regole a caso con seme fisso
    for r in range(400):
        rng = np.random.default_rng(10_000 + r)
        pday = rng.uniform(0.3, 1.0)
        salt = f"B{r}"
        u = np.array([(h64(x, salt, "day") % 10 ** 6) / 10 ** 6 for x in dates])
        sidx = np.flatnonzero(u < pday)
        hname = ["h15", "h60", "hclose"][rng.integers(0, 3)]
        h = HORIZ[hname]
        span = C.NMIN - (15 if h is None else h)
        if rng.random() < 0.5:
            k = np.full(len(sidx), rng.integers(0, span + 1)); mname = "seedfix"
        else:
            k = np.array([h64(dates[i], salt, "k") % (span + 1) for i in sidx]); mname = "hashday"
        kout = np.full(len(sidx), C.NMIN) if h is None else k + h
        if r < 200:
            sname = "hash"
            sd = np.array([1.0 if h64(dates[i], salt, "s") % 2 else -1.0 for i in sidx])
        elif r < 300:
            sname = "long"; sd = np.ones(len(sidx))
        else:
            sname = "short"; sd = -np.ones(len(sidx))
        tid = f"placebo_B{r:03d}_{sname}_{mname}_{hname}"
        rules.append((tid, f"PLACEBO casuale (seme {10_000 + r}): giorni con prob {pday:.2f} da hash, "
                           f"minuto={mname}, lato={sname}, orizzonte={hname}", sidx, k, kout, sd, sname))

    # ---- trade e statistiche non-bootstrap nel processo principale, bootstrap in parallelo
    prepared = []
    for tid, desc, sidx, k, kout, sd, sname in rules:
        t = C.trades_from(sidx, k, kout, sd)
        prepared.append((tid, desc, t, sname))

    def boot(t):
        net = t["gross"].to_numpy() - core.COST_RT_POINTS
        a = core.day_block_bootstrap(net, t["session"].to_numpy())
        b = core.day_block_bootstrap(t["gross"].to_numpy(), t["session"].to_numpy())
        return a, b

    res = Parallel(n_jobs=24, verbose=0)(delayed(boot)(t) for _, _, t, _ in prepared)

    rows = []
    for (tid, desc, t, sname), (st, stg) in zip(prepared, res):
        net = t["gross"].to_numpy() - core.COST_RT_POINTS
        beta = t["side"].to_numpy() * C.drift(t["k_in"].to_numpy(), t["k_out"].to_numpy())
        yr = core.yearly(net, t["session"]); ypos = int((yr["mean"] > 0).sum())
        d20 = core.drop_top(net, 20)
        st = dict(st)
        st.update(gross=float(t["gross"].mean()), mean_beta=float(beta.mean()),
                  beta_adj=float(np.mean(net - beta)), exposure=float(t["side"].mean()),
                  years_pos=f"{ypos}/{len(yr)}", ypos=ypos, drop20=d20,
                  c1=bool(st["p_pos"] < 0.05), c1_bonf=bool(st["p_pos"] < 0.05 / C.K_BONF),
                  c2=bool(np.mean(net - beta) > 0), c3=bool(ypos >= C.YEARS_NEEDED), c4=bool(d20 > 0),
                  p_pos_gross=stg["p_pos"], p_two_gross=stg["p_two"], mean_gross_ci=[stg["lo"], stg["hi"]])
        st["pass_all"] = bool(st["c1"] and st["c2"] and st["c3"] and st["c4"])
        st["pass_all_bonf"] = bool(st["c1_bonf"] and st["c2"] and st["c3"] and st["c4"])
        # beta-aggiustato anche sul lordo (per il nullo simmetrico)
        C.rec(tid, desc, st, side_scheme=sname, battery=tid.split("_")[1][0])
        rows.append(dict(test_id=tid, battery=tid.split("_")[1][0], side=sname, **{k: st[k] for k in (
            "n", "n_days", "mean", "gross", "p_pos", "p_two", "p_pos_gross", "p_two_gross", "mean_beta",
            "beta_adj", "ypos", "drop20", "c1", "c1_bonf", "c2", "c3", "c4", "pass_all", "pass_all_bonf")}))
    df = pd.DataFrame(rows)
    df.to_csv(C.__file__.replace("common.py", "placebo_results.csv"), index=False)
    summarize(df)


def summarize(df):
    pd.set_option("display.width", 200)
    print(f"regole placebo: {len(df)}")
    grp = df.groupby("side")
    out = pd.DataFrame({
        "N": grp.size(),
        "mean_net": grp["mean"].mean(),
        "mean_beta": grp["mean_beta"].mean(),
        "p<0.05 net": grp["c1"].mean(),
        "p<0.01 net": grp["p_pos"].apply(lambda s: (s < 0.01).mean()),
        "p<0.05/24": grp["c1_bonf"].mean(),
        "p_gross<0.05": grp["p_pos_gross"].apply(lambda s: (s < 0.05).mean()),
        "p_gross2<0.05": grp["p_two_gross"].apply(lambda s: (s < 0.05).mean()),
        "c2 badj>0": grp["c2"].mean(),
        "c3 yrs": grp["c3"].mean(),
        "c4 d20": grp["c4"].mean(),
        "ALL4": grp["pass_all"].mean(),
        "ALL4 bonf": grp["pass_all_bonf"].mean(),
        "c1&c3&c4 (senza beta)": grp.apply(lambda x: (x.c1 & x.c3 & x.c4).mean()),
    })
    print(out.round(3).to_string())
    tot = df
    print("\nTOTALE: p<0.05 net %.3f, p<0.01 %.3f, ALL4 %.3f, ALL4bonf %.3f, senza-beta %.3f" % (
        tot.c1.mean(), (tot.p_pos < 0.01).mean(), tot.pass_all.mean(), tot.pass_all_bonf.mean(),
        (tot.c1 & tot.c3 & tot.c4).mean()))
    sym = df[df.side == "hash"]
    print("simmetrici: KS p_gross unilaterale vs U(0,1): ", sps.kstest(sym.p_pos_gross, "uniform"))
    print("simmetrici: KS p_gross bilaterale vs U(0,1): ", sps.kstest(sym.p_two_gross, "uniform"))
    print(np.histogram(sym.p_pos_gross, bins=10, range=(0, 1))[0])
    print(df.sort_values("p_pos").head(15)[["test_id", "n", "mean", "p_pos", "mean_beta", "beta_adj",
                                           "ypos", "drop20", "pass_all"]].to_string())


if __name__ == "__main__":
    main()
