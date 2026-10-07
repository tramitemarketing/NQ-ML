# Famiglia «wild»: calibrazione del caso e idee selvagge

Fase: **solo discovery** (2010-06-07 → 2018-12-31, 2.121 sessioni valide). Unità dichiarata prima di
guardare: **punti NQ netti per 1 contratto** (costo 0,75 punti a/r), lo stesso metro dei criteri del
PROTOCOLLO. Bootstrap `core.day_block_bootstrap` (10.000 repliche, seme 0) ovunque.

**Registro `lab/ledger/wild.jsonl`: 1.362 righe** = 1.266 regole-placebo (`placebo_*`) + 1 riga
descrittiva (`placebo_descr_*`, non è un test) + 95 test su idee selvagge (`wild_*`; 93 distinti, 2
sono ripetizioni identiche dentro una griglia di sensibilità: `W03g_w120_h60` = `W03m_speedasym_gross2_h60`,
`W12s_fresh_w120_f15` = `W12_records_fresh_close`).

**Candidati consegnati: zero.** Motivazione nella sezione 3.

---

## 1. Calibrare il caso (risultato centrale per il laboratorio)

### 1.1 Disegno

Regole che **per costruzione non possono avere senso economico**, con la stessa struttura dei test
veri (1-3 trade al giorno, stessi orizzonti, stessi costi, stesso bootstrap, stessi 4 criteri):

- **giorni**: tutti; somma delle cifre di AAAAMMGG pari / dispari; giorno del mese primo; giorno del
  mese di Fibonacci; giorno dell'anno multiplo di 4; hash MD5 della data (mod 2, mod 3); fase lunare
  calcolata (crescente; ±3 giorni dalla luna piena); probabilità casuale da seme fisso;
- **minuto d'ingresso**: fisso estratto da un seme, estratto dall'hash della data, proporzionale alla
  fase lunare, un minuto primo, fino a 3 minuti primi al giorno scelti dall'hash;
