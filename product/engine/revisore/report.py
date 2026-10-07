"""Report HTML autonomo in italiano: verdetto A-F, semafori, spiegazioni semplici, grafici
matplotlib incorporati in base64. Nessuna dipendenza esterna al momento della lettura."""
from __future__ import annotations

import base64
import html
import io

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from .beta import hourly_profile  # noqa: E402
from .verdict import GREEN, GREY, RED, YELLOW, fmt  # noqa: E402

# palette (dataviz, istanza di riferimento): serie, polarità, neutri
BLUE, RED_C, ORANGE, AQUA = "#2a78d6", "#e34948", "#eb6834", "#1baf7a"
INK, INK2, MUTED, GRID, SURF = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#fcfcfb"
STATUS = {GREEN: "#0ca30c", YELLOW: "#fab219", RED: "#d03b3b", GREY: "#898781"}
STATUS_ICON = {GREEN: "✓", YELLOW: "!", RED: "✕", GREY: "–"}
STATUS_WORD = {GREEN: "superato", YELLOW: "da verificare", RED: "non superato", GREY: "non valutato"}
GRADE_COLOR = {"A": "#0ca30c", "B": "#5a9e1a", "C": "#c98500", "D": "#ec835a", "E": "#d03b3b", "F": "#8f1d1d"}

DISCLAIMER = ("Strumento educativo, non consulenza finanziaria. Il report valuta la solidità statistica di "
              "un backtest fornito dal cliente; non raccomanda l'acquisto o la vendita di strumenti finanziari, "
              "non garantisce risultati futuri e non tiene conto della situazione personale di nessuno. "
              "Il trading con leva può causare perdite superiori al capitale investito.")


def _style():
    plt.rcParams.update({
        "figure.facecolor": SURF, "axes.facecolor": SURF, "axes.edgecolor": GRID, "axes.labelcolor": INK2,
        "xtick.color": INK2, "ytick.color": INK2, "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6,
        "axes.spines.top": False, "axes.spines.right": False, "font.size": 9.5, "axes.titlesize": 10.5,
        "axes.titleweight": "bold", "axes.titlecolor": INK, "legend.frameon": False, "axes.axisbelow": True,
    })


def _png(fig) -> str:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=130, bbox_inches="tight")
    plt.close(fig)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def _img(src, alt):
    return f'<img src="{src}" alt="{html.escape(alt)}">'


# --------------------------------------------------------------------------- grafici
def fig_equity(R) -> str:
    eq, dd = R["equity"], R["dd"]["dd_curve"]
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(8.6, 4.4), sharex=True, gridspec_kw={"height_ratios": [2.3, 1]})
    x = eq.index
    a1.plot(x, eq.to_numpy(), color=BLUE, lw=1.6)
    a1.axhline(0, color=MUTED, lw=0.8)
    a1.set_title(f"Curva dei profitti al netto dei costi ({R['cfg']['currency']}, 1 unità)", loc="left")
    a2.fill_between(x, dd, 0, color=RED_C, alpha=0.35, lw=0)
    a2.plot(x, dd, color=RED_C, lw=1)
    a2.set_title("Drawdown (distanza dal massimo precedente)", loc="left")
    fig.tight_layout()
    return _png(fig)


def fig_boot(R) -> str:
    b = R["boot"]
    fig, ax = plt.subplots(figsize=(8.6, 2.8))
    ax.hist(b["dist"], bins=60, color=BLUE, alpha=0.75, edgecolor=SURF, lw=0.3)
    ax.axvline(0, color=INK, lw=1.2)
    ax.axvline(b["mean"], color=ORANGE, lw=2)
    ax.text(b["mean"], ax.get_ylim()[1] * 0.92, f"  media osservata {fmt(b['mean'])}", color=INK, va="top")
    ax.set_title("Quanto potrebbe variare la media per trade (bootstrap a blocchi per giorno)", loc="left")
    ax.set_xlabel("punti netti per trade")
    ax.set_yticks([])
    return _png(fig)


