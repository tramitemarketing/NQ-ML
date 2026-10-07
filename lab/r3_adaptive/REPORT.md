# Famiglia «r3_adaptive»: si può scegliere online QUALE regola funziona?

Fase: **solo discovery** (2010-06-07 → 2018-12-31, 2.121 sessioni valide; confronti su 2011-07 → 2018-12,
così ogni lookback è completo). Unità dichiarata prima di guardare: **punti NQ per 1 contratto**, netto =
lordo − 0,75 per trade. Tutto in RTH (niente notte, niente roll, beta trascurabile: misurato comunque).
Piano pre-registrato in `s00_piano.py`, prima riga del registro, prima di qualunque risultato.

**Il risultato in una riga: la persistenza di QUALE regola funziona, alla scala mensile del piano, non si
distingue dal caso; le 106 meta-procedure pre-registrate sono tutte negative al netto già in ricerca, e
nessuna ha un vantaggio lordo distinguibile dal placebo. Zero candidati.** Esiste una debole persistenza a
10 sessioni (trovata dopo), ma sta nelle regole con segnali di più giorni, vale 0,3-0,6 punti lordi e non è
significativa in punti.

---

## 1. La libreria (fissata prima)

374 regole, ciascuna al massimo 1 trade al giorno: 6 istanti (10:00, 11:00, …, 15:00) × 3 orizzonti (30,
60 minuti, fino alle 16:00) × 11 segnali × {segui, contro}. Segnali = segno delle feature causali di
`lab/r2_autosearch/common.py`: r15, r60, r_open (dall'apertura), gap, r_on (notte), r_prev (ieri), r_5d,
pos_today / pos_night / pos_20d (segno di posizione − 0,5), e «long». Ingresso all'open della barra T.
«Contro» è lo specchio esatto di «segui» sul lordo.

## 2. A — la regolarità: la performance recente di una regola predice il mese dopo? (`s01_persistenza.py`)

IC_m = correlazione di Spearman, fra le 374 regole, del lordo medio nelle 21·L sessioni precedenti il mese
contro il lordo medio del mese. 90 mesi (2011-07 → 2018-12). Due nulli: **«segno per giorno»** (ogni
sessione riceve un ±1 che moltiplica tutti i rendimenti futuri, feature intatte: conserva la struttura di
correlazione fra le regole; 500 repliche) e **«libreria a lato casuale»** (il lato di ogni regola ogni giorno è
un ±1 casuale; 200 repliche).

| L (mesi) | IC medio | nullo segno: mediana [q95] | p | nullo lato casuale: mediana [q95] | p |
|---|---|---|---|---|---|
| 1 | +0,018 | +0,001 [+0,028] | 0,16 | +0,000 [+0,010] | 0,000 |
| **3 (principale)** | **+0,022** | +0,000 [+0,028] | **0,10** | −0,000 [+0,010] | 0,000 |
| 6 | +0,024 | −0,001 [+0,027] | 0,08 | −0,000 [+0,010] | 0,000 |
| 12 | +0,020 | −0,001 [+0,026] | 0,11 | −0,000 [+0,010] | 0,000 |

- **Il nullo «lato casuale» è troppo debole** e va letto come tale: rompe la correlazione fra regole che
  condividono istante, orizzonte e segnale, quindi sottostima enormemente la varianza dell'IC (q95 0,010
  contro 0,028). Il nullo giusto è «segno per giorno», e lì **nessun L passa** (p 0,08-0,16). La regola del
  piano (passare entrambi) non è soddisfatta.
- Serie IC (L = 3) per anno: 2011 −0,00, 2012 −0,02, 2013 −0,05, 2014 +0,11, 2015 +0,05, 2016 +0,05,
  2017 +0,02, 2018 −0,01 (4/8 anni). Bootstrap a blocchi di 6 mesi: +0,022 [−0,004; +0,051].
