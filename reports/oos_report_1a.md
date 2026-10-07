# Report OOS — Milestone 1a (senza order flow)

Generato il 2026-09-21 · config `0c95cac61e06` · commit `c3e4630` · feature `1a` · cassaforte dal 2026-03-20 **mai usata**

Nota: **C in 1a ha 2 regole** (`vol_slope_excursion < 0` e `vol_reentry_bar > 1`); la terza regola della spec (`delta_excursion > 0`) richiede i tick e arriva in 1b. Tutte le cifre sono calcolate da `data/model/predictions_1a.parquet`; CI 95% block-bootstrap per giorno.

## Criteri pre-registrati (spec §11.1)

| # | criterio | esito | evidenza |
|---|---|---|---|
| 1 | A: R medio/trade > 0 dopo costi, CI esclude 0, a 1 tick; ancora > 0 a 2 tick | FAIL | R medio 0.009 [-0.114, 0.135]; a 2 tick -0.009 |
| 2 | (A − B0), (A − C), (A − C-opt) > 0 su R medio/trade, CI esclude 0 | FAIL | A−B0: [-0.110, 0.141]; A−C: [-0.182, 0.194]; A−Copt: [-0.267, 0.150] |
| 3 | segno positivo di (A − B0) in ≥ 4 finestre su 5 | FAIL | 2/5 finestre: 0: +0.057, 1: -0.027, 2: -0.009, 3: +0.324, 4: -0.059 |
| 4 | shuffle test AUC ∈ [0.45, 0.55]; A batte il solo-contesto su Brier | PASS | shuffle AUC [0.517, 0.492, 0.516, 0.495, 0.479]; Brier media-per-fold A 0.1816 vs contesto 0.1820 (A meglio in 2/5 finestre) — PASS alla lettera del criterio; pooled A 0.1820 = prior geometrico 0.1820: NON confermato |
| 5 | A prende ≥ 300 trade OOS | PASS | 591 trade |

**2/5 criteri superati.** Il modello 1a non supera i criteri: il report dice quali. Prossimo passo secondo la regola dei tre sguardi.


## Come leggere questo report

- L'AUC di A (0.7555, pooled) è quasi tutta geometria dello stop/target, non skill del modello: il prior a zero parametri `p = 1/(1+rr_ratio)` fa 0.7569 — la differenza è nel rumore.
- La clausola Brier del criterio 4 è una parità, non una vittoria di A: Brier medio-per-fold A 0.1816 vs contesto 0.1820 (A meglio in 2/5 finestre) — PASS significa "non falsificato alla lettera del criterio", non che A batte il prior: pooled A 0.1820 = prior geometrico 0.1820.
- L'R medio positivo di A è portato da pochi trade: nello stress che toglie il 5% dei trade migliori, R medio crolla a -0.269; e il segno di (A − B0) cambia da finestra a finestra (0: +0.057, 1: -0.027, 2: -0.009, 3: +0.324, 4: -0.059).
- Sharpe giornaliero e mesi negativi/totali sono calcolati su TUTTI i giorni/mesi di test, non solo su quelli con trade: un giorno o un mese senza trade pesa 0, non manca dal conteggio (vedi nota I1 della review).
- Lo stress `slip_N` applica N tick di slippage per lato sull'ingresso e su **ogni** uscita a mercato (stop, time-stop) — più severo del solo "sugli stop" della bozza; il target resta un ordine limite (nessuno slippage). Un'uscita per gap-through-stop nella stessa barra è valorizzata al livello dello stop (ottimistico); `slip_3` è la proxy più vicina a un mercato che apre in gap.
- C-opt cerca le due soglie a griglia sul training di ogni finestra (in-sample per quella finestra): è un limite superiore ottimistico su quanto le regole potrebbero rendere, non una strategia eseguibile fuori dal backtest.
- La riga "A su MNQ (÷10)" è una divisione ingenua per 10: commissioni e tick di MNQ non scalano linearmente con quelli di NQ, quindi la riga sottostima i costi reali su MNQ.

## Le quattro colonne (OOS aggregato, 5 finestre)

