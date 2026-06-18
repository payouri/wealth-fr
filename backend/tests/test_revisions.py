"""Révisions — Observations sharing a HIST_KEYS tuple across >1 millésime where
the source revised the value (append-only historisation; CONTEXT.md). The deep
core (`resolve_revisions`) is isolation-tested against the fixture; the endpoint
contract is exercised in test_contract-style via TestClient.
"""

from fastapi.testclient import TestClient

from app.data import resolve_revisions
from app.main import app

client = TestClient(app)


def test_surfaces_the_seeded_revision_with_both_millesimes(con, relation):
    revisions = resolve_revisions(con, relation)
    # The fixture seeds exactly one revised value: WID top1 part_patrimoine in
    # 2015 went 26.0 (WID 2024) -> 26.5 (WID 2026). The 2000 value is unchanged
    # across the two millésimes, so it is not a Révision (nothing was revised).
    keys = {(r.annee, r.source, r.indicateur, r.groupe) for r in revisions}
    assert keys == {(2015, "WID", "part_patrimoine", "top1")}

    [rev] = revisions
    # Both millésimes coexist — neither is overwritten — each with its own value
    # and extraction date (traceability).
    by_millesime = {v.millesime_source: v for v in rev.valeurs}
    assert by_millesime["WID 2024"].valeur == 26.0
    assert by_millesime["WID 2024"].date_extraction == "2024-06-01"
    assert by_millesime["WID 2026"].valeur == 26.5
    assert by_millesime["WID 2026"].date_extraction == "2026-06-12"
    # The Convention travels with the révision (never dropped).
    assert rev.unite == "adulte"
    assert rev.concept_patrimoine == "net"


def test_returns_empty_list_when_no_revisions_exist(con, relation):
    # Pin the relation to a single millésime: no tuple then spans >1 millésime,
    # so nothing can have been revised.
    one_millesime = f"(SELECT * FROM {relation} WHERE millesime_source = 'WID 2026')"
    assert resolve_revisions(con, one_millesime) == []


def test_endpoint_returns_the_revision(con):
    body = client.get("/api/revisions").json()
    seeded = [
        r
        for r in body
        if (r["annee"], r["source"], r["indicateur"], r["groupe"])
        == (2015, "WID", "part_patrimoine", "top1")
    ]
    assert len(seeded) == 1
    millesimes = {v["millesime_source"] for v in seeded[0]["valeurs"]}
    assert millesimes == {"WID 2024", "WID 2026"}
