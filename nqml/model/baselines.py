"""Baselines (spec §9.2): B0 = tutti; C = regole letterali a soglia; C-opt = soglie da griglia sul solo training.
Le regole vengono da config per versione (1a: 2 regole senza delta; 1b: 3 regole)."""
from __future__ import annotations

import itertools

import numpy as np
import pandas as pd


def rule_list(df: pd.DataFrame, rules: list[dict]) -> np.ndarray:
    mask = np.ones(len(df), dtype=bool)
    for r in rules:
        x = df[r["feature"]].to_numpy(dtype=float)
        if r["op"] == "<":
            mask &= x < r["value"]   # NaN confrontato è False
        elif r["op"] == ">":
            mask &= x > r["value"]
        else:
            raise ValueError(f"operatore sconosciuto nella regola {r}: {r['op']!r} (ammessi '<' e '>')")
    return mask


def fit_c_opt(train_df: pd.DataFrame, cfg: dict, version: str) -> list[dict]:
    bl = cfg["baselines"]
    base = bl["rules_by_version"][version]
    best, best_r = None, -np.inf
    for combo in itertools.product(*[r["values"] for r in base]):
        cand = [{**r, "value": v} for r, v in zip(base, combo)]
        m = rule_list(train_df, cand)
        if m.sum() < bl["c_opt_min_trades"]:
            continue
        r_mean = float(train_df.loc[m, "realized_R"].mean())
        if r_mean > best_r:
            best, best_r = cand, r_mean
    return best if best is not None else [dict(r) for r in base]


def apply_c_opt(df: pd.DataFrame, rules: list[dict]) -> np.ndarray:
    return rule_list(df, rules)