- **lato**: sempre long, sempre short, hash della data (nullo simmetrico puro), luna (crescente = long);
- **orizzonti**: 15 min, 60 min, fino alle 16:00 (batterie A/B, tutto in RTH); 15/60/**390 minuti di
  orologio** da un minuto qualunque delle 24 ore (C, attraversa sera/notte, prezzi adj); chiusura →
  chiusura successiva, chiusura → apertura successiva, chiusura → chiusura dopo 5 sessioni non
  sovrapposte (D, E).

| batteria | script | regole | cosa |
|---|---|---|---|
| A | `p01_placebo.py` | 126 | 10 filtri-data × 4 lati × 3 orizzonti (+6 «minuti primi») |
| B | `p01_placebo.py` | 400 | casuali: 200 lato-hash, 100 long, 100 short |
| C | `p02_placebo_notte.py` | 150 | 24 h / RTH, orizzonti di orologio 15/60/390; 50 long / 50 short / 50 hash |
| D | `p02_placebo_notte.py` | 90 | 10 filtri-data × {long, short, hash} × {c2c1, c2o, c2c5} |
| E | `p03_placebo_beta.py` | 500 | multi-sessione casuali: 300 long, 100 short, 100 hash (+ correzione proposta) |

Criteri del PROTOCOLLO **applicati al discovery**: (1) p unilaterale < 0,05 (e < 0,05/24, Bonferroni
con K = 8 famiglie × 3); (2) EV netto meno beta > 0, beta = lato × deriva media della stessa finestra
su tutte le sessioni; (3) EV > 0 in almeno 6 anni su 9 (analogo di 3/5); (4) EV senza i 20 trade
migliori > 0.

Nota di onestà sul disegno: le batterie C, D, E sono state aggiunte **dopo** aver visto A/B, perché in
RTH i placebo long non mostravano la lezione del beta (vedi 1.3). È dichiarato nei docstring.

### 1.2 Risultati

| batteria | lato | N | EV netto medio | beta medio | p<0,05 | p<0,01 | p<0,05/24 | tutti e 4 | tutti e 4 con Bonferroni |
|---|---|---|---|---|---|---|---|---|---|
| A (RTH) | long | 32 | −0,95 | +0,04 | 0 | 0 | 0 | 0 | 0 |
| A | short | 32 | −0,57 | −0,02 | 0 | 0 | 0 | 0 | 0 |
| A | hash | 32 | −0,79 | 0,00 | 0 | 0 | 0 | 0 | 0 |
| A | luna | 30 | −1,20 | +0,01 | 0 | 0 | 0 | 0 | 0 |
| B (RTH) | long | 100 | −0,72 | +0,01 | 0 | 0 | 0 | 0 | 0 |
| B | short | 100 | −0,73 | −0,01 | 0 | 0 | 0 | 0 | 0 |
| B | hash | 200 | −0,76 | 0,00 | 1 | 0 | 0 | 0 | 0 |
| C (24 h, fino a 390 min) | long | 50 | −0,43 | +0,25 | 0 | 0 | 0 | 0 | 0 |
| C | short | 50 | −0,94 | −0,17 | 0 | 0 | 0 | 0 | 0 |
| C | hash | 50 | −0,73 | 0,00 | 0 | 0 | 0 | 0 | 0 |
| D (multi-sessione) | long | 30 | **+3,68** | +4,83 | **9** | 2 | 1 | **4** | 1 |
| D | short | 30 | −5,18 | −4,83 | 0 | 0 | 0 | 0 | 0 |
| D | hash | 30 | −1,77 | −0,02 | 1 | 0 | 0 | 0 | 0 |
| E (multi-sessione) | long | 300 | **+4,38** | +5,12 | **138** | 25 | 3 | **33** | 3 |
| E | short | 100 | −6,11 | −5,48 | 0 | 0 | 0 | 0 | 0 |
| E | hash | 100 | −1,02 | −0,02 | 3 | 1 | 0 | 0 | 0 |
| **totale** | | **1.266** | | | **152 (12,0 %)** | 28 | 4 | **37 (2,9 %)** | **4 (0,32 %)** |

**Tasso di falsi positivi per tipo di test** (la tabella da tenere accanto a ogni risultato del laboratorio):

| tipo di test | p<0,05 | tutti e 4 i criteri | tutti e 4 con Bonferroni 0,05/24 |
|---|---|---|---|
| intraday RTH al netto, lato qualunque (A+B, 526) | **0,2 %** (1/526) | **0 %** | 0 % |
| — di cui «fino alla chiusura», lato simmetrico | 1,5 % (1/67) | 0 % | 0 % |
| fino a 390 min da un minuto qualunque delle 24 h (C, 150) | 0 % | 0 % | 0 % |
| multi-sessione, lato simmetrico (D+E hash, 130) | 3,1 % | 0 % | 0 % |
| **multi-sessione solo long (D+E, 330)** | **44,5 %** | **11,2 %** | **1,2 %** |
| **regolarità: lordo, bilaterale, lato simmetrico (312)** | **3,8 %** (p<0,01: 1,6 %) | — | — |

Calibrazione del bootstrap stesso: sui 312 placebo simmetrici i p-value **lordi** bilaterali sono
uniformi (conteggi per decile 24-32-33-35-38-33-31-26-29-31; KS contro U(0,1) p = 0,68 su A/B). Il test
è onesto; il problema non è lo strumento ma quante volte lo si usa e cosa ci si mette dentro.

### 1.3 Tre lezioni

1. **Al netto dei costi, il caso da solo quasi non produce scoperte intraday.** Con 0,75 punti di costo
   un placebo simmetrico parte da −0,75 e deve superare circa 0,75 + 1,65 errori standard: sugli
   orizzonti 15-60 minuti non succede mai (0 su ~400), «fino alla chiusura» nell'1-1,5 % dei casi.
   Quindi un p<0,05 netto intraday è più raro del 5 % nominale — **ma non raro dopo 100 tentativi**: con
   ~40 test «fino alla chiusura» ci si aspetta mezzo falso positivo per famiglia, di più se le varianti
   sono scelte guardando.
2. **Il binario «regolarità» (lordo, bilaterale) ha il tasso nominale pieno: ~4-5 % a p<0,05.** Una
   famiglia che guarda 100 regolarità ne trova ~4 «significative» per puro caso, ~1-2 a p<0,01.
3. **La lezione del beta, e un buco nel criterio 2 del PROTOCOLLO.**
   - Nel 2010-2018 NQ è salito di 4.525 punti adj: **466 in RTH (10 %) e 4.015 fuori RTH (90 %)**
     (riga `placebo_descr_scomposizione_rth_notte`). Per questo i placebo long **intraday** NON vincono
     per beta (deriva 0,01-0,04 punti per trade, sotto i costi): nessuno dei 132 long di A/B passa.
   - Appena la posizione attraversa la notte, i placebo «solo long» vincono per costruzione: **44,5 %** ha
     p<0,05, gli short perdono tutti. È beta, non abilità. Esempio: «long dalla chiusura RTH all'apertura
     successiva, tutti i giorni» fa +1,14 punti netti, p 0,021; al netto del beta −0,75 (esattamente il costo).
   - **Il criterio 2 non basta a fermarli**: chiede solo «EV − beta > 0», non che sia significativo. Un
     sottoinsieme di giorni scelto a caso ha media sopra quella di tutti i giorni con probabilità ~½, quindi
     l'**11,2 %** dei placebo long multi-sessione passa **tutti e quattro** i criteri, e l'**1,2 %** anche con
     Bonferroni 0,05/24. Esempio: `placebo_D_c2o_hash2_long` (long notturno nei giorni con hash MD5 pari):
     +2,53 netti, p 0,0006, 9/9 anni, +0,96 senza i 20 migliori, beta-aggiustato +0,63 → passa tutto.
     Nella validazione 2019-2023 (mercato che sale) il buco resta aperto.
   - **Correzione proposta al controller (misurata)**: sostituire il criterio 2 con «p unilaterale del
     bootstrap sul rendimento netto **meno** beta < soglia». Sui 300 placebo long della batteria E passano
     **0/300**, sia con soglia 0,05 sia con 0,05/24.

### 1.4 Quante «scoperte» aspettarsi dal laboratorio intero per puro caso

Con i tassi misurati sopra, per N test guardati da una famiglia:
- intraday tradeable, soglia p<0,05 netta: **≈ 0,2-1,5 % di N** (per N = 150: 0-2 falsi positivi);
- regolarità lorde p<0,05: **≈ 4 % di N** (per N = 150: ~6; a p<0,01 ~2);
- strategie sbilanciate long con posizione notturna o multi-giorno: **≈ 45 % a p<0,05, ≈ 11 % passano
  tutti i criteri discovery, ≈ 1 % anche con Bonferroni** — il rischio principale per le famiglie
  «orizzonti multi-giorno», «sessioni notturne» e «calendario».

Su 8 famiglie × ~150 test (≈ 1.200) ci si aspettano quindi **decine di «scoperte» nominali** sul
discovery prodotte dal solo caso, concentrate su regolarità lorde e su tutto ciò che è long di notte.
Nessuna regola placebo intraday (A+B+C, 676) ha passato i quattro criteri.

---

## 2. Idee selvagge (21 idee, 93 test distinti)

Direzione dichiarata nel docstring di ogni script **prima** di guardare (`w01_idee.py`, `w02_idee.py`,
`w04_idee.py`; `w02` e `w03_asimmetria.py` contengono anche controlli POST-HOC, dichiarati come tali).
Soglie solo da quantili mobili dei 250 giorni **precedenti**. Unità: punti netti. Tutti i trade in RTH
(nessun roll). Soglia anni: 6/9.

| idea | meccanismo | test | miglior risultato (netto) | esito |
|---|---|---|---|---|
| W01 attraversamento dei tondi (100/50, prezzo grezzo) | stop oltre i tondi → prosecuzione (Osler 2003) | 4 + 8 specchi | prosecuzione −0,67…−1,97 (0-2/9 anni); specchio «contro» +0,47 (p 0,27) | **scartata**: né prosecuzione né rimbalzo pagano; lordo della prosecuzione a 60 min −1,0/−1,2 (p bil. 0,06/0,11) |
| W02 magnete/pinning verso il tondo alle 15:00/15:30 | pinning (Ni-Pearson-Poteshman) | 4 | +0,39 (15:30, livello 100, p 0,28, n 196) | scartata; alle 15:00 −3,2 |
| W03 asimmetria di velocità salita/discesa → contro | ricopertura forzata transitoria | 3 | tutte negative (−1,1…−1,7) | **ipotesi rovesciata**, vedi W03m |
| W03m (POST-HOC) segui l'asimmetria | — | 2 netti + 2 lordi + 12 griglia + 2 controlli + 1 regressione | netto −0,05 (60 min) / +0,19 (chiusura); **lordo +0,70 [0,14; 1,27], p bil. 0,014, 9/9 anni** | regolarità lorda debole; **non promossa** (sotto) |
| W04 skewness della mattina → contro | idem | 1 | −0,89 | scartata |
| W05 giorni-tipo (k-means K = 4/6/8 sulla forma 09:30-11:30, cross-fitting 2010-14 ↔ 2015-18) | forme ricorrenti | 3 | +0,10 (K = 6, p 0,44) | scartata: la forma della mattina non dice il pomeriggio fuori campione |
| W06 percorso liscio (efficiency ratio alto) → prosecuzione | impronta TWAP di un ordine padre | 3 | +1,10 (p 0,16, 4/9) | scartata |
| W07 profilo del volume piatto → prosecuzione | algoritmo a tempo | 2 | −0,40 | scartata |
| W08 barre di volume anomalo (> 5×/10× mediana del minuto) → prosecuzione | blocco informato | 4 | −0,11 (10×, 60 min) | scartata (lordo ≈ 0) |
| W09 notte con molti minuti vuoti → contro il gap | mossa notturna poco informativa | 3 | notte vuota −1,86; controllo notte piena +0,78 (p 0,17) | scartata; segno opposto all'ipotesi |
| W10 entropia di permutazione bassa → prosecuzione | ordine = trend | 3 | +0,34 (p 0,37) | scartata |
| W11 variance ratio delle 5 sessioni precedenti (regime) | Hurst per regime | 3 | −1,16…−2,03 | scartata |
| W12 ritmo dei nuovi massimi/minimi | pressione persistente | 3 + 13 sensibilità | **record freschi +2,48 [−0,05; 5,10], p 0,029, 6/9 anni, senza i 20 migliori −1,28** | **scartata**: vive solo sulla finestra 120 min, fallisce il criterio 4 ovunque, compatibile col caso |
| W13 cifre dei prezzi (quota di close su punto intero) → contro | flusso «umano» rumoroso | 1 | −1,64 | scartata |
| W14 divergenza volume-prezzo → contro | mattina non confermata dal volume | 2 | −0,84 | scartata |
| W15 magnete all'apertura verso il tondo | pinning | 2 | +0,07 | scartata |
| W16 buco di liquidità (escursione alta, volume basso) → contro | mossa senza informazione | 2 | −0,67 / −0,73 | scartata |
| W17 complessità di Lempel-Ziv bassa → prosecuzione | ordine = trend | 1 | −1,36 (0/9) | scartata |
| W18 orologio degli algoritmi (barre :00/:15/:30/:45) → prosecuzione | ordini figli a orario | 2 | −1,04 / −1,05 | scartata |
| W19 volume anomalo 14:00-15:30 → segui fino alle 16:00 | impronta MOC/VWAP | 2 | +0,06 | scartata |
| W20 estremo della mattina su multiplo di 25 → contro | resistenza ai tondi (Osler 2000) | 2 + 2 controlli | n = 26, non informativo; controllo −0,73/−1,55 | scartata |
| W21 Hurst R/S delle 20 sessioni precedenti (regime) | persistenza | 3 | −0,18 | scartata |

Riepilogo sui test netti delle idee (76): **4 con p<0,05 — tutti la stessa idea W12 e sue varianti —,
0 con p<0,01, 0 passano i quattro criteri.** Test lordi di regolarità (18): 3 con p bilaterale < 0,05,
tutti W03m/W03g (e uno è un duplicato). In linea con quanto il caso produce (sezione 1).

### W03m nel dettaglio (perché non è promossa)
- L'ipotesi dichiarata era l'opposto («salite violente → il pomeriggio va contro»): lo specchio è scelto
  dopo aver visto, quindi porta sulle spalle tutti i ~95 tentativi della famiglia.
- Griglia finestra {60, 90, 120, 150} × orizzonte {30, 60, 90}: 11/12 celle positive sul lordo ma solo 2
  con p<0,05 (w90/h90 +0,97, p 0,008; w120/h60 +0,70, p 0,014); le altre +0,02…+0,49. Non vive su un solo
  valore, ma è piccola: **mai sopra i costi** (netto del «segui» −0,05 a 60 min).
- **Controllo di confusione**: regressione HC1 del rendimento 11:30-12:30 su segno(asimmetria), segno e
  ampiezza della mattina: coefficiente dell'asimmetria +0,41 punti, **t = 1,03 (p 0,31)**; l'ampiezza della
  mattina assorbe il resto (t 1,75). È in gran parte **momentum della mattina travestito**, territorio della
  famiglia «momentum intraday», non un fatto nuovo. (In unità di range mattutino: +0,020, p bil. 0,017.)
- Con 18 test lordi il caso ne produce in media ~0,7 a p<0,05 (tasso 3,8 %); due celle correlate della
  stessa idea non sono un segnale distinguibile.

### W12 nel dettaglio
Regola: alle 11:30, se l'ultimo nuovo massimo/minimo della mattina è negli ultimi 15 minuti, segui il
segno di (#nuovi massimi − #nuovi minimi) fino alle 16:00. Netto +2,48 (n 649), p 0,029, 6/9 anni, ma
senza i 20 trade migliori −1,28 (lotteria), e la sensibilità cade: finestra 90 min +0,22…+2,08 (p ≥ 0,10),
150 min +0,48…+0,98 (p ≥ 0,24), freschezza 30 min +0,74 (p 0,22). Il placebo simmetrico «fino alla
chiusura» dà p<0,05 netto nell'1,5 % dei casi: su ~40 test «fino alla chiusura» della famiglia ci si
aspetta ~0,6 falsi positivi. È anche parente stretto del momentum intraday (altra famiglia).

---

## 3. Candidati

**Nessuno** (`candidates.py`: `CANDIDATES = []`, con test minimo). Nessuna idea selvaggia soddisfa i
quattro criteri sul discovery. Le due più vicine falliscono: W12 il criterio 4 e la sensibilità; W03m non
è al netto dei costi e non è un fatto nuovo. Mandarle comunque in validazione alzerebbe K e con esso
la soglia 0,05/K di tutte le altre famiglie: il costo per il laboratorio supera il valore atteso.

## 4. Note per il controller

1. **Criterio 2 (beta) da irrobustire prima della validazione**: così com'è lascia passare l'11 % dei
   placebo long multi-sessione (1,2 % anche con Bonferroni). Proposta misurata: p del bootstrap sul netto
   meno beta < 0,05/K (0/300 placebo passano). Va applicata soprattutto ai candidati di «orizzonti
   multi-giorno», «sessioni notturne», «calendario».
2. **Per leggere i registri delle altre famiglie**: confrontare le regolarità lorde con p<0,05 con ~4 %
   dei test; i p<0,05 netti intraday con ~0,2-1,5 %; qualunque long notturno/multi-giorno con il 45 %.
3. `core.py`: nessun bug trovato. Osservazione: con `n_boot` = 10.000 la risoluzione del p è 1e-4,
   sufficiente per 0,05/K fino a K ≈ 100.
4. File: `common.py`, `features.py` (infrastruttura), `p01/p02/p03_placebo*.py`, `w01/w02/w04_idee.py`,
   `w03_asimmetria.py`, `s01_sintesi.py` (legge solo il registro), CSV dei risultati per ogni giro.
