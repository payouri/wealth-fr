"""Data access — load the harmonized dataset into DuckDB and run queries.

DuckDB reads the Parquet output of the pipeline natively, which suits the
filter/group queries behind /api/series and /api/revisions. Falls back to the
cumulative CSV if Parquet is absent.

STUB: connection helper sketched; query functions are placeholders.
"""

from __future__ import annotations

import os
from pathlib import Path

import duckdb

PARQUET = Path(
    os.environ.get("DATASET_PARQUET", "pipeline/out/dataset_concentration_patrimoine_fr.parquet")
)
CSV = Path(os.environ.get("DATASET_CSV", "pipeline/out/dataset_concentration_patrimoine_fr.csv"))

# Historisation key — identifies one observation across millésimes (CONTEXT.md).
HIST_KEYS = ["annee", "source", "concept_patrimoine", "unite", "groupe", "indicateur"]


def _source_relation(con: duckdb.DuckDBPyConnection) -> str:
    """Return a DuckDB-readable reference to the dataset (Parquet preferred)."""
    if PARQUET.exists():
        return f"read_parquet('{PARQUET}')"
    if CSV.exists():
        return f"read_csv_auto('{CSV}')"
    raise FileNotFoundError(
        "No dataset found. Run the pipeline first: "
        "`python pipeline/build_dataset.py` (and add a Parquet output, jalon 2)."
    )


def connect() -> duckdb.DuckDBPyConnection:
    return duckdb.connect(database=":memory:")


# TODO(jalon 3): implement against the contract in models.py / HANDOFF.md §6.4
def get_meta() -> dict:
    raise NotImplementedError


def get_series(**filters) -> dict:
    """Filter by source, indicateur, groupe, concept, unite, annee_min/max,
    euros_constants. MUST keep unite + concept_patrimoine in the result."""
    raise NotImplementedError


def get_revisions() -> list[dict]:
    """Observations sharing a HIST_KEYS tuple across >1 millésime_source."""
    raise NotImplementedError
