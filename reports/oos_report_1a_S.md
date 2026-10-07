# Report OOS — 1a_S

Generato il 2026-09-21 · config `c75de95ae278` · commit `b2be4fe` · feature `1a` · cassaforte dal 2026-03-20 **mai usata**

Nota: **C in 1a ha 2 regole** (`vol_slope_excursion < 0` e `vol_reentry_bar > 1`); la terza regola della spec (`delta_excursion > 0`) richiede i tick e arriva in 1b. Tutte le cifre sono calcolate da `data/model/predictions_1a_S.parquet`; CI 95% block-bootstrap per giorno.

## Criteri pre-registrati (spec §11.1)

| # | criterio | esito | evidenza |
|---|---|---|---|
| 1 | A: R medio/trade > 0 dopo costi, CI esclude 0, a 1 tick; ancora > 0 a 2 tick | FAIL | R medio -0.047 [-0.169, 0.076]; a 2 tick -0.063 |
| 2 | (A − B0), (A − C), (A − C-opt) > 0 su R medio/trade, CI esclude 0 | FAIL | A−B0: [-0.183, 0.091]; A−C: [-0.481, 0.024]; A−Copt: [-0.297, 0.038] |
| 3 | segno positivo di (A − B0) in ≥ 4 finestre su 5 | FAIL | 2/5 finestre: 0: -0.069, 1: -0.125, 2: +0.089, 3: +0.070, 4: -0.270 |
| 4 | shuffle test AUC ∈ [0.45, 0.55]; A batte il solo-contesto su Brier | FAIL | shuffle AUC [0.641, 0.531, 0.477, 0.615, 0.49]; Brier(A) − Brier(contesto) per evento (bootstrap appaiato per giorno): +0.0054 [+0.0000, +0.0107] — A peggio del solo-contesto (Brier medio-per-fold a vs b: A 0.1874, contesto 0.1826); pooled A 0.1881 vs prior geometrico 0.1777 |
| 5 | A prende ≥ 300 trade OOS | PASS | 453 trade |

**1/5 criteri superati.** Il modello 1a_S non supera i criteri: il report dice quali. Prossimo passo secondo la regola dei tre sguardi.


## Note sulla milestone

# Note sulla milestone 1b-S (order flow su giorni campionati)

- **Shuffle AUC**: seed 0 fuori banda nelle pieghe 0 e 3 per entrambe le esecuzioni (1a_S 0.641/0.615; 1b 0.608/0.610). Rimisurato con 5 seed su 1a_S: piega 0 con vincoli monotoni [0.641, 0.399, 0.453, 0.607, 0.545] media 0.529, senza vincoli media 0.475; piega 3 con vincoli [0.615, 0.442, 0.517, 0.602, 0.434] media 0.522, senza 0.503. Distribuzione simmetrica attorno a 0.5 → non è leakage: test a seed singolo poco potente su n_fit 1.421, con un +0.03 strutturale dovuto ai vincoli monotoni (`rr_ratio: −1` ordina come il prior anche su label mescolate). Ipotesi per lo sguardo #3 (da pre-registrare, non applicata): shuffle multi-seed o senza vincoli.
- **Giorno degraded**: 2026-03-16 marcato "degraded" da Databento (qualità del feed ridotta) nell'ultima finestra di test (piega 4).
- **Quota**: 0.45 di config, 0.4450 effettiva (498/1119, arrotondamento mensile); soglia del criterio (iv) = 300 × 0.445 = 133.5 → 134.
- **Calibrazione**: isotonica su 93–112 punti per piega (metà della validazione): `p` assume 14–46 valori distinti per piega (misurato nella review finale); la calibrazione costa circa +0.007/+0.008 di Brier rispetto alle probabilità grezze dei booster (misurato: Brier grezzo 1b 0.1844, 1a_S 0.1803).
- **Griglia del bootstrap**: la CI del criterio (iii) è invariante alla griglia dei giorni del bootstrap (611 giorni di test / 272 campionati / 235 con trade: estremi che si muovono ≤ 0.003, misurato nella review finale).
- **Conseguenza della regola §12-bis**: (i) e (ii) FAIL → **non si acquistano le finestre restanti**; lo sguardo #3 non è innescato da questa milestone.