- Solo regole «segui» (senza specchi): IC +0,008…+0,016, p 0,17-0,31.
- A livello di **famiglia** (trend = tutte le «segui», MR = tutte le «contro»): la correlazione fra lo spread
  passato e quello del mese dopo è +0,12 (L = 3, p 0,18), +0,26 (L = 6, p 0,03), +0,21 (L = 12, p 0,05).
  Vedi §5: non aggiunge niente alla famiglia trend statica.

## 3. B — le 106 meta-procedure pre-registrate (`s02_meta.py`)

Griglia fissata prima: **top-k** (96) = ribilanciamento {mese, settimana} × L {1, 3, 6, 12 mesi} × k {1, 5,
20} × punteggio {media netta, t netto} × filtro {nessuno, solo regole con media > 0}; **Hedge** (6) = pesi
∝ exp(η · somma dei netti passati in unità di ATR20), η {0,05; 0,2; 1}, memoria {infinita, emivita 63};
**regime** (4) = ogni giorno tutta la famiglia trend o tutta la MR secondo autocorrelazione lag-1 dei
rendimenti di 30 minuti, variance ratio, efficiency ratio (20 sessioni precedenti, sopra/sotto la mediana
causale delle 250 precedenti) o spread di famiglia delle 20 sessioni. Ricerca 2011-07 → 2015-12, verifica
2016-18 senza ritocchi, punteggio = t del P&L netto giornaliero. Le k regole ricevono 1/k contratto
ciascuna e pagano ognuna il costo (nessuna compensazione fra posizioni opposte: conservativo).

| statistica | reale | placebo «segno» (300): mediana [5 %; 95 %] | p |
|---|---|---|---|
| S1 miglior t netto in ricerca (su 106) | **−0,66** | +0,28 [−0,61; +1,55] | 0,96 |
| S3 t in verifica della vincitrice (hedge η 1, memoria infinita) | **−0,22** (−0,42 punti) | −0,55 [−2,21; +0,99] | 0,38 |
| S4 t medio in verifica delle 106 | −1,06 | −1,49 [−2,47; −0,29] | 0,26 |
| configurazioni con t > 1,645 in verifica | 0 | 0 [0; 4] | 1,00 |
| miglior regola FISSA in ricerca (r_on segui, 12:00 → chiusura): t ricerca | +1,60 | +1,15 [+0,49; +2,14] | 0,22 |
| la stessa in verifica | −1,36 | −0,46 [−1,97; +1,00] | 0,83 |
| t(meta) − t(fissa) in verifica | +1,14 | −0,00 [−2,13; +1,82] | 0,12 |

- **Tutte le 106 hanno t netto negativo già in ricerca.** La migliore in verifica (top-1 settimanale, L = 12,
  +1,83 punti, t 1,08) era −0,85 in ricerca: nessuna coerenza fra i due blocchi.
- Il filtro «solo regole con media > 0» non cambia quasi nulla: la migliore di 374 regole ha quasi sempre
  una media passata positiva (è selezione, non segnale).
- Le configurazioni con molte regole (k = 20, Hedge con η piccolo, regime) sono condannate per
  costruzione: il lordo medio di un paniere si annulla e il costo di 0,75 resta intero (t fino a −76).
  Per questo c'è la diagnostica lorda del §4.
- La meta-procedura batte la miglior regola fissa in verifica di 1,1 punti di t, ma è ciò che succede per
  caso (p 0,12): la regola fissa migliore in ricerca crolla in verifica, esattamente come nei giri 1 e 2.

**Controlli completi** sull'intera finestra 2011-07 → 2018-12 (`s05_controlli.py`):

