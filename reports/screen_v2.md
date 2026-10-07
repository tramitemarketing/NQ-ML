# Screening v2 — rifacimento integrale con lo strumento corretto

Generato 2026-09-23 11:24 · config `2ee491362e71` · commit `1af2754`

Pre-registrazione: `docs/superpowers/specs/2026-09-23-screening-v2-rifacimento.md`. Periodo di screening: 2016-09-20 → 2023-09-30 (anni di training del progetto). L'OOS di lavoro (2023-10-02 → 2026-03-19) e la cassaforte (2026-03-20 → 2026-09-19) non sono stati toccati. Statistica primaria: `EV_lordo = media(R_lordo - nullo)`, R_lordo mark-to-market (target a trade-through di 1 tick, stop al tocco, time-stop 15:55 ET — apertura RTH successiva per il solo candidato 6 — nessun costo), CI a blocchi per giorno (10,000 ricampionamenti, seed 0), p a **una coda**. Nullo 0 per i candidati simmetrici (1-5, 8, 0); nullo con deriva (identita' di Wald, mu-hat trailing 252 sessioni) per i candidati direzionali (6, 7). Co-primaria: `EV_netto = media(R_netto)` dopo commissioni ($2,50/lato) e slippage (1 tick/lato su ingresso e uscite a mercato). Specchio obbligatorio per ogni geometria (stesso ingresso, lato opposto, stesse distanze). Robustezza di unita': segno del netto in R, in $ per contratto e in unita' ATR, tutti e tre concordi. **Molteplicita': Benjamini-Hochberg, q = 0,10, sull'intera famiglia di 58 test** (non per lotto).

## Candidato 1 — ORB 15 minuti

Rottura dell'opening range di 15 minuti (candidato 1). 8 geometrie (2 stop x 4 target). Nullo 0 (simmetrico).

| geometria | n | EV_lordo | CI 95% | p | soglia BH | scoperta | EV_netto | CI 95% | segno R/$/ATR concorde | micro | deriva | P | E | S | N |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| S1_T0.5 | 2537 | -0.0208 | [-0.0467, +0.0044] | 0.9450 | 0.0914 | NO | -0.0380 | [-0.0641, -0.0127] | SI | -0.0105 [-0.0233, +0.0022] | -0.0104 [-0.0324, +0.0122] | NO | — | — | SI |
| S1_T1 | 2537 | -0.0148 | [-0.0488, +0.0200] | 0.7962 | 0.0793 | NO | -0.0334 | [-0.0676, +0.0014] | SI | -0.0063 [-0.0120, +0.0000] | -0.0085 [-0.0423, +0.0258] | NO | — | — | SI |
| S1_T1.5 | 2537 | +0.0148 | [-0.0248, +0.0552] | 0.2376 | 0.0397 | NO | -0.0048 | [-0.0444, +0.0358] | NO | +0.0128 [+0.0014, +0.0243] | +0.0020 [-0.0345, +0.0383] | NO | — | — | SI |
| S1_T2 | 2537 | +0.0360 | [-0.0074, +0.0805] | 0.0526 | 0.0276 | NO | +0.0158 | [-0.0276, +0.0604] | SI | +0.0246 [+0.0092, +0.0401] | +0.0114 [-0.0241, +0.0478] | NO | — | — | SI |
| S2_T0.5 | 2537 | -0.0094 | [-0.1402, +0.1408] | 0.5671 | 0.0603 | NO | -0.4307 | [-0.5650, -0.2788] | SI | -0.0586 [-0.1418, +0.0292] | +0.0492 [-0.0418, +0.1452] | NO | — | — | SI |
| S2_T1 | 2537 | +0.0480 | [-0.1555, +0.3020] | 0.3687 | 0.0483 | NO | -0.3786 | [-0.5842, -0.1229] | SI | -0.0145 [-0.1443, +0.1334] | +0.0625 [-0.0742, +0.2164] | NO | — | — | SI |
| S2_T1.5 | 2537 | +0.0241 | [-0.1584, +0.2169] | 0.4093 | 0.0517 | NO | -0.4050 | [-0.5902, -0.2095] | SI | -0.0068 [-0.1318, +0.1239] | +0.0309 [-0.1014, +0.1622] | NO | — | — | SI |
| S2_T2 | 2537 | +0.0386 | [-0.1544, +0.2360] | 0.3553 | 0.0466 | NO | -0.3919 | [-0.5856, -0.1931] | SI | -0.0036 [-0.1422, +0.1393] | +0.0422 [-0.0982, +0.1807] | NO | — | — | SI |

### Esito (albero pre-registrato, spec §3)

**Nessuna geometria supera P (scoperta BH + segno positivo)** → per questo candidato il filone si chiude qui: nessuna geometria autorizza nulla.

## Candidato 2 — Gap di apertura

|gap RTH| >= 2 punti; F (chiusura del gap) e P (prosecuzione), speculari, 3 k ciascuna (candidato 2). 6 geometrie. Nullo 0 (simmetrico). **Condivide il 98,1% dei suoi eventi con la famiglia R del candidato 8** (vedi matrice di sovrapposizione sotto): non sono due prove indipendenti.

