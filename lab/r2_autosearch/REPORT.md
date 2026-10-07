# Famiglia «r2_autosearch»: la macchina inventa le regole, il placebo tiene la contabilità

Fase: **solo discovery** (2010-06-07 → 2018-12-31, 2.121 sessioni valide). Unità dichiarata prima di
guardare: **punti NQ netti per 1 contratto**, costo 0,75 punti sempre, ingresso all'open della barra
dopo il segnale. Piano pre-registrato in `s00_piano.py` (registrato nel ledger come prima riga, prima di
qualunque risultato).

**Risultato in una riga: su 480.181 regole valutate, il miglior risultato reale non si distingue dal
miglior risultato ottenuto su dati placebo, né in ricerca né in selezione. Zero candidati.**

---

## 1. Grammatica (cosa cerca la macchina)

- **13 istanti di decisione** in RTH: 09:45, 10:00, 10:30, …, 15:30. Le feature usano solo barre chiuse
  prima dell'istante; ingresso all'open della barra successiva.
- **5 orizzonti**: 15, 30, 60, 120 minuti, fino alla chiusura (15:59). Tutto dentro l'RTH: niente notte,
  niente roll, deriva/beta trascurabile (lezione del giro 1).
- **23 feature causali** (normalizzate con il range RTH medio delle 20 sessioni precedenti): rendimenti a
  5/15/60 minuti e dall'apertura, gap, notte, ieri, 5 giorni; sorpresa di volatilità realizzata (oggi e
  ultimi 60 minuti contro la media delle 20 sessioni precedenti allo stesso minuto); volume relativo per
  ora (cumulato e ultimi 60 minuti); posizione nel range di oggi / ieri / notte / 20 giorni; distanza dal
  massimo e dal minimo di oggi; range di oggi e della notte relativi; regime di volatilità (ATR20/ATR250);
  minuti dall'ultimo massimo e dall'ultimo minimo. Più il giorno della settimana.
- **Soglie a quantili causali**: rango percentile rispetto alla stessa feature allo stesso istante nelle
  250 sessioni precedenti; condizioni ≤ 0,10 / ≤ 0,25 / ≤ 0,50 / > 0,50 / ≥ 0,75 / ≥ 0,90 → 143 condizioni.
- **Regole**: AND di 1 o 2 condizioni su feature diverse (enumerazione completa), 3 condizioni con beam
  search (le 10 migliori coppie di ogni cella istante × orizzonte × lato estese con ogni terza condizione).
  Lato long o short. Minimo 100 trade nel periodo di ricerca.
- **Totale: 480.181 regole valutate** nella ricerca reale (116 lotti = celle; nel registro una riga per
  lotto con numero di regole, miglior t e quantili della distribuzione dei t). Nota: a 09:45 due coppie di
  feature coincidono (rv_sur = rv60_sur, r60 = r_open, perché la sessione ha meno di 60 minuti): il numero
  di regole *distinte* è leggermente più basso.

Il calcolo è a matrici (somme condizionate = Mᵀ·diag(y)·M): una pipeline intera gira in ~0,5 secondi, e
questo rende possibile ripeterla centinaia di volte sui placebo.

## 2. Disciplina

1. **Ricerca** su 2010-06 → 2015-12: punteggio = t della media netta.
2. **Portafoglio congelato**: le 2 migliori regole per cella, poi le 100 migliori in assoluto (TOP100).
3. **Selezione** su 2016-2018, senza ritoccare nulla: «sopravvive» chi ha media netta > 0 e t > 1,645.
4. **Placebo**: l'intera pipeline (ricerca + TOP100 + selezione) rifatta da capo su
   - **nullo principale «segno per giorno»** (500 repliche): ogni sessione riceve un segno ±1 casuale che
     moltiplica tutti i suoi rendimenti futuri. Conserva il legame feature → ampiezza del movimento (la
     volatilità è prevedibile, e con un costo fisso in punti questo conta) e la struttura dentro la
     giornata; distrugge solo la direzione.
   - **nullo secondario «blocchi di giorni»** (200 repliche): i rendimenti futuri delle sessioni sono
     permutati a blocchi di 20 sessioni (separatamente in ricerca e selezione). Conserva la deriva ma rompe
     il legame volatilità → ampiezza (dichiarato più debole prima di guardare).
