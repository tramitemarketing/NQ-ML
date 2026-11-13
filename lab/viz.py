"""Salva il grafico di un test perché la dashboard possa mostrarlo (`python -m lab.dashboard`, scena «Figura»).

Si chiama dentro lo script di un test, accanto a `core.record`, con dati GIÀ aggregati:

    from lab import viz
    viz.bars("r10_fib", "T1", "per_anno", title="Netto medio per anno", labels=anni, values=netti,
             ylabel="punti NQ netti per trade")
    viz.placebo("r9_dol", "T2", "reale_vs_placebo", title="DOL contro livello specchio",
                real=0.4895, placebo_values=quote_placebo, xlabel="quota di tocchi")

Ogni chiamata scrive un file JSON in `lab/figures/<family>/<test_id>__<name>.json` e basta: non tocca registri,
verdetti o dati. Usa solo la libreria standard; accetta liste, array numpy e Series pandas.

REGOLA DEI DATI. Qui vanno solo aggregati: medie, quote, conteggi, istogrammi, curve di sintesi. Mai prezzi,
barre o tick grezzi: i dati di mercato hanno una licenza e questi file finiscono in video pubblici. Per questo
ogni serie è limitata a MAX_POINTS punti e la funzione si rifiuta di scriverne di più.
"""
from __future__ import annotations

import datetime as dt
import json
import math
import re
from pathlib import Path

FIG_DIR = Path(__file__).resolve().parent / "figures"
MAX_POINTS = 2000
MAX_SERIES = 4          # oltre quattro serie un grafico non si legge: si fanno più figure
_SAFE = re.compile(r"[^A-Za-z0-9_.-]+")


def _list(x) -> list:
    """Lista di numeri Python (None al posto di NaN/inf) da lista, array numpy o Series pandas."""
    if hasattr(x, "tolist"):
        x = x.tolist()
    out = []
    for v in x:
        if v is None:
            out.append(None)
            continue
        v = float(v)
        out.append(v if math.isfinite(v) else None)
    return out


def _labels(x) -> list[str]:
    if hasattr(x, "tolist"):
        x = x.tolist()
    return [str(v) for v in x]


def _check(n: int, what: str) -> None:
    if n > MAX_POINTS:
        raise ValueError(f"{what}: {n} punti, il massimo è {MAX_POINTS}. Qui vanno solo aggregati "
                         "(medie, quote, istogrammi), mai prezzi o tick grezzi: aggrega prima di salvare.")
    if n == 0:
        raise ValueError(f"{what}: nessun punto da salvare.")


def _write(family: str, test_id: str, name: str, kind: str, title: str, body: dict, *, xlabel: str = "",
           ylabel: str = "", note: str = "", demo: bool = False, fig_dir: Path | None = None) -> Path:
    root = FIG_DIR if fig_dir is None else Path(fig_dir)
    fam = _SAFE.sub("_", str(family))
    path = root / fam / f"{_SAFE.sub('_', str(test_id))}__{_SAFE.sub('_', str(name))}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    fig = {"v": 1, "type": kind, "family": str(family), "test_id": str(test_id), "name": str(name),
           "title": str(title), "xlabel": str(xlabel), "ylabel": str(ylabel), "note": str(note),
           "demo": bool(demo), "ts": dt.datetime.now().isoformat(timespec="seconds"), **body}
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(fig, ensure_ascii=False, allow_nan=False), encoding="utf-8")
    tmp.replace(path)                      # scrittura atomica: la dashboard non legge mai un file a metà
    return path


def line(family: str, test_id: str, name: str, *, title: str, x, series: dict, marker: dict | None = None,
         **meta) -> Path:
    """Una o più curve sullo stesso asse. `series` = {"nome": valori}, tutte lunghe come `x`.

    `x` numerico oppure etichette (anni, date come testo). `marker` facoltativo = {"x": ..., "y": ..., "label": ...}
    per segnare un punto (per esempio il δ80 su una curva di potenza). Un solo asse y: due misure con scale
    diverse vanno in due figure.
    """
    xs = x.tolist() if hasattr(x, "tolist") else list(x)
    numeric = all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in xs)
    _check(len(xs), "line")
    if not 1 <= len(series) <= MAX_SERIES:
        raise ValueError(f"line: da 1 a {MAX_SERIES} serie, ricevute {len(series)}.")
    out = []
    for nm, vals in series.items():
        vals = _list(vals)
        if len(vals) != len(xs):
            raise ValueError(f"line: la serie «{nm}» ha {len(vals)} valori, x ne ha {len(xs)}.")
        out.append({"name": str(nm), "y": vals})
    body = {"x": _list(xs) if numeric else _labels(xs), "x_numeric": numeric, "series": out, "marker": marker}
    return _write(family, test_id, name, "line", title, body, **meta)


