# Famiglia ml — REPORT (discovery 2010-06 → 2018-12)

**In breve.** Un modello generico (LightGBM, 40 feature solo passate, 12 istanti fissi al giorno) ha una
capacità **piccola ma stabile** di ordinare i rendimenti a 30-60 minuti (IC ≈ +0,02/+0,03, positivo in
7 anni su 7 nel walk-forward). **Non si incassa**: il lordo sui trade migliori (~0,4-0,7 punti) resta sotto
il costo di 0,75 punti in ogni variante della regola. Consegno **un solo candidato, di tipo "regularity"**
(`ml_rank30`), e **nessun candidato tradeable**. Test registrati: **93** (`lab/ledger/ml.jsonl`, più una riga
PIANO e una NOTA), di cui 40 sono lo scan univariato delle feature.

## 0. Piano fissato prima di guardare (riga `PIANO` del registro)
- Righe: sessioni valide × 12 istanti di decisione (10:00, 10:30, …, 15:30 NY). Le feature usano solo barre
  che iniziano prima di t; ingresso all'open della barra t.
- Target primario: y30 = (close a t+29 − open a t) / (sig1m·√30); sig1m = media delle deviazioni standard dei
  rendimenti 1m RTH delle 20 sessioni **precedenti**. Secondari: 15 e 60 minuti, e la chiusura RTH.
- Unità: P&L in punti NQ netti (costo 0,75), riportata anche in unità di volatilità.
- Walk-forward dentro il discovery: per Y = 2012…2018 si addestra su sessioni < 1° gennaio Y meno 5 sessioni di
  embargo e si prevede l'anno Y. Tuning (4 configurazioni LightGBM + numero di alberi con early stopping) solo su
  una validazione interna = ultimo anno del training, anch'essa con embargo di 5 sessioni.
- Metrica 1: IC di Spearman sulle previsioni fuori campione 2012-2018, CI a blocchi per giorno.
- Regola R1, fissata in anticipo: si opera se |pred| ≥ 90° percentile delle 3.000 |pred| precedenti (solo passato);
  lato = segno; uscita a tempo; trading valutato 2013-2018.
- Baseline: sempre long negli stessi istanti; Ridge a 3 feature (r_sess, r_on, r30); Ridge su tutte le 40 feature.

## 1. Dati e feature (`features.py`)
Griglia di 1440 minuti per sessione (17:00 → 16:59) su prezzi **adj** (il roll cade di notte). Feature
(tutte scalate con misure del passato, **nessuna normalizzazione stimata sul campione**): rendimenti a
5/15/30/60/120/240 minuti, dall'apertura, notte, ieri (RTH e close-close), 5 e 20 giorni, distanza dalla
chiusura di ieri; volatilità realizzata a 15/30/60 minuti, della sessione e della notte; regime di vol
(5 contro 100 sessioni) e livello di vol in bp; volume relativo per ora (cumulato, ultimi 30', notte) contro la
media delle 20 sessioni precedenti allo stesso minuto; posizione nel range di oggi e di ieri, distanza da
massimo/minimo di oggi e della notte, dal VWAP; skew, curtosi e autocorrelazione dei rendimenti 1m (60' e
sessione), variance ratio 5m/1m; distanza dai numeri tondi (prezzo grezzo); ora e giorno.

**Controlli di leakage**
- `test_leak.py`: si perturbano con rumore tutte le barre dalla decisione in poi (e le sessioni successive) e si
  ricalcola tutto. Le feature della riga devono restare identiche **al bit**. Esito: 0 fallimenti (controllo
  positivo: il target invece cambia).
- Controllo positivo nel walk-forward (`ml_diag_poscontrol`): una feature che contiene il 10 % del target
  viene vista, IC 0,048.
- Placebo (`ml_diag_placebo`): con il target permutato fra i giorni l'IC scende a +0,003 [−0,011; +0,016].
- Rimbalzo bid-ask (`ml_REG_M1_h30_bounce_*`): con l'ingresso ritardato di 1 minuto l'effetto scende da
  0,0256 a 0,0186 in unità di vol (p 0,015). Circa un quarto sta nel primo minuto; il resto sopravvive.
- **Errore mio, dichiarato**: la scomposizione dell'IC "fra giorni / dentro il giorno" (`ml_diag_decomp_*`,
  IC fra giorni +0,15) era **contaminata da look-ahead**: la media giornaliera delle previsioni include le
  previsioni delle 15:30, che conoscono i rendimenti delle ore precedenti, cioè gli esiti degli slot
  precedenti. È ritirata (riga `ml_note_decomp_invalid`). Al suo posto c'è l'IC per slot, che non ha questo difetto.
