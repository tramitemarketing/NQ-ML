# r7_quantili — pre-registrazione (2026-10-07, PRIMA di scaricare il calendario e di guardare qualunque risultato)

Regole comuni in `lab/PROTOCOLLO.md` §21 (e §19 per le convenzioni). Solo discovery, 2010-06-07 → 2018-12-31.

## Tesi
Il laboratorio ha confermato che il **livello** della volatilità di domani è prevedibile (HAR + notte). Il
prodotto «Range Atteso» usa una media e poi quantili fissi del rapporto reale/previsto: la stessa ampiezza
di incertezza ogni giorno. Ma l'incertezza non è la stessa ogni giorno: nei giorni di FOMC, CPI e
occupazione le code sono più larghe (le sottostime peggiori dell'indicatore sono quasi tutte giorni di
notizie). Un modello che prevede direttamente i **quantili** del range, con il calendario macro (noto mesi
prima) e la volatilità implicita, dovrebbe dare bande più strette nei giorni calmi e più larghe nei giorni di
notizie, a parità di copertura. È uno strumento di rischio, non un segnale: non dice nulla sulla direzione.

## Dati
- Barre NQ 1m solo tramite `lab.core.load("discovery")`; tabella giornaliera con
  `product/indicator/features.daily_table(bars)` (stesse definizioni dell'indicatore: sessione valida = almeno
  10 barre RTH da 30 minuti; y = ln(100 · range RTH / apertura RTH); l1, m5, m22, lon note alle 09:29:59).
- **Calendario macro** (Passo 0), date 2010-2018 da fonti ufficiali, salvato in
  `data/ext_free/calendario_macro.csv` con fonte e data di download, caricato solo da `lab/extdata.py`:
  - FOMC: giorno del comunicato (federalreserve.gov, calendari storici);
  - CPI: giorno di pubblicazione (BLS);
  - occupazione (Employment Situation): giorno di pubblicazione (BLS).
  Le date sono pubblicate con mesi di anticipo: usarle il giorno stesso non è look-ahead. Non si usano
  sorprese, valori o reazioni: solo «oggi c'è il dato».
- VXN di chiusura del giorno lavorativo precedente, `extdata.known_at_open` (già nel laboratorio).

## Feature (tutte note alle 09:29:59)
l1, m5, m22, lon (come l'indicatore); ln VXN_(t−1); FOMC_t, CPI_t, NFP_t (0/1); lunedì_t (0/1).

## Modelli
Quantili q ∈ {0,05; 0,10; 0,25; 0,50; 0,75; 0,90; 0,95} di y.
- **B0 (riferimento, l'indicatore di oggi):** OLS di y su l1, m5, m22, lon; quantile q = previsione OLS +
  quantile empirico q dei residui di stima.
- **M1 (lineare):** regressione quantile (statsmodels `QuantReg`) per ogni q, su tutte le feature.
- **M2 (ML):** LightGBM con obiettivo `quantile`, uno per q, iperparametri **fissi e non ritoccati**:
  num_leaves 7, learning_rate 0,03, n_estimators 300, min_child_samples 50, subsample 0,8 (bagging_freq 1),
  colsample 1,0, vincoli monotoni crescenti su l1, m5, m22, lon, ln VXN; seme 0. Quantili riordinati
  (sort) se si incrociano.

## Walk-forward dentro il discovery
Per ogni anno Y = 2013 … 2018: stima su tutte le sessioni valide da 2010-07 a Y−1 (finestra espandente),
previsione delle sessioni valide dell'anno Y. Nessuna scelta guarda gli anni previsti.

## Metrica
Per sessione: L = media sui 7 quantili della pinball loss su y. d_M = L(B0) − L(M): positivo = M migliore.

## Test primari (Holm k = 2)
- **A**: media di d_M1 > 0;
- **B**: media di d_M2 > 0.
p unilaterale dal bootstrap a blocchi per giorno (`core.day_block_bootstrap`, una riga per sessione).

## Regole di decisione (fissate ora)
Un modello passa se valgono tutte:
1. p di Holm < 0,05;
2. d medio positivo in almeno 4 anni su 6 e in entrambe le metà (2013-2015 e 2016-2018);
3. miglioramento relativo ≥ 2 % della pinball loss media di B0 (sotto è reale ma irrilevante per il prodotto);
4. calibrazione: copertura empirica di ciascun quantile entro ±2,5 punti percentuali dal nominale
   (per esempio il quantile 0,95 deve stare sopra y fra il 92,5 % e il 97,5 % delle sessioni);
5. nei giorni con evento (FOMC, CPI o NFP) la copertura del quantile 0,95 non peggiora rispetto a B0.

Se passano entrambi, va avanti uno solo: quello con d medio più alto (deciso ora, per non usare due candidati
sulla stessa idea). Il candidato è una **regolarità** (`kind="regularity"`, segno atteso +): la `fn`
restituisce per ogni sessione d = L(B0) − L(M) con **parametri congelati** stimati una volta su tutto il
discovery (2010-07 → 2018-12), quindi gira identica su qualunque fase.

**Effetto plausibile, dichiarato ora:** 2-5 % di riduzione della pinball loss. Al Passo 0 si stima la
deviazione standard di d con una coppia di modelli che **non** è oggetto di test (B0 contro B0 con i quantili
dei residui presi su una finestra mobile di 250 sessioni invece che su tutta la stima), la si registra, e si
calcola l'MDE80 = (z di Holm + 0,84) × sd(d) / √n in percentuale della loss di B0. Se l'MDE80 supera il 5 %, la
famiglia si chiude come «non decidibile».

## Controlli e descrittivi (nel registro, non promuovono nulla)
- Placebo: date degli eventi spostate a caso dentro lo stesso mese (200 repliche): il guadagno di M1 e M2
  deve venire dal calendario vero.
- Importanza delle feature di M2 (gain), copertura per tipo di evento, d per anno.
- Larghezza media della banda 5-95 % nei giorni con e senza evento.

## Onestà dichiarata ora
- L'indicatore (B0) ha i coefficienti stimati su 2010-2023/09 e valutati sulla conferma. Qui B0 è **rifatto**
  dentro il discovery con lo stesso walk-forward: nessun parametro viene da dati successivi.
- Che i giorni di notizie siano più volatili è un fatto noto. La domanda non è se, ma se migliora una banda
  già buona di almeno il 2 %.
- Validazione e conferma sono già state usate da altre ipotesi (20 e 7). Se nasce un candidato, l'esame
  davvero vergine resta la cassaforte, che decide l'utente.

## Addendum 1 (2026-10-07, prima di qualunque esito di M1 o M2)
Il controllo meccanico del codice (forme delle previsioni, conteggi del placebo; nessuna loss calcolata) ha
mostrato che LightGBM 4.7 rifiuta i vincoli monotoni con l'obiettivo `quantile` («Cannot use
monotone_constraints in quantile objective»). M2 si esegue quindi **senza vincoli monotoni**; tutti gli altri
iperparametri, i dati, il walk-forward, i test e le regole di decisione restano identici. Nessun'altra
modifica.
