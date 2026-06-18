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


# --- The emitted OpenAPI schema is the canonical contract (issue #17, ADR 0005) ---
# These assert the SHAPE of the contract the app emits — the closed enums and the
# 422 model wiring — NOT the vocabulary value set (that would make the test a
# fourth mirror of values that legitimately grow via /api/meta). They guard the
# backend->frontend generation seam: if the Pydantic Literals / `responses=`
# declarations regress, the generated types.ts would silently drift.


def _series_param_schema(name: str) -> dict:
    """The OpenAPI schema of a /api/series query parameter (unwrapping the
    `anyOf [<schema>, null]` that an Optional param emits)."""
    params = app.openapi()["paths"]["/api/series"]["get"]["parameters"]
    schema = next(p["schema"] for p in params if p["name"] == name)
    if "anyOf" in schema:  # Optional param -> anyOf [<enum>, {type: null}]
        schema = next(s for s in schema["anyOf"] if s.get("type") != "null")
    return schema


def test_openapi_closes_curated_axes_as_enums():
    """Source/Unite/Indicateur are closed `Literal`s in BOTH the models and the
    route params, so the route params are OpenAPI enums (-> generated TS unions,
    and FastAPI 422s an unknown value for free)."""
    for name in ("source", "indicateur", "unite"):
        schema = _series_param_schema(name)
        assert isinstance(schema.get("enum"), list) and schema["enum"], (
            f"query param {name} is not emitted as a non-empty enum schema"
        )


def test_openapi_keeps_concept_axis_open():
    """concept_patrimoine stays an OPEN string discovered via /api/meta — never an
    enum (ADR 0005). The observable proof the hybrid split is structural, not a
    convention."""
    schema = _series_param_schema("concept")
    assert schema["type"] == "string"
    assert "enum" not in schema


def test_openapi_declares_ambiguous_convention_422_model():
    """The 422 body is a real Pydantic model (AmbiguousConventionDetail with a
    ConventionChoice list) declared as the 422 response on the resolving routes,
    so it lands in OpenAPI and is generated for the frontend."""
    spec = app.openapi()
    schemas = spec["components"]["schemas"]
    assert "AmbiguousConventionDetail" in schemas
    assert "ConventionChoice" in schemas
    # `error` is a closed literal; `concept_patrimoine` stays an open string.
    detail = schemas["AmbiguousConventionDetail"]["properties"]
    assert detail["error"].get("const") == "ambiguous_convention" or detail["error"].get(
        "enum"
    ) == ["ambiguous_convention"]
    choice = schemas["ConventionChoice"]["properties"]
    assert choice["concept_patrimoine"]["type"] == "string"
    assert "enum" not in choice["concept_patrimoine"]
    # Declared as the 422 response component on every Convention-resolving route.
    for path in ("/api/series", "/api/compare", "/api/export.csv"):
        responses = spec["paths"][path]["get"]["responses"]
        assert "422" in responses, f"{path} missing a declared 422 response"
        ref = responses["422"]["content"]["application/json"]["schema"]["$ref"]
        assert ref.endswith("/AmbiguousConventionDetail"), (
            f"{path} 422 is not the AmbiguousConventionDetail model ({ref})"
        )


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


def test_series_closed_axis_rejects_unknown_value_with_422():
    """A bogus value on a closed axis (source) is rejected by FastAPI with 422 —
    the closed half of the hybrid vocabulary split (ADR 0005)."""
    res = client.get(
        "/api/series",
        params={"source": "BOGUS", "indicateur": "part_patrimoine", "groupe": "top1"},
    )
    assert res.status_code == 422


def test_series_open_axis_accepts_unknown_value_with_200_empty_points():
    """A made-up value on the OPEN concept axis is NOT rejected: it returns 200
    with empty `points` (no rows match), so a new concept needs no code change —
    the open half of the hybrid split (ADR 0005)."""
    res = client.get(
        "/api/series",
        params={
            "source": "WID",
            "indicateur": "part_patrimoine",
            "groupe": "top1",
            "concept": "made_up",
        },
    )
    assert res.status_code == 200
    assert res.json()["points"] == []


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