## Come leggere questo report

- L'AUC di A (0.7485, pooled) è quasi tutta geometria dello stop/target, non skill del modello: il prior a zero parametri `p = 1/(1+rr_ratio)` fa 0.7701 — la differenza è nel rumore.
- La clausola Brier del criterio 4 (spec §11.1 «dalla 1b»): bootstrap appaiato per evento di Brier(A) − Brier(contesto) = +0.0054 [+0.0000, +0.0107] — A peggio del solo-contesto (Brier medio-per-fold a vs b: A 0.1874, contesto 0.1826, A meglio in 1/5 finestre); pooled A 0.1881 vs prior geometrico 0.1777.
- L'R medio di A è negativo (-0.047): nello stress che toglie il 5% dei trade migliori, R medio scende a -0.267; e il segno di (A − B0) cambia da finestra a finestra (0: -0.069, 1: -0.125, 2: +0.089, 3: +0.070, 4: -0.270).
- Sharpe giornaliero e mesi negativi/totali sono calcolati su TUTTI i giorni/mesi di test, non solo su quelli con trade: un giorno o un mese senza trade pesa 0, non manca dal conteggio (vedi nota I1 della review).
- Lo stress `slip_N` applica N tick di slippage per lato sull'ingresso e su **ogni** uscita a mercato (stop, time-stop) — più severo del solo "sugli stop" della bozza; il target resta un ordine limite (nessuno slippage). Un'uscita per gap-through-stop nella stessa barra è valorizzata al livello dello stop (ottimistico); `slip_3` è la proxy più vicina a un mercato che apre in gap.
- C-opt cerca le due soglie a griglia sul training di ogni finestra (in-sample per quella finestra): è un limite superiore ottimistico su quanto le regole potrebbero rendere, non una strategia eseguibile fuori dal backtest.
- La riga "A su MNQ (÷10)" è una divisione ingenua per 10: commissioni e tick di MNQ non scalano linearmente con quelli di NQ, quindi la riga sottostima i costi reali su MNQ.
- Esecuzione su un sottoinsieme campionato (quota effettiva 0.4450 dei giorni di popolazione): solo quei giorni possono avere trade, quindi `trades_per_day` e `pct_days_active` sono diluiti di circa 1/0.445 ≈ 2.25× rispetto a un'esecuzione su tutti i giorni, e lo Sharpe giornaliero di circa √0.445 ≈ 0.67× rispetto a un'esecuzione sull'intera popolazione.

## Le quattro colonne (OOS aggregato, 5 finestre)

| strategia | n | trades_per_day | win_rate | mean_R | ci | profit_factor | expectancy_usd | max_dd_R | max_dd_usd | sharpe_daily | months |
|---|---|---|---|---|---|---|---|---|---|---|---|
| A | 453 | 0.741 | 0.422 | -0.047 | [-0.169, 0.076] | 0.984 | -6.545 | 40.533 | 22245.000 | -0.082 | 14/30 |
| B0 | 1191 | 1.949 | 0.420 | -0.005 | [-0.100, 0.104] | 0.988 | -5.155 | 71.513 | 34685.000 | -0.101 | 13/30 |
| C | 86 | 0.141 | 0.558 | 0.177 | [-0.057, 0.421] | 1.366 | 176.279 | 4.047 | 5215.000 | 0.836 | 11/30 |
| Copt | 258 | 0.422 | 0.535 | 0.084 | [-0.060, 0.228] | 1.188 | 89.283 | 15.406 | 12345.000 | 0.747 | 13/30 |
| A su MNQ (÷10) | 453 | 0.741 | 0.422 | -0.047 |  | 0.984 | -0.655 | 40.533 | 2224.500 | -0.082 | 14/30 |

### Differenze su R medio/trade (CI 95%)

| confronto | stima | CI |
|---|---|---|
| A − B0 | -0.042 | [-0.183, 0.091] |
| A − C | -0.225 | [-0.481, 0.024] |
| A − Copt | -0.132 | [-0.297, 0.038] |

