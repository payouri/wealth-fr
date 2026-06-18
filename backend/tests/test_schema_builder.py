"""Schema builder — the machine-readable contract / agent entry point behind
/api/schema (ADR 0004). Publishes the Conventions, the per-indicateur value
semantics with the `dimensionless` flag (the in-band encoding of ADR 0003), the
known Ruptures, the historisation key, and the guard rails as English strings.
"""

from app.data import HIST_KEYS, build_schema


def test_lists_every_convention_pair_grouped_by_source(con, relation):
    schema = build_schema(con, relation)
    pairs = {(c.source, c.unite, concept) for c in schema.conventions for concept in c.concepts}
    # Every distinct (source, unite, concept_patrimoine) tuple in the fixture.
    assert ("WID", "adulte", "net") in pairs
    assert ("INSEE", "menage", "brut") in pairs
    assert ("INSEE", "menage", "brut_hors_reste") in pairs
    assert ("DGFiP", "foyer_fiscal", "total") in pairs
    assert ("DGFiP", "foyer_fiscal", "immobilier") in pairs


def test_dimensionless_flag_encodes_adr_0003(con, relation):
    schema = build_schema(con, relation)
    by_indicateur = {i.indicateur: i for i in schema.indicateurs}
    # %/indice shares + Gini are dimensionless (cross-source-comparable in shape).
    assert by_indicateur["part_patrimoine"].dimensionless is True
    assert by_indicateur["gini"].dimensionless is True
    # Euro levels are NOT dimensionless (Convention-bound, may not be overlaid).
    assert by_indicateur["patrimoine_moyen"].dimensionless is False
    assert by_indicateur["impot_moyen"].dimensionless is False


def test_surfaces_the_dgfip_2018_rupture(con, relation):
    schema = build_schema(con, relation)
    dgfip = [r for r in schema.ruptures if r.source == "DGFiP"]
    assert (2018, "ISF (total) → IFI (immobilier)") in {(r.annee, r.label) for r in dgfip}


def test_publishes_historisation_key_and_guard_rail_rules(con, relation):
    schema = build_schema(con, relation)
    assert schema.historisation_key == HIST_KEYS
    rules = " ".join(schema.rules).lower()
    assert "convention" in rules  # never merge across Convention
    assert "euros_constants" in rules or "level" in rules  # deflation only on levels
    assert "revision" in rules or "append" in rules  # append-only historisation
