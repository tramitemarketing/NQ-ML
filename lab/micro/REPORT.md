# Famiglia `micro` — dinamica a scala di minuti (solo discovery 2010-06-07 → 2018-12-31)

**In una riga:** 457 test registrati (circa 800 letture, perché quasi ogni riga contiene sia il fade sia la
continuazione). **Nessuna strategia a scala di minuti regge in modo convincente al netto di 0,75 punti.**
Trovo una **regolarità robusta ma non incassabile**: dopo un salto «a sorpresa» di 15 minuti il prezzo
continua. C'è poi **un solo candidato tradeable, debole**: il fade della prima rottura del range notturno.
Il miglior p unilaterale netto di tutto il registro (0,0075) è quello che ci si aspetta dal caso su ~800 letture.

## Convenzioni (fissate prima di guardare, in `common.py`)
- **Unità primaria:** punti NQ **netti** per operazione da 1 contratto (lordo − 0,75), CI 95 % bootstrap a
  blocchi per giorno. **Secondaria:** la stessa media sul solo 2016-2018. Sempre riportati anche lordo,
  anni positivi su 9, media senza i 20 trade migliori (`d20`) e beta (lato × deriva media long della
  stessa finestra oraria, stesso orizzonte, su tutto il discovery).
- **Esecuzione:** il segnale è noto alla chiusura della barra 1m; si entra all'open della barra dopo, nella
  stessa sessione. L'uscita a tempo avviene al close dell'ultima barra che termina entro ingresso + H,
  e i segnali RTH non vanno mai oltre le 15:59. Target preso solo con trade-through di 1 tick. Stop al
  prezzo di stop, oppure all'open se la barra apre già oltre (più conservativo della convenzione del
  progetto). Se stop e target cadono nella stessa barra conta lo stop. Prezzi adj. Un trade alla volta
  (`nonoverlap`, causale).
- **Registro:** ogni configurazione guardata è una riga in `lab/ledger/micro.jsonl`. Le righe `evaluate_pair`
  contengono le due letture speculari (fade e continuazione) della stessa popolazione.
- Fasce: **RTH** = segnale 09:35-14:59 e uscita entro le 15:59. **ETH** = segnale 18:05-08:28 (niente
  08:30 e niente pre-apertura).

## Ipotesi provate (27 idee) ed esito

