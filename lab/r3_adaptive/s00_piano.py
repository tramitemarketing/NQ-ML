"""r3_adaptive — PIANO PRE-REGISTRATO (scritto e registrato prima di guardare qualunque risultato).

DOMANDA: c'e' persistenza in QUALE regola semplice funziona? Se si', una meta-procedura che sceglie
online fra molte regole in base alla performance recente dovrebbe battere le regole fisse.

UNITA' (fissata ora): punti NQ per 1 contratto; netto = lordo - 0,75 per trade. Tutto in RTH.

LIBRERIA (fissata ora, N regole, ogni regola al massimo 1 trade al giorno)
- Istanti T: 10:00, 11:00, 12:00, 13:00, 14:00, 15:00 (6). Ingresso all'open della barra T.
- Orizzonti: 30, 60 minuti, fino alla chiusura 16:00 (3). (15:00+60 coincide con la chiusura: regola
  non esistente, eliminata.)
- Segnali (lato = segno della feature causale di lab/r2_autosearch/common.py): r15, r60, r_open, gap,
  r_on (notte), r_prev (ieri), r_5d; pos_today, pos_night, pos_20d (segno di pos - 0,5); 'long' (+1).
- Direzione: segui (follow) o contro (fade = specchio). N = 6 x 3 x 11 x 2 - regole inesistenti.
- Lato 0 o feature mancante -> nessun trade quel giorno (netto 0).

A. REGOLARITA' DI PERSISTENZA (misura prima di tutto)
- Per ogni mese m: punteggio passato = lordo medio giornaliero della regola nelle 21*L sessioni prima
  del mese; futuro = lordo medio giornaliero nel mese m. IC_m = correlazione di Spearman fra le N regole.
- Statistica: media di IC_m sui mesi del discovery con lookback completo. L principale = 3 (1, 6, 12
  sensibilita'). Anche la versione solo-follow (senza specchi) come sensibilita'.
- Nulli: (i) 'segno per giorno' (come r2_autosearch): ogni sessione riceve un segno +-1 casuale che
  moltiplica tutti i rendimenti futuri, feature intatte (500 repliche); (ii) 'libreria a lato casuale':
  il lato di ogni regola ogni giorno e' un +-1 casuale (200 repliche). p unilaterale = quota di placebo
  con IC medio >= reale. Persistenza dichiarata solo se p < 0,05 su ENTRAMBI i nulli con L = 3.
- Lo stesso per la persistenza a livello di famiglia (trend = media delle follow, MR = media delle fade):
  lo spread D = follow - fade del mese passato predice quello del mese dopo? (correlazione mensile).

B. META-PROCEDURE (griglia fissata ora, 106 configurazioni)
- TOP-K (96): frequenza di ribilanciamento {mese, settimana} x L {1, 3, 6, 12 mesi = 21L sessioni} x
  k {1, 5, 20} x punteggio {media netta, t netto} x filtro {nessuno, solo regole con media netta > 0}.
  Nel periodo si operano le k regole scelte con 1/k contratto ciascuna (ogni regola paga il suo costo;
  nessuna compensazione fra regole: conservativo). P&L giornaliero = media dei netti delle regole scelte
  che quel giorno tradano.
- HEDGE (6): pesi ~ exp(eta * somma dei netti passati in unita' di ATR20) aggiornati ogni giorno,
  eta {0,05, 0,2, 1,0} x memoria {infinita, emivita 63 sessioni}.
- REGIME (4): ogni giorno si opera l'intera famiglia trend (tutte le follow) oppure MR (tutte le fade)
  secondo una statistica causale delle 20 sessioni precedenti sopra/sotto la sua mediana causale delle
  250 sessioni precedenti: autocorrelazione lag-1 dei rendimenti di 30 minuti (sopra -> trend), variance
  ratio 6h/30m (sopra -> trend), efficiency ratio (sopra -> trend), spread D medio delle 20 sessioni (>0 -> trend).
- Finestra comune di confronto: ricerca 2011-07-01 -> 2015-12-31 (tutte le configurazioni attive),
  verifica 2016-01-01 -> 2018-12-31 senza ritocchi.
- Punteggio = t del P&L netto giornaliero (giorni con almeno un trade).
- Statistiche: S1 = max t in ricerca; S3 = t in verifica della vincitrice; S4 = t medio in verifica di
  tutte le 106; benchmark: miglior regola FISSA della libreria in ricerca -> suo t in verifica.
- Placebo 'segno per giorno' dell'intera pipeline (300 repliche) -> p corretti.

REGOLA DI DECISIONE (fissata ora)
- Candidato tradeable solo se: la vincitrice ha media netta > 0 e t > 1,645 in verifica 2016-18 E
  p(S3) < 0,05 sul placebo. Poi controlli completi sull'intero discovery (beta, anni, senza i 20
  migliori, placebo). Il candidato e' la META-procedura intera, ricostruita online dal solo passato.
- Candidato regolarita' solo se la persistenza (A) passa su entrambi i nulli.
- Massimo 2 candidati. Altrimenti zero: 'la persistenza delle strategie non esiste' e' il risultato.
"""
from lab import core

if __name__ == "__main__":
    core.record("r3_adaptive", "piano", "piano pre-registrato (vedi s00_piano.py)", "discovery",
                {"n": 0}, note="nessun dato guardato")
    print("piano registrato")