def fig_beta(R) -> str:
    be = R["beta"]
    sn, sa = be["stat_net"], be["stat_adj"]
    labels = ["Netto", "Beta\n(mercato)", "Netto meno beta\n(abilità)"]
    vals = [sn["mean"], be["beta_mean"], sa["mean"]]
    err = [[sn["mean"] - sn["lo"], 0, sa["mean"] - sa["lo"]], [sn["hi"] - sn["mean"], 0, sa["hi"] - sa["mean"]]]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(8.6, 3.0), gridspec_kw={"width_ratios": [1, 1.6]})
    cols = [BLUE, MUTED, AQUA]
    a1.bar(labels, vals, color=cols, width=0.6, yerr=err, capsize=4, ecolor=INK2)
    a1.axhline(0, color=INK, lw=0.8)
    a1.set_title("Punti per trade (con intervallo 95 %)", loc="left")
    prof = hourly_profile(_market_stub(R), be["profile"])
    c2 = [BLUE if v >= 0 else RED_C for v in prof.to_numpy()]
    a2.bar([str(h) for h in prof.index], prof.to_numpy(), color=c2, width=0.75)
    a2.axhline(0, color=INK, lw=0.8)
    a2.set_title("Deriva media del mercato per ora (punti per sessione)", loc="left")
    a2.tick_params(axis="x", labelsize=7.5)
    fig.tight_layout()
    return _png(fig)


class _Stub:
    def __init__(self, daily, session_start):
        self.daily, self.session_start = daily, session_start


def _market_stub(R):
    return _Stub(R["market_info"]["daily"], R["cfg"]["session_start"])


def fig_placebo(R) -> str:
    pl = R["placebo"]
    sc = pl["scenarios"]
    names = list(sc)
    fig, axes = plt.subplots(len(names), 1, figsize=(8.6, 1.9 * len(names)), sharex=True)
    axes = np.atleast_1d(axes)
    real = pl["real_net_mean"]
    for ax, nm in zip(axes, names):
        s = sc[nm]
        ax.hist(s["dist"], bins=50, color=MUTED, alpha=0.8, edgecolor=SURF, lw=0.3)
        ax.axvline(real, color=ORANGE, lw=2.2)
        ax.set_yticks([])
        ax.set_title(f"{s['label']} — strategia al percentile {fmt(s['percentile'], 1)}", loc="left", fontsize=9)
    axes[-1].set_xlabel("punti netti per trade (linea arancione = strategia reale, riprezzata sugli stessi dati)")
    fig.tight_layout()
    return _png(fig)


def fig_years(R) -> str:
    y = R["years"]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(8.6, 2.9), gridspec_kw={"width_ratios": [1.6, 1]})
    c = [BLUE if v > 0 else RED_C for v in y["mean"].to_numpy()]
    a1.bar([str(i) for i in y.index], y["mean"].to_numpy(), color=c, width=0.7)
    a1.axhline(0, color=INK, lw=0.8)
    a1.set_title("Media netta per trade, anno per anno (punti)", loc="left")
    a1.tick_params(axis="x", labelsize=8, rotation=45)
    dc = R["drop_top_curve"]
    ks = [0] + list(dc)
    vs = [R["basic"]["net_mean"]] + list(dc.values())
    a2.plot(ks, vs, color=BLUE, marker="o", ms=5, lw=1.8)
    a2.axhline(0, color=INK, lw=0.8)
    a2.set_title("Togliendo i trade migliori", loc="left")
    a2.set_xlabel("trade migliori tolti")
    fig.tight_layout()
    return _png(fig)


def fig_decay(R) -> str:
    dc = R["decay"]
    ins, oos = dc["is"], dc["oos"]
    fig, ax = plt.subplots(figsize=(5.2, 2.8))
    lab = ["Dentro il campione", "Fuori campione"] if dc["true_oos"] else ["Primi 2/3", "Ultimo 1/3"]
    v = [ins["mean"], oos["mean"]]
    e = [[ins["mean"] - ins["lo"], oos["mean"] - oos["lo"]], [ins["hi"] - ins["mean"], oos["hi"] - oos["mean"]]]
    ax.bar(lab, v, color=[BLUE, ORANGE], width=0.55, yerr=e, capsize=5, ecolor=INK2)
    ax.axhline(0, color=INK, lw=0.8)
    ax.set_title("Media netta per trade (punti, intervallo 95 %)", loc="left")
    return _png(fig)


