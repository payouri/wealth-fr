"""/api/sources — provenance + licence/attribution per Source (jalon 8, §7).

Static metadata the methodology page renders so reuse terms stay in sync with
the data; every Source must carry a non-empty licence and attribution.
"""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_returns_each_source_with_licence_and_attribution():
    body = client.get("/api/sources").json()
    by_source = {s["source"]: s for s in body}
    # All three Sources of the dataset are described (`SOURCE_INFO` in `app/data.py`).
    assert set(by_source) == {"WID", "INSEE", "DGFiP"}
    for info in body:
        assert info["url"].startswith("http")
        assert info["convention"]
        assert info["licence"]
        assert info["attribution"]
