"""r6_silverbullet: test primari A e B (PREREG), placebo, sensibilita'. Solo discovery.

Definizioni operative fissate qui, prima dell'esecuzione:
- A: rendimento nel verso del bias dal prezzo di fill al close della barra fill+H-1 min; primario H = 60, in bps
  (punti / prezzo grezzo del minuto di fill x 1e4). p = t unilaterale sul P&L giornaliero (zeri inclusi).
- B: netto in bps giornaliero a 0,75 per il p; netto a 1,25 per trade nelle due meta'.
- percentuale di vincite = quota di trade chiusi al target; pareggio = media di (1 + 1,25/R)/3.
- placebo: per ogni trade reale, stessa sessione e finestra, minuto casuale; decide A; B solo riportato.
- criteri del §19 su B con soglia 0,05/2 (primo passo di Holm).
"""
import json

import numpy as np
import pandas as pd

from lab import core, r6_common as RC
from lab.r6_silverbullet import common as C

FAM = "r6_silverbullet"
N_PLAC = 200


def per_session(D, t, col, cost_pts=0.0):
    v = (t[col] - cost_pts) / t["raw_px"] * 1e4
    return v.groupby(t["session"]).sum().reindex(D.sessions).fillna(0.0)


def placebo(D, t, rng):
    """Una storia placebo: un trade per ogni trade reale, stessa sessione e finestra, minuto casuale."""
    years = pd.DatetimeIndex(t["session"]).year.to_numpy()
    risks = t["risk"].to_numpy()
    a60, net = [], []
    for k, r in enumerate(t.itertuples()):
        wopen = (r.session + pd.Timedelta(minutes=C.WINDOWS[r.window])).tz_localize(core.NY)
        a, b = D.i1(wopen), D.i1(wopen + pd.Timedelta(minutes=60))
        i = rng.integers(a, b)
        lo = D.i1(D.t1[i] - pd.Timedelta(minutes=120))
        mid = (D.h1[lo:i].max() + D.l1[lo:i].min()) / 2
        entry = D.o1[i]
        side = -1 if entry > mid else +1
        R = rng.choice(risks[years == years[k]])
        px, _, _ = C.manage(D, i, side, entry, entry - side * R, entry + 2 * side * R)
        p60, _ = C.horizon_px(D, i, 60)
        a60.append((p60 - entry) * side / D.raw1[i] * 1e4)
        net.append((px - entry) * side - core.COST_RT_POINTS)
    return float(np.mean(a60)), float(np.mean(net))


def summary(D, t, label):
    t = t.copy()
    t["bps60"] = t["a60_pts"] / t["raw_px"] * 1e4
    dA = per_session(D, t, "a60_pts")
    dB = per_session(D, t, "gross_pts", core.COST_RT_POINTS)
    h = RC.half_of(t["session"])
    out = {"label": label, "n": len(t),
           "A60": RC.daily_t(dA), "A60_halves": RC.by_half(dA),
           "A_other_bps": {H: float((t[f"a{H}_pts"] / t["raw_px"] * 1e4).mean()) for H in (15, 30, 60, 120)},
           "A60_R": float((t["a60_pts"] / t["risk"]).mean()),
           "B_net075_daily": RC.daily_t(dB),
           "B_gross_pts": float(t["gross_pts"].mean()),
           "B_net075_pts": float((t["gross_pts"] - 0.75).mean()), "B_net125_pts": float((t["gross_pts"] - 1.25).mean()),
           "B_net125_halves": {k: float((t["gross_pts"][h == k] - 1.25).mean()) for k in RC.HALVES},
           "B_R_gross": float((t["gross_pts"] / t["risk"]).mean()),
           "B_winrate": float((t["why"] == "target").mean()),
           "B_breakeven": float(((1 + 1.25 / t["risk"]) / 3).mean()),
           "exits": t["why"].value_counts().to_dict(),
           "B_years_net075": t.groupby(pd.DatetimeIndex(t["session"]).year)["gross_pts"].mean().sub(0.75).round(2).to_dict()}
    return out


