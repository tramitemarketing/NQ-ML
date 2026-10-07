"""PLACEBO, batterie C e D: le stesse regole senza senso, ma con posizioni che attraversano la notte.

Motivo (scritto dopo p01, dichiarato): nella batteria A/B (tutto dentro la RTH) la deriva media per
trade e' ~0,01 punti, quindi i placebo «long» NON vincono per beta: nel 2010-2018 la salita di NQ
e' avvenuta quasi tutta fuori dalla RTH. La lezione del beta va quindi mostrata dove il beta c'e':
  C (150): ingresso a un minuto qualunque della sessione (24 h, o solo RTH), orizzonte 15 / 60 / 390
           minuti di orologio (390 dalla RTH finisce nella sera Globex), prezzi adj;
  D (90):  chiusura RTH -> chiusura RTH successiva, chiusura RTH -> apertura RTH successiva (notte),
           chiusura -> chiusura dopo 5 sessioni (non sovrapposti); 10 filtri-data x long/short/hash.
Stessi costi, stesso bootstrap, stessi 4 criteri. Unita': punti netti.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from joblib import Parallel, delayed

from lab import core
from lab.wild import common as C
from lab.wild.p01_placebo import h64, moon_phase, PRIMES, summarize


def main():
    bars, daily = core.load("discovery")
    bars = bars[bars["in_phase"]]
    ts = bars.index.tz_convert(None).to_numpy().astype("datetime64[m]")
    close = bars["adj_close"].to_numpy()
    tnext = ts + np.timedelta64(1, "m")                 # istante di fine barra
    sess_b = bars["session"].to_numpy().astype("datetime64[D]")
    nym = bars["ny_min"].to_numpy().astype(int)
    rth = bars["rth"].to_numpy()

    def fwd(i_entry, h):
        """Rendimento adj da fine barra i a (fine barra i + h minuti), ultimo prezzo disponibile."""
        target = tnext[i_entry] + np.timedelta64(int(h), "m")
        j = np.searchsorted(tnext, target, side="right") - 1
        return close[j] - close[i_entry], j

    # deriva della stessa finestra: media per minuto NY d'ingresso e orizzonte, su tutte le barre
    drift_tab = {}
    all_i = np.arange(len(bars))
    for h in (15, 60, 390):
        r, _ = fwd(all_i, h)
        drift_tab[h] = pd.Series(r).groupby(nym).mean()

    dv = daily[daily["valid"] & daily["in_phase"]]
    sess = dv.index
    dates = [d.strftime("%Y%m%d") for d in sess]
    S = len(sess)
    digsum = np.array([sum(int(c) for c in x) for x in dates])
    dom = sess.day.to_numpy(); doy = sess.dayofyear.to_numpy(); moon = moon_phase(sess)
    hsh = lambda salt: np.array([h64(x, salt) for x in dates], dtype=np.int64)
    FILTERS = {
        "all": np.ones(S, bool), "digsum_even": digsum % 2 == 0, "digsum_odd": digsum % 2 == 1,
        "dom_prime": np.isin(dom, PRIMES), "hash3": hsh("f4") % 3 == 0, "moon_waxing": moon < 0.5,
        "moon_full": (moon > 0.4) & (moon < 0.6), "doy_mod4": doy % 4 == 0,
        "dom_fibo": np.isin(dom, [1, 2, 3, 5, 8, 13, 21]), "hash2": hsh("f9") % 2 == 0,
    }

    # indice delle barre per sessione
    sess_codes = pd.DatetimeIndex(sess).values.astype("datetime64[D]")
    starts = np.searchsorted(sess_b, sess_codes, side="left")
    ends = np.searchsorted(sess_b, sess_codes, side="right")

    prepared = []
    # ---------------- batteria C
    for r in range(150):
        rng = np.random.default_rng(20_000 + r)
        pday = rng.uniform(0.3, 1.0); salt = f"C{r}"
        h = [15, 60, 390][rng.integers(0, 3)]
        only_rth = rng.random() < 0.5
        side_s = "long" if r < 50 else ("short" if r < 100 else "hash")
        I, SD, SS = [], [], []
        for i in range(S):
            if (h64(dates[i], salt, "d") % 10 ** 6) / 10 ** 6 >= pday:
                continue
            a, b = starts[i], ends[i]
            cand = np.arange(a, b)
            if only_rth:
                cand = cand[rth[a:b]]
            if len(cand) == 0:
                continue
            ie = cand[h64(dates[i], salt, "k") % len(cand)]
            I.append(ie); SS.append(i)
            SD.append(1.0 if side_s == "long" else -1.0 if side_s == "short"
                      else (1.0 if h64(dates[i], salt, "s") % 2 else -1.0))
        I = np.array(I); SD = np.array(SD)
        g, _ = fwd(I, h)
        t = pd.DataFrame(dict(session=sess[np.array(SS)], side=SD, gross=SD * g,
                              beta=SD * drift_tab[h].reindex(nym[I]).to_numpy()))
        tid = f"placebo_C{r:03d}_{side_s}_{'rth' if only_rth else '24h'}_h{h}"
        prepared.append((tid, f"PLACEBO casuale (seme {20_000 + r}): minuto d'ingresso da hash "
                              f"({'RTH' if only_rth else '24h'}), orizzonte {h} minuti di orologio, "
                              f"prezzi adj, lato={side_s}", t, side_s))

    # ---------------- batteria D
    rc = dv["rth_close"].to_numpy(); ro = dv["rth_open"].to_numpy()
    # sessioni consecutive valide: la successiva nella tabella valida
    win = {
        "c2c1": (np.r_[rc[1:], np.nan] - rc, 1),
        "c2o": (np.r_[ro[1:], np.nan] - rc, 1),
        "c2c5": (np.r_[rc[5:], [np.nan] * 5] - rc, 5),
    }
    for wname, (ret, step) in win.items():
        dmean = np.nanmean(ret)
        for fname, fmask in FILTERS.items():
            for side_s in ("long", "short", "hash"):
                idx = []
                nxt = -1
                for i in np.flatnonzero(fmask):
                    if i >= nxt and np.isfinite(ret[i]):
                        idx.append(i); nxt = i + step
                idx = np.array(idx)
                SD = (np.ones(len(idx)) if side_s == "long" else -np.ones(len(idx)) if side_s == "short"
                      else np.array([1.0 if h64(dates[i], "Dside", wname, fname) % 2 else -1.0 for i in idx]))
                t = pd.DataFrame(dict(session=sess[idx], side=SD, gross=SD * ret[idx], beta=SD * dmean))
                tid = f"placebo_D_{wname}_{fname}_{side_s}"
                prepared.append((tid, f"PLACEBO multi-sessione: finestra {wname} (prezzi adj), "
                                      f"giorni={fname}, lato={side_s}", t, side_s))

    def boot(t):
        net = t["gross"].to_numpy() - core.COST_RT_POINTS
        return (core.day_block_bootstrap(net, t["session"].to_numpy()),
                core.day_block_bootstrap(t["gross"].to_numpy(), t["session"].to_numpy()))

    res = Parallel(n_jobs=24)(delayed(boot)(t) for _, _, t, _ in prepared)
    rows = []
    for (tid, desc, t, sname), (st, stg) in zip(prepared, res):
        net = t["gross"].to_numpy() - core.COST_RT_POINTS
        beta = t["beta"].to_numpy()
        yr = core.yearly(net, t["session"]); ypos = int((yr["mean"] > 0).sum())
        d20 = core.drop_top(net, 20)
        badj = float(np.mean(net - beta))
        st = dict(st)
        st.update(gross=float(t["gross"].mean()), mean_beta=float(beta.mean()), beta_adj=badj,
                  exposure=float(t["side"].mean()), years_pos=f"{ypos}/{len(yr)}", ypos=ypos, drop20=d20,
                  c1=bool(st["p_pos"] < 0.05), c1_bonf=bool(st["p_pos"] < 0.05 / C.K_BONF), c2=bool(badj > 0),
                  c3=bool(ypos >= C.YEARS_NEEDED), c4=bool(d20 > 0),
                  p_pos_gross=stg["p_pos"], p_two_gross=stg["p_two"])
        st["pass_all"] = bool(st["c1"] and st["c2"] and st["c3"] and st["c4"])
        st["pass_all_bonf"] = bool(st["c1_bonf"] and st["c2"] and st["c3"] and st["c4"])
        bat = "C" if tid.startswith("placebo_C") else "D"
        C.rec(tid, desc, st, side_scheme=sname, battery=bat)
        rows.append(dict(test_id=tid, battery=bat, side=sname, **{k: st[k] for k in (
            "n", "n_days", "mean", "gross", "p_pos", "p_two", "p_pos_gross", "p_two_gross", "mean_beta",
            "beta_adj", "ypos", "drop20", "c1", "c1_bonf", "c2", "c3", "c4", "pass_all", "pass_all_bonf")}))
    df = pd.DataFrame(rows)
    df.to_csv(C.__file__.replace("common.py", "placebo_results_notte.csv"), index=False)
    for bat in ("C", "D"):
        print(f"\n===== batteria {bat}")
        summarize(df[df.battery == bat])
    if True:
        d = df[df.battery == "D"]
        print(d.pivot_table(index="test_id", values=["mean", "p_pos", "mean_beta", "beta_adj", "ypos",
                                                     "pass_all"]).sort_values("p_pos").head(30).to_string())


if __name__ == "__main__":
    main()
