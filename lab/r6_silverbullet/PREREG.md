# r6_silverbullet — pre-registrazione (2026-09-30, PRIMA di guardare qualunque risultato)

Ipotesi 8 del documento dell'utente del 2026-09-29: ICT Silver Bullet, nella specifica meccanica del repo
pubblico `cjosh4toyotas-stack/silver-bullet-backtest` (`update.py`, `RULES_VERSION = "1.1 (2026-08-18)"`,
letto il 2026-09-30). Regole comuni in `lab/PROTOCOLLO.md` §19.

## Cosa si sa già
Il repo riporta 27 trade fra luglio e settembre 2026, 25,9 % vincenti, profit factor 0,51: troppo pochi
per concludere qualcosa. Il repo copre giugno-settembre 2026, cioè dentro la **nostra cassaforte**, che
quindi per questa ipotesi non è alla cieca. Validazione e conferma restano cieche. Non c'è un meccanismo
accademico. Il test serve a chiudere la leggenda con regole congelate.

## Specifica del repo (dal codice, riportata fedelmente)
- Barre a **5 minuti** in ora di New York, costruite dal nostro 1 minuto e allineate a :00/:05, prezzi adj.
- Finestre: 03:00-04:00, 10:00-11:00, 14:00-15:00 ET. La scansione dello sweep parte 30 minuti prima
  dell'apertura della finestra. Serve che la finestra abbia almeno 4 barre.
- **Sweep**: la prima barra i della scansione con `low < min(low delle 24 barre precedenti)` e
  `close > quel minimo` è rialzista, con estremo = low. Speculare per il ribasso, con
  `high > max(24 precedenti)` e `close <` quel massimo. Si controlla prima il lato rialzista, come nel
  codice.
- **FVG**: la prima terna (c1, c2, c3), con c3 da max(i+1, prima barra della finestra) fino alla fine della
  finestra.
  - Rialzista: `c3.low − c1.high ≥ gap_min` e c2 chiude sopra la sua apertura.
  - Ribassista: `c1.low − c3.high ≥ gap_min` e c2 chiude sotto la sua apertura.
- **Ingresso**: limite al bordo vicino del gap, cioè c3.low per il rialzista e c3.high per il ribassista.
  Deve essere eseguito prima della chiusura della finestra.
- **Stop**: 1 tick oltre l'estremo dello sweep. Il trade si salta se lo stop sta dalla parte sbagliata
  rispetto all'ingresso o se il rischio supera il tetto.
- **Uscita**: target 2R; uscita a tempo dopo 24 barre da 5 minuti (2 ore) al close; stop e target nella
  stessa barra = stop; un trade per finestra.

## Deviazioni dal repo (fissate ora, come nel documento)
- Soglie scalate col prezzo:
  - gap_min = max(1 tick, 0,5·P/P_ref), arrotondato al tick superiore;
  - tetto del rischio = 60·P/P_ref punti;
  - P = prezzo all'inizio della finestra; **P_ref = 30.400**, preso da una fonte del 29-09-2026 e mai
    calcolato dai nostri dati.
  - Le soglie originali (0,5 e 60 punti) sono solo una sensibilità.
- Fill a limite solo con attraversamento di almeno 1 tick, verificato sulle barre a **1 minuto**; il repo
  accetta il semplice tocco. Le ambiguità fra stop e target si risolvono a 1 minuto; se lo stesso minuto
  tocca entrambi è una perdita. Le stesse regole valgono nel placebo; i casi vanno contati.
- Costi 0,75 e 1,25 punti a/r, invece dei 10 $ del repo.

## Passo 0 (risposte prima dei test, solo discovery)
1. Copertura Globex 02:30-04:00 ET per anno. Se manca, si tengono solo le finestre delle 10 e delle 14.
2. Numero di setup per anno e per finestra, e casi di trade saltati per il tetto del rischio o per lo stop
   dalla parte sbagliata. Solo conteggi, nessun risultato di trade.
3. Differenze fra questa sintesi e il codice del repo: se ne emergono altre, si dichiarano prima dei test.

## Test primari (Holm k = 2)
- **A — segnale nudo**: dall'istante del fill, rendimento nel verso del bias a 15, 30, 60 e 120 minuti,
  senza barriere, in punti, bps e R. Primario: **60 minuti**, in bps.
- **B — geometria del repo**: stop, target 2R e uscita a 2 ore come sopra; netto a 0,75 e a 1,25.
  Percentuale di vincite contro il pareggio (1 + c/R)/3.
- Sensibilità, non decisive: soglie originali 0,5/60; le tre finestre separate; fill al tocco come nel repo.

**Placebo**: istante τ casuale nella stessa finestra. Short se il prezzo sta nella metà alta del range delle
2 ore precedenti, long altrimenti. R estratto dagli R reali dello stesso anno. Stesse uscite.

## Regole di decisione (fissate ora)
GO solo se valgono tutte:
- A ha p di Holm < 0,05;
- t ≥ 1 in entrambe le metà;
- placebo ≥ 95° percentile;
- B netto a 1,25 > 0 in entrambe le metà, con percentuale di vincite sopra il pareggio;
- criteri del §19.
Con GO, B diventa candidato `tradeable`. Altrimenti la famiglia si chiude per sempre, senza varianti di
parametri.
