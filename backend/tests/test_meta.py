"""Meta builder — distinct dimension values + global year bounds (against fixture)."""

from app.data import build_meta


def test_meta_lists_distinct_dimension_values(con, relation):
    meta = build_meta(con, relation)
    assert set(meta.sources) == {"WID", "INSEE", "DGFiP"}
    assert set(meta.concepts) == {"net", "brut", "total", "immobilier"}
    assert set(meta.unites) == {"adulte", "menage", "foyer_fiscal"}
    assert "part_patrimoine" in meta.indicateurs
    assert "redevables" in meta.groupes
    assert set(meta.millesimes) == {"WID 2024", "WID 2026", "INSEE 2021", "DGFiP 2024"}


def test_meta_reports_global_year_bounds(con, relation):
    meta = build_meta(con, relation)
    assert meta.annee_min == 2000
    assert meta.annee_max == 2021
