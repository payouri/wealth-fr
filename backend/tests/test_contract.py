"""Contract tests against HANDOFF.md §6.4.

STUB: health check passes today; the contract tests are written but skipped
until the endpoints are implemented (jalon 3). Un-skip as each lands.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    assert client.get("/api/health").json() == {"status": "ok"}


@pytest.mark.skip(reason="jalon 3: implement /api/meta")
def test_meta_lists_dimensions():
    body = client.get("/api/meta").json()
    for key in ("sources", "indicateurs", "groupes", "concepts", "unites"):
        assert key in body


@pytest.mark.skip(reason="jalon 3: implement /api/series")
def test_series_keeps_convention():
    body = client.get(
        "/api/series",
        params={"source": "WID", "indicateur": "part_patrimoine", "groupe": "top1"},
    ).json()
    # The Convention must survive into the response (CONTEXT.md guard rail).
    assert "unite" in body and "concept_patrimoine" in body