# --------------------------------------------------------------------------- HTML
CSS = """
:root{color-scheme:light;--ink:#0b0b0b;--ink2:#52514e;--muted:#898781;--grid:#e1e0d9;--surf:#fcfcfb;--card:#ffffff;--accent:#2a78d6}
*{box-sizing:border-box}
body{margin:0;background:var(--surf);color:var(--ink);font:15px/1.55 -apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
main{max-width:920px;margin:0 auto;padding:28px 16px 60px}
h1{font-size:26px;margin:0 0 4px}h2{font-size:19px;margin:34px 0 8px;padding-top:12px;border-top:1px solid var(--grid)}
h3{font-size:15px;margin:18px 0 6px}
p{margin:6px 0 10px}.sub{color:var(--ink2);margin:0 0 18px}
.verdict{display:flex;gap:22px;align-items:center;background:var(--card);border:1px solid var(--grid);border-radius:14px;padding:18px 20px;margin:18px 0}
.grade{flex:0 0 auto;width:96px;height:96px;border-radius:16px;color:#fff;font-size:58px;font-weight:800;display:flex;align-items:center;justify-content:center}
.verdict .h{font-size:18px;font-weight:700;margin:0 0 6px}
.verdict ul{margin:4px 0 0;padding-left:18px;color:var(--ink2);font-size:14px}
.flags span{display:inline-block;font-size:12px;font-weight:700;padding:2px 9px;border-radius:99px;margin:6px 6px 0 0;border:1px solid}
table{border-collapse:collapse;width:100%;font-size:14px;background:var(--card)}
th,td{text-align:left;padding:8px 10px;border-bottom:1px solid var(--grid);vertical-align:top}
th{color:var(--ink2);font-weight:600;font-size:12.5px;text-transform:uppercase;letter-spacing:.03em}
td.num{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
.light{display:inline-flex;align-items:center;gap:7px;font-weight:600;white-space:nowrap}
.dot{width:20px;height:20px;border-radius:50%;color:#fff;font-size:12px;font-weight:800;display:inline-flex;align-items:center;justify-content:center}
.why{color:var(--ink2);font-size:13px}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:10px;margin:10px 0}
.kpi{background:var(--card);border:1px solid var(--grid);border-radius:10px;padding:10px 12px}
.kpi .l{color:var(--ink2);font-size:12.5px}.kpi .v{font-size:20px;font-weight:700;font-variant-numeric:tabular-nums}
img{max-width:100%;height:auto;display:block;margin:8px 0 4px;border-radius:8px}
.box{background:#f3f2ee;border-radius:10px;padding:10px 14px;margin:10px 0;font-size:14px}
.warn{background:#fff4dc;border-left:4px solid #fab219}
.bad{background:#fde8e8;border-left:4px solid #d03b3b}
.disc{margin-top:36px;padding:14px 16px;border:1px solid var(--grid);border-radius:10px;color:var(--ink2);font-size:13px}
.table-wrap{overflow-x:auto}
@media (max-width:600px){.verdict{flex-direction:column;align-items:flex-start}.grade{width:76px;height:76px;font-size:44px}}
@media print{h2{break-before:auto}.verdict,.kpi,img{break-inside:avoid}}
"""


def _light(status):
    return (f'<span class="light"><span class="dot" style="background:{STATUS[status]}">{STATUS_ICON[status]}</span>'
            f'{STATUS_WORD[status]}</span>')


def _kpi(label, value):
    return f'<div class="kpi"><div class="l">{html.escape(label)}</div><div class="v">{value}</div></div>'


def _money(R, pts):
    pv = R["cfg"]["point_value"]
    return f"{fmt(pts * pv)} {R['cfg']['currency']}"


