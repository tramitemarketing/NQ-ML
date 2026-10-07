# r5_amd — pre-registrazione (2026-09-28, PRIMA di guardare qualunque risultato)

## Da dove viene
Video YouTube «How to trade high RR the RIGHT way (trend days vs reversal days)», Tmac, caricato il
2026-09-27 (https://www.youtube.com/watch?v=30mgndqOOk0). Modello ICT «AMD» (accumulazione →
manipolazione → distribuzione, alias Power of 3 / Judas swing). La tesi, in sintesi:

1. Asia e Londra **accumulano**; all'apertura di New York il prezzo **manipola** (spazza la liquidità
   oltre il massimo/minimo notturno, «Judas swing»).
2. Uno short **contro trend** su una settimana rialzista è lecito **solo** se la manipolazione finisce
   dentro un **PD array di timeframe alto** (order block a 4 ore): lì finiscono sia la manipolazione
   intraday sia la distribuzione del timeframe alto.
3. Ingresso: limite alla **mitigazione dell'order block a 2 minuti** formato in manipolazione (senza
   aspettare la rottura di struttura). Stop sopra il massimo della manipolazione.
4. Obiettivi: l'ultimo swing di accumulazione in Asia / il minimo asiatico, oppure l'apertura del giorno
   («daily key open»); il giorno «gira la candela giornaliera». Rapporto rischio/rendimento dichiarato 12R.
5. Le prove del video sono P&L di membri del Discord su **un** giorno: aneddoti, con selezione del
   sopravvissuto; non entrano nella valutazione.

## Traduzione meccanica (fissata ora; orari NY, sessione `core` = dalle 18:00 del giorno prima)
Descritta per lo **short** (manipolazione al rialzo); il long è lo specchio esatto.

- **Accumulazione (notte)**: barre 18:00 → 08:29. `ON_high`, `ON_low`. `Asia` = 18:00 → 23:59:
  `asia_low`, `asia_high`. `midnight_open` = open della barra 00:00 (la «daily open» ICT).
- **Order block a 4 ore (ribassista)**: barre 4h allineate alle 18:00 NY (18, 22, 02, 06, 10, 14), da
  `adj_*`. Un OB ribassista è l'ultima candela 4h rialzista (close > open) seguita **subito** da una candela
  4h che chiude sotto il suo minimo (spostamento). Zona = [open, high] della candela rialzista. L'OB è noto
  solo alla chiusura della candela di spostamento. Resta valido finché il prezzo (1m, `adj_high`) non
  rientra nella zona (prima mitigazione = il tocco che usiamo; dopo il primo tocco è consumato) e al
  massimo per 30 sessioni.
- **Manipolazione**: finestra 08:30 → 11:59. Il primo istante in cui il massimo 1m della sessione supera
  `ON_high` di almeno 1 tick («liquidità esterna presa») **e**, nella stessa sessione dalle 08:30, il
  prezzo ha toccato un OB 4h ribassista valido (`adj_high` ≥ fondo della zona). Si prende il primo evento
  della sessione in cui valgono entrambe.
- **OB a 2 minuti di manipolazione e ingresso**: dopo l'evento, barre 2m (allineate ai minuti pari). Si
  segue il massimo in corso `M`. L'OB 2m = l'ultima candela 2m rialzista prima della candela 2m che fa
  `M`; quando una candela 2m chiude sotto il suo minimo (spostamento) si piazza un **limite di vendita
  all'open** di quella candela rialzista. Se prima dello spostamento il prezzo fa un nuovo massimo, si
  ricalcola. Riempimento solo se il prezzo **supera il limite di 1 tick** (trade-through, lezione di
  r2_execution), entro le 12:59; altrimenti nessun trade.
- **Stop**: `M` + 1 tick (M = massimo della manipolazione fino al riempimento). Se nella barra di
  riempimento si tocca anche lo stop, conta lo stop.
- **Obiettivo primario**: `asia_low` (se già sotto l'ingresso − 1R non ha senso ICT: in quel caso si usa
  comunque `asia_low`, ma serve `asia_low` < ingresso, altrimenti niente trade). Uscita a tempo 15:59 al
  close. Stop e obiettivo nella stessa barra: conta lo stop.
