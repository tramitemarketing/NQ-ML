"""Dashboard e figure: solo registri finti in cartelle temporanee, nessun dato di mercato."""
import json
import math

import pytest

from lab import viz
from lab.dashboard import server


def _ledger(tmp_path, rows):
    d = tmp_path / "ledger"
    d.mkdir(parents=True, exist_ok=True)
    with open(d / "fam.jsonl", "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    return tmp_path


def _row(i, **kw):
    return {"ts": f"2026-01-01T00:00:{i:02d}", "family": "fam", "test_id": f"t{i}", "phase": "discovery",
            "description": "prova", **kw}


def test_z_dal_p_bilaterale_ha_il_segno_della_media():
    assert server.z_from(1.0, 0.05) == pytest.approx(1.96, abs=0.001)
    assert server.z_from(-1.0, 0.05) == pytest.approx(-1.96, abs=0.001)
    assert server.z_from(1.0, 1.0) == pytest.approx(0.0, abs=1e-9)


def test_z_ha_un_tetto_e_il_p_zero_non_esplode():
    assert server.z_from(1.0, 0.0) == pytest.approx(server.N01.inv_cdf(1 - server.P_FLOOR / 2))
    assert server.z_from(None, None, t=99.0) == server.Z_CAP
    assert server.z_from(None, None, t=-99.0) == -server.Z_CAP


def test_niente_z_senza_p():
    """Media e intervallo senza p non bastano: per un rapporto di varianze l'ipotesi nulla non è zero."""
    assert server.z_from(0.88, None) is None


def test_registro_ordinato_nel_tempo_e_righe_contate(tmp_path):
    lab = _ledger(tmp_path, [_row(2, mean=1.0, lo=0.1, hi=1.9, p_two=0.03, n=100),
                             _row(1, mean=-1.0, p_two=0.5, n=50, yearly={"2010": -1.0, "2011": float("nan")}),
                             _row(3)])
    res, n = server.read_ledger(lab / "ledger")
    assert n == 3 and [r["id"] for r in res] == ["t1", "t2", "t3"]
    assert res[0]["z"] < 0 < res[1]["z"] and res[2]["z"] is None
    assert res[0]["yearly"] == {"2010": -1.0}          # il NaN è scartato, non arriva alla pagina


def test_riga_con_due_versi_diventa_due_risultati(tmp_path):
    lab = _ledger(tmp_path, [_row(1, fade_mean=-0.9, fade_p_two=0.001, fade_lo=-1.0, fade_hi=-0.8,
                                  cont_mean=0.1, cont_p_two=0.6, fade_n=10, cont_n=10)])
    res, n = server.read_ledger(lab / "ledger")
    assert n == 1 and [r["label"] for r in res] == ["fade", "cont"] and {r["row"] for r in res} == {0}


def test_riga_scritta_a_meta_viene_saltata(tmp_path):
    lab = _ledger(tmp_path, [_row(1, mean=1.0, p_two=0.2)])
    with open(lab / "ledger" / "fam.jsonl", "a", encoding="utf-8") as f:
        f.write('{"ts": "2026-01-01T00:00:09", "family": "fam", "test_id": "t9", "mea')
    res, n = server.read_ledger(lab / "ledger")
    assert n == 1


def test_verdetti_mde_come_potenza_py(tmp_path):
    """Stessa formula di lab/potenza.py: (z_alpha + z_80) * SE, unilaterale per i tradeable."""
    (tmp_path / "verdicts").mkdir()
    v = [{"id": "a", "family": "f", "kind": "tradeable", "phase": "validation", "k": 13, "alpha": 0.05 / 13,
          "stat": {"n_days": 498, "mean": 1.538152610441767, "lo": -5.984964859437751, "hi": 9.503074799196778,
                   "p_two": 0.6981}, "verdict": "FAIL"}]
    (tmp_path / "verdicts" / "validation.json").write_text(json.dumps(v), encoding="utf-8")
    (tmp_path / "verdicts" / "validation_giro1.json").write_text(json.dumps(v), encoding="utf-8")
    out = server.read_verdicts(tmp_path / "verdicts")
    assert len(out) == 1                                # i file che ripetono l'ultimo giro non si contano due volte
    assert out[0]["se"] == pytest.approx(3.951, abs=0.001) and out[0]["mde80"] == pytest.approx(13.86, abs=0.01)


def test_stato_serializzabile_e_firma_che_cambia(tmp_path):
    lab = _ledger(tmp_path, [_row(1, mean=float("inf"), p_two=0.2, n=3)])
    s1 = server.signature(lab)
    json.dumps(server.build_state(lab), allow_nan=False)   # nessun NaN/inf deve arrivare al browser
    with open(lab / "ledger" / "fam.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(_row(2, mean=0.5, p_two=0.4)) + "\n")
    assert server.signature(lab) != s1
    assert server.build_state(lab)["lab"]["rows"] == 2


def test_figure_scrittura_lettura_e_demo_nascoste(tmp_path):
    fig = tmp_path / "figures"
    viz.bars("fam", "t1", "anni", title="x", labels=[2010, 2011], values=[1.0, float("nan")], fig_dir=fig)
    viz.placebo("fam", "t1", "pl", title="x", real=2.0, placebo_values=[0.0, 1.0, 2.0, 3.0], fig_dir=fig, demo=True)
    assert [f["type"] for f in server.read_figures(fig, demo=False)] == ["bars"]
    both = server.read_figures(fig, demo=True)
    assert len(both) == 2 and both[0]["values"] == [1.0, None]
    pl = [f for f in both if f["type"] == "placebo"][0]
    assert pl["share_as_extreme"] == pytest.approx(0.5) and sum(pl["counts"]) == 4


def test_figure_rifiutano_dati_grezzi_e_lunghezze_sbagliate(tmp_path):
    with pytest.raises(ValueError, match="aggregati"):
        viz.scatter("f", "t", "n", title="x", x=range(viz.MAX_POINTS + 1), y=range(viz.MAX_POINTS + 1), fig_dir=tmp_path)
    with pytest.raises(ValueError):
        viz.line("f", "t", "n", title="x", x=[1, 2, 3], series={"a": [1, 2]}, fig_dir=tmp_path)
    with pytest.raises(ValueError):
        viz.line("f", "t", "n", title="x", x=[1, 2], series={str(i): [1, 2] for i in range(5)}, fig_dir=tmp_path)
    assert not list(tmp_path.rglob("*.json"))


def test_istogramma_salva_conteggi_non_valori(tmp_path):
    p = viz.hist("f", "t", "h", title="x", values=[math.sin(i) for i in range(5000)], bins=20, fig_dir=tmp_path)
    fig = json.loads(p.read_text(encoding="utf-8"))
    assert fig["n"] == 5000 and sum(fig["counts"]) == 5000 and len(fig["edges"]) == 21 and "values" not in fig


def test_righe_di_controllo_fuori_dal_conto_dei_test(tmp_path):
    lab = _ledger(tmp_path, [_row(1, mean=1.0, p_two=0.2), _row(2, kind="control", mean=9.0, p_two=0.0001)])
    st = server.build_state(lab)
    assert st["lab"]["rows"] == 1 and st["lab"]["controls"] == 1 and st["lab"]["with_z"] == 1
    assert [r["control"] for r in st["results"]] == [False, True]


# --- forme dei giri 8, 9 e 10 (righe finte con gli stessi campi di quelle vere) ---

def test_blocco_netto_z_dal_p_two_e_p_del_test_a_una_coda(tmp_path):
    row = _row(1, p=1.0, netto={"n": 100, "mean": -1.09, "lo": -1.44, "hi": -0.74, "p_two": 0.0001, "p_pos": 1.0},
               base={"lordo_pt": -0.34, "netto_pt": -1.09}, per_anno={"2010": {"mean": -0.5, "count": 9}, "2011": {"mean": -1.1}},
               criteri={"years_pos": "0/2", "years": {"2010": -0.46}})
    r = server.read_ledger(_ledger(tmp_path, [row]) / "ledger")[0][0]
    assert r["mean"] == -1.09 and (r["lo"], r["hi"]) == (-1.44, -0.74) and r["n"] == 100
    assert r["z"] == pytest.approx(-3.89, abs=0.01)          # molto negativo: il p_two piccolo NON è un test superato
    assert (r["p"], r["p_kind"]) == (1.0, "one")              # si mostra il p del test, a una coda
    assert r["yearly"] == {"2010": -0.5, "2011": -1.1} and r["years_pos"] == "0/2" and r["gross"] == -0.34
    assert r["unit"] == "punti netti per trade"


def test_blocco_netto_anni_da_netto_pt_e_unita_solo_se_confermata(tmp_path):
    row = _row(1, p=0.5, netto={"mean": 0.2, "p_two": 0.9}, base={"netto_pt": 9.9},
               per_anno={"2010": {"n": 3, "netto_pt": -0.9}})
    r = server.read_ledger(_ledger(tmp_path, [row]) / "ledger")[0][0]
    assert r["yearly"] == {"2010": -0.9} and r["unit"] is None   # base.netto_pt non coincide: nessuna unità inventata


def test_futilita_senza_p_non_ha_z(tmp_path):
    row = _row(1, n=13603, mean_net_R=-0.386, lo=-0.408, hi=-0.363, se=0.011, gross_R=-0.063,
               per_anno={"2010": -0.456, "2011": -0.381}, anni_positivi="0/2")
    r = server.read_ledger(_ledger(tmp_path, [row]) / "ledger")[0][0]
    assert r["mean"] == -0.386 and r["z"] is None and r["p"] is None       # il PREREG non registra un p: niente z
    assert r["yearly"] == {"2010": -0.456, "2011": -0.381} and r["unit"] == "R netti per trade"


def test_diff_con_p_a_una_coda(tmp_path):
    pos = _row(1, diff=0.0013, p=0.4279, boot={"lo": -0.009, "hi": 0.012})
    neg = _row(2, diff=-0.0026, lo=-0.008, hi=0.003, p=0.811)
    a, b = server.read_ledger(_ledger(tmp_path, [pos, neg]) / "ledger")[0]
    assert a["z"] == pytest.approx(0.18, abs=0.01) and (a["lo"], a["hi"]) == (-0.009, 0.012) and a["stat"] == "diff"
    assert b["z"] == pytest.approx(-0.88, abs=0.01) and (b["lo"], b["hi"]) == (-0.008, 0.003)
    assert server.z_from_one_sided(1.0) == pytest.approx(-server.z_from_one_sided(0.0))   # p = 1 e p = 0 non esplodono


def test_le_forme_nuove_non_toccano_le_righe_con_media_in_cima(tmp_path):
    row = _row(1, mean=1.0, p_two=0.05, diff=-9.0, p=0.99, netto={"mean": -5.0, "p_two": 0.001})
    r = server.read_ledger(_ledger(tmp_path, [row]) / "ledger")[0][0]
    assert r["mean"] == 1.0 and r["z"] == pytest.approx(1.96, abs=0.001)


def test_z_al_limite_del_bootstrap_e_segnato_come_limite(tmp_path):
    """Tre test diversi con p = 0,0001 cadono sullo stesso z: non è una misura, è il limite del bootstrap."""
    rows = [_row(1, netto={"mean": -3.1, "p_two": 0.0001}, p=1.0),          # forma dei giri 9 e 10
            _row(2, mean=-7.4, p_two=0.0),                                  # forma vecchia, p registrato come 0
            _row(3, mean=1.0, p_two=0.03),                                  # misura vera
            _row(4, diff=-0.0026, p=0.811),                                 # p a una coda lontano dai limiti
            _row(5, diff=0.5, p=0.0001),                                    # p a una coda al minimo
            _row(6, b=0.2, t=7.5)]                                          # t oltre il tetto
    lab = _ledger(tmp_path, rows)
    a, b, c, d, e, f = server.read_ledger(lab / "ledger")[0]
    assert a["z"] == b["z"] == pytest.approx(-3.89, abs=0.01)
    assert [r["z_lim"] for r in (a, b, c, d, e, f)] == [True, True, False, False, True, True]
    assert server.build_state(lab)["lab"]["z_lim"] == 4
    assert server.read_ledger(_ledger(tmp_path / "x", [_row(1)]) / "ledger")[0][0]["z_lim"] is False
