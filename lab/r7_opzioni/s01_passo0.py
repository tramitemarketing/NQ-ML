"""Passo 0 di r7_opzioni (PREREG.md): copertura, conteggi, spread e potenza. NESSUN rendimento di straddle.

Uso: .venv/Scripts/python.exe -m lab.r7_opzioni.s01_passo0
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
from scipy.stats import norm

from lab import core
from lab.r7_opzioni import common as OC
from lab.r7_quantili import common as Q

DIR = core.ROOT / "data" / "ext_paid" / "opzioni"
NY = "America/New_York"
PARENTS = ["NQ_OPT", "QN1_OPT", "QN2_OPT", "QN3_OPT", "QN4_OPT", "QN5_OPT"]


def load_defs() -> pd.DataFrame:
    d = pd.concat([pd.read_parquet(DIR / f"{p}_definition.parquet").assign(parent=p) for p in PARENTS])
    d = d[d["instrument_class"].isin(["C", "P"])].drop_duplicates("instrument_id", keep="last")
    d["exp_ny"] = pd.DatetimeIndex(d["expiration"]).tz_convert(NY)
    d["exp_date"] = d["exp_ny"].dt.tz_localize(None).dt.normalize()
    return d


def load_tbbo() -> pd.DataFrame:
    t = pd.concat([pd.read_parquet(DIR / f"{p}_tbbo.parquet") for p in PARENTS], ignore_index=True)
    t["ts"] = pd.DatetimeIndex(t["ts_recv"]).tz_convert(NY)
    return t.sort_values("ts")


def front_contract_ids() -> pd.Series:
    """instrument_id del future NQ.v.0 per ogni data (simbologia Databento usata da lab.core)."""
    m = json.load(open(core.CACHE / "nq_v0_mapping.json"))
    rows = []
    for seg in m:
        for d in pd.date_range(seg["d0"], pd.Timestamp(seg["d1"]) - pd.Timedelta(days=1)):
            rows.append((d, int(seg["s"])))
    return pd.Series(dict(rows))


def main() -> None:
    d = load_defs()
    t = load_tbbo()
    print(f"definizioni (call/put): {len(d):,}; righe tbbo: {len(t):,}")
    # 2. orario di scadenza e sottostante
    d["exp_hhmm"] = d["exp_ny"].dt.strftime("%H:%M")
    d["fam"] = np.where(d["parent"] == "NQ_OPT", "mensile/trimestrale", "settimanale")
    print("\norario di scadenza (NY) per famiglia:")
    print(d.groupby(["fam", "exp_hhmm"]).size().sort_values(ascending=False).head(12).to_string())
    print("\nscadenze per giorno della settimana:")
    dd = d.drop_duplicates(["exp_date", "fam"])
    print(dd.groupby(["fam", dd["exp_date"].dt.dayofweek]).size().to_string())

    bars, daily = core.load("discovery")
    rth = bars[bars["rth"]]
    c0944 = rth[rth["ny_min"] == 584].set_index("session")["close"]
    B = OC.build_days(bars, d, t)                    # stessa costruzione dei test (la colonna f_t NON si guarda)
    fri_exp = sorted({x for x in d["exp_date"].unique() if pd.Timestamp(x).dayofweek == 4
                      and pd.Timestamp(x) in set(pd.DatetimeIndex(daily.index))})
    P = pd.DataFrame(index=pd.DatetimeIndex(fri_exp, name="day"))
    P["usable"] = P.index.isin(B.index)
    P["spread_pct"] = (100 * (B["C_ask"] - B["C_bid"] + B["P_ask"] - B["P_bid"]) / B["mid"]).reindex(P.index)
    P["mid"] = B["mid"].reindex(P.index)
    P["n_series"] = 1
    P["und_front"] = np.nan
    y = P.groupby(P.index.year).agg(venerdi_con_scadenza=("n_series", "size"), utilizzabili=("usable", "sum"),
                                    spread_pct_mediano=("spread_pct", "median"), mid_mediano=("mid", "median"))
    print("\nPer anno (venerdì con scadenza NQ, discovery):")
    print(y.to_string())
    U = P[P["usable"] & (P.index >= pd.Timestamp("2012-01-01"))]
    n = len(U)
    print(f"\nvenerdì utilizzabili dal 2012 (anni di test): {n}")

    # 4. potenza: solo future. CV di |F_16:00 - F_09:45| rispetto al range RTH previsto (HAR + notte, stima su tutto il
    # discovery: per la potenza basta l'ordine di grandezza)
    tq = Q.table("discovery")
    A = np.column_stack([np.ones(len(tq)), tq[Q.HAR].to_numpy()])
    b, *_ = np.linalg.lstsq(A, tq["y"].to_numpy(), rcond=None)
    fc = np.exp(A @ b) / 100 * tq["rth_open"].to_numpy()                 # range previsto in punti (mediana)
    fri = tq.index.dayofweek == 4
    c1559 = rth[rth["ny_min"] == 959].set_index("session")["close"]
    mv = (c1559.reindex(tq.index) - c0944.reindex(tq.index)).abs().to_numpy()
    ratio = mv[fri] / fc[fri]
    ratio = ratio[np.isfinite(ratio)]
    cv = ratio.std(ddof=1) / ratio.mean()
    z = norm.ppf(1 - 0.05 / 2) + norm.ppf(0.80)                           # Holm k = 2
    mde_b = z * cv / np.sqrt(max(n, 1))                                   # P&L medio in frazione del mid
    print(f"CV di |movimento 09:45-16:00| / range previsto, venerdì: {cv:.3f} (n = {len(ratio)})")
    print(f"MDE80 di B (in % del mid dello straddle): {100 * mde_b:.1f} %  (effetto plausibile del PREREG: <= 5 %)")
    # MDE80 della pendenza di A: serve la dispersione di s = ln(previsione / mid), entrambi noti a t0 (non esiti)
    sU = np.log(OC.forecasts(U.index) / U["mid"]).dropna()
    mde_a = z * cv / (sU.std(ddof=1) * np.sqrt(max(len(sU), 1))) if len(sU) > 2 else np.inf
    print(f"sd(s) = {sU.std(ddof=1):.3f} su {len(sU)} venerdì; MDE80 della pendenza di A: {mde_a:.3f} "
          f"(effetto plausibile del PREREG: <= 0,15)")
    print(f"giorni utilizzabili: {n} (minimo del PREREG: 150)")
    core.record("r7_opzioni", "passo0", "Passo 0: copertura, spread, potenza (nessun rendimento di straddle)",
                "discovery", {"n_usable_2012_2018": n, "cv_move": float(cv), "mde80_B_frac_mid": float(mde_b),
                 "mde80_A_slope": float(mde_a)},
                per_anno=y.reset_index().to_dict(orient="records"))
    P.to_csv(DIR / "passo0_venerdi.csv")


if __name__ == "__main__":
    main()