| procedura | netto [CI 95 %] | p unil. | netto − beta (p) | anni + | senza i 20 migliori |
|---|---|---|---|---|---|
| vincitrice (hedge η 1) | −0,44 [−2,13; +1,23] | 0,70 | −0,44 (0,70) | 2/8 | −2,22 |
| canonica «momentum delle strategie» (mese, L 3, top-1) | −0,39 [−1,93; +1,16] | 0,70 | −0,40 (0,70) | 3/8 | −1,90 |
| miglior regola fissa della ricerca | −0,21 [−1,58; +1,16] | 0,63 | −0,20 (0,62) | 3/8 | −1,75 |

Beta medio per trade +0,002 / +0,011 / −0,015 punti: irrilevante (tutto RTH, lati misti).

## 4. C — c'è almeno un vantaggio LORDO di selezione? (`s03_lordo.py`, POST-HOC dichiarato)

Stesse 106 procedure, stessa scelta online, misurate sul lordo per contratto su 2011-07 → 2018:

| statistica | reale | placebo: mediana [q95] | p |
|---|---|---|---|
| t lordo medio delle 106 | +0,33 | +0,00 [+0,99] | 0,26 |
| miglior t lordo delle 106 | +1,69 | +1,84 [+2,78] | 0,61 |
| configurazioni con t lordo > 2 | 0 | 0 [13] | — |
| miglior t lordo in ricerca → sua verifica | +1,95 → −0,29 | +1,82 → −0,06 | 0,42 / 0,59 |

Le migliori al lordo sono top-k settimanali con L = 12 (+0,35…+0,97 punti lordi, t ≤ 1,7): sotto il costo
e dentro il caso. **Il meccanismo «scegli ciò che ha funzionato» non produce nemmeno un vantaggio lordo.**

## 5. D — cambiare famiglia (trend / mean-reversion) secondo chi ha vinto (`s04_famiglia.py`, POST-HOC)

Ogni mese si tiene la famiglia che ha vinto nelle 21·L sessioni precedenti; lordo medio giornaliero:
L = 3 +0,17 (p 0,09), **L = 6 +0,24 [+0,05; +0,43], p 0,017** (placebo p 0,018, 6/8 anni, senza i 20
migliori +0,004), L = 12 +0,16 (p 0,11). Ma la famiglia **trend statica**, tenuta sempre, fa +0,18 lordi
(p bil. 0,065; 2016 −0,50) e lo switch sceglie «trend» nel 61-69 % dei mesi: **quasi tutto lo switch è la
famiglia trend statica**, e tutto è a un quarto del costo. Una cella su tre con p < 0,05, scelta dopo aver
visto s01: compatibile con il caso.

## 6. F-G — persistenza a scale brevi (`s06_scale_brevi.py`, `s07_w10.py`, estensione dichiarata dopo s01)

IC fra blocchi non sovrapposti, nullo «segno per giorno» (300):

| passato → futuro (sessioni) | IC | placebo q95 | p |
|---|---|---|---|
| 1 → 1 | +0,002 | +0,007 | 0,35 |
| 5 → 5 | +0,015 | +0,014 | 0,027 |
| **10 → 10** | **+0,037** | +0,020 | **0,000 (0/300)** |
| 63 → 5 | +0,009 | +0,012 | 0,13 |

L'unico segnale netto del lavoro. Cosa è (diagnostica POST-HOC):
- **Non è una differenza statica fra regole**: togliendo a ogni regola la sua media dell'intero periodo
  l'IC resta +0,037. È positivo in 7/8 anni (2015 −0,04), in ricerca +0,030 e in verifica +0,049.
- **Vive nelle regole con segnali di più giorni** (gap, notte, ieri, 5 giorni, pos_20d, pos_night, long):
  IC +0,050, p 0,000. Nelle regole con segnali **intraday** (r15, r60, r_open, pos_today) è +0,018, **p 0,16**:
  nessuna persistenza. Quindi non è «il mercato alterna regimi intraday trend/MR», ma, con ogni
  probabilità, struttura a più giorni della direzione dell'indice (parente del TSMOM già bocciato nel giro 1).
