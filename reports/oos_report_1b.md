# Report OOS — 1b

Generato il 2026-09-21 · config `c75de95ae278` · commit `b2be4fe` · feature `1b` · cassaforte dal 2026-03-20 **mai usata**

Nota: **C ha 3 regole** (`vol_slope_excursion < 0`, `vol_reentry_bar > 1`, `delta_excursion > 0`), come da spec §9.2.

## Criteri pre-registrati (spec §11.1)

| # | criterio | esito | evidenza |
|---|---|---|---|
| 1 | A: R medio/trade > 0 dopo costi, CI esclude 0, a 1 tick; ancora > 0 a 2 tick | FAIL | R medio -0.040 [-0.177, 0.095]; a 2 tick -0.057 |
| 2 | (A − B0), (A − C), (A − C-opt) > 0 su R medio/trade, CI esclude 0 | FAIL | A−B0: [-0.177, 0.092]; A−C: [-0.877, -0.011]; A−Copt: [-0.601, 0.109] |
| 3 | segno positivo di (A − B0) in ≥ 4 finestre su 5 | FAIL | 2/5 finestre: 0: -0.199, 1: +0.106, 2: -0.213, 3: +0.188, 4: -0.368 |
| 4 | shuffle test AUC ∈ [0.45, 0.55]; A batte il solo-contesto su Brier | FAIL | shuffle AUC [0.608, 0.484, 0.492, 0.61, 0.493]; Brier(A) − Brier(contesto) per evento (bootstrap appaiato per giorno): +0.0086 [+0.0031, +0.0143] — A peggio del solo-contesto (Brier medio-per-fold a vs b: A 0.1909, contesto 0.1826); pooled A 0.1913 vs prior geometrico 0.1777 |
| 5 | A prende ≥ 300 trade OOS | PASS | 410 trade |

**1/5 criteri superati.** Il modello 1b non supera i criteri: il report dice quali. Prossimo passo secondo la regola dei tre sguardi.


## Note sulla milestone

# Note sulla milestone 1b-S (order flow su giorni campionati)

- **Shuffle AUC**: seed 0 fuori banda nelle pieghe 0 e 3 per entrambe le esecuzioni (1a_S 0.641/0.615; 1b 0.608/0.610). Rimisurato con 5 seed su 1a_S: piega 0 con vincoli monotoni [0.641, 0.399, 0.453, 0.607, 0.545] media 0.529, senza vincoli media 0.475; piega 3 con vincoli [0.615, 0.442, 0.517, 0.602, 0.434] media 0.522, senza 0.503. Distribuzione simmetrica attorno a 0.5 → non è leakage: test a seed singolo poco potente su n_fit 1.421, con un +0.03 strutturale dovuto ai vincoli monotoni (`rr_ratio: −1` ordina come il prior anche su label mescolate). Ipotesi per lo sguardo #3 (da pre-registrare, non applicata): shuffle multi-seed o senza vincoli.
- **Giorno degraded**: 2026-03-16 marcato "degraded" da Databento (qualità del feed ridotta) nell'ultima finestra di test (piega 4).
- **Quota**: 0.45 di config, 0.4450 effettiva (498/1119, arrotondamento mensile); soglia del criterio (iv) = 300 × 0.445 = 133.5 → 134.
- **Calibrazione**: isotonica su 93–112 punti per piega (metà della validazione): `p` assume 14–46 valori distinti per piega (misurato nella review finale); la calibrazione costa circa +0.007/+0.008 di Brier rispetto alle probabilità grezze dei booster (misurato: Brier grezzo 1b 0.1844, 1a_S 0.1803).
- **Griglia del bootstrap**: la CI del criterio (iii) è invariante alla griglia dei giorni del bootstrap (611 giorni di test / 272 campionati / 235 con trade: estremi che si muovono ≤ 0.003, misurato nella review finale).
- **Conseguenza della regola §12-bis**: (i) e (ii) FAIL → **non si acquistano le finestre restanti**; lo sguardo #3 non è innescato da questa milestone.


