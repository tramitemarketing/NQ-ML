# Potenza dei verdetti: che cosa un FAIL esclude davvero

Generato da `lab/potenza.py` rileggendo soltanto `lab/verdicts/*.json`: nessun dato, nessun test nuovo.
Unità: quelle del verdetto (punti netti a trade per i tradeable; per le regolarità l'unità della famiglia,
vedi la relazione). SE ricavato dall'intervallo bootstrap a blocchi per giorno; MDE80 = effetto minimo che
il test vedeva con probabilità 80 % alla soglia α = 0,05/K usata dal controller; «escluso sopra» = limite
unilaterale al livello α. Sono ordini di grandezza (approssimazione normale), non verdetti nuovi.

| fase | id | tipo | K | n | stima [CI 95 %] | SE | MDE80 | escluso sopra | verdetto |
|---|---|---|---|---|---|---|---|---|---|
| confi | `cross_session_onrange_rthrange` | regu | 4 | 611 | 0,164 [0,124; 0,204] | 0,021 | 0,069 | — | PASS |
| confi | `cross_session_rth_to_evening` | regu | 4 | 609 | 2,50 [-1,29; 5,64] | 1,77 | 5,90 | 6,92 | FAIL |
| confi | `r2_footprints_slice_continuation` | regu | 3 | 611 | 0,010 [-0,009; 0,030] | 0,010 | 0,032 | 0,034 | FAIL |
| confi | `r2_range_pcband_breakout_R` | regu | 3 | 190 | 0,006 [-0,044; 0,065] | 0,028 | 0,091 | 0,073 | FAIL |
| confi | `vol_har_vs_mean22` | regu | 4 | 611 | 0,175 [0,128; 0,224] | 0,025 | 0,082 | — | PASS |
| confi | `postval_rth_to_evening_trade` | trad | 4 | 609 | 1,75 [-2,04; 4,89] | 1,77 | 5,45 | 5,71 | FAIL |
| confi | `r2_range_pcband_breakout` | trad | 3 | 190 | -2,59 [-15,77; 12,13] | 7,12 | 21,13 | 12,56 | FAIL |
| valid | `cross_session_onrange_rthrange` | regu | 13 | 1187 | 0,121 [0,093; 0,148] | 0,014 | 0,052 | — | PASS |
| valid | `cross_session_rth_to_evening` | regu | 13 | 1186 | 1,70 [0,651; 2,75] | 0,536 | 2,00 | — | PASS |
| valid | `intraday_momentum_rin_last30_gross` | regu | 13 | 1186 | 1,76 [-0,811; 4,33] | 1,31 | 4,89 | 5,55 | FAIL |
| valid | `micro_surprise_continuation` | regu | 13 | 512 | 3,60 [-1,01; 8,04] | 2,31 | 8,61 | 10,27 | FAIL |
| valid | `ml_rank30` | regu | 13 | 1187 | 0,014 [-0,003; 0,030] | 0,008 | 0,031 | 0,038 | FAIL |
| valid | `r2_costaware_mom20_restofday` | regu | 5 | 1184 | 0,024 [-0,026; 0,075] | 0,026 | 0,088 | 0,091 | FAIL |
| valid | `r2_footprints_close_clock_continuation` | regu | 5 | 1187 | 0,177 [0,039; 0,319] | 0,071 | 0,244 | 0,361 | FAIL |
| valid | `r2_footprints_slice_continuation` | regu | 5 | 1187 | 0,024 [0,009; 0,038] | 0,007 | 0,025 | — | PASS |
| valid | `r2_range_pcband_breakout_R` | regu | 5 | 354 | 0,061 [0,027; 0,097] | 0,018 | 0,060 | — | PASS |
| valid | `r4_implied_har_plus_vxn` | regu | 2 | 1187 | 0,014 [-0,002; 0,031] | 0,009 | 0,026 | 0,034 | FAIL |
| valid | `r4_implied_on_plus_vxn` | regu | 2 | 1187 | 0,006 [-0,007; 0,019] | 0,007 | 0,020 | 0,021 | FAIL |
| valid | `vol_har_vs_mean22` | regu | 13 | 1187 | 0,214 [0,171; 0,261] | 0,023 | 0,085 | — | PASS |
| valid | `vol_leverage_sign` | regu | 13 | 1187 | 0,033 [-0,001; 0,066] | 0,017 | 0,064 | 0,083 | FAIL |
| valid | `vol_midday_variance_ratio` | regu | 13 | 1183 | -0,056 [-0,097; -0,014] | 0,021 | 0,079 | -0,118 | FAIL |
| valid | `calendar_turnaround_tue_am` | trad | 13 | 83 | -5,28 [-30,80; 20,26] | 13,02 | 45,68 | 29,43 | FAIL |
| valid | `intraday_momentum_hivol_last30` | trad | 13 | 386 | 7,88 [1,47; 14,12] | 3,23 | 11,32 | 16,48 | FAIL |
| valid | `micro_overnight_break_fade` | trad | 13 | 498 | 1,54 [-5,98; 9,50] | 3,95 | 13,86 | 12,07 | FAIL |
| valid | `multiday_contra10_long` | trad | 13 | 67 | -19,75 [-133; 80,54] | 54,51 | 191 | 126 | FAIL |
| valid | `multiday_contra10_ls` | trad | 13 | 134 | -76,85 [-158; -1,00] | 39,97 | 140 | 29,68 | FAIL |
| valid | `r2_range_pcband_breakout` | trad | 5 | 354 | 12,06 [4,73; 19,38] | 3,74 | 11,85 | — | PASS |

