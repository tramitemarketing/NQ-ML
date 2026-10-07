# Test del muro — candidati 5, 6, 7, 8 (VWAP, overnight, ultima ora, apertura fuori VA) — Benjamini-Hochberg

Generato 2026-09-23 00:58 · config `2ee491362e71` · commit `324d51d`

Pre-registrazione: `docs/superpowers/specs/2026-09-23-screening-candidati-5-8-e-ibridi.md`. Periodo di screening: 2016-09-20 → 2023-09-30 (anni di training del progetto). L'OOS di lavoro (2023-10-02 → 2026-03-19) e la cassaforte (2026-03-20 → 2026-09-19) non sono stati toccati. Eseguiti insieme, in un'unica passata: nessuno dei quattro e' stato ri-eseguito dopo aver visto gli altri. **Controllo di molteplicita': Benjamini-Hochberg, q = 0,10, sui 22 test di questo lotto** (6 VWAP + 4 overnight + 4 ultima ora + 8 apertura fuori VA), non retroattivo sulle righe S1-S4 (Bonferroni, gia' chiuse). p-value bootstrap a due code, 10,000 ricampionamenti, seed 0, con correzione (k+1)/(B+1). Una geometria che non e' una scoperta BH non e' un candidato, qualunque sia la sua CI 95%.

## Candidato 5 — Ritorno alla media sul VWAP

Evento: dalle 10:00 ET, la prima barra 1m che chiude a piu' di 2σ dal VWAP di sessione (pesato per volume dall'apertura) genera un ritorno alla media (short se sopra, long se sotto). Sei geometrie (2 target x 3 stop in ATR del giorno precedente). Attesa dichiarata: 20% di almeno una scoperta BH.

- giorni nel periodo: 1826
- giorni con ≥ 300 barre RTH: 1755
- giorni con almeno un evento: 1637
- eventi totali: 2185 (long 1078, short 1107; quota long 49.3%)
- eventi per anno: 311.0

### Test del muro (6 geometrie)

| geometria | n | freq | prior medio | g | CI 95% | p (bootstrap) | soglia BH | scoperta | EV senza costi | R medio dopo costi |
|---|---|---|---|---|---|---|---|---|---|---|
| TVWAP_A1.0 | 2183 | 0.287 | 0.305 | -0.0187 | [-0.0377, +0.0000] | 0.0504 | 0.0682 | SI | -0.0815 R | -0.1171 R |
| TVWAP_A1.5 | 2183 | 0.377 | 0.393 | -0.0155 | [-0.0349, +0.0038] | 0.1200 | 0.0818 | NO | -0.0612 R | -0.0542 R |
| TVWAP_A2.0 | 2183 | 0.436 | 0.460 | -0.0236 | [-0.0434, -0.0038] | 0.0210 | 0.0591 | SI | -0.0711 R | -0.0368 R |
| TMID_A1.0 | 2183 | 0.438 | 0.460 | -0.0213 | [-0.0421, -0.0009] | 0.0410 | 0.0636 | SI | -0.0559 R | -0.1196 R |
| TMID_A1.5 | 2183 | 0.546 | 0.556 | -0.0096 | [-0.0304, +0.0107] | 0.3482 | 0.0955 | NO | -0.0270 R | -0.0623 R |
| TMID_A2.0 | 2183 | 0.606 | 0.622 | -0.0161 | [-0.0367, +0.0040] | 0.1140 | 0.0773 | NO | -0.0351 R | -0.0542 R |

### Esito

**3 geometria/e scoperta/e dal BH** (TVWAP_A1.0, TVWAP_A2.0, TMID_A1.0) → candidato: la geometria con g piu' alto e' **TVWAP_A1.0** (g = -0.0187 [-0.0377, +0.0000] CI 95%, p = 0.0504, n = 2183). Autorizza una milestone pre-registrata il cui verdetto e' sull'OOS vergine 2023-10 → 2026-03, mai toccato: la scoperta e' un candidato, non un risultato.

## Candidato 6 — Tenuta overnight

Evento: long alla chiusura RTH, uscita all'apertura RTH successiva; nessuna condizione, un evento ogni giorno valido. Quattro geometrie (2 stop x 2 target in ATR del giorno precedente). Unica deroga del lotto: il time stop non e' alle 15:55 ma all'apertura RTH successiva (nella definizione del setup, non un parametro). Attesa dichiarata: 30% di almeno una scoperta BH.

