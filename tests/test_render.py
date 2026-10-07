from nqml.report.render import evaluate_criteria, render_report
from nqml.config import load_config

CFG = load_config("config.yaml")


def _res(**over):
    base = dict(mean_R_A=0.15, ci_A=(0.05, 0.25), mean_R_A_slip2=0.10, n_A=800,
                diff_ci={"B0": (0.02, 0.2), "C": (0.01, 0.3), "Copt": (0.01, 0.2)},
                fold_signs={0: 0.1, 1: 0.2, 2: -0.1, 3: 0.05, 4: 0.3},
                shuffle_aucs=[0.5, 0.49, 0.52, 0.48, 0.51], brier_A_mean=0.22, brier_context_mean=0.235,
                summary={}, diffs={}, stress=None, sanity=[], calib=None, decomposition={}, features_by_fold={},
                folds=[], engine_counts={}, n_days=0,
                brier_folds_A_better=3, brier_A_pooled=0.22, brier_rw_pooled=0.235, brier_base_pooled=0.25,
                auc_A_pooled=0.75, auc_rw_pooled=0.75, prior={"pooled": {}, "by_fold": {}})
    return base | over


def test_criteria_all_pass_on_good_result():
    crit = evaluate_criteria(_res())
    assert [c["id"] for c in crit] == [1, 2, 3, 4, 5] and all(c["passed"] for c in crit)


def test_criteria_fail_cases():
    assert not evaluate_criteria(_res(ci_A=(-0.01, 0.25)))[0]["passed"]              # CI include 0
    assert not evaluate_criteria(_res(mean_R_A_slip2=-0.01))[0]["passed"]           # a 2 tick negativo
    assert not evaluate_criteria(_res(diff_ci={"B0": (-0.1, 0.2), "C": (0.01, 0.3), "Copt": (0.0, 0.2)}))[1]["passed"]
    assert not evaluate_criteria(_res(fold_signs={0: 0.1, 1: -0.2, 2: -0.1, 3: 0.05, 4: 0.3}))[2]["passed"]   # 3/5
    assert not evaluate_criteria(_res(shuffle_aucs=[0.5, 0.6, 0.5, 0.5, 0.5]))[3]["passed"]
    assert not evaluate_criteria(_res(brier_A_mean=0.24, brier_context_mean=0.235))[3]["passed"]
    assert not evaluate_criteria(_res(n_A=299))[4]["passed"]


def test_render_report_contains_key_sections():
    md = render_report(_res(), CFG)
    for s in ("# Report OOS", "Criteri", "PASS", "C in 1a", "cassaforte"):
        assert s in md


def test_render_report_uses_tag_and_version_note():
    md = render_report(_res() | {"tag": "1b", "version": "1b", "comparison_md": "## Confronto appaiato 1b − 1a_S\nX\n"}, CFG)
    assert "# Report OOS — 1b" in md and "C ha 3 regole" in md and "Confronto appaiato 1b − 1a_S" in md
    md_a = render_report(_res() | {"tag": "1a_S", "version": "1a"}, CFG)
    assert "# Report OOS — 1a_S" in md_a and "C in 1a ha 2 regole" in md_a


def test_render_report_header_uses_res_version_not_config_default():
    md = render_report(_res() | {"tag": "1b", "version": "1b"}, CFG)
    assert "feature `1b`" in md and "feature `1a`" not in md.split("Nota:")[0]


def test_render_report_1b_style_paired_brier_and_negative_mean_r():
    res = _res() | {
        "tag": "1b", "version": "1b", "mean_R_A": -0.040, "ci_A": (-0.177, 0.095),
        "brier_A_vs_context": {"point": 0.0086, "ci": (0.0031, 0.0143)},
    }
    md = render_report(res, CFG)
    assert "peggio" in md
    assert "negativo" in md
    assert "parità" not in md
    assert "PASS alla lettera" not in md
    assert "+0.0086" in md and "+0.0031" in md and "+0.0143" in md


def test_render_report_1a_style_keeps_fold_mean_semantics_without_forbidden_phrasing():
    res = _res() | {"tag": "1a_S", "version": "1a", "brier_A_mean": 0.1874, "brier_context_mean": 0.1826}
    md = render_report(res, CFG)
    assert "PASS alla lettera" not in md
    assert "= prior" not in md and "NON confermato" not in md
    assert "peggio" in md or "meglio" in md


def test_render_report_inserts_notes_md_section():
    md = render_report(_res() | {"notes_md": "Nota di prova sulla milestone."}, CFG)
    assert "## Note sulla milestone" in md and "Nota di prova sulla milestone." in md
    assert md.index("## Note sulla milestone") < md.index("## Come leggere questo report")


def test_render_report_fraction_dilution_bullet():
    md = render_report(_res() | {"fraction": 0.445}, CFG)
    assert "sottoinsieme campionato" in md and "0.445" in md
