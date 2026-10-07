"""Criteri pre-registrati dello sguardo #3 (spec §12-ter): G1, P1, S1, G2 su bootstrap per giorno."""
from __future__ import annotations

import numpy as np
import pandas as pd

from nqml.report.compare import paired_brier_ci


def _verdict(ci95: tuple, ci99: tuple) -> str:
    if ci99[1] < 0:
        return "confermato"
    if ci95[1] < 0:
        return "candidato"
    return "FAIL"


def evaluate_1c(pred_a: pd.DataFrame, pred_b: pd.DataFrame, pred_a1: pd.DataFrame, sampled_days: pd.DataFrame,
                n_boot: int, seed: int) -> dict:
    for name, df in (("A", pred_a), ("B", pred_b), ("A'", pred_a1)):
        if df["event_id"].duplicated().any():
            raise ValueError(f"{name}: event_id duplicati")
    if not (set(pred_a["event_id"]) == set(pred_b["event_id"]) == set(pred_a1["event_id"])):
        raise ValueError("i tre bracci non coprono gli stessi eventi")
    a = pred_a.set_index("event_id")
    b = pred_b.set_index("event_id").reindex(a.index)
    a1 = pred_a1.set_index("event_id").reindex(a.index)
    if not (a["label"].to_numpy() == b["label"].to_numpy()).all() or not (a["label"].to_numpy() == a1["label"].to_numpy()).all():
        raise ValueError("label diverse tra i bracci")
    keep = set(pd.to_datetime(sampled_days["session_date"]).dt.date)
    in_s = pd.to_datetime(a["session_date"]).dt.date.isin(keep).to_numpy()

    fa = a.reset_index()
    g1 = paired_brier_ci(fa, "p", "p_rw", n_boot, seed)                       # A contro il prior grezzo L1
    p1_95 = paired_brier_ci(fa, "p", "p_l2", n_boot, seed)                    # A contro il prior calibrato L2
    p1_99 = paired_brier_ci(fa, "p", "p_l2", n_boot, seed, alpha=0.01)
    pf = fa[["event_id", "session_date", "label", "p"]].rename(columns={"p": "p_a"})
    pf["p_b"] = b["p"].to_numpy()
    pf_s = pf[in_s]
    s1_95 = paired_brier_ci(pf_s, "p_b", "p_a", n_boot, seed)
    s1_99 = paired_brier_ci(pf_s, "p_b", "p_a", n_boot, seed, alpha=0.01)
    non_s = ~in_s
    med_ab = float(np.median(np.abs(b["p"].to_numpy()[non_s] - a["p"].to_numpy()[non_s])))
    med_aa1 = float(np.median(np.abs(a1["p"].to_numpy()[non_s] - a["p"].to_numpy()[non_s])))
    g2 = {"median_b_vs_a": med_ab, "median_a_vs_a1": med_aa1, "passed": bool(med_ab <= 2 * med_aa1)}

    if g1["ci"][0] > 0:
        verdict_p1 = "invalido"                                               # A peggio del prior grezzo: pipeline sotto sospetto
    else:
        verdict_p1 = _verdict(p1_95["ci"], p1_99["ci"])
    if verdict_p1 in ("FAIL", "invalido"):
        verdict_s1 = "non letto"
    elif not g2["passed"]:
        verdict_s1 = "invalido"
    else:
        verdict_s1 = _verdict(s1_95["ci"], s1_99["ci"])
    return dict(g1=g1, p1_95=p1_95, p1_99=p1_99, s1_95=s1_95, s1_99=s1_99, g2=g2,
                verdict_p1=verdict_p1, verdict_s1=verdict_s1,
                n_all=int(len(a)), n_s=int(in_s.sum()), n_non_s=int(non_s.sum()),
                brier=dict(A=float(np.mean((a["p"] - a["label"]) ** 2)), B_s=float(np.mean((b["p"][in_s] - b["label"][in_s]) ** 2)),
                           A_s=float(np.mean((a["p"][in_s] - a["label"][in_s]) ** 2)),
                           L1=float(np.mean((a["p_rw"] - a["label"]) ** 2)), L2=float(np.mean((a["p_l2"] - a["label"]) ** 2))))


def _ci(d: dict) -> str:
    return f"{d['point']:+.4f} [{d['ci'][0]:+.4f}, {d['ci'][1]:+.4f}]"


def _g2_esito(verdict_s1: str, verdict_p1: str = "FAIL") -> str:
    if verdict_s1 == "non letto":
        return f"S1 non letto (P1 {verdict_p1})"
    if verdict_s1 == "invalido":
        return "S1 invalido"
    return "S1 valido"


