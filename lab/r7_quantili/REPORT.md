# r7_quantili — relazione (discovery 2010-06 → 2018-12, 2026-10-07)

**In breve.** Due test primari (Holm k = 2), eseguiti una volta con il codice committato prima (`eeaaab3`).
**Nessun candidato.** Il modello lineare con calendario macro e VXN batte la banda di oggi dell'indicatore in
modo statisticamente solido, ma di poco (1,3 %, soglia 2 %) e con code peggio calibrate. Il modello di
machine learning (LightGBM) è **peggiore** della banda di oggi del 3,2 %.

## Che cosa si è misurato
Walk-forward 2013-2018 (1.478 sessioni), finestra espandente dal 2010-07. Per ogni sessione la pinball loss
media sui quantili 5-95 % del log del range RTH; d = loss(B0) − loss(modello), positivo = modello migliore.
B0 è la banda dell'indicatore «Range Atteso» rifatta dentro il discovery (OLS log-HAR + notte, più i quantili
empirici dei residui). Dettagli e regole in `PREREG.md` (con l'addendum 1: LightGBM non accetta vincoli
monotoni con l'obiettivo quantile, tolti prima di qualunque esito).

## Risultati

| | d medio [CI 95 %] | relativo | p (Holm) | anni + | metà | calibrazione | q95 nei giorni di evento | verdetto |
|---|---|---|---|---|---|---|---|---|
| **M1** QuantReg lineare | +0,00118 [+0,00014; +0,00222] | **+1,29 %** | 0,026 | 6/6 | +/+ | no (q90 a 87,4 %) | 91,1 % contro 91,7 % | **FAIL** (c3, c4, c5) |
| **M2** LightGBM quantile | −0,00291 [−0,00436; −0,00147] | **−3,20 %** | 0,9999 | 1/6 | −/− | no (q05 a 9,1 %) | 90,0 % contro 91,7 % | **FAIL** |

Controlli (non promuovono nulla):
- **Placebo del calendario** (eventi spostati a caso nello stesso mese, 200 repliche): M1 reale +0,00118
  contro mediana +0,00085, p 0,010. Il calendario porta informazione vera, ma è circa un quarto del
  guadagno di M1; il resto viene da VXN e dalla forma lineare. M2: p 0,64, nessuna.
- **Copertura del quantile 95 %** per tipo di evento: FOMC 91,7 % con M1 contro 85,4 % con B0 (48
  giorni); CPI 94,3 % contro 97,1 %; occupazione 88,4 % contro 91,3 %. Il FOMC è l'unico evento in cui il
  calendario allarga la banda dove serve.
- **Importanza (gain) in M2, quantile 95 %**: l1, m5, ln VXN e notte fanno il 96 %; FOMC, CPI e NFP
  insieme l'1,4 %.

## Lettura
- **Il machine learning qui fa peggio di una regressione.** Con 600-1.500 sessioni di stima e un segnale
  quasi lineare (la volatilità è persistente), gli alberi aggiungono varianza, non informazione. È lo stesso
  esito di `lab/ml` sulla direzione, ora anche sulla volatilità.
- **Il calendario macro è reale ma piccolo** per il range dell'intera sessione RTH: CPI e occupazione escono
  alle 08:30, prima dell'apertura, quindi il loro effetto è già quasi tutto nel range notturno (`lon`), che
  l'indicatore usa già. Il FOMC (14:00, dentro l'RTH) è l'unico evento che il modello non vede altrimenti.
- **Descrittivo utile per il prodotto, senza nuovi test:** anche B0 nel walk-forward del discovery copre il
  quantile 95 % nel 92,9 % delle sessioni e nei giorni di FOMC solo nell'85,4 %. Nei giorni di FOMC la
  banda esterna va letta come un minimo, come già dice il README dell'indicatore.

## Esito
`r7_quantili` chiusa: nessun candidato, validazione e conferma non usate, cassaforte chiusa. Il Range Atteso
resta com'è. Registro: `lab/ledger/r7_quantili.jsonl` (Passo 0, 2 primari, 2 placebo, 1 descrittivo).