if __name__ == "__main__":
    bars, daily = core.load("discovery", warmup_days=5)
    D = C.Data(bars, daily)
    od = C.orders(D)
    t = C.trades(D, od)
    t.to_parquet(core.CACHE / "r6_silverbullet_trades.parquet")
    S = summary(D, t, "primario")
    print(json.dumps(S, indent=1, default=str))

    rng = np.random.default_rng(6)
    pl = np.array([placebo(D, t, rng) for _ in range(N_PLAC)])
    pA_plac = RC.placebo_p(float((t["a60_pts"] / t["raw_px"] * 1e4).mean()), pl[:, 0])   # bps medi per trade
    pB_plac = RC.placebo_p(S["B_net075_pts"], pl[:, 1])
    S["placebo"] = {"A60_mean_bps_per_trade_real": float((t["a60_pts"] / t["raw_px"] * 1e4).mean()),
                    "A60_placebo_pct": [float(x) for x in np.percentile(pl[:, 0], [5, 50, 95])],
                    "p_A": pA_plac,
                    "B_net_pts_placebo_pct": [float(x) for x in np.percentile(pl[:, 1], [5, 50, 95])], "p_B": pB_plac}
    ph = RC.holm({"A": S["A60"]["p_pos"], "B": S["B_net075_daily"]["p_pos"]})
    S["holm"] = ph
    crit = RC.lab_criteria(bars, t[["session", "entry_ts", "exit_ts", "side", "gross_pts"]], alpha=0.025)
    S["lab_criteria_B"] = crit
    go = {"A_holm": ph["A"] < 0.05,
          "A_t1_both_halves": all(S["A60_halves"][k]["t"] >= 1 for k in RC.HALVES),
          "A_placebo95": pA_plac <= 0.05,
          "B_net125_both_halves": all(v > 0 for v in S["B_net125_halves"].values()),
          "B_winrate_above_breakeven": S["B_winrate"] > S["B_breakeven"],
          "lab_criteria": crit["pass"]}
    S["GO_checks"] = go
    S["GO"] = all(go.values())
    print(json.dumps({k: S[k] for k in ("placebo", "holm", "GO_checks", "GO")}, indent=1, default=str))
    print(json.dumps(crit, indent=1, default=str))
    core.record(FAM, "A60", "Silver Bullet segnale nudo 60 min, bps giornalieri (primario)", "discovery",
                S["A60"], halves=S["A60_halves"], placebo_p=pA_plac, holm_p=ph["A"])
    core.record(FAM, "B", "Silver Bullet geometria del repo, netto 0,75 bps giornalieri (primario)", "discovery",
                S["B_net075_daily"], net125_halves=S["B_net125_halves"], winrate=S["B_winrate"],
                breakeven=S["B_breakeven"], holm_p=ph["B"], lab_criteria=crit["crit"], GO=S["GO"])

    # sensibilita' (non decisive)
    sens = {}
    for lab_, kw in (("soglie_originali", {"fixed_thresholds": True}), ("fill_al_tocco", {"fill_touch": True})):
        ts = C.trades(D, C.orders(D, **kw))
        sens[lab_] = summary(D, ts, lab_)
    for w in C.WINDOWS:
        tw = t[t["window"] == w]
        sens["finestra_" + w] = summary(D, tw, w)
    for k, v in sens.items():
        print(k, "n", v["n"], "A60 bps/giorno", round(v["A60"]["mean"], 3), "t", round(v["A60"]["t"], 2),
              "B netto0,75 pt", round(v["B_net075_pts"], 2), "WR", round(v["B_winrate"], 3), "pareggio", round(v["B_breakeven"], 3))
        core.record(FAM, "sens_" + k, "sensibilita' (non decisiva)", "discovery", v["A60"], B_net075_pts=v["B_net075_pts"],
                    winrate=v["B_winrate"])
    (core.ROOT / "lab" / FAM / "results.json").write_text(json.dumps({"primary": S, "sens": sens}, indent=1, default=str),
                                                          encoding="utf-8")
