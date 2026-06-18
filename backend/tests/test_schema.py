"""GET /api/schema — the machine-readable contract / agent entry point (ADR 0004).

Publishes the Conventions, the per-indicateur `dimensionless` flag (in-band ADR
0003), the known Ruptures, the historisation key, and the guard-rail rules.
"""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_schema_returns_conventions_and_dimensionless_flags():
    body = client.get("/api/schema").json()
    pairs = {
        (c["source"], c["unite"], concept) for c in body["conventions"] for concept in c["concepts"]
    }
    assert ("DGFiP", "foyer_fiscal", "total") in pairs
    assert ("DGFiP", "foyer_fiscal", "immobilier") in pairs

    by_indicateur = {i["indicateur"]: i for i in body["indicateurs"]}
    assert by_indicateur["part_patrimoine"]["dimensionless"] is True
    assert by_indicateur["patrimoine_moyen"]["dimensionless"] is False


def test_schema_surfaces_ruptures_and_rules():
    body = client.get("/api/schema").json()
    assert (2018, "ISF (total) → IFI (immobilier)") in {
        (r["annee"], r["label"]) for r in body["ruptures"] if r["source"] == "DGFiP"
    }
    assert body["historisation_key"] == [
        "annee",
        "source",
        "concept_patrimoine",
        "unite",
        "groupe",
        "indicateur",
    ]
    assert len(body["rules"]) >= 3  # the guard rails, as English strings