- **Bug trovato e corretto**: nella prima esecuzione (`ml_M1_lgb_h30`) l'IC della validazione interna era NaN
  per indici disallineati, quindi il tuning sceglieva sempre la prima configurazione. Corretto e rifatto in `ml_M1b_lgb_h30`.
  Entrambe le righe restano nel registro.

## 2. Risultati principali (walk-forward, fuori campione dentro il discovery)

| test | IC [CI 95 %] | trade R1 p90: netto punti [CI] | lordo | anni + |
|---|---|---|---|---|
| B0 sempre long, h30 | — | −0,764 [−0,94; −0,59] | −0,014 | 0/6 |
| B1 Ridge 3 feature, h30 | −0,006 [−0,021; +0,008] | −0,098 [−0,69; +0,49] | +0,65 | 3/6 |
| B2 Ridge 40 feature, h30 | +0,012 [−0,003; +0,026] | −0,031 [−0,72; +0,67] | +0,72 | 2/6 |
| **M1 LightGBM, h30 (primario)** | **+0,020 [+0,006; +0,034]** | −0,383 [−0,84; +0,10] | +0,37 | 2/6 |
| M1 h15 | +0,019 [+0,004; +0,033] | −0,370 [−0,69; −0,06] | +0,38 | 0/6 |
| M1 h60 | +0,029 [+0,011; +0,046] | −0,070 [−0,61; +0,50] | +0,68 | 3/6 |
| M1 fino alla chiusura | +0,009 [−0,030; +0,049] | −0,249 [−6,4; +6,0] | +0,50 | 2/6 |
| E1 LightGBM 5 semi, h60 | +0,028 [+0,010; +0,046] | −0,160 [−0,75; +0,46] | +0,59 | 2/6 |
| E2 LGB+Ridge, h60 | +0,024 [+0,005; +0,044] | +0,095 [−0,84; +1,05] | +0,85 | 4/6 |
| E4 LGB classificazione, h60 | +0,032 [+0,014; +0,051] | −0,213 [−0,68; +0,26] | +0,54 | 1/5 |

- L'IC di M1 è positivo **in tutti e 7 gli anni** (h30: da 0,013 a 0,033). È lo stesso per ogni seme,
  obiettivo e orizzonte fino a 60 minuti. Si spegne verso la chiusura.
- Il LightGBM batte la baseline lineare a 3 feature, che ha IC ≈ 0, e il Ridge su tutte le feature, che è più
  debole e non significativo. Non batte il costo.
- Beta: la quota long dei trade va da 0,5 a 0,6 e la deriva intraday 10:00-16:00 del periodo è ≈ 0
  (sempre long: lordo −0,01 punti a 30'). Il beta non spiega né aiuta nulla, perché la salita del Nasdaq
  2013-2018 sta quasi tutta nella notte.
- Da dove viene l'IC:
  - lo scan univariato (40 test) dà come più forti r_20d (+0,024, p 0,001) e r_5d (+0,018), cioè momentum
    multi-giorno; poi regime di vol (−), curtosi (+), skew (−) e reversal a 5-15' (−);
  - l'ablazione dice che né le sole feature veloci (IC 0,000) né le sole lente (0,011, non significativo) bastano:
    l'effetto sta nella combinazione;
  - per slot è diffuso su tutta la giornata (nessuno slot domina).

**Perché non si incassa.** La regola R1 prende il decile estremo, con un lordo atteso ≈ 0,05-0,06 in unità di
vol. Il costo in unità di vol, 0,75/(sig1m·√h), nel 2013-2017 vale 0,06-0,12. Solo con volatilità alta in punti
(2018) il costo scende sotto l'effetto, ma nel discovery quei trade sono troppo pochi (24-60) per dire qualcosa
(`ml_diag_costregime_*`).

## 3. Varianti di regola e altri disegni (tutti scartati)
- **Quantile 95 % / 98 %** (h30, h60): netto da −0,31 a +0,47 punti, nessun CI sopra lo zero, anni positivi 2-4
  su 4-6. Il miglior numero (h60 q98 +0,47) poggia su 768 trade e cade con il drop-top20 (−0,50).
- **R2, regola sul costo** (opera se |pred|·sig1m·√h > c·costo, con c = 1 o 2): instabile, da −0,53 a +0,64 con
  n tra 252 e 2.028 e anni positivi 1-2. Scartata.
- **Modello giornaliero**: una decisione alle 10:00 e uscita alle 15:59.
  - LGB: IC −0,019, netto +0,08.
  - Ridge: IC +0,026 non significativo, netto +1,9 punti con p_pos 0,041. Lo fanno due anni su sei, 2016 e
    2018, e togliendo i 20 trade migliori va a −0,60. Scartato.
  - Segno di r_20d / r_5d (test **post hoc** suggeriti dallo scan): −0,35 e +1,24 punti, CI con dentro lo zero. Scartati.
- **Regolarità a 60'** (E1, tutti gli slot, lato centrato): lordo +0,255 punti (p 0,09) e +0,023 in vol
  (p 0,015). Più debole del 30' perché gli esiti si sovrappongono. Non promossa.

## 4. Candidato consegnato: `ml_rank30` (kind = "regularity")
**Regola.** A ogni istante 10:00-15:30 si prende posizione nel verso di (previsione − mediana delle 3.000
previsioni precedenti) e si esce dopo 30 minuti. Il centraggio sulla mediana passata rende il lato ~50/50
long/short (0,506), quindi si misura la capacità di **ordinare** i rendimenti, non il beta. La previsione è la
media di 5 LightGBM con semi diversi. Motivo della media: con un solo seme l'effetto andava da 0,013 (seme 11,
p 0,09) a 0,028 a seconda del seme (`ml_SENS_*`), e un risultato che dipende dal seme è rumore finché non si
dimostra il contrario.

