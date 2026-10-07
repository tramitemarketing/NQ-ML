# r7_opzioni — relazione (discovery 2010-06 → 2018-12, 2026-10-07)

**In breve.** Famiglia chiusa al Passo 0 come **«non decidibile nel discovery»**, senza eseguire i test
primari, per le regole scritte nel PREREG prima di scaricare i dati. Nessun rendimento di straddle è stato
calcolato o guardato (il codice dei test, committato in `c942f3b`, non è mai stato eseguito).

## Dati
Databento `GLBX.MDP3`, `definition` + `tbbo`, `NQ.OPT` e `QN1-5.OPT`, 2010-06-07 → 2018-12-31: 163.657
opzioni (call/put), 1.651.066 scambi con il miglior bid/ask. Costo stimato 15,22 $ (più, forse, 1,13 $ di una
richiesta in streaming interrotta: addendum 1). Hash in `data/ext_paid/opzioni/download.json`.

## Passo 0 (`s01_output.txt`)
- **Orari di scadenza (NY):** settimanali 16:00 (qualche 13:00 nei giorni corti); mensili e trimestrali
  09:30 (fixing del mattino, esclusi), 16:15, 17:00, 17:15.
- **Venerdì con scadenza:** 310 settimanali + 87 mensili nel discovery.
- **Venerdì utilizzabili** (sottostante = contratto di `NQ.v.0`, straddle ATM con bid/ask registrato fra le
  09:15 e le 09:45 su entrambe le gambe): 4, 6, 7, 5, 10, 1, 6, 18, 6 per anno dal 2010 al 2018. **53 dal 2012.**
  Prima del 2019 le opzioni su future NQ vicino all'apertura si scambiano di rado: quasi tutto il volume
  del Nasdaq-100 passava da NDX e QQQ.
- **Spread** dello straddle: mediana fra il 7 % e il 25 % del mid a seconda dell'anno.
- **Potenza** (CV di |movimento 09:45-16:00| / range previsto = 0,83, solo future):
  - MDE80 di B = **32 %** del mid, contro un effetto plausibile ≤ 5 %;
  - MDE80 della pendenza di A = **1,79**, contro un effetto plausibile ≤ 0,15 (sd di s = 0,18 su 51 venerdì).

## Esito
Tutte e tre le condizioni di chiusura del PREREG sono vere (meno di 150 giorni, entrambe le MDE80 sopra
l'effetto plausibile). Come scritto prima, **non si comprano dati dal 2019** per allungare il campione: sono
validazione e conferma.

Lettura: la domanda «la previsione di volatilità del laboratorio batte il prezzo delle opzioni?» resta
aperta, ma **non è decidibile con le opzioni su future NQ del 2010-2018**. Una risposta seria richiederebbe le
opzioni NDX/QQQ (CBOE/OPRA, altri costi e altre licenze) oppure le opzioni NQ giornaliere dal 2022, che però
cadono nei blocchi già usati: andrebbero trattate come una prova in avanti, con una nuova pre-registrazione.
Anche con un campione grande, spread del 7-25 % del mid sono un muro: il vantaggio di timing dovrebbe superarli.
