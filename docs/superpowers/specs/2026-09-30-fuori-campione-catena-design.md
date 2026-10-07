# Fuori Campione — la catena che verifica le strategie dei social (progetto, 2026-09-30)

**Stato:** progetto, niente codice della catena ancora scritto. Il primo pezzo esiste e funziona: il registro
«già provata?» (`product/registro/`, 12 test verdi). Le decisioni segnate ⚑ spettano a Giovanni (§ 9).

## 0. In una pagina

**Cosa fa.** Una strategia vista sui social entra, viene tradotta in regole e controllata nel registro. Poi
viene pre-registrata con data certa, testata sul discovery e pubblicata come verdetto: una scheda, una pagina,
un video breve. Se sopravvive, entra nella prova in avanti, cioè viene giudicata sui dati che arrivano dopo la
sua registrazione.

**Perché ora.** La catena esiste già, fatta a mano:
- il giro 5 ha preso un video YouTube e l'ha pre-registrato e testato (49 test);
- il giro 6 ha preso quattro ipotesi di un documento esterno. Pre-registrazione committata alle 14:44
  (`b487951`), Passo 0 alle 15:05, codice alle 15:15, esito alle 15:22 (`9863df8`): 13 test primari, 0 candidati.

Automatizzare vuol dire togliere le ore di Giovanni, non il metodo.

**Cosa non fa, mai.**
- Non consiglia operazioni e non esegue trade.
- Non usa validazione, conferma o cassaforte da sola.
- Non raccoglie dati contro le regole delle piattaforme.
- Non giudica persone.

**Ritmo realistico:** 2-4 verdetti nuovi a settimana. Il limite vero è l'uso di Claude Code, più il tempo di
Giovanni ai tre cancelli. Si parte però con circa 20 verdetti già pronti dal laboratorio (§ 7), cioè più di un
mese di contenuti senza un test nuovo.

## 1. Principi (ereditati dal laboratorio, non negoziabili)

1. **Pre-registrazione prima dei dati, pubblica e con data certa.** Il PREREG viene committato e pubblicato
   (pagina con hash del commit) prima di calcolare qualunque risultato.
2. **Il registro conta tutto:** segnalazioni ricevute, versioni dell'interpretazione, test, falliti compresi.
   Il numero di tentativi fa parte del verdetto.
3. **Blocchi di tempo del laboratorio** (`lab/core.py`, PROTOCOLLO § 1 e § 19). La catena usa solo il discovery
   2010-06-07 → 2018-12-31. Validazione e conferma solo tramite controller, e solo con il via di Giovanni. La
   cassaforte mai. Nota di `lab/RISULTATI.md`: la validazione è già stata usata da 20 ipotesi e la conferma da 7,
   e ogni riuso le consuma. Per questo il giudizio vero dei sopravvissuti è la prova in avanti (§ 3.7).