**Unità, dichiarata.** Per questo candidato `gross_pts` è il rendimento firmato **in unità di volatilità**
(y30, la stessa unità del target fissata nel PIANO). È la misura naturale di un ordinamento e pesa allo stesso
modo anni calmi e agitati. La colonna `gross_points` contiene la stessa misura in punti. Ho guardato entrambe prima
di scegliere: in punti è più debole (p 0,011 contro 0,002). Il controller può valutarle tutte e due.

**Modelli.** Per ogni anno Y ≤ 2018 `fn` usa i modelli walk-forward di quell'anno, quindi sul discovery
restituisce solo previsioni **fuori campione**. Dal 2019 usa i 5 modelli addestrati una volta su tutto il
discovery: `lab/ml/models/lgb_y30_final_s*.txt`, generati da `train_models.py`. Con il warmup di 400 sessioni
i lati sono identici a quelli dell'esecuzione sull'intero periodo (verificato).

**Numeri discovery** (restituiti da `fn`, `test_candidates.py` → OK):

| misura | valore |
|---|---|
| n trade (giorni) | 18.700 (≈ 1.560) |
| lordo, unità di vol | **+0,0228 [+0,0085; +0,0373]**, p bilaterale 0,0022, anni positivi **7/7** |
| lordo, punti | +0,210 [+0,046; +0,375], p 0,011, 7/7 |
| netto, punti (se fosse operata) | **−0,54**: non incassabile |
| senza i 20 trade migliori (vol) | +0,016 |
| sensibilità | finestra della mediana 1.000 / 6.000: +0,0205 / +0,0234; semi singoli 0,013-0,028 |

**Potenza in validazione (stima onesta).** SE in validazione ≈ 0,0084 in unità di vol su ~1.190 sessioni, da
cui t atteso ≈ 2,7 **se l'effetto è pieno**. Con Bonferroni la potenza vale:

| K | potenza, effetto pieno | potenza, metà effetto |
|---|---|---|
| 3 | ≈ 0,62 | ≈ 0,07-0,15 |
| 10 | ≈ 0,46 | ≈ 0,07-0,15 |
| 20 | ≈ 0,37 | ≈ 0,07-0,15 |

La stima discovery è gonfiata dalla selezione: 93 test guardati, e la statistica centrata è stata scelta fra 3
varianti di regolarità. Quindi la verifica ha una probabilità concreta di finire in "non si sa". Lo dico prima.
Osservazione, **non** un candidato: se l'ordinamento reggesse, nel 2019-2023 la volatilità in punti è più alta e
il costo relativo più basso. Una versione operata potrebbe allora avere senso, ma il discovery non la sostiene e
non la propongo.

## 5. Che cosa ho scartato e perché, in una riga ciascuno
- M1 e varianti come **strategie**: netto negativo o CI con dentro lo zero, anni positivi ≤ 4/6, drop-top20 negativo.
- Modello giornaliero LGB/Ridge, segno di r_20d/r_5d: nessuna significatività, dipendenza da 1-2 anni.
- Regolarità a 60 minuti e al decile estremo: più deboli del 30' e con esiti sovrapposti.
- Scomposizione dell'IC fra giorni: ritirata per look-ahead (vedi §1).

## 6. Note su `core.py` (nessun bug trovato)
- L'aggiustamento del roll è additivo e porta i prezzi adj del 2010 ~3.800 punti sopra i grezzi. I **rendimenti
  percentuali** calcolati sui prezzi adj sono quindi distorti negli anni lontani. Qui uso solo differenze in punti
  divise per scale di vol in punti, e il prezzo grezzo per i numeri tondi e il livello di vol in bp.

## 7. File
- Codice: `features.py`, `common.py`, `run_01…run_13_*.py`.
- Controlli: `test_leak.py`.
- Candidato: `candidates.py`, `train_models.py`, `test_candidates.py`.
- Modelli: `models/` (40 file + `meta.json`). Cache: `cache/`.