- giorni d'ingresso nel periodo: 1755
- giorni d'ingresso validi (uscita nel periodo e non oltre il confine): 1695
- eventi scartati per il confine di periodo (uscita >= 2023-10-01, non troncati): 1
- eventi totali: 1695

### Test del muro (4 geometrie)

| geometria | n | freq | prior medio | g | CI 95% | p (bootstrap) | soglia BH | scoperta | EV senza costi | R medio dopo costi |
|---|---|---|---|---|---|---|---|---|---|---|
| S1.0_T1.0 | 1694 | 0.573 | 0.500 | +0.0732 | [+0.0496, +0.0968] | 0.0002 | 0.0045 | SI | +0.1464 R | +0.0734 R |
| S1.0_T2.0 | 1694 | 0.392 | 0.333 | +0.0586 | [+0.0350, +0.0817] | 0.0002 | 0.0091 | SI | +0.1759 R | +0.1066 R |
| S2.0_T1.0 | 1694 | 0.715 | 0.667 | +0.0482 | [+0.0264, +0.0695] | 0.0002 | 0.0136 | SI | +0.0723 R | +0.0393 R |
| S2.0_T2.0 | 1694 | 0.543 | 0.500 | +0.0431 | [+0.0189, +0.0667] | 0.0004 | 0.0500 | SI | +0.0862 R | +0.0691 R |

### Esito

**4 geometria/e scoperta/e dal BH** (S1.0_T1.0, S1.0_T2.0, S2.0_T1.0, S2.0_T2.0) → candidato: la geometria con g piu' alto e' **S1.0_T1.0** (g = +0.0732 [+0.0496, +0.0968] CI 95%, p = 0.0002, n = 1694). Autorizza una milestone pre-registrata il cui verdetto e' sull'OOS vergine 2023-10 → 2026-03, mai toccato: la scoperta e' un candidato, non un risultato.

## Candidato 7 — Momentum dell'ultima ora

Evento: alle 15:00 ET, nella direzione della sessione rispetto all'apertura RTH; un evento ogni giorno (salvo sessione esattamente flat). Quattro geometrie (2 stop x 2 target in ATR del giorno precedente). Attesa dichiarata: 15% di almeno una scoperta BH.

- giorni nel periodo: 1826
- giorni con ≥ 300 barre RTH: 1755
- giorni con almeno un evento: 1748
- eventi totali: 1748 (long 976, short 772; quota long 55.8%)
- eventi per anno: 248.8

### Test del muro (4 geometrie)

| geometria | n | freq | prior medio | g | CI 95% | p (bootstrap) | soglia BH | scoperta | EV senza costi | R medio dopo costi |
|---|---|---|---|---|---|---|---|---|---|---|
| S0.5_T0.5 | 1748 | 0.514 | 0.500 | +0.0137 | [-0.0103, +0.0372] | 0.2548 | 0.0909 | NO | +0.0275 R | -0.1092 R |
| S0.5_T1.0 | 1748 | 0.348 | 0.333 | +0.0151 | [-0.0072, +0.0374] | 0.1820 | 0.0864 | NO | +0.0452 R | -0.0898 R |
| S1.0_T0.5 | 1748 | 0.687 | 0.667 | +0.0204 | [-0.0013, +0.0416] | 0.0640 | 0.0727 | SI | +0.0306 R | -0.0285 R |
| S1.0_T1.0 | 1748 | 0.511 | 0.500 | +0.0109 | [-0.0126, +0.0338] | 0.3548 | 0.1000 | NO | +0.0217 R | -0.0060 R |

### Esito

**1 geometria/e scoperta/e dal BH** (S1.0_T0.5) → candidato: la geometria con g piu' alto e' **S1.0_T0.5** (g = +0.0204 [-0.0013, +0.0416] CI 95%, p = 0.0640, n = 1748). Autorizza una milestone pre-registrata il cui verdetto e' sull'OOS vergine 2023-10 → 2026-03, mai toccato: la scoperta e' un candidato, non un risultato.

## Candidato 8 — Apertura fuori dalla value area di ieri