def render_1c(res: dict, shuffle_a: list[float], shuffle_b: list[float],
              shuffle_fixed_a: list[float] | None = None, shuffle_fixed_b: list[float] | None = None) -> str:
    L = ["## Sguardo #3 — criteri pre-registrati (spec §12-ter)\n",
         f"Eventi: {res['n_all']} totali · S {res['n_s']} · non-S {res['n_non_s']}. Brier pooled: L1 {res['brier']['L1']:.4f} · "
         f"L2 {res['brier']['L2']:.4f} · A {res['brier']['A']:.4f} · su S: A {res['brier']['A_s']:.4f}, B {res['brier']['B_s']:.4f}.\n",
         "| # | criterio | evidenza | esito |", "|---|---|---|---|",
         f"| G1 | Brier(A) − Brier(L1), n {res['n_all']} | {_ci(res['g1'])} | {'invalido' if res['verdict_p1'] == 'invalido' else 'valido'} |",
         f"| P1 | Brier(A) − Brier(L2), n {res['n_all']} | 95 %: {_ci(res['p1_95'])} · 99 %: {_ci(res['p1_99'])} | **{res['verdict_p1']}** |",
         f"| S1 | Brier(B) − Brier(A) su S, n {res['n_s']} | 95 %: {_ci(res['s1_95'])} · 99 %: {_ci(res['s1_99'])} | **{res['verdict_s1']}** |",
         f"| G2 | mediana \\|p_B − p_A\\| sui non-S {res['g2']['median_b_vs_a']:.5f} ≤ 2 × mediana \\|p_A − p_A′\\| {res['g2']['median_a_vs_a1']:.5f} | "
         f"{'PASS' if res['g2']['passed'] else 'FAIL'} | {_g2_esito(res['verdict_s1'], res['verdict_p1'])} |",
         f"\nShuffle AUC (media di 5 seed sui soli alberi) — A per piega: {[round(x, 3) for x in shuffle_a]} · B: {[round(x, 3) for x in shuffle_b]}\n"]
    if shuffle_fixed_a is not None and shuffle_fixed_b is not None:
        L.append(
            "Variante a offset fisso (registrazione originaria, solo riportata; §12-ter emendato il 2026-09-22): "
            f"A per piega {[round(x, 3) for x in shuffle_fixed_a]} · B {[round(x, 3) for x in shuffle_fixed_b]} — "
            "anti-correlata per costruzione (gli alberi cancellano l'offset), nessuna banda applicata.\n"
        )
    if res.get("mean_r_b_vs_a") is not None and res.get("overlap") is not None:
        mr, ov = res["mean_r_b_vs_a"], res["overlap"]
        L.append(
            "Descrittivi (nessun verdetto) — "
            f"R medio B − A appaiato per giorno: {mr['point']:+.3f} [{mr['ci'][0]:+.3f}, {mr['ci'][1]:+.3f}] "
            f"(n {mr['n_b']} vs {mr['n_a']}) · decisioni: Jaccard {ov['jaccard']:.3f} · entrambe {ov['both']} · "
            f"solo A {ov['only_a']} · solo B {ov['only_b']}\n"
        )
    if res["verdict_p1"] == "FAIL":
        if res["p1_95"]["point"] < 0:
            L.append(
                f"Lettura pre-registrata: P1 FAIL con stima negativa ({res['p1_95']['point']:+.4f}): l'informazione oltre L2, "
                "se c'è, è sotto la soglia di rilevabilità a questa n (potenza dichiarata 20–50 %); il falsificatore "
                "pre-registrato (stima ≥ +0.0005) NON è scattato; il forward test NON si attiva (richiede P1 ≥ candidato); "
                "L2 resta il modello di riferimento; S1 non letto.\n"
            )
        else:
            L.append(
                f"Lettura pre-registrata: P1 FAIL con stima ≥ 0 ({res['p1_95']['point']:+.4f}): nessuna informazione "
                "rilevabile oltre la geometria calibrata a questa n; il forward test NON si attiva (richiede P1 ≥ "
                "candidato); L2 resta il modello di riferimento; S1 non letto.\n"
            )
    else:
        L.append(
            "Lettura pre-registrata: candidato/confermato → replica su cassaforte o forward test prima di qualsiasi uso; "
            "S1 si legge solo se P1 ≥ candidato.\n"
        )
    return "\n".join(L)