| geometria | n | EV_lordo | CI 95% | p | soglia BH | scoperta | EV_netto | CI 95% | segno R/$/ATR concorde | micro | deriva | P | E | S | N |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| F_k0.5 | 1683 | -0.0025 | [-0.0716, +0.0702] | 0.5333 | 0.0586 | NO | -0.0863 | [-0.1597, -0.0115] | SI | +0.0137 [-0.0380, +0.0714] | -0.0162 [-0.0870, +0.0526] | NO | — | — | SI |
| F_k1 | 1683 | -0.0218 | [-0.0691, +0.0281] | 0.8112 | 0.0828 | NO | -0.0637 | [-0.1128, -0.0131] | SI | -0.0259 [-0.0488, -0.0006] | +0.0040 [-0.0398, +0.0477] | NO | — | — | SI |
| F_k2 | 1683 | -0.0000 | [-0.0365, +0.0400] | 0.4964 | 0.0569 | NO | -0.0190 | [-0.0561, +0.0214] | SI | +0.0105 [-0.0077, +0.0308] | -0.0106 [-0.0434, +0.0226] | NO | — | — | SI |
| P_k0.5 | 1683 | -0.0319 | [-0.0693, +0.0052] | 0.9564 | 0.0948 | NO | -0.0711 | [-0.1090, -0.0332] | SI | -0.0090 [-0.0306, +0.0158] | -0.0229 [-0.0606, +0.0120] | NO | — | — | SI |
| P_k1 | 1683 | -0.0183 | [-0.0661, +0.0291] | 0.7805 | 0.0776 | NO | -0.0605 | [-0.1091, -0.0116] | NO | +0.0034 [-0.0233, +0.0347] | -0.0217 [-0.0714, +0.0243] | NO | — | — | SI |
| P_k2 | 1683 | -0.0086 | [-0.0703, +0.0536] | 0.6248 | 0.0655 | NO | -0.0533 | [-0.1159, +0.0093] | NO | -0.0107 [-0.0424, +0.0194] | +0.0021 [-0.0499, +0.0541] | NO | — | — | SI |

### Esito (albero pre-registrato, spec §3)

**Nessuna geometria supera P (scoperta BH + segno positivo)** → per questo candidato il filone si chiude qui: nessuna geometria autorizza nulla.

## Candidato 3 — Estremi della prima ora

FHH/FHL sulle 60 barre 1m 09:30-10:29:59 ET, rottura dalle 10:30 (candidato 3). 8 geometrie (2 stop x 4 target). Nullo 0 (simmetrico).

| geometria | n | EV_lordo | CI 95% | p | soglia BH | scoperta | EV_netto | CI 95% | segno R/$/ATR concorde | micro | deriva | P | E | S | N |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| S1_T0.5 | 1932 | +0.0208 | [-0.0040, +0.0460] | 0.0484 | 0.0259 | NO | +0.0090 | [-0.0158, +0.0344] | SI | -0.0037 [-0.0150, +0.0076] | +0.0245 [+0.0020, +0.0477] | NO | — | — | SI |
| S1_T1 | 1932 | +0.0289 | [-0.0017, +0.0597] | 0.0324 | 0.0190 | NO | +0.0160 | [-0.0147, +0.0469] | SI | -0.0021 [-0.0050, +0.0013] | +0.0310 [+0.0005, +0.0619] | NO | — | — | SI |
| S1_T1.5 | 1932 | +0.0360 | [+0.0023, +0.0709] | 0.0166 | 0.0103 | NO | +0.0224 | [-0.0114, +0.0574] | SI | +0.0081 [+0.0008, +0.0152] | +0.0279 [-0.0038, +0.0605] | NO | — | — | SI |
| S1_T2 | 1932 | +0.0368 | [+0.0020, +0.0727] | 0.0188 | 0.0121 | NO | +0.0230 | [-0.0120, +0.0589] | SI | +0.0106 [+0.0011, +0.0201] | +0.0262 [-0.0051, +0.0584] | NO | — | — | SI |
| S2_T0.5 | 1932 | +0.1780 | [-0.0024, +0.3733] | 0.0267 | 0.0172 | NO | -0.2684 | [-0.4536, -0.0700] | NO | -0.0341 [-0.1430, +0.0782] | +0.2122 [+0.0944, +0.3325] | NO | — | — | SI |
| S2_T1 | 1932 | +0.2224 | [-0.0186, +0.4822] | 0.0352 | 0.0241 | NO | -0.2288 | [-0.4725, +0.0326] | NO | -0.0209 [-0.1641, +0.1330] | +0.2434 [+0.0938, +0.3995] | NO | — | — | SI |
| S2_T1.5 | 1932 | +0.2742 | [+0.0014, +0.5714] | 0.0244 | 0.0155 | NO | -0.1796 | [-0.4520, +0.1214] | NO | +0.0331 [-0.1313, +0.2101] | +0.2411 [+0.0707, +0.4194] | NO | — | — | SI |
| S2_T2 | 1932 | +0.3308 | [+0.0300, +0.6582] | 0.0152 | 0.0069 | NO | -0.1239 | [-0.4254, +0.2068] | NO | +0.0588 [-0.1210, +0.2503] | +0.2720 [+0.0881, +0.4640] | NO | — | — | SI |

