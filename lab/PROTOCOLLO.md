# Laboratorio aperto — protocollo (fissato il 2026-09-23, PRIMA di qualunque test)

L'utente ha chiesto di «provare qualsiasi cosa, finché non si trova qualcosa di reale». Questo è
esattamente il disegno che produce falsi positivi garantiti: con abbastanza tentativi, qualcosa passa
sempre. Il protocollo sotto rende la ricerca libera **e** il verdetto credibile, separando dove si
esplora da dove si giudica. È scritto e committato prima che venga guardato un solo risultato.

## 1. Tre blocchi di tempo, con guardia nel codice (`lab/core.py`)

| fase | periodo | chi la usa | quante volte |
|---|---|---|---|
| discovery | 2010-06-07 → 2018-12-31 | tutti gli agenti | illimitate |
| validation | 2019-01-01 → 2023-09-30 | solo il controller, su candidati congelati | una volta per candidato |
| confirmation | 2023-10-01 → 2026-03-19 | solo il controller, sui sopravvissuti | una volta per candidato |
| cassaforte | ≥ 2026-03-20 | **nessuno** | resta all'utente |

Nota onesta: 2019-2023 è già stato usato dal progetto per lo screening di setup specifici (value
area, ORB, gap, prima/ultima ora, VWAP, overnight). Per le **idee nuove** di questo laboratorio è
comunque fuori campione; per le varianti di idee già schermate non lo è, e va dichiarato.

## 2. Discovery (agenti, famiglie di idee in parallelo)

Libertà totale sul discovery. Obblighi:
- ogni test guardato va in `lab/ledger/<famiglia>.jsonl` via `core.record()`;
- nessun dato fuori discovery (la guardia lo impedisce; è vietato aggirarla);
- ogni segnale usa solo informazione disponibile **prima** dell'ingresso (lezione del TEST B);
- per ogni candidato promosso: EV netto (costi 0,75 punti a/r), CI a blocchi per giorno, tabella
  per anno, EV senza i 20 trade migliori, controllo beta (lezione dell'overnight), specchio/placebo
  quando ha senso;
- al massimo **3 candidati per famiglia**, con specifica congelata come funzione Python.

## 3. Validazione (controller, una volta)

K = numero totale di candidati inviati da tutte le famiglie. Un candidato passa se:
1. EV netto medio > 0 con p unilaterale (bootstrap a blocchi per giorno) < 0,05 / K (Bonferroni);
2. EV netto al netto del beta (esposizione × deriva media della stessa finestra oraria) > 0;
3. EV netto > 0 in almeno 3 dei 5 anni solari 2019-2023;
4. EV netto senza i 20 trade migliori > 0.

## 4. Conferma (controller, una volta)

K2 = numero di sopravvissuti. Stessi quattro criteri su 2023-10-01 → 2026-03-19, con 0,05 / K2
e «almeno 2 anni su 3» (2023-Q4 conta con il 2024). Solo chi passa entrambe le fasi si chiama
**reale**. La cassaforte non viene aperta: se qualcosa arriva fin qui, la decisione di usarla è
dell'utente.

## 5. Binario separato: «reale ma non incassabile»

Regolarità statistiche (es. prevedibilità della volatilità, effetti lordi sotto i costi) seguono lo
stesso percorso discovery → validation → confirmation con test bilaterale sul lordo, e vengono
riportate come tali: veri fatti sul mercato, non strategie.

## 6. Cosa conta come risultato

Anche «zero sopravvissuti su N» è un risultato, e va scritto con N. Il numero totale di test
guardati (dal registro) accompagna ogni conclusione.

## 7. Emendamento 1 (2026-09-23, prima di qualunque validazione)

Il criterio 2 («EV netto meno beta > 0») chiedeva solo il segno, non la significatività. La
calibrazione con i placebo della famiglia `wild` (`lab/wild/REPORT.md`, batterie D-E) ha mostrato che
così passa tutti e quattro i criteri l'**11 %** dei placebo long che attraversano la notte (1,2 % anche con
Bonferroni), perché nel 2010-2018 il 90 % della salita di NQ è avvenuto fuori dall'RTH. Con la versione
irrobustita — p unilaterale del bootstrap su (netto − beta) < 0,05/K — passano **0 su 300**.
Nuovo criterio 2: **EV netto meno beta > 0 con p unilaterale < 0,05/K**, per tutti i candidati.
Motivazione esclusivamente dai placebo; la modifica è fatta dopo aver letto i numeri di discovery dei
candidati ma prima di qualunque dato di validazione. Il criterio 4 (senza i 20 migliori) resta invariato
anche se penalizza gli eventi rari: cambiarlo ora sarebbe motivato dai candidati, non dai placebo.

