# Famiglia cross_session: come si parlano le sessioni

(Testo prodotto dall'agente della famiglia; salvato dal controller perché la scrittura dell'agente era stata bloccata.)

Solo discovery (2010-06-07 → 2018-12-31). Registro: `lab/ledger/cross_session.jsonl`, **123 righe**
(una è un doppione: 122 test effettivi).

## Verdetto
**Nessuna regola direzionale fra sessioni regge nel discovery.** Su 117 test direzionali o di livello,
uno solo ha EV netto con p unilaterale < 0,05, contro circa 6 attesi per caso. 24 hanno il lordo con p
bilaterale < 0,05, correlati e tutti sotto i costi. Le sessioni **si parlano in volatilità, non in
direzione**. Consegna: **0 candidati tradeable, 2 regolarità**.

## Convenzioni dichiarate prima di guardare
- Unità primaria: punti per 1 contratto; ogni test riporta anche la versione in ATR20.
- Segmenti: Asia 18:00-02:00, Europa 02:00-08:30, pre-apertura 08:30-09:30, RTH 09:30-16:00, sera 16:00-17:00.
- Prezzi solo `adj_*` (il roll cade alle 00:00 UTC, dentro l'Asia). Segnale = close dell'ultima barra
  prima del confine; esecuzione = open della prima barra dopo.
- Soglie di «movimento grande» solo causali (quantili sulle 250 sessioni precedenti).
- Slippage notturno: 1 tick a lato è ottimista per Asia/Europa e riapertura domenicale.

## Nota su core.py (non modificato)
1. Aggiustamento additivo: i rendimenti % su `adj_*` sono falsati di ~3× negli anni iniziali.
2. Fra il 2010 e il 2015 NQ scambiava fino alle 17:15: le barre 17:00-17:15 finiscono nella sessione
   *successiva*, e in quegli anni `daily.glbx_open` è il prezzo delle 17:00.
3. La pausa 16:15-16:30 c'è in tutto il discovery; CME l'ha tolta nel 2021.

## Idee provate (sintesi, punti lordi)
- **Segno di un segmento → successivo (20 test)**: Asia → Europa −0,76 (p 0,035); Londra 03:00-03:30 →
  resto −0,64 (p 0,047); 08:30-08:45 → 08:45-09:30 −0,16; Asia → RTH +1,32 (p 0,14); il resto rumore.
- **Stesse coppie con movimento grande (20 test)**: pre-apertura grande → 09:30-10:30 −1,79 (p 0,033);
  02:00-03:00 → Londra +1,02 (isolato); ultima ora → 16-17 +1,00 (p 0,025).
- **Range, posizione, calendario, volume (22 test)**: range notturno → range RTH +0,147 p 0,0001 9/9
  (candidato 1); notte del lunedì → RTH +3,57 (p 0,065); NFP niente; utili sera → Asia incoerente.
- **Livelli (8 test)**: massimo/minimo notturni non sono livelli (né fade né rottura); rottura del range
  asiatico non prosegue.
- **Gao et al.**: +0,23 (p 0,34), assente su NQ.
- **Trasmissione di volatilità (6 test)**: tutte le direzioni p ≈ 0,0001, 9/9 anni.
- **Ridge con tutti i segmenti**: RTH −0,41; Asia successiva +1,04 ma beta-corretto +0,08.
- **Weekend (9 test)**: segno del venerdì → Asia del lunedì +1,84, ma tutto nelle prime 2 ore dopo la
  riapertura sottile; negativo 2010-2013; placebo sulle altre notti zero. Scartato.
- **Fine RTH → sera (16 test)**: 16:30-17:00 prosegue il segno della RTH (+0,32, p 0,005; ATR 0,0002);
  placebo casuale +0,04. Candidato 2, post hoc.
- **Fade della pre-apertura (12 test)**: lordo positivo in 12/12 varianti, netto significativo solo a
  q90 (p_pos 0,048, n 199), senza i 20 migliori sempre negativo. Non promosso.

## Candidati — entrambi `regularity`, test bilaterale sul lordo
1. `cross_session_onrange_rthrange`: side = +1 se il range notturno normalizzato supera la sua mediana
   causale, altrimenti −1; quantità = side × (range RTH / media RTH 20 − 1). n 2.053, **+0,1469
   [+0,1253; +0,1685]**, p 0,0001, 9/9 anni. Warmup 280.
2. `cross_session_rth_to_evening`: side = segno(RTH); quantità = side × (close 16:59 − open della prima
   barra dalle 16:15). n 1.988, **lordo +0,321 [+0,093; +0,546]**, p 0,0056, 7/9 anni. Netto −0,43:
   non incassabile. Post hoc fra 16 varianti.