| # | Idea | Test | Esito |
|---|---|---|---|
| H1 | Movimento estremo di 1/5/15 min in multipli di σ60 (std 1m delle 60 barre precedenti), RTH/ETH, soglie 3/4/6, H 5-60 | 72 | **Il fade perde quasi ovunque, anche al lordo.** La continuazione è lorda positiva e cresce con k e con la soglia (k15 RTH z4 H60: lordo +3,0, netto +2,25 [+0,16; +4,45], ma n = 262 e d20 −1,0: sono pochi giorni di notizie). |
| H1b | Stessa cosa normalizzata sul range RTH medio a 20 giorni (ADR20), k 5-60, soglie 0,10-0,30, H 30/60/120/fine RTH | 64 | Lordo in continuazione da +0,1 a +0,5, netto negativo quasi ovunque. **L'effetto sta nella sorpresa rispetto alla volatilità locale, non nella dimensione assoluta del movimento.** |
| H16 | «Sorpresa» con σ misurata PRIMA della finestra, k 10/15/30, z 3/4/5, RTH/ETH, H 30/60 | 40 | Continuazione lorda positiva in 35 configurazioni su 36, crescente con z; netto mai significativo (miglior p 0,08). |
| H15/H18A/H19 | Binario regolarità della continuazione | 10 | **Candidato 1** (sotto). Tutta la parte RTH: +1,79 lordo [+0,91; +2,72]; ETH debole (+0,25, CI con lo zero). Beta −0,007: non spiega nulla. |
| H3 | Picchi di volume (vrel ≥ 3/5/10 rispetto alla mediana dello stesso minuto a 20 giorni): climax (barra grande) e assorbimento (barra piccola dopo un movimento), RTH/ETH, H 15-60 | 36 | Nulla: lordi entro ±0,3, netti tutti negativi, nessuna differenza fra assorbimento e climax. |
| H12 | Rapporto volume/range: barre grandi illiquide vs liquide | 12 | Nulla. |
| H4 | Numeri tondi (Osler) su prezzi GREZZI: primo tocco in sessione di multipli di 100 e 50, «reject» contro «break», con placebo su livelli spostati (+23/+61, +17/+33) | 48 | **I livelli tondi non si distinguono dai placebo** in nessuna combinazione. Il numero di eventi è basso (259 reject a 100 in RTH in 9 anni). |
| H36 | Calamita del numero tondo (verso il livello con target sul livello) | 5 | Lordo negativo, un po' peggiore sui tondi (−0,36/−0,43) che sui placebo (−0,15/−0,32): al massimo un debole effetto barriera, lontano dall'essere incassabile. |
| H5 | Massimo/minimo di ieri (PD), della notte (ON), della settimana scorsa (PW): sweep, break, rientro | 18 | PD: nulla. PW: tendenza alla prosecuzione (n piccolo, d20 negativo). ON: il fade di break e rientro è positivo a 60 m. |
| H5s/H5c/H14/H18B | Sensibilità e controlli su ON | 64 | **Candidato 2** (sotto). L'effetto vive solo nelle rotture 09:35-10:30. Dopo non c'è, e con uscite a bracket non migliora. |
| H8 | Autocorrelazione per ora del giorno (continuazione del rendimento a 15/30 m, griglia 15 m, ogni ora NY) | 44 | Lordi fra −0,5 e +0,4 punti. Unico lordo apprezzabile: **09:30-10:00, fade dei primi 15 minuti +0,33** (vicino all'ORB già chiuso). Nulla supera i costi. (Nella stampa dello script la colonna «p2» è sul netto; nel registro c'è la statistica completa.) |
| H9a | Prima barra dopo ≥ 5 minuti senza scambi (notte) | 4 | Nulla. |
| H9b | Riapertura delle 18:00 contro la chiusura delle 16:59 | 2 | Nulla (lordo +0,07/+0,17). |
| H11 | Sequenze di 5/7/9 barre nello stesso verso | 6 | Nulla (lieve continuazione lorda, sotto i costi). |
| H13 | Barre delle notizie 08:30 e 10:00, 14:00 con volume ≥ 5× | 18 | Continuazione lorda (08:30 z4: +1,0/+1,3), netto non significativo, pochi eventi. Stessa famiglia di H1. |
| H22b | 16:00-16:10 dopo la chiusura cash (utili) | 2 | Continuazione +1,7/+4,3 netto ma n = 97/23: aneddotico. |
| H16bis | Nuovo massimo/minimo di sessione dopo ≥ 60/120 minuti | 4 | Nulla. |
| H17 | Compressione del range 30 m e rottura | 4 | Nulla. |
| H25 | Stagionalità per minuto dell'ora (:00, :30, :55), regolarità lorda | 3 | Nulla (lordo entro ±0,07). |
| H32 | Intraday momentum di Gao-Han-Li-Zhou (segno ieri close → 10:00, trade 15:30-16:00). **Variante di un'idea già schermata** (ultima ora) | 1 | Lordo +0,26, netto −0,49. |
| H33 | Momentum MOC 15:50-16:00 | 1 | Lordo +0,29, netto −0,46. |
| H35 | Barre outside 1m | 2 | Nulla. |
| H39 | Esaurimento (3 barre grandi con volume decrescente) | 1 | n = 63, nulla. |

Non rifatti perché già chiusi dal progetto: fade della value area, ORB, gap, VWAP.

## Lezioni trasversali
1. **A scala di minuti il fade dei movimenti estremi perde anche al lordo:** sulla scala di un'ora conta
   la continuazione, non il rimbalzo. È coerente con un VR < 1 medio (TEST A del progetto) solo perché
   quel ritorno medio vive nei movimenti ordinari. Sui salti a sorpresa succede l'opposto.
2. **I costi decidono tutto.** Nel 2016-2018 una barra 1m RTH si muove in media ~1-2,6 punti. Quasi
   ogni effetto lordo trovato (0,1-0,5 punti) è 2-7 volte più piccolo di 0,75. Gli unici lordi
   sopra 1 punto sono condizionati a eventi rari (salti a sorpresa, notizie) con code grasse: la media
   senza i 20 migliori (`d20`) diventa negativa, cioè il criterio 4 del protocollo li boccerebbe.
3. **I livelli «famosi» non sono tutti uguali:** la prima rottura del massimo o del minimo notturno
   tende a rientrare, quella del massimo o minimo di ieri e della settimana scorsa tende a proseguire.
   Si può raccontare (liquidità sottile di notte), ma è anche esattamente il tipo di storia che si
   costruisce dopo.

## Candidati congelati (`candidates.py`, test in `test_candidates.py`)

### 1. `micro_surprise_continuation`: regolarità (binario «reale ma non incassabile»)
Regola: in RTH, per ogni barra 1m con minuto NY fra 09:45 e 14:59 in cui
|close − close di 15 min prima| ≥ 3 · σ60 · √15, si misura il rendimento nel verso del movimento
dall'open della barra successiva a 30 minuti dopo. La popolazione comprende tutte le barre di segnale
(righe sovrapposte; il bootstrap per giorno ne tiene conto). La definizione è stata scritta prima di
misurarla (H19). La scelta «tutte le barre» è stata fissata dopo aver visto la versione senza
sovrapposizione, ma prima di vedere questa: i due numeri sono equivalenti, quindi lo dichiaro e basta.

