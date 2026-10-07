# NQ-ML: Testing intraday trading signals in Nasdaq-100 futures

**Giovanni Febo · independent research · research report v4.1 · 7 October 2026**

A documented case study of measurement bias, multiple testing and statistical
power in intraday research. The code and records accompany the working paper
**Testing Intraday Trading Signals in Nasdaq-100 Futures: Measurement Bias,
Multiple Testing, and Statistical Power**.

- [Read the paper (PDF)](docs/paper/nq_working_paper_en.pdf)
- [Paper source (HTML)](docs/paper/nq_working_paper_en.html)
- [Reproducibility and data requirements](REPRODUCIBILITY.md)
- [Research provenance and publication changes](PROVENANCE.md)

The paper is a working paper, not independently human peer reviewed. Claude
(Anthropic) substantially assisted research design, code, execution, analysis,
drafting and model-session reviews. Codex (OpenAI) assisted the publication
adaptation and repository preparation. Model reviews are not human peer review.

## Research and findings

Part I tests machine-learning selection for a value-area re-entry setup against
a calibrated geometric prior. Part II broadens the investigation to 24 hypothesis
families on data spanning June 2010 to March 2026: **5,013 logged tests** and
**480,181 automatically generated rules**.

| Finding | Interpretation |
| --- | --- |
| Automatic search: maximum real t = 4.18; median placebo maximum = 4.01 across 700 worlds; search-adjusted p = 0.31 | The best rule does not clear the search-adjusted test. |
| Sole directional candidate passing validation: +12.06 net points/trade; confirmation: -2.59, 190 trades | It fails confirmation; about 10% power against half the validation effect leaves smaller effects unresolved. |
| Realized-variance persistence and overnight/day-range association persist across laboratory blocks | Volatility predictability does not establish directional profitability. |
| Time-stop labels, future-side controls and outcome-dependent sampling are corrected | Measurement conventions and sample construction can change the interpretation of backtests. |

None of the **tested** directional strategies met all confirmation criteria.
This is not a proof that directional edges do not exist. The conclusions depend
on the tested hypotheses, one instrument, assumed costs, reused chronological
blocks and statistical power.

## Chronology matters

The 2023-2026 dates were used in the original Part I milestones and subsequently
in Part II. Some later Part I branch-specific confirmations were not run; that
does not make the calendar period globally untouched. The Expected Range
evaluation is descriptive after prior laboratory exposure. See the paper's
Research chronology section.

Preregistration is documented by the author's **original local Git records**.
This repository is a new public snapshot; it does not contain the original
history or provide an independent timestamp for those preregistrations.
The reported unopened vault status is based on the author's records, not an
external access audit. No vault data were accessed during the publication
adaptation, and no new empirical results were generated.

## Repository contents

| Path | Contents |
| --- | --- |
| `docs/paper/` | English v4.1 paper and figures |
| `nqml/`, `scripts/`, `tests/` | Original setup pipeline and synthetic unit tests |
| `lab/` | Laboratory code, protocol, aggregate verdicts and experiment ledgers |
| `reports/` | Selected aggregate reports from the original milestones |
| `product/engine/` | Backtest auditor and synthetic calibration tests |
| `product/indicator/` | Fixed-coefficient Expected Range research prototype |

Licensed price/trade data, event-level exports, caches, fitted-model artifacts,
credentials, private business material and the original full Git history are
excluded. This public source is **not a turnkey data bundle**.

## Run synthetic checks

The main project declares **Python 3.13+**. From the repository root:

```text
python -m venv .venv
python -m pip install -e ".[dev]"
python -m pytest tests
```

Activate the environment or invoke its Python executable directly before the
install and test commands. The tests use synthetic fixtures, including temporary
bar files. They do not require a market-data subscription. Read
[REPRODUCIBILITY.md](REPRODUCIBILITY.md) before attempting an empirical rerun;
data-download scripts may incur vendor charges.

## Citation and rights

Use [CITATION.cff](CITATION.cff) or the repository's “Cite this repository” button.
Versioned publications are available in [GitHub Releases](https://github.com/tramitemarketing/NQ-ML/releases).

**Copyright © 2026 Giovanni Febo. All rights reserved.** Public visibility does
not grant an open-source license. See [LICENSE](LICENSE). Third-party packages
retain their own terms. This is research and educational material; no investment
recommendation or promise of returns is made.

## Sintesi in italiano

Ricerca indipendente sul future Nasdaq-100: verifica di un setup sulla Value Area,
laboratorio con controlli placebo, correzione dei falsi positivi e analisi della
potenza statistica. Nessuna strategia direzionale testata supera tutti i criteri
di conferma, ma diversi risultati restano inconcludenti per effetti più piccoli.
Il paper distingue la previsione della volatilità da un vantaggio direzionale.
Codice e registri sono pubblici; i dati commerciali sono esclusi. Tutti i diritti
sono riservati.