4. **Tre cancelli umani:** G1 (quali strategie testare questa settimana), G2 (la pre-registrazione, cioè
   l'interpretazione), G3 (la pubblicazione). Pochi minuti ciascuno.
5. **Metodi, non persone.** `docs/business/STRATEGIA_VENDITA.md` § 11-12: niente giudizi pubblici su strategie
   di terzi riconoscibili senza il loro consenso. In pratica:
   - un metodo noto (ORB, VWAP, Silver Bullet, un paper) si pubblica con il suo nome, citando le fonti;
   - un sistema legato a una persona (i suoi numeri, il suo video) si pubblica anonimo oppure con il suo
     consenso ⚑.
   A chi lo ha ideato si offre sempre la replica: se propone un'altra interpretazione, diventa una nuova
   versione, testata e contata.
6. **Regole delle piattaforme:** solo canali ufficiali, niente scraping, niente download di video altrui.
7. **Nessuna raccomandazione** (STRATEGIA § 10.1 e linee guida ESMA-CONSOB di gennaio 2026). «Questa regola non
   batte il caso» sì; «compra», «vendi», «usala sul tuo conto» mai. Il verdetto riguarda la statistica passata
   di una regola, non il futuro del prezzo.

## 2. Il flusso

```
segnalazioni ─► 1 ascolto ─► 2 smistamento ─► [G1] ─► 3 regole + PREREG ─► [G2] ─► 4 test sul discovery
                                   │                                                        │
                                   │ «già provata?» (product/registro)                      ▼
                                   └─► verdetto già esistente ──────────────► 5 scheda, pagina, video
                                                                                            │
                                                                        [G3] ─► 6 pubblicazione
                                                                                            │
                                                   7 prova in avanti (solo per chi sopravvive o si registra)
```

## 3. I pezzi

### 3.1 Ascolto (fonti)

Stato delle regole verificato il 2026-09-30. Fonti: pagine ufficiali di X, Reddit, YouTube, Instagram, Telegram
e TikTok.

| Fonte | Come | Costo | Fase |
|---|---|---|---|
| Modulo sul sito (`controprova.it/segnala`) | link, descrizione, trascrizione facoltativa | 0 | 1 |
| Bot Telegram | la gente inoltra messaggi e link al bot (Bot API) | 0 | 1 |
| X | menzioni dell'account («@… testa questa») più 3-5 ricerche salvate | 0,005 $ per post letto, niente piano gratis; 300 post al giorno ≈ 45 $ al mese, con tetto di spesa | 2 |
| YouTube | ricerca e feed RSS di una lista di canali | 0, quota standard (una ricerca costa 100 unità su 10.000 al giorno) | 2 |
| Discord | bot con comando `/controprova` nei server che lo invitano | 0 | 3 |
| Reddit | solo dopo l'approvazione esplicita (Responsible Builder Policy); uso commerciale solo con permesso scritto | — | se approvato |
| TikTok, Instagram, TradingView | solo come link dal modulo o dal bot (la Research API di TikTok è per università ed enti no profit) | 0 | 1 |

**Trascrizioni.** L'API di YouTube dà le trascrizioni solo a chi può modificare il video. Scaricare i video
altrui (yt-dlp) va contro le condizioni di YouTube. La trascrizione la incolla chi segnala, oppure Giovanni la
copia da «Mostra trascrizione».

**Cosa si salva di una segnalazione:** id, data, canale, url, handle pubblico dell'autore della strategia (se
pubblico), testo o trascrizione forniti, metriche pubbliche se l'API le dà, stato. Di chi segnala si salva solo
un identificativo anonimo: niente dati personali oltre il necessario. Tempi di conservazione da scrivere
nell'informativa ⚑.

### 3.2 Smistamento

Per ogni segnalazione, un agente:
1. **Controlla se è testabile:** strumento con dati (oggi NQ; ES e ZN costano 21 e 19 $ secondo
   `lab/RISULTATI.md`), barre da almeno 1 minuto, regole ricavabili. Molte strategie di X saranno su crypto,
   forex o azioni: finiscono in una lista «non testabile ora», contata anche quella.
2. **Controlla se è già stata provata:** `python -m product.registro.cerca "<descrizione>" --json`.
   - «Probabilmente sì» porta al verdetto esistente (link alla relazione): contenuto pronto, zero test.
   - «Forse» porta a un controllo a mano al G1.
3. **Dà una priorità:** diffusione (visualizzazioni, numero di segnalazioni indipendenti) × novità ×
   testabilità, divisa per il costo (dati da comprare?).
4. **Consegna la lista della settimana**, al massimo 5 strategie, per il G1.

### 3.3 Regole e pre-registrazione

Modello: `lab/r5_amd/PREREG.md` e `lab/r6_*/PREREG.md`. Contenuto minimo:
- fonte e citazione breve;
- la tesi in parole semplici;
- le regole in pseudocodice;
- **le scelte d'interpretazione dichiarate**, con le alternative (le strategie ICT ne hanno sempre);
- test primari (segnale nudo, poi regole complete), placebo e fill;
- criteri del PROTOCOLLO § 3 con l'emendamento 1, più le regole della pre-registrazione;
- budget dei test.