### Esito (albero pre-registrato, spec §3)

**Nessuna geometria supera P (scoperta BH + segno positivo)** → per questo candidato il filone si chiude qui: nessuna geometria autorizza nulla.

## Candidato 4 — Prosecuzione value area

Prima transizione INSIDE->BROKEN per (tipo di VA x lato), evento alla rottura indipendentemente dal rientro (candidato 4). 8 geometrie (2 stop x 4 target). Nullo 0 (simmetrico).

| geometria | n | EV_lordo | CI 95% | p | soglia BH | scoperta | EV_netto | CI 95% | segno R/$/ATR concorde | micro | deriva | P | E | S | N |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| S1_T0.25 | 5573 | -0.0161 | [-0.0576, +0.0283] | 0.7724 | 0.0741 | NO | -0.2688 | [-0.3130, -0.2220] | SI | -0.0944 [-0.1168, -0.0714] | +0.0783 [+0.0469, +0.1106] | NO | — | — | SI |
| S1_T0.5 | 5573 | +0.0031 | [-0.0544, +0.0639] | 0.4626 | 0.0534 | NO | -0.2570 | [-0.3161, -0.1949] | SI | -0.0781 [-0.1107, -0.0452] | +0.0812 [+0.0406, +0.1234] | NO | — | — | SI |
| S1_T0.75 | 5573 | +0.0203 | [-0.0488, +0.0952] | 0.2937 | 0.0431 | NO | -0.2441 | [-0.3146, -0.1678] | SI | -0.0716 [-0.1117, -0.0299] | +0.0919 [+0.0437, +0.1415] | NO | — | — | SI |
| S1_T1.0 | 5573 | +0.0420 | [-0.0423, +0.1332] | 0.1710 | 0.0345 | NO | -0.2255 | [-0.3111, -0.1326] | SI | -0.0527 [-0.1021, -0.0011] | +0.0946 [+0.0387, +0.1532] | NO | — | — | SI |
| S2_T0.25 | 5573 | +0.0175 | [+0.0006, +0.0341] | 0.0209 | 0.0138 | NO | -0.0267 | [-0.0440, -0.0098] | SI | -0.0202 [-0.0290, -0.0114] | +0.0377 [+0.0226, +0.0528] | NO | — | — | SI |
| S2_T0.5 | 5573 | +0.0270 | [+0.0039, +0.0507] | 0.0108 | 0.0034 | NO | -0.0198 | [-0.0433, +0.0041] | SI | -0.0152 [-0.0244, -0.0056] | +0.0421 [+0.0200, +0.0644] | NO | — | — | SI |
| S2_T0.75 | 5573 | +0.0321 | [+0.0025, +0.0616] | 0.0158 | 0.0086 | NO | -0.0167 | [-0.0464, +0.0130] | SI | -0.0120 [-0.0229, -0.0009] | +0.0440 [+0.0171, +0.0712] | NO | — | — | SI |
| S2_T1.0 | 5573 | +0.0253 | [-0.0086, +0.0596] | 0.0713 | 0.0293 | NO | -0.0250 | [-0.0590, +0.0097] | SI | -0.0127 [-0.0265, +0.0015] | +0.0380 [+0.0077, +0.0691] | NO | — | — | SI |

### Esito (albero pre-registrato, spec §3)

**Nessuna geometria supera P (scoperta BH + segno positivo)** → per questo candidato il filone si chiude qui: nessuna geometria autorizza nulla.

## Candidato 5 — Ritorno al VWAP

Ritorno alla media, segnale a 2 sigma dal VWAP di sessione dalle 10:00 ET (candidato 5). 6 geometrie (2 target x 3 stop in ATR). Nullo 0 (simmetrico).

| geometria | n | EV_lordo | CI 95% | p | soglia BH | scoperta | EV_netto | CI 95% | segno R/$/ATR concorde | micro | deriva | P | E | S | N |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| TVWAP_A1.0 | 2183 | -0.0517 | [-0.1179, +0.0143] | 0.9348 | 0.0897 | NO | -0.1302 | [-0.1970, -0.0633] | SI | -0.0039 [-0.0409, +0.0330] | -0.0479 [-0.1051, +0.0085] | NO | — | — | SI |
| TVWAP_A1.5 | 2183 | -0.0152 | [-0.0694, +0.0396] | 0.7104 | 0.0707 | NO | -0.0657 | [-0.1200, -0.0106] | SI | -0.0054 [-0.0311, +0.0199] | -0.0098 [-0.0577, +0.0380] | NO | — | — | SI |
| TVWAP_A2.0 | 2183 | -0.0085 | [-0.0549, +0.0383] | 0.6422 | 0.0672 | NO | -0.0455 | [-0.0922, +0.0014] | SI | -0.0036 [-0.0227, +0.0154] | -0.0049 [-0.0478, +0.0371] | NO | — | — | SI |
| TMID_A1.0 | 2183 | -0.0642 | [-0.1121, -0.0164] | 0.9954 | 0.1000 | NO | -0.1385 | [-0.1872, -0.0901] | SI | -0.0249 [-0.0452, -0.0052] | -0.0393 [-0.0829, +0.0041] | NO | — | — | SI |
| TMID_A1.5 | 2183 | -0.0254 | [-0.0651, +0.0139] | 0.9012 | 0.0879 | NO | -0.0728 | [-0.1128, -0.0332] | SI | -0.0182 [-0.0338, -0.0027] | -0.0072 [-0.0436, +0.0285] | NO | — | — | SI |
| TMID_A2.0 | 2183 | -0.0279 | [-0.0632, +0.0063] | 0.9492 | 0.0931 | NO | -0.0627 | [-0.0982, -0.0282] | SI | -0.0203 [-0.0343, -0.0064] | -0.0077 [-0.0399, +0.0231] | NO | — | — | SI |

