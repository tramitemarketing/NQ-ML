# Report OOS — 1c_B

Generato il 2026-09-22 · config `2ee491362e71` · commit `18a2b44` · feature `1c_B` · cassaforte dal 2026-03-20 **mai usata**

Nota: **C ha 3 regole** (`vol_slope_excursion < 0`, `vol_reentry_bar > 1`, `delta_excursion > 0`), come da spec §9.2.

Nota: le 3 feature order flow sono NaN su 2618 dei 4677 eventi di test (giorni non campionati): il modello B usa la direzione di default degli split fuori da S; le regole C con `delta_excursion` scattano solo su S.

## Criteri pre-registrati (spec §11.1)

| # | criterio | esito | evidenza |
|---|---|---|---|
| 1 | A: R medio/trade > 0 dopo costi, CI esclude 0, a 1 tick; ancora > 0 a 2 tick | FAIL | R medio -0.099 [-0.316, 0.133]; a 2 tick -0.118 |
| 2 | (A − B0), (A − C), (A − C-opt) > 0 su R medio/trade, CI esclude 0 | FAIL | A−B0: [-0.313, 0.132]; A−C: [-0.975, -0.019]; A−Copt: [-0.649, 0.157] |
| 3 | segno positivo di (A − B0) in ≥ 4 finestre su 5 | FAIL | 1/5 finestre: 0: -0.245, 1: -0.005, 2: -0.123, 3: +nan, 4: +0.298 |
| 4 | shuffle test AUC ∈ [0.45, 0.55]; A batte il solo-contesto su Brier | FAIL | shuffle AUC [0.523, 0.499, 0.476, 0.514, 0.517]; Brier(A) − Brier(contesto) per evento (bootstrap appaiato per giorno): +0.0005 [-0.0005, +0.0015] — A peggio del solo-contesto (Brier medio-per-fold a vs b: A 0.1786, contesto 0.1782); pooled A 0.1791 vs prior geometrico 0.1820 |
| 5 | A prende ≥ 300 · quota (= 134) trade OOS (§12-ter: le feature tick esistono solo sui giorni campionati) | PASS | 194 trade — soglia 300 · 0.445 = 134 (§12-ter: le feature tick esistono solo sui giorni campionati) |

