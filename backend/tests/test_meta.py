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


def test_meta_tranche_taux_maps_each_tranche_to_its_marginal_rate(con, relation):
    """Each `tranche_marginale_*` groupe carries its marginal RATE as a number,
    derived from the `(taux marginal X %)` fragment in `notes` (stable per tranche
    across years), so the UI can label "Tranche à 0,7 %" instead of an opaque
    ordinal that starts at 2 and skips the 0,5 % band (issue #15)."""
    meta = build_meta(con, relation)
    assert meta.tranche_taux == {
        "tranche_marginale_2": 0.7,
        "tranche_marginale_3": 1.0,
        "tranche_marginale_5": 1.5,
    }


def test_meta_tranche_taux_is_deterministic_across_distinct_notes(con, relation):
    """A tranche routinely yields several distinct `(groupe, notes)` rows — a
    value-row note and a borne/seuil-row note, plus multiple millésimes under
    append-only historisation — all embedding the same `(taux marginal X %)`. The
    SELECT is `ORDER BY`-ed so first-parseable-wins is reproducible across runs,
    not at the mercy of DuckDB's arbitrary row order. `tranche_marginale_2` carries
    two distinct notes in the fixture; the rate must come out stable regardless."""
    notes = {
        n
        for (n,) in con.execute(
            f"SELECT DISTINCT notes FROM {relation} WHERE groupe = 'tranche_marginale_2'"
        ).fetchall()
    }
    assert len(notes) >= 2  # the fixture really exercises the multi-note case
    # Run several times; a deterministic ORDER BY makes every run agree.
    for _ in range(5):
        assert build_meta(con, relation).tranche_taux["tranche_marginale_2"] == 0.7
