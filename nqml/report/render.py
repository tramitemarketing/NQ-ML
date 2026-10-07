"""Report OOS (spec §10–§11): tabelle con CI, criteri pre-registrati con PASS/FAIL, stress, sanity, figure."""
from __future__ import annotations

import datetime as dt
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from nqml.config import config_hash, git_commit
from nqml.features.build import feature_set


def evaluate_criteria(res: dict) -> list[dict]:
    lo, hi = res["ci_A"]
    c1 = res["mean_R_A"] > 0 and lo > 0 and res["mean_R_A_slip2"] > 0
    diffs_ok = all(res["diff_ci"][k][0] > 0 for k in ("B0", "C", "Copt"))
    pos_folds = sum(1 for v in res["fold_signs"].values() if v > 0)
    c3 = pos_folds >= 4
    shuffle_ok = all(0.45 <= a <= 0.55 for a in res["shuffle_aucs"])
    n_folds = len(res["fold_signs"])
    bvc = res.get("brier_A_vs_context")
    if bvc is not None:
        # spec §11.1 «dalla 1b»: bootstrap appaiato per evento di Brier(A) − Brier(contesto), CI che esclude 0.
        pt, ci = bvc["point"], bvc["ci"]
        brier_ok = ci[1] < 0
        verdict = "A peggio del solo-contesto" if pt > 0 else "A meglio del solo-contesto"
        c4_evidence = (
            f"shuffle AUC {[round(a, 3) for a in res['shuffle_aucs']]}; "
            f"Brier(A) − Brier(contesto) per evento (bootstrap appaiato per giorno): {pt:+.4f} [{ci[0]:+.4f}, {ci[1]:+.4f}] "
            f"— {verdict} (Brier medio-per-fold a vs b: A {res['brier_A_mean']:.4f}, contesto {res['brier_context_mean']:.4f}); "
            f"pooled A {res['brier_A_pooled']:.4f} vs prior geometrico {res['brier_rw_pooled']:.4f}"
        )
    else:
        brier_ok = res["brier_A_mean"] < res["brier_context_mean"]
        verdict = "A peggio del solo-contesto" if res["brier_A_mean"] > res["brier_context_mean"] else "A meglio del solo-contesto"
        c4_evidence = (
            f"shuffle AUC {[round(a, 3) for a in res['shuffle_aucs']]}; "
            f"Brier medio-per-fold a vs b: A {res['brier_A_mean']:.4f} vs contesto {res['brier_context_mean']:.4f} "
            f"— {verdict} (A meglio in {res['brier_folds_A_better']}/{n_folds} finestre); "
            f"pooled A {res['brier_A_pooled']:.4f} vs prior geometrico {res['brier_rw_pooled']:.4f}"
        )
    c4 = shuffle_ok and brier_ok
    # M3d (§12-ter riga D): per i bracci con order-flow su un sottoinsieme campionato, la soglia dei trade e' 300 *
    # quota, non 300 (le feature tick esistono solo sui giorni campionati) — res["trade_threshold"] la porta da 07.
    threshold = res.get("trade_threshold", 300)
    frac = res.get("trade_threshold_fraction")
    c5 = res["n_A"] >= threshold
    if frac is not None:
        c5_text = f"A prende ≥ 300 · quota (= {threshold:.0f}) trade OOS (§12-ter: le feature tick esistono solo sui giorni campionati)"
        c5_evidence = f"{res['n_A']} trade — soglia 300 · {frac:.3f} = {threshold:.0f} (§12-ter: le feature tick esistono solo sui giorni campionati)"
    else:
        c5_text = "A prende ≥ 300 trade OOS"
        c5_evidence = f"{res['n_A']} trade"
    return [
        dict(id=1, text="A: R medio/trade > 0 dopo costi, CI esclude 0, a 1 tick; ancora > 0 a 2 tick", passed=bool(c1),
             evidence=f"R medio {res['mean_R_A']:.3f} [{lo:.3f}, {hi:.3f}]; a 2 tick {res['mean_R_A_slip2']:.3f}"),
        dict(id=2, text="(A − B0), (A − C), (A − C-opt) > 0 su R medio/trade, CI esclude 0", passed=bool(diffs_ok),
             evidence="; ".join(f"A−{k}: [{v[0]:.3f}, {v[1]:.3f}]" for k, v in res["diff_ci"].items())),
        dict(id=3, text="segno positivo di (A − B0) in ≥ 4 finestre su 5", passed=bool(c3),
             evidence=f"{pos_folds}/{n_folds} finestre: " + ", ".join(f"{k}: {v:+.3f}" for k, v in res["fold_signs"].items())),
        dict(id=4, text="shuffle test AUC ∈ [0.45, 0.55]; A batte il solo-contesto su Brier", passed=bool(c4),
             evidence=c4_evidence),
        dict(id=5, text=c5_text, passed=bool(c5), evidence=c5_evidence),
    ]


