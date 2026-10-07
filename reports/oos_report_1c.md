# Report OOS — 1c (sguardo #3)

Generato il 2026-09-22 · config `2ee491362e71` · commit `18a2b44` · bootstrap 10000 / seed 0

## Sguardo #3 — criteri pre-registrati (spec §12-ter)

Eventi: 4677 totali · S 2059 · non-S 2618. Brier pooled: L1 0.1820 · L2 0.1804 · A 0.1797 · su S: A 0.1751, B 0.1748.

| # | criterio | evidenza | esito |
|---|---|---|---|
| G1 | Brier(A) − Brier(L1), n 4677 | -0.0023 [-0.0041, -0.0005] | valido |
| P1 | Brier(A) − Brier(L2), n 4677 | 95 %: -0.0007 [-0.0023, +0.0010] · 99 %: -0.0007 [-0.0028, +0.0015] | **FAIL** |
| S1 | Brier(B) − Brier(A) su S, n 2059 | 95 %: -0.0003 [-0.0016, +0.0009] · 99 %: -0.0003 [-0.0020, +0.0013] | **non letto** |
| G2 | mediana \|p_B − p_A\| sui non-S 0.01003 ≤ 2 × mediana \|p_A − p_A′\| 0.00786 | PASS | S1 non letto (P1 FAIL) |

Shuffle AUC (media di 5 seed sui soli alberi) — A per piega: [0.506, 0.502, 0.475, 0.502, 0.521] · B: [0.523, 0.499, 0.476, 0.514, 0.517]

Variante a offset fisso (registrazione originaria, solo riportata; §12-ter emendato il 2026-09-22): A per piega [0.249, 0.248, 0.225, 0.257, 0.262] · B [0.251, 0.247, 0.224, 0.257, 0.266] — anti-correlata per costruzione (gli alberi cancellano l'offset), nessuna banda applicata.

Descrittivi (nessun verdetto) — R medio B − A appaiato per giorno: +0.023 [-0.160, +0.216] (n 194 vs 326) · decisioni: Jaccard 0.370 · entrambe 160 · solo A 220 · solo B 52

Lettura pre-registrata: P1 FAIL con stima negativa (-0.0007): l'informazione oltre L2, se c'è, è sotto la soglia di rilevabilità a questa n (potenza dichiarata 20–50 %); il falsificatore pre-registrato (stima ≥ +0.0005) NON è scattato; il forward test NON si attiva (richiede P1 ≥ candidato); L2 resta il modello di riferimento; S1 non letto.
