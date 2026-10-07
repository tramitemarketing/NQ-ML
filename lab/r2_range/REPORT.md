# Famiglia r2_range (giro 2): la volatilità prevista usata per la DIREZIONE

**Registro:** `lab/ledger/r2_range.jsonl`, **590 test** guardati (tutti sul discovery 2010-06-07 → 2018-12-31).

**Esito in breve:** l'idea guida (usare la previsione del range per decidere il verso) **non regge**:
fade dell'estremo a bilancio esaurito, rottura tardiva a bilancio basso, apertura lontana dal centro,
bande come livelli da fadeare e sorpresa di volatilità non danno nulla sopra i costi. Resta **una sola
regola** (rottura della banda «chiusura di ieri ± 0,9 range previsti», nel verso della rottura), presentata
in due binari (tradeable + regolarità in unità di R). Avvertenza: il placebo mostra che la previsione
*giornaliera* della vol spiega al più un terzo dell'effetto.

## Strumento: previsione del range (h00)
`common.forecast`: y = log(range RTH in % dell'open); regressori = y di ieri, media 5, media 22 (sessioni
valide precedenti), log(range notturno 18:00-09:29). OLS mobile 500 sessioni (min 150), stimata solo su
sessioni < t; smearing per riportare la media. Nota alle 09:30 (l'open grezzo serve solo a convertire in
punti). R² fuori campione su log range **0,571** contro **0,460** della media a 20 giorni; rapporto
realizzato/previsto medio 1,01 (calibrata). Il 2010 fa da warmup (primo trade possibile: febbraio 2011).

Esecuzione (`common.sim`): segnale alla close della barra, ingresso all'open della successiva, stop al
livello o all'open se la barra apre oltre, target solo con trade-through di 1 tick, stop e target nella
stessa barra → stop, uscita a tempo alla close della barra 15:59. Costi 0,75 punti. Unità di decisione:
netto in punti; diagnostica in unità di R_hat. Beta = `controller.beta_component`.

## Ipotesi provate (griglie dichiarate nell'intestazione di ogni script prima di eseguirlo)

| script | ipotesi | test | esito |
|---|---|---|---|
| h00 | qualità della previsione (strumento) | 2 | R² 0,571 contro 0,460 |
| h01 | **bilancio esaurito → fade dell'estremo**: primo istante 10-15 in cui il range percorso raggiunge k·R_hat (k 0,5 controllo / 0,75 / 1 / 1,25), fade e continuazione, stop, target, 60m/EOD, placebo | 99 | **Falsa.** Lordo in R ≈ 0 ovunque (\|gross_R\| < 0,015). Primario dichiarato (k=1, stop 0,3R, EOD): **−1,89 punti netti**, 2/8 anni. Placebo R_naive e R rimescolato: uguale. |
| h02 | stesso bilancio a orari fissi (10:30-14:30) × posizione nel range; fade degli estremi e continuazione della giornata per cella di u | 80 | Il fade degli estremi a bilancio alto **perde** (u 0,8-1,1: in media −2,8 netti a EOD): se mai gli estremi a bilancio esaurito continuano. Nessuna cella regge. |
| h03 | **apertura lontana dal centro** del range previsto: z = (open − close ieri)/R_hat e (open − centro notte)/R_hat; fade 09:31→10:30/12:00/15:59 | 24 | Niente per soglie basse; per \|z_pc\| > 0,5 fade fino alle 12:00 +3,78 netti p 0,011 (n 413) → approfondito in h08c. |
| h04 | **bande di vol previste come livelli**: ancora (open, close ieri) ± h·R_hat, primo tocco 09:45-15:00, fade e rottura, stop, target, 60m/EOD | 98 | **Il fade delle bande perde ovunque** (primario dichiarato −0,85, 1/8 anni; placebo rimescolato −1,04). Unica zona positiva: **rottura** della banda ancorata alla **chiusura di ieri**, h=0,75, uscita EOD (+2,0/+2,2, p 0,003-0,005). |
| h05 | **sorpresa di vol** della prima ora (range 9:30-10:29 / R_hat, percentile causale): effetto leva (short se sorpresa alta), continuazione/fade del primo movimento | 16 | Leva: lordo +0,04 R a EOD ma p 0,18-0,29. Niente. |
| h06 | **range sotto il previsto a metà giornata → rottura tardiva** (T 12/13/14, u < 0,4/0,5/0,6 contro controllo) | 72 | **Falsa.** I giorni compressi non recuperano range (estensione residua uguale o minore) e la rottura tardiva perde (compressi: −1,25 netti in media). |
| h07 | approfondimento della rottura banda-chiusura-di-ieri: griglia h 0,5-1,25 × stop × finestra, regimi, lati, specchio, placebo | 61 | **Plateau** positivo per h 0,75-1,0 con stop 0,1-0,3 (p 0,0003-0,015); h ≤ 0,6 e h = 1,25 non significativi; senza stop più debole. |
| h08b | specchio di h02: continuazione dall'estremo alle 13:30-15:00 con bilancio alto | 97 | Debole e instabile (2/8-5/8 anni); parente del momentum di fine giornata del giro 1. Scartata. |
| h08c | fade del gap in unità di R (da h03), griglia g × uscita | 17 | Monotono in g ma **drop20 negativo ovunque**, 2018 dominante, 4-7/8 anni; i gap erano già falliti al giro 1. Scartato. |
| h09, h10 | controlli finali sul punto scelto; regolarità del gap in R; placebo | 24 | vedi sotto |

