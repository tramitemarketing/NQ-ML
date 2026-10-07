"""r6_community: statistiche della community contro il caso (PREREG + addendum 1). Test A-F, solo discovery.

Definizioni operative fissate qui, prima dell'esecuzione (valgono identiche per reale e placebo):
- Ogni barra a 1 minuto e' la terna (rc, rh, rl) = log(close, high, low) - log(close precedente), prezzi adj.
  Minuto senza barra = (0, 0, 0). Il percorso si ricostruisce concatenando le sessioni valide dell'anno.
- Placebo (addendum 1): terne divise per la vol della sessione (radice della somma di rc^2), rimescolate minuto per
  minuto fra le sessioni dello stesso anno (la terna resta insieme), rimoltiplicate per la vol della sessione di
  destinazione. 200 storie.
- «Apertura» di un'ora/minuto X = close della barra X-1 (identico nei due mondi; differenza <= qualche tick).
- sigma (A, B): SD dei 20 rendimenti 16:00->16:00 precedenti, calcolata sul percorso (reale o placebo).
- Livelli in log; 1 tick = log(1 + 0,25 / prezzo grezzo reale del giorno). Punti = log x prezzo grezzo reale.
- A: primo tocco (H >= O8+0,25s o L <= O8-0,25s) fra 08:00 e 08:59; stesso minuto su entrambi = escluso;
  successo = ritorno a O8 (L <= O8 dopo un tocco in alto) nei minuti successivi fino alle 11:59.
- B: fade con limite al livello, fill con attraversamento di 1 tick fra 08:00 e 08:59, target O8 con
  attraversamento di 1 tick, altrimenti close delle 11:59. Statistica: bps netti (0,75) medi per trade.
  Sensibilita': stop a 1 sigma oltre l'ingresso (stop prima del target).
- C: ore 08-15; l'apertura dell'ora sta nel range dell'ora precedente (estremi inclusi); primo sweep H > max o
  L < min dell'ora precedente (stesso minuto su entrambi = escluso); successo = ritorno all'apertura dell'ora
  entro la fine dell'ora.
- D: settimana = sessioni con la stessa settimana ISO nello stesso anno (le settimane a cavallo d'anno sono
  escluse: il percorso placebo riparte a inizio anno); livello = apertura 09:30 della prima sessione;
  successo = tocco (L <= livello <= H) nelle RTH di una sessione successiva della settimana. Fasce di distanza
  |apertura della seconda sessione - livello| / livello.
- E: livello = apertura delle 00:00; successo = tocco nelle RTH; sopra/sotto secondo l'apertura RTH.
- F: AM 08:00-11:59, PM 12:00-15:59. «Estremo fatto per ultimo» nell'AM (massimo o minimo, confrontando i minuti);
  successo in tempo reale = il PM rompe l'estremo AM opposto. Versione pubblicata = stesso tasso solo sulle
  sessioni «opposte» (massimo e minimo 08-16 in meta' diverse, note alle 16:00).
- p = (1 + #placebo >= reale)/201, Holm k = 6 su A-F; «stesso segno nelle due meta'» = reale - media placebo > 0
  in ciascuna meta'.
"""
import json

import numpy as np
import pandas as pd

from lab import core, r6_common as RC

FAM = "r6_community"
N_PLAC = 200


def mi(hh, mm):
    return ((hh * 60 + mm) - 1080) % 1440


