"""Meta builder — distinct dimension values + global year bounds (against fixture)."""

from app.data import build_meta


def test_meta_lists_distinct_dimension_values(con, relation):
    meta = build_meta(con, relation)
    assert set(meta.sources) == {"WID", "INSEE", "DGFiP"}
    assert set(meta.concepts) == {
        "net",
        "brut",
        "brut_hors_reste",
        "net_hors_reste",
        "total",
        "immobilier",
    }
    assert set(meta.unites) == {"adulte", "menage", "foyer_fiscal"}
    assert "part_patrimoine" in meta.indicateurs
    assert "redevables" in meta.groupes
    assert set(meta.millesimes) == {"WID 2024", "WID 2026", "INSEE 2021", "DGFiP 2024"}


def test_meta_availability_is_source_scoped(con, relation):
    """`availability` maps each source to only the (indicateur -> groupes) it owns,
    so the UI never offers a source a figure it never measured (Convention guard)."""
    meta = build_meta(con, relation)
    assert set(meta.availability) == {"WID", "INSEE", "DGFiP"}
    # DGFiP measures IFI/ISF levels on `redevables`, never the WID shares.
    assert "part_patrimoine" not in meta.availability["DGFiP"]
    assert meta.availability["DGFiP"]["impot_moyen"] == ["redevables"]
    # INSEE shares live on top1/top10; gini on the whole population.
    assert set(meta.availability["INSEE"]["part_patrimoine"]) == {"top1", "top10"}
    assert meta.availability["INSEE"]["gini"] == ["ensemble"]


def test_meta_reports_global_year_bounds(con, relation):
    meta = build_meta(con, relation)
    assert meta.annee_min == 2000
    assert meta.annee_max == 2021