## Il candidato: rottura della banda «chiusura di ieri ± 0,9·R_hat»

Regola (congelata in `candidates.py`): bande = close RTH di ieri ± 0,9·R_hat; al primo tocco (1 tick oltre)
fra 09:45 e 15:00 di una banda non già superata prima delle 09:45, ingresso nel verso della rottura
all'open della barra dopo, stop 0,2·R_hat, uscita 15:59; un trade al giorno.

**Scelta post hoc, dichiarata:** il punto dichiarato prima di guardare era h=0,75 (in h04 e h07); h=0,9 è il
centro del plateau {0,75; 0,9; 1,0} scelto dopo aver visto la griglia di h07.

| misura (discovery) | valore |
|---|---|
| n (sessioni) | 617 (feb 2011 - dic 2018) |
| netto medio, CI 95 % a blocchi per giorno | **+3,11 punti [+1,30; +5,02]**, p unilaterale 0,001 |
| lordo | +3,86 punti; in unità di R **+0,069 [+0,038; +0,101]**, p bilaterale 0,0001 |
| anni positivi (netto) | **7/8** (2011 −0,30; 2018 +10,65); in unità di R **8/8** (da +0,026 a +0,122) |
| senza i 20 migliori | **+0,12** (marginale; a h=0,75 era −0,32) |
| netto − beta | +3,10 (p 0,001); quota long 0,49 → beta trascurabile |
| senza il 2018 | +1,86 [+0,39; +3,35] |
| costo 1,25 punti | +2,61 |
| ingresso 1 minuto dopo | +3,66 |
| trigger su chiusura oltre la banda | +2,84 (drop20 −0,20) |
| solo long / solo short | +3,16 (p 0,001) / +1,20 (p 0,19) |
| mattina (< 12:00) / pomeriggio | +3,40 (n 403) / +2,57 (n 214, p 0,08) |
| terzili di regime di vol (a h=0,75) | basso −0,42, medio +2,72, alto +4,42 (il costo pesa meno a vol alta) |
| specchio (fade, stessa geometria) | −1,06 |
| ancora = open RTH invece della chiusura di ieri | −0,39 (niente) |
| R_naive (media 20 range) al posto di R_hat | +2,67, 8/8 anni |
| **R_hat rimescolato fra sessioni dello stesso anno (10 semi)** | **media +2,20**; 1 seme su 10 ≥ +3,11 |
| uscite | 56 % in stop, 44 % a fine giornata |

