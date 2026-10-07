"""Ramo B della pre-registrazione `docs/superpowers/specs/2026-09-23-preregistrazione-pendenza-e-estensione.md`:
eventi, etichette e PENDENZA anno per anno sui sei anni nuovi 2010-06-07 -> 2016-09-19.

Scrive tutto in `data/ext/` per NON toccare `data/events/events.parquet` ne' gli altri artefatti delle
milestone. Non legge nulla dopo il 2016-09-19: l'OOS (2023-10 -> 2026-03) e la cassaforte restano intatti.

Uso: .venv\\Scripts\\python scripts\\26_extension_2010_2016.py
"""
from __future__ import annotations

import datetime as dt
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

from nqml.config import config_hash, git_commit, load_config
from nqml.data.bars import load_bars, rth_bars, sessions_iter
from nqml.detector.run_day import run_day
from nqml.labels.labeler import label_event
from nqml.screen.wall2 import r_gross

EXT_START, EXT_END = dt.date(2010, 6, 7), dt.date(2016, 9, 20)   # fine esclusiva: il training parte il 2016-09-20


def slope(x: np.ndarray, y: np.ndarray) -> float:
    """Pendenza OLS in forma chiusa (niente polyfit: stessa scelta del resto del progetto)."""
    xm, ym = x.mean(), y.mean()
    den = ((x - xm) ** 2).sum()
    return float(((x - xm) * (y - ym)).sum() / den) if den > 0 else float("nan")


