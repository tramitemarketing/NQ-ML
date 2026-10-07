"""Sguardo #3 (spec §12-ter): criteri G1/P1/S1/G2 sui tre bracci 1c e report. Uso: .venv\\Scripts\\python scripts\\10_report_1c.py"""
from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

import pandas as pd

from nqml.config import config_hash, git_commit, load_config
from nqml.model.walkforward import assert_no_vault, make_folds, trading_dates
from nqml.report.compare import decision_overlap, paired_frame, paired_mean_r
from nqml.report.criteria_1c import evaluate_1c, render_1c


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    cfg = load_config("config.yaml")
    md_dir = Path(cfg["model"]["model_dir"])
    a, b, a1 = (pd.read_parquet(md_dir / f"predictions_{t}.parquet") for t in ("1c_A", "1c_B", "1c_A_seed1"))
    for df in (a, b, a1):
        assert_no_vault(df, cfg)
    sampled = pd.read_parquet(Path(cfg["tick"]["tick_dir"]) / "sampled_days.parquet")
    bn, bs = cfg["backtest"]["bootstrap_n"], cfg["backtest"]["bootstrap_seed"]
    res = evaluate_1c(a, b, a1, sampled, bn, bs)
    folds_a = json.load(open(md_dir / "sanity_1c_A.json", encoding="utf-8"))["folds"]
    folds_b = json.load(open(md_dir / "sanity_1c_B.json", encoding="utf-8"))["folds"]
    sa = [f["auc_shuffle"] for f in folds_a]
    sb = [f["auc_shuffle"] for f in folds_b]
    # I1 (§12-ter emendato): variante shuffle a offset fisso — registrazione originaria, solo riportata, nessuna banda.
    sa_fixed = [sum(f["auc_shuffle_fixed_offset_seeds"]) / len(f["auc_shuffle_fixed_offset_seeds"]) for f in folds_a]
    sb_fixed = [sum(f["auc_shuffle_fixed_offset_seeds"]) / len(f["auc_shuffle_fixed_offset_seeds"]) for f in folds_b]
    # M1 (§12-ter riga D): R medio B − A appaiato per giorno e Jaccard delle decisioni, stessi giorni di test di 07.
    days = pd.read_parquet(Path(cfg["data"]["events_dir"]) / "days.parquet")
    dates = trading_dates(days, cfg)
    folds = make_folds(dates, cfg)
    test_days = [d for d in dates if any(f.test_start <= d <= f.test_end for f in folds)]
    pf = paired_frame(a, b)
    res["mean_r_b_vs_a"] = paired_mean_r(pf, test_days, bn, bs)
    res["overlap"] = decision_overlap(pf)
    head = (f"# Report OOS — 1c (sguardo #3)\n\nGenerato il {dt.date.today().isoformat()} · config `{config_hash('config.yaml')}` · "
            f"commit `{git_commit()}` · bootstrap {bn} / seed {bs}\n\n")
    out = Path(cfg["backtest"]["reports_dir"]) / "oos_report_1c.md"
    out.write_text(head + render_1c(res, sa, sb, sa_fixed, sb_fixed), encoding="utf-8")
    print(out.read_text(encoding="utf-8"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