def _fmt(v, nd=3):
    if v is None or (isinstance(v, float) and (np.isnan(v))):
        return "n/d"
    if isinstance(v, float) and np.isinf(v):
        return "∞"
    return f"{v:.{nd}f}" if isinstance(v, float) else str(v)


def _table(headers: list[str], rows: list[list]) -> str:
    out = ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
    out += ["| " + " | ".join(_fmt(c) for c in r) + " |" for r in rows]
    return "\n".join(out)


def render_report(res: dict, cfg: dict) -> str:
    tag = res.get("tag", cfg["features"]["version"])
    version_label = res.get("version", cfg["features"]["version"])
    L = [f"# Report OOS — {tag}\n",
         f"Generato il {dt.date.today().isoformat()} · config `{config_hash('config.yaml')}` · commit `{git_commit()}` · "
         f"feature `{version_label}` · cassaforte dal {cfg['vault']['start']} **mai usata**\n"]
    if feature_set(res.get("version", cfg["features"]["version"]))["has_orderflow"]:
        L.append("Nota: **C ha 3 regole** (`vol_slope_excursion < 0`, `vol_reentry_bar > 1`, `delta_excursion > 0`), come da spec §9.2.\n")
        if tag.startswith("1c") and res.get("tick_nan_test") is not None:
            # M3e: su 1c_B le feature order-flow esistono solo sui giorni campionati (S) — vanno NaN altrove.
            L.append(
                f"Nota: le 3 feature order flow sono NaN su {res['tick_nan_test']} dei {res['n_test_total']} eventi di test "
                "(giorni non campionati): il modello B usa la direzione di default degli split fuori da S; le regole C con "
                "`delta_excursion` scattano solo su S.\n"
            )
    else:
        # M3b: la frase e' ereditata dalla 1a — per una feature-version diversa va detto che le 2 regole sono le
        # stesse della 1a (1a_S resta "versione 1a" sotto un tag diverso: il testo non cambia per quella).
        c2_label = "C in 1a ha 2 regole" if version_label == "1a" else f"C in {tag} ha 2 regole (le stesse della 1a)"
        L.append(
            f"Nota: **{c2_label}** (`vol_slope_excursion < 0` e `vol_reentry_bar > 1`); la terza regola della spec "
            "(`delta_excursion > 0`) richiede i tick e arriva in 1b. Tutte le cifre sono calcolate da "
            f"`data/model/predictions_{tag}.parquet`; CI 95% block-bootstrap per giorno.\n"
        )
    crit = evaluate_criteria(res)
    L.append("## Criteri pre-registrati (spec §11.1)\n")
    L.append(_table(["#", "criterio", "esito", "evidenza"], [[c["id"], c["text"], "PASS" if c["passed"] else "FAIL", c["evidence"]] for c in crit]))
    n_pass = sum(c["passed"] for c in crit)
    # M3c: al terzo sguardo la "regola dei tre sguardi" e' gia' esaurita — il prossimo passo e' l'ipotesi pre-registrata.
    next_step = "Prossimo passo secondo la regola dei tre sguardi."
    if tag.startswith("1c"):
        next_step += " (questo è il terzo: dal prossimo serve l'ipotesi pre-registrata)"
    L.append(f"\n**{n_pass}/5 criteri superati.** " + ("Si apre la cassaforte per la conferma finale (decisione dell'utente)." if n_pass == 5
             else f"Il modello {tag} non supera i criteri: il report dice quali. {next_step}") + "\n")
    if res.get("notes_md"):
        L.append("\n## Note sulla milestone\n")
        L.append(res["notes_md"].strip() + "\n")
    L.append("\n## Come leggere questo report\n")
    st = res.get("stress")
    drop_row = st[st["name"].str.startswith("drop_top")] if st is not None else None
    drop_mean_r = float(drop_row["mean_R"].iloc[0]) if drop_row is not None and len(drop_row) else None
    fold_signs_txt = ", ".join(f"{k}: {v:+.3f}" for k, v in res["fold_signs"].items())
    bvc = res.get("brier_A_vs_context")
    if bvc is not None:
        pt, ci = bvc["point"], bvc["ci"]
        verdict = "peggio" if pt > 0 else "meglio"
        brier_bullet = (
            f"La clausola Brier del criterio 4 (spec §11.1 «dalla 1b»): bootstrap appaiato per evento di Brier(A) − "
            f"Brier(contesto) = {pt:+.4f} [{ci[0]:+.4f}, {ci[1]:+.4f}] — A {verdict} del solo-contesto (Brier "
            f"medio-per-fold a vs b: A {_fmt(res.get('brier_A_mean'), 4)}, contesto {_fmt(res.get('brier_context_mean'), 4)}, "
            f"A meglio in {res.get('brier_folds_A_better', 'n/d')}/{len(res['fold_signs'])} finestre); pooled A "
            f"{_fmt(res.get('brier_A_pooled'), 4)} vs prior geometrico {_fmt(res.get('brier_rw_pooled'), 4)}."
        )
    else:
        verdict = "peggio" if res.get('brier_A_mean', 0) > res.get('brier_context_mean', 0) else "meglio"
        brier_bullet = (
            f"Il criterio 4 confronta Brier medio-per-fold a vs b: A {_fmt(res.get('brier_A_mean'), 4)} vs contesto "
            f"{_fmt(res.get('brier_context_mean'), 4)} — A {verdict} del solo-contesto (A meglio in "
            f"{res.get('brier_folds_A_better', 'n/d')}/{len(res['fold_signs'])} finestre); pooled A "
            f"{_fmt(res.get('brier_A_pooled'), 4)} vs prior geometrico {_fmt(res.get('brier_rw_pooled'), 4)}."
        )
    mean_r_a = res.get("mean_R_A")
    if mean_r_a is not None and mean_r_a >= 0:
        r_bullet = (
            f"L'R medio positivo di A è portato da pochi trade: nello stress che toglie il 5% dei trade migliori, R medio "
            f"crolla a {_fmt(drop_mean_r)}; e il segno di (A − B0) cambia da finestra a finestra ({fold_signs_txt})."
        )
    else:
        r_bullet = (
            f"L'R medio di A è negativo ({_fmt(mean_r_a, 3)}): nello stress che toglie il 5% dei trade migliori, R medio "
            f"scende a {_fmt(drop_mean_r)}; e il segno di (A − B0) cambia da finestra a finestra ({fold_signs_txt})."
        )
    bullets = [
        f"L'AUC di A ({_fmt(res.get('auc_A_pooled'), 4)}, pooled) è quasi tutta geometria dello stop/target, non skill del "
        f"modello: il prior a zero parametri `p = 1/(1+rr_ratio)` fa {_fmt(res.get('auc_rw_pooled'), 4)} — la differenza è "
        "nel rumore.",
        brier_bullet,
        r_bullet,
        "Sharpe giornaliero e mesi negativi/totali sono calcolati su TUTTI i giorni/mesi di test, non solo su quelli con "
        "trade: un giorno o un mese senza trade pesa 0, non manca dal conteggio (vedi nota I1 della review).",
        "Lo stress `slip_N` applica N tick di slippage per lato sull'ingresso e su **ogni** uscita a mercato (stop, "
        "time-stop) — più severo del solo \"sugli stop\" della bozza; il target resta un ordine limite (nessuno "
        "slippage). Un'uscita per gap-through-stop nella stessa barra è valorizzata al livello dello stop (ottimistico); "
        "`slip_3` è la proxy più vicina a un mercato che apre in gap.",
        "C-opt cerca le due soglie a griglia sul training di ogni finestra (in-sample per quella finestra): è un limite "
        "superiore ottimistico su quanto le regole potrebbero rendere, non una strategia eseguibile fuori dal backtest.",
        "La riga \"A su MNQ (÷10)\" è una divisione ingenua per 10: commissioni e tick di MNQ non scalano linearmente "
        "con quelli di NQ, quindi la riga sottostima i costi reali su MNQ.",
    ]
    if res.get("fraction") is not None:
        frac = res["fraction"]
        bullets.append(
            f"Esecuzione su un sottoinsieme campionato (quota effettiva {frac:.4f} dei giorni di popolazione): solo "
            f"quei giorni possono avere trade, quindi `trades_per_day` e `pct_days_active` sono diluiti di circa "
            f"1/{frac:.3f} ≈ {1 / frac:.2f}× rispetto a un'esecuzione su tutti i giorni, e lo Sharpe giornaliero di "
            f"circa √{frac:.3f} ≈ {frac ** 0.5:.2f}× rispetto a un'esecuzione sull'intera popolazione."
        )
    L.append("\n".join(f"- {b}" for b in bullets) + "\n")
    if res.get("comparison_md"):
        L.append("\n" + res["comparison_md"])
    if res.get("summary"):
        L.append("## Le quattro colonne (OOS aggregato, 5 finestre)\n")
        keys = ["n", "trades_per_day", "win_rate", "mean_R", "ci", "profit_factor", "expectancy_usd", "max_dd_R", "max_dd_usd", "sharpe_daily", "months"]
        rows = []
        for name, s in res["summary"].items():
            ci = res.get("ci", {}).get(name, (np.nan, np.nan))
            rows.append([name, s["n"], s["trades_per_day"], s["win_rate"], s["mean_R"], f"[{_fmt(ci[0])}, {_fmt(ci[1])}]", s["profit_factor"],
                         s["expectancy_usd"], s["max_dd_R"], s["max_dd_usd"], s["sharpe_daily"], f"{s['months_negative']}/{s['months_total']}"])
        sA = res["summary"].get("A")
        if sA:
            rows.append(["A su MNQ (÷10)", sA["n"], sA["trades_per_day"], sA["win_rate"], sA["mean_R"], "", sA["profit_factor"],
                         sA["expectancy_usd"] / 10, sA["max_dd_R"], sA["max_dd_usd"] / 10, sA["sharpe_daily"], f"{sA['months_negative']}/{sA['months_total']}"])
        L.append(_table(["strategia"] + keys, rows))
        L.append("\n### Differenze su R medio/trade (CI 95%)\n")
        L.append(_table(["confronto", "stima", "CI"], [[f"A − {k}", v["point"], f"[{_fmt(v['ci'][0])}, {_fmt(v['ci'][1])}]"] for k, v in res["diffs"].items()]))
        L.append("\n### Segno di (A − B0) per finestra\n")
        L.append(_table(["finestra", "test", "A − B0 (R medio)"], [[k, res["folds"][k], v] for k, v in res["fold_signs"].items()]))
        L.append("\n### Motore: esiti per strategia\n")
        L.append(_table(["strategia", "taken", "duplicate", "skipped_in_position", "not_taken"],
                        [[k, v.get("taken", 0), v.get("duplicate", 0), v.get("skipped_in_position", 0), v.get("not_taken", 0)] for k, v in res["engine_counts"].items()]))
    if res.get("stress") is not None:
        L.append("\n## Stress su A (decisioni fisse a 1 tick, P&L rivalutato; slippage per lato: ingresso e ogni "
                  "uscita a mercato; target = limite)\n")
        st = res["stress"]
        L.append(_table(["scenario", "n", "win rate", "R medio", "PF", "expectancy $", "max DD R"],
                        [[r["name"], r["n"], r["win_rate"], r["mean_R"], r["profit_factor"], r["expectancy_usd"], r["max_dd_R"]] for r in st.to_dict("records")]))
    if res.get("sanity"):
        L.append("\n## Controlli anti-inganno per finestra\n")
        prior_by_fold = res.get("prior", {}).get("by_fold", {})
        L.append(_table(["finestra", "test", "AUC A", "Brier A", "Brier contesto", "AUC shuffle", "AUC prior", "Brier prior", "n feature A", "best iter", "C-opt"],
                        [[s["fold"], f"{s['test_start']}..{s['test_end']}", s["auc_A"], s["brier_A"], s["brier_context"], s["auc_shuffle"],
                          prior_by_fold.get(s["fold"], {}).get("auc_rw"), prior_by_fold.get(s["fold"], {}).get("brier_rw"),
                          len(s["features_A"]), s["best_iteration"], str(s["c_opt_params"])] for s in res["sanity"]]))
        l2_frag = f" · L2 (prior calibrato sul training) {res['brier_l2_pooled']:.4f}" if res.get("brier_l2_pooled") is not None else ""
        L.append(
            f"\nPrior geometrico p = 1/(1+rr): AUC {_fmt(res.get('auc_rw_pooled'), 4)} vs A {_fmt(res.get('auc_A_pooled'), 4)} "
            f"(pooled); Brier prior {_fmt(res.get('brier_rw_pooled'), 4)} vs A {_fmt(res.get('brier_A_pooled'), 4)} (pooled); "
            f"Brier tasso base {_fmt(res.get('brier_base_pooled'), 4)}{l2_frag}\n"
        )
    if res.get("calib") is not None:
        L.append("\n## Calibrazione (decili di p, tutti gli eventi di test)\n")
        sanity_folds = res.get("sanity") or []
        if sanity_folds and all(s.get("n_val_cal") == 0 and "l2_a" in s for s in sanity_folds):
            # M3b: per i modelli a offset (1c) non c'e' calibratore post hoc — la tabella e' comunque valida
            # (affidabilita' di p), ma va detto che qui non c'e' isotonica su meta' validazione come in 1a/1b.
            L.append("\nModalità offset (§12-ter): nessun calibratore post hoc, validazione intera per early stopping.\n")
        L.append(_table(["decile", "p media", "freq. osservata", "n"], res["calib"]))
    if res.get("decomposition"):
        L.append("\n## Decomposizione dei trade A (solo lettura, mai per selezionare)\n")
        for name, rows in res["decomposition"].items():
            L.append(f"\n**per {name}**\n\n" + _table(["gruppo", "n", "win rate", "R medio"], rows))
    if res.get("features_by_fold"):
        L.append("\n## Feature selezionate per finestra\n")
        L.append(_table(["finestra", "feature"], [[k, ", ".join(v)] for k, v in res["features_by_fold"].items()]))
    L.append("\n## Figure\n")
    for f in res.get("figures", []):
        L.append(f"- `{f}`")
    return "\n".join(L) + "\n"