### Segno di (A − B0) per finestra

| finestra | test | A − B0 (R medio) |
|---|---|---|
| 0 | 2023-10-02..2024-03-28 | -0.069 |
| 1 | 2024-04-01..2024-09-30 | -0.125 |
| 2 | 2024-10-01..2025-03-31 | 0.089 |
| 3 | 2025-04-01..2025-09-30 | 0.070 |
| 4 | 2025-10-01..2026-03-19 | -0.270 |

### Motore: esiti per strategia

| strategia | taken | duplicate | skipped_in_position | not_taken |
|---|---|---|---|---|
| A | 453 | 16 | 78 | 1512 |
| B0 | 1191 | 83 | 785 | 0 |
| C | 86 | 12 | 2 | 1959 |
| Copt | 258 | 30 | 27 | 1744 |

## Stress su A (decisioni fisse a 1 tick, P&L rivalutato; slippage per lato: ingresso e ogni uscita a mercato; target = limite)

| scenario | n | win rate | R medio | PF | expectancy $ | max DD R |
|---|---|---|---|---|---|---|
| base | 453 | 0.422 | -0.047 | 0.984 | -6.545 | 40.533 |
| slip_2 | 453 | 0.422 | -0.063 | 0.966 | -14.558 | 44.452 |
| slip_3 | 453 | 0.422 | -0.077 | 0.948 | -22.572 | 48.234 |
| comm_x2 | 453 | 0.422 | -0.058 | 0.973 | -11.545 | 43.421 |
| drop_top_5pct | 430 | 0.391 | -0.267 | 0.789 | -93.651 | 116.739 |

## Controlli anti-inganno per finestra

| finestra | test | AUC A | Brier A | Brier contesto | AUC shuffle | AUC prior | Brier prior | n feature A | best iter | C-opt |
|---|---|---|---|---|---|---|---|---|---|---|
| 0 | 2023-10-02..2024-03-28 | 0.743 | 0.190 | 0.187 | 0.641 | 0.767 | 0.183 | 15 | 321 | [{'feature': 'vol_slope_excursion', 'op': '<', 'value': 0.0, 'values': [-0.05, -0.02, 0.0, 0.02, 0.05]}, {'feature': 'vol_reentry_bar', 'op': '>', 'value': 0.8, 'values': [0.8, 1.0, 1.2, 1.5]}] |
| 1 | 2024-04-01..2024-09-30 | 0.748 | 0.191 | 0.181 | 0.531 | 0.781 | 0.178 | 18 | 422 | [{'feature': 'vol_slope_excursion', 'op': '<', 'value': 0.0, 'values': [-0.05, -0.02, 0.0, 0.02, 0.05]}, {'feature': 'vol_reentry_bar', 'op': '>', 'value': 0.8, 'values': [0.8, 1.0, 1.2, 1.5]}] |
| 2 | 2024-10-01..2025-03-31 | 0.758 | 0.191 | 0.179 | 0.477 | 0.789 | 0.171 | 18 | 186 | [{'feature': 'vol_slope_excursion', 'op': '<', 'value': 0.0, 'values': [-0.05, -0.02, 0.0, 0.02, 0.05]}, {'feature': 'vol_reentry_bar', 'op': '>', 'value': 0.8, 'values': [0.8, 1.0, 1.2, 1.5]}] |
| 3 | 2025-04-01..2025-09-30 | 0.739 | 0.193 | 0.188 | 0.615 | 0.754 | 0.180 | 17 | 445 | [{'feature': 'vol_slope_excursion', 'op': '<', 'value': 0.0, 'values': [-0.05, -0.02, 0.0, 0.02, 0.05]}, {'feature': 'vol_reentry_bar', 'op': '>', 'value': 0.8, 'values': [0.8, 1.0, 1.2, 1.5]}] |
| 4 | 2025-10-01..2026-03-19 | 0.745 | 0.173 | 0.178 | 0.490 | 0.750 | 0.176 | 15 | 101 | [{'feature': 'vol_slope_excursion', 'op': '<', 'value': -0.02, 'values': [-0.05, -0.02, 0.0, 0.02, 0.05]}, {'feature': 'vol_reentry_bar', 'op': '>', 'value': 0.8, 'values': [0.8, 1.0, 1.2, 1.5]}] |