Il commit arriva prima di qualunque dato, poi si pubblica la pagina «pre-registrazione» con hash e data (G2).

### 3.4 Test

Una famiglia nuova per strategia, `lab/fc_<nome>/`, con la struttura del laboratorio:
- Passo 0, PREREG, script, `REPORT.md`;
- registro con `core.record()`;
- solo discovery.

Se nasce un candidato ci si ferma, e decide Giovanni: controller come da PROTOCOLLO, oppure direttamente la
prova in avanti.

### 3.5 Verdetto e materiali

Tre esiti. Nessuno dei tre si chiama mai «certificazione» (STRATEGIA § 12.6):

| Esito | Quando |
|---|---|
| **Non batte il caso** | fallisce i criteri del discovery |
| **Reale ma non si incassa** | regolarità confermata ma sotto i costi, come l'apertura di mezzanotte del giro 6 |
| **Sopravvive al discovery** | passa i criteri: va in prova in avanti; non è un consiglio |

Materiali generati da modelli fissi:
- **scheda:** cosa è stato testato, interpretazione, trade, netto a trade, anni positivi, confronto con il
  placebo, periodo, tentativi, link a PREREG, commit e relazione;
- **pagina** `/verdetti/<nome>`;
- **copione di un video da 45-60 secondi:** gancio, regola, cosa abbiamo fatto, risultato, lezione. Il montaggio
  usa il template Remotion con KineticCaptions, e la faccia e la voce restano di Giovanni;
- due righe per X e Telegram, più la risposta a chi ha segnalato;
- una voce nella newsletter settimanale.

### 3.6 Pubblicazione (G3), lista di controllo

- [ ] Ogni numero coincide con `REPORT.md` e con il registro.
- [ ] Nessun giudizio su persone; terzi riconoscibili anonimi o con consenso.
- [ ] Nessuna raccomandazione e nessuna previsione di direzione.
- [ ] Fonte citata e link alla pre-registrazione.
- [ ] Interesse economico dichiarato quando si parla dei prodotti Controprova.

### 3.7 Prova in avanti

- Regole congelate (hash del PREREG), fatte girare solo sui dati successivi alla data di registrazione.
- Orizzonti e soglie fissati alla registrazione: 3, 6 e 12 mesi, con gli stessi criteri del PROTOCOLLO. La
  pagina pubblica mostra l'andamento, ma il verdetto arriva solo agli orizzonti.
- Dati: barre NQ a 1 minuto scaricate dopo la chiusura. Costano una frazione della storia intera: ES a 1 minuto
  intero costa circa 21 $.
- **Blocco da sciogliere prima di partire ⚑:** in `config.yaml` la cassaforte è `vault.start: 2026-03-20` senza
  fine. I dati da ottobre ricadrebbero lì.
