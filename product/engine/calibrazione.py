"""Calibrazione del Revisore: quanto spesso sbaglia, misurato e non creduto.

Fa girare il verdetto completo (`run_audit`) su strategie sintetiche di cui conosciamo la verità:

1. **Caso puro**: ingressi, durate e lati a caso su un mercato senza vantaggio, a costo zero (così la media
   netta attesa è esattamente zero: con un costo positivo il caso perderebbe sempre e i falsi positivi
   sarebbero zero per costruzione). Ogni A o B è un falso positivo.
2. **Scelta della migliore fra 20**: 20 strategie a caso sullo stesso mercato, si tiene quella con la media più
   alta. Audit due volte: dichiarando N = 1 (chi non dice quante ne ha provate) e N = 20 (onesto).
3. **Vantaggio piantato** di diversa dimensione: quanto spesso il Revisore lo riconosce (A o B).

Mercato: `tests/conftest.rth_market` (barre da 1 minuto 09:30-16:00, σ = 1 punto al minuto, quindi un trade di
60 minuti ha σ ≈ 7,7 punti). Costo 0,5 punti a/r. Le dimensioni del vantaggio si riportano anche in unità
di σ del trade, che è la grandezza che conta su qualunque mercato.

Uso (da product/engine): python calibrazione.py [--reps 200]   -> scrive CALIBRAZIONE.md e calibrazione.json
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from revisore import AuditConfig, Market, load_trades, run_audit  # noqa: E402
from tests.conftest import make_trades, rth_market  # noqa: E402

COST = 0.5
SIGMA_TRADE = np.sqrt(60.0)          # σ di un trade di 60 minuti con σ = 1 al minuto
FAST = dict(n_boot=2000, n_placebo=200)
GRADES = "ABCDEF"


def audit(bars_or_market, tr, n_tried: int, cost: float = COST) -> dict:
    m = bars_or_market if isinstance(bars_or_market, Market) else Market(bars_or_market)
    R = run_audit(load_trades(tr), m, AuditConfig(n_tried=n_tried, cost=cost, point_value=20, **FAST))
    return {"grade": R["verdict"]["grade"], "mean": R["boot"]["mean"], "p": R["boot"]["p_pos"],
            "mde": R["power"]["mde"]}


def random_trades(bars, rng, share=0.7):
    d = bars.index.tz_convert("America/New_York").tz_localize(None).normalize().unique()
    d = d[rng.random(len(d)) < share]
    start = pd.to_timedelta(rng.integers(600, 900, len(d)), unit="min")
    dur = pd.to_timedelta(rng.integers(15, 90, len(d)), unit="min")
    return make_trades(bars, d + start, d + start + dur, rng.choice([-1, 1], len(d)))


def edge_trades(bars, sig, n_days):
    d = sig.index[:n_days]
    return make_trades(bars, d + pd.Timedelta(hours=10), d + pd.Timedelta(hours=11), sig.to_numpy()[:n_days])


def dist(res: list[dict]) -> dict:
    c = Counter(r["grade"] for r in res)
    n = len(res)
    out = {g: c.get(g, 0) / n for g in GRADES}
    out["AB"] = out["A"] + out["B"]
    out["n"] = n
    return out


def wilson(p: float, n: int) -> tuple[float, float]:
    z = 1.96
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return max(0.0, c - h), min(1.0, c + h)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reps", type=int, default=200)
    a = ap.parse_args()
    reps = a.reps
    t0 = time.time()
    out: dict = {"reps": reps, "cost": COST, "sigma_trade": SIGMA_TRADE, "fast": FAST}

    # 1. caso puro
    res = []
    for i in range(reps):
        bars, _ = rth_market(750, seed=10_000 + i, edge=0.0)
        res.append(audit(bars, random_trades(bars, np.random.default_rng(i)), 1, cost=0.0))
    out["caso_puro"] = dist(res)
    print("caso puro", out["caso_puro"], f"{time.time() - t0:.0f}s", flush=True)

    # 2. la migliore fra 20
    lie, honest = [], []
    for i in range(reps):
        bars, _ = rth_market(750, seed=20_000 + i, edge=0.0)
        m = Market(bars)
        rng = np.random.default_rng(50_000 + i)
        cands = [random_trades(bars, rng) for _ in range(20)]
        best = max(cands, key=lambda t: t["pnl_points"].mean())
        lie.append(audit(m, best, 1, cost=0.0))
        honest.append(audit(m, best, 20, cost=0.0))
    out["migliore_di_20_dichiara_1"] = dist(lie)
    out["migliore_di_20_dichiara_20"] = dist(honest)
    print("migliore di 20", out["migliore_di_20_dichiara_1"], out["migliore_di_20_dichiara_20"],
          f"{time.time() - t0:.0f}s", flush=True)

    # 3. vantaggio piantato: lordo E punti a trade, netto E - COST
    rows = []
    for n_days in (250, 750):
        for E in (0.75, 1.0, 1.5, 2.0, 3.0, 4.0):
            res = []
            for i in range(reps // 2):
                bars, sig = rth_market(n_days, seed=30_000 + 97 * i + int(10 * E), edge=E)
                res.append(audit(bars, edge_trades(bars, sig, n_days), 1))
            dd = dist(res)
            dd.update({"n_trades": n_days, "edge_gross": E, "edge_net": E - COST,
                       "net_in_sigma": (E - COST) / SIGMA_TRADE,
                       "mde80_median": float(np.nanmedian([r["mde"] for r in res if r["mde"] is not None]))
                       if any(r["mde"] is not None for r in res) else None})
            rows.append(dd)
            print("vantaggio", n_days, E, {k: round(v, 2) for k, v in dd.items() if k in ("AB", "C", "D")},
                  f"{time.time() - t0:.0f}s", flush=True)
    out["vantaggio"] = rows
    out["secondi"] = time.time() - t0
    (HERE / "calibrazione.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    write_md(out)


def pct(x: float) -> str:
    return f"{100 * x:.1f} %".replace(".", ",")


def write_md(o: dict) -> None:
    def row(name, d):
        lo, hi = wilson(d["AB"], d["n"])
        return (f"| {name} | {d['n']} | " + " | ".join(pct(d[g]) for g in GRADES) +
                f" | **{pct(d['AB'])}** [{pct(lo)}; {pct(hi)}] |")

    L = ["# Calibrazione del Revisore", "",
         f"Generata da `calibrazione.py` ({o['reps']} ripetizioni per scenario, {o['secondi'] / 60:.0f} minuti). "
         "Strategie sintetiche di cui si conosce la verità, verdetto completo `run_audit` con i dati di mercato. "
         f"Scenari nulli a costo zero (media netta attesa esattamente zero); vantaggi piantati con costo "
         f"{str(o['cost']).replace('.', ',')} punti a/r. Per velocità: {o['fast']['n_boot']} bootstrap e "
         f"{o['fast']['n_placebo']} placebo per audit (in produzione 10.000 e 1.000).", "",
         "## Falsi positivi: strategie senza vantaggio", "",
         "Ogni A o B qui è un errore del Revisore. Fra parentesi l'intervallo al 95 % (Wilson).", "",
         "| scenario | n | A | B | C | D | E | F | A+B (falsi positivi) |",
         "|---|---|---|---|---|---|---|---|---|",
         row("caso puro, N dichiarato = 1", o["caso_puro"]),
         row("migliore fra 20, dichiara N = 1", o["migliore_di_20_dichiara_1"]),
         row("migliore fra 20, dichiara N = 20", o["migliore_di_20_dichiara_20"]), "",
         "## Potenza: vantaggi veri piantati", "",
         f"Trade di 60 minuti, σ del trade ≈ {o['sigma_trade']:.1f} punti".replace(".", ",") + ". «Netto in σ» = vantaggio netto diviso σ "
         "del trade: è la grandezza confrontabile fra mercati (per NQ con trade di un'ora σ ≈ 40-100 punti).", "",
         "| trade | lordo | netto | netto in σ | A+B (riconosciuto) | C | D+E (mancato) | MDE80 mediano (punti) |",
         "|---|---|---|---|---|---|---|---|"]
    for r in o["vantaggio"]:
        mde = "—" if r["mde80_median"] is None else f"{r['mde80_median']:.2f}".replace(".", ",")
        L.append(f"| {r['n_trades']} | {r['edge_gross']:.2f} | {r['edge_net']:.2f} | {r['net_in_sigma']:.3f} | "
                 f"**{pct(r['AB'])}** | {pct(r['C'])} | {pct(r['D'] + r['E'])} | {mde} |".replace(".", ","))
    L += ["", "## Come leggerlo", "",
          "- **Caso puro**: la frazione di A+B è il tasso di falsi positivi quando l'utente è onesto sul numero di "
          "tentativi.",
          "- **Migliore fra 20 che dichiara N = 1**: è il caso del venditore che sceglie la variante migliore e non "
          "lo dice. La differenza con la riga «dichiara N = 20» è quanto il Revisore dipende da ciò che l'utente "
          "dichiara: il Revisore non può vedere i tentativi nascosti, e la pagella deve dirlo.",
          "- **Potenza**: sotto circa 0,1 σ netti a trade e con qualche centinaio di trade il Revisore di solito "
          "non riconosce un vantaggio vero. È un limite della statistica, non del software: la riga MDE80 della "
          "pagella lo dice caso per caso.", ""]
    (HERE / "CALIBRAZIONE.md").write_text("\n".join(L), encoding="utf-8")
    print("scritto", HERE / "CALIBRAZIONE.md")


if __name__ == "__main__":
    main()
