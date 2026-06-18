"""Series resolver — the deep core. All §3 / guard-rail meaning lives here."""

import pytest

from app.data import AmbiguousConvention, resolve_series


def test_resolves_wid_series_with_convention_echoed(con, relation):
    series = resolve_series(
        con,
        relation,
        source="WID",
        indicateur="part_patrimoine",
        groupe="top1",
        concept="net",
    )
    # The Convention travels with the data (CONTEXT.md guard rail).
    assert series.unite == "adulte"
    assert series.concept_patrimoine == "net"
    assert series.unite_valeur == "%"
    assert [(p.annee, p.valeur) for p in series.points] == [
        (2000, 22.1),
        (2015, 26.5),
        (2021, 27.0),
    ]


def test_ambiguous_convention_raises_with_choices(con, relation):
    # DGFiP spans two Concepts (total ≤2017, immobilier ≥2018). Without a concept
    # the query is ambiguous across the 2018 Rupture.
    with pytest.raises(AmbiguousConvention) as excinfo:
        resolve_series(
            con,
            relation,
            source="DGFiP",
            indicateur="impot_moyen",
            groupe="redevables",
            annee_min=2000,
            annee_max=2020,
        )
    concepts = {c["concept_patrimoine"] for c in excinfo.value.choices}
    assert concepts == {"total", "immobilier"}
    assert all(c["unite"] == "foyer_fiscal" for c in excinfo.value.choices)


def test_euros_constants_selects_deflated_rows(con, relation):
    nominal = resolve_series(
        con,
        relation,
        source="WID",
        indicateur="patrimoine_moyen",
        groupe="top1",
        concept="net",
        annee_min=2000,
        annee_max=2021,
        euros_constants=False,
    )
    deflated = resolve_series(
        con,
        relation,
        source="WID",
        indicateur="patrimoine_moyen",
        groupe="top1",
        concept="net",
        annee_min=2000,
        annee_max=2021,
        euros_constants=True,
    )
    assert [(p.annee, p.valeur) for p in nominal.points] == [(2021, 1000000.0)]
    assert nominal.unite_valeur == "euros"
    assert [(p.annee, p.valeur) for p in deflated.points] == [(2021, 950000.0)]
    assert deflated.unite_valeur == "euros_constants_2021"


def test_defaults_to_latest_millesime_but_pins_when_asked(con, relation):
    # Default: latest date_extraction → WID 2026 revised the 2015 value to 26.5.
    latest = resolve_series(
        con,
        relation,
        source="WID",
        indicateur="part_patrimoine",
        groupe="top1",
        concept="net",
        annee_min=2015,
        annee_max=2015,
    )
    assert latest.millesime_source == "WID 2026"
    assert [(p.annee, p.valeur) for p in latest.points] == [(2015, 26.5)]

    # Pinning the older vintage returns the previous value.
    pinned = resolve_series(
        con,
        relation,
        source="WID",
        indicateur="part_patrimoine",
        groupe="top1",
        concept="net",
        annee_min=2015,
        annee_max=2015,
        millesime="WID 2024",
    )
    assert pinned.millesime_source == "WID 2024"
    assert [(p.annee, p.valeur) for p in pinned.points] == [(2015, 26.0)]


def test_valid_query_matching_no_rows_returns_empty_points(con, relation):
    series = resolve_series(
        con,
        relation,
        source="WID",
        indicateur="part_patrimoine",
        groupe="bottom50",
        concept="net",
    )
    assert series.points == []
    # The Convention is still echoed for an empty (but legitimate) result.
    assert series.unite == "adulte"
    assert series.concept_patrimoine == "net"


def test_insee_without_concept_is_ambiguous_across_brut_and_hors_reste(con, relation):
    # INSEE now spans more than one Convention (all-inclusive brut vs brut hors
    # reste); with no concept pinned the Gini query is ambiguous, exactly like
    # DGFiP across the 2018 Rupture (issue #14).
    with pytest.raises(AmbiguousConvention) as excinfo:
        resolve_series(con, relation, source="INSEE", indicateur="gini", groupe="ensemble")
    concepts = {c["concept_patrimoine"] for c in excinfo.value.choices}
    assert concepts == {"brut", "brut_hors_reste"}
    assert all(c["unite"] == "menage" for c in excinfo.value.choices)


def test_insee_with_pinned_concept_resolves_cleanly(con, relation):
    series = resolve_series(
        con,
        relation,
        source="INSEE",
        indicateur="gini",
        groupe="ensemble",
        concept="brut_hors_reste",
    )
    assert series.unite == "menage"
    assert series.concept_patrimoine == "brut_hors_reste"
    assert series.points  # the headline hors-reste Gini resolves to actual points


def test_dgfip_series_carries_2018_rupture_in_range(con, relation):
    series = resolve_series(
        con,
        relation,
        source="DGFiP",
        indicateur="impot_moyen",
        groupe="redevables",
        concept="immobilier",
        annee_min=2018,
        annee_max=2020,
    )
    assert [(r.annee, r.label) for r in series.ruptures] == [
        (2018, "ISF (total) → IFI (immobilier)")
    ]
