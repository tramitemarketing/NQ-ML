# Famiglia r2_execution (giro 2): esecuzione aggressiva contro passiva

Solo discovery (2010-06-07 → 2018-12-31). Registro `lab/ledger/r2_execution.jsonl`: **203 righe = 1 PIANO
+ 202 test**, ognuno guardato. **Candidati: zero.**

## In una riga
Con una simulazione conservativa degli ordini limite (eseguiti solo con trade-through di 1 tick),
**l'esecuzione passiva non cambia il segno del netto di nessun segnale**. Sui segnali senza vantaggio
il costo per trade eseguito resta **~0,70-0,80 punti, cioè quanto quello aggressivo (0,75)**: la
selezione avversa si mangia tutto lo spread risparmiato. Sui segnali con vantaggio il passivo perde i
trade migliori, che sono quelli che scappano senza eseguirlo.

## Regole di simulazione (fissate prima di guardare: riga PIANO e docstring di `common.py`)
- Segnale noto alla chiusura della barra 1m i. Uscita a tempo sullo **stesso orologio** per le due
  esecuzioni. Prezzi adj. Unità: **punti netti per segnale**. I segnali passivi non eseguiti contano 0 e
  restano nel denominatore; il tasso di riempimento è sempre riportato.
- **AGG**: open della barra i+1, costo 0,75 (convenzione del progetto; la media AGG di
  `hivol_last30` riproduce esattamente il +2,29 del giro 1, verificato in `test_candidates.py`).
- **PAS**: limite a c_i ∓ off, eseguito solo se una barra successiva, entro N minuti, scambia **1 tick
  oltre** il limite. Il prezzo è quello del limite, senza miglioramenti. Nella barra del fill si
  controlla solo lo stop, mai il target. Il target è a limite, senza slippage, con la stessa regola di
  trade-through. Stop e tempo sono a mercato con 1 tick di slippage. Commissioni sempre (0,25 a/r).
  Sensibilità a **2 tick**; «touch» (eseguito al solo tocco) è una diagnostica ottimista, mai usata per
  decidere.
- **Selezione avversa (AS)** = lordo AGG dei segnali mancati − lordo AGG dei segnali eseguiti in PAS.
- Beta: stesso metodo del controller. Non sovrapposizione indipendente dall'esecuzione, così AGG e PAS
  vedono gli stessi segnali. Anni, senza i 20 migliori e beta sono in ogni riga del registro.

## Batterie e risultati

### B0: placebo (24 test). La calibrazione che decide tutto
Lato e istante casuali, RTH ed ETH, uscita a 15 o 60 minuti, off {0, 2 tick, 0,5·σ60·√5}, N {5, 15}.
- Il netto PAS per segnale va da −0,24 a −0,93: **0/24 positivi**, quasi ovunque 0/9 anni. Il
  simulatore non è ottimista.
- **Per trade eseguito** il PAS perde da −0,64 a −1,09, contro −0,76/−0,99 dell'AGG sugli stessi
  segnali. Il passivo «costa meno» per segnale solo perché fa meno trade.
- AS sempre molto positiva (+1 … +6 punti): i limiti eseguiti sono quelli in cui il prezzo continua
  contro. Con il trade-through di 1 tick, il riempimento equivale in media a pagare lo spread.
- Col «touch» ottimista il guadagno per trade è di appena ~0,1-0,15 punti. Anche il simulatore più
  generoso non trasforma il passivo in un vantaggio.

### B1: segnali del giro 1, AGG vs PAS (51 test)
Ricostruiti importando le funzioni congelate (non modificate); off {0, 2t, 0,5σ5}, N {5, 15, orizzonte}.

| segnale | AGG netto | PAS netto (intervallo sulla griglia) | riempimento | AS | esito |
|---|---|---|---|---|---|
| fade prima rottura del range notturno | +1,23 | +0,79 … +1,20 | 0,64-0,95 | +5 … +15 | PAS ≤ AGG, d20 < 0 |
| sorpresa 15 m → 30 m (non sovrapposta) | +0,28 | +0,36 … +0,41 | 0,65-0,98 | +3,5 … +7,5 | +0,1 migliore, p ≥ 0,11; a 2 tick +0,10…+0,20 |
| ultima mezz'ora, tutti i giorni | −0,13 | −0,18 … +0,02 | 0,58-0,97 | +3 … +10 | resta ~0 / negativo |
| ultima mezz'ora, alta vol | +2,29 | +1,39 … +2,05 | 0,62-0,97 | +6 … +16 | **PAS peggiore** di 0,25-0,9 |
| turnaround Tuesday | +7,36 | +6,53 … +7,58 | 0,84-0,99 | +2,5 … +29 | invariato (il costo conta poco su 150 m) |
| RTH → sera | −0,43 | −0,83 … −0,28 | 0,30-0,84 | +1,9 … +3,4 | **PAS peggiore** per trade eseguito |

Lezione: sui segnali di momentum il limite viene eseguito proprio quando il segnale sbaglia, e i trade
mancati valgono in media da +4 a +17 punti lordi. Nessun segno cambia.

