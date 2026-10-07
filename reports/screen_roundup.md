# Test del muro — candidati 2, 3, 4 (gap, prima ora, prosecuzione value area)

Generato 2026-09-23 00:17 · config `2ee491362e71` · commit `7f17ba8`

Pre-registrazione: `docs/superpowers/specs/2026-09-22-screening-candidati-2-3-4.md`. Periodo di screening: 2016-09-20 → 2023-09-30 (anni di training del progetto). L'OOS di lavoro (2023-10-02 → 2026-03-19) e la cassaforte (2026-03-20 → 2026-09-19) non sono stati toccati. Eseguiti insieme, in un'unica passata: nessuno dei tre e' stato ri-eseguito dopo aver visto gli altri. Molteplicita' del filone: 8 (ORB15, gia' chiuso) + 6 (gap) + 8 (prima ora) + 8 (prosecuzione VA) = 30 test. M1: CI 95% esclude 0 ed e' positiva. M2: CI 99,83% (Bonferroni 0,05/30) esclude 0 ed e' positiva. M3: n ≥ 500. In ogni candidato una sola geometria puo' avanzare.

## Candidato 2 — Gap di apertura (S2)

Evento: |gap RTH| ≥ 2 punti (apertura RTH − chiusura RTH del giorno precedente). Due famiglie speculari, tre geometrie ciascuna: F (chiusura del gap, verso la chiusura precedente) e P (prosecuzione, nella direzione del gap), k ∈ {0,5; 1; 2}. Al massimo un evento per giorno. Attesa dichiarata: 15% di passare M2.

- giorni nel periodo: 1826
- giorni con ≥ 300 barre RTH e chiusura precedente nota: 1755
- giorni con un gap ≥ 2 punti: 1683
- eventi totali: 1683 (gap in su 951, gap in giù 732; quota in su 56.5%)
- eventi per anno: 239.6

### Test del muro (6 geometrie)

| geometria | n | freq | prior medio | g | CI 95% | CI 99,83% | M1 | M2 | M3 | EV senza costi | R medio dopo costi |
|---|---|---|---|---|---|---|---|---|---|---|---|
| F_k0.5 | 1683 | 0.284 | 0.333 | -0.0493 | [-0.0707, -0.0279] | [-0.0824, -0.0137] | FAIL | FAIL | PASS | -0.1480 R | -0.0617 R |
| F_k1 | 1683 | 0.387 | 0.500 | -0.1126 | [-0.1352, -0.0888] | [-0.1492, -0.0742] | FAIL | FAIL | PASS | -0.2252 R | -0.0540 R |
| F_k2 | 1683 | 0.475 | 0.667 | -0.1919 | [-0.2157, -0.1682] | [-0.2301, -0.1535] | FAIL | FAIL | PASS | -0.2879 R | -0.0152 R |
| P_k0.5 | 1683 | 0.515 | 0.667 | -0.1521 | [-0.1765, -0.1283] | [-0.1925, -0.1149] | FAIL | FAIL | PASS | -0.2282 R | -0.0571 R |
| P_k1 | 1683 | 0.374 | 0.500 | -0.1257 | [-0.1488, -0.1025] | [-0.1623, -0.0888] | FAIL | FAIL | PASS | -0.2513 R | -0.0510 R |
| P_k2 | 1683 | 0.199 | 0.333 | -0.1343 | [-0.1539, -0.1159] | [-0.1652, -0.1028] | FAIL | FAIL | PASS | -0.4029 R | -0.0458 R |

### Esito

**Nessuna geometria passa M1** → candidato **chiuso**, nessun modello addestrato.

## Candidato 3 — Estremi della prima ora (S3)

Evento: FHH/FHL sulle 60 barre 1m dalle 09:30 alle 10:29:59 ET; dalle 10:30 la prima barra che chiude oltre l'estremo genera l'evento (al massimo uno per lato al giorno). Otto geometrie (2 stop × 4 target), stessa struttura dell'ORB15 su una finestra di un'ora. Attesa dichiarata: 15% di passare M2.

- giorni nel periodo: 1826
- giorni con ≥ 300 barre RTH: 1755
- giorni con almeno un evento: 1641
- eventi totali: 1932 (long 1035, short 897; quota long 53.6%)
- eventi per anno: 275.0

### Test del muro (8 geometrie)

| geometria | n | freq | prior medio | g | CI 95% | CI 99,83% | M1 | M2 | M3 | EV senza costi | R medio dopo costi |
|---|---|---|---|---|---|---|---|---|---|---|---|
| S1_T0.5 | 1932 | 0.513 | 0.679 | -0.1659 | [-0.1886, -0.1432] | [-0.2021, -0.1317] | FAIL | FAIL | PASS | -0.2449 R | +0.0100 R |
| S1_T1 | 1932 | 0.224 | 0.514 | -0.2898 | [-0.3081, -0.2714] | [-0.3188, -0.2600] | FAIL | FAIL | PASS | -0.5653 R | +0.0166 R |
| S1_T1.5 | 1932 | 0.104 | 0.413 | -0.3094 | [-0.3229, -0.2956] | [-0.3302, -0.2881] | FAIL | FAIL | PASS | -0.7500 R | +0.0232 R |
| S1_T2 | 1932 | 0.050 | 0.346 | -0.2957 | [-0.3050, -0.2859] | [-0.3104, -0.2794] | FAIL | FAIL | PASS | -0.8556 R | +0.0237 R |
| S2_T0.5 | 1932 | 0.117 | 0.097 | +0.0196 | [+0.0058, +0.0338] | [-0.0024, +0.0424] | PASS | FAIL | PASS | +0.1747 R | -0.1487 R |
| S2_T1 | 1932 | 0.052 | 0.053 | -0.0011 | [-0.0106, +0.0089] | [-0.0154, +0.0148] | FAIL | FAIL | PASS | -0.0489 R | -0.1383 R |
| S2_T1.5 | 1932 | 0.026 | 0.036 | -0.0100 | [-0.0168, -0.0027] | [-0.0210, +0.0014] | FAIL | FAIL | PASS | -0.3455 R | -0.0883 R |
| S2_T2 | 1932 | 0.013 | 0.028 | -0.0143 | [-0.0192, -0.0089] | [-0.0215, -0.0056] | FAIL | FAIL | PASS | -0.4693 R | -0.0487 R |

### Esito

**Passa M1 ma non M2** → «segnale debole»: si annota, non si apre nulla. Geometria con g più alto: **S2_T0.5** (g = +0.0196 [+0.0058, +0.0338] CI 95%, n = 1932); può rientrare in un disegno futuro solo se pre-registrato esplicitamente come replica, con soglia M2.

## Candidato 4 — Prosecuzione della value area (S4)

Evento: prima transizione INSIDE → BROKEN per (tipo di value area ON/DEV × lato di rottura) per giorno — prima chiusura di barra 5m oltre il bordo della value area, indipendentemente da cio' che accade dopo. Guida le stesse barre 5m e lo stesso codice di value area di nqml/detector/run_day.py (ON fissa, DEV ricalcolata a ogni chiusura 5m) senza usare `SetupDetector`, che emette solo al rientro: gli eventi gia' calcolati in `data/events/events.parquet` conterrebbero percio' solo le rotture poi rientrate, una selezione che favorirebbe artificialmente il rientro. Otto geometrie (2 stop × 4 target su k della larghezza della value area alla rottura). Attesa dichiarata: 25% di passare M2.

- giorni nel periodo: 1826
- giorni con ≥ 300 barre RTH: 1755
- giorni con almeno un evento: 1755
- eventi totali: 5573 (ON 2422, DEV 3151; long 2856, short 2717, quota long 51.2%)
- eventi per anno: 793.3

### Test del muro (8 geometrie)

| geometria | n | freq | prior medio | g | CI 95% | CI 99,83% | M1 | M2 | M3 | EV senza costi | R medio dopo costi |
|---|---|---|---|---|---|---|---|---|---|---|---|
| S1_T0.25 | 5573 | 0.466 | 0.470 | -0.0041 | [-0.0166, +0.0082] | [-0.0246, +0.0153] | FAIL | FAIL | PASS | -0.0062 R | -0.2040 R |
| S1_T0.5 | 5573 | 0.339 | 0.333 | +0.0055 | [-0.0067, +0.0178] | [-0.0149, +0.0238] | FAIL | FAIL | PASS | +0.0140 R | -0.1946 R |
| S1_T0.75 | 5573 | 0.265 | 0.262 | +0.0033 | [-0.0081, +0.0149] | [-0.0159, +0.0222] | FAIL | FAIL | PASS | +0.0155 R | -0.1874 R |
| S1_T1.0 | 5573 | 0.217 | 0.216 | +0.0008 | [-0.0104, +0.0121] | [-0.0171, +0.0188] | FAIL | FAIL | PASS | +0.0207 R | -0.1655 R |
| S2_T0.25 | 5573 | 0.756 | 0.741 | +0.0150 | [+0.0033, +0.0266] | [-0.0037, +0.0335] | PASS | FAIL | PASS | +0.0208 R | -0.0153 R |
| S2_T0.5 | 5573 | 0.606 | 0.595 | +0.0101 | [-0.0029, +0.0233] | [-0.0107, +0.0324] | FAIL | FAIL | PASS | +0.0192 R | -0.0073 R |
| S2_T0.75 | 5573 | 0.502 | 0.500 | +0.0025 | [-0.0112, +0.0163] | [-0.0179, +0.0254] | FAIL | FAIL | PASS | +0.0054 R | -0.0052 R |
| S2_T1.0 | 5573 | 0.417 | 0.432 | -0.0143 | [-0.0279, -0.0006] | [-0.0354, +0.0086] | FAIL | FAIL | PASS | -0.0321 R | -0.0109 R |

### Esito

**Passa M1 ma non M2** → «segnale debole»: si annota, non si apre nulla. Geometria con g più alto: **S2_T0.25** (g = +0.0150 [+0.0033, +0.0266] CI 95%, n = 5573); può rientrare in un disegno futuro solo se pre-registrato esplicitamente come replica, con soglia M2.

## Sintesi — tutti i 30 test del filone screening

Le 8 righe ORB15 sono copiate letteralmente da `reports/screen_orb15.md` (candidato 1, S1, gia' chiuso e registrato: CI al 99,4%, Bonferroni sulle sue 8 geometrie soltanto, non ricalcolate a 99,83%). Le altre 22 righe usano la soglia M2 aggiornata di questo documento (99,83%, Bonferroni sui 30 test del filone).

| candidato | geometria | n | g | M1 | M2 | M3 | nota |
|---|---|---|---|---|---|---|---|
| ORB15 (candidato 1) | S1_T0.5 | 2537 | -0.0488 | FAIL | FAIL | PASS | già registrato (S1, CI 99,4%) |
| ORB15 (candidato 1) | S1_T1 | 2537 | -0.0986 | FAIL | FAIL | PASS | già registrato (S1, CI 99,4%) |
| ORB15 (candidato 1) | S1_T1.5 | 2537 | -0.1285 | FAIL | FAIL | PASS | già registrato (S1, CI 99,4%) |
| ORB15 (candidato 1) | S1_T2 | 2537 | -0.1546 | FAIL | FAIL | PASS | già registrato (S1, CI 99,4%) |
| ORB15 (candidato 1) | S2_T0.5 | 2537 | -0.0060 | FAIL | FAIL | PASS | già registrato (S1, CI 99,4%) |
| ORB15 (candidato 1) | S2_T1 | 2537 | -0.0043 | FAIL | FAIL | PASS | già registrato (S1, CI 99,4%) |
| ORB15 (candidato 1) | S2_T1.5 | 2537 | -0.0042 | FAIL | FAIL | PASS | già registrato (S1, CI 99,4%) |
| ORB15 (candidato 1) | S2_T2 | 2537 | -0.0077 | FAIL | FAIL | PASS | già registrato (S1, CI 99,4%) |
| Gap (candidato 2) | F_k0.5 | 1683 | -0.0493 | FAIL | FAIL | PASS | |
| Gap (candidato 2) | F_k1 | 1683 | -0.1126 | FAIL | FAIL | PASS | |
| Gap (candidato 2) | F_k2 | 1683 | -0.1919 | FAIL | FAIL | PASS | |
| Gap (candidato 2) | P_k0.5 | 1683 | -0.1521 | FAIL | FAIL | PASS | |
| Gap (candidato 2) | P_k1 | 1683 | -0.1257 | FAIL | FAIL | PASS | |
| Gap (candidato 2) | P_k2 | 1683 | -0.1343 | FAIL | FAIL | PASS | |
| Prima ora (candidato 3) | S1_T0.5 | 1932 | -0.1659 | FAIL | FAIL | PASS | |
| Prima ora (candidato 3) | S1_T1 | 1932 | -0.2898 | FAIL | FAIL | PASS | |
| Prima ora (candidato 3) | S1_T1.5 | 1932 | -0.3094 | FAIL | FAIL | PASS | |
| Prima ora (candidato 3) | S1_T2 | 1932 | -0.2957 | FAIL | FAIL | PASS | |
| Prima ora (candidato 3) | S2_T0.5 | 1932 | +0.0196 | PASS | FAIL | PASS | |
| Prima ora (candidato 3) | S2_T1 | 1932 | -0.0011 | FAIL | FAIL | PASS | |
| Prima ora (candidato 3) | S2_T1.5 | 1932 | -0.0100 | FAIL | FAIL | PASS | |
| Prima ora (candidato 3) | S2_T2 | 1932 | -0.0143 | FAIL | FAIL | PASS | |
| Prosecuzione VA (candidato 4) | S1_T0.25 | 5573 | -0.0041 | FAIL | FAIL | PASS | |
| Prosecuzione VA (candidato 4) | S1_T0.5 | 5573 | +0.0055 | FAIL | FAIL | PASS | |
| Prosecuzione VA (candidato 4) | S1_T0.75 | 5573 | +0.0033 | FAIL | FAIL | PASS | |
| Prosecuzione VA (candidato 4) | S1_T1.0 | 5573 | +0.0008 | FAIL | FAIL | PASS | |
| Prosecuzione VA (candidato 4) | S2_T0.25 | 5573 | +0.0150 | PASS | FAIL | PASS | |
| Prosecuzione VA (candidato 4) | S2_T0.5 | 5573 | +0.0101 | FAIL | FAIL | PASS | |
| Prosecuzione VA (candidato 4) | S2_T0.75 | 5573 | +0.0025 | FAIL | FAIL | PASS | |
| Prosecuzione VA (candidato 4) | S2_T1.0 | 5573 | -0.0143 | FAIL | FAIL | PASS | |

## Come leggere questa tabella

`g` è lo scarto tra la frequenza osservata (target prima dello stop) e il prior di passeggiata aleatoria `1/(1+rr)`: se `g` non è positivo con CI che esclude 0, nessuna geometria — e quindi nessun modello — può rendere profittevole quella coppia stop/target. «EV senza costi» ed «R medio dopo costi» sono descrittivi: entrano nella lettura ma non nel criterio del muro, che è solo su `g`. Nessun filtro (volume, volatilità, giorno della settimana, notizie) è stato applicato: questo è il setup nudo di ciascun candidato.
