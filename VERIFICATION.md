# Publication verification

Verified on 7 October 2026 against the public snapshot, using the existing
research environment. The imported `nqml` module was confirmed to come from
this public copy, not the original private source directory.

- Main synthetic suite: **256 passed**, 17.49 seconds.
- Backtest-auditor synthetic suite: **16 passed**, 8.57 seconds.
- No market-data download, purchase, empirical backtest, controller execution
  or vault access was performed for this publication.

Environment observed at verification: Python 3.13.13, NumPy 2.5.3,
pandas 3.0.6, LightGBM 4.7.0, scikit-learn 1.9.1, pytest 9.1.1,
PyArrow 25.0.1, Databento client 0.86.0.

The tests were run with bytecode and pytest-cache writing disabled. Synthetic
fixtures were written to a separate temporary workspace. The first invocation
started outside the repository and failed to locate `config.yaml`; running
from the documented repository root resolved that invocation error.

These checks verify behavior covered by the existing synthetic tests. They are
not a clean-environment installation test, an independent empirical replication,
or an audit of the original data-access history.