def save_figures(pred: pd.DataFrame, taken_frames: dict, res: dict, boosters: dict, features_by_fold: dict, out_dir: Path, cfg: dict) -> list[Path]:
    import shap
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    fig, ax = plt.subplots(figsize=(9, 4.5))
    for name, t in taken_frames.items():
        t = t.sort_values("entry_ts")
        ax.plot(np.arange(1, len(t) + 1), t["realized_R"].cumsum().to_numpy(), label=f"{name} (n={len(t)})")
    ax.set_xlabel("trade #"); ax.set_ylabel("R cumulato"); ax.legend(); ax.grid(alpha=0.3); ax.set_title("Equity OOS (R)")
    p = out_dir / "equity_oos.png"; fig.tight_layout(); fig.savefig(p, dpi=120); plt.close(fig); paths.append(p)

    fig, ax = plt.subplots(figsize=(4.5, 4.5))
    calib = res.get("calib") or []
    if calib:
        ax.plot([r[1] for r in calib], [r[2] for r in calib], "o-", label="A")
    ax.plot([0, 1], [0, 1], "--", color="gray"); ax.set_xlabel("p media"); ax.set_ylabel("frequenza osservata"); ax.set_title("Calibrazione"); ax.legend()
    p = out_dir / "calibration.png"; fig.tight_layout(); fig.savefig(p, dpi=120); plt.close(fig); paths.append(p)

    if boosters:
        k = max(boosters)
        feats = features_by_fold[k]
        X = pred.loc[pred["fold"] == k, feats]
        explainer = shap.TreeExplainer(boosters[k])
        sv = explainer.shap_values(X)
        sv = sv[1] if isinstance(sv, list) else sv
        imp = pd.Series(np.abs(sv).mean(axis=0), index=feats).sort_values()
        fig, ax = plt.subplots(figsize=(7, 0.35 * len(feats) + 1.5))
        imp.plot.barh(ax=ax); ax.set_title(f"media |SHAP| — finestra {k} (test)"); fig.tight_layout()
        p = out_dir / "shap_summary.png"; fig.savefig(p, dpi=120); plt.close(fig); paths.append(p)
        for f in ("vol_slope_excursion", "vol_reentry_bar", "rr_ratio", "delta_excursion", "absorption_score", "delta_reentry"):
            if f in feats:
                j = feats.index(f)
                fig, ax = plt.subplots(figsize=(5, 4))
                ax.scatter(X[f], sv[:, j], s=6, alpha=0.5); ax.set_xlabel(f); ax.set_ylabel("SHAP"); ax.grid(alpha=0.3)
                p = out_dir / f"shap_dependence_{f}.png"; fig.tight_layout(); fig.savefig(p, dpi=120); plt.close(fig); paths.append(p)
    return paths