- Un trade per sessione al massimo; si valuta prima lo short o il long a seconda di quale evento arriva
  prima.

## Test primario (uno solo, dichiarato ora)
`P0`: regola sopra, entrambi i lati, 2010-06 → 2018-12, P&L in **punti netti** (0,75 a/r) per contratto,
bootstrap a blocchi per giorno. Criteri di discovery per promuovere a candidato (più severi del minimo
del protocollo, perché i candidati buttati in validazione consumano il blocco): netto > 0 con p < 0,05,
netto − beta > 0, ≥ 6/9 anni positivi, positivo senza i 20 migliori. **Nota pre-registrata**: una
strategia «ad alto R» vive di pochi grandi vincitori; se fallisce il criterio dei 20 migliori, fallisce —
il criterio non si cambia.

## Controlli (dichiarati ora, per dire *cosa* eventualmente funziona)
- `C1` stesso ingresso **senza** la condizione OB 4h (solo Judas oltre il massimo notturno).
- `C2` OB 4h toccato **senza** la presa del massimo notturno.
- `C3` placebo: zona OB spostata di ±k giorni (OB di un'altra data, stessa larghezza) — la zona finta
  deve rendere meno della vera.
- `C4` specchio: stessa situazione, lato opposto (continuazione) con stop/obiettivo speculari in R.
- `C5` controtendenza vs a favore: il video dice che il valore è nello short contro una settimana
  rialzista. Trend = segno di (close RTH di ieri − close RTH di 5 sessioni prima). Si riportano entrambe le
  metà; nessuna delle due è promossa se il totale P0 fallisce, salvo che la metà contro-trend sia la tesi
  esplicita del video (lo è): quindi `P0_ct` (solo contro-trend) è il **secondo** test pre-registrato,
  con soglia p < 0,025 (Bonferroni su 2).

## Sensibilità (solo descrittive, non promuovono nulla da sole)
Zona OB [low, high] invece di [open, high]; età massima OB 10 / 60 sessioni; finestra di manipolazione
fino alle 10:59 / 12:59; obiettivi alternativi: `midnight_open`, 2R, 3R, uscita 15:59 senza obiettivo;
ingresso a mercato alla chiusura della candela di spostamento invece del limite.

## Regole del laboratorio che valgono qui
Ogni test guardato va in `lab/ledger/r5_amd.jsonl`. Solo discovery. Nessun ritocco del primario dopo averlo
visto: le varianti sono sensibilità, e se una variante «vince» non diventa il candidato senza pagare il
numero di tentativi (e comunque non in questo giro). Validazione solo per candidati congelati, una volta,
e solo dopo aver scritto il piano in `lab/PROTOCOLLO.md`. Onestà dichiarata: il 2019-2023 ha già visto
`micro_overnight_break_fade` (fade della prima rottura del range notturno, bocciato in validazione);
P0 ne è parente (richiede in più l'OB 4h, l'ingresso a mitigazione, lo stop strutturale e il target
asiatico): se P0 funziona **solo** perché ricalca quel fade, C1 lo mostrerà.

## Addendum 1 (2026-09-28, DOPO aver visto P0/controlli/anatomia, PRIMA di far girare le proposte)
Visto: P0 −0,26 netti (1/9 anni), P0_ct −0,89; R lordo +0,03 [−0,19; +0,26]; il costo vale 0,19R a trade
(stop mediano 4 punti); 10R+ nello 0,9 % dei trade. Tre proposte, scritte ora, motivate da questa anatomia
(quindi **non** fuori campione rispetto al discovery: sono a posteriori e lo dichiaro):
- `PA` stop largo: stop = max(M + 1 tick, ingresso + 0,10·ATR20) — il costo pesa meno in R.
- `PB` obiettivo raggiungibile: solo se (ingresso − minimo asiatico) ≤ 0,5·ATR20.
- `PC` «gira la candela»: short solo se l'ingresso è sopra l'apertura di mezzanotte, obiettivo = apertura
  di mezzanotte (specchio per il long).
Regola: una proposta diventa candidato solo se in discovery supera tutti e quattro i criteri con p < 0,05/3
e il p beta-corretto sotto la stessa soglia. Altrimenti la famiglia consegna zero candidati.