5. **p corretto per la ricerca** = quota di placebo con statistica ≥ reale (stile Reality Check di White:
   si confronta il massimo reale con la distribuzione dei massimi placebo).

Regola di decisione fissata nel piano: si consegnano candidati **solo se** p(S2) < 0,05 oppure p(S3) < 0,05
sul nullo principale.

## 3. Reale contro placebo (il risultato)

| statistica della pipeline | reale | placebo «segno»: mediana [5 %; 95 %] | p | placebo «blocchi»: mediana [95 %] | p |
|---|---|---|---|---|---|
| S1 miglior t in ricerca (su ~480 mila regole) | **4,18** | 4,01 [3,58; 4,71] (max 5,65) | **0,31** | 4,04 [4,87] | 0,36 |
| S2 sopravvissuti del TOP100 in selezione | **1** | 2 [0; 8] | **0,87** | 2 [7] | 0,83 |
| S3 miglior t in selezione nel TOP100 | **2,13** | 2,10 [1,39; 2,92] | **0,46** | 2,06 [3,02] | 0,45 |
| S4 t medio in selezione del TOP100 | −0,20 | −0,27 [−0,61; +0,05] | 0,37 | −0,28 [+0,05] | 0,36 |
| S5 regole con t > 3 in ricerca | 420 | 136 [40; 574] | 0,09 | 117 [371] | 0,03 |
| regole «forti» in selezione (t > 3,29) | 0 | — | — | — | — |

Lettura:
- **Il miglior t del mondo reale (4,18) è esattamente quello che mezzo milione di regole produce sul
  rumore** (mediana placebo 4,01; nel 31 % dei placebo il migliore è più alto). Un «t = 4» trovato da una
  ricerca così vale un p corretto di 0,31.
- **La selezione fuori campione non fa meglio del caso**: il TOP100 reale ha t medio −0,20 nel
  2016-2018 (placebo −0,27), 1 sopravvissuto (placebo: 2 in mediana), miglior t 2,13 (placebo 2,10).
  La prima regola della ricerca (t 4,18) fa −1,48 punti netti a trade nella selezione.