**Lettura onesta.** Il segnale vive sull'ancora (la chiusura di ieri: ancorato all'open non funziona) e sulla
dimensione del movimento in unità di volatilità *tipica*; la previsione *giornaliera* della volatilità (la
regolarità confermata al giro 1) aggiunge circa un punto su tre e non in modo distinguibile dal placebo.
Quindi la risposta alla domanda della famiglia («la vol prevista serve per la direzione?») è sostanzialmente
**no**: serve come unità di misura, ma una media mobile del range fa quasi lo stesso lavoro. È un payoff da
trend-following (56 % dei trade chiude in stop, coda destra), quindi è esposto al criterio «senza i 20
migliori», che passa per un soffio. È parente, anche se non identico, dell'intraday momentum della
letteratura (movimento dalla chiusura di ieri → continuazione fino alla chiusura) e del candidato bocciato
`intraday_momentum_hivol_last30`: non è un ripescaggio (ingresso all'evento, non a orario fisso; soglia in
unità di vol; nessun filtro di regime), ma la parentela va tenuta presente. Sui 590 test, circa 67 hanno
p < 0,05 (in gran parte griglie correlate della stessa famiglia di bande, contro ~29 attesi per caso): il
candidato è il migliore di una ricerca ampia, e la validazione con Bonferroni è il giudice giusto.

## Candidati congelati (`lab/r2_range/candidates.py`)
1. `r2_range_pcband_breakout`: **tradeable**, n 617, **+3,112 netti [+1,30; +5,02]**, p 0,001, 7/8 anni,
   drop20 +0,124, netto−beta +3,10. warmup 560.
2. `r2_range_pcband_breakout_R`: **regularity**, stessa regola, quantità = lordo/R_hat, segno atteso +1;
   n 617, **+0,0687 [+0,038; +0,101]**, p bilaterale 0,0001, 8/8 anni. Serve a separare «fatto sulla
   dinamica» da «incassabile»: se il netto in punti cade per i 20 migliori o per un anno cattivo, la
   regolarità scale-free può ancora dire se la continuazione esiste. (Stessi trade: le due prove non sono
   indipendenti.)

Test di riproduzione: `.venv/Scripts/python.exe -m lab.r2_range.test_candidates` (gira le fn su
`core.load("discovery")` senza cache e verifica n, media e drop20 dichiarati: OK). Verificato anche che la
fn dia gli stessi trade partendo da una finestra di dati spostata (differenze < 1e-12 punti), cioè che il
warmup funziona come previsto.

## Scartato e perché
- Fade dell'estremo a bilancio esaurito (h01, h02): falso, se mai il segno è opposto.
- Rottura tardiva dopo mattinate compresse (h06): falso; la compressione non si «recupera».
- Fade delle bande di vol (h04): perde ovunque; le bande non sono livelli di inversione.
- Apertura lontana dal centro / gap in unità di R (h03, h08c, h09B): pochi eventi, drop20 negativo, 2018
  dominante, soglia 0,4 non significativa; variante di un'idea già bocciata.
- Sorpresa di volatilità → direzione (h05): segno «leva» plausibile ma non significativo.
- Continuazione dall'estremo nel pomeriggio (h08b): instabile, troppo vicina al momentum di fine giornata.

## Note tecniche
- Cache locale del solo discovery in `data/lab/r2_range_disc.pkl` (generata dal codice stesso, usata dagli
  script esplorativi). Le fn dei candidati NON la usano.
- `h09_final_checks.py` si è interrotto una volta per un bug di maschera dopo aver registrato 7 test; la
  ripresa (`--rest`) ha registrato solo i test mancanti: nessun duplicato nel registro (verificato).
- Nessun bug trovato in `core.py`.