def render(R: dict) -> str:
    _style()
    cfg = R["cfg"]
    v = R["verdict"]
    e = html.escape
    b, bs = R["boot"], R["basic"]
    parts = []
    title = cfg["title"] + (f" — {cfg['client']}" if cfg["client"] else "")
    parts.append(f"<h1>{e(title)}</h1>")
    parts.append(f'<p class="sub">{e(cfg["instrument"] or "strumento non indicato")} · periodo {R["period"][0]} → '
                 f'{R["period"][1]} · {bs["n"]} trade · costi {fmt(cfg["cost"])} punti andata e ritorno · '
                 f'{fmt(cfg["point_value"])} {e(cfg["currency"])}/punto · tentativi dichiarati N = {cfg["n_tried"]} · '
                 f'generato il {R["created"]} (motore v{R["version"]})</p>')
    # ---- verdetto
    flags = []
    if v["flags"].get("beta"):
        flags.append(('BETA: il risultato viene dal mercato', "#d03b3b"))
    if v["flags"].get("leak"):
        flags.append(("LOOK-AHEAD catturato", "#8f1d1d"))
    if v["flags"].get("data"):
        flags.append(("DATI incoerenti con il mercato", "#8f1d1d"))
    if v["flags"].get("no_edge"):
        flags.append(("Nessun vantaggio dimostrato", "#52514e"))
    fl = "".join(f'<span style="color:{c};border-color:{c}">{e(t)}</span>' for t, c in flags)
    reasons = "".join(f"<li>{e(r)}</li>" for r in v["reasons"]) or "<li>nessuna riserva</li>"
    parts.append(f'<section class="verdict"><div class="grade" style="background:{GRADE_COLOR[v["grade"]]}">'
                 f'{v["grade"]}</div><div><p class="h">{e(v["headline"])}</p><ul>{reasons}</ul>'
                 f'<div class="flags">{fl}</div></div></section>')
    # ---- semafori
    rows = "".join(f"<tr><td>{_light(c['status'])}</td><td><b>{e(c['title'])}</b><div class='why'>{e(c['why'])}</div></td>"
                   f"<td class='num'>{e(c['value'])}</td></tr>" for c in R["checks"])
    parts.append("<h2>Le prove, una per una</h2><div class='table-wrap'><table><tr><th>Esito</th><th>Domanda</th>"
                 f"<th>Misura</th></tr>{rows}</table></div>")
    parts.append("<p class='why'>Scala: <b>A</b> vantaggio solido · <b>B</b> probabile con una riserva · <b>C</b> "
                 "segnali deboli o misti · <b>D</b> nessun vantaggio dimostrato (caso o beta) · <b>E</b> perde al "
                 "netto dei costi · <b>F</b> difetto grave (look-ahead o dati che non tornano).</p>")
    # ---- numeri
    parts.append("<h2>I numeri in breve</h2><div class='kpis'>" + "".join([
        _kpi("Media lorda per trade", f"{fmt(bs['gross_mean'])} pt"),
        _kpi("Media netta per trade", f"{fmt(bs['net_mean'])} pt"),
        _kpi("Netto per trade in valuta", _money(R, bs["net_mean"])),
        _kpi("Totale netto", _money(R, bs["net_total"])),
        _kpi("Trade vincenti", f"{fmt(100 * bs['win_rate'], 1)} %"),
        _kpi("Profit factor", fmt(bs["profit_factor"])),
        _kpi("Sharpe annuo (giornaliero)", fmt(R["sharpe_ann"])),
        _kpi("Drawdown massimo", f"{fmt(R['dd']['max_dd'], 0)} {e(cfg['currency'])}"),
    ]) + "</div>")
    parts.append(_img(fig_equity(R), "curva dei profitti e drawdown"))
    ddb = R["dd_boot"]
    parts.append(f"<p>Il drawdown massimo osservato è <b>{fmt(R['dd']['max_dd'], 0)} {e(cfg['currency'])}</b>. "
                 f"Rimescolando i giorni dello stesso backtest, un drawdown di <b>{fmt(ddb['median'], 0)}</b> è "
                 f"tipico e uno di <b>{fmt(ddb['q95'], 0)}</b> succede in 1 storia su 20: è la cifra da avere in "
                 f"mente prima di iniziare, non quella del backtest.</p>")
    # ---- fortuna?
    d = R["dsr"]
    parts.append("<h2>1. È fortuna?</h2>")
    parts.append(f"<p>Media netta <b>{fmt(b['mean'])} punti</b> per trade, intervallo al 95 % "
                 f"<b>[{fmt(b['lo'])}; {fmt(b['hi'])}]</b>, p unilaterale <b>{fmt(b['p_pos'], 4)}</b> "
                 f"({b['n']} trade in {b['n_days']} giorni). Il bootstrap rimescola le <i>giornate</i>, non i singoli "
                 "trade: i trade dello stesso giorno si muovono insieme e trattarli come indipendenti gonfierebbe la "
                 "fiducia.</p>")
    parts.append(_img(fig_boot(R), "distribuzione bootstrap della media"))
    parts.append(f"<div class='box'><b>Deflated Sharpe Ratio</b> (Bailey &amp; López de Prado, 2014). Sharpe annuo "
                 f"{fmt(R['sharpe_ann'])} su {d['T']} giorni (asimmetria {fmt(d['skew'])}, curtosi {fmt(d['kurt'])}). "
                 f"Con <b>N = {d['n_trials']}</b> varianti provate, il migliore Sharpe atteso per puro caso è "
                 f"{fmt(d['sr0'] * np.sqrt(252))} annuo. Probabilità che il vantaggio sia vero: <b>PSR = "
                 f"{fmt(d['psr'], 3)}</b> senza correzione, <b>DSR = {fmt(d['dsr'], 3)}</b> dopo la correzione per i "
                 "tentativi. Soglia: 0,95. Se il numero di tentativi dichiarato è sottostimato, il DSR vero è più "
                 "basso.</div>")
    # ---- beta
    parts.append("<h2>2. È abilità o solo il mercato?</h2>")
    if R.get("beta"):
        be = R["beta"]
        ws = be["window_split"]
        parts.append(f"<p>Per ogni trade calcoliamo quanto avrebbe reso <i>stare esposti</i> nelle stesse ore e nello "
                     f"stesso verso nel giorno medio del periodo (deriva media del mercato per minuto del giorno, "
                     f"{fmt(be['drift_per_session'])} punti per sessione). Beta medio <b>{fmt(be['beta_mean'])}</b> "
                     f"punti per trade contro un netto di <b>{fmt(be['net_mean'])}</b>. Netto meno beta: "
                     f"<b>{fmt(be['stat_adj']['mean'])}</b> [{fmt(be['stat_adj']['lo'])}; {fmt(be['stat_adj']['hi'])}], "
                     f"p = {fmt(be['stat_adj']['p_pos'], 4)}.</p>")
        expo = (f"<p>Esposizione: {fmt(100 * be['long_share_trades'], 0)} % dei trade long, "
                f"{fmt(100 * be['long_share_time'], 0)} % del tempo in posizione long. ")
        if be["n_overnight"]:
            expo += (f"{be['n_overnight']} trade ({fmt(100 * be['share_overnight'], 0)} %) restano aperti fuori dalla "
                     f"finestra {e(cfg['rth'] or '')} o attraversano più sessioni (beta medio di quei trade "
                     f"{fmt(be['beta_overnight_mean'])}, degli altri {fmt(be['beta_intraday_mean'])}); del beta totale, "
                     f"{fmt(be['beta_outside_mean'])} punti per trade maturano fuori dalla finestra diurna.</p>")
        else:
            expo += f"Nessun trade resta aperto fuori dalla finestra {e(cfg['rth'] or '')}.</p>"
        parts.append(expo)
        if ws:
            parts.append(f"<p>Nel periodo il mercato si è mosso di {fmt(ws['total'], 0)} punti: {fmt(ws['inside'], 0)} "
                         f"nella finestra {e(ws['window'])} e {fmt(ws['outside'], 0)} fuori. Chi è long fuori da "
                         "quella finestra guadagna per costruzione se il mercato sale di notte.</p>")
        if be["flag"]:
            parts.append("<div class='box bad'><b>Segnalazione beta.</b> Il guadagno è significativo ma sparisce (o "
                         "si dimezza) togliendo la parte spiegata dalla deriva del mercato: la strategia sta "
                         "incassando il rialzo (o il ribasso) del mercato, non un vantaggio suo. Un fondo indicizzato "
                         "farebbe lo stesso con meno costi e rischi.</div>")
        parts.append(_img(fig_beta(R), "beta e profilo orario del mercato"))
    else:
        parts.append("<p>Non valutato: servono i dati di mercato.</p>")
    # ---- placebo
    parts.append("<h2>3. Contro il caso: strategie placebo</h2>")
    if R.get("placebo"):
        pl = R["placebo"]
        parts.append(f"<p>Abbiamo generato {fmt(pl['n_sims'], 0)} storie alternative per ciascuno scenario, con la stessa "
                     "struttura della strategia (stesso numero di trade per giorno, stessi orari e durate, stessi "
                     "costi) ma ingressi senza alcun criterio. La strategia reale viene riprezzata sugli stessi dati "
                     f"(<b>{fmt(pl['real_net_mean'])}</b> punti netti per trade; il file del cliente dice "
                     f"{fmt(pl['client_net_mean'])}). Nel laboratorio da cui nasce questo metodo, su 1.266 regole senza "
                     "senso economico, il 45 % dei placebo «solo long» con posizione notturna risultava significativo: "
                     "è il motivo per cui il placebo solo long è sempre mostrato.</p>")
        rows = "".join(f"<tr><td>{e(s['label'])}</td><td class='num'>{fmt(s['median'])}</td><td class='num'>"
                       f"{fmt(s['q95'])}</td><td class='num'><b>{fmt(s['percentile'], 1)}</b></td><td class='num'>"
                       f"{fmt(s['p'], 3)}</td></tr>" for s in pl["scenarios"].values())
        parts.append("<div class='table-wrap'><table><tr><th>Scenario</th><th>Mediana placebo</th><th>95° percentile</th>"
                     f"<th>Percentile strategia</th><th>p</th></tr>{rows}</table></div>")
        sl = pl["scenarios"].get("solo_long")
        if sl and sl["median"] > 0:
            parts.append(f"<p class='why'>Il placebo «solo long» ha mediana positiva ({fmt(sl['median'])}): in questo "
                         "periodo bastava comprare nelle stesse ore per guadagnare. È il beta, non un'abilità.</p>")
        parts.append(_img(fig_placebo(R), "distribuzioni placebo"))
    else:
        parts.append("<p>Non valutato: servono i dati di mercato.</p>")
    # ---- stabilità
    parts.append("<h2>4. Anno per anno e senza i trade migliori</h2>")
    y = R["years"]
    rows = "".join(f"<tr><td>{yy}</td><td class='num'>{int(r['count'])}</td><td class='num'>{fmt(r['mean'])}</td>"
                   f"<td class='num'>{_money(R, r['sum'])}</td></tr>" for yy, r in y.iterrows())
    parts.append("<div class='table-wrap'><table><tr><th>Anno</th><th>Trade</th><th>Netto per trade (pt)</th>"
                 f"<th>Totale netto</th></tr>{rows}</table></div>")
    parts.append(_img(fig_years(R), "anni e senza i migliori"))
    parts.append(f"<p>Senza i {R['top_k']} trade migliori la media netta diventa <b>{fmt(R['drop_top'])}</b> punti. "
                 "Se pochi trade eccezionali reggono tutto il risultato, nel futuro basta non incontrarli.</p>")
    # ---- oos
    dc = R["decay"]
    parts.append("<h2>5. Dentro e fuori campione</h2>")
    if dc["oos"]["n"]:
        if dc["true_oos"]:
            parts.append(f"<p>Periodo di costruzione fino al {dc['cut']}, poi fuori campione. ")
        else:
            parts.append(f"<p><b>Data di fine ottimizzazione non fornita</b>: confrontiamo i primi 2/3 dei trade (fino "
                         f"al {dc['cut']}) con l'ultimo terzo. È un controllo di stabilità, non un vero fuori campione. ")
        parts.append(f"Dentro: {fmt(dc['is']['mean'])} punti per trade (p {fmt(dc['is']['p_pos'], 4)}); fuori: "
                     f"{fmt(dc['oos']['mean'])} (p {fmt(dc['oos']['p_pos'], 4)}). Rapporto di restringimento "
                     f"<b>{fmt(dc['ratio'])}</b>: <b>{e(dc['class'])}</b>.</p>")
        parts.append("<p class='why'>Riferimento misurato: nel laboratorio le regolarità vere hanno mantenuto la "
                     "dimensione da un periodo all'altro (rapporto 0,8-1,2); gli effetti trovati provando molte varianti "
                     "si sono ristretti a 0,35-0,7 appena usciti dal campione, e il migliore candidato passato in "
                     "validazione (+12,1 punti) ha fatto −2,6 in conferma.</p>")
        parts.append(_img(fig_decay(R), "confronto dentro/fuori campione"))
    else:
        parts.append("<p>Non valutabile: nessun trade dopo la data di taglio.</p>")
    # ---- look-ahead
    parts.append("<h2>6. Look-ahead: il codice sbircia il futuro?</h2>")
    la = R.get("lookahead")
    if la:
        if la["ok"]:
            parts.append(f"<div class='box'><b>Nessuna violazione</b> in {la['n_runs']} prove ({la['n_cuts']} istanti di "
                         "taglio, ciascuno con tendenza forte verso l'alto e verso il basso, anche esattamente agli "
                         "ingressi dei trade).</div>")
        else:
            items = "".join(f"<li>T = {e(p['T'])} (tendenza {'+' if p['direction'] > 0 else '−'}): {e(p['problem'])}</li>"
                            for p in la["problems"][:12])
            parts.append(f"<div class='box bad'><b>Look-ahead catturato</b>: {len(la['problems'])} violazioni su "
                         f"{la['n_runs']} prove. Cambiando i prezzi DOPO l'istante T cambiano trade decisi PRIMA di T: "
                         f"il codice usa informazione che nella realtà non avrebbe.<ul>{items}</ul></div>")
        ctrl = "catturata" if la.get("control_caught") else "NON catturata (l'audit su questi dati ha poco potere)"
        parts.append(f"<p class='why'>Controllo positivo: una strategia costruita apposta per barare, sugli stessi dati, "
                     f"è stata {ctrl} ({la.get('control_problems', 0)} violazioni su {la.get('control_runs', 0)} prove).</p>")
    else:
        parts.append("<p>Non eseguito: richiede il codice della strategia come funzione Python "
                     "<code>fn(barre) → trade</code>. Un backtest con look-ahead è la causa più comune di risultati "
                     "troppo belli: è la prima cosa da verificare quando il codice è disponibile.</p>")
    # ---- dati
    parts.append("<h2>7. Qualità dei dati</h2>")
    q = R.get("quality")
    if q:
        parts.append(f"<p>Ogni trade è stato riprezzato sui dati di mercato (ingresso e uscita all'apertura della prima "
                     f"barra dall'orario indicato). Correlazione fra P&amp;L dichiarato e riprezzato <b>{fmt(q['corr'], 3)}</b>; "
                     f"scarto medio (dichiarato − mercato) <b>{fmt(q['mean_diff'])}</b> punti per trade, scarto tipico "
                     f"{fmt(q['median_abs_diff'])}; {fmt(100 * q['share_aligned'], 1)} % dei trade agganciati entro "
                     f"{fmt(cfg['tol_minutes'], 0)} minuti a una barra.</p>")
        if q["mean_diff"] > 0.5 * max(cfg["cost"], 0.25):
            parts.append("<div class='box warn'>Il backtest dichiara in media prezzi <b>migliori</b> di quelli del "
                         "mercato agli stessi orari: fill ottimistici (stop eseguiti al prezzo esatto, ingressi al "
                         "minimo della barra...) gonfiano il risultato. Il placebo e il confronto usano il riprezzato.</div>")
        if q.get("tz_hint_hours"):
            parts.append(f"<div class='box warn'>Spostando gli orari di {q['tz_hint_hours']:+d} ore la corrispondenza "
                         f"con il mercato migliora molto (correlazione {fmt(q['tz_hint_corr'], 2)}): il fuso orario "
                         "del file potrebbe essere sbagliato.</div>")
    for n_ in R["notes"]:
        parts.append(f"<p class='why'>Nota: {e(n_)}</p>")
    if R.get("market_info"):
        mi = R["market_info"]
        kind = "giornalieri" if mi["daily"] else f"barre da {fmt(mi['bar_minutes'], 0)} minuti"
        parts.append(f"<p class='why'>Dati di mercato: {kind}, {mi['n_sessions']} sessioni, fuso {e(mi['tz'])}, "
                     f"dal {e(mi['first'][:16])} al {e(mi['last'][:16])} (UTC).</p>")
    # ---- potenza
    pw = R["power"]
    parts.append("<h2>8. Quanti dati servono</h2>")
    txt = (f"<p>Con i dati attuali il test rileva (con probabilità 80 %) solo un vantaggio di almeno "
           f"<b>{fmt(pw['mde'])} punti netti per trade</b> ({_money(R, pw['mde'])}).")
    if np.isfinite(pw.get("n_needed", np.inf)):
        yrs = pw["days_needed"] / 252
        txt += (f" Per confermare il vantaggio osservato ({fmt(b['mean'])} punti) servono circa "
                f"<b>{fmt(pw['n_needed'], 0)} trade</b> (circa {fmt(yrs, 1)} anni al ritmo attuale); potenza attuale "
                f"{fmt(100 * pw['power_now'], 0)} %.")
    else:
        txt += " Il vantaggio osservato non è positivo: nessuna quantità di dati lo renderà significativo."
    parts.append(txt + "</p>")
    # ---- metodo
    parts.append("<h2>Metodo e limiti</h2><ul class='why'>"
                 "<li>Unità: punti per 1 unità (contratto/azione); costi sottratti per ogni trade andata e ritorno.</li>"
                 "<li>Bootstrap a blocchi per giorno (10.000 repliche); Deflated Sharpe sul P&amp;L netto giornaliero "
                 "con zero nei giorni senza trade; varianza degli Sharpe fra i tentativi = quella dello stimatore sotto "
                 "l'ipotesi nulla, salvo indicazione diversa.</li>"
                 "<li>Beta: deriva media del mercato per minuto del giorno (per sessione) sul periodo dei trade, "
                 "sommata sulle ore di esposizione di ciascun trade, più le sessioni intere per i trade di più giorni.</li>"
                 "<li>Placebo: ingressi casuali con la stessa struttura, riprezzati al prezzo d'apertura della barra "
                 "(nessuno slippage oltre ai costi dichiarati).</li>"
                 "<li>Il report non vede i dettagli di esecuzione (liquidità, slippage reale, rifiuti di ordini), "
                 "non verifica la gestione del rischio e non può sapere quante varianti sono state davvero provate: "
                 "il numero N dichiarato è un'ipotesi del cliente e pesa sul DSR. Misurato su strategie a caso "
                 "(product/engine/CALIBRAZIONE.md): la migliore di 20 prende A o B nel 57 % dei casi se si dichiara "
                 "N = 1, nel 4,5 % se si dichiara N = 20; una strategia a caso dichiarata onestamente, nel 2 %.</li>"
                 "<li>Un buon voto dice che il passato non è spiegabile con caso, beta o look-ahead; non dice che il "
                 "vantaggio continuerà. I mercati cambiano: nel laboratorio di riferimento un candidato che aveva "
                 "superato la validazione ha perso nella conferma successiva.</li></ul>")
    parts.append(f"<div class='disc'><b>Avvertenza.</b> {e(DISCLAIMER)}</div>")
    body = "\n".join(parts)
    return (f"<!doctype html><html lang='it'><head><meta charset='utf-8'><meta name='viewport' "
            f"content='width=device-width,initial-scale=1'><title>Revisione backtest</title><style>{CSS}</style>"
            f"</head><body><main>{body}</main></body></html>")


def write_report(R: dict, path) -> str:
    htm = render(R)
    with open(path, "w", encoding="utf-8") as f:
        f.write(htm)
    return str(path)
