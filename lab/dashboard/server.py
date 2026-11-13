"""Dashboard «Scena» del laboratorio: legge i registri e li serve a una pagina locale.

Legge soltanto file che il laboratorio scrive già:
- `lab/ledger/*.jsonl`   una riga per ogni test guardato (`core.record`);
- `lab/verdicts/*.json`  i verdetti del controller;
- `lab/figures/**/*.json` i grafici salvati con `lab.viz` (facoltativi).

Non carica barre, non importa `lab.core`, non esegue test e non scrive nulla. Usa solo la libreria standard.
Ascolta su 127.0.0.1: la pagina si vede solo da questo computer.

Uso: python -m lab.dashboard            (poi apri http://127.0.0.1:8765)
     python -m lab.dashboard --demo     (aggiunge le figure finte di `lab/dashboard/demo.py`)
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from statistics import NormalDist

LAB = Path(__file__).resolve().parents[1]
HERE = Path(__file__).resolve().parent
N01 = NormalDist()
Z80 = N01.inv_cdf(0.80)
Z_CAP = 5.0            # i p del bootstrap hanno risoluzione finita: oltre questo valore lo z non è informativo
P_FLOOR = 1e-4         # 10.000 repliche di bootstrap: un p registrato come 0 vale «meno di 1 su 10.000»
PREFIXES = ("fade", "cont")  # righe che registrano due risultati (stesso evento, due versi)
DESC_MAX = 260


def _num(x) -> float | None:
    """Numero finito oppure None (nel registro ci sono None, NaN e stringhe)."""
    if isinstance(x, bool) or not isinstance(x, (int, float)):
        return None
    return float(x) if math.isfinite(x) else None


def z_from(mean, p_two, t=None) -> float | None:
    """z con segno. Da `t` se c'è, altrimenti dal p bilaterale e dal segno della media.

    Non si ricava mai z da media e intervallo senza un p: per molte regolarità l'ipotesi nulla non è zero
    (un rapporto di varianze vale 1), quindi media/errore standard non sarebbe un test.
    """
    t = _num(t)
    if t is not None:
        return max(-Z_CAP, min(Z_CAP, t))
    mean, p_two = _num(mean), _num(p_two)
    if mean is None or p_two is None or mean == 0:
        return None
    p = min(1.0, max(P_FLOOR, p_two))
    z = N01.inv_cdf(1 - p / 2)
    return max(-Z_CAP, min(Z_CAP, math.copysign(z, mean)))


def z_limited(p_two=None, t=None, p_one=None) -> bool:
    """True se lo z è un limite e non una misura: il p registrato è al minimo del bootstrap (1 su 10.000) oppure
    `t` supera Z_CAP. In quel caso la distanza vera è più grande di quella mostrata e la pagina scrive «oltre»."""
    t, p_two, p_one = _num(t), _num(p_two), _num(p_one)
    if t is not None:
        return abs(t) > Z_CAP
    eps = P_FLOOR * (1 + 1e-9)
    if p_two is not None:
        return p_two <= eps
    return p_one is not None and (p_one <= eps or p_one >= 1 - eps)


def _result(row: dict, prefix: str = "") -> dict | None:
    """Estrae un risultato (media, intervallo, p, anni) da una riga, al livello principale o con un prefisso."""
    k = (lambda name: f"{prefix}_{name}") if prefix else (lambda name: name)
    mean = _num(row.get(k("mean")))
    is_coef = False
    if mean is None and not prefix:
        mean = _num(row.get("b"))            # regressioni: coefficiente
        is_coef = mean is not None
    p_two = _num(row.get(k("p_two")))
    z = z_from(mean, p_two, None if prefix else row.get("t"))
    if mean is None and z is None:
        return None
    yearly = row.get(k("yearly"))
    if isinstance(yearly, dict):
        yearly = {str(y): v for y, v in ((y, _num(v)) for y, v in yearly.items()) if v is not None}
    else:
        yearly = None
    return {
        "mean": mean, "lo": _num(row.get(k("lo"))), "hi": _num(row.get(k("hi"))),
        "p": p_two if p_two is not None else (_num(row.get("p_one")) if not prefix else None),
        "p_kind": "two" if p_two is not None else ("one" if _num(row.get("p_one")) is not None and not prefix else None),
        "z": z, "z_lim": z is not None and z_limited(p_two, None if prefix else row.get("t")),
        "n": _num(row.get(k("n"))) if _num(row.get(k("n"))) is not None else _num(row.get("n")),
        "yearly": yearly or None, "years_pos": row.get(k("years_pos")),
        "gross": _num(row.get(k("mean_gross"))) if _num(row.get(k("mean_gross"))) is not None else _num(row.get("gross")),
        "placebo_p": _num(row.get("placebo_p")) if not prefix else None, "is_coef": is_coef,
    }


def z_from_one_sided(p) -> float | None:
    """z da un p a una coda con ipotesi «risultato > 0»: p piccolo → z positivo, p vicino a 1 → z negativo."""
    p = _num(p)
    if p is None:
        return None
    p = min(1.0 - P_FLOOR, max(P_FLOOR, p))
    return max(-Z_CAP, min(Z_CAP, N01.inv_cdf(1 - p)))


def _yearly(obj) -> dict | None:
    """{anno: valore} da {anno: numero} oppure da {anno: {"mean" | "netto_pt": numero, ...}}."""
    if not isinstance(obj, dict):
        return None
    out = {}
    for y, v in obj.items():
        if isinstance(v, dict):
            v = v.get("mean") if _num(v.get("mean")) is not None else v.get("netto_pt")
        v = _num(v)
        if v is not None and str(y)[:4].isdigit():
            out[str(y)] = v
    return out or None


def _result_alt(row: dict) -> dict | None:
    """Le forme dei giri 8, 9 e 10, verificate riga per riga sul registro (2026-11-13).

    - blocco `netto` (r9 T3, r10 Z e L618): media netta con intervallo e `p_two` a due code contro 0; il `p` in cima è
      il p a una coda del test (netto > 0). z dal `p_two` e dal segno, come per gli altri risultati netti.
    - `mean_net_R` (r8, prove di futilità): media e intervallo, nessun p per scelta del PREREG. Quindi nessuno z:
      la dashboard non calcola una statistica che il laboratorio ha deciso di non registrare.
    - `diff` con `p` a una coda (r9 T2, r10 LIV): differenza reale − placebo, ipotesi «diff > 0». z dal p a una coda.
    """
    p_one = _num(row.get("p"))
    netto = row.get("netto")
    empty = {"lo": None, "hi": None, "p": None, "p_kind": None, "z": None, "z_lim": False, "n": None, "yearly": None,
             "years_pos": None, "gross": None, "placebo_p": None, "is_coef": False, "stat": "mean", "unit_hint": None}
    if isinstance(netto, dict) and _num(netto.get("mean")) is not None:
        mean, p_two = _num(netto["mean"]), _num(netto.get("p_two"))
        base = row.get("base") if isinstance(row.get("base"), dict) else {}
        crit = row.get("criteri") if isinstance(row.get("criteri"), dict) else {}
        z = z_from(mean, p_two)
        in_points = _num(base.get("netto_pt")) is not None and abs(base["netto_pt"] - mean) < 1e-9
        return {**empty, "mean": mean, "lo": _num(netto.get("lo")), "hi": _num(netto.get("hi")),
                "p": p_one if p_one is not None else p_two, "p_kind": "one" if p_one is not None else ("two" if p_two is not None else None),
                "z": z if z is not None else z_from_one_sided(p_one),
                "z_lim": z_limited(p_two) if z is not None else z_limited(p_one=p_one), "n": _num(netto.get("n")),
                "p2": p_two if p_one is not None else None,   # lo z viene da questo: la pagina lo mostra accanto al p a una coda
                "yearly": _yearly(row.get("per_anno")) or _yearly(crit.get("years")), "years_pos": crit.get("years_pos"),
                "gross": _num(base.get("lordo_pt")), "unit_hint": "punti netti per trade" if in_points else None}
    if _num(row.get("mean_net_R")) is not None:
        return {**empty, "mean": _num(row["mean_net_R"]), "lo": _num(row.get("lo")), "hi": _num(row.get("hi")),
                "n": _num(row.get("n")), "yearly": _yearly(row.get("per_anno")), "years_pos": row.get("anni_positivi"),
                "gross": _num(row.get("gross_R")), "unit_hint": "R netti per trade"}
    if _num(row.get("diff")) is not None and p_one is not None:
        boot = row.get("boot") if isinstance(row.get("boot"), dict) else {}
        lo = _num(row.get("lo")) if _num(row.get("lo")) is not None else _num(boot.get("lo"))
        hi = _num(row.get("hi")) if _num(row.get("hi")) is not None else _num(boot.get("hi"))
        return {**empty, "mean": _num(row["diff"]), "lo": lo, "hi": hi, "p": p_one, "p_kind": "one",
                "z": z_from_one_sided(p_one), "z_lim": z_limited(p_one=p_one), "stat": "diff"}
    return None


def read_ledger(ledger_dir: Path) -> tuple[list[dict], int]:
    """Tutte le righe del registro in ordine di tempo. Ritorna (risultati, numero di righe)."""
    rows = []
    for f in sorted(ledger_dir.glob("*.jsonl")):
        with open(f, encoding="utf-8") as fh:
            for ln, line in enumerate(fh):
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue                     # riga a metà scrittura: la si vede al prossimo giro
                if isinstance(row, dict) and "test_id" in row:
                    rows.append((str(row.get("ts", "")), f.name, ln, row))
    rows.sort(key=lambda r: r[:3])
    out = []
    for i, (ts, _, _, row) in enumerate(rows):
        base = {"row": i, "ts": ts, "fam": str(row.get("family", "?")), "id": str(row.get("test_id", "?")),
                "phase": str(row.get("phase", "?")), "kind": row.get("kind"), "unit": row.get("unit"),
                "control": row.get("kind") == "control",   # righe di controllo del laboratorio: non sono test di ipotesi
                "desc": str(row.get("description", ""))[:DESC_MAX]}
        found = False
        top = _result(row)
        if top is not None and (top["z"] is not None or top["yearly"] or top["lo"] is not None):
            out.append({**base, "label": "", **top})
            found = True
        if not found or top is None or top["z"] is None:
            for p in PREFIXES:
                r = _result(row, p)
                if r is not None and r["z"] is not None:
                    out.append({**base, "label": p, **r})
                    found = True
        if not found:
            alt = _result_alt(row)
            if alt is not None:
                hint = alt.pop("unit_hint")
                out.append({**base, "label": "", **alt, "unit": base["unit"] or hint})
                found = True
        if not found:
            out.append({**base, "label": "", "mean": None, "lo": None, "hi": None, "p": None, "p_kind": None,
                        "z": None, "z_lim": False, "n": _num(row.get("n")), "yearly": None, "years_pos": None, "gross": None,
                        "placebo_p": None, "is_coef": False})
    return out, len(rows)


def read_verdicts(verdict_dir: Path) -> list[dict]:
    """Verdetti del controller con errore standard ed effetto minimo visibile, come `lab/potenza.py`."""
    seen, out = set(), []
    for f in sorted(verdict_dir.glob("*.json")):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        for v in data if isinstance(data, list) else []:
            key = (v.get("id"), v.get("phase"))
            s = v.get("stat") or {}
            mean, lo, hi, alpha = _num(s.get("mean")), _num(s.get("lo")), _num(s.get("hi")), _num(v.get("alpha"))
            if key in seen or None in (mean, lo, hi):
                continue
            seen.add(key)
            se = (hi - lo) / (2 * 1.96)
            mde = zc = None
            if alpha and 0 < alpha < 1 and se > 0:
                zc = N01.inv_cdf(1 - alpha / 2) if v.get("kind") == "regularity" else N01.inv_cdf(1 - alpha)
                mde = (zc + Z80) * se
            out.append({"id": str(v.get("id")), "fam": str(v.get("family", "")), "kind": v.get("kind"),
                        "phase": v.get("phase"), "k": v.get("k"), "alpha": alpha,
                        "n": _num(s.get("n_days")) or _num(v.get("n")), "mean": mean, "lo": lo, "hi": hi,
                        "p": _num(s.get("p_two")), "se": se, "zc": zc, "mde80": mde, "verdict": str(v.get("verdict", "?")),
                        "file": f.name})
    order = {"validation": 0, "confirmation": 1}
    out.sort(key=lambda v: (order.get(v["phase"], 2), v["kind"] != "tradeable", v["id"]))
    return out


def read_figures(fig_dir: Path, demo: bool) -> list[dict]:
    out = []
    if not fig_dir.exists():
        return out
    for f in sorted(fig_dir.rglob("*.json")):
        try:
            fig = json.loads(f.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        if not isinstance(fig, dict) or "type" not in fig:
            continue
        if fig.get("demo") and not demo:
            continue
        fig["path"] = f.relative_to(fig_dir).as_posix()
        out.append(fig)
    return out


def build_state(lab: Path = LAB, demo: bool = False) -> dict:
    results, n_rows = read_ledger(lab / "ledger")
    fams: dict[str, int] = {}
    phases: dict[str, int] = {}
    seen, controls = set(), 0
    for r in results:
        if r["row"] in seen:
            continue
        seen.add(r["row"])
        if r["control"]:
            controls += 1
            continue
        fams[r["fam"]] = fams.get(r["fam"], 0) + 1
        phases[r["phase"]] = phases.get(r["phase"], 0) + 1
    zs = [r["z"] for r in results if r["z"] is not None and not r["control"]]
    ts = [r["ts"] for r in results if r["ts"]]
    return {
        "generated": dt.datetime.now().isoformat(timespec="seconds"),
        "lab": {"rows": n_rows - controls, "controls": controls, "with_z": len(zs), "families": sorted(fams.items(), key=lambda kv: -kv[1]),
                "phases": phases, "first_ts": min(ts) if ts else None, "last_ts": max(ts) if ts else None,
                "z_mean": sum(zs) / len(zs) if zs else None,
                "z_beyond": sum(1 for z in zs if abs(z) > 1.96), "z_above": sum(1 for z in zs if z > 1.96),
                "z_below": sum(1 for z in zs if z < -1.96), "z_cap": Z_CAP,
                "z_lim": sum(1 for r in results if r["z"] is not None and r["z_lim"] and not r["control"])},
        "results": results,
        "verdicts": read_verdicts(lab / "verdicts"),
        "figures": read_figures(lab / "figures", demo),
    }


def signature(lab: Path = LAB) -> str:
    """Cambia quando un file dei registri cambia: la pagina la interroga per sapere se ricaricare."""
    parts = []
    for sub, pat in (("ledger", "*.jsonl"), ("verdicts", "*.json"), ("figures", "**/*.json")):
        d = lab / sub
        if d.exists():
            for f in sorted(d.glob(pat)):
                st = f.stat()
                parts.append(f"{f.name}:{st.st_size}:{st.st_mtime_ns}")
    return str(hash("|".join(parts)))


class _Cache:
    def __init__(self, lab: Path, demo: bool):
        self.lab, self.demo, self.sig, self.body, self.lock = lab, demo, None, b"", threading.Lock()

    def get(self) -> tuple[str, bytes]:
        with self.lock:
            sig = signature(self.lab)
            if sig != self.sig:
                state = build_state(self.lab, self.demo)
                state["sig"] = sig
                self.body = json.dumps(state, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")
                self.sig = sig
            return self.sig, self.body


def make_handler(cache: _Cache):
    class Handler(BaseHTTPRequestHandler):
        def _send(self, code: int, body: bytes, ctype: str) -> None:
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):  # noqa: N802 (nome imposto da http.server)
            path = self.path.split("?", 1)[0]
            if path in ("/", "/index.html"):
                self._send(200, (HERE / "index.html").read_bytes(), "text/html; charset=utf-8")
            elif path == "/api/sig":
                self._send(200, json.dumps({"sig": signature(cache.lab)}).encode(), "application/json")
            elif path == "/api/state":
                self._send(200, cache.get()[1], "application/json; charset=utf-8")
            else:
                self._send(404, b"not found", "text/plain")

        def log_message(self, *args):  # silenzioso: la pagina interroga ogni pochi secondi
            pass

    return Handler


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description="Dashboard «Scena» del laboratorio NQ-ML (solo lettura dei registri).")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--lab", type=Path, default=LAB, help="cartella lab/ da leggere (default: quella del repo)")
    ap.add_argument("--demo", action="store_true", help="mostra anche le figure finte marcate DEMO")
    ap.add_argument("--no-open", action="store_true", help="non aprire il browser")
    a = ap.parse_args(argv)
    srv = ThreadingHTTPServer(("127.0.0.1", a.port), make_handler(_Cache(a.lab.resolve(), a.demo)))
    url = f"http://127.0.0.1:{a.port}"
    print(f"Dashboard del laboratorio: {url}   (Ctrl+C per chiudere)")
    if not a.no_open:
        threading.Timer(0.6, webbrowser.open, args=(url,)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        srv.server_close()


if __name__ == "__main__":
    main()