### Esito (albero pre-registrato, spec §3)

**Nessuna geometria supera P (scoperta BH + segno positivo)** → per questo candidato il filone si chiude qui: nessuna geometria autorizza nulla.

## Candidato 6 — Tenuta overnight

Long alla chiusura RTH, uscita all'apertura RTH successiva, nessuna condizione (candidato 6). 4 geometrie (2 stop x 2 target in ATR). **Nullo con deriva** (identita' di Wald, mu-hat trailing 252 sessioni del segmento overnight): unico candidato interamente long, il nullo a zero sarebbe banale da battere su un indice in salita nel training.

| geometria | n | EV_lordo | CI 95% | p | soglia BH | scoperta | EV_netto | CI 95% | segno R/$/ATR concorde | micro | deriva | P | E | S | N |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| S1.0_T1.0 | 1694 | +0.0446 | [-0.0155, +0.0999] | 0.0715 | 0.0310 | NO | +0.0622 | [+0.0137, +0.1101] | SI | -0.0210 [-0.0285, -0.0138] | +0.0656 [+0.0054, +0.1207] | NO | — | — | SI |
| S1.0_T2.0 | 1694 | -0.0089 | [-0.0893, +0.0685] | 0.5818 | 0.0621 | NO | +0.0962 | [+0.0257, +0.1656] | SI | -0.0223 [-0.0586, +0.0140] | +0.0135 [-0.0557, +0.0783] | NO | — | — | SI |
| S2.0_T1.0 | 1694 | -0.0055 | [-0.0440, +0.0313] | 0.6061 | 0.0638 | NO | +0.0306 | [-0.0028, +0.0631] | SI | -0.0099 [-0.0280, +0.0085] | +0.0044 [-0.0305, +0.0377] | NO | — | — | SI |
| S2.0_T2.0 | 1694 | -0.0277 | [-0.0810, +0.0237] | 0.8504 | 0.0845 | NO | +0.0636 | [+0.0157, +0.1103] | SI | -0.0123 [-0.0179, -0.0073] | -0.0154 [-0.0681, +0.0353] | NO | — | — | SI |

### Esito (albero pre-registrato, spec §3)

**Nessuna geometria supera P (scoperta BH + segno positivo)** → per questo candidato il filone si chiude qui: nessuna geometria autorizza nulla.

## Candidato 7 — Momentum ultima ora

Alle 15:00 ET, nella direzione della sessione rispetto all'apertura RTH (candidato 7). 4 geometrie (2 stop x 2 target in ATR). **Nullo con deriva** (identita' di Wald, mu-hat trailing 252 sessioni del segmento RTH): il lato del trade e' correlato all'andamento della sessione, quindi il nullo a zero non e' neutro.

| geometria | n | EV_lordo | CI 95% | p | soglia BH | scoperta | EV_netto | CI 95% | segno R/$/ATR concorde | micro | deriva | P | E | S | N |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| S0.5_T0.5 | 1748 | -0.0111 | [-0.0585, +0.0355] | 0.6711 | 0.0690 | NO | -0.1604 | [-0.2091, -0.1114] | SI | -0.0429 [-0.0546, -0.0312] | +0.0318 [-0.0143, +0.0770] | NO | — | — | SI |
| S0.5_T1.0 | 1748 | +0.0431 | [-0.0238, +0.1100] | 0.1047 | 0.0328 | NO | -0.1131 | [-0.1816, -0.0444] | SI | -0.0312 [-0.0649, +0.0013] | +0.0742 [+0.0177, +0.1291] | NO | — | — | SI |
| S1.0_T0.5 | 1748 | +0.0156 | [-0.0172, +0.0479] | 0.1747 | 0.0362 | NO | -0.0531 | [-0.0866, -0.0198] | NO | -0.0189 [-0.0344, -0.0027] | +0.0345 [+0.0049, +0.0633] | NO | — | — | SI |
| S1.0_T1.0 | 1748 | +0.0536 | [+0.0080, +0.0987] | 0.0121 | 0.0052 | NO | -0.0192 | [-0.0655, +0.0269] | NO | -0.0115 [-0.0191, -0.0043] | +0.0651 [+0.0204, +0.1097] | NO | — | — | SI |

### Esito (albero pre-registrato, spec §3)

**Nessuna geometria supera P (scoperta BH + segno positivo)** → per questo candidato il filone si chiude qui: nessuna geometria autorizza nulla.