| discovery | n | lordo medio | CI 95 % | p bilaterale | anni > 0 | d20 lordo | quota long |
|---|---|---|---|---|---|---|---|
| tutte le barre (congelato) | 3.347 (879 giorni) | **+1,49** | [+0,48; +2,59] | 0,005 | 7/9 | +1,08 | 38 % |
| senza sovrapposizione | 1.063 | +1,02 | [+0,32; +1,72] | 0,004 | 8/9 | +0,28 | — |

Il netto senza sovrapposizione è +0,27 [−0,43; +0,96]: **non incassabile.** Beta ≈ 0 (i segnali sono
più short che long su un mercato che sale, quindi il beta lavora contro). Meccanismo proposto: arrivo di
informazione con sotto-reazione. Il punto di forza è la coerenza sulla griglia (H1, H1b, H16, H13: la
continuazione lorda è positiva quasi ovunque e cresce con la soglia), non il singolo p. Punto debole:
2010-2011 ≈ 0 e il p del discovery (0,005) è appena sufficiente per una correzione di Bonferroni con K
piccolo.

### 2. `micro_overnight_break_fade`: tradeable, **DEBOLE**
Regola: fra le 09:35 e le 11:59 si prende il primo attraversamento nella sessione del massimo (minimo)
della notte 18:00-09:29, con la barra che chiude oltre il livello di almeno 1 tick e il close
precedente dentro il range. Si va short (long) all'open della barra dopo e si esce a tempo dopo 120
minuti; nessuno stop, un trade alla volta.

| discovery | n | netto medio | CI 95 % | p unilaterale | anni > 0 | 2016-18 | d20 | beta |
|---|---|---|---|---|---|---|---|---|
| | 959 | **+1,23** | [−0,13; +2,64] | 0,043 | 6/9 | +2,62 (p 0,06) | **−0,29** | +0,009 |

Per anno (netto): 2010 +2,71 · 2011 −0,01 · 2012 −0,09 · 2013 −1,35 · 2014 +1,32 · 2015 +1,06 ·
2016 +0,53 · 2017 +2,85 · 2018 +4,14.
A favore:
- lo specchio (continuazione) perde −2,7;
- il controllo «fade del movimento dall'apertura a orari fissi» (H5c) perde da −0,3 a −0,9 lordo, quindi
  il livello aggiunge qualcosa rispetto al generico ritorno del primo movimento;
- la sensibilità all'orizzonte è ordinata: lordo +1,0 / +1,05 / +1,6 / +2,0 a 30 / 60 / 90 / 120 minuti.

Contro:
- **d20 negativo**: il criterio 4 del protocollo probabilmente cade;
- il CI del discovery contiene lo zero;
- dopo le 10:30 l'effetto sparisce;
- sui livelli di ieri e della settimana la stessa regola va nel verso opposto;
- con 457 test un p di 0,04 non significa nulla da solo.

L'idea è inoltre **vicina a idee già chiuse** (gap, ORB, value area: tutte dinamiche dell'apertura) e
per questo il 2019-2023 non è completamente vergine per lei. Lo mando avanti solo perché è l'unica
regola tradeable con un controllo che la separa dal banale. **La mia attesa è che non passi la validazione.**

Il terzo posto resta vuoto di proposito: nient'altro giustifica il costo in K che imporrebbe alle altre famiglie.

## Scartati da segnalare (possibili trappole se qualcuno li ripesca)
- **ON rottura, terzile del range notturno piccolo:** netto +2,63 [+0,65; +4,65], p 0,0075, 8/9 anni. È una
  divisione **post hoc** in 3 e il test migliore su ~800 letture: non promosso.
- **Continuazione dopo salti enormi (z ≥ 4-6) e dopo notizie delle 08:30, 14:00 e 16:00:** netti anche
  di +2/+4 punti, ma su 20-270 eventi e con d20 negativo. È una lotteria sui giorni di notizie.
- **Numeri tondi:** nessuna differenza rispetto ai placebo, in nessuna forma (barriera, rottura, calamita).

## Note tecniche
- `core.py`: nessun bug trovato. Le mezze giornate (per esempio il 24/12) hanno `valid = False` ma le
  barre ci sono: i miei segnali non filtrano su `valid`, e i candidati le includono. Per le fn va bene
  perché usano solo le barre.
- File: `common.py` (dati, simulatore numba, valutazione), `h01…h19_*.py` (uno script per lotto di
  ipotesi, ciascuno registra ciò che stampa), `candidates.py`, `test_candidates.py`
  (`python -m lab.micro.test_candidates` riproduce n e medie dichiarati).
