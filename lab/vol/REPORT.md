# Famiglia `vol` — rapporto di discovery (2010-06-07 → 2018-12-31)

(Testo prodotto dall'agente della famiglia; salvato dal controller perché la scrittura dell'agente era stata bloccata.)

**Test registrati: 114** (`lab/ledger/vol.jsonl`): 43 binario A (regolarità, di cui 4 di robustezza), 71 binario B. Solo discovery.
**Verdetto:** A dà fatti netti e stabili (tre congelati); B non dà nulla: nessuna strategia condizionata alla volatilità regge beta e robustezza. **Candidati tradeable: zero.**

## Convenzioni dichiarate prima di guardare
- Regolarità: RV RTH = somma dei 78 rendimenti log 5m² (prezzi grezzi, %), in log; previsioni solo con dati ≤ t−1; HAR = OLS mobile sulle 500 sessioni precedenti.
- Strategie: punti per contratto, costi 0,75; diagnostica in ATR20.
- Regime (B): HAR a pesi fissi (logRV_{t−1}+media5+media22)/3, percentile causale su 250 sessioni, terzili.

## Binario A (43 test)
| id | quantità | segno atteso | media [CI 95 %] | anni |
|---|---|---|---|---|
| A1 | err² media22 − err² HAR (log RV) | + | +0,182 [+0,155; +0,211]; R² HAR 0,624, media22 0,401, RW 0,546, media250 0,070 | 8/8 |
| A1b/A1c | HAR vs RW / vs media250 | + | +0,064 / +0,454 | — |
| A2 | + log range overnight a HAR | + | +0,023 [+0,014; +0,033] (R² 0,652) | 8/8 |
| A2b | range RTH dal range notturno | + | +0,020 (R² 0,408→0,475) | — |
| A3 | residuo HAR × −segno(c-c ieri) | + | +0,064 [+0,039; +0,089] | 7/8 |
| A3b | HAR asimmetrico, guadagno MSE | + | +0,021 [+0,011; +0,032] | 8/8 |
| A3c/d | residuo dopo < −1 % / > +1 % | +/− | +0,277 / −0,097 | — |
| A4a/b | profilo a U: apertura / chiusura vs 12-14 | + | +0,724 (≈2,06×) / +0,244 (≈1,28×) | — |
| A5 | leva intraday 30m | + | +0,054 [+0,041; +0,066] | — |
| A6a/b/c | vol dopo shock 5m | + | +0,61 / +0,59 / +0,034 [+0,025; +0,045] | 9/9 |
| A7/A7b | range²/RV − 4ln2 | − dichiarato | +0,094 / +0,359: **segno opposto, previsione sbagliata** | — |
| A8 | VR 30m/5m giornaliero | − | −0,025 [−0,042; −0,008] | 7/9 |
| A8_h | VR 60m/5m per ora | − | 9:30 +0,045 · 10:30 +0,008 · 11:30 −0,037 · 12:30 −0,131 · 13:30 −0,155 · 14:30 −0,112 · 15:30 −0,050 | — |
| A8m | VR 12:30-15:30 (post hoc) | − | −0,117 [−0,145; −0,088] | 8/9 |
| A9 | residuo HAR per giorno | n.d. | lun −0,055, mar +0,079, mer +0,109, gio +0,019, ven −0,109 | — |
| A12 | compressione → RV 5 giorni dopo / RV5 | + | +0,198 | — |
| A13/A14 | volume ieri / \|gap\| oltre HAR | + | ≈0 (nulli) | — |

Robustezza: VR mezzogiorno su base 15m −0,064 [−0,090; −0,039]; finestra 12:00-15:00 −0,105; HAR vs
media22 in QLIKE +0,157, 8/8. Dopo un giorno in calo la varianza è ~+9 % sulla previsione, dopo un
rialzo ~−5 %.

## Binario B (71 test, netti in punti)
IB60 breakout/fade per regime, segui la prima ora, compressione → rottura, NR7, long dopo shock,
reversal per regime, Gao per regime, fade di mezzogiorno (la regolarità A8 vale ~0,2 punti lordi, sotto
il costo), long RTH per regime (non monotono), gap fade, direzione overnight, ultima ora nel verso del
giorno (5/9 anni, top-20 −0,79), long notte (beta), long notte dopo shock (+2,84 netto ma
beta-corretto +0,87 [−2,4; +3,6], concentrato nel 2018), IB stretta. **9/71 con p < 0,05 (≈3,5 attesi
per caso), nessuno dopo il beta.** Placebo di coerenza: «la notte che precede uno shock» vale −6,2
punti, 0/9 anni — mostra quanto è grande un numero falso quando si seleziona sull'esito.

## Candidati (kind="regularity")
| id | segno | n | media [CI] | p₂ | anni | warmup |
|---|---|---|---|---|---|---|
| vol_har_vs_mean22 | + | 1849 | +0,1821 [+0,1546; +0,2105] | 0,0001 | 8/8 | 560 |
| vol_leverage_sign | + | 1849 | +0,0640 [+0,0385; +0,0888] | 0,0001 | 7/8 | 560 |
| vol_midday_variance_ratio | − | 2121 | −0,1168 [−0,1448; −0,0881] | 0,0001 | 8/9 | 0 |

La finestra del terzo è post hoc (dichiarato). Escluso per limite: A2 (range notturno). Sono fatti sul
mercato, non strategie.

## Non testato
Eventi macro (nessuna data nel dataset); dimensionamento inverso alla vol (non esprimibile a 1 contratto).
