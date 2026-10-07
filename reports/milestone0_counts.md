# Milestone 0 — conteggio eventi e geometria
Generato il 2026-09-20 · config `50dbad171d7c` · commit `19b6be7`
Tutte le cifre sono misurate da `data/events/*.parquet`; i costi tick sono estrapolati da 40 + 40 finestre campionate con `metadata.get_cost` (seed 0).
## Giorni
- sessioni totali: 2593; valide (>= 300 barre RTH): 2492; valide dal 2021-09-20: 1245
## Eventi per anno × va_type × side
|   year |   ('DEV', 'long') |   ('DEV', 'short') |   ('ON', 'long') |   ('ON', 'short') |
|-------:|------------------:|-------------------:|-----------------:|------------------:|
|   2016 |               196 |                183 |               77 |                88 |
|   2017 |               585 |                733 |              302 |               324 |
|   2018 |               646 |                676 |              334 |               333 |
|   2019 |               567 |                715 |              248 |               284 |
|   2020 |               665 |                756 |              322 |               334 |
|   2021 |               643 |                661 |              312 |               300 |
|   2022 |               670 |                626 |              306 |               305 |
|   2023 |               591 |                693 |              337 |               305 |
|   2024 |               658 |                675 |              331 |               327 |
|   2025 |               603 |                672 |              269 |               279 |
|   2026 |               400 |                483 |              210 |               186 |

- **Totale 10 anni: 19210** · **dal 2021-09-20 (N5): 9438** · eventi/giorno valido: 7.71
## Geometria (quantili 10 | 25 | 50 | 75 | 90)
| misura | q10 | q25 | q50 | q75 | q90 |
|---|---|---|---|---|---|
| stop (punti) | 5.00 | 10.00 | 20.75 | 39.00 | 65.50 |
| target (punti) | 9.50 | 19.00 | 40.25 | 76.25 | 122.50 |
| rr_ratio | 0.56 | 1.07 | 1.92 | 3.54 | 6.38 |
| excursion_minutes | 10.00 | 10.00 | 15.00 | 25.00 | 45.00 |
| bars_outside | 1.00 | 1.00 | 2.00 | 4.00 | 8.00 |
| minuti finestra tick | 10.00 | 10.00 | 15.00 | 25.00 | 45.00 |

- eventi con rr_ratio < 1: 22.7% · rr >= 2: 48.5%
- eventi DEV con rientro entro le 09:45 (profilo con <= 3 barre): 1285
## Costo tick nelle finestre (schema `trades`)
- finestre uniche dal 2021-09-20: 9073 · costo medio campionato $0.0266 → **STIMA $241.25**
- finestre uniche 2016→2021-09-20: 9450 · costo medio campionato $0.0219 → 10 anni **STIMA $447.97**
## Decisione (regola spec §12: N5 >= 6000 → 5 anni, altrimenti 10)
**5 anni di tick (N5 >= 6000)**