## Come leggere questo report

- L'AUC di A (0.7421, pooled) è quasi tutta geometria dello stop/target, non skill del modello: il prior a zero parametri `p = 1/(1+rr_ratio)` fa 0.7701 — la differenza è nel rumore.
- La clausola Brier del criterio 4 (spec §11.1 «dalla 1b»): bootstrap appaiato per evento di Brier(A) − Brier(contesto) = +0.0086 [+0.0031, +0.0143] — A peggio del solo-contesto (Brier medio-per-fold a vs b: A 0.1909, contesto 0.1826, A meglio in 2/5 finestre); pooled A 0.1913 vs prior geometrico 0.1777.
- L'R medio di A è negativo (-0.040): nello stress che toglie il 5% dei trade migliori, R medio scende a -0.293; e il segno di (A − B0) cambia da finestra a finestra (0: -0.199, 1: +0.106, 2: -0.213, 3: +0.188, 4: -0.368).
- Sharpe giornaliero e mesi negativi/totali sono calcolati su TUTTI i giorni/mesi di test, non solo su quelli con trade: un giorno o un mese senza trade pesa 0, non manca dal conteggio (vedi nota I1 della review).
- Lo stress `slip_N` applica N tick di slippage per lato sull'ingresso e su **ogni** uscita a mercato (stop, time-stop) — più severo del solo "sugli stop" della bozza; il target resta un ordine limite (nessuno slippage). Un'uscita per gap-through-stop nella stessa barra è valorizzata al livello dello stop (ottimistico); `slip_3` è la proxy più vicina a un mercato che apre in gap.
- C-opt cerca le due soglie a griglia sul training di ogni finestra (in-sample per quella finestra): è un limite superiore ottimistico su quanto le regole potrebbero rendere, non una strategia eseguibile fuori dal backtest.
- La riga "A su MNQ (÷10)" è una divisione ingenua per 10: commissioni e tick di MNQ non scalano linearmente con quelli di NQ, quindi la riga sottostima i costi reali su MNQ.
- Esecuzione su un sottoinsieme campionato (quota effettiva 0.4450 dei giorni di popolazione): solo quei giorni possono avere trade, quindi `trades_per_day` e `pct_days_active` sono diluiti di circa 1/0.445 ≈ 2.25× rispetto a un'esecuzione su tutti i giorni, e lo Sharpe giornaliero di circa √0.445 ≈ 0.67× rispetto a un'esecuzione sull'intera popolazione.


## Confronto appaiato 1b − 1a_S (stessi eventi, stesse pieghe)

| finestra | AUC A_a | AUC A_b | AUC prior | Brier A_a | Brier A_b | Brier prior |
|---|---|---|---|---|---|---|
| 0 | 0.7428 | 0.7121 | 0.7672 | 0.1902 | 0.1965 | 0.1825 |
| 1 | 0.7481 | 0.7752 | 0.7808 | 0.1906 | 0.1791 | 0.1783 |
| 2 | 0.7582 | 0.7489 | 0.7893 | 0.1905 | 0.1994 | 0.1709 |
| 3 | 0.7391 | 0.7353 | 0.7544 | 0.1927 | 0.2023 | 0.1803 |
| 4 | 0.7447 | 0.7425 | 0.7497 | 0.1731 | 0.1774 | 0.1760 |

- Brier per evento, 1b − 1a_S: **+0.0032** [-0.0019, +0.0084]
- Brier per evento, 1b − prior geometrico: **+0.0137** [+0.0076, +0.0196]
- Brier per evento, 1a_S − prior geometrico: **+0.0105** [+0.0045, +0.0166]
- Brier per evento, 1b − solo-contesto: **+0.0086** [+0.0031, +0.0143]
- Brier per evento, 1a_S − solo-contesto: **+0.0054** [+0.0000, +0.0107]
- R medio dei trade presi, 1b − 1a_S: **+0.007** [-0.117, +0.130] (n 410 vs 453)
- Decisioni: Jaccard 0.418 · entrambe 307 · solo 1a_S 240 · solo 1b 188