class World:
    def __init__(self):
        bars, daily = core.load("discovery")
        d = daily[daily["valid"] & daily["in_phase"]]
        self.S = pd.DatetimeIndex(d.index)
        b = bars[bars["session"].isin(d.index.values)]
        lc = np.log(b["adj_close"].to_numpy())
        prev = np.r_[lc[0], lc[:-1]]
        ms = (b["ny_min"].to_numpy().astype(int) - 1080) % 1440
        si = self.S.get_indexer(pd.DatetimeIndex(b["session"].to_numpy()))
        ok = ms < 1380
        n = len(self.S)
        self.T = np.zeros((n, 1380, 3))
        for k, col in enumerate(("adj_close", "adj_high", "adj_low")):
            self.T[si[ok], ms[ok], k] = np.log(b[col].to_numpy())[ok] - prev[ok]
        self.years = self.S.year.to_numpy()
        # prezzo di partenza di ogni anno: log close prima della prima barra dell'anno
        self.start = {}
        for y in np.unique(self.years):
            i0 = np.searchsorted(b["session"].to_numpy(), np.datetime64(self.S[self.years == y][0]))
            self.start[y] = prev[i0]
        raw16 = b[b["rth"]].groupby("session")["close"].last().reindex(self.S)
        self.raw = raw16.shift(1).bfill().to_numpy()             # prezzo grezzo di riferimento del giorno
        self.tick = np.log(1 + core.TICK / self.raw)
        self.vol = np.sqrt((self.T[:, :, 0] ** 2).sum(1)) + 1e-12
        self.bars = bars
        self.ts0 = pd.DatetimeIndex([(s - pd.Timedelta(hours=6)).tz_localize(core.NY) for s in self.S]).tz_convert("UTC")

    def shuffled(self, rng):
        Z = self.T / self.vol[:, None, None]
        out = np.empty_like(Z)
        for y in np.unique(self.years):
            rows = np.where(self.years == y)[0]
            perm = rng.random((len(rows), 1380)).argsort(0)
            out[rows] = np.take_along_axis(Z[rows], perm[:, :, None], axis=0)
        return out * self.vol[:, None, None]

    def path(self, T):
        C = np.empty(T.shape[:2])
        for y in np.unique(self.years):
            rows = np.where(self.years == y)[0]
            C[rows] = (self.start[y] + np.cumsum(T[rows, :, 0].ravel())).reshape(len(rows), 1380)
        P = C - T[:, :, 0]
        return C, P + T[:, :, 1], P + T[:, :, 2]


def first_true(M):
    """Indice della prima colonna True per riga (-1 se nessuna)."""
    any_ = M.any(1)
    return np.where(any_, M.argmax(1), -1)