| strategia | n | trades_per_day | win_rate | mean_R | ci | profit_factor | expectancy_usd | max_dd_R | max_dd_usd | sharpe_daily | months |
|---|---|---|---|---|---|---|---|---|---|---|---|
| A | 591 | 0.967 | 0.437 | 0.009 | [-0.114, 0.135] | 0.957 | -18.257 | 45.939 | 37160.000 | -0.261 | 14/30 |
| B0 | 2658 | 4.350 | 0.418 | -0.005 | [-0.071, 0.068] | 0.948 | -22.613 | 98.875 | 133655.000 | -0.679 | 18/30 |
| C | 208 | 0.340 | 0.519 | 0.005 | [-0.138, 0.153] | 0.988 | -6.538 | 13.036 | 20985.000 | -0.046 | 14/30 |
| Copt | 109 | 0.178 | 0.596 | 0.067 | [-0.105, 0.241] | 1.090 | 45.138 | 7.722 | 10860.000 | 0.232 | 15/30 |
| A su MNQ (÷10) | 591 | 0.967 | 0.437 | 0.009 |  | 0.957 | -1.826 | 45.939 | 3716.000 | -0.261 | 14/30 |

### Differenze su R medio/trade (CI 95%)

| confronto | stima | CI |
|---|---|---|
| A − B0 | 0.014 | [-0.110, 0.141] |
| A − C | 0.005 | [-0.182, 0.194] |
| A − Copt | -0.057 | [-0.267, 0.150] |

### Segno di (A − B0) per finestra

| finestra | test | A − B0 (R medio) |
|---|---|---|
| 0 | 2023-10-02..2024-03-28 | 0.057 |
| 1 | 2024-04-01..2024-09-30 | -0.027 |
| 2 | 2024-10-01..2025-03-31 | -0.009 |
| 3 | 2025-04-01..2025-09-30 | 0.324 |
| 4 | 2025-10-01..2026-03-19 | -0.059 |

### Motore: esiti per strategia

| strategia | taken | duplicate | skipped_in_position | not_taken |
|---|---|---|---|---|
| A | 591 | 14 | 48 | 4024 |
| B0 | 2658 | 227 | 1792 | 0 |
| C | 208 | 26 | 7 | 4436 |
| Copt | 109 | 19 | 5 | 4544 |

## Stress su A (decisioni fisse a 1 tick, P&L rivalutato; slippage per lato: ingresso e ogni uscita a mercato; target = limite)

| scenario | n | win rate | R medio | PF | expectancy $ | max DD R |
|---|---|---|---|---|---|---|
| base | 591 | 0.437 | 0.009 | 0.957 | -18.257 | 45.939 |
| slip_2 | 591 | 0.437 | -0.009 | 0.939 | -26.134 | 48.917 |
| slip_3 | 591 | 0.437 | -0.026 | 0.922 | -34.010 | 51.768 |
| comm_x2 | 591 | 0.437 | -0.002 | 0.945 | -23.257 | 48.325 |
| drop_top_5pct | 561 | 0.406 | -0.269 | 0.767 | -104.091 | 151.186 |

## Controlli anti-inganno per finestra

| finestra | test | AUC A | Brier A | Brier contesto | AUC shuffle | AUC prior | Brier prior | n feature A | best iter | C-opt |
|---|---|---|---|---|---|---|---|---|---|---|
| 0 | 2023-10-02..2024-03-28 | 0.763 | 0.188 | 0.189 | 0.517 | 0.759 | 0.188 | 17 | 100 | {'vol_slope_excursion_max': 0.05, 'vol_reentry_bar_min': 1.2} |
| 1 | 2024-04-01..2024-09-30 | 0.751 | 0.192 | 0.192 | 0.492 | 0.758 | 0.189 | 16 | 119 | {'vol_slope_excursion_max': 0.05, 'vol_reentry_bar_min': 1.2} |
| 2 | 2024-10-01..2025-03-31 | 0.779 | 0.165 | 0.164 | 0.516 | 0.777 | 0.170 | 19 | 280 | {'vol_slope_excursion_max': 0.0, 'vol_reentry_bar_min': 1.2} |
| 3 | 2025-04-01..2025-09-30 | 0.756 | 0.188 | 0.191 | 0.495 | 0.746 | 0.186 | 15 | 89 | {'vol_slope_excursion_max': 0.0, 'vol_reentry_bar_min': 1.2} |
| 4 | 2025-10-01..2026-03-19 | 0.749 | 0.174 | 0.173 | 0.479 | 0.744 | 0.176 | 15 | 175 | {'vol_slope_excursion_max': 0.0, 'vol_reentry_bar_min': 1.2} |

