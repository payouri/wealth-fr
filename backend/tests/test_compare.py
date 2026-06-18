"""Comparison — one indicateur/groupe fanned across Sources (jalon 5, ADR 0003).

Each Source resolves through the *same* jalon-3 resolver, so each line keeps its
own Convention; Sources are overlaid, never merged. The 422 ambiguity contract
is inherited from the resolver unchanged.
"""

from fastapi.testclient import TestClient

from app.data import resolve_compare
from app.main import app

client = TestClient(app)


def test_returns_one_series_per_source_each_keeping_its_convention(con, relation):
    series = resolve_compare(
        con,
        relation,
        indicateur="part_patrimoine",
        groupe="top1",
        sources=["WID", "INSEE"],
    )
    by_source = {str(s.query["source"]): s for s in series}
    assert set(by_source) == {"WID", "INSEE"}
    # Each Source keeps its own (unité, concept) — never collapsed into one.
    # INSEE's shares are the *brut hors reste* Convention (issue #14): the headline
    # figures INSEE publishes, distinct from the all-inclusive brut.
    assert (by_source["WID"].unite, by_source["WID"].concept_patrimoine) == ("adulte", "net")
    assert (by_source["INSEE"].unite, by_source["INSEE"].concept_patrimoine) == (
        "menage",
        "brut_hors_reste",
    )


def test_endpoint_overlays_sources_with_distinct_conventions():
    body = client.get(
        "/api/compare",
        params={"indicateur": "part_patrimoine", "groupe": "top1", "sources": "WID,INSEE"},
    ).json()
    assert len(body) == 2
    conventions = {(s["unite"], s["concept_patrimoine"]) for s in body}
    assert conventions == {("adulte", "net"), ("menage", "brut_hors_reste")}


def test_ambiguous_source_returns_422_with_choices():
    # DGFiP spans two Concepts across the 2018 Rupture; with no concept pinned the
    # resolver is ambiguous, and compare must surface the same 422 contract.
    res = client.get(
        "/api/compare",
        params={"indicateur": "impot_moyen", "groupe": "redevables", "sources": "DGFiP"},
    )
    assert res.status_code == 422
    choices = res.json()["detail"]["choices"]
    assert {c["concept_patrimoine"] for c in choices} == {"total", "immobilier"}


def test_unknown_source_returns_422():
    # `sources` is a free-form CSV, not a closed Literal, so an unknown source is
    # validated in the route: a bogus source is a client error (422), never a
    # silently-degenerate 200.
    res = client.get(
        "/api/compare",
        params={"indicateur": "part_patrimoine", "groupe": "top1", "sources": "BOGUS"},
    )
    assert res.status_code == 422


def test_one_unknown_source_422s_the_whole_request():
    # If any leg is invalid the whole request 422s — we never quietly return the
    # valid leg(s) and drop the bogus one.
    res = client.get(
        "/api/compare",
        params={"indicateur": "part_patrimoine", "groupe": "top1", "sources": "WID,BOGUS"},
    )
    assert res.status_code == 422


def test_ambiguous_insee_concept_returns_422_with_choices():
    # INSEE spans all-inclusive brut and brut hors reste (issue #14); with no
    # concept pinned the Gini query surfaces the same 422 chooser as DGFiP.
    res = client.get(
        "/api/compare",
        params={"indicateur": "gini", "groupe": "ensemble", "sources": "INSEE"},
    )
    assert res.status_code == 422
    choices = res.json()["detail"]["choices"]
    assert {c["concept_patrimoine"] for c in choices} == {"brut", "brut_hors_reste"}