Evento: se l'apertura RTH di oggi e' fuori dalla value area (70%) della sessione RTH precedente, un evento per famiglia (R ritorno, C continuazione) alla prima barra RTH. Otto geometrie (2 famiglie x 4 multipli della larghezza della VA precedente; vedi nota nel modulo `nqml/screen/prevva.py` sulla lettura del testo della spec). Attesa dichiarata: 20% di almeno una scoperta BH.

- giorni nel periodo: 1826
- giorni con ≥ 300 barre RTH: 1755
- giorni con almeno un evento: 1191
- eventi totali: 2382 (long 1191, short 1191; quota long 50.0%)
- eventi per anno: 339.1

### Test del muro (8 geometrie)

| geometria | n | freq | prior medio | g | CI 95% | p (bootstrap) | soglia BH | scoperta | EV senza costi | R medio dopo costi |
|---|---|---|---|---|---|---|---|---|---|---|
| R_K0.25 | 1191 | 0.303 | 0.340 | -0.0370 | [-0.0631, -0.0110] | 0.0060 | 0.0545 | SI | +0.0355 R | +0.0409 R |
| R_K0.5 | 1191 | 0.411 | 0.470 | -0.0595 | [-0.0869, -0.0325] | 0.0002 | 0.0182 | SI | -0.0849 R | -0.0196 R |
| R_K0.75 | 1191 | 0.476 | 0.551 | -0.0746 | [-0.1022, -0.0476] | 0.0002 | 0.0227 | SI | -0.0977 R | +0.0428 R |
| R_K1.0 | 1191 | 0.505 | 0.607 | -0.1018 | [-0.1294, -0.0747] | 0.0002 | 0.0273 | SI | -0.1473 R | +0.0161 R |
| C_K0.25 | 1191 | 0.545 | 0.660 | -0.1150 | [-0.1412, -0.0875] | 0.0002 | 0.0318 | SI | -0.1695 R | -0.0813 R |
| C_K0.5 | 1191 | 0.481 | 0.530 | -0.0488 | [-0.0745, -0.0222] | 0.0002 | 0.0364 | SI | -0.0733 R | -0.0667 R |
| C_K0.75 | 1191 | 0.377 | 0.449 | -0.0724 | [-0.0981, -0.0459] | 0.0002 | 0.0409 | SI | -0.0637 R | -0.0750 R |
| C_K1.0 | 1191 | 0.313 | 0.393 | -0.0796 | [-0.1046, -0.0539] | 0.0002 | 0.0455 | SI | +0.0802 R | -0.0438 R |

### Esito

**8 geometria/e scoperta/e dal BH** (R_K0.25, R_K0.5, R_K0.75, R_K1.0, C_K0.25, C_K0.5, C_K0.75, C_K1.0) → candidato: la geometria con g piu' alto e' **R_K0.25** (g = -0.0370 [-0.0631, -0.0110] CI 95%, p = 0.0060, n = 1191). Autorizza una milestone pre-registrata il cui verdetto e' sull'OOS vergine 2023-10 → 2026-03, mai toccato: la scoperta e' un candidato, non un risultato.

## Sintesi — i 22 test del lotto 5-8 (BH q = 0,10)

