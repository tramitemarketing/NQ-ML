"""Controller del laboratorio: giudica i candidati congelati su validation o confirmation.

Uso (solo il controller):  LAB_CONTROLLER=1 python -m lab.controller validation [id1 id2 ...]
Criteri: lab/PROTOCOLLO.md §3-§5. Nessun parametro qui dentro dipende dai risultati.
"""
from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from lab import core

FAMILIES = ["intraday_momentum", "calendar", "multiday", "micro", "cross_session", "ml", "vol", "wild", "postval", "r2_range", "r2_costaware", "r2_execution", "r2_analog", "r2_autosearch", "r2_footprints", "r3_adaptive", "r4_implied", "r4_macro", "r5_amd"]
OUT = core.ROOT / "lab" / "verdicts"
DISCOVERY_SIGN = {  # regolarita' senza expected_sign: segno della media di discovery dichiarata dall'agente
    "intraday_momentum_rin_last30_gross": +1, "micro_surprise_continuation": +1,
    "cross_session_onrange_rthrange": +1, "cross_session_rth_to_evening": +1, "ml_rank30": +1,
}


def all_candidates() -> list[dict]:
    out = []
    for fam in FAMILIES:
        p = core.ROOT / "lab" / fam / "candidates.py"
        if not p.exists():
            continue
        mod = importlib.import_module(f"lab.{fam}.candidates")
        for c in getattr(mod, "CANDIDATES", []):
            c = dict(c)
            c["family"] = fam
            out.append(c)
    return out


def beta_component(bars: pd.DataFrame, trades: pd.DataFrame) -> np.ndarray:
    """Parte del P&L spiegata dalla deriva media per minuto del giorno nella fase: per ogni trade,
    side x somma, sui minuti tenuti, della variazione media di adj_close a quel minuto NY."""
    b = bars[bars["in_phase"]]
    r = b["adj_close"].diff().to_numpy().copy()
    r[0] = 0.0
    prof = pd.Series(r).groupby(b["ny_min"].to_numpy()).mean()
    mu = prof.reindex(b["ny_min"].to_numpy()).fillna(0.0).to_numpy()
    C = np.concatenate([[0.0], np.cumsum(mu)])
    idx = b.index
    i0 = idx.searchsorted(pd.DatetimeIndex(trades["entry_ts"]))      # barra d'ingresso (open)
    i1 = idx.searchsorted(pd.DatetimeIndex(trades["exit_ts"]))
    # ingresso all'open della barra i0: conta la deriva dalla barra i0 inclusa alla barra d'uscita esclusa
    return trades["side"].to_numpy() * (C[np.minimum(i1 + 1, len(idx))] - C[np.minimum(i0, len(idx))])


def judge(phase: str, cands: list[dict], k: int) -> list[dict]:
    years_needed = {"validation": 3, "confirmation": 2}[phase]
    alpha = 0.05 / k
    res = []
    cache: dict[int, tuple] = {}
    for c in cands:
        w = int(c.get("warmup_days", 0))
        if w not in cache:
            cache[w] = core.load(phase, warmup_days=w)
        bars, daily = cache[w]
        t = c["fn"](bars.copy(), daily.copy())
        t = t.copy()
        t["session"] = pd.to_datetime(t["session"])
        t = t[t["session"].isin(daily.index[daily["in_phase"]])]
        kind = c.get("kind", "tradeable")
        row = {"id": c["id"], "family": c["family"], "kind": kind, "phase": phase, "k": k, "alpha": alpha,
               "n": len(t)}
        if len(t) == 0:
            row["verdict"] = "FAIL (nessun trade)"
            res.append(row)
            continue
        gross = t["gross_pts"].to_numpy(float)
        if kind == "regularity":
            st = core.day_block_bootstrap(gross, t["session"].values)
            row.update(stat=st)
            # segno atteso: dichiarato, altrimenti quello del discovery (tutti +1, fissato prima della validazione)
            exp = c.get("expected_sign") or DISCOVERY_SIGN[c["id"]]
            row["expected_sign"] = exp
            sign_ok = np.sign(st["mean"]) == np.sign(exp)
            row["verdict"] = "PASS" if (st["p_two"] < alpha and sign_ok) else "FAIL"
        else:
            net = gross - core.COST_RT_POINTS
            beta = beta_component(bars, t)
            st = core.day_block_bootstrap(net, t["session"].values)
            st_b = core.day_block_bootstrap(net - beta, t["session"].values)
            yr = core.yearly(net, t["session"])
            if phase == "confirmation":
                yy = yr.copy()
                yy.index = [max(y, 2024) for y in yy.index]
                yr = pd.DataFrame({"sum": yy.groupby(level=0)["sum"].sum(), "count": yy.groupby(level=0)["count"].sum()})
                yr["mean"] = yr["sum"] / yr["count"]
            yrs_pos = int((yr["mean"] > 0).sum())
            dt20 = core.drop_top(net, 20)
            crit = {
                "c1_p": st["p_pos"] < alpha and st["mean"] > 0,
                "c2_beta": st_b["mean"] > 0 and st_b["p_pos"] < alpha,   # emendamento 1 (PROTOCOLLO §7)
                "c3_years": yrs_pos >= years_needed,
                "c4_droptop": dt20 > 0,
            }
            row.update(stat=st, stat_beta_adj=st_b, years=yr["mean"].round(3).to_dict(), years_pos=yrs_pos,
                       drop_top20=dt20, gross_mean=float(np.nanmean(gross)), crit=crit,
                       usd_per_trade=st["mean"] * core.POINT_USD)
            row["verdict"] = "PASS" if all(crit.values()) else "FAIL"
        res.append(row)
        print(json.dumps(row, default=str, ensure_ascii=False))
    return res


def main() -> None:
    phase = sys.argv[1]
    only = set(sys.argv[2:])
    cands = all_candidates()
    if only:
        cands = [c for c in cands if c["id"] in only]
    k = len(cands)
    print(f"[controller] fase={phase} K={k}: {[c['id'] for c in cands]}")
    res = judge(phase, cands, k)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{phase}.json").write_text(json.dumps(res, default=str, ensure_ascii=False, indent=1), encoding="utf-8")
    for r in res:
        core.record("controller", r["id"], f"verdetto {phase}", phase, r.get("stat", {}), verdict=r["verdict"])
    print("\n".join(f"{r['verdict']:<6} {r['id']}" for r in res))


if __name__ == "__main__":
    main()
