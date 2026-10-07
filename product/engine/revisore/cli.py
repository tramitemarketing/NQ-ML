"""Riga di comando.

  python -m revisore audit trades.csv --market bars.parquet --n-tried 50 --cost 0.75 --point-value 20 --out report.html
  python -m revisore stats trades.csv --cost 0.75 --n-tried 50            (solo statistiche, senza mercato)
  python -m revisore lookahead --strategy mia_strategia.py:segnali --market bars.parquet

ATTENZIONE: --strategy ESEGUE il codice Python indicato. Usalo solo su codice che hai letto, oppure in
una macchina/contenitore isolato.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from .audit import AuditConfig, run_audit
from .lookahead import audit_lookahead
from .market import load_market
from .report import write_report
from .trades import load_trades


def _kv(s: str | None) -> dict:
    if not s:
        return {}
    out = {}
    for part in s.split(","):
        k, v = part.split("=", 1)
        out[k.strip()] = v.strip()
    return out


def load_strategy(spec: str):
    path, sep, name = spec.rpartition(":")
    if not sep or not name or any(c in name for c in "\\/.") or not path or path.endswith(("\\", "/")) or len(path) == 1:
        path, name = spec, "strategy"          # nessun ":funzione" (o solo la lettera di unità di Windows)
    sp = importlib.util.spec_from_file_location("strategia_cliente", path)
    mod = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(mod)
    return getattr(mod, name)


def _market_args(p):
    p.add_argument("--market", help="barre OHLCV (CSV o parquet), 1 minuto/intraday o giornaliere")
    p.add_argument("--market-cols", help="mappatura colonne mercato, es. open=Open,close=Last,volume=Vol")
    p.add_argument("--market-time-col", help="colonna temporale del mercato (se non è l'indice)")
    p.add_argument("--market-tz", default=None, help="fuso dei timestamp del mercato senza fuso (default = --tz)")
    p.add_argument("--no-adj", action="store_true", help="non usare le colonne adj_* anche se presenti")
    p.add_argument("--bar-label", default="start", choices=["start", "end"], help="le barre sono etichettate all'inizio o alla fine")
    p.add_argument("--session-start", default="17:00", help="ora locale d'inizio sessione (future CME: 17:00/18:00)")


def _common(p):
    p.add_argument("--tz", default="America/New_York", help="fuso degli orari senza fuso nel file dei trade")
    p.add_argument("--cols", help="mappatura colonne trade, es. entry_time=Entrata,exit_time=Uscita,side=Dir,pnl=Profitto,qty=Qta")
    p.add_argument("--pnl-unit", default="auto", choices=["auto", "points", "currency"])
    p.add_argument("--pnl-net", action="store_true", help="il P&L del file è già al netto dei costi")
    p.add_argument("--dayfirst", action="store_true", help="date nel formato giorno/mese/anno")
    p.add_argument("--n-tried", type=int, default=1, help="quante varianti/strategie sono state provate (per il DSR)")
    p.add_argument("--cost", type=float, default=0.0, help="costo andata e ritorno in punti per unità")
    p.add_argument("--point-value", type=float, default=1.0, help="valuta per punto (NQ 20, ES 50)")
    p.add_argument("--currency", default="$")
    p.add_argument("--is-end", help="ultimo giorno del periodo di costruzione/ottimizzazione (AAAA-MM-GG)")
    p.add_argument("--sr-var", type=float, help="varianza degli Sharpe (giornalieri) fra i tentativi, se nota")
    p.add_argument("--top-k", type=int)
    p.add_argument("--n-boot", type=int, default=10000)
    p.add_argument("--n-placebo", type=int, default=1000)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--rth", default="09:30-16:00", help="finestra diurna per la scomposizione del movimento")


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="revisore", description="Revisore di backtest - motore Pro")
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("audit", help="audit completo e report HTML")
    a.add_argument("trades")
    _common(a)
    _market_args(a)
    a.add_argument("--strategy", help="file.py:funzione  fn(bars)->trades, per l'audit del look-ahead (esegue codice!)")
    a.add_argument("--out", default="report.html")
    a.add_argument("--json", help="salva anche un riassunto JSON")
    a.add_argument("--title", default="Revisione del backtest")
    a.add_argument("--client", default="")
    a.add_argument("--instrument", default="")
    s = sub.add_parser("stats", help="solo statistiche (senza mercato), stampa a video")
    s.add_argument("trades")
    _common(s)
    lk = sub.add_parser("lookahead", help="solo audit del look-ahead")
    lk.add_argument("--strategy", required=True)
    _market_args(lk)
    lk.add_argument("--start")
    lk.add_argument("--end")
    return ap


def _load_market(args, start=None, end=None):
    return load_market(args.market, tz=args.market_tz or getattr(args, "tz", "America/New_York"),
                       columns=_kv(args.market_cols), time_col=args.market_time_col, prefer_adj=not args.no_adj,
                       session_start=args.session_start, bar_label=args.bar_label, start=start, end=end)


def _cfg(args, **kw) -> AuditConfig:
    return AuditConfig(n_tried=args.n_tried, cost=args.cost, point_value=args.point_value, pnl_is_net=args.pnl_net,
                       tz=args.tz, session_start=getattr(args, "session_start", "17:00"), rth=args.rth,
                       is_end=args.is_end, n_boot=args.n_boot, n_placebo=args.n_placebo, seed=args.seed,
                       top_k=args.top_k, sr_var=args.sr_var, currency=args.currency, **kw)


def summary(R: dict) -> dict:
    v = R["verdict"]
    out = {"grade": v["grade"], "headline": v["headline"], "reasons": v["reasons"], "flags": v["flags"],
           "n": R["basic"]["n"], "net_mean_pts": R["basic"]["net_mean"], "p_pos": R["boot"]["p_pos"],
           "dsr": R["dsr"]["dsr"], "psr": R["dsr"]["psr"], "sharpe_ann": R["sharpe_ann"],
           "checks": [{k: c[k] for k in ("key", "status", "value")} for c in R["checks"]]}
    if R.get("beta"):
        out["beta_mean_pts"] = R["beta"]["beta_mean"]
        out["net_minus_beta_p"] = R["beta"]["stat_adj"]["p_pos"]
    if R.get("placebo"):
        out["placebo_percentiles"] = {k: s["percentile"] for k, s in R["placebo"]["scenarios"].items()}
    out["decay"] = {"ratio": R["decay"]["ratio"], "class": R["decay"]["class"], "true_oos": R["decay"]["true_oos"]}
    if R.get("lookahead"):
        out["lookahead_ok"] = R["lookahead"]["ok"]
    return out


def main(argv=None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:  # noqa: BLE001
        pass
    args = build_parser().parse_args(argv)
    if args.cmd == "lookahead":
        m = _load_market(args, args.start, args.end)
        fn = load_strategy(args.strategy)
        res = audit_lookahead(fn, m.bars)
        print("OK: nessun look-ahead" if res["ok"] else f"LOOK-AHEAD: {len(res['problems'])} violazioni")
        for p in res["problems"][:20]:
            print(f"  T={p['T']} ({'+' if p['direction'] > 0 else '-'}): {p['problem']}")
        return 0 if res["ok"] else 2
    tr = load_trades(args.trades, columns=_kv(args.cols), tz=args.tz, pnl_unit=args.pnl_unit,
                     point_value=args.point_value, dayfirst=args.dayfirst)
    if args.cmd == "stats":
        R = run_audit(tr, None, _cfg(args))
        print(json.dumps(summary(R), ensure_ascii=False, indent=1, default=float))
        return 0
    market = None
    if args.market:
        start = tr["entry_ts"].min() - pd.Timedelta(days=10)
        end = tr["exit_ts"].max() + pd.Timedelta(days=3)
        market = _load_market(args, start, end)
    strategy = load_strategy(args.strategy) if args.strategy else None
    R = run_audit(tr, market, _cfg(args, title=args.title, client=args.client, instrument=args.instrument),
                  strategy=strategy)
    write_report(R, args.out)
    sm = summary(R)
    if args.json:
        Path(args.json).write_text(json.dumps(sm, ensure_ascii=False, indent=1, default=float), encoding="utf-8")
    print(f"Verdetto {sm['grade']}: {sm['headline']}")
    for r in sm["reasons"]:
        print("  -", r)
    print(f"Report: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
