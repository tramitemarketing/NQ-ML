# Report OOS — 1c_A

Generato il 2026-09-22 · config `2ee491362e71` · commit `18a2b44` · feature `1c_A` · cassaforte dal 2026-03-20 **mai usata**

Nota: **C in 1c_A ha 2 regole (le stesse della 1a)** (`vol_slope_excursion < 0` e `vol_reentry_bar > 1`); la terza regola della spec (`delta_excursion > 0`) richiede i tick e arriva in 1b. Tutte le cifre sono calcolate da `data/model/predictions_1c_A.parquet`; CI 95% block-bootstrap per giorno.

## Criteri pre-registrati (spec §11.1)

| # | criterio | esito | evidenza |
|---|---|---|---|
| 1 | A: R medio/trade > 0 dopo costi, CI esclude 0, a 1 tick; ancora > 0 a 2 tick | FAIL | R medio -0.122 [-0.267, 0.024]; a 2 tick -0.136 |
| 2 | (A − B0), (A − C), (A − C-opt) > 0 su R medio/trade, CI esclude 0 | FAIL | A−B0: [-0.266, 0.026]; A−C: [-0.317, 0.080]; A−Copt: [-0.450, -0.010] |
| 3 | segno positivo di (A − B0) in ≥ 4 finestre su 5 | FAIL | 1/5 finestre: 0: -0.052, 1: -0.137, 2: -0.074, 3: +nan, 4: +0.010 |
| 4 | shuffle test AUC ∈ [0.45, 0.55]; A batte il solo-contesto su Brier | FAIL | shuffle AUC [0.506, 0.502, 0.475, 0.502, 0.521]; Brier(A) − Brier(contesto) per evento (bootstrap appaiato per giorno): +0.0011 [-0.0001, +0.0023] — A peggio del solo-contesto (Brier medio-per-fold a vs b: A 0.1793, contesto 0.1782); pooled A 0.1797 vs prior geometrico 0.1820 |
| 5 | A prende ≥ 300 trade OOS | PASS | 326 trade |