| # | criterio appaiato | esito | evidenza |
|---|---|---|---|
| i | Brier(A_1b) − Brier(A_1a_S) per evento: CI esclude 0, negativa | FAIL | +0.0032 [-0.0019, +0.0084] |
| ii | Brier(A_1b) − Brier(prior geometrico) per evento: CI esclude 0, negativa | FAIL | +0.0137 [+0.0076, +0.0196] |
| iii | R medio(A_1b) − R medio(A_1a_S) appaiato per giorno: CI esclude 0, positiva | FAIL | +0.007 [-0.117, +0.130] (n 410 vs 453) |
| iv | A_1b prende ≥ 300 · quota trade OOS (= 134) | PASS | 410 trade |

## Le quattro colonne (OOS aggregato, 5 finestre)

| strategia | n | trades_per_day | win_rate | mean_R | ci | profit_factor | expectancy_usd | max_dd_R | max_dd_usd | sharpe_daily | months |
|---|---|---|---|---|---|---|---|---|---|---|---|
| A | 410 | 0.671 | 0.393 | -0.040 | [-0.177, 0.095] | 0.960 | -16.195 | 51.930 | 21390.000 | -0.190 | 17/30 |
| B0 | 1184 | 1.938 | 0.420 | -0.001 | [-0.098, 0.110] | 0.994 | -2.677 | 66.230 | 36210.000 | -0.052 | 14/30 |
| C | 40 | 0.065 | 0.625 | 0.364 | [-0.017, 0.817] | 1.642 | 288.375 | 3.035 | 3740.000 | 0.885 | 8/30 |
| Copt | 52 | 0.085 | 0.577 | 0.183 | [-0.126, 0.534] | 1.428 | 195.769 | 6.059 | 6240.000 | 0.795 | 11/30 |
| A su MNQ (÷10) | 410 | 0.671 | 0.393 | -0.040 |  | 0.960 | -1.620 | 51.930 | 2139.000 | -0.190 | 17/30 |

### Differenze su R medio/trade (CI 95%)

| confronto | stima | CI |
|---|---|---|
| A − B0 | -0.039 | [-0.177, 0.092] |
| A − C | -0.403 | [-0.877, -0.011] |
| A − Copt | -0.222 | [-0.601, 0.109] |

### Segno di (A − B0) per finestra

| finestra | test | A − B0 (R medio) |
|---|---|---|
| 0 | 2023-10-02..2024-03-28 | -0.199 |
| 1 | 2024-04-01..2024-09-30 | 0.106 |
| 2 | 2024-10-01..2025-03-31 | -0.213 |
| 3 | 2025-04-01..2025-09-30 | 0.188 |
| 4 | 2025-10-01..2026-03-19 | -0.368 |

### Motore: esiti per strategia

| strategia | taken | duplicate | skipped_in_position | not_taken |
|---|---|---|---|---|
| A | 410 | 9 | 76 | 1564 |
| B0 | 1184 | 83 | 792 | 0 |
| C | 40 | 4 | 0 | 2015 |
| Copt | 52 | 7 | 1 | 1999 |

## Stress su A (decisioni fisse a 1 tick, P&L rivalutato; slippage per lato: ingresso e ogni uscita a mercato; target = limite)

| scenario | n | win rate | R medio | PF | expectancy $ | max DD R |
|---|---|---|---|---|---|---|
| base | 410 | 0.393 | -0.040 | 0.960 | -16.195 | 51.930 |
| slip_2 | 410 | 0.393 | -0.057 | 0.941 | -24.317 | 54.915 |
| slip_3 | 410 | 0.393 | -0.074 | 0.923 | -32.439 | 57.804 |
| comm_x2 | 410 | 0.393 | -0.051 | 0.948 | -21.195 | 54.262 |
| drop_top_5pct | 389 | 0.360 | -0.293 | 0.714 | -122.995 | 113.855 |