def stats_of(W, C, H, L, want_trades=False):
    n = len(W.S)
    out = {}
    # ---- sigma e O8
    c16 = C[:, mi(15, 59)]
    sig = pd.Series(np.r_[np.nan, np.diff(c16)]).rolling(20).std().shift(1).to_numpy()
    O8 = C[:, mi(7, 59)]
    a0, a1, noon = mi(8, 0), mi(8, 59) + 1, mi(11, 59)
    up, dn = O8 + 0.25 * sig, O8 - 0.25 * sig
    # ---- A
    tu = first_true(H[:, a0:a1] >= up[:, None])
    td = first_true(L[:, a0:a1] <= dn[:, None])
    succ, ev_days, ev_side = [], [], []
    for i in range(n):
        if np.isnan(sig[i]):
            continue
        u, dd = tu[i], td[i]
        if u < 0 and dd < 0:
            continue
        if u >= 0 and dd >= 0 and u == dd:
            continue
        if dd < 0 or (u >= 0 and u < dd):
            t = a0 + u
            s = bool((L[i, t + 1:noon + 1] <= O8[i]).any())
        else:
            t = a0 + dd
            s = bool((H[i, t + 1:noon + 1] >= O8[i]).any())
        succ.append(s); ev_days.append(i)
    out["A"] = (np.array(succ, float), np.array(ev_days))
    # ---- B (fade con trade-through) e sensibilita' con stop a 1 sigma
    tk = W.tick
    fu = first_true(H[:, a0:a1] >= (up + tk)[:, None])
    fd = first_true(L[:, a0:a1] <= (dn - tk)[:, None])
    bnet, bdays, bstop, trades = [], [], [], []
    for i in range(n):
        if np.isnan(sig[i]) or (fu[i] < 0 and fd[i] < 0) or (fu[i] >= 0 and fu[i] == fd[i]):
            continue
        if fd[i] < 0 or (fu[i] >= 0 and fu[i] < fd[i]):
            side, t, ent = -1, a0 + fu[i], up[i]
        else:
            side, t, ent = +1, a0 + fd[i], dn[i]
        seg_h, seg_l = H[i, t + 1:noon + 1], L[i, t + 1:noon + 1]
        hit = (seg_l <= O8[i] - tk[i]) if side < 0 else (seg_h >= O8[i] + tk[i])
        j = first_true(hit[None, :])[0]
        ex, jx = (O8[i], t + 1 + j) if j >= 0 else (C[i, noon], noon)
        g = side * (ex - ent)
        bnet.append(g * 1e4 - 0.75 / W.raw[i] * 1e4); bdays.append(i)
        trades.append((i, t, jx, side, g * W.raw[i]))
        stp = ent - side * sig[i]
        hs = (seg_h >= stp) if side < 0 else (seg_l <= stp)
        ks = first_true(hs[None, :])[0]
        if ks >= 0 and (j < 0 or ks <= j):
            g2 = side * (stp - ent)
        else:
            g2 = g
        bstop.append(g2 * 1e4 - 0.75 / W.raw[i] * 1e4)
    out["B"] = (np.array(bnet), np.array(bdays))
    out["B_stop"] = (np.array(bstop), np.array(bdays))
    # ---- C
    cs, cd, cthird = [], [], []
    for hh in range(8, 16):
        s0 = mi(hh, 0)
        PH, PL = H[:, s0 - 60:s0].max(1), L[:, s0 - 60:s0].min(1)
        Op = C[:, s0 - 1]
        inside = (Op >= PL) & (Op <= PH)
        su = first_true(H[:, s0:s0 + 60] > PH[:, None])
        sd = first_true(L[:, s0:s0 + 60] < PL[:, None])
        for i in np.where(inside)[0]:
            u, dd = su[i], sd[i]
            if (u < 0 and dd < 0) or (u >= 0 and u == dd):
                continue
            if dd < 0 or (u >= 0 and u < dd):
                t = s0 + u
                s = bool((L[i, t + 1:s0 + 60] <= Op[i]).any())
            else:
                t = s0 + dd
                s = bool((H[i, t + 1:s0 + 60] >= Op[i]).any())
            cs.append(s); cd.append(i); cthird.append((t - s0) // 20)
    out["C"] = (np.array(cs, float), np.array(cd))
    out["C_third"] = np.array(cthird)
    # ---- D
    r0, r1 = mi(9, 30), mi(15, 59) + 1
    iso = W.S.isocalendar()
    wk = (iso["year"].astype(int) * 100 + iso["week"].astype(int)).to_numpy()
    ds, dd_, dband = [], [], []
    for w in np.unique(wk):
        rows = np.where(wk == w)[0]
        if len(rows) < 2 or len(np.unique(W.years[rows])) > 1:
            continue
        lvl = C[rows[0], r0 - 1]
        hit = any(((L[r, r0:r1] <= lvl) & (H[r, r0:r1] >= lvl)).any() for r in rows[1:])
        dist = abs(np.exp(C[rows[1], r0 - 1] - lvl) - 1)
        ds.append(hit); dd_.append(rows[0]); dband.append(np.digitize(dist, [0.0025, 0.005, 0.01, 0.015]))
    out["D"] = (np.array(ds, float), np.array(dd_))
    out["D_band"] = np.array(dband)
    # ---- E
    Z = C[:, mi(23, 59)]
    touch = ((L[:, r0:r1] <= Z[:, None]) & (H[:, r0:r1] >= Z[:, None])).any(1)
    out["E"] = (touch.astype(float), np.arange(n))
    out["E_above"] = C[:, r0 - 1] > Z
    # ---- F
    am0, am1, pm1 = mi(8, 0), mi(12, 0), mi(15, 59) + 1
    AH, AL = H[:, am0:am1].max(1), L[:, am0:am1].min(1)
    ah_t, al_t = H[:, am0:am1].argmax(1), L[:, am0:am1].argmin(1)
    PHh, PLl = H[:, am1:pm1].max(1), L[:, am1:pm1].min(1)
    high_last = ah_t > al_t
    fs = np.where(high_last, PLl < AL, PHh > AH).astype(float)
    opposite = ((PHh > AH) & ~(PLl < AL)) | ((PLl < AL) & ~(PHh > AH))
    out["F"] = (fs, np.arange(n))
    out["F_published"] = (fs[opposite], np.where(opposite)[0])
    if want_trades:
        out["B_trades"] = trades
    return out


def rate_stats(out):
    return {k: float(np.mean(out[k][0])) for k in ("A", "B", "C", "D", "E", "F")} | {
        "F_published": float(np.mean(out["F_published"][0])), "B_stop": float(np.mean(out["B_stop"][0]))}


def half_rates(W, out, k):
    v, days = out[k]
    h = RC.half_of(W.S[days])
    return {x: float(np.mean(v[h == x])) for x in RC.HALVES}


if __name__ == "__main__":
    W = World()
    C, H, L = W.path(W.T)
    real = stats_of(W, C, H, L, want_trades=True)
    R = rate_stats(real)
    RH = {k: half_rates(W, real, k) for k in ("A", "B", "C", "D", "E", "F")}
    rng = np.random.default_rng(11)
    P, PH, Psimple = [], [], []
    for it in range(N_PLAC):
        Cp, Hp, Lp = W.path(W.shuffled(rng))
        o = stats_of(W, Cp, Hp, Lp)
        P.append(rate_stats(o))
        PH.append({k: half_rates(W, o, k) for k in ("A", "B", "C", "D", "E", "F")})
    # descrittivo: rimescolamento semplice (senza scala), 50 storie
    for it in range(50):
        Z = W.T.copy()
        out = np.empty_like(Z)
        for y in np.unique(W.years):
            rows = np.where(W.years == y)[0]
            perm = rng.random((len(rows), 1380)).argsort(0)
            out[rows] = np.take_along_axis(Z[rows], perm[:, :, None], axis=0)
        Psimple.append(rate_stats(stats_of(W, *W.path(out))))
    P, Psimple = pd.DataFrame(P), pd.DataFrame(Psimple)
    res = {"n_events": {k: int(len(real[k][0])) for k in ("A", "B", "C", "D", "E", "F")}, "real": R,
           "placebo_mean": P.mean().round(4).to_dict(), "placebo_p95": P.quantile(0.95).round(4).to_dict(),
           "placebo_simple_mean": Psimple.mean().round(4).to_dict()}
    pv = {k: RC.placebo_p(R[k], P[k].to_numpy()) for k in ("A", "B", "C", "D", "E", "F")}
    ph = RC.holm(pv)
    res["p_placebo"], res["p_holm"] = pv, ph
    halves = {}
    for k in ("A", "B", "C", "D", "E", "F"):
        pm = {x: float(np.mean([p[k][x] for p in PH])) for x in RC.HALVES}
        halves[k] = {x: {"real": RH[k][x], "placebo": pm[x], "diff": RH[k][x] - pm[x]} for x in RC.HALVES}
    res["halves"] = halves
    verdict = {}
    for k in ("A", "C", "D", "E", "F"):
        verdict[k] = "reale" if (ph[k] < 0.05 and all(halves[k][x]["diff"] > 0 for x in RC.HALVES)) else \
            "spiegato dal random walk"
    # B: sfruttabile?
    tr = real["B_trades"]
    tdf = pd.DataFrame(tr, columns=["i", "t", "jx", "side", "gross_pts"])
    tdf["session"] = W.S[tdf["i"]]
    tdf["entry_ts"] = W.ts0[tdf["i"]] + pd.to_timedelta(tdf["t"], unit="min")
    tdf["exit_ts"] = W.ts0[tdf["i"]] + pd.to_timedelta(tdf["jx"], unit="min")
    h = RC.half_of(tdf["session"])
    net125 = {x: float((tdf["gross_pts"][h == x] - 1.25).mean()) for x in RC.HALVES}
    crit = RC.lab_criteria(W.bars, tdf[["session", "entry_ts", "exit_ts", "side", "gross_pts"]], alpha=0.05 / 6)
    verdict["B"] = "sfruttabile" if (ph["B"] < 0.05 and pv["B"] <= 0.05 and all(v > 0 for v in net125.values())
                                     and crit["pass"]) else "non sfruttabile"
    res["B_detail"] = {"n": len(tdf), "gross_pts": float(tdf["gross_pts"].mean()),
                       "net075_pts": float((tdf["gross_pts"] - 0.75).mean()), "net125_halves": net125,
                       "long_share": float((tdf["side"] > 0).mean()), "lab_criteria": crit}
    res["verdict"] = verdict
    # descrittivi
    res["C_by_third"] = pd.Series(real["C"][0]).groupby(real["C_third"]).mean().round(4).to_dict()
    res["D_by_band"] = pd.Series(real["D"][0]).groupby(real["D_band"]).agg(["mean", "size"]).round(4).to_dict()
    res["E_above_below"] = {"sopra": float(real["E"][0][real["E_above"]].mean()),
                            "sotto": float(real["E"][0][~real["E_above"]].mean())}
    res["F_conditioning_adds"] = {"reale": R["F_published"] - R["F"],
                                  "placebo": float(P["F_published"].mean() - P["F"].mean())}
    print(json.dumps(res, indent=1, default=str))
    for k in ("A", "B", "C", "D", "E", "F"):
        core.record(FAM, k, f"community test {k} contro placebo scalato (primario)", "discovery",
                    {"real": R[k], "placebo_mean": float(P[k].mean()), "p_placebo": pv[k], "p_holm": ph[k],
                     "n": res["n_events"][k]}, halves=halves[k], verdict=verdict[k])
    (core.ROOT / "lab" / FAM / "results.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