## Conferma: si poteva vedere quello che la validazione prometteva?

Bersaglio = 0,5 × stima di validazione (maledizione del vincitore misurata nel laboratorio:
0,35-0,7). «Anni necessari» = anni di dati come quelli del blocco di conferma per vedere il bersaglio con
potenza 80 %.

| id | validazione | bersaglio | conferma [CI 95 %] | potenza sul bersaglio | anni necessari | lettura |
|---|---|---|---|---|---|---|
| `cross_session_onrange_rthrange` | 0,121 | 0,060 | 0,164 [0,124; 0,204] | 67 % | 3,2 | confermata |
| `cross_session_rth_to_evening` | 1,70 | 0,849 | 2,50 [-1,29; 5,64] | 2 % | 119 | **non decidibile** con questo blocco |
| `r2_footprints_slice_continuation` | 0,024 | 0,012 | 0,010 [-0,009; 0,030] | 11 % | 18,4 | **non decidibile** con questo blocco |
| `r2_range_pcband_breakout_R` | 0,061 | 0,031 | 0,006 [-0,044; 0,065] | 10 % | 21,5 | **non decidibile** con questo blocco |
| `vol_har_vs_mean22` | 0,214 | 0,107 | 0,175 [0,128; 0,224] | 97 % | 1,5 | confermata |
| `r2_range_pcband_breakout` | 12,06 | 6,03 | -2,59 [-15,77; 12,13] | 10 % | 30,3 | **non decidibile** con questo blocco |

## Come leggerlo

- Un FAIL con MDE80 grande non dice «non esiste»: dice «se c'è, è sotto *escluso sopra*». La formula
  onesta per i contenuti è «non ha retto» oppure «non decidibile con questi dati», mai «era fortuna».
- Le due regolarità confermate (HAR e notte → giorno) hanno MDE80 molto sotto la stima: lì la potenza c'è.
- Per un tradeable come la rottura delle bande (σ ≈ 100 punti a trade, ~77 trade l'anno) un vantaggio
  vero di qualche punto non è decidibile su un solo strumento in tempi umani: servono più mercati
  indipendenti o trade più frequenti, non più anni di NQ.