Prior geometrico p = 1/(1+rr): AUC 0.7569 vs A 0.7555 (pooled); Brier prior 0.1820 vs A 0.1820 (pooled); Brier tasso base 0.2238


## Calibrazione (decili di p, tutti gli eventi di test)

| decile | p media | freq. osservata | n |
|---|---|---|---|
| 0 | 0.040 | 0.081 | 578 |
| 1 | 0.122 | 0.117 | 489 |
| 2 | 0.171 | 0.186 | 436 |
| 3 | 0.213 | 0.220 | 395 |
| 4 | 0.275 | 0.283 | 477 |
| 5 | 0.339 | 0.380 | 498 |
| 6 | 0.383 | 0.422 | 410 |
| 7 | 0.470 | 0.432 | 461 |
| 8 | 0.561 | 0.532 | 489 |
| 9 | 0.853 | 0.795 | 444 |

## Decomposizione dei trade A (solo lettura, mai per selezionare)


**per va_type**

| gruppo | n | win rate | R medio |
|---|---|---|---|
| DEV | 443 | 0.411 | -0.037 |
| ON | 148 | 0.514 | 0.146 |

**per side**

| gruppo | n | win rate | R medio |
|---|---|---|---|
| long | 299 | 0.455 | -0.069 |
| short | 292 | 0.418 | 0.089 |

**per fascia**

| gruppo | n | win rate | R medio |
|---|---|---|---|
| 09:30-10:30 | 342 | 0.482 | -0.035 |
| 10:30-12:00 | 156 | 0.378 | 0.076 |
| 12:00-14:00 | 73 | 0.329 | 0.023 |
| 14:00-15:30 | 20 | 0.500 | 0.191 |

## Feature selezionate per finestra

| finestra | feature |
|---|---|
| 0 | va_type, minutes_since_open, bars_in_profile, open_vs_on_va, va_width_atr, excursion_depth, excursion_minutes, reentry_close_pos, va_shift, in_other_va, stop_dist_atr, rr_ratio, vol_slope_excursion, vol_at_extreme, vol_reentry_bar, bars_outside, poc_pos |
| 1 | va_type, minutes_since_open, bars_in_profile, open_vs_on_va, va_width_atr, excursion_depth, excursion_minutes, reentry_close_pos, va_shift, in_other_va, stop_dist_atr, rr_ratio, vol_slope_excursion, vol_at_extreme, vol_reentry_bar, rel_vol_session |
| 2 | va_type, minutes_since_open, bars_in_profile, open_vs_on_va, va_width_atr, excursion_depth, excursion_minutes, reentry_close_pos, va_shift, in_other_va, stop_dist_atr, rr_ratio, vol_slope_excursion, vol_at_extreme, vol_reentry_bar, bars_outside, dist_other_near_atr, overlap_on_dev, vol_excursion_vs_pre |
| 3 | va_type, minutes_since_open, bars_in_profile, open_vs_on_va, va_width_atr, excursion_depth, excursion_minutes, reentry_close_pos, va_shift, in_other_va, stop_dist_atr, rr_ratio, vol_slope_excursion, vol_at_extreme, vol_reentry_bar |
| 4 | va_type, minutes_since_open, bars_in_profile, open_vs_on_va, va_width_atr, excursion_depth, excursion_minutes, reentry_close_pos, va_shift, in_other_va, stop_dist_atr, rr_ratio, vol_slope_excursion, vol_at_extreme, vol_reentry_bar |

## Figure

- `reports/figures_1a/equity_oos.png`
- `reports/figures_1a/calibration.png`
- `reports/figures_1a/shap_summary.png`
- `reports/figures_1a/shap_dependence_vol_slope_excursion.png`
- `reports/figures_1a/shap_dependence_vol_reentry_bar.png`
- `reports/figures_1a/shap_dependence_rr_ratio.png`
