# Reproducibility scope

This release preserves research source, selected specifications, aggregate
reports and logs. It does not include licensed data or all historical
intermediate artifacts. Publication preparation did not rerun empirical tests.

## Main setup pipeline

- Python requirement declared in `pyproject.toml`: 3.13 or later.
- Data source recorded in the manuscript: Databento `GLBX.MDP3`, continuous
  Nasdaq-100 futures symbol `NQ.v.0`.
- One-minute bars, a stratified sample of tick-trade windows, and later options
  definitions/trades have separate permissions and preparation requirements.
- Main configuration: `config.yaml`. Research specifications are under
  `docs/superpowers/specs/`; look records are `oos_looks.md` and
  `screening_looks.md`.
- Historical environment versions reported in Appendix B refer to the
  original experiments. `pyproject.toml` contains minimum versions, not a
  complete historical lockfile; future installations can differ.

The published scripts describe the original workflows. Inspect their input
requirements and vendor costs before use. The release excludes data files,
symbology mappings, event-level exports, caches and fitted models. These inputs
must be obtained/prepared under the relevant licenses before an end-to-end
rerun. Missing private artifacts can prevent a script from running unchanged;
the public snapshot is a source-and-evidence release, not an assertion that
every pipeline has been reproduced from a clean installation.

## Laboratory

`lab/PROTOCOLLO.md` describes candidate-level access rules. The original blocks
are discovery (2010-06-07 to 2018-12-31), validation (2019-01-01 to 2023-09-30),
and confirmation (2023-10-01 to 2026-03-19). `lab/core.py` is the laboratory's
data gateway. Controller-only access uses `LAB_CONTROLLER=1`; it is a procedural
guard, not a security boundary or external preregistration service.

Read the v4.1 paper's chronology clarification before interpreting these dates
as new evidence: Part I already evaluated overlapping dates. Repeated reuse
across research stages limits independence at the project level even where a
candidate's controller access was restricted.

## Synthetic tests

From the repository root, after installing the main development dependencies:

```text
python -m pytest tests
```

For the standalone auditor, use its own `product/engine/pyproject.toml` and run
its tests from that directory. Its declared Python minimum is 3.10, separate
from the main project's 3.13 requirement.

```text
python -m pip install -e ./product/engine
python -m pytest product/engine/tests
```

Passing synthetic tests checks implementation behavior on those fixtures. It
does not reproduce or independently validate the manuscript's empirical
findings, exclude all look-ahead bias, or certify market-data access history.

## Historical evidence

Aggregate logs and verdicts are preserved as original research artifacts,
including failed and superseded results. Their historical language should be
read with the v4.1 chronology and corrections. `PUBLICATION_MANIFEST.json`
records copied-source hashes; `PROVENANCE.md` describes original commit
references and the limits of the public history.
