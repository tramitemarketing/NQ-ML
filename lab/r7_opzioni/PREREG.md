# r7_opzioni — pre-registrazione (2026-10-07, PRIMA di scaricare le opzioni e di guardare qualunque risultato)

Regole comuni in `lab/PROTOCOLLO.md` §21 (e §19 per le convenzioni). Solo discovery, 2010-06-07 → 2018-12-31.

## Tesi
La volatilità RTH di oggi è prevedibile (HAR + notte, confermata su tre blocchi). Il future non la incassa:
dice quanto si muove il prezzo, non dove. Le opzioni sì: uno straddle at-the-money comprato la mattina della
scadenza guadagna se il movimento fino alla scadenza supera il prezzo pagato. Se il mercato delle opzioni non
incorpora del tutto l'informazione della previsione, il rapporto previsione/prezzo dello straddle ordina il
rendimento dello straddle. Altrimenti il prezzo sa già tutto, ed è la risposta più probabile.

## Dati (a pagamento, spesa autorizzata dall'utente entro ~26 $)
Databento `GLBX.MDP3`, simbologia `parent`:
- `NQ.OPT` (mensili e trimestrali) e `QN1.OPT` … `QN5.OPT` (settimanali del venerdì);
- schema `definition` (strike, scadenza, sottostante) e `tbbo` (ogni scambio con il miglior bid/ask del
  momento);
- intervallo **2010-06-07 → 2018-12-31**, con un `assert` nel codice di download sulla fine < 2019-01-01.
  Stima del costo (2026-10-07, `metadata.get_cost`): circa 15 $. Si stampa il costo esatto prima di comprare.
- File in `data/ext_paid/opzioni/` (non versionati), sha256 annotati al Passo 0.
- Barre NQ 1m solo da `lab.core.load("discovery")`.

## Il trade (definizione, fissata ora)
- **Giorni:** venerdì con un'opzione NQ (settimanale o mensile) che scade quel giorno al fixing pomeridiano.
- **t0 = 09:45 NY.** Sottostante = il future indicato nella definizione dell'opzione; prezzo F0 = close della
  barra 1m delle 09:44 di quel contratto (se il contratto non è quello di `NQ.v.0` quel giorno, il giorno si
  esclude).
- **Strike** K = lo strike quotato più vicino a F0 (in caso di pari, il più basso).
- **Prezzo dello straddle:** per call e put con strike K, l'ultimo bid/ask registrato nel `tbbo` fra le 09:15 e
  le 09:45. Se manca o è più vecchio di 30 minuti per una delle due gambe, il giorno si esclude. Mid = media
  di bid e ask, sommata sulle due gambe.
- **Esito a scadenza:** payoff = |F_T − K|, con F_T = close della barra 1m che termina all'orario di scadenza
  della definizione (verificato al Passo 0).
- **Costi:** si compra all'ask e si vende al bid (spread pieno), più 1,25 $ per lato per opzione (2,50 $ a/r
  per gamba, 5 $ per straddle = 0,25 punti); unità: punti NQ (20 $ a punto).

## Previsione (solo passato)
Movimento atteso fino alla scadenza: E|F_T − F0| = c · range RTH previsto. Range previsto = log-HAR + notte
dell'indicatore (stessa forma, `product/indicator/features.daily_table`), ma con coefficienti e c **ristimati
ogni anno sul solo passato del discovery** (finestra espandente dal 2010-07; c = rapporto medio fra
|F_16:00 − F_09:45| e range previsto sui venerdì di stima). I coefficienti pubblicati dell'indicatore NON si
usano: sono stimati anche su dati successivi. Primo anno previsto: 2012.

Segnale s = ln(E|F_T − F0| / mid dello straddle).

## Test primari (Holm k = 2)
- **A (regolarità, lordo a mid):** rendimento r = (|F_T − K| − mid) / mid. OLS di r su s, una riga per
  giorno, errori HAC (Newey-West, 4 lag). H1: pendenza > 0.
