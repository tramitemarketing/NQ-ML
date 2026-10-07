"""Confronto appaiato tra due esecuzioni sugli stessi eventi (spec §12-bis): Brier per evento, R medio dei trade presi, decisioni."""
from __future__ import annotations

import pandas as pd

from nqml.backtest.engine import taken
from nqml.backtest.metrics import block_bootstrap_ci, diff_mean_r_stat, per_day_table

PAIR_COLS = ["p", "p_context", "p_rw", "ev_r", "take_A", "realized_R", "pnl_usd"]
COMMON = ["event_id", "session_date", "fold", "label", "entry_ts", "exit_ts"]


def paired_frame(pred_a: pd.DataFrame, pred_b: pd.DataFrame) -> pd.DataFrame:
    """Una riga per evento con le colonne di entrambe le esecuzioni (suffissi _a/_b). Rifiuta se gli insiemi di
    eventi differiscono, se un event_id e' duplicato o se le label non coincidono evento per evento."""
    if set(pred_a["event_id"]) != set(pred_b["event_id"]):
        raise ValueError("le due esecuzioni non coprono gli stessi eventi: confronto appaiato impossibile")
    if pred_a["event_id"].duplicated().any() or pred_b["event_id"].duplicated().any():
        raise ValueError("event_id duplicati: il confronto appaiato richiede una riga per evento")
    a = pred_a[COMMON + PAIR_COLS].rename(columns={c: f"{c}_a" for c in PAIR_COLS})
    b = pred_b[["event_id", "label"] + PAIR_COLS].rename(columns={c: f"{c}_b" for c in PAIR_COLS} | {"label": "label_b"})
    pf = a.merge(b, on="event_id", how="inner")
    if not (pf["label"].to_numpy() == pf["label_b"].to_numpy()).all():
        raise ValueError("le label differiscono tra le due esecuzioni per uno o piu' eventi: confronto appaiato impossibile")
    return pf.drop(columns=["label_b"])


def brier_per_day(pf: pd.DataFrame, col_b: str, col_a: str) -> pd.DataFrame:
    y = pf["label"].to_numpy(dtype=float)
    d = (pf[col_b].to_numpy(dtype=float) - y) ** 2 - (pf[col_a].to_numpy(dtype=float) - y) ** 2
    t = pd.DataFrame({"session_date": pf["session_date"].to_numpy(), "d": d})
    g = t.groupby("session_date")
    return pd.DataFrame({"d_sum": g["d"].sum(), "n": g.size()})


def paired_brier_ci(pf: pd.DataFrame, col_b: str, col_a: str, n_boot: int, seed: int, alpha: float = 0.05) -> dict:
    tab = brier_per_day(pf, col_b, col_a)
    stat = lambda t: float(t["d_sum"].sum() / t["n"].sum())
    return {"point": stat(tab), "ci": block_bootstrap_ci(tab, stat, n_boot, seed, alpha=alpha)}


def _as_pred(pf: pd.DataFrame, suffix: str) -> pd.DataFrame:
    cols = {f"{c}_{suffix}": c for c in PAIR_COLS}
    return pf[COMMON + list(cols)].rename(columns=cols)


def paired_mean_r(pf: pd.DataFrame, days, n_boot: int, seed: int) -> dict:
    ta, tb = taken(_as_pred(pf, "a"), "take_A"), taken(_as_pred(pf, "b"), "take_A")
    tab = per_day_table({"A": ta, "B": tb}, list(days))
    point = diff_mean_r_stat("B", "A")(tab)
    return {"point": float(point), "ci": block_bootstrap_ci(tab, diff_mean_r_stat("B", "A"), n_boot, seed), "n_a": int(len(ta)), "n_b": int(len(tb))}


def decision_overlap(pf: pd.DataFrame) -> dict:
    a, b = pf["take_A_a"].to_numpy(bool), pf["take_A_b"].to_numpy(bool)
    both, only_a, only_b = int((a & b).sum()), int((a & ~b).sum()), int((~a & b).sum())
    union = both + only_a + only_b
    return {"jaccard": both / union if union else float("nan"), "only_a": only_a, "only_b": only_b, "both": both}


