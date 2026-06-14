"""Shared fixtures: point the backend at a small committed CSV fixture that
conforms to the §3 tidy schema, and expose a DuckDB relation for unit tests.

The fixture covers: all three Sources (Meta + guard rail); DGFiP's two Concepts
`total`/`immobilier` (the 422 path + the 2018 Rupture); one Révision (the same
HIST_KEYS tuple in two Millésimes with different `date_extraction`); and a level
indicator with both nominal and `euros_constants` rows.
"""

from __future__ import annotations

from pathlib import Path

import duckdb
import pytest

from app import data

FIXTURE_CSV = Path(__file__).parent / "fixtures" / "dataset_fixture.csv"


@pytest.fixture(autouse=True)
def _point_backend_at_fixture(monkeypatch):
    """Make the endpoints (and get_meta/get_series wrappers) read the fixture.

    Parquet is pointed at a non-existent path so the CSV branch is exercised by
    default; the Parquet-preferred branch has its own dedicated test.
    """
    monkeypatch.setattr(data, "CSV", FIXTURE_CSV)
    monkeypatch.setattr(data, "PARQUET", FIXTURE_CSV.with_suffix(".does-not-exist.parquet"))


@pytest.fixture
def con() -> duckdb.DuckDBPyConnection:
    return duckdb.connect(database=":memory:")


@pytest.fixture
def relation() -> str:
    """A DuckDB-readable reference to the fixture, for isolation tests."""
    return f"read_csv_auto('{FIXTURE_CSV}')"
