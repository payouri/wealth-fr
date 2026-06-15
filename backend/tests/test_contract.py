"""Contract tests against the API contract (`app/models.py` + the route signatures
in `app/main.py`) — endpoint-level, via TestClient.

The dataset is the committed fixture (see conftest). These exercise the HTTP
contract: the Convention echo, the 422-with-choices on ambiguity, the empty
`points` on no-match, the default Millésime, and the Rupture annotation.
"""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    assert client.get("/api/health").json() == {"status": "ok"}


def test_meta_lists_dimensions():
    body = client.get("/api/meta").json()
    for key in ("sources", "indicateurs", "groupes", "concepts", "unites"):
        assert key in body
    assert set(body["sources"]) == {"WID", "INSEE", "DGFiP"}


def test_series_keeps_convention():
    body = client.get(
        "/api/series",
        params={
            "source": "WID",
            "indicateur": "part_patrimoine",
            "groupe": "top1",
            "concept": "net",
        },
    ).json()
    # The Convention must survive into the response (CONTEXT.md guard rail).
    assert body["unite"] == "adulte"
    assert body["concept_patrimoine"] == "net"
    assert body["unite_valeur"] == "%"
    assert body["millesime_source"] == "WID 2026"  # latest by date_extraction


def test_series_ambiguous_convention_returns_422_with_choices():
    res = client.get(
        "/api/series",
        params={"source": "DGFiP", "indicateur": "impot_moyen", "groupe": "redevables"},
    )
    assert res.status_code == 422
    choices = res.json()["detail"]["choices"]
    assert {c["concept_patrimoine"] for c in choices} == {"total", "immobilier"}


def test_series_no_match_returns_200_empty_points():
    res = client.get(
        "/api/series",
        params={
            "source": "WID",
            "indicateur": "part_patrimoine",
            "groupe": "bottom50",
            "concept": "net",
        },
    )
    assert res.status_code == 200
    assert res.json()["points"] == []


def test_series_dgfip_carries_2018_rupture():
    body = client.get(
        "/api/series",
        params={
            "source": "DGFiP",
            "indicateur": "impot_moyen",
            "groupe": "redevables",
            "concept": "immobilier",
            "annee_min": 2018,
            "annee_max": 2020,
        },
    ).json()
    assert [(r["annee"], r["label"]) for r in body["ruptures"]] == [
        (2018, "ISF (total) → IFI (immobilier)")
    ]