**1/5 criteri superati.** Il modello 1c_B non supera i criteri: il report dice quali. Prossimo passo secondo la regola dei tre sguardi. (questo è il terzo: dal prossimo serve l'ipotesi pre-registrata)


## Come leggere questo report

- L'AUC di A (0.7633, pooled) è quasi tutta geometria dello stop/target, non skill del modello: il prior a zero parametri `p = 1/(1+rr_ratio)` fa 0.7569 — la differenza è nel rumore.
- La clausola Brier del criterio 4 (spec §11.1 «dalla 1b»): bootstrap appaiato per evento di Brier(A) − Brier(contesto) = +0.0005 [-0.0005, +0.0015] — A peggio del solo-contesto (Brier medio-per-fold a vs b: A 0.1786, contesto 0.1782, A meglio in 3/5 finestre); pooled A 0.1791 vs prior geometrico 0.1820.
- L'R medio di A è negativo (-0.099): nello stress che toglie il 5% dei trade migliori, R medio scende a -0.352; e il segno di (A − B0) cambia da finestra a finestra (0: -0.245, 1: -0.005, 2: -0.123, 3: +nan, 4: +0.298).
- Sharpe giornaliero e mesi negativi/totali sono calcolati su TUTTI i giorni/mesi di test, non solo su quelli con trade: un giorno o un mese senza trade pesa 0, non manca dal conteggio (vedi nota I1 della review).
- Lo stress `slip_N` applica N tick di slippage per lato sull'ingresso e su **ogni** uscita a mercato (stop, time-stop) — più severo del solo "sugli stop" della bozza; il target resta un ordine limite (nessuno slippage). Un'uscita per gap-through-stop nella stessa barra è valorizzata al livello dello stop (ottimistico); `slip_3` è la proxy più vicina a un mercato che apre in gap.
- C-opt cerca le due soglie a griglia sul training di ogni finestra (in-sample per quella finestra): è un limite superiore ottimistico su quanto le regole potrebbero rendere, non una strategia eseguibile fuori dal backtest.
- La riga "A su MNQ (÷10)" è una divisione ingenua per 10: commissioni e tick di MNQ non scalano linearmente con quelli di NQ, quindi la riga sottostima i costi reali su MNQ.

## Le quattro colonne (OOS aggregato, 5 finestre)

| strategia | n | trades_per_day | win_rate | mean_R | ci | profit_factor | expectancy_usd | max_dd_R | max_dd_usd | sharpe_daily | months |
|---|---|---|---|---|---|---|---|---|---|---|---|
| A | 194 | 0.318 | 0.309 | -0.099 | [-0.316, 0.133] | 0.904 | -37.500 | 37.155 | 22970.000 | -0.334 | 12/30 |
| B0 | 2675 | 4.378 | 0.421 | -0.002 | [-0.068, 0.070] | 0.953 | -20.479 | 95.757 | 133805.000 | -0.624 | 18/30 |
| C | 40 | 0.065 | 0.625 | 0.369 | [-0.012, 0.822] | 1.665 | 299.125 | 3.035 | 3740.000 | 0.922 | 8/30 |
| Copt | 52 | 0.085 | 0.558 | 0.130 | [-0.172, 0.477] | 1.280 | 132.500 | 6.597 | 6240.000 | 0.568 | 11/30 |
| A su MNQ (÷10) | 194 | 0.318 | 0.309 | -0.099 |  | 0.904 | -3.750 | 37.155 | 2297.000 | -0.334 | 12/30 |

### Differenze su R medio/trade (CI 95%)

| confronto | stima | CI |
|---|---|---|
| A − B0 | -0.097 | [-0.313, 0.132] |
| A − C | -0.468 | [-0.975, -0.019] |
| A − Copt | -0.229 | [-0.649, 0.157] |

### Segno di (A − B0) per finestra

| finestra | test | A − B0 (R medio) |
|---|---|---|
| 0 | 2023-10-02..2024-03-28 | -0.245 |
| 1 | 2024-04-01..2024-09-30 | -0.005 |
| 2 | 2024-10-01..2025-03-31 | -0.123 |
| 3 | 2025-04-01..2025-09-30 | n/d |
| 4 | 2025-10-01..2026-03-19 | 0.298 |

### Motore: esiti per strategia

| strategia | taken | duplicate | skipped_in_position | not_taken |
|---|---|---|---|---|
| A | 194 | 2 | 16 | 4465 |
| B0 | 2675 | 229 | 1773 | 0 |
| C | 40 | 4 | 0 | 4633 |
| Copt | 52 | 7 | 1 | 4617 |

## Stress su A (decisioni fisse a 1 tick, P&L rivalutato; slippage per lato: ingresso e ogni uscita a mercato; target = limite)

| scenario | n | win rate | R medio | PF | expectancy $ | max DD R |
|---|---|---|---|---|---|---|
| base | 194 | 0.309 | -0.099 | 0.904 | -37.500 | 37.155 |
| slip_2 | 194 | 0.309 | -0.118 | 0.885 | -46.005 | 39.374 |
| slip_3 | 194 | 0.309 | -0.136 | 0.866 | -54.510 | 41.527 |
| comm_x2 | 194 | 0.309 | -0.111 | 0.893 | -42.500 | 38.750 |
| drop_top_5pct | 184 | 0.272 | -0.352 | 0.612 | -160.408 | 66.484 |

## Controlli anti-inganno per finestra

| finestra | test | AUC A | Brier A | Brier contesto | AUC shuffle | AUC prior | Brier prior | n feature A | best iter | C-opt |
|---|---|---|---|---|---|---|---|---|---|---|
| 0 | 2023-10-02..2024-03-28 | 0.759 | 0.188 | 0.188 | 0.523 | 0.759 | 0.188 | 18 | 197 | [{'feature': 'vol_slope_excursion', 'op': '<', 'value': -0.02, 'values': [-0.05, -0.02, 0.0, 0.02, 0.05]}, {'feature': 'vol_reentry_bar', 'op': '>', 'value': 0.8, 'values': [0.8, 1.0, 1.2, 1.5]}, {'feature': 'delta_excursion', 'op': '>', 'value': 0.0, 'values': [-0.1, 0.0, 0.1, 0.2]}] |
| 1 | 2024-04-01..2024-09-30 | 0.761 | 0.187 | 0.184 | 0.499 | 0.758 | 0.189 | 18 | 39 | [{'feature': 'vol_slope_excursion', 'op': '<', 'value': 0.0, 'values': [-0.05, -0.02, 0.0, 0.02, 0.05]}, {'feature': 'vol_reentry_bar', 'op': '>', 'value': 0.8, 'values': [0.8, 1.0, 1.2, 1.5]}, {'feature': 'delta_excursion', 'op': '>', 'value': 0.0, 'values': [-0.1, 0.0, 0.1, 0.2]}] |
| 2 | 2024-10-01..2025-03-31 | 0.783 | 0.165 | 0.164 | 0.476 | 0.777 | 0.170 | 18 | 60 | [{'feature': 'vol_slope_excursion', 'op': '<', 'value': 0.0, 'values': [-0.05, -0.02, 0.0, 0.02, 0.05]}, {'feature': 'vol_reentry_bar', 'op': '>', 'value': 1.0, 'values': [0.8, 1.0, 1.2, 1.5]}, {'feature': 'delta_excursion', 'op': '>', 'value': 0.0, 'values': [-0.1, 0.0, 0.1, 0.2]}] |
| 3 | 2025-04-01..2025-09-30 | 0.758 | 0.182 | 0.183 | 0.514 | 0.746 | 0.186 | 18 | 22 | [{'feature': 'vol_slope_excursion', 'op': '<', 'value': 0.0, 'values': [-0.05, -0.02, 0.0, 0.02, 0.05]}, {'feature': 'vol_reentry_bar', 'op': '>', 'value': 1.0, 'values': [0.8, 1.0, 1.2, 1.5]}, {'feature': 'delta_excursion', 'op': '>', 'value': 0.0, 'values': [-0.1, 0.0, 0.1, 0.2]}] |
| 4 | 2025-10-01..2026-03-19 | 0.757 | 0.170 | 0.171 | 0.517 | 0.744 | 0.176 | 18 | 136 | [{'feature': 'vol_slope_excursion', 'op': '<', 'value': 0.0, 'values': [-0.05, -0.02, 0.0, 0.02, 0.05]}, {'feature': 'vol_reentry_bar', 'op': '>', 'value': 1.0, 'values': [0.8, 1.0, 1.2, 1.5]}, {'feature': 'delta_excursion', 'op': '>', 'value': 0.0, 'values': [-0.1, 0.0, 0.1, 0.2]}] |

Prior geometrico p = 1/(1+rr): AUC 0.7569 vs A 0.7633 (pooled); Brier prior 0.1820 vs A 0.1791 (pooled); Brier tasso base 0.2238 · L2 (prior calibrato sul training) 0.1804


## Calibrazione (decili di p, tutti gli eventi di test)


Modalità offset (§12-ter): nessun calibratore post hoc, validazione intera per early stopping.

| decile | p media | freq. osservata | n |
|---|---|---|---|
| 0 | 0.055 | 0.051 | 468 |
| 1 | 0.124 | 0.145 | 468 |
| 2 | 0.177 | 0.156 | 467 |
| 3 | 0.231 | 0.201 | 468 |
| 4 | 0.293 | 0.288 | 468 |
| 5 | 0.354 | 0.313 | 467 |
| 6 | 0.419 | 0.429 | 468 |
| 7 | 0.496 | 0.471 | 467 |
| 8 | 0.603 | 0.528 | 468 |
| 9 | 0.803 | 0.797 | 468 |

## Decomposizione dei trade A (solo lettura, mai per selezionare)


**per va_type**

| gruppo | n | win rate | R medio |
|---|---|---|---|
| DEV | 148 | 0.277 | -0.152 |
| ON | 46 | 0.413 | 0.073 |

**per side**

| gruppo | n | win rate | R medio |
|---|---|---|---|
| long | 95 | 0.337 | -0.059 |
| short | 99 | 0.283 | -0.137 |

**per fascia**

| gruppo | n | win rate | R medio |
|---|---|---|---|
| 09:30-10:30 | 113 | 0.354 | 0.034 |
| 10:30-12:00 | 53 | 0.283 | -0.105 |
| 12:00-14:00 | 20 | 0.200 | -0.546 |
| 14:00-15:30 | 8 | 0.125 | -0.823 |

## Feature selezionate per finestra

| finestra | feature |
|---|---|
| 0 | va_type, minutes_since_open, bars_in_profile, open_vs_on_va, va_width_atr, excursion_depth, excursion_minutes, reentry_close_pos, va_shift, in_other_va, stop_dist_atr, rr_ratio, vol_slope_excursion, vol_at_extreme, vol_reentry_bar, delta_excursion, delta_reentry, absorption_score |
| 1 | va_type, minutes_since_open, bars_in_profile, open_vs_on_va, va_width_atr, excursion_depth, excursion_minutes, reentry_close_pos, va_shift, in_other_va, stop_dist_atr, rr_ratio, vol_slope_excursion, vol_at_extreme, vol_reentry_bar, delta_excursion, delta_reentry, absorption_score |
| 2 | va_type, minutes_since_open, bars_in_profile, open_vs_on_va, va_width_atr, excursion_depth, excursion_minutes, reentry_close_pos, va_shift, in_other_va, stop_dist_atr, rr_ratio, vol_slope_excursion, vol_at_extreme, vol_reentry_bar, delta_excursion, delta_reentry, absorption_score |
| 3 | va_type, minutes_since_open, bars_in_profile, open_vs_on_va, va_width_atr, excursion_depth, excursion_minutes, reentry_close_pos, va_shift, in_other_va, stop_dist_atr, rr_ratio, vol_slope_excursion, vol_at_extreme, vol_reentry_bar, delta_excursion, delta_reentry, absorption_score |
| 4 | va_type, minutes_since_open, bars_in_profile, open_vs_on_va, va_width_atr, excursion_depth, excursion_minutes, reentry_close_pos, va_shift, in_other_va, stop_dist_atr, rr_ratio, vol_slope_excursion, vol_at_extreme, vol_reentry_bar, delta_excursion, delta_reentry, absorption_score |

## Figure

- `reports/figures_1c_B/equity_oos.png`
- `reports/figures_1c_B/calibration.png`
- `reports/figures_1c_B/shap_summary.png`
- `reports/figures_1c_B/shap_dependence_vol_slope_excursion.png`
- `reports/figures_1c_B/shap_dependence_vol_reentry_bar.png`
- `reports/figures_1c_B/shap_dependence_rr_ratio.png`
- `reports/figures_1c_B/shap_dependence_delta_excursion.png`
- `reports/figures_1c_B/shap_dependence_absorption_score.png`
- `reports/figures_1c_B/shap_dependence_delta_reentry.png`
