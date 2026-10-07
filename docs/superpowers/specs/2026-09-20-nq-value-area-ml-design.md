# NQ-ML — Modello di meta-labeling per il setup "failed auction sulla value area" su Nasdaq (NQ)

**Data:** 2026-09-20
**Stato:** approvata il 2026-09-20; M0 e M1a chiuse il 2026-09-21 (M1a: modello = prior geometrico); §12-bis pre-registra la 1b-S (order flow su giorni campionati, zero spesa oltre i crediti)
**Scopo:** tradare la strategia dal vivo (non un progetto da portfolio). Questo documento copre il **sotto-progetto 1: ricerca, modello, backtest**. Il sotto-progetto 2 (segnale live) avrà una spec propria.

---

## 1. Obiettivo

Costruire e validare in modo onesto un modello ML che, dato un candidato generato da una strategia discrezionale su volume profile e order flow, stimi la probabilità che il trade raggiunga il target prima dello stop, e decida se prenderlo in base al valore atteso. Solo Nasdaq (future NQ, CME).

La strategia, come descritta dall'utente:

1. Volume profile della sessione → VAH / VAL / POC (value area = 70% del volume).
2. Il prezzo rompe la value area (sotto la VAL per il caso long).
3. Durante l'escursione le barre di volume calano → nessuno sta vendendo davvero.
4. Arrivano i buyer: absorption visibile nell'order flow (ordini grossi, seller assorbiti).
5. Il prezzo richiude dentro la VA con volume in crescita → LONG.
6. Stop sotto il low dell'escursione, target VAH.

I punti 1, 2, 5, 6 sono regole deterministiche e vivono nel **detector**. I punti 3 e 4 sono il giudizio discrezionale e vivono nelle **feature** che il modello valuta. Il modello non "impara la strategia": classifica i candidati che il detector trova (**meta-labeling**).

## 2. Decisioni prese

| # | Decisione | Scelta | Chi |
|---|---|---|---|
| D1 | Dati | Future NQ via Databento (`GLBX.MDP3`) | utente |
| D2 | Scopo | Tradarla davvero → backtest conservativo, live in un sotto-progetto separato | utente |
| D3 | Value area di riferimento | **Entrambe**: overnight (ON, statica dalle 9:30) e sessione corrente in sviluppo (DEV, ricalcolata ogni 5m); il modello riceve entrambe come feature separate e impara quando pesarle | utente |
| D4 | Timeframe | Conferma (rottura/rientro) su barre **5m**; feature su barre **1m** e trade tick dentro la finestra | utente |
| D5 | Direzione | **Simmetrica** long/short, feature normalizzate per direzione, un solo modello, nessuna feature `side` esplicita | utente |
| D6 | Storia | Barre 1m: **10 anni** (2016-09-20 → 2026-09-19). Tick nelle finestre di escursione: **5 anni** (2021-09-20 →), estendibili a 10 se Milestone 0 conta pochi eventi | utente + misure |
| D7 | Approccio ML | **A** = meta-labeling con LightGBM; **C** = regole a soglia solo come baseline. **C non pre-filtra mai A**: il detector è strutturale e permissivo, A vede tutti i candidati | utente |
| D8 | Modello | LightGBM binario, vincoli monotoni sulle feature di tesi, calibrazione isotonica, decisione via valore atteso | utente |
| D9 | Validazione | Walk-forward a finestra espandente, embargo 1 giorno, split per data; verdetto sull'OOS aggregato con CI block-bootstrap | utente |
| D10 | Regola dei tre sguardi + cassaforte | Contatore degli sguardi all'OOS; dopo 3, si continua solo con ipotesi pre-registrata; ultimi 6 mesi in cassaforte, aperti una sola volta | utente ("non uccidiamolo se non passa subito") |
| D11 | Repo | Repo git proprio dentro `NQ-ML/` (come GCOS-APP e INTEGRA), non nel repo di root | Claude (routine) |

## 3. Dati

### 3.1 Fonte e costi misurati (2026-09-20, via `metadata.get_cost`)

Dataset `GLBX.MDP3`, simbolo continuo **`NQ.v.0`** (front month per volume; nella misura di costo è stato usato `NQ.c.0`, stessa dimensione).

| Schema | Periodo | Dimensione | Costo |
|---|---|---|---|
| `ohlcv-1m` | 10 anni | 194 MB | **$12.67** |
| `ohlcv-1m` | 5 anni | 98 MB | $6.41 |
| `trades` | 1 giorno normale (2026-08-12) | 13.9 MB, 288.754 record | $0.36 (RTH $0.27, overnight $0.08) |
| `trades` | 1 mese | 0.36 GB | $9.42 |
| `trades` | 3 anni completi | 13.2 GB | $345.38 (fuori budget) |
| `trades` | finestra 2h RTH | ~1 MB | ~$0.02 |

Crediti gratuiti alla registrazione: **$125** (scadono dopo 6 mesi; verificato su databento.com/pricing). Chiave API già in `NQ-ML/.env` (`DATABENTO_API_KEY`), gitignored e verificata funzionante.

Budget fase 1, **aggiornato dopo Milestone 0 (2026-09-20, misure)**: barre 1m 10 anni spese **$12.81** (dai crediti; restano ~$112). Tick nelle finestre: Databento fattura a blocchi (5 e 10 minuti costano uguale, 0.531 MB), quindi una finestra media costa ~$0.03 e la STIMA originale ($50–80) era sbagliata. Misurato con `get_cost` su campioni di 40 finestre (seed 0):