- Più avanti, la stessa macchina si apre a chi vende strategie (l'idea «Prova in avanti»): paga chi vende,
  consulta gratis chi compra, niente si cancella e niente si ritocca.

## 4. File

| Percorso | Cosa | Stato |
|---|---|---|
| `product/registro/` | ricerca «già provata?» su registro, verdetti e relazioni | **fatto** |
| `product/catena/fonti/` | un modulo per fonte (modulo sito, Telegram, X, YouTube) | da fare |
| `product/catena/smistamento.py` | testabilità, «già provata?», priorità, lista settimanale | da fare |
| `product/catena/prompt/` | istruzioni versionate degli agenti (smistamento, PREREG, verdetto) | da fare |
| `product/catena/modelli/` | modelli di scheda, pagina, copione, post | da fare |
| `product/catena/registro_pubblico.jsonl` | una riga per segnalazione con l'esito, senza dati personali | da fare |
| `data/catena/` (non versionata) | segnalazioni grezze | da fare |
| `lab/fc_<nome>/` | una famiglia per strategia testata | quando serve |

## 5. Costi e limiti

| Voce | Costo | Nota |
|---|---|---|
| X | ~45 $/mese a 300 post letti al giorno | tetto di spesa nella console di X |
| YouTube, Telegram, Discord, modulo | 0 | limiti di quota |
| Dati per la prova in avanti | pochi $/mese | Databento, dopo la chiusura |
| Sito statico | 0 con i piani gratuiti | |
| Claude Code | il limite vero | 2-4 verdetti nuovi a settimana |

## 6. Fasi

- **Fase 0 (fatta il 30 settembre):** registro «già provata?», 12 test.
- **Fase 1, due settimane:**
  - modulo sul sito e bot Telegram;
  - smistamento semi-automatico;
  - modello di PREREG;
  - generatore di schede e pagine;
  - pubblicazione dei ~20 verdetti del § 7, uno ogni due o tre giorni.
- **Fase 2, settimane 3-6:** menzioni di X e ricerca YouTube, copione video automatico, prova in avanti per i
  sopravvissuti.
- **Fase 3, dal terzo mese:** bot Discord, torneo pubblico «Batti il caso», prova in avanti aperta a chi vende.

**Criteri di arresto** da fissare prima di partire, come STRATEGIA § 9.3 ⚑. Per esempio: rivedere la catena
se dopo 8 settimane arrivano meno di 5 segnalazioni utili a settimana, o se la metà dei verdetti richiede più di
un'ora di lavoro di Giovanni.

## 7. Verdetti già pronti dal laboratorio

Il contenuto della prima fase: niente test nuovi, solo schede scritte dalle relazioni. I numeri si copiano
dalla relazione al momento di scrivere la scheda, e ogni scheda passa il G3.

| # | Strategia | Dove | Esito in breve |
|---|---|---|---|
| 1 | Opening Range Breakout 15 minuti | `screening_looks.md` S1 | peggio del caso in 8 geometrie su 8 |
| 2 | Rottura della prima ora | `reports/screen_roundup.md` | chiuso |
| 3 | Gap: chiusura e prosecuzione | `reports/screen_roundup.md` | tutte le varianti falliscono |
| 4 | VWAP e bande | `reports/screen_v2.md` | chiuso |
| 5 | RSI(2) su più giorni | `lab/multiday` | niente |
| 6 | Turnaround Tuesday | `lab/calendar` | bocciato in validazione |
| 7 | Fine mese, solo NQ | `lab/calendar`, `lab/r2_footprints` | ottimo 2010-18, distrutto dal 2022 |
| 8 | Rialzo prima della Fed (pre-FOMC) | `lab/calendar` | sparito dopo il 2011 |
| 9 | Numeri tondi | `lab/micro` | nessuna differenza dal placebo |
| 10 | NR7 e inside day | `lab/multiday` | nessuna direzione |
| 11 | Momentum dell'ultima mezz'ora (paper JFE) | `lab/intraday_momentum` | perde dopo i costi, variante bocciata in validazione |
| 12 | Reversal a 10 giorni | `lab/multiday` | bocciato in validazione |
| 13 | Time-series momentum | `lab/multiday` | segno opposto a 2 settimane |
| 14 | Modello AMD di un video ICT (anonimo o con consenso) | `lab/r5_amd` | −0,26 punti netti a trade, 1 anno positivo su 9 |
| 15 | ICT Silver Bullet | `lab/r6_silverbullet` | −0,96 punti netti a trade, 0 anni positivi su 9 |
| 16 | Noise Area di Zarattini (paper 2024) | `lab/r6_noise` | non batte un orario casuale |
| 17 | Le «probabilità» dei siti di statistiche NQ | `lab/r6_community` | geometria del caso; unica regolarità l'apertura di mezzanotte |
| 18 | Filtro gamma (GEX) | `lab/r6_gamma` | reale ma troppo piccolo |
| 19 | Fasi lunari | `lab/wild` | usate come regola senza senso, per misurare quanto «vince» il caso |
| 20 | La rottura delle bande di volatilità | `lab/r2_range` | +3,1 in scoperta, +12,1 in validazione, −2,6 in conferma: la storia di punta |
| 21 | 480.181 regole contro 700 mondi placebo | `lab/r2_autosearch` | miglior t reale 4,18 contro mediana dei placebo 4,01 |

## 8. Rischi

| Rischio | Come si riduce |
|---|---|
| Diffamazione, terzi riconoscibili | § 1.5: metodi e non persone, anonimato o consenso, replica |
| Scivolare nella consulenza | § 1.7 e lista del G3; nessun commento su posizioni di nessuno |
| Regole delle piattaforme | solo canali ufficiali (§ 3.1); niente scraping né download |
| Licenza dei dati Databento | si pubblicano solo statistiche derivate; va verificato che la licenza lo consenta (STRATEGIA § 10.5) ⚑ |
| Consumo di validazione e conferma | la catena non chiama il controller da sola; il giudizio vero è in avanti |
| Traduzioni sbagliate delle strategie | interpretazioni dichiarate, versioni contate, replica dell'autore |
| Limiti di Claude Code | pochi verdetti fatti bene; il backlog del § 7 copre le settimane lente |
| «L'anti-guru che vende» | prezzi e metodo pubblici; nessuna affiliazione con broker o prop (STRATEGIA § 12.5) |

## 9. Decisioni che spettano a Giovanni ⚑

1. **Cassaforte.** Chiuderla al 2026-09-30 (aggiungere `vault.end`) e usare i dati da ottobre solo per le prove in
   avanti, ognuna dalla propria data di registrazione? Senza questa decisione la § 3.7 non parte.
   **Deciso il 2026-10-07: sì** (`lab/PROTOCOLLO.md` §23, `config.yaml` `vault.end`).
2. **Terzi riconoscibili:** sempre anonimi, oppure consenso scritto caso per caso?
3. **Nome e account:** «Fuori Campione» e «Controprova» su X, Telegram e Discord (disponibilità da verificare).
4. **Budget X:** proposta 50 $ al mese con tetto.
5. **Criteri di arresto** della catena (§ 6).
6. **Licenza Databento** per la pubblicazione di statistiche derivate.

## 10. Cose da fare di persona (account, chiavi, richieste)

Da fare con i tuoi account. Le chiavi vanno in `.env`, che non si committa.

1. **Bot Telegram:** in Telegram apri @BotFather, comando `/newbot`, scegli nome e username, copia il token in
   `.env` come `TELEGRAM_BOT_TOKEN`.
2. **YouTube:** Google Cloud Console → nuovo progetto → abilita «YouTube Data API v3» → crea una chiave API →
   `.env` come `YOUTUBE_API_KEY`.
3. **X (Fase 2):** nella Developer Console di X crea un'app, compra crediti e imposta il tetto di spesa, poi
   copia il Bearer token in `.env` come `X_BEARER_TOKEN`.
4. **Reddit (facoltativo):** richiesta dalla pagina della [Responsible Builder
   Policy](https://support.reddithelp.com/hc/en-us/articles/42728983564564-Responsible-Builder-Policy). Testo da
   adattare, in inglese:

   > We are Controprova, a one-person Italian project that tests trading strategies shared online against
   > historical market data, with the rules written and published before any result is computed. We would like
   > read-only access to a small number of public posts in trading subreddits (for example r/algotrading and
   > r/FuturesTrading): posts that users explicitly point us to, or that match a few keywords, at most a few
   > hundred posts per week. We use a post only to extract the strategy rules it describes. We test them on our
   > own data and publish the result with a link back to the post. We will not store usernames beyond that link.
   > We will not train or fine-tune any AI model on Reddit data, and we will not sell, license or share Reddit
   > data or use it for advertising. The project sells statistics education and backtest audits; Reddit data
   > would not be part of anything we sell. Please tell us whether this counts as commercial use and what
   > approval it needs.

5. **Modulo sul sito:** una pagina di controprova.it con url, descrizione, trascrizione facoltativa e consenso
   all'informativa.