## 8. Esito della validazione e piano della conferma (2026-09-23, prima di aprire la conferma)

Validazione eseguita una volta, K = 13, soglia 0,05/13 (`lab/verdicts/validation.json`):
**0/5 candidati tradeable passano; 3/8 regolarità passano**: `vol_har_vs_mean22`,
`cross_session_onrange_rthrange`, `cross_session_rth_to_evening`. Il più vicino fra i tradeable,
`intraday_momentum_hivol_last30`, ha p 0,0051 contro 0,0038: FAIL, e resta fuori (nessun ripescaggio).

Conferma (2023-10-01 → 2026-03-19), una volta, **K2 = 4**, soglia 0,05/4 = 0,0125:
1-3. le tre regolarità sopravvissute, bilaterale sul lordo con il segno del discovery;
4. `postval_rth_to_evening_trade`: la stessa regola della regolarità 2 giudicata come **strategia**
   (quattro criteri tradeable, almeno 2 anni su 3). Registrata dopo aver visto la validazione, quindi
   solo la conferma conta. Sensibilità dichiarata ma non decisiva: costo 1,25 punti (2 tick/lato:
   la fascia 16:15-17:00 è meno liquida).

## 9. Esito della conferma — fine del giro 1 (2026-09-23)

Conferma eseguita una volta, K2 = 4, soglia 0,0125 (`lab/verdicts/confirmation.json`):
- **PASS** `vol_har_vs_mean22`: +0,175 [+0,128; +0,224] (discovery +0,182, validazione +0,214).
- **PASS** `cross_session_onrange_rthrange`: +0,164 [+0,124; +0,204] (discovery +0,147, validazione +0,121).
- FAIL `cross_session_rth_to_evening`: +2,50 punti lordi [−1,29; +5,64], p 0,15 (stesso segno, non significativo).
- FAIL `postval_rth_to_evening_trade`: +1,75 netti [−2,04; +4,89], senza i 20 migliori −2,05.

**Giro 1: 2.699 test registrati in discovery → 13 candidati → 3 in validazione → 2 confermati.**
Entrambi i confermati sono regolarità di volatilità (reali, stabili su 16 anni, non incassabili con il
solo future). Nessuna strategia direzionale sopravvive. La cassaforte resta chiusa.

## 10. Giro 2 — regole (fissate prima di lanciarlo)

Stessa struttura del giro 1: discovery libero, poi validation e confirmation una volta sola, K
contato solo sui candidati del giro 2 (il giro 1 è chiuso e riportato a parte). Gli agenti del giro 2
non ricevono i numeri di validazione/conferma del giro 1, solo il fatto che nessun tradeable è
sopravvissuto e le due regolarità confermate (che sono comunque letteratura nota). Nessun candidato
del giro 1 bocciato può essere ripresentato identico o con ritocchi di parametri.

## 11. Giro 2 — discovery chiuso, piano di validazione (prima di aprirla)