| Opzione | Cosa | Costo |
|---|---|---|
| A | tick nelle finestre **unite per giorno** (5.140 finestre invece di 9.073 grezze) | STIMA **$230** (±$50 di rumore di campionamento) |
| B | trade RTH interi, 5 anni (1.245 giorni × $0.27) | STIMA **$336**: label e profili tick-accurate, nessun riacquisto futuro |
| C | nessun tick: solo feature da barre 1m | **$0** |

**Decisione dell'utente (2026-09-21): sequenza C → A/B.** Milestone 1a costruisce tutta l'infrastruttura senza order flow (benchmark "contesto + geometria + volume"); Milestone 1b compra i tick (A o B, scelta rimandata ai numeri della 1a) e aggiunge le feature di delta/absorption. Il confronto 1b vs 1a misura esattamente quanto vale l'order flow. L'order flow resta l'obiettivo centrale, non una rinuncia. Ogni acquisto passa da `get_cost` + conferma esplicita.

Il **Budget** dell'account nel portale Databento limita gli acquisti indipendentemente dai crediti residui (era a $20; alzato a $100 il 2026-09-21 dopo un 402 osservato durante la Milestone 1b-S).

### 3.2 Cosa serve a cosa

- **Barre 1m** (tutte le ore): detector, barre 5m (resample), profili ON e DEV, label, feature di volume e volatilità. I profili da barre 1m (volume della barra distribuito uniformemente sul suo range in tick da 0.25) replicano ciò che fa TradingView con i dati intrabar: i livelli del backtest sono gli stessi che l'utente vede sul grafico.
- **Trade tick** solo nelle **finestre di escursione** (dall'open della barra 5m di rottura alla chiusura della barra 5m di rientro): unica fonte del lato aggressore (`side` = A/B/N), quindi di delta e absorption. Le barre 1m di Databento non hanno lo split buy/sell.
- Riserva dichiarata, non attivata: trade completi dell'ultimo anno ($115.30 misurati) per label e profili tick-accurate, oppure NinjaTrader (un utente Reddit riporta ~2.5 anni di tick gratis con account simulato: **da verificare** quando servirà).

### 3.3 Storage e regole

- Parquet: barre 1m partizionate **per mese** (`data/raw/ohlcv_1m/YYYY-MM.parquet`, 121 file), tick **per evento** (`data/raw/trades_windows/<event_id>.parquet`).
- Ogni script è idempotente: se il Parquet esiste, la chiamata API non si ripete.
- Timestamp **UTC su disco**; conversione a `America/New_York` solo nel calcolo delle sessioni (DST cambia l'open RTH in UTC: 13:30 in estate, 14:30 in inverno).
- Sessioni: RTH 09:30–16:00 ET; ON 18:00 ET (giorno prima) → 09:30 ET; manutenzione Globex 17:00–18:00 esclusa.
- Roll: `NQ.v.0` non è back-adjusted; sui giorni di roll il profilo ON è quello del contratto front all'apertura RTH; flag `roll_day` tra le feature esplorative. Tutte le feature sono relative (tick / larghezza VA / ATR), quindi il gap di roll incide solo sull'ATR di quel giorno.
- Giorni con barre RTH < 300 (festivi, half day) sono esclusi dal detector e loggati.
- Le barre 16:00–17:59 ET (post-chiusura RTH e manutenzione) non entrano in nessun profilo: né RTH né ON.

## 4. Volume profile

- Istogramma su livelli di prezzo a passo 0.25 (tick NQ). Per ogni barra 1m il volume è distribuito uniformemente sui livelli da `low` a `high` inclusi.
- **POC** = livello con volume massimo (a parità, il più vicino al centro del range).
- **Value area (70%)**: partendo dal POC, si aggiunge il lato (sopra o sotto) con più volume nei due livelli adiacenti, finché la somma ≥ 70% del totale. VAH = livello più alto incluso, VAL = più basso.
- **ON**: calcolato una volta, alle 9:30 ET, dalle barre 18:00 → 09:29 ET. Fisso per la giornata.
- **DEV**: ricalcolato alla chiusura di ogni barra 5m RTH dalle barre 1m 09:30 → chiusura della barra inclusa. Nei primi 15 minuti esiste ma è instabile: non bloccato, `bars_in_profile` è una feature.

## 5. Detector (strutturale, permissivo, zero soglie)

Quattro macchine a stati in parallelo per giornata RTH: (ON, DEV) × (long, short).

```
INSIDE ──[barra 5m chiude fuori VA]──▶ BROKEN ──[barra 5m chiude dentro VA]──▶ EVENTO
   ▲                                     │
   └──────[escursione > max_excursion_minutes]─────┘   reset: è un trend day
```

- "Fuori" per il lato long = `close < VAL`; per lo short = `close > VAH`. "Dentro" = `VAL ≤ close ≤ VAH`. Per DEV i livelli sono quelli calcolati alla chiusura di quella barra.
- In `BROKEN` si traccia l'estremo dell'escursione (low per long, high per short) e si accumulano le barre 1m della finestra.
- L'evento nasce **alla chiusura** della barra 5m di rientro. L'ingresso simulato è **all'open della barra 5m successiva**. Se quell'open cade dopo le 15:30 ET l'evento **non viene emesso** (né tradato né etichettato: con il time-stop alle 15:55 sarebbe quasi sempre uno `0` che insegna solo l'ora).
- Stop = estremo − 1 tick (long) / + 1 tick (short). Target = VAH (long) / VAL (short) della VA di riferimento **al momento del rientro**. Time-stop: flat alle 15:55 ET.
- Per DEV la VA può muoversi fino a inglobare il prezzo senza che il prezzo rientri: l'evento si emette lo stesso; `va_shift` è una feature.
- Nessuna soglia su profondità, volume, delta: un'escursione di 1 tick è un candidato (negativo utile).
- Unico parametro: `max_excursion_minutes = 90`.
- Dopo l'evento la macchina torna a `INSIDE`. Un solo evento per (macchina, escursione).
- Dopo il timeout la macchina entra in `EXHAUSTED` e si riarma (torna a `INSIDE`, senza evento) quando una barra 5m chiude di nuovo dentro la VA **oppure** quando chiude oltre il bordo *opposto* (ha attraversato tutta la VA): in quest'ultimo caso il setup su questo lato è comunque concluso, che sia arrivato prima o dopo il timeout. Un trend di ore non deve produrre un falso rientro con `excursion_minutes` corto. La stessa regola sul bordo opposto vale già in `BROKEN` prima del timeout (nessun cambio lì).

- Stato iniziale `INSIDE` all'apertura RTH anche se l'open è fuori dalla VA overnight: un gap open sotto la VAL seguito da una chiusura 5m dentro è un candidato ON-long (`gap_open` è una feature candidata per la Milestone 1).

**Output** `data/events/events.parquet`, una riga per candidato: `event_id`, `date`, `va_type`, `side`, `break_ts`, `reentry_ts`, `extreme_price`, `vah/val/poc` alla rottura e al rientro, `entry_ref_price` (close di rientro), `entry_price` (open successivo, per il backtest), `stop_price`, `target_price`.

## 6. Feature

Regole: **mai prezzi assoluti** (NQ è passato da ~11k a ~25k in 5 anni: un prezzo grezzo è una feature-anno mascherata); distanze in tick / larghezza VA / ATR; direzioni normalizzate rispetto al lato della rottura ("con" = nella direzione della rottura, "contro" = nella direzione del rientro). Nessuna feature `side`.

Al momento della decisione (chiusura della barra di rientro) l'open successivo non è noto: le feature di rischio/rendimento usano `entry_ref_price` = close di rientro. Il backtest usa l'open reale + slippage.

### 6.1 Feature core (18)

| Gruppo | Feature | Definizione |
|---|---|---|
| Contesto | `va_type` | categorica ON / DEV |
| | `minutes_since_open` | minuti dalle 09:30 ET alla chiusura di rientro |
| | `bars_in_profile` | barre 5m RTH incluse nel profilo DEV (per ON: barre 1m del profilo ON / 5) |
| | `open_vs_on_va` | categorica: open RTH sotto / dentro / sopra la VA overnight |
| Geometria | `va_width_atr` | (VAH − VAL) / ATR |
| | `excursion_depth` | distanza bordo rotto → estremo / larghezza VA |
| | `excursion_minutes` | minuti tra open della barra di rottura e chiusura di rientro |
| | `reentry_close_pos` | (close − bordo rotto) / larghezza VA, positivo verso il bordo opposto (0 = bordo rotto, 1 = bordo opposto) |
| | `va_shift` | (bordo rotto al rientro − bordo rotto alla rottura) / larghezza VA alla rottura, positivo se la VA si è mossa verso l'estremo; 0 per ON |
| Cross-VA | `in_other_va` | 1 se il close di rientro è dentro l'altra VA (DEV per un evento ON, ON per un evento DEV) |
| Rischio/rend. | `stop_dist_atr` | abs(entry_ref − stop) / ATR |
| | `rr_ratio` | abs(target − entry_ref) / abs(entry_ref − stop) |
| Volume (1m) | `vol_slope_excursion` | pendenza OLS del volume 1m sull'indice di barra nella finestra di escursione, divisa per il volume medio della finestra |
| | `vol_at_extreme` | volume della barra 1m che contiene l'estremo / volume medio 1m della finestra |
| | `vol_reentry_bar` | volume della barra 5m di rientro / volume medio delle barre 5m RTH di oggi fino a quella esclusa |
| Order flow (tick) | `delta_excursion` | (vol contro − vol con) / (vol contro + vol con) sui trade della finestra |
| | `delta_reentry` | stessa formula sui trade della barra 5m di rientro |
| | `absorption_score` | vol aggressore "con" nei trade entro 4 tick dall'estremo / vol totale della finestra (molto volume nella direzione della rottura proprio sull'estremo, senza progresso = qualcuno assorbe) |

