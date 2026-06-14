"""Dataset source resolver — Parquet-preferred, CSV-fallback, explicit error."""

from pathlib import Path

import pytest

from app import data
from app.data import _source_relation


def test_prefers_parquet_when_present(con, tmp_path, monkeypatch):
    parquet = tmp_path / "dataset.parquet"
    con.execute(f"COPY (SELECT * FROM read_csv_auto('{data.CSV}')) TO '{parquet}' (FORMAT PARQUET)")
    monkeypatch.setattr(data, "PARQUET", parquet)
    monkeypatch.setattr(data, "CSV", Path("/nonexistent/should-not-be-read.csv"))

    relation = _source_relation(con)

    assert "read_parquet" in relation
    # The relation is queryable and round-trips the fixture rows.
    [(count,)] = con.execute(f"SELECT count(*) FROM {relation}").fetchall()
    assert count > 0


def test_falls_back_to_csv_when_no_parquet(con, monkeypatch):
    monkeypatch.setattr(data, "PARQUET", Path("/nonexistent/missing.parquet"))
    # data.CSV already points at the fixture (conftest autouse).
    relation = _source_relation(con)
    assert "read_csv_auto" in relation


def test_raises_when_no_dataset_exists(con, monkeypatch):
    monkeypatch.setattr(data, "PARQUET", Path("/nonexistent/missing.parquet"))
    monkeypatch.setattr(data, "CSV", Path("/nonexistent/missing.csv"))
    with pytest.raises(FileNotFoundError):
        _source_relation(con)