Sei famiglie (r2_range, r2_costaware, r2_execution, r2_analog, r2_autosearch, r2_footprints), circa
1.700 test registrati più 480.181 regole della ricerca automatica (con 700 ripetizioni placebo).
Tre famiglie consegnano zero candidati (esecuzione, analoghi, ricerca automatica). Candidati: **K = 5**,
soglia 0,05/5 = 0,01; tutti superano l'audit anti-look-ahead:
`r2_range_pcband_breakout` (tradeable), `r2_range_pcband_breakout_R`, `r2_costaware_mom20_restofday`,
`r2_footprints_slice_continuation`, `r2_footprints_close_clock_continuation` (regolarità, segno +).
Conferma poi sui sopravvissuti, K2 = numero di sopravvissuti. Nessuna aggiunta dopo la validazione.

## 12. Giro 2 — esito della validazione e piano della conferma (prima di aprirla)

Validazione K = 5 (`lab/verdicts/validation_giro2.json`): **PASS** `r2_range_pcband_breakout` (+12,06 netti
[+4,73; +19,38], p 0,0013, beta-corretto p 0,0018, 5/5 anni, senza i 20 migliori +0,82 — il primo candidato
tradeable del progetto a superare una validazione), **PASS** `r2_range_pcband_breakout_R`, **PASS**
`r2_footprints_slice_continuation`; FAIL `r2_costaware_mom20_restofday`, FAIL
`r2_footprints_close_clock_continuation` (p 0,0136 contro 0,01). Rilettura del codice del breakout: causale.
Stress sulla validazione (non decisivo): costo 2,0 punti + 2 tick extra sugli stop → +10,56 p 0,004.
Conferma K2 = 3, soglia 0,0167, una volta, sui tre PASS, criteri invariati.

## 13. Giro 2 — esito della conferma (2026-09-23)

Conferma K2 = 3 (`lab/verdicts/confirmation_giro2.json`): **tutti FAIL**.
`r2_range_pcband_breakout` −2,59 netti [−15,77; +12,13] (2024 +1,59; 2025 −5,98; 2026 −12,48);
`r2_range_pcband_breakout_R` +0,006 [−0,044; +0,065]; `r2_footprints_slice_continuation` +0,010
[−0,010; +0,030] (discovery +0,062 → validazione +0,024 → conferma +0,010: decade a ogni blocco).
**Giro 2: ~1.700 test + 480.181 regole automatiche → 5 candidati → 3 in validazione → 0 confermati.**

## 14. Giro 3 e chiusura (2026-09-23)

Giro 3 (`r3_adaptive`, meta-strategie adattive): 255 test, ~70.000 pipeline placebo, **0 candidati**:
nessuna persistenza mensile in quale regola funziona (rango +0,022, p 0,10 contro il nullo «segno per
giorno»). Validazione e conferma non usate. Laboratorio chiuso; sintesi in `lab/RISULTATI.md`.
La cassaforte non è stata aperta.

## 15. Giro 4 — dati esterni gratuiti (riapertura, 2026-09-23)

Su richiesta dell'utente il laboratorio si riapre con **informazione nuova**: serie giornaliere
gratuite (FRED: VXN, VIX, VIX 3 mesi, tassi, curva, dollaro; CBOE: VIX9D, VVIX, SKEW), in
`data/ext_free/`, caricate solo tramite `lab/extdata.py` con ritardi di pubblicazione conservativi
(indici CBOE: dalla sessione successiva; tassi: +2 giorni lavorativi; dollaro: +8 giorni). Le ipotesi
che usano queste serie non sono mai state testate in nessun blocco: validazione e conferma restano
fuori campione per loro. Stesse regole dei giri precedenti; K contato sul solo giro 4.
Nota di onestà: il controller conosce gli esiti dei giri 1-3 su 2019-2026 (es. il 2022 orso); gli
agenti del giro 4 ricevono solo le lezioni di discovery.

## 16. Giro 4 — discovery chiuso, piano di validazione (2026-09-24, prima di aprirla)

