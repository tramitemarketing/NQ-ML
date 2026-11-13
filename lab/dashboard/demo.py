"""Figure FINTE per provare la scena «Figura» senza dati di mercato.

Numeri inventati con un generatore casuale a seme fisso: non misurano niente. Ogni figura è marcata
`demo = True`, ha DEMO nel titolo, e la dashboard la mostra solo se avviata con `--demo`.

Uso: python -m lab.dashboard.demo        (scrive in lab/figures/_demo/)
     python -m lab.dashboard --demo
"""
from __future__ import annotations

import math
import random

from lab import viz

FAM = "_demo"
NOTE = "DEMO: numeri inventati, non sono risultati del laboratorio."


def main() -> None:
    rnd = random.Random(7)
    anni = [str(y) for y in range(2010, 2019)]
    viz.bars(FAM, "esempio", "per_anno", title="DEMO · Netto medio per anno", labels=anni,
             values=[round(rnd.gauss(-0.5, 1.2), 2) for _ in anni], ylabel="punti NQ netti per trade",
             note=NOTE, demo=True)
    decili = [f"D{i}" for i in range(1, 11)]
    viz.line(FAM, "esempio", "gamma_per_decile", title="DEMO · Rimbalzo del prezzo per decile di GEX",
             x=decili, series={"variance ratio": [round(1.02 - 0.012 * i + rnd.gauss(0, 0.006), 4) for i in range(10)]},
             xlabel="decile di GEX della sera prima", ylabel="variance ratio a 30 minuti", note=NOTE, demo=True)
    viz.placebo(FAM, "esempio", "reale_vs_placebo", title="DEMO · Strategia contro 1.000 placebo", real=0.31,
                placebo_values=[rnd.gauss(0.0, 0.22) for _ in range(1000)], xlabel="netto medio (R)",
                real_label="strategia", note=NOTE, demo=True)
    deltas = [round(0.05 * i, 2) for i in range(0, 61)]
    quota = [1 / (1 + math.exp(-(d - 1.3) / 0.22)) for d in deltas]
    viz.line(FAM, "esempio", "potenza", title="DEMO · Quanto deve essere grande un edge perché il lab lo veda",
             x=deltas, series={"quota riconosciuta": quota}, marker={"x": 1.6, "y": 0.8, "label": "δ80"},
             xlabel="edge piantato δ (punti netti per trade)", ylabel="quota di strategie riconosciute",
             note=NOTE, demo=True)
    viz.scatter(FAM, "esempio", "nuvola", title="DEMO · Range notturno e range di giornata",
                x=[round(rnd.lognormvariate(3.2, 0.4), 1) for _ in range(400)],
                y=[round(rnd.lognormvariate(3.9, 0.45), 1) for _ in range(400)],
                xlabel="range della notte (punti)", ylabel="range RTH (punti)", note=NOTE, demo=True)
    print("Figure DEMO scritte in", viz.FIG_DIR / FAM)


if __name__ == "__main__":
    main()