### 6.2 Feature esplorative (entrano solo se migliorano la validazione dentro il training di ogni finestra)

`roll_day`, `bars_outside` (barre 5m in BROKEN), `poc_pos` (POC oltre l'ingresso verso il target: 1/0), `dist_other_val_atr`, `dist_other_vah_atr`, `overlap_on_dev` (frazione di sovrapposizione tra le due VA), `target_dist_atr`, `vol_excursion_vs_pre` (volume medio 1m della finestra / volume medio 1m dei 30 minuti prima della rottura), `vol_reentry_slope` (pendenza normalizzata degli ultimi 5 volumi 1m), `rel_vol_session` (volume RTH cumulato / media del cumulato allo stesso minuto negli ultimi 20 giorni RTH), `delta_at_extreme` (delta nei 3 minuti prima dell'estremo), `extreme_zone_delta` (delta dei trade entro 4 tick dall'estremo), `large_trade_share` (frazione di volume in trade ≥ 95° percentile di size della finestra), `large_trade_delta` (delta dei soli trade grandi), `cum_delta_divergence` (1 se il prezzo ha fatto un nuovo estremo nella finestra ma il delta cumulato no), `atr_14_5m` (in punti), `day_range_atr` (range RTH finora / ATR).

### 6.3 Vincoli monotoni (prior del trader, iniettati nel modello)

| Feature | Vincolo su p(target) | Tesi |
|---|---|---|
| `delta_excursion` | non decrescente | buyer aggressivi nell'escursione |
| `absorption_score` | non decrescente | seller assorbiti sull'estremo |
| `delta_reentry` | non decrescente | rientro spinto dai buyer |
| `vol_slope_excursion` | non crescente | volume che cala = nessuno vende davvero |
| `vol_reentry_bar` | non decrescente | rientro con volume |
| `rr_ratio` | non crescente | un target più lontano è meno raggiungibile |

Se un vincolo fa crollare la validazione, la feature è non-monotona e il vincolo si toglie (con nota in `oos_looks.md`).

- **ATR**: 14 periodi su barre 5m, calcolato sulle barre fino a quella di rientro inclusa.
- **Test di no-lookahead**: ogni feature calcolata sui dati troncati a `reentry_ts` deve coincidere con quella calcolata sui dati completi.
- **Test di simmetria**: un evento long e il suo specchio short (prezzi riflessi, lati aggressori invertiti) producono lo stesso vettore di feature.

## 7. Label

Dalle barre 1m **dopo** l'ingresso (open della barra 5m successiva al rientro + 1 tick di slippage):

- barra tocca lo stop → `0`; tocca il target → `1`; tocca entrambi nella stessa barra → `0` (conservativo); 15:55 senza toccare nulla → `0` (uscita al close della barra delle 15:55); `gap`: l'open della barra d'ingresso è già oltre lo stop o il target (col tick di slippage) → il trade non è mai entrato davvero, P&L 0 (`exit_reason = "gap"`, distinto da `no_bars`).
- `realized_R`: P&L al netto di costi in unità di rischio (1 R = abs(entry − stop)). Costi default: commissione $2.50/lato, slippage 1 tick ($5) per lato. NQ = $20/punto.
- Ambiguità dichiarata: con barre 1m non si sa cosa è arrivato prima in una barra che tocca entrambi. La regola conservativa sbaglia dalla parte giusta; il caso è raro per NQ (target 30–80 punti, stop 10–30: STIMA da verificare in Milestone 0).

## 8. Modello e decisione

- **LightGBM** classificatore binario. Motivi: dati tabulari piccoli, `NaN` gestiti nativamente (finestra tick mancante → feature vuota, il modello lo sa), veloce, spiegabile con SHAP.
- Griglia piccola (non una search) dentro il training di ogni finestra: `num_leaves ∈ {7, 15}`, `min_data_in_leaf ∈ {20, 50, 100}`, `learning_rate 0.03`, `feature_fraction 0.7`, `n_estimators` da early stopping.
- Early stopping e selezione della griglia su una **fetta temporale** (ultimi 3 mesi del training), mai un campione casuale.
- **Calibrazione isotonica** sulla stessa fetta, così `p = 0.6` significa 60%.
- Set di feature: core 18; le esplorative entrano una alla volta solo se migliorano il Brier sulla fetta di validazione.

**Decisione via valore atteso**, per ogni evento:

```
EV_R = p · rr_ratio − (1 − p) · 1 − costi_in_R
prendi il trade se EV_R > margine          (margine = 0.1 R, parametro)
```

Una soglia fissa su `p` resta nel report solo come confronto.

## 9. Validazione

### 9.1 Walk-forward

Eventi 2021-09-20 → 2026-03-19 (**OOS di lavoro**); 2026-03-20 → 2026-09-19 = **cassaforte** (§11).

```
train 2021-09 → 2023-09 │ test 2023-10 → 2024-03
train 2021-09 → 2024-03 │ test 2024-04 → 2024-09
train 2021-09 → 2024-09 │ test 2024-10 → 2025-03
train 2021-09 → 2025-03 │ test 2025-04 → 2025-09
train 2021-09 → 2025-09 │ test 2025-10 → 2026-03
```

Cinque finestre di test da 6 mesi (30 mesi OOS). Finestra espandente, **embargo 1 giorno** di trading tra fine train e inizio test, **split per data mai per riga** (gli eventi ON e DEV della stessa escursione stanno nella stessa fetta). Variante di robustezza: test da 12 mesi (3 finestre).

Se D6 estende i tick a 10 anni, il training parte dal 2016-09 e le finestre di test restano le stesse.

### 9.2 Quattro colonne nella stessa finestra, mai in cascata

| | Cosa prende |
|---|---|
| **B0** | tutti i candidati |
| **C** | strategia letterale: `vol_slope_excursion < 0` e `delta_excursion > 0` e `vol_reentry_bar > 1` |
| **C-opt** | le stesse 3 regole con soglie cercate a griglia sul solo training di ogni finestra |
| **A** | LightGBM + regola EV |

### 9.3 Controlli anti-inganno (obbligatori nel report)

1. **Shuffle test**: label mescolate → AUC atteso in [0.45, 0.55]. Fuori = leakage.
2. **Modello solo-contesto**: solo feature di contesto + rischio/rendimento. La differenza con A è il valore reale di volume e order flow.
3. SHAP summary + dipendenza per le 6 feature di tesi (§6.3): conferma o smentita della tesi del trader.
4. **Prior geometrico** `p = 1/(1+rr_ratio)`: riga permanente della tabella sanity (AUC, Brier); ogni modello deve batterlo — altrimenti l'AUC misurata è geometria dello stop/target, non skill.

## 10. Backtest e metriche

### 10.1 Motore (event-driven su barre 1m)

- Una posizione alla volta, 1 contratto NQ. Evento durante una posizione → `skipped_in_position` (contato nel report).
- ON e DEV che rientrano sulla stessa barra = stesso trade: si prende quello con EV più alto, l'altro è `duplicate`.
- Ingresso all'open della barra 5m dopo il rientro, ultimo ingresso 15:30 ET, flat 15:55 ET.
- Costi default §7. Metriche in R e in $, con riga MNQ (÷10).

### 10.2 Metriche (OOS aggregato, CI al 95% via block-bootstrap per giorno, 10.000 ricampionamenti, seed fisso)

N trade, trade/giorno, % giorni operativi, win rate, **R medio/trade**, profit factor, expectancy $, max drawdown (R e $), Sharpe giornaliero, mesi negativi/totali, calibrazione (reliability plot), AUC e Brier per finestra, segno di (A − B0) per finestra, decomposizione per `va_type` / lato / fascia oraria (**solo lettura, mai per selezionare**).

### 10.3 Stress (stessa tabella ripetuta)

Slippage 2 e 3 tick (di stress) applicato per lato: sull'ingresso e su ogni uscita a mercato (stop, time-stop) — non solo sugli stop; il target resta un ordine limite, quindi senza slippage. Commissioni ×2; **tolti i 5% trade migliori**.

## 11. Criteri di successo, sguardi, cassaforte, checkpoint

### 11.1 Criteri (pre-registrati, prima di vedere l'OOS)

1. A: R medio/trade > 0 dopo costi, CI che esclude lo zero, a 1 tick; ancora > 0 a 2 tick.
2. (A − B0), (A − C), (A − C-opt) > 0 su R medio/trade, CI che esclude lo zero.
3. Segno positivo di (A − B0) in **≥ 4 finestre su 5**.
4. Shuffle test in [0.45, 0.55]; A batte il solo-contesto su Brier.
   - Dalla 1b: la clausola Brier del criterio 4 si valuta con un bootstrap accoppiato per evento del Brier(A) − Brier(contesto), CI che esclude 0 — pre-registrato il 2026-09-21 dopo lo sguardo 1 della 1a.
5. A prende **≥ 300 trade OOS**; sotto, il verdetto è "non provato".

Tutti e cinque → si apre la cassaforte per la conferma finale e si passa al sotto-progetto 2. Anche uno fallito → il report dice quale e perché.

Ordine di grandezza (calcolo, α = 0.05, potenza 0.8): con ~2000 trade per gruppo sull'OOS aggregato si rileva una differenza di win rate di ~4.4 punti; con ~300 per finestra ne servono ~11. Per questo il verdetto è sull'aggregato.

### 11.2 Regola dei tre sguardi + cassaforte

- `oos_looks.md`: ogni sguardo all'OOS di lavoro seguito da una modifica (detector, feature, parametri) è una riga con data, cosa è cambiato, risultato.
- Sguardi 1–3: liberi.
- Dallo sguardo 4 in poi si continua, ma ogni ciclo richiede un'**ipotesi pre-registrata** scritta in `oos_looks.md` *prima* di far girare il codice: cosa cambia, cosa ci si aspetta, cosa falsificherebbe l'ipotesi.
- **Cassaforte** (2026-03-20 → 2026-09-19): mai usata in nessun ciclo. Si apre **una sola volta**, quando l'utente decide di chiedere il verdetto finale. Dopo l'apertura, il forward test in paper trading (sotto-progetto 2) è l'unico OOS nuovo.

### 11.3 Checkpoint datato

**15 novembre 2026**: primo report OOS completo. Non è una data di chiusura: è il momento in cui utente e Claude decidono insieme se e come continuare, sulla base del report.

## 12. Milestone

| # | Milestone | Esce |
|---|---|---|
| 0 | Barre 1m 10 anni + detector + **conteggio eventi** per anno / `va_type` / lato; distribuzione di stop e target in punti | `reports/milestone0_counts.md`; decisione tick 5 vs 10 anni |
| 1a | **Senza order flow**: feature di contesto/geometria/volume da barre 1m + label + baselines B0/C-senza-delta + walk-forward + sanity + backtest + report; test no-lookahead e simmetria verdi | `data/features/features_1a.parquet`, `reports/oos_report_1a.md` (benchmark) |
| 1b | **Order flow**: acquisto tick (opzione A o B, §3.1) + feature delta/absorption + rerun identico della pipeline 1a | `data/features/features_1b.parquet`, `reports/oos_report_1b.md` con confronto 1b − 1a (EV, win rate, Brier) |
| 2 | (assorbita in 1a/1b) | — |
| 3 | (assorbita in 1a/1b) | — |

Milestone 0 chiusa il 2026-09-21: `reports/milestone0_counts.md` (N = 19.210, N5 = 9.438, 7,7 candidati/giorno; stop mediano 20,75 pt, target 40,25 pt, rr mediano 1,92). Regola §12 → 5 anni di tick. Note per la 1a/1b dalla review finale: `symbol` nelle barre è la costante `NQ.v.0`, `roll_day` va derivato da `metadata.symbology.resolve` (gratis); le finestre tick vanno chiavate per `(break_ts, reentry_ts)` e unite per giorno; il feature builder non deve mai leggere `entry_ts`/`entry_price` (post-decisione) — da rendere un test.

## 12-bis. Milestone 1b-S — order flow su giorni campionati (decisione del 2026-09-21)

**Vincolo**: nessuna spesa oltre i crediti Databento residui (~$112). I trade tick per tutte le finestre dei 4,5 anni costerebbero STIMA $230 (finestre unite per giorno); la 1b si fa quindi su un **campione di giorni**.

**Campionamento pre-registrato** (deciso prima di vedere qualsiasi numero tick):
- Popolazione: giorni validi con `session_date` in [`walkforward.train_start`, `vault.start`).
- Strato = **mese di calendario** (55 strati, 2021-09 → 2026-03): in ogni mese si estraggono `round(0.45 · n_giorni_validi)` giorni (minimo 1) con `numpy.random.default_rng(0)`. La quota costante per mese rende il campione omogeneo per anno e per ciascuna delle 5 finestre walk-forward, sia nel train sia nel test.
- Regola di budget: se il costo esatto (somma delle `get_cost` sulle finestre unite dei giorni campionati) supera `data.tick_budget_usd` (105), la quota si riduce a `quota · budget / costo` e si ricampiona con lo stesso seed. La quota effettiva, il seed, i conteggi per mese e il costo esatto vengono scritti in `reports/1b_sampling.md` **prima** dell'acquisto.
- Finestre: unione per giorno degli intervalli `[break_ts, reentry_ts)` di tutti gli eventi del giorno (sovrapposte o adiacenti → una sola richiesta), schema `trades`.

**Sottoinsieme S** = eventi dei giorni campionati. La 1a viene **rieseguita su S** con lo stesso codice (`predictions_1a_S`), così il confronto 1b − 1a è appaiato evento per evento sulle stesse 5 pieghe. Il confronto è un unico sguardo (#2) in `oos_looks.md`.

**Feature 1b** = `CORE_1A` + `delta_excursion`, `delta_reentry`, `absorption_score` (core, con i vincoli monotoni di §6.3) e le 5 esplorative tick di §6.2; `roll_day` resta rimandata. Convenzione lato Databento: `side = "A"` = aggressore in vendita, `"B"` = aggressore in acquisto, `"N"` ignorato — verificata con un test sui dati reali (barra 1m con close ≫ open ⇒ volume B > volume A nella maggioranza dei casi).

**Modifiche di modello applicate a entrambe le esecuzioni (1a-S e 1b), pre-registrate**: calibrazione isotonica su una metà temporale della validazione separata da quella usata per early stopping/griglia/selezione; `p_context` e `p_rw` persistiti per evento; calibratore salvato.

**Criteri per la 1b-S** (i 5 criteri di §11.1 restano il riferimento, ma su ~45 % degli eventi): il verdetto primario è il **confronto appaiato**: (i) `Brier(A_1b) − Brier(A_1a)` per evento, CI block-bootstrap per giorno che esclude 0; (ii) `Brier(A_1b) − Brier(p_rw)` idem; (iii) `R medio(A_1b) − R medio(A_1a)` appaiato per giorno. Il criterio 5 si legge in proporzione (≥ 300 · quota). Se (i) e (ii) sono positivi, si compra il resto delle finestre e si ripete sui 4,5 anni interi (sguardo #3, pre-registrato come "stessa pipeline, più dati").

## 12-ter. Milestone 1c — sguardo #3 pre-registrato: "informazione oltre la geometria calibrata" (decisione del 2026-09-21, dopo il consiglio a tre)

**Esito della 1b-S (sguardi 2 e 2-bis)**: (i) (ii) (iii) FAIL, (iv) PASS; il prior geometrico `p_rw = 1/(1+rr_ratio)` batte entrambi i modelli (Brier 0.1777 vs 1a_S 0.1881 vs 1b 0.1913). Regola §12-bis applicata: **non si acquistano le finestre restanti**. Diagnostiche post hoc (riga 2-ter di `oos_looks.md`, misure del consiglio in sola lettura): `Brier(p) − Brier(prior) = V − 2C` con V = E[(p − p_rw)²] e C = E[(p − p_rw)(y − p_rw)]; C > 0 con CI che esclude 0 in tutte le versioni (+0.004/+0.005) ma l'incremento dovuto alle tick ha C = +0.0017 [−0.0001, +0.0035] e V +0.004 (varianza senza covarianza); l'isotonica su ~100 punti raddoppia V senza toccare C; il prior è ottimista di +0.040 (media p_rw 0.378 vs tasso base 0.338) e un Platt sul solo prior vale 0.1801 vs 0.1820; guadagno massimo ottenibile con shrinkage lineare in-sample 0.0026 (4.677 eventi) / 0.0016 / 0.0012; semi-ampiezza della CI appaiata 0.0026 a n = 4.677 e ≈ 0.005 a n = 2.059. **Il disegno che segue è stato scelto DOPO queste misure**: ogni PASS è quindi "candidato" finché non replicato su dati mai visti (cassaforte o forward test).

**Domanda dello sguardo #3**: c'è informazione, nelle feature, oltre la geometria stop/target *calibrata*? E, condizionatamente, l'order flow ne aggiunge?

**Ipotesi** (falsificabili): H1 — partendo dal prior calibrato come offset, un modello con le 15 feature core 1a ha Brier inferiore al prior calibrato sui 4.677 eventi di test (effetto atteso ≤ 0.001, potenza dichiarata ~20–50 %). H1b — le 3 feature order flow core abbassano ulteriormente il Brier sui 2.059 eventi di S (effetto atteso ≤ 0.0007, potenza 10–25 %). Attesa dichiarata dal consiglio: ≥ 70 % di probabilità che H1 non passi.

**Bracci** (stesso training, tutti gli eventi dal `walkforward.train_start`, stesse 5 pieghe della 1a):
- **L1** = prior grezzo `p_rw`. **L2** = prior calibrato: regressione logistica `y ~ a·logit(p_rw) + b` stimata, per ogni piega, sul **solo `fit_df`** (n_fit 3.347–7.250; mai su validazione o test).
- **A** = `CORE_1A` (15 feature) su tutti gli eventi.
- **B** = A + `ORDERFLOW_CORE` (3) con le tick a NaN sui giorni non campionati (`features_1c.parquet` = left-join di `features_1a` con le 3 colonne tick di `features_1b` su `event_id`; verificato che le 46 colonne comuni sono identiche nei due file). Eventi di training con tick per piega: 1.664–3.396 (misura del consiglio).
- **A′** = A con `seed = 1` (solo per la guardia G2; fa parte dell'unica esecuzione).
- Esplorative (`EXPLORATORY_1A`, `ORDERFLOW_EXPLORATORY`) **spente**: nessuna forward selection.

**Pipeline comune, pre-registrata** (uguale per A, B, A′): `init_score = logit(L2)` su `dtrain` e `dval`; predizione = sigmoide(`raw_score` degli alberi + `logit(L2)`); **nessun calibratore post hoc** (`split_val` non usato: la validazione intera, 3 mesi, serve a griglia ed early stopping); tutto il resto identico alla 1b-S — griglia `num_leaves {7,15} × min_data_in_leaf {20,50,100}`, `learning_rate 0.03`, `feature_fraction 0.7`, `early_stopping 100 / max_rounds 2000`, vincoli monotoni (`rr_ratio: −1` compreso), `seed 0`, embargo, label, `p_rw`, `realized_R`, costi, decisione `EV > 0.1 R`, motore, bootstrap per giorno 10.000 / seed 0, campione S invariato, **zero acquisti**, cassaforte chiusa. Test di annidamento (pytest, prima del run): con 0 round `p ≡ L2` (tolleranza 1e-9). Sanity: shuffle test sul solo punteggio degli alberi (offset escluso), **5 seed**, banda [0.45, 0.55] sulla media; simmetria e no-lookahead invariati. **Emendamento del 2026-09-22 (prima dell'esecuzione, review del Task 3)**: con label mescolate e offset *fisso* stimato sulle label vere, gli alberi imparano a cancellare l'offset e il loro punteggio diventa anti-correlato con la label vera (misurato su dati sintetici: AUC media 0.19) — il null registrato era mal posto. Il controllo di sanità diventa: label mescolate su fit e validazione **e L2 rifittata sulle label mescolate** (offset ≈ costante, null pulito), 5 seed, banda [0.45, 0.55] sulla media; la variante a offset fisso viene comunque riportata, etichettata «offset fisso (registrazione originaria)», senza banda. Lo shuffle resta un controllo di sanità: non entra in G1/P1/S1/G2 né nell'albero degli esiti.

**Criteri** (CI 95 % che esclude 0 = *candidato*; CI 99 % = *confermato*, correzione dichiarata per i ~5 disegni considerati dal consiglio):

| # | criterio | statistica | n | soglia | potenza dichiarata |
|---|---|---|---|---|---|
| G1 validità | Brier(A) − Brier(L1) | appaiata per evento, block per giorno | 4.677 | invalido se CI > 0 | atteso PASS (50–97 %) |
| **P1 primario** | Brier(A) − Brier(L2) | idem | 4.677 | CI < 0 → candidato (95 %) / confermato (99 %) | ~20–50 % (effetto ≤ 0.0007, semi-ampiezza ≈ 0.0007–0.0026) |
| S1 secondario | Brier(B) − Brier(A) su S — **letto solo se P1 ≥ candidato** | idem | 2.059 | idem | 10–25 % (effetto ≤ 0.0007, semi-ampiezza ≈ 0.001–0.005) |
| G2 unione | mediana \|p_B − p_A\| sui 2.618 eventi non-S ≤ 2 × mediana \|p_A − p_A′\| | — | 2.618 | altrimenti S1 **invalido** (non FAIL); P1 resta valido | — |
| D descrittivi | R medio di A, B (CI); B − A appaiato per giorno; trade A ≥ 300, B ≥ 134; Jaccard; SHAP delle tick; i 5 criteri §11.1 su A | — | — | nessun verdetto | — |

**Esiti pre-registrati** (albero delle conseguenze):
- G1 fallisce → lo sguardo è **comunque consumato**; un rerun (#4, stessa pre-registrazione, criteri intoccati) è ammesso **solo** se un nuovo test pytest dimostra un bug (fallisce sul codice vecchio, passa sul nuovo) senza toccare un solo parametro; altrimenti G1 fallito = P1 FAIL definitivo.
- P1 FAIL con stima ≥ 0 → «nessuna informazione rilevabile oltre la geometria calibrata a questa n»; L2 è il modello di riferimento; S1 solo descrittivo; order flow non comprato.
- P1 candidato / confermato → S1 letto: candidato → order flow «candidato»; FAIL → «non provato (potenza 10–25 %)».
- In ogni caso il modello per il forward test è **B** (annida A e L2; se G2 fallisce → A); L1, L2, A, B e B0 si calcolano su ogni evento live.
- **Non si fa**: quarto sguardo sull'OOS di lavoro senza ipotesi pre-registrata; acquisto delle finestre restanti (credito riservato ai tick della cassaforte, STIMA $22.7); ensemble; apertura della cassaforte prima del checkpoint; ritocchi a detector/feature/costi/decisione dopo il risultato; re-render dopo i risultati se non come sguardo 3-bis dichiarato.

**Forward test (sotto-progetto 2), pre-registrato ora, solo se P1 ≥ candidato**: primario Brier(B) − Brier(L2) per evento live, CI 95 % < 0 (semi-ampiezza ≈ 0.001 a 2.000 eventi); co-primario economico R medio dei trade di B > 0 dopo costi, CI 95 %. Arresto: finale a **2.000 eventi** (≈ 260 giorni ≈ 12–13 mesi a 7.7 candidati/giorno, STIMA); un solo interim a 330 trade, solo per futilità (R medio < −0.10). Con SD(R) ≈ 1.6 (misurata: 1.64 nella 1a, 1.50 nella 1b) il forward risolve un edge ≥ 0.20 R con ~400 trade (≈ 1–1.6 anni) e ≥ 0.10 R con ~1.600 trade (≈ 3.5–6 anni): sotto 400 trade non si conclude. Invalidano: modifiche a detector/feature/costi/decisione durante il test; feed live senza test di mappatura dei lati A/B; tick mancanti > 10 % dei giorni; decisioni discrezionali dell'utente registrate al posto di quelle del modello; stop discrezionali; uso di C come filtro.

**Cosa cambierebbe idea al consiglio (dichiarato prima)**: Opus — con G1 PASS, stima di P1 ≥ +0.0005 (gli alberi peggiorano il prior calibrato anche partendo da esso) falsifica «è varianza, non assenza». Fable — S1 con CI < 0 al 95 % **e** C dell'incremento tick (B − A, contro L2) con CI che esclude 0 ritira «l'order flow aggiunge varianza e zero covarianza».

## 13. Struttura del repo

```
NQ-ML/
├── .env (gitignored) · .gitignore · pyproject.toml · config.yaml · oos_looks.md
├── nqml/
│   ├── data/       databento_client.py (guardia costo + cache), bars.py (1m→5m, sessioni NY), trade_windows.py
│   ├── profile/    volume_profile.py, sessions.py
│   ├── detector/   state_machine.py, events.py
│   ├── features/   context.py, geometry.py, volume.py, orderflow.py, volatility.py, build.py
│   ├── labels/     labeler.py
│   ├── model/      train.py, decision.py, baselines.py, walkforward.py, sanity.py
│   ├── backtest/   engine.py, metrics.py, stress.py
│   └── report/     render.py
├── scripts/        00_check_cost.py … 07_report.py (numerati, idempotenti)
├── data/ (gitignored)   raw/ → interim/ → events/ → features/
├── reports/        milestone0_counts.md, oos_report.md, figures/
├── tests/
└── docs/superpowers/specs/
```

- `config.yaml` è l'unica fonte dei parametri (date, sessioni, tick, costi, `max_excursion_minutes`, griglia, margine EV, soglia di conferma costo). Ogni report riporta hash di `config.yaml` e commit git.
- Dipendenze: `databento`, `python-dotenv`, `pandas`, `pyarrow`, `numpy`, `lightgbm`, `scikit-learn`, `shap`, `matplotlib`, `pyyaml`, `pytest`. Python 3.13, venv in `NQ-ML/.venv` (già creato, `databento 0.86.0` installato).
- Seed fisso ovunque (bootstrap, LightGBM, griglia).

## 14. Test (pytest, TDD per ogni modulo)

I quattro decisivi:

1. **No-lookahead** (§6): feature su dati troncati == feature su dati completi.
2. **Simmetria** (§6): long e specchio short → stesso vettore di feature.
3. **DST** (§3.3): 2026-03-10 e 2026-11-03 → open RTH a 13:30 UTC e 14:30 UTC.
4. **Guardia di costo**: client Databento con costo stimato sopra soglia rifiuta senza conferma esplicita; cache hit non chiama l'API (mock, nessuna chiamata reale nei test).

Da manuale: profilo su barre sintetiche con VAH/VAL/POC noti (simmetrico, singolo prezzo, 70% esatto); macchina a stati su sequenze costruite (evento semplice, timeout, rientro per VA che si muove, mai-rientra, specchio short); labeler (target / stop / entrambi → 0 / time-stop → 0, aritmetica dei costi in R); decisione EV; walk-forward (nessuna sovrapposizione di date, embargo rispettato); motore (una posizione, duplicati, equity = somma dei `realized_R`); bootstrap deterministico col seed e CI che contiene la stima puntuale.

## 15. Fuori scope (sotto-progetto 2 e oltre)

- Segnale live (feed real-time Databento Live o broker, alert, esecuzione).
- Modelli sequenziali (1D-CNN/GRU) sull'escursione grezza.
- Altri strumenti (ES/RTY/YM) come dati aggiuntivi: opzione dichiarata, spenta.
- Due posizioni simultanee: si valuta solo se `skipped_in_position` risulta alto.

## 16. Rischi noti

| Rischio | Mitigazione |
|---|---|
| Pochi eventi (N < 6k su 5 anni) | Milestone 0 conta prima di comprare i tick; estensione a 10 anni; vincoli monotoni; 18 feature core |
| Lookahead nascosto | test §14.1, shuffle test, decisione alla chiusura di rientro e ingresso all'open successivo |
| Metriche instabili per finestra | verdetto sull'OOS aggregato con CI bootstrap; trade bounded in [−1 R, rr·R] |
| Overfitting per iterazione | `oos_looks.md`, ipotesi pre-registrate dal 4° sguardo, cassaforte |
| Profili da barre 1m ≠ profili tick | dichiarato; è ciò che vede TradingView; riserva tick completi ultimo anno ($115.30) |
| Costo tick sopra stima | guardia `get_cost` per batch con soglia in `config.yaml` e conferma esplicita |
| Fuso orario / DST | UTC su disco, test DST |
