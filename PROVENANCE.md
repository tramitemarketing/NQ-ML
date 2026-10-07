# Publication provenance

Author: Giovanni Febo. Publication snapshot prepared on 7 October 2026.
Original local source HEAD: `d02187aa818607aca60a0ca45bdd1058df025350`.
Original English v4.0 manuscript SHA-256 (UTF-8 source): `cc29413e4157b8f1813f49468507339bafb74359292dce2034658367dff923f1`.

This repository starts a **new public Git history**. The original history contains data-derived
artifacts and is intentionally excluded. Original commit IDs in the manuscript identify
records in the author's local source; they are not commits available in this public repository.
Their timestamps are local Git metadata, not independent preregistration timestamps.
This release does not independently establish that the source history was immutable or that
all market-data access followed the protocol. The source records are provided as documented
research provenance with that limitation.

| Original commit | Recorded author timestamp | Recorded subject |
| --- | --- | --- |
| `177ca1ec9f037beb395c5ea38ff59d528cf1170a` | 2026-09-23T18:27:16+02:00 | PASSO 0: il +0,1486 di B2 era un artefatto di campionamento. Filone chiuso. |
| `3a07983bfb027806bd006b32227d80048b3e42d8` | 2026-10-07T21:36:28+02:00 | lab: cassaforte chiusa al 2026-09-30 per decisione dell'utente; dal 2026-10-01 solo prove in avanti pre-registrate (PROTOCOLLO §23) |
| `4f7ac9b7d4ccce51cfe1cd939df1cfd4b9133f2f` | 2026-09-21T15:03:32+02:00 | docs(spec): §12-bis Milestone 1b-S — order flow su giorni campionati, pre-registrazione del campionamento e dei criteri appaiati |
| `e5e398e2094a7f309ea682068b0a42edaa70f6c7` | 2026-09-21T17:39:52+02:00 | docs(1b): campionamento pre-registrato e costo esatto delle finestre |
| `2432fefb256843acc059028911cce43261eaec25` | 2026-09-21T22:59:24+02:00 | docs(1c): pre-registrazione dello sguardo #3 (§12-ter) e diagnostiche post hoc del consiglio (2-ter) |
| `bbab3855b63a1efb6ad02a038faf366dd436fac3` | 2026-09-22T11:37:46+02:00 | fix(1c): shuffle di sanita' con L2 rifittata sulle label mescolate (emendamento §12-ter prima del run) |
| `f12f9e3e757a79ead7766aa0115d2c33a0d40409` | 2026-09-22T11:40:50+02:00 | feat(1c): walk-forward con offset del prior, p_l2 persistita, shuffle a 5 seed, --seed |
| `1b0cc0c5e1907bf272499e8add4cce0f06449601` | 2026-10-07T18:42:14+02:00 | lab: giro 7, pre-registrazione di r7_quantili (ML sui quantili del range) e r7_opzioni (previsione di volatilità contro straddle), prima di qualunque dato |
| `eeaaab3d367f1f61b70bdee4286059ceda8858d2` | 2026-10-07T19:43:51+02:00 | lab: giro 7, Passo 0 di r7_quantili (calendario macro, potenza MDE80 0,66 %), addendum 1 e codice dei test primari (prima di eseguirli); script di download e Passo 0 di r7_opzioni |
| `c942f3b054f55d5bb335c467b3f9966ba12e45ec` | 2026-10-07T19:56:50+02:00 | lab: giro 7, r7_opzioni: addendum 1, codice comune e dei test primari (prima del Passo 0 e di qualunque esito) |
| `4f17faa0eaec6a7be2bd6704a20f19c32d249905` | 2026-10-07T19:55:17+02:00 | lab: giro 7, esito di r7_quantili (2 test primari, 0 candidati: lineare +1,3 % sotto soglia, LightGBM -3,2 %); download opzioni via API batch |
| `8fa25f93d3bbc846532ac83ab6fb57323486519a` | 2026-10-07T21:24:48+02:00 | lab: giro 7, r7_opzioni chiusa al Passo 0 (53 venerdì utilizzabili, MDE80 32 % del mid: non decidibile nel discovery); esito del giro 7 |

`PUBLICATION_MANIFEST.json` records SHA-256 hashes of copied source files before editorial
publication changes. The v4.1 manuscript, README, availability notes, citation metadata and
exclusion rules are publication additions. No empirical experiment or vault access was run
during this adaptation.

## Editorial changes from English v4.0 to v4.1

- Academic title and shorter abstract; explicit AI-use disclosure.
- Corrected the scope of “never opened”: later unexecuted branch confirmations do not erase
  earlier use of the 2023-2026 dates in Part I or their subsequent use in Part II.
- Distinguished the original September 19 vault boundary from the final September 30 boundary.
- Replaced broad market-efficiency conclusions and unsupported defect-probability rhetoric
  with conclusions limited to tested hypotheses and available power.
- Qualified optional stopping with discrete-time integrability and bounded stopping.
- Disclosed the limits of locally recorded preregistration and the fresh public snapshot.
- Corrected the range-model comparison to its actual baseline; added missing methodological references.
- Updated code/data availability. Numerical results and historical ledgers were not recomputed.
- Scoped the directional conclusion in the indicator README for consistency with the paper.
