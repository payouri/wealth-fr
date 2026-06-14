"""Pipeline output — Parquet beside the cumulative CSV (jalon 2, issue #3).

The pipeline already writes a cumulative CSV (the canonical fallback the backend
reads when no Parquet is present). The backend *prefers* a Parquet fast path
(`_source_relation`), so the output step must also emit a Parquet of the same
cumulative dataframe. These tests assert the round-trip through the pipeline's
public output interface (`write_outputs`): the Parquet's rows and columns equal
the cumulative CSV's, including across an append (the dataframe is cumulative,
not just the latest extraction).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

# `write_outputs` lives in the pipeline package at the repo root; the backend
# test suite runs from `backend/`, so put `pipeline/` on the path to import it.
PIPELINE_DIR = Path(__file__).resolve().parents[2] / "pipeline"
if str(PIPELINE_DIR) not in sys.path:
    sys.path.insert(0, str(PIPELINE_DIR))

from build_dataset import OUTPUT_STEM, write_outputs  # noqa: E402


def _sample_df(date_extraction: str = "2024-01-01", millesime: str = "WID 2024") -> pd.DataFrame:
    """A tidy-schema slice big enough to exercise the round-trip (HANDOFF §3)."""
    return pd.DataFrame(
        [
            {
                "annee": 2015,
                "source": "WID",
                "concept_patrimoine": "net",
                "unite": "adulte",
                "groupe": "top1",
                "indicateur": "part_patrimoine",
                "valeur": 0.24,
                "unite_valeur": "%",
                "euros_constants": False,
                "date_extraction": date_extraction,
                "millesime_source": millesime,
                "notes": "",
            },
            {
                "annee": 2016,
                "source": "WID",
                "concept_patrimoine": "net",
                "unite": "adulte",
                "groupe": "top1",
                "indicateur": "part_patrimoine",
                "valeur": 0.25,
                "unite_valeur": "%",
                "euros_constants": False,
                "date_extraction": date_extraction,
                "millesime_source": millesime,
                "notes": "",
            },
        ]
    )


def _rows(df: pd.DataFrame) -> list[tuple[str, ...]]:
    """Order-independent row multiset, normalised past CSV's lossy text encoding.

    Reading back a CSV turns empty strings into NaN and typed values into text;
    Parquet preserves them faithfully. Comparing each cell as a filled string
    makes "same rows" mean the data, not the serialisation format.
    """
    text = df.fillna("").astype(str)
    return sorted(tuple(row) for row in text.itertuples(index=False, name=None))


def test_parquet_written_beside_csv_matches_cumulative_rows_and_columns(tmp_path):
    df = _sample_df()

    write_outputs(df, OUTPUT_STEM, append=False, out_dir=tmp_path)

    csv_path = tmp_path / f"{OUTPUT_STEM}.csv"
    parquet_path = tmp_path / f"{OUTPUT_STEM}.parquet"
    assert parquet_path.exists(), "pipeline must emit a Parquet beside the cumulative CSV"

    from_csv = pd.read_csv(csv_path)
    from_parquet = pd.read_parquet(parquet_path)

    assert list(from_parquet.columns) == list(from_csv.columns)
    assert _rows(from_parquet) == _rows(from_csv)


def test_parquet_reflects_the_cumulative_dataframe_after_append(tmp_path):
    # First extraction lands a CSV + Parquet…
    write_outputs(_sample_df(), OUTPUT_STEM, append=True, out_dir=tmp_path)
    # …a later extraction (new millésime, new rows) appends to both.
    second = _sample_df(date_extraction="2025-02-01", millesime="WID 2025")
    second.loc[:, "annee"] = [2017, 2018]
    write_outputs(second, OUTPUT_STEM, append=True, out_dir=tmp_path)

    csv_path = tmp_path / f"{OUTPUT_STEM}.csv"
    parquet_path = tmp_path / f"{OUTPUT_STEM}.parquet"

    from_csv = pd.read_csv(csv_path)
    from_parquet = pd.read_parquet(parquet_path)

    # The Parquet is the *cumulative* dataframe, not just the latest extraction:
    # it carries both extractions and equals the cumulative CSV row-for-row.
    assert len(from_parquet) == 4
    assert _rows(from_parquet) == _rows(from_csv)