def bars(family: str, test_id: str, name: str, *, title: str, labels, values, lo=None, hi=None, **meta) -> Path:
    """Barre con base a zero (per anno, per fascia oraria, per gruppo). `lo`/`hi` facoltativi = intervallo."""
    lab, val = _labels(labels), _list(values)
    _check(len(val), "bars")
    if len(lab) != len(val):
        raise ValueError(f"bars: {len(lab)} etichette e {len(val)} valori.")
    body = {"labels": lab, "values": val, "lo": _list(lo) if lo is not None else None,
            "hi": _list(hi) if hi is not None else None}
    for k in ("lo", "hi"):
        if body[k] is not None and len(body[k]) != len(val):
            raise ValueError(f"bars: «{k}» ha {len(body[k])} valori, le barre sono {len(val)}.")
    return _write(family, test_id, name, "bars", title, body, **meta)


def scatter(family: str, test_id: str, name: str, *, title: str, x, y, **meta) -> Path:
    """Nuvola di punti aggregati (un punto per giorno, per mese, per cella), non un punto per barra."""
    xs, ys = _list(x), _list(y)
    _check(len(xs), "scatter")
    if len(xs) != len(ys):
        raise ValueError(f"scatter: x ha {len(xs)} valori, y ne ha {len(ys)}.")
    return _write(family, test_id, name, "scatter", title, {"x": xs, "y": ys}, **meta)


def _bin(values: list[float], bins: int, lo: float | None = None, hi: float | None = None):
    vals = [v for v in values if v is not None]
    if not vals:
        raise ValueError("istogramma: nessun valore finito.")
    lo = min(vals) if lo is None else lo
    hi = max(vals) if hi is None else hi
    if hi <= lo:
        hi = lo + 1.0
    width = (hi - lo) / bins
    counts = [0] * bins
    for v in vals:
        if lo <= v <= hi:
            counts[min(bins - 1, int((v - lo) / width))] += 1
    return [lo + i * width for i in range(bins + 1)], counts, len(vals)


def hist(family: str, test_id: str, name: str, *, title: str, values, bins: int = 30, **meta) -> Path:
    """Istogramma. Salva solo i conteggi per classe, non i valori: va bene anche per migliaia di osservazioni."""
    edges, counts, n = _bin(_list(values), bins)
    return _write(family, test_id, name, "hist", title, {"edges": edges, "counts": counts, "n": n}, **meta)


def placebo(family: str, test_id: str, name: str, *, title: str, real: float, placebo_values, bins: int = 30,
            real_label: str = "reale", **meta) -> Path:
    """Il valore reale contro la distribuzione dei placebo. Salva i conteggi dei placebo e il valore reale.

    Salva anche la quota di placebo che fa almeno quanto il reale (dal lato del reale rispetto alla mediana):
    è una descrizione del grafico, non sostituisce il p pre-registrato del test.
    """
    vals = [v for v in _list(placebo_values) if v is not None]
    real = float(real)
    if not vals or not math.isfinite(real):
        raise ValueError("placebo: servono un valore reale finito e almeno un placebo.")
    lo, hi = min(vals + [real]), max(vals + [real])
    pad = (hi - lo) * 0.04 or 1.0
    edges, counts, n = _bin(vals, bins, lo - pad, hi + pad)
    med = sorted(vals)[len(vals) // 2]
    share = sum(1 for v in vals if (v >= real if real >= med else v <= real)) / len(vals)
    body = {"edges": edges, "counts": counts, "n": n, "real": real, "real_label": str(real_label),
            "placebo_median": med, "share_as_extreme": share}
    return _write(family, test_id, name, "placebo", title, body, **meta)