Prior geometrico p = 1/(1+rr): AUC 0.7701 vs A 0.7485 (pooled); Brier prior 0.1777 vs A 0.1881 (pooled); Brier tasso base 0.2241


## Calibrazione (decili di p, tutti gli eventi di test)

| decile | p media | freq. osservata | n |
|---|---|---|---|
| 0 | 0.020 | 0.089 | 415 |
| 1 | 0.200 | 0.222 | 248 |
| 2 | 0.233 | 0.237 | 262 |
| 3 | 0.250 | 0.273 | 231 |
| 4 | 0.345 | 0.455 | 101 |
| 5 | 0.448 | 0.357 | 185 |
| 6 | 0.541 | 0.492 | 242 |
| 7 | 0.683 | 0.610 | 172 |
| 8 | 0.850 | 0.714 | 203 |

## Decomposizione dei trade A (solo lettura, mai per selezionare)


**per va_type**

| gruppo | n | win rate | R medio |
|---|---|---|---|
| DEV | 315 | 0.406 | -0.028 |
| ON | 138 | 0.457 | -0.092 |

**per side**

| gruppo | n | win rate | R medio |
|---|---|---|---|
| long | 213 | 0.446 | -0.010 |
| short | 240 | 0.400 | -0.081 |

**per fascia**

| gruppo | n | win rate | R medio |
|---|---|---|---|
| 09:30-10:30 | 219 | 0.511 | 0.060 |
| 10:30-12:00 | 138 | 0.333 | -0.153 |
| 12:00-14:00 | 69 | 0.319 | -0.114 |
| 14:00-15:30 | 27 | 0.407 | -0.208 |

## Feature selezionate per finestra

| finestra | feature |
|---|---|
| 0 | va_type, minutes_since_open, bars_in_profile, open_vs_on_va, va_width_atr, excursion_depth, excursion_minutes, reentry_close_pos, va_shift, in_other_va, stop_dist_atr, rr_ratio, vol_slope_excursion, vol_at_extreme, vol_reentry_bar |
| 1 | va_type, minutes_since_open, bars_in_profile, open_vs_on_va, va_width_atr, excursion_depth, excursion_minutes, reentry_close_pos, va_shift, in_other_va, stop_dist_atr, rr_ratio, vol_slope_excursion, vol_at_extreme, vol_reentry_bar, dist_other_near_atr, dist_other_far_atr, target_dist_atr |
| 2 | va_type, minutes_since_open, bars_in_profile, open_vs_on_va, va_width_atr, excursion_depth, excursion_minutes, reentry_close_pos, va_shift, in_other_va, stop_dist_atr, rr_ratio, vol_slope_excursion, vol_at_extreme, vol_reentry_bar, bars_outside, poc_pos, day_range_atr |
| 3 | va_type, minutes_since_open, bars_in_profile, open_vs_on_va, va_width_atr, excursion_depth, excursion_minutes, reentry_close_pos, va_shift, in_other_va, stop_dist_atr, rr_ratio, vol_slope_excursion, vol_at_extreme, vol_reentry_bar, dist_other_near_atr, rel_vol_session |
| 4 | va_type, minutes_since_open, bars_in_profile, open_vs_on_va, va_width_atr, excursion_depth, excursion_minutes, reentry_close_pos, va_shift, in_other_va, stop_dist_atr, rr_ratio, vol_slope_excursion, vol_at_extreme, vol_reentry_bar |

## Figure

- `reports/figures_1a_S/equity_oos.png`
- `reports/figures_1a_S/calibration.png`
- `reports/figures_1a_S/shap_summary.png`
- `reports/figures_1a_S/shap_dependence_vol_slope_excursion.png`
- `reports/figures_1a_S/shap_dependence_vol_reentry_bar.png`
- `reports/figures_1a_S/shap_dependence_rr_ratio.png`