- **Non vale punti**: operando ogni 10 sessioni le k regole migliori delle 10 precedenti, lordo +0,59 (k 1),
  +0,50 (k 5), +0,28 (k 20), nessuno significativo (p 0,15-0,24; placebo p 0,16-0,20), netto −0,16…−0,47;
  long-short top20 − bottom20 +0,55 lordi [−0,50; +1,61], p 0,31 (2015 −2,49).
- È stato trovato dopo il piano, alla terza scala provata: per la regola pre-registrata **non** è un candidato.
  Se il controller vuole una regolarità da pre-registrare per un giro successivo, è questa: «IC di Spearman
  10 → 10 sessioni fra regole con segnali di più giorni > 0», con la stessa libreria.

## 7. Candidati

**Nessuno** (`candidates.py`: `CANDIDATES = []`). Regola di decisione del piano:
- tradeable: la vincitrice della ricerca ha t −0,22 in verifica e p(S3) = 0,38 → no;
- regolarità: la persistenza mensile (L = 3) ha p 0,10 sul nullo «segno per giorno» → no.

## 8. Cosa se ne impara

1. **La non-stazionarietà dei giri 1-2 non è sfruttabile scegliendo in modo adattivo.** Se l'identità della
   regola buona persistesse per mesi, scegliere online batterebbe le regole fisse: non succede. La regola
   che «funziona» in un mese è, alla scala mensile, quasi indipendente da quella del mese dopo (IC +0,02,
   dentro il caso).
2. Selezionare fra 374 regole su finestre corte **aggiunge rumore** (S1 reale −0,66 contro +0,28 del
   placebo): la selezione insegue il rumore e paga costi pieni.
3. Il nullo «libreria a lato casuale» è **ingannevole** (dà p = 0 a tutto): con regole correlate serve un
   nullo che conservi la correlazione (segno per giorno). Nota metodologica per chiunque misuri IC fra
   strategie.
4. La sola persistenza reale trovata (10 sessioni) è persistenza della direzione dell'indice su più giorni
   vista attraverso le regole, non dei regimi intraday, e vale meno del costo.

## 9. Registro e file

`lab/ledger/r3_adaptive.jsonl`: **255 righe** = 1 piano + 20 statistiche di persistenza (A) + 106
meta-procedure nette + 1 riepilogo della pipeline (B) + 106 lorde + 1 riepilogo lordo (C) + 3 switch di
famiglia + 1 famiglia statica (D) + 3 controlli completi (E) + 4 scale brevi (F) + 9 diagnostiche della
persistenza a 10 sessioni (G). Placebo: 700 (A), 300 pipeline intere × 106 configurazioni (B) e (C),
1.500 (D), 1.200 (F), ~1.100 (G).

- `s00_piano.py` piano; `common.py` libreria, motore top-k / Hedge / regime (tutto causale);
- `s01_persistenza.py` A; `s02_meta.py` B; `s03_lordo.py` C; `s04_famiglia.py` D; `s05_controlli.py` E;
  `s06_scale_brevi.py` F; `s07_w10.py` G (due gruppi di righe, `D_follow_static` e `G_ic10_sub_*`, registrati
  da comandi in linea con lo stesso codice);
- `test_candidates.py` test di riproduzione (`.venv/Scripts/python.exe -m lab.r3_adaptive.test_candidates`:
  IC L3 0,0219, S1 −0,66, S3 −0,22, IC 10 → 10 0,0371 — eseguito, ok);
- `cache/`: `meta_real.csv`, `meta_placebo.csv`, `meta_gross_*.csv`, `persist_placebo.csv`, ATR20.
- Correzione prima di guardare i risultati: il variance ratio in `common.regime_stats` era diviso per 12 due
  volte (mediana 0,08 invece di ~1): corretto prima di qualunque test.
- `core.py`: nessun bug trovato. Il pannello è quello in cache di `r2_autosearch` (sola lettura).
