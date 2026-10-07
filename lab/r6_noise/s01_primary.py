"""r6_noise: Noise Area di Zarattini (parametri del paper, 14 giorni). Test primari A e B, placebo. Solo discovery.

Definizioni operative fissate qui, prima dell'esecuzione:
- matrici RTH per sessione (minuti 09:30-15:59), prezzi adj; P_tau = close della barra che inizia a tau-1;
  ingresso all'open della barra tau; uscita A al close della barra 15:59.
- B: a ogni tau' successivo della griglia, long esce se P_tau' < max(UB_tau', VWAP_tau') (short: > min(LB, VWAP)),
  all'open della barra tau'; VWAP RTH = somma((h+l+c)/3 * volume) / somma(volume) sulle barre prima di tau'.
- p di A: t unilaterale sui bps lordi giornalieri (zeri inclusi); p di B: sui bps netti a 0,75.
- «t >= 1 in entrambe le meta'» e «placebo >= 95°» si applicano ad A e a B (lettura severa).
- placebo: per ogni sessione con un trade reale, tau casuale sulla griglia, lato = segno di ln(P_tau/O),
  stesse uscite; statistica = bps medi per trade (A lordo, B netto 0,75).
"""
import json

import numpy as np
import pandas as pd

from lab import core, r6_common as RC

FAM = "r6_noise"
GRID = np.array([600 + 30 * i for i in range(12)])      # 10:00 ... 15:30
N_PLAC = 200


def matrices(bars, daily):
    d = daily[daily["valid"]]
    b = bars[bars["rth"] & bars["session"].isin(d.index.values)]
    col = b["ny_min"].to_numpy() - 570
    si = pd.Index(d.index).get_indexer(pd.DatetimeIndex(b["session"].to_numpy()))
    n = len(d)
    M = {}
    for k, src in (("o", "adj_open"), ("h", "adj_high"), ("l", "adj_low"), ("c", "adj_close"), ("v", "volume"),
                   ("raw", "close")):
        A = np.full((n, 390), np.nan)
        A[si, col] = b[src].to_numpy()
        M[k] = A
    for k in ("c", "raw"):                                  # barre mancanti (rarissime): ultimo prezzo noto
        M[k] = pd.DataFrame(M[k]).ffill(axis=1).to_numpy()
    for k in ("o", "h", "l"):
        M[k] = np.where(np.isnan(M[k]), M["c"], M[k])
    M["v"] = np.nan_to_num(M["v"])
    return d, M


def setup(d, M):
    O = M["o"][:, 0]
    P = M["c"][:, GRID - 571]                               # P_tau = close della barra tau-1
    Cprev = np.r_[np.nan, M["c"][:-1, 389]]
    dev = pd.DataFrame(np.abs(P / O[:, None] - 1))
    sig = dev.rolling(14, min_periods=14).mean().shift(1).to_numpy()
    UB = np.maximum(O, Cprev)[:, None] * (1 + sig)
    LB = np.minimum(O, Cprev)[:, None] * (1 - sig)
    tp = (M["h"] + M["l"] + M["c"]) / 3
    cv = np.cumsum(M["v"], axis=1)
    cpv = np.cumsum(tp * M["v"], axis=1)
    VW = cpv[:, GRID - 571] / np.where(cv[:, GRID - 571] > 0, cv[:, GRID - 571], np.nan)
    return O, P, UB, LB, VW


def run(M, O, P, UB, LB, VW, rows, gi, side):
    """Trade per le sessioni `rows`, ingresso al punto di griglia gi, lato side. Restituisce (A_pts, B_pts, uscita B)."""
    ent = M["o"][rows, GRID[gi] - 570]
    a_pts = side * (M["c"][rows, 389] - ent)
    b_pts = a_pts.copy()
    b_exit = np.full(len(rows), 389)
    for k in range(len(rows)):
        r, g, s = rows[k], gi[k], side[k]
        for g2 in range(g + 1, len(GRID)):
            if s > 0 and P[r, g2] < max(UB[r, g2], VW[r, g2]) or s < 0 and P[r, g2] > min(LB[r, g2], VW[r, g2]):
                px = M["o"][r, GRID[g2] - 570]
                b_pts[k] = s * (px - ent[k])
                b_exit[k] = GRID[g2] - 570
                break
    return a_pts, b_pts, ent, b_exit