## Controlli anti-inganno per finestra

| finestra | test | AUC A | Brier A | Brier contesto | AUC shuffle | AUC prior | Brier prior | n feature A | best iter | C-opt |
|---|---|---|---|---|---|---|---|---|---|---|
| 0 | 2023-10-02..2024-03-28 | 0.712 | 0.196 | 0.187 | 0.608 | 0.767 | 0.183 | 21 | 1112 | [{'feature': 'vol_slope_excursion', 'op': '<', 'value': -0.02, 'values': [-0.05, -0.02, 0.0, 0.02, 0.05]}, {'feature': 'vol_reentry_bar', 'op': '>', 'value': 0.8, 'values': [0.8, 1.0, 1.2, 1.5]}, {'feature': 'delta_excursion', 'op': '>', 'value': 0.0, 'values': [-0.1, 0.0, 0.1, 0.2]}] |
| 1 | 2024-04-01..2024-09-30 | 0.775 | 0.179 | 0.181 | 0.484 | 0.781 | 0.178 | 21 | 239 | [{'feature': 'vol_slope_excursion', 'op': '<', 'value': 0.0, 'values': [-0.05, -0.02, 0.0, 0.02, 0.05]}, {'feature': 'vol_reentry_bar', 'op': '>', 'value': 0.8, 'values': [0.8, 1.0, 1.2, 1.5]}, {'feature': 'delta_excursion', 'op': '>', 'value': 0.0, 'values': [-0.1, 0.0, 0.1, 0.2]}] |
| 2 | 2024-10-01..2025-03-31 | 0.749 | 0.199 | 0.179 | 0.492 | 0.789 | 0.171 | 21 | 478 | [{'feature': 'vol_slope_excursion', 'op': '<', 'value': 0.0, 'values': [-0.05, -0.02, 0.0, 0.02, 0.05]}, {'feature': 'vol_reentry_bar', 'op': '>', 'value': 1.0, 'values': [0.8, 1.0, 1.2, 1.5]}, {'feature': 'delta_excursion', 'op': '>', 'value': 0.0, 'values': [-0.1, 0.0, 0.1, 0.2]}] |
| 3 | 2025-04-01..2025-09-30 | 0.735 | 0.202 | 0.188 | 0.610 | 0.754 | 0.180 | 19 | 424 | [{'feature': 'vol_slope_excursion', 'op': '<', 'value': 0.0, 'values': [-0.05, -0.02, 0.0, 0.02, 0.05]}, {'feature': 'vol_reentry_bar', 'op': '>', 'value': 1.0, 'values': [0.8, 1.0, 1.2, 1.5]}, {'feature': 'delta_excursion', 'op': '>', 'value': 0.0, 'values': [-0.1, 0.0, 0.1, 0.2]}] |
| 4 | 2025-10-01..2026-03-19 | 0.743 | 0.177 | 0.178 | 0.493 | 0.750 | 0.176 | 23 | 226 | [{'feature': 'vol_slope_excursion', 'op': '<', 'value': 0.0, 'values': [-0.05, -0.02, 0.0, 0.02, 0.05]}, {'feature': 'vol_reentry_bar', 'op': '>', 'value': 1.0, 'values': [0.8, 1.0, 1.2, 1.5]}, {'feature': 'delta_excursion', 'op': '>', 'value': 0.0, 'values': [-0.1, 0.0, 0.1, 0.2]}] |

Prior geometrico p = 1/(1+rr): AUC 0.7701 vs A 0.7421 (pooled); Brier prior 0.1777 vs A 0.1913 (pooled); Brier tasso base 0.2241


## Calibrazione (decili di p, tutti gli eventi di test)

