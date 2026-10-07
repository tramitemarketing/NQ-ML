"""r7_quantili: tabella giornaliera, feature, modelli e pinball loss (PREREG.md)."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

from lab import core, extdata

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "product" / "indicator"))
import features as F  # noqa: E402

QS = np.array([0.05, 0.10, 0.25, 0.50, 0.75, 0.90, 0.95])
HAR = ["l1", "m5", "m22", "lon"]
EXTRA = ["lvxn", "fomc", "cpi", "nfp", "monday"]
FEATS = HAR + EXTRA
YEARS_OOS = list(range(2013, 2019))


def table(phase: str = "discovery") -> pd.DataFrame:
    """Sessioni valide con y, feature HAR dell'indicatore, VXN di ieri e calendario. Solo tramite lab.core."""
    bars, _ = core.load(phase)
    t = F.daily_table(bars)
    t = t[t["valid"]].copy()
    ext = extdata.known_at_open(t.index)
    t["lvxn"] = np.log(ext["VXN"])
    cal = extdata.macro_calendar(t.index)
    for c in ("fomc", "cpi", "nfp"):
        t[c] = cal[c]
    t["monday"] = (t.index.dayofweek == 0).astype(float)
    t = t[t.index >= pd.Timestamp("2010-07-08")]          # come l'indicatore: 22 sessioni di storia
    return t.dropna(subset=["y"] + FEATS)


def pinball(y: np.ndarray, q: np.ndarray) -> np.ndarray:
    """Pinball loss media sui quantili QS, una per riga. q: matrice (n, len(QS))."""
    u = y[:, None] - q
    return np.mean(np.maximum(QS * u, (QS - 1) * u), axis=1)


def b0(train: pd.DataFrame, test: pd.DataFrame, resid_window: int | None = None) -> np.ndarray:
    """OLS log-HAR + notte; quantili = previsione + quantili empirici dei residui (tutta la stima,
    oppure le ultime `resid_window` sessioni: variante usata SOLO per la potenza al Passo 0)."""
    A = np.column_stack([np.ones(len(train)), train[HAR].to_numpy()])
    b, *_ = np.linalg.lstsq(A, train["y"].to_numpy(), rcond=None)
    res = train["y"].to_numpy() - A @ b
    if resid_window:
        res = res[-resid_window:]
    rq = np.quantile(res, QS)
    mu = np.column_stack([np.ones(len(test)), test[HAR].to_numpy()]) @ b
    return mu[:, None] + rq[None, :]


def walk_forward(t: pd.DataFrame, model) -> pd.DataFrame:
    """Per Y in 2013..2018: stima su sessioni < Y (dal 2010-07), previsione dell'anno Y."""
    out = []
    for y in YEARS_OOS:
        tr = t[t.index < pd.Timestamp(y, 1, 1)]
        te = t[(t.index >= pd.Timestamp(y, 1, 1)) & (t.index < pd.Timestamp(y + 1, 1, 1))]
        q = np.sort(model(tr, te), axis=1)
        out.append(pd.DataFrame(q, index=te.index, columns=[f"q{x:.2f}" for x in QS]))
    return pd.concat(out)