- **Unico segnale di struttura: S5**, cioè *quante* regole superano t = 3 in ricerca (420 contro 117-136
  in mediana; p 0,09 / 0,03). Diagnostica **post-hoc** (`s03_diag.py`, dichiarata tale, non cambia la
  decisione): le 65 regole singole/coppie reali con t > 3 (placebo: mediana 11-16, p 0,03-0,09) sono
  concentrate nelle celle **long dal mattino alla chiusura** (09:45 → chiusura: 17; 09:45 → +120: 9;
  11:00 → chiusura: 5; …), cioè varianti della stessa cosa: «nei giorni calmi del 2010-2015 la sessione
  sale». Ma in selezione non reggono meglio del caso: t medio +0,13 (placebo −0,17 / −0,27, p 0,21-0,24),
  quota con t > 1,645 del 3 % (p 0,24). È una regolarità del periodo di ricerca (deriva dei giorni calmi,
  parente dell'effetto leva), non una strategia; la long incondizionata 09:45 → chiusura fa −0,83 netti sul
  discovery, 3/9 anni positivi.

**Conclusione: in questa classe di regole (AND di 1-3 condizioni a quantili su 23 feature causali, 13
istanti, 5 orizzonti, lato libero, al netto di 0,75 punti) il data-mining da solo spiega tutto quello che
si trova. Lo spazio delle regole semplici intraday su NQ, a questi costi, appare vuoto** — o con effetti
troppo piccoli per emergere da una ricerca di questa ampiezza. È coerente con il giro 1 (nessun tradeable
sopravvissuto) ed è una misura più forte: non 150 idee scelte a mano, ma mezzo milione di regole con il
loro costo di ricerca contabilizzato.

## 4. Trasparenza: le regole guardate da vicino (`s04_look.py`)

| regola | n | netto medio (discovery) [CI 95 %] | p unil. | anni + | senza 20 migliori | ricerca → selezione |
|---|---|---|---|---|---|---|
| n.1 della ricerca: 11:00, long fino alla chiusura se r_5d ≤ 0,50 & vol60_rel ≤ 0,50 & pos_today ≤ 0,50 | 192 | +3,59 [−2,39; +9,69] | 0,12 | 7/9 | −3,63 | +6,18 → **−1,48** |
| unica sopravvissuta: 11:30, long 120 min se r60 > 0,50 & gap > 0,50 & pos_night ≥ 0,75 | 257 | +2,46 [+1,04; +3,83] | 0,0002 | 9/9 | +0,72 | +1,90 → +3,43 (t 2,13, n 94) |
| long incondizionata 09:45 → chiusura (riferimento) | 2.121 | −0,83 [−2,42; +0,73] | 0,85 | 3/9 | −2,10 | −0,50 → −1,46 |

La sopravvissuta **non è un candidato**, per la regola pre-registrata: la pipeline nel suo insieme non
batte il caso (p(S2) = 0,87, p(S3) = 0,46), e un t di selezione di 2,13 è la *mediana* di ciò che il
TOP100 produce sul rumore. I suoi numeri sull'intero discovery sono gonfiati perché 2/3 delle sessioni sono
quelle in cui è stata scelta (il p 0,0002 non ha significato dopo 480 mila tentativi). È inoltre momentum
della mattina (apertura sopra ieri + ultima ora forte + prezzo in alto nel range notturno → continua a
mezzogiorno), territorio già esplorato e bocciato nel giro 1. Promuoverla vorrebbe dire proprio ciò che
questa famiglia esiste per impedire: scegliere col senno di poi il vincitore di una lotteria di 100
biglietti.

## 5. Candidati

**Nessuno** (`candidates.py`: `CANDIDATES = []`). Motivo: regola di decisione del piano (p(S2) = 0,874,
p(S3) = 0,462, entrambi ≥ 0,05).

## 6. Registro e file

`lab/ledger/r2_autosearch.jsonl`: **224 righe** = 1 piano + 116 lotti di ricerca (aggregati: 480.181 regole
reali) + 100 valutazioni in selezione del TOP100 + 1 riepilogo reale + 2 riepiloghi placebo + 1 diagnostica
post-hoc + 3 sguardi di trasparenza. Regole valutate in totale, placebo compresi: ~480 mila × (1 reale +
700 placebo) ≈ **3,4 × 10⁸**, più 400 placebo della diagnostica (solo singole e coppie).

Nota di processo: la prima esecuzione di `s01_autosearch.py` si è interrotta per un errore di nome di
argomento in `core.record` DOPO aver registrato lotti e selezione e salvato i CSV dei placebo; il bug è
corretto in `s01` e le righe di riepilogo sono state scritte da `s02_summary.py` (pipeline reale
deterministica ricalcolata, placebo letti dai CSV: niente ripetuto o scelto).

- `s00_piano.py` piano pre-registrato; `common.py` feature, ranghi causali, rendimenti;
- `s01_autosearch.py` ricerca + selezione + 700 placebo; `s02_summary.py` confronto reale/placebo;
- `s03_diag.py` diagnostica post-hoc delle regole con t > 3; `s04_look.py` controlli completi di 3 regole;
- `test_candidates.py` test di riproduzione (`.venv/Scripts/python.exe -m lab.r2_autosearch.test_candidates`);
- `cache/`: pannello, `real_top100.csv`, `real_lots.csv`, `placebo_sign.csv`, `placebo_block.csv`,
  `diag_placebo.csv`.
- `core.py`: nessun bug trovato.