## Candidato 8 — Apertura fuori VA di ieri

Apertura RTH fuori dalla value area (70%) della sessione precedente; famiglie R (ritorno) e C (continuazione) (candidato 8). 8 geometrie (2 famiglie x 4 k). Nullo 0 (simmetrico). **La famiglia R condivide il 98,1% dei suoi eventi con il candidato 2 (gap)**: vedi matrice di sovrapposizione sotto.

| geometria | n | EV_lordo | CI 95% | p | soglia BH | scoperta | EV_netto | CI 95% | segno R/$/ATR concorde | micro | deriva | P | E | S | N |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| R_K0.25 | 1191 | +0.1188 | [-0.0063, +0.2504] | 0.0327 | 0.0207 | NO | +0.0026 | [-0.1260, +0.1388] | SI | +0.0743 [-0.0114, +0.1716] | +0.0445 [-0.0691, +0.1474] | NO | — | — | SI |
| R_K0.5 | 1191 | +0.0136 | [-0.0638, +0.0925] | 0.3793 | 0.0500 | NO | -0.0360 | [-0.1148, +0.0434] | NO | +0.0321 [-0.0136, +0.0787] | -0.0185 [-0.0858, +0.0459] | NO | — | — | SI |
| R_K0.75 | 1191 | +0.0605 | [-0.0051, +0.1274] | 0.0351 | 0.0224 | NO | +0.0356 | [-0.0305, +0.1027] | SI | +0.0320 [-0.0002, +0.0647] | +0.0285 [-0.0256, +0.0831] | NO | — | — | SI |
| R_K1.0 | 1191 | +0.0255 | [-0.0279, +0.0792] | 0.1772 | 0.0379 | NO | +0.0085 | [-0.0448, +0.0625] | SI | +0.0140 [-0.0106, +0.0389] | +0.0114 [-0.0348, +0.0584] | NO | — | — | SI |
| C_K0.25 | 1191 | -0.0517 | [-0.1036, +0.0044] | 0.9659 | 0.0966 | NO | -0.0954 | [-0.1483, -0.0385] | SI | -0.0398 [-0.0672, -0.0111] | -0.0119 [-0.0522, +0.0291] | NO | — | — | SI |
| C_K0.5 | 1191 | -0.0299 | [-0.1034, +0.0551] | 0.7747 | 0.0759 | NO | -0.0764 | [-0.1512, +0.0091] | SI | -0.0390 [-0.0792, +0.0057] | +0.0091 [-0.0458, +0.0672] | NO | — | — | SI |
| C_K0.75 | 1191 | -0.0297 | [-0.1233, +0.0816] | 0.7310 | 0.0724 | NO | -0.0775 | [-0.1717, +0.0331] | SI | -0.0385 [-0.0904, +0.0191] | +0.0089 [-0.0577, +0.0791] | NO | — | — | SI |
| C_K1.0 | 1191 | +0.0068 | [-0.1071, +0.1445] | 0.4790 | 0.0552 | NO | -0.0415 | [-0.1552, +0.0963] | SI | -0.0171 [-0.0806, +0.0541] | +0.0239 [-0.0548, +0.1085] | NO | — | — | SI |

### Esito (albero pre-registrato, spec §3)

**Nessuna geometria supera P (scoperta BH + segno positivo)** → per questo candidato il filone si chiude qui: nessuna geometria autorizza nulla.

## Candidato 0 — Setup value-area originale (rientro)