| decile | p media | freq. osservata | n |
|---|---|---|---|
| 0 | 0.021 | 0.075 | 412 |
| 1 | 0.167 | 0.252 | 206 |
| 2 | 0.213 | 0.254 | 264 |
| 3 | 0.290 | 0.260 | 285 |
| 4 | 0.321 | 0.356 | 87 |
| 5 | 0.435 | 0.468 | 237 |
| 6 | 0.488 | 0.454 | 183 |
| 7 | 0.653 | 0.606 | 188 |
| 8 | 0.869 | 0.685 | 197 |

## Decomposizione dei trade A (solo lettura, mai per selezionare)


**per va_type**

| gruppo | n | win rate | R medio |
|---|---|---|---|
| DEV | 288 | 0.375 | -0.032 |
| ON | 122 | 0.434 | -0.059 |

**per side**

| gruppo | n | win rate | R medio |
|---|---|---|---|
| long | 186 | 0.435 | -0.008 |
| short | 224 | 0.357 | -0.066 |

**per fascia**

| gruppo | n | win rate | R medio |
|---|---|---|---|
| 09:30-10:30 | 188 | 0.489 | 0.078 |
| 10:30-12:00 | 124 | 0.315 | -0.108 |
| 12:00-14:00 | 69 | 0.304 | -0.100 |
| 14:00-15:30 | 29 | 0.310 | -0.370 |

## Feature selezionate per finestra

| finestra | feature |
|---|---|
| 0 | va_type, minutes_since_open, bars_in_profile, open_vs_on_va, va_width_atr, excursion_depth, excursion_minutes, reentry_close_pos, va_shift, in_other_va, stop_dist_atr, rr_ratio, vol_slope_excursion, vol_at_extreme, vol_reentry_bar, delta_excursion, delta_reentry, absorption_score, poc_pos, target_dist_atr, large_trade_share |
| 1 | va_type, minutes_since_open, bars_in_profile, open_vs_on_va, va_width_atr, excursion_depth, excursion_minutes, reentry_close_pos, va_shift, in_other_va, stop_dist_atr, rr_ratio, vol_slope_excursion, vol_at_extreme, vol_reentry_bar, delta_excursion, delta_reentry, absorption_score, rel_vol_session, day_range_atr, delta_at_extreme |
| 2 | va_type, minutes_since_open, bars_in_profile, open_vs_on_va, va_width_atr, excursion_depth, excursion_minutes, reentry_close_pos, va_shift, in_other_va, stop_dist_atr, rr_ratio, vol_slope_excursion, vol_at_extreme, vol_reentry_bar, delta_excursion, delta_reentry, absorption_score, dist_other_far_atr, delta_at_extreme, large_trade_delta |
| 3 | va_type, minutes_since_open, bars_in_profile, open_vs_on_va, va_width_atr, excursion_depth, excursion_minutes, reentry_close_pos, va_shift, in_other_va, stop_dist_atr, rr_ratio, vol_slope_excursion, vol_at_extreme, vol_reentry_bar, delta_excursion, delta_reentry, absorption_score, delta_at_extreme |
| 4 | va_type, minutes_since_open, bars_in_profile, open_vs_on_va, va_width_atr, excursion_depth, excursion_minutes, reentry_close_pos, va_shift, in_other_va, stop_dist_atr, rr_ratio, vol_slope_excursion, vol_at_extreme, vol_reentry_bar, delta_excursion, delta_reentry, absorption_score, bars_outside, poc_pos, vol_excursion_vs_pre, vol_reentry_slope, rel_vol_session |

## Figure

- `reports/figures_1b/equity_oos.png`
- `reports/figures_1b/calibration.png`
- `reports/figures_1b/shap_summary.png`
- `reports/figures_1b/shap_dependence_vol_slope_excursion.png`
- `reports/figures_1b/shap_dependence_vol_reentry_bar.png`
- `reports/figures_1b/shap_dependence_rr_ratio.png`
- `reports/figures_1b/shap_dependence_delta_excursion.png`
- `reports/figures_1b/shap_dependence_absorption_score.png`
- `reports/figures_1b/shap_dependence_delta_reentry.png`
