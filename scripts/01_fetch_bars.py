"""Scarica le barre 1m NQ per mese, con costo stampato prima e cache Parquet.
Uso: .venv\\Scripts\\python scripts\\01_fetch_bars.py [--yes]"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from nqml.config import load_config
from nqml.data.databento_client import (
    CostAboveThreshold, FetchSpec, cached_fetch_month, estimate_cost, guard_cost, make_client, month_ranges,
)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--yes", action="store_true", help="conferma il costo sopra soglia")
    args = ap.parse_args()

    cfg = load_config("config.yaml")
    d = cfg["data"]
    load_dotenv(".env")
    client = make_client(os.environ["DATABENTO_API_KEY"])
    out_dir = Path(d["raw_dir"]) / "ohlcv_1m"

    months = month_ranges(d["bars_start"], d["bars_end"])
    missing = [(s, e) for s, e in months if not (out_dir / f"{s[:7]}.parquet").exists()]
    print(f"mesi totali {len(months)}, mancanti {len(missing)}")
    if not missing:
        print("tutto in cache, nessuna chiamata")
        return 0

    total = 0.0
    for s, e in missing:
        total += estimate_cost(client, FetchSpec(d["dataset"], d["symbol"], d["stype_in"], d["bars_schema"], s, e))
    print(f"costo stimato per i mesi mancanti: ${total:.2f} (soglia auto ${d['max_auto_cost_usd']:.2f})")
    try:
        guard_cost(total, float(d["max_auto_cost_usd"]), confirmed=args.yes)
    except CostAboveThreshold as ex:
        print(f"FERMATO: {ex}")
        return 2

    rows = 0
    for i, (s, e) in enumerate(missing, 1):
        spec = FetchSpec(d["dataset"], d["symbol"], d["stype_in"], d["bars_schema"], s, e)
        df = cached_fetch_month(client, spec, out_dir / f"{s[:7]}.parquet")
        rows += len(df)
        print(f"[{i}/{len(missing)}] {s} -> {e}: {len(df)} barre")
    print(f"fatto: {rows} barre scaricate")
    return 0


if __name__ == "__main__":
    sys.exit(main())
