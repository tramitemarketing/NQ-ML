"""Salvataggio degli eventi di ogni candidato (1-8) per la matrice di sovrapposizione e la fase ibrida
(pre-registrazione `docs/superpowers/specs/2026-09-23-screening-candidati-5-8-e-ibridi.md`, §2): un file
parquet per candidato in `data/screen/`, con almeno le colonne comuni richieste. Non altera i DataFrame
usati per i report: chi chiama passa una copia gia' rinominata/arricchita, se serve."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

REQUIRED_COLS = ["event_id", "session_date", "side", "signal_ts", "entry_ts", "entry_price", "entry_ref_price"]


def save_events(ev_df: pd.DataFrame, name: str, cfg: dict) -> Path:
    missing = [c for c in REQUIRED_COLS if c not in ev_df.columns]
    if missing:
        raise ValueError(f"eventi di {name}: mancano le colonne minime {missing}")
    out_dir = Path(cfg["data"]["raw_dir"]).parent / "screen"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"events_{name}.parquet"
    ev_df.to_parquet(out, index=False)
    return out