- **B (tradeable, netto):** s̃ = s − mediana di s sui 52 venerdì precedenti (solo passato). Se s̃ > 0 si
  compra lo straddle all'ask, altrimenti lo si vende al bid; P&L netto in punti con i costi sopra.
  Criteri §3 con l'emendamento 1. Il **beta** qui è il premio per il rischio di volatilità: si confronta con
  «vendere sempre lo straddle» negli stessi giorni (stessi costi). Il criterio beta diventa: P&L di B meno
  P&L di «vendi sempre» > 0 con la stessa soglia.

## Regole di decisione (fissate ora)
- A passa se: p di Holm < 0,05; stesso segno con t ≥ 1 in entrambe le metà (2012-2015, 2016-2018);
  placebo (s permutato fra i venerdì dello stesso anno, 1.000 repliche) ≥ 95° percentile.
- B passa se: i quattro criteri del §3 (soglia di Holm), il criterio beta adattato sopra, positivo in almeno
  4 anni su 7, positivo senza i 20 trade migliori.
- Se passa solo A: «reale ma non si incassa» (§5), descrittivo.
- Candidati: al massimo uno per tipo (A regolarità, B tradeable).

## Passo 0 (solo conteggi, nessun esito)
1. Costo esatto, sha256, date coperte.
2. Orario di scadenza delle settimanali e delle mensili nelle definizioni; sottostante delle settimanali.
3. Per anno: venerdì con scadenza, venerdì con straddle ATM quotato (regola sopra), spread medio dello
   straddle in % del mid, anzianità mediana della quotazione.
4. **Potenza:** con n giorni utilizzabili e la deviazione standard del rapporto |F_T − F0| / range previsto
   (solo future, già visto nel laboratorio), MDE80 della pendenza di A e del P&L di B.
   **Effetto plausibile dichiarato ora:** pendenza ≤ 0,15; vantaggio di timing ≤ 5 % del mid dello straddle.
   Se l'MDE80 supera questi valori, o se i giorni utilizzabili sono meno di 150, la famiglia si chiude come
   «non decidibile nel discovery» senza fare i test. Non si comprano dati dal 2019 per allungare il campione:
   sono validazione e conferma.

## Onestà dichiarata ora
- Vendere volatilità rende in media (premio per il rischio) e perde molto nelle code: per questo il beta di B
  è «vendere sempre», non zero.
- Le opzioni su future NQ prima del 2019 sono poco liquide: è probabile che il Passo 0 chiuda la famiglia.
- Lo spread pieno è prudente; il fixing di scadenza approssimato con la barra 1m è un'approssimazione
  dichiarata.
- Il giro 4 ha già visto che il premio per il rischio di varianza (VXN) non predice la direzione di NQ: qui la
  domanda è diversa (il rendimento dello straddle, non la direzione).

## Addendum 1 (2026-10-07, prima del Passo 0 e di qualunque esito)
Dettagli di implementazione fissati scrivendo il codice (`common.py`, `s02_primari.py`), nessun dato guardato:
1. Se nello stesso venerdì scadono più serie, si usa quella con la prima scadenza **dopo le 09:45**: le
   scadenze del mattino (fixing di apertura delle trimestrali) sono già scadute a t0 e si escludono.
2. In B la mediana di s usa i 52 venerdì utilizzabili precedenti, con un minimo di 10: nel 2012 la
   finestra si riempie; i primi venerdì senza 10 precedenti non entrano in B.
3. Download: i file delle settimanali si chiedono con l'API batch di Databento (lo streaming era lentissimo);
   la richiesta in streaming interrotta di `QN1.OPT definition` potrebbe essere stata addebitata (+1,13 $).
4. Il Passo 0 usa la stessa costruzione dei giorni dei test (`common.build_days`) e non stampa esiti.
