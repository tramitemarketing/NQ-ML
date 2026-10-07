# Test del muro — ORB15 (Opening Range Breakout, 15 minuti)

Generato 2026-09-22 23:49 · config `2ee491362e71` · commit `ec7a5fa`

Pre-registrazione: `docs/superpowers/specs/2026-09-22-screening-nuovi-setup.md` (§2). Periodo di screening: 2016-09-20 → 2023-09-30 (anni di training del progetto). L'OOS di lavoro (2023-10-02 → 2026-03-19) e la cassaforte (2026-03-20 → 2026-09-19) non sono stati toccati.

## Eventi

- giorni nel periodo: 1826
- giorni con ≥ 300 barre RTH: 1755
- giorni con almeno un evento ORB: 1747
- eventi totali: 2537 (long 1314, short 1223; quota long 51.8%)
- eventi per anno: 361.1

## Test del muro (8 geometrie)

g = media per evento di (label − prior geometrico); CI da bootstrap a blocchi per giorno, 10,000 ricampionamenti, seed 0. M1: CI 95% esclude 0 ed è positiva. M2: CI 99,4% (Bonferroni 0,05/8) esclude 0 ed è positiva. M3: n ≥ 500.

| geometria | n | freq | prior medio | g | CI 95% | CI 99,4% | M1 | M2 | M3 | EV senza costi | R medio dopo costi |
|---|---|---|---|---|---|---|---|---|---|---|---|
| S1_T0.5 | 2537 | 0.639 | 0.687 | -0.0488 | [-0.0673, -0.0302] | [-0.0755, -0.0235] | FAIL | FAIL | PASS | -0.0713 R | -0.0334 R |
| S1_T1 | 2537 | 0.425 | 0.524 | -0.0986 | [-0.1177, -0.0790] | [-0.1252, -0.0725] | FAIL | FAIL | PASS | -0.1893 R | -0.0307 R |
| S1_T1.5 | 2537 | 0.295 | 0.423 | -0.1285 | [-0.1459, -0.1104] | [-0.1527, -0.1038] | FAIL | FAIL | PASS | -0.3057 R | -0.0036 R |
| S1_T2 | 2537 | 0.201 | 0.355 | -0.1546 | [-0.1698, -0.1388] | [-0.1764, -0.1321] | FAIL | FAIL | PASS | -0.4387 R | +0.0160 R |
| S2_T0.5 | 2537 | 0.150 | 0.156 | -0.0060 | [-0.0188, +0.0073] | [-0.0242, +0.0119] | FAIL | FAIL | PASS | -0.0140 R | -0.3335 R |
| S2_T1 | 2537 | 0.084 | 0.089 | -0.0043 | [-0.0145, +0.0061] | [-0.0182, +0.0107] | FAIL | FAIL | PASS | -0.0235 R | -0.3006 R |
| S2_T1.5 | 2537 | 0.058 | 0.062 | -0.0042 | [-0.0129, +0.0047] | [-0.0159, +0.0080] | FAIL | FAIL | PASS | -0.0818 R | -0.2903 R |
| S2_T2 | 2537 | 0.040 | 0.048 | -0.0077 | [-0.0151, -0.0002] | [-0.0176, +0.0028] | FAIL | FAIL | PASS | -0.2594 R | -0.2772 R |

## Esito (albero pre-registrato, spec §3)

**Nessuna geometria passa M1** → filone ORB15 **chiuso**; si passa al candidato successivo dell'elenco (gap di apertura, estremi della prima ora, prosecuzione della value area). Nessun modello viene addestrato.

In ogni caso una sola geometria avanza; le altre restano descrittive e non possono essere ripescate in seguito senza una nuova pre-registrazione.

## Come leggere questa tabella

`g` è lo scarto tra la frequenza osservata (target prima dello stop) e il prior di passeggiata aleatoria `1/(1+rr)`: se `g` non è positivo con CI che esclude 0, nessuna geometria — e quindi nessun modello — può rendere profittevole quella coppia stop/target, perché sotto passeggiata aleatoria il valore atteso è identicamente zero per qualunque rr. «EV senza costi» ed «R medio dopo costi» sono descrittivi (§1): entrano nella lettura ma non nel criterio del muro, che è solo su `g`. Nessun filtro (volume, volatilità, giorno della settimana) è stato applicato: questo è il setup nudo.