`r4_implied`: 295 test → 2 regolarità (`r4_implied_har_plus_vxn`, `r4_implied_on_plus_vxn`: il VXN
migliora la previsione della varianza di domani oltre HAR e oltre il range notturno); nessun tradeable
(il premio per il rischio di varianza non predice la direzione a 1-20 giorni). `r4_macro`: 83 test → 0
candidati. Validazione K = 2, soglia 0,025, bilaterale con segno +; poi conferma sui sopravvissuti.

## 17. Giro 4 — esito della validazione (2026-09-24)

K = 2 (`lab/verdicts/validation_giro4.json`): **entrambe FAIL**. `r4_implied_har_plus_vxn` +0,014
[−0,002; +0,031], p 0,09 (discovery +0,025); `r4_implied_on_plus_vxn` +0,006 [−0,007; +0,019], p 0,36.
Stesso segno, dimensione dimezzata. Conferma non usata. **Giro 4: 378 test → 2 candidati → 0.**

## 18. Giro 5 — `r5_amd`, il modello AMD/ICT di un video (2026-09-28)

Su richiesta dell'utente (trascrivere, studiare e mettere alla prova il video di Tmac «How to trade high
RR the RIGHT way»), una sola famiglia, `r5_amd`, con spec e test primario pre-registrati e committati prima
di qualunque numero (`lab/r5_amd/PREREG.md`, `ec42841`) e tre proposte dichiarate in un addendum prima di
farle girare (`5ce9764`). Esito in discovery: P0 −0,26 netti (1/9 anni), contro-trend −0,89, R lordo +0,03;
nessuna proposta supera i criteri. **49 test → 0 candidati.** Validazione e conferma non usate.

## 19. Giro 6 — quattro ipotesi esterne (pre-registrazione, 2026-09-30, PRIMA di qualunque dato)

Da dove vengono: documento dell'utente «NQ-ML — Nuove ipotesi da testare» (29 settembre 2026), con otto
ipotesi e un Blocco 0 comune. L'utente ne ha tenute quattro:
- 3, filtro gamma → `r6_gamma`
- 4, revisore delle statistiche da community → `r6_community`
- 7, Noise Area di Zarattini → `r6_noise`
- 8, ICT Silver Bullet → `r6_silverbullet`

Scartate perché già testate in questo laboratorio (rifarle sarebbe un ripescaggio):
- 1, momentum dell'ultima mezz'ora: `intraday_momentum`, 98 test, due candidati bocciati in validazione;
- 2, fine mese: `calendar`, su NQ da solo; la versione con ZN richiede dati a pagamento;
- 5, finestre notturne: `cross_session`.
Scartata per ora perché richiede dati ES a pagamento: 6, divergenza SMT.

**Adattamento dei blocchi (vincolante).** Il documento chiama «training» il periodo 2010-06 → 2023-09 e
«cassaforte» il periodo 2023-10 → 2026-03. Qui valgono i blocchi del §1:
- discovery 2010-06-07 → 2018-12-31, libero;
- validation e confirmation solo dal controller, una volta per candidato congelato;
- cassaforte (≥ 2026-03-20) all'utente.
Le «due metà» del documento diventano due metà del discovery: **2010-06-07 → 2014-12-31** e
**2015-01-01 → 2018-12-31**. Il descrittivo «2019-2023» del documento non si fa: è validation.
Conseguenza dichiarata: con 8,5 anni invece di 13,25 la potenza di discovery è più bassa di quella
calcolata nel documento.

**Blocco 0 tradotto nelle convenzioni del laboratorio:**
- Orari America/New_York con DST. Le barre Databento sono in UTC, etichettate con l'inizio del minuto.
- P_h = close della barra che inizia alle h−1 minuto. L'ingresso «al primo prezzo dopo h» è l'open della
  barra che inizia alle h.
- Solo sessioni `valid` (≥ 300 barre RTH): le mezze giornate sono escluse per costruzione.
- Prezzi `adj_*` per qualunque rendimento che attraversa la notte o più giorni. Il bps usa il prezzo grezzo.
- ATR = ATR20: media delle 20 sessioni valide precedenti del range RTH (adj_high − adj_low), nota prima
  della sessione.