if __name__ == "__main__":
    bars, daily = core.load("discovery", warmup_days=20)
    d, M = matrices(bars, daily)
    O, P, UB, LB, VW = setup(d, M)
    inph = d["in_phase"].to_numpy() & ~np.isnan(UB).any(1)
    up, dn = P > UB, P < LB
    first = np.where(up | dn, np.arange(len(GRID))[None, :], 99).min(1)
    rows = np.where(inph & (first < 99))[0]
    gi = first[rows]
    side = np.where(up[rows, gi], 1, -1)
    a_pts, b_pts, ent, b_exit = run(M, O, P, UB, LB, VW, rows, gi, side)
    raw = M["raw"][rows, GRID[gi] - 571]
    S_all = d.index[inph]
    sess = d.index[rows]

    def per_day(v):
        return pd.Series(v, index=sess).reindex(S_all).fillna(0.0)
    A_bps, B_net_bps = a_pts / raw * 1e4, (b_pts - 0.75) / raw * 1e4
    dA, dB = per_day(A_bps), per_day(B_net_bps)
    h = RC.half_of(sess)
    res = {"n_trades": len(rows), "n_days": int(inph.sum()), "long_share": float((side > 0).mean()),
           "A": RC.daily_t(dA), "A_halves": RC.by_half(dA), "B": RC.daily_t(dB), "B_halves": RC.by_half(dB),
           "A_gross_pts": float(a_pts.mean()), "B_gross_pts": float(b_pts.mean()),
           "B_net125_halves": {k: float((b_pts[h == k] - 1.25).mean()) for k in RC.HALVES},
           "B_years_net075": pd.Series(b_pts - 0.75, index=sess).groupby(sess.year).mean().round(2).to_dict(),
           "A_units": {"pts": float(a_pts.mean()), "bps": float(A_bps.mean())}}
    # orizzonti descrittivi di A a 30 e 60 minuti
    for H in (30, 60):
        j = np.minimum(GRID[gi] - 570 + H - 1, 389)
        res[f"A{H}_bps"] = float((side * (M["c"][rows, j] - ent) / raw * 1e4).mean())
    atr = pd.Series(d["rth_high"] - d["rth_low"]).rolling(20).mean().shift(1).to_numpy()[rows]
    res["B_gross_atr"] = float(np.nanmean(b_pts / atr))

    rng = np.random.default_rng(7)
    pl = []
    for _ in range(N_PLAC):
        g = rng.integers(0, len(GRID), len(rows))
        s = np.where(np.log(P[rows, g] / O[rows]) >= 0, 1, -1)
        pa, pb, _, _ = run(M, O, P, UB, LB, VW, rows, g, s)
        rw = M["raw"][rows, GRID[g] - 571]
        pl.append(((pa / rw * 1e4).mean(), ((pb - 0.75) / rw * 1e4).mean()))
    pl = np.array(pl)
    res["placebo"] = {"p_A": RC.placebo_p(A_bps.mean(), pl[:, 0]), "p_B": RC.placebo_p(B_net_bps.mean(), pl[:, 1]),
                      "A_pct": np.percentile(pl[:, 0], [5, 50, 95]).round(3).tolist(),
                      "B_pct": np.percentile(pl[:, 1], [5, 50, 95]).round(3).tolist(),
                      "A_real_bps_per_trade": float(A_bps.mean()), "B_real_net_bps_per_trade": float(B_net_bps.mean())}
    ph = RC.holm({"A": res["A"]["p_pos"], "B": res["B"]["p_pos"]})
    res["holm"] = ph
    tr = pd.DataFrame({"session": sess, "side": side, "gross_pts": b_pts})
    # timestamp di ingresso/uscita (barre RTH reali della sessione)
    rth = bars[bars["rth"]]
    first_ts = rth.groupby("session").apply(lambda x: x.index[0])
    t0 = pd.DatetimeIndex(first_ts.reindex(sess).to_numpy())
    tr["entry_ts"] = t0 + pd.to_timedelta(GRID[gi] - 570, unit="min")
    tr["exit_ts"] = t0 + pd.to_timedelta(b_exit, unit="min")
    crit = RC.lab_criteria(bars, tr, alpha=0.025)
    res["lab_criteria_B"] = crit
    go = {"A_B_holm": ph["A"] < 0.05 and ph["B"] < 0.05,
          "t1_both_halves": all(res[x][k]["t"] >= 1 for x in ("A_halves", "B_halves") for k in RC.HALVES),
          "placebo95": res["placebo"]["p_A"] <= 0.05 and res["placebo"]["p_B"] <= 0.05,
          "B_net125_both_halves": all(v > 0 for v in res["B_net125_halves"].values()),
          "lab_criteria": crit["pass"]}
    res["GO_checks_before_correlation"] = go
    res["GO_before_correlation"] = all(go.values())
    print(json.dumps(res, indent=1, default=str))
    tr.to_parquet(core.CACHE / "r6_noise_trades.parquet")
    core.record(FAM, "A", "Noise Area segnale nudo fino alle 16:00, bps lordi giornalieri (primario)", "discovery",
                res["A"], halves=res["A_halves"], placebo_p=res["placebo"]["p_A"], holm_p=ph["A"])
    core.record(FAM, "B", "Noise Area regole complete, bps netti 0,75 giornalieri (primario)", "discovery",
                res["B"], halves=res["B_halves"], placebo_p=res["placebo"]["p_B"], holm_p=ph["B"],
                net125_halves=res["B_net125_halves"], lab_criteria=crit["crit"])
    (core.ROOT / "lab" / FAM / "results.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