### B2: fornitura di liquidità OCO a fasce di volatilità prevista (36 test)
Ogni 15 minuti, acquisto a c − k·sW e vendita a c + k·sW (sW = σ60·√15), attesa 15 m, k {1, 2, 3}, uscita a
tempo 30 m / target 1·sW + 30 m / target + 60 m; finestre apertura, mezzogiorno, RTH, notte.
**36/36 con netto ≤ +0,01**, 0 significativi. Per trade eseguito si perde di più quanto più le fasce
sono lontane (k=1 circa −0,7; k=3 fino a −1,3 in RTH): chi arriva a k·σ è un movimento che continua,
come dice la regolarità di continuazione del giro 1. La notte non aiuta (per trade circa −0,7/−1,5).
Nota: per l'OCO la colonna AGG del registro non è un confronto valido, perché il lato è scelto dal
fill; conta solo il netto PAS.

### B3: mean reversion con limite (32 test)
Fade di r30 o della distanza dalla media 60 m oltre z·σ {1, 2}, mezzogiorno 12:30-15:00 o RTH, uscita
30/60 m, off {0, 0,5σ5}. **Già il lordo AGG è ≤ 0 ovunque.** Il PAS perde meno per segnale (+0,21 in
media rispetto all'AGG) solo perché esegue meno. Un solo netto positivo (+0,18, p 0,42, n 407, a 2
tick −0,06). Il VR<1 di mezzogiorno del giro 1 non è incassabile nemmeno con i limiti.

### B4: rottura e ritest con limite al livello (30 test)
Massimo/minimo di ieri, della notte e della prima ora; limite al livello o a metà; N {15, 60}; uscita
60 m o 15:59; variante con stop. **30/30 non significativi**, quasi tutti negativi. Il migliore è IB,
metà, con stop: +0,34 (p 0,23, a 2 tick 0,00, d20 −1,30). La AS è la più alta di tutte (+5 … +21): il
ritest che viene eseguito è quello in cui la rottura fallisce.

### B5: terza esecuzione dichiarata, «limite poi mercato» + ibrido con target a limite (13 test)
- Placebo: «limite poi mercato» −0,79/−0,81 contro AGG −0,85: guadagno **~+0,05 per trade**. Ibrido
  (ingresso a mercato, target a limite, costo 0,50 sui target): −0,83/−0,85 contro −0,96/−0,98, cioè
  +0,13/+0,15. È un risparmio contabile reale ma piccolo, non un vantaggio statistico.
- Segnali del giro 1: sorpresa +0,28 → +0,52 (p 0,058); hivol +2,29 → +2,44 (d20 da −0,1 a +0,3);
  fade rottura notte e turnaround invariati. **Sono candidati del giro 1 già bocciati**: per il §10 non
  si ripresentano con un ritocco di esecuzione. Li riporto come informazione, non come scoperta.

### B6: fasce OCO condizionate al regime di notte previsto (16 test)
Regimi dalla regolarità confermata «range notturno → range RTH» (terzili causali). Ipotesi: nei giorni
calmi la fornitura di liquidità soffre meno. **16/16 negativi o nulli**; basso e alto regime quasi
uguali (per esempio RTH k1: −0,32 contro −0,38).

## Conteggi dal registro
- 202 test: B0 24, B1 51, B2 36, B3 32, B4 30, B5 13, B6 16.
- Netto PAS con p < 0,05: **28, tutti su segnali del giro 1** (fade rottura notte, hivol last30,
  turnaround). In nessuno il PAS supera l'AGG in modo significativo.
- Cambi di segno (AGG < 0 e PAS > 0): **3** (`B1_last30_all_offs5h_N5` +0,02, `B2_open_k3_tg1t60` +0,01,
  `B3_mid_dev60_z2_H60_off0` +0,18), p fra 0,42 e 0,46, **tutti negativi a 2 tick**. Sono rumore.

## Candidati
**Nessuno.** Un'esecuzione passiva conservativa non crea vantaggio dove non c'è. Dove un vantaggio c'è
(segnali del giro 1), il passivo lo riduce oppure lo lascia uguale, e quei segnali non sono comunque
ripresentabili. L'unico miglioramento sistematico, il «limite poi mercato» su segnali che hanno già
alfa (+0,05 … +0,25 punti), è troppo piccolo per trasformare in strategia un'idea nuova e l'ho visto
solo su idee vecchie. Mandare qualcosa aumenterebbe K per le altre famiglie senza speranza realistica.

## Scettici su noi stessi
- Barre da 1 minuto: non conosciamo la posizione in coda né l'ordine degli eventi dentro la barra. Il
  trade-through di 1 tick è la regola minima onesta. Con il touch i risultati migliorano solo di ~0,1-0,2
  e restano negativi: la conclusione non dipende dalla regola.
- Lo spread di NQ nel 2010-2018 era quasi sempre 1 tick. Il «mezzo spread guadagnato» con il limite
  non esiste davvero se si esige il trade-through, ed è esattamente quello che i placebo misurano.
- L'uscita a tempo passiva paga 1 tick come l'aggressiva. Non ho simulato uscite a tempo con limite:
  i placebo B5 mostrano che un ordine limite in un istante qualsiasi vale ~0.

## File
`common.py` (simulatore numba AGG/PAS/OCO/«limite poi mercato», beta come il controller),
`b0_placebo.py` … `b6_bands_regime.py` (ognuno registra ciò che stampa), `candidates.py` (vuoto),
`test_candidates.py` (riproduce B0 e la coincidenza AGG = giro 1 per hivol: OK).
`core.py`: nessun bug trovato.