def evaluate_paired_criteria(cmp: dict, fraction: float, n_A_b: int) -> list[dict]:
    ba, brw, mr = cmp["brier_b_vs_a"], cmp["brier_b_vs_rw"], cmp["mean_r"]
    need = 300 * fraction
    return [
        dict(id="i", text="Brier(A_1b) − Brier(A_1a_S) per evento: CI esclude 0, negativa", passed=bool(ba["ci"][1] < 0),
             evidence=f"{ba['point']:+.4f} [{ba['ci'][0]:+.4f}, {ba['ci'][1]:+.4f}]"),
        dict(id="ii", text="Brier(A_1b) − Brier(prior geometrico) per evento: CI esclude 0, negativa", passed=bool(brw["ci"][1] < 0),
             evidence=f"{brw['point']:+.4f} [{brw['ci'][0]:+.4f}, {brw['ci'][1]:+.4f}]"),
        dict(id="iii", text="R medio(A_1b) − R medio(A_1a_S) appaiato per giorno: CI esclude 0, positiva", passed=bool(mr["ci"][0] > 0),
             evidence=f"{mr['point']:+.3f} [{mr['ci'][0]:+.3f}, {mr['ci'][1]:+.3f}] (n {mr['n_b']} vs {mr['n_a']})"),
        dict(id="iv", text=f"A_1b prende ≥ 300 · quota trade OOS (= {need:.0f})", passed=bool(n_A_b >= need), evidence=f"{n_A_b} trade"),
    ]


def render_comparison(cmp: dict, tag_a: str, tag_b: str) -> str:
    L = [f"## Confronto appaiato {tag_b} − {tag_a} (stessi eventi, stesse pieghe)\n",
         "| finestra | AUC A_a | AUC A_b | AUC prior | Brier A_a | Brier A_b | Brier prior |", "|---|---|---|---|---|---|---|"]
    for r in cmp["by_fold"]:
        L.append(f"| {r['fold']} | {r['auc_a']:.4f} | {r['auc_b']:.4f} | {r['auc_rw']:.4f} | {r['brier_a']:.4f} | {r['brier_b']:.4f} | {r['brier_rw']:.4f} |")
    ov = cmp["overlap"]
    L += ["", f"- Brier per evento, {tag_b} − {tag_a}: **{cmp['brier_b_vs_a']['point']:+.4f}** [{cmp['brier_b_vs_a']['ci'][0]:+.4f}, {cmp['brier_b_vs_a']['ci'][1]:+.4f}]",
          f"- Brier per evento, {tag_b} − prior geometrico: **{cmp['brier_b_vs_rw']['point']:+.4f}** [{cmp['brier_b_vs_rw']['ci'][0]:+.4f}, {cmp['brier_b_vs_rw']['ci'][1]:+.4f}]"]
    if cmp.get("brier_a_vs_rw") is not None:
        v = cmp["brier_a_vs_rw"]
        L.append(f"- Brier per evento, {tag_a} − prior geometrico: **{v['point']:+.4f}** [{v['ci'][0]:+.4f}, {v['ci'][1]:+.4f}]")
    if cmp.get("brier_b_vs_context") is not None:
        v = cmp["brier_b_vs_context"]
        L.append(f"- Brier per evento, {tag_b} − solo-contesto: **{v['point']:+.4f}** [{v['ci'][0]:+.4f}, {v['ci'][1]:+.4f}]")
    if cmp.get("brier_a_vs_context") is not None:
        v = cmp["brier_a_vs_context"]
        L.append(f"- Brier per evento, {tag_a} − solo-contesto: **{v['point']:+.4f}** [{v['ci'][0]:+.4f}, {v['ci'][1]:+.4f}]")
    L += [f"- R medio dei trade presi, {tag_b} − {tag_a}: **{cmp['mean_r']['point']:+.3f}** [{cmp['mean_r']['ci'][0]:+.3f}, {cmp['mean_r']['ci'][1]:+.3f}] (n {cmp['mean_r']['n_b']} vs {cmp['mean_r']['n_a']})",
          f"- Decisioni: Jaccard {ov['jaccard']:.3f} · entrambe {ov['both']} · solo {tag_a} {ov['only_a']} · solo {tag_b} {ov['only_b']}", ""]
    if "criteria" in cmp:
        L += ["| # | criterio appaiato | esito | evidenza |", "|---|---|---|---|"]
        L += [f"| {c['id']} | {c['text']} | {'PASS' if c['passed'] else 'FAIL'} | {c['evidence']} |" for c in cmp["criteria"]]
    return "\n".join(L) + "\n"
