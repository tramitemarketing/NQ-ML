"""Unione 1c (spec §12-ter): le feature 1a su tutti gli eventi + le colonne tick della 1b dove esistono (NaN altrove)."""
from __future__ import annotations

import numpy as np
import pandas as pd


def union_tick(fa: pd.DataFrame, fb: pd.DataFrame, tick_cols: list[str]) -> pd.DataFrame:
    for name, df in (("features_1a", fa), ("features_1b", fb)):
        if df["event_id"].duplicated().any():
            raise ValueError(f"{name}: event_id duplicati")
    common = [c for c in fa.columns if c in fb.columns and c not in ("event_id", "feature_version")]
    m = fa[["event_id"] + common].merge(fb[["event_id"] + common], on="event_id", how="inner", suffixes=("", "_b"))
    for c in common:
        x, y = m[c], m[f"{c}_b"]
        same = np.allclose(x.astype(float), y.astype(float), equal_nan=True) if x.dtype.kind in "fi" and y.dtype.kind in "fi" \
            else bool((x.astype(str) == y.astype(str)).all())
        if not same:
            raise ValueError(f"colonna comune {c!r} diversa tra features_1a e features_1b: unione rifiutata")
    out = fa.merge(fb[["event_id"] + list(tick_cols)], on="event_id", how="left")
    out["feature_version"] = "1c"
    return out