def block_bootstrap_slope(df: pd.DataFrame, n_boot: int = 4000, seed: int = 0) -> tuple[float, float]:
    """CI a blocchi per giorno della pendenza: ricampiona giornate intere."""
    rng = np.random.default_rng(seed)
    groups = [g[["x", "y"]].to_numpy() for _, g in df.groupby("session_date")]
    n = len(groups)
    out = np.empty(n_boot)
    for i in range(n_boot):
        idx = rng.integers(0, n, n)
        arr = np.vstack([groups[j] for j in idx])
        out[i] = slope(arr[:, 0], arr[:, 1])
    return float(np.nanpercentile(out, 2.5)), float(np.nanpercentile(out, 97.5))


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    t0 = time.time()
    cfg = load_config("config.yaml")
    out_dir = Path("data/ext"); out_dir.mkdir(parents=True, exist_ok=True)
    bars = load_bars(Path(cfg["data"]["raw_dir"]))

    ev_path, lab_path = out_dir / "events_ext.parquet", out_dir / "labels_ext.parquet"
    if ev_path.exists():
        events = pd.read_parquet(ev_path)
        print(f"eventi gia' in cache: {len(events)}")
    else:
        rows, n_days, n_valid = [], 0, 0
        for sd, day in sessions_iter(bars):
            if not (EXT_START <= sd < EXT_END):
                continue
            n_days += 1
            res = run_day(day, sd, cfg)
            n_valid += int(res.valid)
            rows.extend(res.events)
            if n_days % 200 == 0:
                print(f"  detector: {n_days} sessioni, {len(rows)} eventi ({time.time()-t0:.0f}s)", flush=True)
        events = pd.DataFrame(rows)
        events.to_parquet(ev_path, index=False)
        print(f"detector: {n_days} sessioni ({n_valid} valide), {len(events)} eventi ({time.time()-t0:.0f}s)", flush=True)

    assert pd.to_datetime(events["session_date"]).dt.date.max() < EXT_END, "evento oltre il confine dell'estensione"

    # --- etichettatura con le convenzioni pre-registrate (trade-through sul target) ---
    if lab_path.exists():
        lab = pd.read_parquet(lab_path)
        print(f"etichette gia' in cache: {len(lab)}")
    else:
        days_rth = {}
        for sd, day in sessions_iter(bars):
            if EXT_START <= sd < EXT_END:
                r = rth_bars(day, cfg["sessions"]["rth_open"], cfg["sessions"]["rth_close"])
                if len(r) >= cfg["sessions"]["min_rth_bars"]:
                    days_rth[sd] = r
        rows = []
        for i, r in enumerate(events.to_dict("records")):
            rth = days_rth.get(pd.Timestamp(r["session_date"]).date() if not isinstance(r["session_date"], dt.date) else r["session_date"])
            if rth is None:
                continue
            g = r_gross(r, rth, cfg)                      # target a trade-through di 1 tick, time stop al close
            atr_col = r.get("atr_14_5m", np.nan)
            rows.append(dict(event_id=r["event_id"], session_date=r["session_date"], side=r["side"],
                             rr=abs(r["target_price"] - r["entry_ref_price"]) / abs(r["entry_ref_price"] - r["stop_price"]),
                             pnl_pts=g["pnl_pts"], r_unit_pts=g["r_unit_pts"], R_gross=g["R_gross"],
                             exit_reason=g["exit_reason"], atr=atr_col))
            if (i + 1) % 3000 == 0:
                print(f"  etichette: {i+1}/{len(events)} ({time.time()-t0:.0f}s)", flush=True)
        lab = pd.DataFrame(rows)
        lab.to_parquet(lab_path, index=False)
        print(f"etichette: {len(lab)} ({time.time()-t0:.0f}s)", flush=True)

    # --- ATR(14) su barre 5m del giorno precedente, come nel resto del progetto ---
    from nqml.screen.atr import previous_day_atr
    atr_map = previous_day_atr(bars, cfg) if callable(previous_day_atr) else {}
    lab["session_date"] = pd.to_datetime(lab["session_date"]).dt.date
    lab["atr"] = lab["session_date"].map(atr_map) if atr_map else lab["atr"]

    d = lab.dropna(subset=["atr", "rr", "pnl_pts"]).copy()
    d = d[(d["rr"] > 0) & (d["atr"] > 0) & (d["exit_reason"] != "gap")]
    d["y"] = d["pnl_pts"] / d["atr"]
    d["x"] = np.log(d["rr"])
    d["anno"] = pd.to_datetime(d["session_date"]).dt.year
    d = d.replace([np.inf, -np.inf], np.nan).dropna(subset=["x", "y"])

    print(f"\n=== RAMO B — PENDENZA SUI SEI ANNI NUOVI (n {len(d)}) ===", flush=True)
    s_tot = slope(d["x"].to_numpy(), d["y"].to_numpy())
    lo, hi = block_bootstrap_slope(d)
    print(f"pendenza complessiva 2010-2016: {s_tot:+.4f} [{lo:+.4f}, {hi:+.4f}]")
    per = d.groupby("anno").apply(lambda g: slope(g["x"].to_numpy(), g["y"].to_numpy()), include_groups=False)
    n_per = d.groupby("anno").size()
    print("\npendenza per anno (nuovi):")
    for a in per.index:
        print(f"  {a}: {per[a]:+.4f}   (n {n_per[a]})")
    print(f"\nanni negativi fra i nuovi: {(per < 0).sum()}/{len(per)}")

    res = pd.DataFrame({"anno": per.index, "pendenza": per.values, "n": n_per.values})
    res.to_parquet(out_dir / "pendenza_per_anno_ext.parquet", index=False)
    (out_dir / "ramo_b_riassunto.txt").write_text(
        f"config {config_hash('config.yaml')} commit {git_commit()}\n"
        f"n {len(d)} | pendenza complessiva {s_tot:+.4f} [{lo:+.4f}, {hi:+.4f}]\n"
        + "\n".join(f"{a}: {per[a]:+.4f} (n {n_per[a]})" for a in per.index) + "\n", encoding="utf-8")
    print(f"\nscritti data/ext/pendenza_per_anno_ext.parquet e ramo_b_riassunto.txt ({time.time()-t0:.0f}s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
