# r6_noise — pre-registrazione (2026-09-30, PRIMA di guardare qualunque risultato)

Ipotesi 7 del documento dell'utente del 2026-09-29: Noise Area di Zarattini, Aziz e Barbon (2024,
SSRN 4824172). Regole comuni in `lab/PROTOCOLLO.md` §19.

## Cosa si sa già (conoscenza a priori, dichiarata)
- Il paper riporta Sharpe 1,33 su SPY, 2007-2024.
- Quantitativo su ES con i parametri del paper: Sharpe 0,91, «sostanzialmente piatta 2010-2017».
  Questo tocca il nostro discovery.
- Una replica pre-registrata (codecat-ops) su SPY da luglio 2020 e su ES da maggio 2024 a luglio 2026:
  Sharpe circa zero dal 2025.
Quindi la validazione è in parte e la cassaforte del tutto coperte da risultati pubblici. È un parente
stretto delle famiglie di breakout già chiuse. Aspettativa bassa, dichiarata.

## Passo 0 (risposte prima dei test, solo discovery)
1. O = open della barra delle 09:30. C_(t−1) = close della barra 15:59 della sessione valida precedente,
   in adj.
2. σ̄_τ = media di |P_τ/O − 1| agli stessi minuti τ nelle 14 sessioni valide precedenti, giorno t escluso.
   Verificare che nessun dato di t entri nelle bande.
3. Esecuzione: il segnale nasce alla chiusura della barra τ, l'ordine si esegue all'open della barra
   successiva, mai sulla barra del segnale.
4. Sovrapposizione: quali famiglie chiuse si possono ricostruire nel discovery dal codice esistente
   (`r2_range_pcband_breakout`, ORB15 e prima ora dello screening `nqml/screen`, candidato 4)? Quelle che
   non si possono ricostruire vanno dichiarate.

## Regole (parametri del paper, 14 giorni; nessuna ottimizzazione e nessuna griglia)
- UB_τ = max(O, C_(t−1))·(1 + σ̄_τ)
- LB_τ = min(O, C_(t−1))·(1 − σ̄_τ)
- τ ∈ {10:00, 10:30, …, 15:30}

- **A — segnale nudo**: primo τ del giorno con P_τ > UB_τ (long) o P_τ < LB_τ (short). Rendimento fino
  alle 16:00, senza stop. Orizzonti di 30 e 60 minuti solo descrittivi.
- **B — regole complete**: trailing stop a max(UB, VWAP) per i long e min(LB, VWAP) per gli short,
  controllato ogni 30 minuti; uscita alle 16:00; 1 contratto; niente vol targeting. Lordo e netto per anno.
  VWAP RTH dalle 09:30, dalle barre a 1 minuto (prezzo tipico × volume).

**Placebo**: τ casuale sulla stessa griglia, lato = segno di ln(P_τ/O), stesse uscite.
Si riporta la correlazione del P&L giornaliero di B con ogni famiglia chiusa che si riesce a ricostruire.

## Regole di decisione (fissate ora)
GO solo se valgono tutte:
- Holm k = 2, e sia A sia B hanno p di Holm < 0,05;
- t ≥ 1 in entrambe le metà;
- placebo ≥ 95° percentile;
- B netto a 1,25 > 0 in entrambe le metà;
- correlazione < 0,5 con ogni famiglia chiusa;
- criteri del §19.
Con GO, B diventa candidato `tradeable`. La lettura dei suoi verdetti in validazione e in cassaforte andrà
pesata con la conoscenza pubblica dichiarata sopra. Altrimenti la famiglia si chiude, senza varianti.

## Addendum 1 (2026-09-30, dopo il Passo 0 e prima di qualunque test primario; deciso dall'utente)
Il criterio «correlazione < 0,5 con ogni famiglia chiusa» si legge in senso severo. La correlazione del
P&L giornaliero di B, con zero nei giorni senza trade, deve stare sotto 0,5 con **ognuna** delle serie
seguenti, ricostruite sul discovery dal codice esistente:
- le 8 geometrie di ORB15 (`nqml/screen/orb.py`);
- le 8 geometrie della prima ora (`nqml/screen/firsthour.py`);
- le 8 geometrie del candidato 4 (`nqml/screen/vabreak.py`);
- la rottura delle bande di volatilità, `r2_range_pcband_breakout` (`lab/r2_range/candidates.py`).

In tutto sono 25 serie. Basta una correlazione ≥ 0,5 per bloccare il GO.
Se una serie non si riesce a ricostruire, va dichiarata prima di guardare la correlazione di B.
Tutto il resto del PREREG resta invariato.