- Ogni risultato in punti, bps e ATR. I test statistici primari del documento usano i bps. Il giudizio del
  controller resta sul netto in punti (§3).
- Costi 0,75 punti a/r (base) e 1,25 (stress).
- Unità statistica = giorno (bootstrap a blocchi per giorno, oppure t su P&L giornaliero). Se la posizione
  dura più di un giorno si usa HAC Newey–West a 5 lag.
- Placebo: 200 repliche salvo diversa indicazione, p = (1 + #placebo ≥ reale)/(n + 1). Fill e uscite
  identici fra reale e placebo. Gli ordini limite si considerano eseguiti solo con attraversamento di
  almeno 1 tick (lezione di `r2_execution`). Barra ambigua fra stop e target = stop.

**Passo 0 prima di tutto.** Ogni famiglia risponde prima alle domande del proprio Passo 0 (solo sul
discovery: copertura, fusi, roll, definizioni). Nessun test primario gira finché l'utente non scrive
«approvato».

**Promozione a candidato.** Una ipotesi manda un candidato in validazione solo se nel discovery passa
**sia** le regole di decisione del proprio PREREG **sia** i quattro criteri del §3 (con l'emendamento 1),
calcolati sul discovery con la soglia di Holm della famiglia. Vale per le strategie; per le regolarità
valgono il §5 e il PREREG. Massimo 3 candidati per famiglia. Audit `lab.audit_lookahead` obbligatorio
prima della validazione.

**Budget dei test primari:** gamma 3, community 6, noise 2, silverbullet 2, **totale 13**. Sensibilità,
descrittivi e controlli vanno comunque nel registro, ma non promuovono nulla. In validazione K = numero di
candidati del giro 6; poi conferma sui sopravvissuti, K2 = numero dei sopravvissuti.

**Onestà sulla cassaforte, dichiarata ora.** Per `r6_noise` e `r6_silverbullet` la cassaforte **non è
alla cieca**: repliche pubbliche coprono già il 2026. Per Zarattini c'è una replica su SPY ed ES fino a
luglio 2026, piatta dal 2025. Per il Silver Bullet c'è il repo, giugno → settembre 2026, profit factor
0,51. Nemmeno la validazione è del tutto cieca per `r6_noise`: la replica su SPY parte da luglio 2020. Per
`r6_gamma` e `r6_community` nessuna fonte che conosciamo copre i nostri blocchi con le nostre definizioni.

## 20. Giro 6 — esito del discovery (2026-09-30)

Tredici test primari eseguiti una volta, con il codice committato prima (`0d04dc0`). **Nessun candidato: la
validazione e la conferma non sono usate, la cassaforte resta chiusa.**
- `r6_gamma`: il rango del GEX passa Holm (0,025), le due metà e il placebo (0,003), ma la differenza fra
  regimi è 0,067, sotto la soglia di 0,10 → GEX chiuso come filtro. Un bug sui giorni senza GEX, trovato dopo
  il primo giro e corretto, non cambia il verdetto (vedi REPORT).
- `r6_community`: A, C, D, F spiegati dal random walk (C addirittura sotto il caso); **E reale** (ritocco
  dell'apertura delle 00:00 nelle RTH, 70,7 % contro 64,7 %, Holm 0,03), che resta descrittivo; B, il fade,
  non sfruttabile (−0,91 punti netti).
- `r6_noise`: A non significativo e sotto il placebo; B +1,73 bps netti al giorno ma negativo senza i 20
  migliori, trascinato dal 2018 e correlato 0,54 con la rottura delle bande di volatilità → chiusa.
- `r6_silverbullet`: −0,96 punti netti a trade, 0/9 anni positivi, segnale a 60 minuti sotto tutte le 200
  storie placebo → chiusa definitivamente.
**Giro 6: 26 righe di registro, 13 test primari → 0 candidati.**

## 21. Giro 7 — volatilità con ML e opzioni (pre-registrazione, 2026-10-07, PRIMA di qualunque dato)

Da dove viene: review del 2026-10-07 (potenza dei verdetti in `lab/POTENZA.md`) e richiesta dell'utente di
provare il machine learning. Il ML sulla **direzione** è già stato fatto tre volte (`nqml/`, `lab/ml`,
`lab/r3_adaptive`) e non si rifà: sarebbe un ripescaggio. Si usa dove il laboratorio ha trovato segnale vero,
la volatilità. Due famiglie:
- `r7_quantili`: distribuzione del range RTH (quantili) con calendario macro noto in anticipo e VXN;
- `r7_opzioni`: la previsione di volatilità del laboratorio contro il prezzo degli straddle NQ in scadenza.
  Dati a pagamento (Databento, opzioni GLBX), spesa autorizzata dall'utente entro il credito residuo
  (~26 $); scaricati **solo** per il discovery (fine < 2019-01-01, guardia nel codice).

Regole: §1-§6 con l'emendamento 1; convenzioni del Blocco 0 del §19. Passo 0 prima di tutto (copertura,
conteggi, nessun esito); **nessun test primario gira finché l'utente non scrive «approvato»**. Budget dei
test primari: quantili 2, opzioni 2, **totale 4** (Holm dentro la famiglia). Promozione a candidato come
nel §19. In validazione K = numero di candidati del giro 7, poi conferma sui sopravvissuti.

**Potenza dichiarata prima (lezione di `lab/POTENZA.md`).** Ogni PREREG riporta, al Passo 0 e prima dei
test, l'effetto minimo rilevabile con potenza 80 % sul discovery. Se è più grande dell'effetto plausibile
dichiarato nel PREREG, la famiglia si chiude come «non decidibile con questi dati» senza fare i test.

## 22. Giro 7 — esito (2026-10-07)

- `r7_quantili`: 2 test primari (codice `eeaaab3`, addendum 1: niente vincoli monotoni in LightGBM), **0
  candidati**. M1 lineare +1,29 % sulla pinball loss (Holm 0,026, 6/6 anni) ma sotto la soglia del 2 % e mal
  calibrato; M2 LightGBM −3,2 %. Il calendario macro porta informazione vera ma piccola (placebo p 0,010).
- `r7_opzioni`: chiusa al Passo 0 come «non decidibile nel discovery» (53 venerdì utilizzabili su 150
  richiesti; MDE80 di B 32 % del mid contro 5 %; di A 1,79 contro 0,15). Test primari mai eseguiti.
**Giro 7: 2 test primari eseguiti, 2 non eseguiti per potenza, 0 candidati.** Validazione e conferma non
usate, cassaforte chiusa.

## 23. Chiusura della cassaforte (decisione dell'utente, 2026-10-07)

La cassaforte è il periodo **2026-03-20 → 2026-09-30**. Resta chiusa: nessuno script la carica, nessun test la
guarda, e si apre soltanto con una nuova decisione dell'utente, per un candidato preciso e una volta sola.
I dati dal **2026-10-01** sono il blocco della **prova in avanti**. Regole:
- una prova in avanti parte dalla data del commit della propria pre-registrazione (regole congelate, orizzonti e
  soglie fissati prima) e usa solo dati successivi a quella data;
- ogni prova in avanti si giudica una volta per orizzonte dichiarato; i passaggi intermedi si possono mostrare
  ma non decidono nulla;
- il primo candidato naturale è il Range Atteso (coefficienti fissi): copertura delle bande e confronto con media
  a 20 giorni e ATR scalato, sugli stessi criteri del README dell'indicatore.
In codice: `lab/core.py` (`VAULT_END`, `FORWARD_START`) e `config.yaml` (`vault.end`). Nessuna fase di
`core.load` restituisce ancora dati della prova in avanti: si aggiungerà con la prima pre-registrazione.
