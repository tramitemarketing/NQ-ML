"""Potenza dei verdetti del controller: che cosa un FAIL esclude davvero.

Rilegge soltanto `lab/verdicts/*.json` (nessun dato di mercato, nessuna fase aperta, nessun test nuovo) e per
ogni verdetto calcola, dall'intervallo bootstrap a blocchi per giorno già registrato:

- SE: errore standard implicito, (hi − lo) / (2 · 1,96);
- MDE80: il più piccolo effetto vero che quel test avrebbe visto con probabilità 80 % alla soglia usata
  (α = 0,05/K; unilaterale per i tradeable, bilaterale per le regolarità, come in `controller.judge`);
- escluso sopra: il limite superiore unilaterale al livello α. Un FAIL dice «nessun vantaggio sopra questo
  valore», non «nessun vantaggio»;
- per la conferma, la potenza contro metà della stima di validazione (la maledizione del vincitore misurata
  nel laboratorio riduce gli effetti trovati scavando a 0,35-0,7 volte) e quanti anni di dati del blocco
  servirebbero per vederla con potenza 80 %.

L'approssimazione normale dell'intervallo bootstrap è grossolana per campioni piccoli e code pesanti: i numeri
sono ordini di grandezza, non verdetti nuovi.

Uso: .venv/Scripts/python.exe -m lab.potenza   (scrive lab/POTENZA.md)
"""
from __future__ import annotations

import json
from pathlib import Path

from scipy.stats import norm

ROOT = Path(__file__).resolve().parent
Z80 = norm.ppf(0.80)
# durata in anni dei blocchi (PROTOCOLLO §1): validazione 2019-01-01 → 2023-09-30, conferma 2023-10-01 → 2026-03-19
YEARS = {"validation": 4.75, "confirmation": 2.47}
SHRINK = 0.5


def load() -> list[dict]:
    seen, rows = set(), []
    for f in sorted((ROOT / "verdicts").glob("*.json")):
        for v in json.loads(f.read_text(encoding="utf-8")):
            key = (v["id"], v["phase"])
            if key in seen:  # confirmation.json e validation.json duplicano l'ultimo giro
                continue
            seen.add(key)
            rows.append(v)
    return rows


def analyse(v: dict, prev: dict | None) -> dict:
    s = v["stat"]
    se = (s["hi"] - s["lo"]) / (2 * 1.96)
    two_sided = v["kind"] == "regularity"
    zc = norm.ppf(1 - v["alpha"] / 2) if two_sided else norm.ppf(1 - v["alpha"])
    sign = v.get("expected_sign", 1) or 1
    out = {"id": v["id"], "phase": v["phase"], "kind": v["kind"], "k": v["k"], "n": s["n_days"],
           "mean": s["mean"], "lo": s["lo"], "hi": s["hi"], "se": se, "mde": (zc + Z80) * se,
           "excl": s["mean"] + zc * se if sign > 0 else s["mean"] - zc * se,
           "verdict": v["verdict"], "prev": None}
    if prev is not None:
        target = SHRINK * prev["stat"]["mean"]
        if target * sign > 0:
            power = float(norm.cdf(abs(target) / se - zc))
            n_need = s["n_days"] * (out["mde"] / abs(target)) ** 2
            years = YEARS[v["phase"]] * n_need / s["n_days"]
            out["prev"] = {"est": prev["stat"]["mean"], "target": target, "power": power, "years": years}
    return out


def fmt(x: float, nd: int = 3) -> str:
    if abs(x) >= 100:
        nd = 0
    elif abs(x) >= 1:
        nd = min(nd, 2)
    return f"{x:,.{nd}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def main() -> None:
    rows = load()
    by = {(v["id"], v["phase"]): v for v in rows}
    res = [analyse(v, by.get((v["id"], "validation")) if v["phase"] == "confirmation" else None) for v in rows]
    res.sort(key=lambda r: (r["phase"] != "confirmation", r["kind"], r["id"]))

    L = ["# Potenza dei verdetti: che cosa un FAIL esclude davvero", "",
         "Generato da `lab/potenza.py` rileggendo soltanto `lab/verdicts/*.json`: nessun dato, nessun test nuovo.",
         "Unità: quelle del verdetto (punti netti a trade per i tradeable; per le regolarità l'unità della famiglia,",
         "vedi la relazione). SE ricavato dall'intervallo bootstrap a blocchi per giorno; MDE80 = effetto minimo che",
         "il test vedeva con probabilità 80 % alla soglia α = 0,05/K usata dal controller; «escluso sopra» = limite",
         "unilaterale al livello α. Sono ordini di grandezza (approssimazione normale), non verdetti nuovi.", "",
         "| fase | id | tipo | K | n | stima [CI 95 %] | SE | MDE80 | escluso sopra | verdetto |",
         "|---|---|---|---|---|---|---|---|---|---|"]
    for r in res:
        L.append(f"| {r['phase'][:5]} | `{r['id']}` | {r['kind'][:4]} | {r['k']} | {r['n']} | "
                 f"{fmt(r['mean'])} [{fmt(r['lo'])}; {fmt(r['hi'])}] | {fmt(r['se'])} | {fmt(r['mde'])} | "
                 f"{fmt(r['excl']) if r['verdict'] == 'FAIL' else '—'} | {r['verdict']} |")
    L += ["", "## Conferma: si poteva vedere quello che la validazione prometteva?", "",
          f"Bersaglio = {fmt(SHRINK, 1)} × stima di validazione (maledizione del vincitore misurata nel laboratorio:",
          "0,35-0,7). «Anni necessari» = anni di dati come quelli del blocco di conferma per vedere il bersaglio con",
          "potenza 80 %.", "",
          "| id | validazione | bersaglio | conferma [CI 95 %] | potenza sul bersaglio | anni necessari | lettura |",
          "|---|---|---|---|---|---|---|"]
    for r in res:
        p = r["prev"]
        if r["phase"] != "confirmation" or p is None:
            continue
        if r["verdict"] == "PASS":
            lettura = "confermata"
        elif p["power"] >= 0.8:
            lettura = "bocciata con potenza sufficiente"
        else:
            lettura = "**non decidibile** con questo blocco"
        L.append(f"| `{r['id']}` | {fmt(p['est'])} | {fmt(p['target'])} | {fmt(r['mean'])} "
                 f"[{fmt(r['lo'])}; {fmt(r['hi'])}] | {fmt(100 * p['power'], 0)} % | {fmt(p['years'], 1)} | {lettura} |")
    L += ["", "## Come leggerlo", "",
          "- Un FAIL con MDE80 grande non dice «non esiste»: dice «se c'è, è sotto *escluso sopra*». La formula",
          "  onesta per i contenuti è «non ha retto» oppure «non decidibile con questi dati», mai «era fortuna».",
          "- Le due regolarità confermate (HAR e notte → giorno) hanno MDE80 molto sotto la stima: lì la potenza c'è.",
          "- Per un tradeable come la rottura delle bande (σ ≈ 100 punti a trade, ~77 trade l'anno) un vantaggio",
          "  vero di qualche punto non è decidibile su un solo strumento in tempi umani: servono più mercati",
          "  indipendenti o trade più frequenti, non più anni di NQ.", ""]
    (ROOT / "POTENZA.md").write_text("\n".join(L), encoding="utf-8")
    print(f"scritto {ROOT / 'POTENZA.md'}")


if __name__ == "__main__":
    main()