| candidato | geometria | n | g | p | soglia BH | scoperta |
|---|---|---|---|---|---|---|
| Candidato 5 — VWAP | TVWAP_A1.0 | 2183 | -0.0187 | 0.0504 | 0.0682 | SI |
| Candidato 5 — VWAP | TVWAP_A1.5 | 2183 | -0.0155 | 0.1200 | 0.0818 | NO |
| Candidato 5 — VWAP | TVWAP_A2.0 | 2183 | -0.0236 | 0.0210 | 0.0591 | SI |
| Candidato 5 — VWAP | TMID_A1.0 | 2183 | -0.0213 | 0.0410 | 0.0636 | SI |
| Candidato 5 — VWAP | TMID_A1.5 | 2183 | -0.0096 | 0.3482 | 0.0955 | NO |
| Candidato 5 — VWAP | TMID_A2.0 | 2183 | -0.0161 | 0.1140 | 0.0773 | NO |
| Candidato 6 — Overnight | S1.0_T1.0 | 1694 | +0.0732 | 0.0002 | 0.0045 | SI |
| Candidato 6 — Overnight | S1.0_T2.0 | 1694 | +0.0586 | 0.0002 | 0.0091 | SI |
| Candidato 6 — Overnight | S2.0_T1.0 | 1694 | +0.0482 | 0.0002 | 0.0136 | SI |
| Candidato 6 — Overnight | S2.0_T2.0 | 1694 | +0.0431 | 0.0004 | 0.0500 | SI |
| Candidato 7 — Ultima ora | S0.5_T0.5 | 1748 | +0.0137 | 0.2548 | 0.0909 | NO |
| Candidato 7 — Ultima ora | S0.5_T1.0 | 1748 | +0.0151 | 0.1820 | 0.0864 | NO |
| Candidato 7 — Ultima ora | S1.0_T0.5 | 1748 | +0.0204 | 0.0640 | 0.0727 | SI |
| Candidato 7 — Ultima ora | S1.0_T1.0 | 1748 | +0.0109 | 0.3548 | 0.1000 | NO |
| Candidato 8 — Apertura fuori VA | R_K0.25 | 1191 | -0.0370 | 0.0060 | 0.0545 | SI |
| Candidato 8 — Apertura fuori VA | R_K0.5 | 1191 | -0.0595 | 0.0002 | 0.0182 | SI |
| Candidato 8 — Apertura fuori VA | R_K0.75 | 1191 | -0.0746 | 0.0002 | 0.0227 | SI |
| Candidato 8 — Apertura fuori VA | R_K1.0 | 1191 | -0.1018 | 0.0002 | 0.0273 | SI |
| Candidato 8 — Apertura fuori VA | C_K0.25 | 1191 | -0.1150 | 0.0002 | 0.0318 | SI |
| Candidato 8 — Apertura fuori VA | C_K0.5 | 1191 | -0.0488 | 0.0002 | 0.0364 | SI |
| Candidato 8 — Apertura fuori VA | C_K0.75 | 1191 | -0.0724 | 0.0002 | 0.0409 | SI |
| Candidato 8 — Apertura fuori VA | C_K1.0 | 1191 | -0.0796 | 0.0002 | 0.0455 | SI |

**16 scoperta/e su 22 test** al livello BH q = 0.10.

## Matrice di sovrapposizione fra i setup (candidati 1-8)

Per ogni coppia ORDINATA (riga, colonna): quota degli eventi della riga che hanno un evento della colonna nello stesso giorno, stesso lato, entro 15 minuti (`signal_ts`). Descrittiva: nessun criterio, non decide nulla da sola — serve solo a sapere se un ibrido futuro aggiungerebbe informazione o conterebbe due volte la stessa operazione (spec §2).

| da \\ a | orb15 | gap | firsthour | vabreak | vwap | overnight | lasthour | prevva |
|---|---|---|---|---|---|---|---|---|
| orb15 | — | 10.2% | 29.6% | 70.3% | 2.5% | 0.0% | 0.8% | 7.4% |
| gap | 7.7% | — | 0.0% | 58.6% | 0.0% | 0.0% | 0.0% | 69.4% |
| firsthour | 38.9% | 0.0% | — | 25.3% | 0.1% | 0.0% | 2.6% | 0.0% |
| vabreak | 47.1% | 50.6% | 10.0% | — | 1.8% | 0.0% | 0.7% | 35.0% |
| vwap | 2.9% | 0.0% | 0.1% | 4.0% | — | 0.0% | 0.5% | 0.0% |
| overnight | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | — | 0.0% | 0.0% |
| lasthour | 1.1% | 0.0% | 2.9% | 2.1% | 0.6% | 0.0% | — | 0.0% |
| prevva | 7.9% | 98.1% | 0.0% | 57.2% | 0.0% | 0.0% | 0.0% | — |

## Come leggere questa tabella

`g` è lo scarto tra la frequenza osservata (target prima dello stop) e il prior di passeggiata aleatoria `1/(1+rr)`. Il controllo di molteplicita' e' Benjamini-Hochberg (q = 0,10) sui 22 test di questo lotto: una geometria e' una **scoperta** se il suo p-value e' minore o uguale alla soglia BH assegnata al suo rango nell'ordinamento crescente dei p-value dell'intero lotto (non alla sua posizione naturale nella tabella). Una scoperta autorizza una milestone pre-registrata, il cui verdetto e' sull'OOS vergine, non su questi anni: e' un candidato, non un risultato. «EV senza costi» ed «R medio dopo costi» sono descrittivi: entrano nella lettura ma non nel criterio. Nessun filtro e' stato applicato: questo e' il setup nudo di ciascun candidato.
