# r6_gamma — pre-registrazione (2026-09-30, PRIMA di scaricare il GEX e di guardare qualunque risultato)

Ipotesi 3 del documento dell'utente del 2026-09-29. Regole comuni in `lab/PROTOCOLLO.md` §19.

## Tesi
I dealer di opzioni coprono il delta. Con gamma lunga comprano i ribassi e vendono i rialzi, quindi
l'intraday ritorna indietro. Con gamma corta fanno il contrario, quindi l'intraday insiste. Se il GEX
pubblicato la sera prima classifica la giornata successiva, è un filtro di regime: da solo non produce
un trade.

## Dati
- **CSV SqueezeMetrics DIX/GEX**, gratuito (`https://squeezemetrics.com/monitor/static/DIX.csv`).
  Va salvato in `data/ext_free/squeezemetrics_DIX.csv`. Si annotano subito sha256 e data di download.
  Si caricano **solo** tramite `lab/extdata.py`, allineati con `known_at_open`: il valore del giorno d vale
  dalla sessione con data > d, come gli indici CBOE. Il file non si apre a mano oltre alla verifica di
  intestazione, prima e ultima data. Il loader non restituisce righe fuori dalla fase richiesta.
- Il GEX riguarda l'S&P 500, non il Nasdaq-100: è un limite dichiarato. La serie storica del fornitore
  potrebbe essere stata ricostruita a posteriori (backfill): è un limite dichiarato.
- VXN da `lab/extdata.py`, già presente.

## Passo 0 (risposte prima dei test, solo discovery)
1. Colonne, unità, prima e ultima data, sha256, data di download.
2. Verificare dalla documentazione del fornitore che il GEX della data d sia calcolato dopo la chiusura
   di d. In ogni caso lo si usa solo per d+1.
3. Quota di giorni con GEX < 0, per anno.
4. Date mancanti del VXN.
5. Autocorrelazione media dei rendimenti a 1 e a 5 minuti, per anno.

## Variabile di esito
RTH 09:30-16:00, 78 rendimenti logaritmici a 5 minuti (adj).
`VR6_t` = varianza delle somme sovrapposte di 6 rendimenti / (6 × varianza dei rendimenti a 5 minuti),
con la correzione di Lo–MacKinlay per campioni finiti. VR6 > 1 indica una giornata che insiste
(trend), VR6 < 1 una giornata che ritorna indietro.

Controlli, tutti noti prima della sessione:
- ln VXN_(t−1);
- ln RV_(t−1), cioè la media a 5 giorni della varianza realizzata a 5 minuti;
- VR6_(t−1).

## Test primari (Holm k = 3)
- **A**: `VR6_t = a + b·1[GEX_(t−1) < 0] + controlli`, OLS con Newey–West a 5 lag. H1: b > 0.
- **B**: come A, con GEX_(t−1) espresso come rango percentile sui 250 giorni precedenti.
  H1: coefficiente < 0.
- **C**: come A, con esito = autocorrelazione di primo ordine dei rendimenti a 1 minuto RTH. H1: b > 0.

**Placebo**: GEX permutato fra giorni dello stesso anno, 1.000 permutazioni; si riporta il percentile di b.
**Descrittivo**: VR6 medio per terzile di GEX × terzile di VXN; b per ciascuna metà.

## Regole di decisione (fissate ora)
Il classificatore passa se valgono tutte:
- A oppure B ha p di Holm < 0,05;
- stesso segno, con t ≥ 1, in entrambe le metà del discovery;
- placebo ≥ 95° percentile;
- differenza di VR6 fra i due regimi, al netto dei controlli, ≥ 0,10.

Se passa, il candidato è una **regolarità** (`kind="regularity"`, segno atteso +). La `fn` restituisce per
ogni sessione il contributo di Frisch–Waugh–Lovell: esito e indicatore residualizzati sui controlli,
stimati dentro la fase, e scalati in modo che la media per sessione sia uguale a b. Nessuna strategia in
questo giro: i test economici (fade con gamma positiva, momentum con gamma negativa) sarebbero ipotesi
nuove, con un PREREG proprio.

Se non passa, il GEX si chiude come filtro per NQ.

Onestà dichiarata ora:
- `r2_footprints` ha già visto un'autocorrelazione a 5 minuti più bassa nei giorni di scadenza, coerente
  con la gamma lunga;
- `r4_implied` ha già provato regimi di VXN e VIX sull'intraday.
Il GEX però è un'informazione nuova per tutti i blocchi.