Setup value-area originale (rientro nella value area dopo la rottura), `data/events/events.parquet`. Una sola geometria (gia' fissata dal detector) + 5 strati di rr (quintili calcolati sugli eventi del training). Nullo 0 (simmetrico). Un evento (20170410-DEV-short-0940) ha `entry_price == stop_price` (r_unit = 0, artefatto del detector originale, non una scelta di geometria): scartato prima dei quintili, stessa convenzione «salta se |entry_ref - stop| <= 0» gia' usata dai candidati 1-8. **Gli strati di rr sono esplorativi**: nascono dall'aver guardato il training e non possono autorizzare nulla da soli, anche se il BH li segna come scoperta.

| geometria | n | EV_lordo | CI 95% | p | soglia BH | scoperta | EV_netto | CI 95% | segno R/$/ATR concorde | micro | deriva | P | E | S | N |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| complessiva | 13619 | -0.0171 | [-0.0488, +0.0151] | 0.8507 | 0.0862 | NO | -0.0934 | [-0.1257, -0.0608] | SI | +0.0022 [-0.0156, +0.0206] | -0.0193 [-0.0483, +0.0098] | NO | — | — | SI |
| rr_Q1 *(esplorativo)* | 2725 | +0.0398 | [+0.0116, +0.0678] | 0.0024 | 0.0017 | NO | +0.0095 | [-0.0190, +0.0379] | SI | +0.0019 [-0.0094, +0.0132] | +0.0378 [+0.0119, +0.0630] | NO | — | — | SI |
| rr_Q2 *(esplorativo)* | 2723 | +0.0115 | [-0.0302, +0.0533] | 0.2933 | 0.0414 | NO | -0.0314 | [-0.0737, +0.0105] | NO | -0.0054 [-0.0184, +0.0071] | +0.0169 [-0.0231, +0.0572] | NO | — | — | SI |
| rr_Q3 *(esplorativo)* | 2727 | +0.0131 | [-0.0415, +0.0673] | 0.3218 | 0.0448 | NO | -0.0434 | [-0.0989, +0.0112] | SI | +0.0190 [-0.0054, +0.0434] | -0.0059 [-0.0564, +0.0446] | NO | — | — | SI |
| rr_Q4 *(esplorativo)* | 2720 | -0.0285 | [-0.0953, +0.0385] | 0.8000 | 0.0810 | NO | -0.1091 | [-0.1762, -0.0418] | SI | +0.0290 [-0.0088, +0.0678] | -0.0575 [-0.1166, -0.0005] | NO | — | — | SI |
| rr_Q5 *(esplorativo)* | 2724 | -0.1214 | [-0.2181, -0.0224] | 0.9915 | 0.0983 | NO | -0.2929 | [-0.3906, -0.1927] | SI | -0.0336 [-0.1023, +0.0363] | -0.0878 [-0.1682, -0.0068] | NO | — | — | SI |

### Esito (albero pre-registrato, spec §3)

**Nessuna geometria supera P (scoperta BH + segno positivo)** → per questo candidato il filone si chiude qui: nessuna geometria autorizza nulla.

## Sintesi — tutti i 58 test, ordinati per p (BH q = 0,10 sull'intera famiglia)

| candidato | geometria | n | p | soglia BH | scoperta | EV_lordo | EV_netto | P | E | S | N |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Setup value-area originale (rientro) | rr_Q1 *(espl.)* | 2725 | 0.0024 | 0.0017 | NO | +0.0398 | +0.0095 | NO | — | — | SI |
| Prosecuzione value area | S2_T0.5 | 5573 | 0.0108 | 0.0034 | NO | +0.0270 | -0.0198 | NO | — | — | SI |
| Momentum ultima ora | S1.0_T1.0 | 1748 | 0.0121 | 0.0052 | NO | +0.0536 | -0.0192 | NO | — | — | SI |
| Estremi della prima ora | S2_T2 | 1932 | 0.0152 | 0.0069 | NO | +0.3308 | -0.1239 | NO | — | — | SI |
| Prosecuzione value area | S2_T0.75 | 5573 | 0.0158 | 0.0086 | NO | +0.0321 | -0.0167 | NO | — | — | SI |
| Estremi della prima ora | S1_T1.5 | 1932 | 0.0166 | 0.0103 | NO | +0.0360 | +0.0224 | NO | — | — | SI |
| Estremi della prima ora | S1_T2 | 1932 | 0.0188 | 0.0121 | NO | +0.0368 | +0.0230 | NO | — | — | SI |
| Prosecuzione value area | S2_T0.25 | 5573 | 0.0209 | 0.0138 | NO | +0.0175 | -0.0267 | NO | — | — | SI |
| Estremi della prima ora | S2_T1.5 | 1932 | 0.0244 | 0.0155 | NO | +0.2742 | -0.1796 | NO | — | — | SI |
| Estremi della prima ora | S2_T0.5 | 1932 | 0.0267 | 0.0172 | NO | +0.1780 | -0.2684 | NO | — | — | SI |
| Estremi della prima ora | S1_T1 | 1932 | 0.0324 | 0.0190 | NO | +0.0289 | +0.0160 | NO | — | — | SI |
| Apertura fuori VA di ieri | R_K0.25 | 1191 | 0.0327 | 0.0207 | NO | +0.1188 | +0.0026 | NO | — | — | SI |
| Apertura fuori VA di ieri | R_K0.75 | 1191 | 0.0351 | 0.0224 | NO | +0.0605 | +0.0356 | NO | — | — | SI |
| Estremi della prima ora | S2_T1 | 1932 | 0.0352 | 0.0241 | NO | +0.2224 | -0.2288 | NO | — | — | SI |
| Estremi della prima ora | S1_T0.5 | 1932 | 0.0484 | 0.0259 | NO | +0.0208 | +0.0090 | NO | — | — | SI |
| ORB 15 minuti | S1_T2 | 2537 | 0.0526 | 0.0276 | NO | +0.0360 | +0.0158 | NO | — | — | SI |
| Prosecuzione value area | S2_T1.0 | 5573 | 0.0713 | 0.0293 | NO | +0.0253 | -0.0250 | NO | — | — | SI |
| Tenuta overnight | S1.0_T1.0 | 1694 | 0.0715 | 0.0310 | NO | +0.0446 | +0.0622 | NO | — | — | SI |
| Momentum ultima ora | S0.5_T1.0 | 1748 | 0.1047 | 0.0328 | NO | +0.0431 | -0.1131 | NO | — | — | SI |
| Prosecuzione value area | S1_T1.0 | 5573 | 0.1710 | 0.0345 | NO | +0.0420 | -0.2255 | NO | — | — | SI |
| Momentum ultima ora | S1.0_T0.5 | 1748 | 0.1747 | 0.0362 | NO | +0.0156 | -0.0531 | NO | — | — | SI |
| Apertura fuori VA di ieri | R_K1.0 | 1191 | 0.1772 | 0.0379 | NO | +0.0255 | +0.0085 | NO | — | — | SI |
| ORB 15 minuti | S1_T1.5 | 2537 | 0.2376 | 0.0397 | NO | +0.0148 | -0.0048 | NO | — | — | SI |
| Setup value-area originale (rientro) | rr_Q2 *(espl.)* | 2723 | 0.2933 | 0.0414 | NO | +0.0115 | -0.0314 | NO | — | — | SI |
| Prosecuzione value area | S1_T0.75 | 5573 | 0.2937 | 0.0431 | NO | +0.0203 | -0.2441 | NO | — | — | SI |
| Setup value-area originale (rientro) | rr_Q3 *(espl.)* | 2727 | 0.3218 | 0.0448 | NO | +0.0131 | -0.0434 | NO | — | — | SI |
| ORB 15 minuti | S2_T2 | 2537 | 0.3553 | 0.0466 | NO | +0.0386 | -0.3919 | NO | — | — | SI |
| ORB 15 minuti | S2_T1 | 2537 | 0.3687 | 0.0483 | NO | +0.0480 | -0.3786 | NO | — | — | SI |
| Apertura fuori VA di ieri | R_K0.5 | 1191 | 0.3793 | 0.0500 | NO | +0.0136 | -0.0360 | NO | — | — | SI |
| ORB 15 minuti | S2_T1.5 | 2537 | 0.4093 | 0.0517 | NO | +0.0241 | -0.4050 | NO | — | — | SI |
| Prosecuzione value area | S1_T0.5 | 5573 | 0.4626 | 0.0534 | NO | +0.0031 | -0.2570 | NO | — | — | SI |
| Apertura fuori VA di ieri | C_K1.0 | 1191 | 0.4790 | 0.0552 | NO | +0.0068 | -0.0415 | NO | — | — | SI |
| Gap di apertura | F_k2 | 1683 | 0.4964 | 0.0569 | NO | -0.0000 | -0.0190 | NO | — | — | SI |
| Gap di apertura | F_k0.5 | 1683 | 0.5333 | 0.0586 | NO | -0.0025 | -0.0863 | NO | — | — | SI |
| ORB 15 minuti | S2_T0.5 | 2537 | 0.5671 | 0.0603 | NO | -0.0094 | -0.4307 | NO | — | — | SI |
| Tenuta overnight | S1.0_T2.0 | 1694 | 0.5818 | 0.0621 | NO | -0.0089 | +0.0962 | NO | — | — | SI |
| Tenuta overnight | S2.0_T1.0 | 1694 | 0.6061 | 0.0638 | NO | -0.0055 | +0.0306 | NO | — | — | SI |
| Gap di apertura | P_k2 | 1683 | 0.6248 | 0.0655 | NO | -0.0086 | -0.0533 | NO | — | — | SI |
| Ritorno al VWAP | TVWAP_A2.0 | 2183 | 0.6422 | 0.0672 | NO | -0.0085 | -0.0455 | NO | — | — | SI |
| Momentum ultima ora | S0.5_T0.5 | 1748 | 0.6711 | 0.0690 | NO | -0.0111 | -0.1604 | NO | — | — | SI |
| Ritorno al VWAP | TVWAP_A1.5 | 2183 | 0.7104 | 0.0707 | NO | -0.0152 | -0.0657 | NO | — | — | SI |
| Apertura fuori VA di ieri | C_K0.75 | 1191 | 0.7310 | 0.0724 | NO | -0.0297 | -0.0775 | NO | — | — | SI |
| Prosecuzione value area | S1_T0.25 | 5573 | 0.7724 | 0.0741 | NO | -0.0161 | -0.2688 | NO | — | — | SI |
| Apertura fuori VA di ieri | C_K0.5 | 1191 | 0.7747 | 0.0759 | NO | -0.0299 | -0.0764 | NO | — | — | SI |
| Gap di apertura | P_k1 | 1683 | 0.7805 | 0.0776 | NO | -0.0183 | -0.0605 | NO | — | — | SI |
| ORB 15 minuti | S1_T1 | 2537 | 0.7962 | 0.0793 | NO | -0.0148 | -0.0334 | NO | — | — | SI |
| Setup value-area originale (rientro) | rr_Q4 *(espl.)* | 2720 | 0.8000 | 0.0810 | NO | -0.0285 | -0.1091 | NO | — | — | SI |
| Gap di apertura | F_k1 | 1683 | 0.8112 | 0.0828 | NO | -0.0218 | -0.0637 | NO | — | — | SI |
| Tenuta overnight | S2.0_T2.0 | 1694 | 0.8504 | 0.0845 | NO | -0.0277 | +0.0636 | NO | — | — | SI |
| Setup value-area originale (rientro) | complessiva | 13619 | 0.8507 | 0.0862 | NO | -0.0171 | -0.0934 | NO | — | — | SI |
| Ritorno al VWAP | TMID_A1.5 | 2183 | 0.9012 | 0.0879 | NO | -0.0254 | -0.0728 | NO | — | — | SI |
| Ritorno al VWAP | TVWAP_A1.0 | 2183 | 0.9348 | 0.0897 | NO | -0.0517 | -0.1302 | NO | — | — | SI |
| ORB 15 minuti | S1_T0.5 | 2537 | 0.9450 | 0.0914 | NO | -0.0208 | -0.0380 | NO | — | — | SI |
| Ritorno al VWAP | TMID_A2.0 | 2183 | 0.9492 | 0.0931 | NO | -0.0279 | -0.0627 | NO | — | — | SI |
| Gap di apertura | P_k0.5 | 1683 | 0.9564 | 0.0948 | NO | -0.0319 | -0.0711 | NO | — | — | SI |
| Apertura fuori VA di ieri | C_K0.25 | 1191 | 0.9659 | 0.0966 | NO | -0.0517 | -0.0954 | NO | — | — | SI |
| Setup value-area originale (rientro) | rr_Q5 *(espl.)* | 2724 | 0.9915 | 0.0983 | NO | -0.1214 | -0.2929 | NO | — | — | SI |
| Ritorno al VWAP | TMID_A1.0 | 2183 | 0.9954 | 0.1000 | NO | -0.0642 | -0.1385 | NO | — | — | SI |

**0 scoperta/e BH su 58 test** al livello q = 0.10; **0 soddisfano anche P** (scoperta con segno positivo — identico a scoperta, dato che il test e' a una coda solo positiva).

## Esito complessivo del filone

**Nessuna scoperta P su tutta la famiglia (esclusi gli strati esplorativi del candidato 0)** → il filone screening si **chiude**; la conclusione e' quella gia' scritta in §4 della spec `docs/superpowers/specs/2026-09-23-screening-candidati-5-8-e-ibridi.md`.

## Matrice di sovrapposizione fra i setup (copiata da `reports/screen_batch2.md`)

Citata per intero perche' rilevante alle righe gap (candidato 2) e prevva/R (candidato 8), che condividono il 98,1% degli eventi (spec v2 §0.3): non sono due prove indipendenti, anche se contano separatamente nella famiglia BH.

## Matrice di sovrapposizione fra i setup (candidati 1-8)

Per ogni coppia ORDINATA (riga, colonna): quota degli eventi della riga che hanno un evento della colonna nello stesso giorno, stesso lato, entro 15 minuti (`signal_ts`). Descrittiva: nessun criterio, non decide nulla da sola — serve solo a sapere se un ibrido futuro aggiungerebbe informazione o conterebbe due volte la stessa operazione (spec §2).

| da \\ a | orb15 | gap | firsthour | vabreak | vwap | overnight | lasthour | prevva |
|---|---|---|---|---|---|---|---|---|
| orb15 | — | 10.2% | 29.6% | 70.3% | 2.5% | 0.0% | 0.8% | 7.4% |
| gap | 7.7% | — | 0.0% | 58.6% | 0.0% | 0.0% | 0.0% | 69.4% |
| firsthour | 38.9% | 0.0% | — | 25.3% | 0.1% | 0.0% | 2.6% | 0.0% |
| vabreak | 47.1% | 50.6% | 10.0% | — | 1.8% | 0.0% | 0.7% | 35.0% |
| vwap | 2.9% | 0.0% | 0.1% | 4.0% | — | 0.0% | 0.5% | 0.0% |
| overnight | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | — | 0.0% | 0.0% |
| lasthour | 1.1% | 0.0% | 2.9% | 2.1% | 0.6% | 0.0% | — | 0.0% |
| prevva | 7.9% | 98.1% | 0.0% | 57.2% | 0.0% | 0.0% | 0.0% | — |


## Come leggere questa tabella

`EV_lordo` è la media per evento di `R_lordo - nullo` (nullo 0 per i simmetrici, nullo con deriva per overnight e ultima ora), con CI a blocchi per giorno; `p` è a una coda (solo positivo). `soglia BH` è la soglia assegnata al rango di quel test nell'ordinamento crescente dei p-value dell'intera famiglia di 58 (non alla sua posizione naturale nella tabella): una geometria è **scoperta** se `p` ≤ soglia BH. `EV_netto` è la media di `R_netto` dopo costi (commissione + slippage), criterio E: CI 95% che esclude 0 ed è positiva. `micro` e `deriva` sono il test dello specchio: `micro = (EV_orig+EV_specchio)/2`, `deriva = (EV_orig-EV_specchio)/2`; criterio S: deriva positiva e |micro| < |deriva| (effetto direzionale, non microstruttura). Il segno R/$/ATR concorde è il criterio di robustezza di unità: la scoperta è valida solo se il segno del netto è lo stesso in tutte e tre le unità. P/E/S/N sono i quattro criteri della spec §3: solo P**+**E**+**S insieme, sulla geometria con EV_netto più alto fra tutte quelle che li passano, autorizzano la proposta di un test di replica sull'OOS vergine — mai eseguito senza approvazione esplicita dell'utente. Gli strati di rr del candidato 0 sono **esplorativi**: anche se il BH li segna come scoperta, non possono autorizzare nulla da soli (nascono dall'aver guardato il training). «—» in E/S significa che il criterio non è stato valutato perché la geometria non supera P.
