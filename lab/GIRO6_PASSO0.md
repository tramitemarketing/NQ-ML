# Giro 6 — risposte al Passo 0 (2026-09-30, solo discovery, nessun esito guardato)

Script: `lab/r6_*/s00_passo0.py`. Pre-registrazione: `lab/PROTOCOLLO.md` §19 e `lab/r6_*/PREREG.md` (`b487951`).

## Blocco 0
- **Orari.** Le barre Databento sono in UTC, etichettate con l'inizio del minuto. Vengono convertite una
  volta sola in America/New_York con DST (`core._build_cache`).
- **Sessioni.** Una sessione va dalle 18:00 del giorno prima. RTH 09:30-16:00. Mezze giornate e giorni
  incompleti sono esclusi da `valid` (almeno 300 barre RTH).
- **Roll.** Le date vengono dalla simbologia Databento; il cambio avviene alle 00:00 UTC, dentro la notte.
  Aggiustamento all'indietro additivo (`adj_*`). Un rendimento RTH non attraversa mai un roll.
- **ATR20** come nel §19: range RTH delle 20 sessioni valide precedenti.
- **Metà del discovery**: 2010-06-07 → 2014-12-31 e 2015-01-01 → 2018-12-31.

## r6_gamma
1. File SqueezeMetrics `DIX.csv`, scaricato il 2026-09-30 alle 13:01 UTC.
   - Colonne: `date, price, dix, gex`. Righe dal 2011-05-02 al 2026-09-29.
   - sha256 `2a3ae669…2748385a`.
   - Le date dalla cassaforte in poi vengono scartate in `lab/extdata.py` alla lettura.
   - Unità del GEX: dollari (convenzione del fornitore). Nel discovery va da −2,6e9 a 9,0e9, mediana 2,1e9.
2. La documentazione pubblica del fornitore non dice a che ora viene calcolato il GEX. La riga contiene la
   chiusura dell'S&P del giorno d, quindi è calcolata dopo la chiusura di d. Si usa per la sessione
   successiva, come stabilito nel PREREG.
3. **Il GEX negativo è raro nel discovery.** Quota di giorni con GEX < 0:

   | anno | 2011 | 2012 | 2013 | 2014 | 2015 | 2016 | 2017 | 2018 |
   |---|---|---|---|---|---|---|---|---|
   | GEX < 0 | 17,6 % | 5,2 % | 0,8 % | 2,0 % | 9,1 % | 8,7 % | 0,8 % | 15,5 % |

   In tutto sono circa 145 giorni: circa 50 nella prima metà e circa 86 nella seconda. Il test A
   (indicatore) ha poca potenza e il test B (rango) porta quasi tutta l'informazione. Non propongo modifiche.
4. VXN: nessuna sessione valida senza valore. Un solo caso di ritardo sopra i 4 giorni (2012).
5. L'autocorrelazione media RTH è negativa ogni anno: a 1 minuto da −0,015 a −0,058, a 5 minuti da
   −0,011 a −0,051. È incondizionata e non dice nulla sul GEX.

## r6_community
1. Copertura 00:00-09:29 ET: dall'89 % (2010) al 99,8 % (2018) dei minuti. I minuti senza barra sono
   minuti senza scambi e contano come prezzo fermo.
2. 0,25σ in punti, mediana per anno: da 1,8 (2010) a 11,6 (2018). Le definizioni di nqstats potrebbero
   essere diverse.
3. **Il placebo del documento (rimescolamento semplice fra giorni) non conserva le code.**

   | | reale | semplice | scalato |
   |---|---|---|---|
   | curtosi del rendimento RTH giornaliero | 6,37 | 1,69 | 8,31 |
   | autocorrelazione del rendimento giornaliero in valore assoluto | 0,26 | 0,10 | 0,24 |
   | SD del rendimento RTH giornaliero (bps) | 44,7 | 42,1 | 42,9 |

   Il profilo di volatilità per minuto si conserva in entrambi. Con il rimescolamento semplice ogni
   giornata diventa «media» e il σ dei 20 giorni precedenti perde il legame con la giornata, quindi le
   probabilità di tocco del placebo sarebbero distorte. La versione **scalata** conserva livello di
   volatilità del giorno e code, e toglie la memoria: ogni giornata viene divisa per la sua volatilità
   realizzata, rimescolata minuto per minuto fra i giorni dello stesso anno, poi rimoltiplicata. Le
   sessioni si concatenano dentro l'anno, quindi il test D (settimana) funziona. **Proposta, decide
   l'utente: usare la versione scalata come placebo primario, con la semplice come descrittivo.**
4. Regola di fill: confermata come nel PREREG.

## r6_noise
1. La barra delle 09:30 e quella delle 15:59 ci sono nel 100 % delle sessioni valide. Mancano in media
   0,01 barre RTH a sessione. Nessuna barra RTH ha volume 0, quindi il VWAP si può calcolare.
2. Le bande usano solo le 14 sessioni valide precedenti. 2107 sessioni su 2121 hanno i 14 giorni di storia.
3. Esecuzione: confermata come nel PREREG.
4. Famiglie chiuse che si possono ricostruire dal codice esistente:
   - ORB15: `nqml/screen/orb.py`;
   - prima ora: `nqml/screen/firsthour.py`;
   - candidato 4: `nqml/screen/vabreak.py`;
   - rottura delle bande di volatilità: `lab/r2_range/candidates.py`.

   Le prime tre hanno 8 geometrie ciascuna. **Proposta: la correlazione deve stare sotto 0,5 con ognuna
   delle geometrie** (lettura severa del criterio).

## r6_silverbullet
1. Copertura Globex 02:30-03:59 ET: dal 92 al 100 % per anno. Si tengono tutte e tre le finestre.
2. Conteggi nel discovery (nessun esito):

   | finestra | sweep | FVG | stop dalla parte sbagliata | rischio oltre il tetto | ordini | fill al tocco | fill con 1 tick |
   |---|---|---|---|---|---|---|---|
   | 03-04 | 1720 | 967 | 134 | 89 | 744 | 504 | 464 |
   | 10-11 | 2000 | 1258 | 273 | 610 | 375 | 234 | 221 |
   | 14-15 | 1630 | 801 | 141 | 212 | 448 | 300 | 279 |

   In totale ci sono **964 trade**, circa 110 l'anno. Rischio mediano 3,25 punti (dal 10° al 90° percentile:
   da 1,25 a 7,5).
3. Differenze dal repo da dichiarare:
   - Il tetto del rischio scalato col prezzo (60·P/30.400, cioè circa 4 punti nel 2010) scarta metà dei
     setup delle 10-11. È la conseguenza della regola fissata nel documento.
   - Il fill con attraversamento di 1 tick toglie circa il 7 % dei fill rispetto al tocco.
   - Il prezzo di esecuzione è sempre il limite.
   - Il repo controlla stop e target dalla barra a 5 minuti del fill in poi. Qui si parte dal minuto del fill.
   - Il lookback di 24 barre, come nel repo, conta barre e non tempo. Le barre a 5 minuti mancanti sono rare.
   - Il primo giro dello script aveva un errore di conteggio sulle due colonne «stop dalla parte sbagliata»
     e «rischio oltre il tetto». La riga del registro con quei numeri è sbagliata ed è sostituita dalla
     successiva.

## Decisioni che spettano all'utente, prima di «approvato»
1. Placebo di r6_community: versione scalata come primaria (proposta) oppure quella semplice del documento.
2. r6_noise: correlazione < 0,5 con tutte le geometrie delle famiglie chiuse (proposta).
Le scelte vanno scritte come addendum ai PREREG e committate prima di qualunque test primario.
