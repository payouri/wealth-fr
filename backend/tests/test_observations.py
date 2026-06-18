"""GET /api/observations — the faithful, unpinned agent access surface (ADR 0004).

The explicit contract difference from /api/series: this endpoint co-locates
self-describing rows across Conventions and NEVER 422s on ambiguity.
"""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_no_params_returns_envelope_with_self_describing_rows():
    res = client.get("/api/observations")
    assert res.status_code == 200
    body = res.json()
    for key in ("query", "total", "limit", "offset", "observations"):
        assert key in body
    assert body["total"] == len(body["observations"])  # fixture fits under the limit
    # Every row is self-describing: Convention + value semantics + traceability.
    row = body["observations"][0]
    for field in (
        "source",
        "concept_patrimoine",
        "unite",
        "groupe",
        "indicateur",
        "valeur",
        "unite_valeur",
        "millesime_source",
        "date_extraction",
    ):
        assert field in row


def test_query_spanning_dgfip_two_concepts_returns_both_never_422():
    # The defining contract difference from /api/series: DGFiP's total + immobilier
    # come back co-located, never a 422 chooser (ADR 0004).
    res = client.get(
        "/api/observations",
        params={"source": "DGFiP", "indicateur": "impot_moyen", "groupe": "redevables"},
    )
    assert res.status_code == 200
    concepts = {r["concept_patrimoine"] for r in res.json()["observations"]}
    assert concepts == {"total", "immobilier"}


def test_empty_match_is_a_normal_200_with_empty_list():
    res = client.get("/api/observations", params={"source": "WID", "groupe": "bottom50"})
    assert res.status_code == 200
    body = res.json()
    assert body["observations"] == []
    assert body["total"] == 0


def test_comma_list_filter_selects_the_union():
    res = client.get("/api/observations", params={"source": "WID,INSEE"})
    assert res.status_code == 200
    sources = {r["source"] for r in res.json()["observations"]}
    assert sources == {"WID", "INSEE"}


def test_limit_and_offset_slice_while_total_stays_full():
    full = client.get("/api/observations", params={"source": "WID"}).json()
    page = client.get("/api/observations", params={"source": "WID", "limit": 2}).json()
    assert page["total"] == full["total"]
    assert len(page["observations"]) == 2


def test_malformed_paging_params_are_rejected_as_422_not_500():
    # Negative offset / non-positive limit would otherwise reach DuckDB's
    # LIMIT/OFFSET and raise a BinderException → uncaught 500 on the public agent
    # surface. FastAPI's Query bounds (offset>=0, limit in [1,50000]) reject them.
    assert client.get("/api/observations", params={"offset": -1}).status_code == 422
    assert client.get("/api/observations", params={"limit": -1}).status_code == 422
    assert client.get("/api/observations", params={"limit": 0}).status_code == 422
    assert client.get("/api/observations", params={"limit": 50001}).status_code == 422