**1/5 criteri superati.** Il modello 1c_A non supera i criteri: il report dice quali. Prossimo passo secondo la regola dei tre sguardi. (questo è il terzo: dal prossimo serve l'ipotesi pre-registrata)


## Come leggere questo report

- L'AUC di A (0.7617, pooled) è quasi tutta geometria dello stop/target, non skill del modello: il prior a zero parametri `p = 1/(1+rr_ratio)` fa 0.7569 — la differenza è nel rumore.
- La clausola Brier del criterio 4 (spec §11.1 «dalla 1b»): bootstrap appaiato per evento di Brier(A) − Brier(contesto) = +0.0011 [-0.0001, +0.0023] — A peggio del solo-contesto (Brier medio-per-fold a vs b: A 0.1793, contesto 0.1782, A meglio in 1/5 finestre); pooled A 0.1797 vs prior geometrico 0.1820.
- L'R medio di A è negativo (-0.122): nello stress che toglie il 5% dei trade migliori, R medio scende a -0.320; e il segno di (A − B0) cambia da finestra a finestra (0: -0.052, 1: -0.137, 2: -0.074, 3: +nan, 4: +0.010).
- Sharpe giornaliero e mesi negativi/totali sono calcolati su TUTTI i giorni/mesi di test, non solo su quelli con trade: un giorno o un mese senza trade pesa 0, non manca dal conteggio (vedi nota I1 della review).
- Lo stress `slip_N` applica N tick di slippage per lato sull'ingresso e su **ogni** uscita a mercato (stop, time-stop) — più severo del solo "sugli stop" della bozza; il target resta un ordine limite (nessuno slippage). Un'uscita per gap-through-stop nella stessa barra è valorizzata al livello dello stop (ottimistico); `slip_3` è la proxy più vicina a un mercato che apre in gap.
- C-opt cerca le due soglie a griglia sul training di ogni finestra (in-sample per quella finestra): è un limite superiore ottimistico su quanto le regole potrebbero rendere, non una strategia eseguibile fuori dal backtest.
- La riga "A su MNQ (÷10)" è una divisione ingenua per 10: commissioni e tick di MNQ non scalano linearmente con quelli di NQ, quindi la riga sottostima i costi reali su MNQ.

## Le quattro colonne (OOS aggregato, 5 finestre)

| strategia | n | trades_per_day | win_rate | mean_R | ci | profit_factor | expectancy_usd | max_dd_R | max_dd_usd | sharpe_daily | months |
|---|---|---|---|---|---|---|---|---|---|---|---|
| A | 326 | 0.534 | 0.380 | -0.122 | [-0.267, 0.024] | 0.883 | -50.445 | 58.929 | 38350.000 | -0.585 | 12/30 |
| B0 | 2680 | 4.386 | 0.423 | -0.003 | [-0.069, 0.069] | 0.952 | -20.584 | 96.992 | 139030.000 | -0.628 | 18/30 |
| C | 208 | 0.340 | 0.519 | -0.004 | [-0.145, 0.142] | 0.981 | -10.529 | 12.768 | 20985.000 | -0.073 | 15/30 |
| Copt | 109 | 0.178 | 0.624 | 0.110 | [-0.061, 0.285] | 1.214 | 101.376 | 5.580 | 9275.000 | 0.522 | 15/30 |
| A su MNQ (÷10) | 326 | 0.534 | 0.380 | -0.122 |  | 0.883 | -5.044 | 58.929 | 3835.000 | -0.585 | 12/30 |

### Differenze su R medio/trade (CI 95%)

| confronto | stima | CI |
|---|---|---|
| A − B0 | -0.119 | [-0.266, 0.026] |
| A − C | -0.117 | [-0.317, 0.080] |
| A − Copt | -0.231 | [-0.450, -0.010] |

### Segno di (A − B0) per finestra

| finestra | test | A − B0 (R medio) |
|---|---|---|
| 0 | 2023-10-02..2024-03-28 | -0.052 |
| 1 | 2024-04-01..2024-09-30 | -0.137 |
| 2 | 2024-10-01..2025-03-31 | -0.074 |
| 3 | 2025-04-01..2025-09-30 | n/d |
| 4 | 2025-10-01..2026-03-19 | 0.010 |

### Motore: esiti per strategia

| strategia | taken | duplicate | skipped_in_position | not_taken |
|---|---|---|---|---|
| A | 326 | 4 | 50 | 4297 |
| B0 | 2680 | 230 | 1767 | 0 |
| C | 208 | 26 | 7 | 4436 |
| Copt | 109 | 19 | 5 | 4544 |

## Stress su A (decisioni fisse a 1 tick, P&L rivalutato; slippage per lato: ingresso e ogni uscita a mercato; target = limite)

| scenario | n | win rate | R medio | PF | expectancy $ | max DD R |
|---|---|---|---|---|---|---|
| base | 326 | 0.380 | -0.122 | 0.883 | -50.445 | 58.929 |
| slip_2 | 326 | 0.380 | -0.136 | 0.866 | -58.620 | 62.499 |
| slip_3 | 326 | 0.380 | -0.150 | 0.850 | -66.794 | 65.971 |
| comm_x2 | 326 | 0.380 | -0.132 | 0.873 | -55.445 | 61.580 |
| drop_top_5pct | 309 | 0.346 | -0.320 | 0.661 | -154.709 | 103.177 |

## Controlli anti-inganno per finestra

| finestra | test | AUC A | Brier A | Brier contesto | AUC shuffle | AUC prior | Brier prior | n feature A | best iter | C-opt |
|---|---|---|---|---|---|---|---|---|---|---|
| 0 | 2023-10-02..2024-03-28 | 0.754 | 0.189 | 0.188 | 0.506 | 0.759 | 0.188 | 15 | 326 | [{'feature': 'vol_slope_excursion', 'op': '<', 'value': 0.05, 'values': [-0.05, -0.02, 0.0, 0.02, 0.05]}, {'feature': 'vol_reentry_bar', 'op': '>', 'value': 1.2, 'values': [0.8, 1.0, 1.2, 1.5]}] |
| 1 | 2024-04-01..2024-09-30 | 0.762 | 0.186 | 0.184 | 0.502 | 0.758 | 0.189 | 15 | 27 | [{'feature': 'vol_slope_excursion', 'op': '<', 'value': 0.05, 'values': [-0.05, -0.02, 0.0, 0.02, 0.05]}, {'feature': 'vol_reentry_bar', 'op': '>', 'value': 1.2, 'values': [0.8, 1.0, 1.2, 1.5]}] |
| 2 | 2024-10-01..2025-03-31 | 0.777 | 0.168 | 0.164 | 0.475 | 0.777 | 0.170 | 15 | 240 | [{'feature': 'vol_slope_excursion', 'op': '<', 'value': 0.0, 'values': [-0.05, -0.02, 0.0, 0.02, 0.05]}, {'feature': 'vol_reentry_bar', 'op': '>', 'value': 1.2, 'values': [0.8, 1.0, 1.2, 1.5]}] |
| 3 | 2025-04-01..2025-09-30 | 0.761 | 0.182 | 0.183 | 0.502 | 0.746 | 0.186 | 15 | 30 | [{'feature': 'vol_slope_excursion', 'op': '<', 'value': 0.0, 'values': [-0.05, -0.02, 0.0, 0.02, 0.05]}, {'feature': 'vol_reentry_bar', 'op': '>', 'value': 1.2, 'values': [0.8, 1.0, 1.2, 1.5]}] |
| 4 | 2025-10-01..2026-03-19 | 0.757 | 0.171 | 0.171 | 0.521 | 0.744 | 0.176 | 15 | 98 | [{'feature': 'vol_slope_excursion', 'op': '<', 'value': 0.0, 'values': [-0.05, -0.02, 0.0, 0.02, 0.05]}, {'feature': 'vol_reentry_bar', 'op': '>', 'value': 1.2, 'values': [0.8, 1.0, 1.2, 1.5]}] |

Prior geometrico p = 1/(1+rr): AUC 0.7569 vs A 0.7617 (pooled); Brier prior 0.1820 vs A 0.1797 (pooled); Brier tasso base 0.2238 · L2 (prior calibrato sul training) 0.1804


## Calibrazione (decili di p, tutti gli eventi di test)


Modalità offset (§12-ter): nessun calibratore post hoc, validazione intera per early stopping.

| decile | p media | freq. osservata | n |
|---|---|---|---|
| 0 | 0.052 | 0.056 | 468 |
| 1 | 0.122 | 0.139 | 468 |
| 2 | 0.176 | 0.152 | 467 |
| 3 | 0.230 | 0.220 | 468 |
| 4 | 0.289 | 0.282 | 468 |
| 5 | 0.351 | 0.315 | 467 |
| 6 | 0.418 | 0.423 | 468 |
| 7 | 0.496 | 0.471 | 467 |
| 8 | 0.607 | 0.526 | 468 |
| 9 | 0.808 | 0.797 | 468 |

## Decomposizione dei trade A (solo lettura, mai per selezionare)


**per va_type**

| gruppo | n | win rate | R medio |
|---|---|---|---|
| DEV | 227 | 0.357 | -0.138 |
| ON | 99 | 0.434 | -0.085 |

**per side**

| gruppo | n | win rate | R medio |
|---|---|---|---|
| long | 173 | 0.410 | -0.039 |
| short | 153 | 0.346 | -0.215 |

**per fascia**

| gruppo | n | win rate | R medio |
|---|---|---|---|
| 09:30-10:30 | 191 | 0.471 | 0.022 |
| 10:30-12:00 | 87 | 0.287 | -0.244 |
| 12:00-14:00 | 34 | 0.235 | -0.289 |
| 14:00-15:30 | 14 | 0.071 | -0.917 |

## Feature selezionate per finestra

| finestra | feature |
|---|---|
| 0 | va_type, minutes_since_open, bars_in_profile, open_vs_on_va, va_width_atr, excursion_depth, excursion_minutes, reentry_close_pos, va_shift, in_other_va, stop_dist_atr, rr_ratio, vol_slope_excursion, vol_at_extreme, vol_reentry_bar |
| 1 | va_type, minutes_since_open, bars_in_profile, open_vs_on_va, va_width_atr, excursion_depth, excursion_minutes, reentry_close_pos, va_shift, in_other_va, stop_dist_atr, rr_ratio, vol_slope_excursion, vol_at_extreme, vol_reentry_bar |
| 2 | va_type, minutes_since_open, bars_in_profile, open_vs_on_va, va_width_atr, excursion_depth, excursion_minutes, reentry_close_pos, va_shift, in_other_va, stop_dist_atr, rr_ratio, vol_slope_excursion, vol_at_extreme, vol_reentry_bar |
| 3 | va_type, minutes_since_open, bars_in_profile, open_vs_on_va, va_width_atr, excursion_depth, excursion_minutes, reentry_close_pos, va_shift, in_other_va, stop_dist_atr, rr_ratio, vol_slope_excursion, vol_at_extreme, vol_reentry_bar |
| 4 | va_type, minutes_since_open, bars_in_profile, open_vs_on_va, va_width_atr, excursion_depth, excursion_minutes, reentry_close_pos, va_shift, in_other_va, stop_dist_atr, rr_ratio, vol_slope_excursion, vol_at_extreme, vol_reentry_bar |

## Figure

- `reports/figures_1c_A/equity_oos.png`
- `reports/figures_1c_A/calibration.png`
- `reports/figures_1c_A/shap_summary.png`
- `reports/figures_1c_A/shap_dependence_vol_slope_excursion.png`
- `reports/figures_1c_A/shap_dependence_vol_reentry_bar.png`
- `reports/figures_1c_A/shap_dependence_rr_ratio.png`
