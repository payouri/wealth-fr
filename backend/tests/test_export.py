"""/api/export.csv — stream exactly the rows the jalon-3 resolver selects (jalon
9). Same Convention guard and single-Millésime pick as /api/series; tidy schema
columns; the Convention (unité + concept) is preserved on every row.
"""

import csv
import io

from fastapi.testclient import TestClient

from app.data import EXPORT_COLUMNS, resolve_rows
from app.main import app

client = TestClient(app)


def test_resolve_rows_returns_resolved_millesime_rows_in_tidy_schema(con, relation):
    rows = resolve_rows(
        con,
        relation,
        source="WID",
        indicateur="part_patrimoine",
        groupe="top1",
        concept="net",
    )
    # The default Millésime is the latest (WID 2026), so 2015 is the revised 26.5.
    assert [(r["annee"], r["valeur"]) for r in rows] == [
        (2000, 22.1),
        (2015, 26.5),
        (2021, 27.0),
    ]
    # The Convention is carried on every row (never dropped on export).
    assert all(r["unite"] == "adulte" and r["concept_patrimoine"] == "net" for r in rows)
    assert all(r["millesime_source"] == "WID 2026" for r in rows)


def test_endpoint_streams_csv_with_tidy_columns():
    res = client.get(
        "/api/export.csv",
        params={
            "source": "WID",
            "indicateur": "part_patrimoine",
            "groupe": "top1",
            "concept": "net",
        },
    )
    assert res.status_code == 200
    assert res.headers["content-type"].startswith("text/csv")
    reader = csv.DictReader(io.StringIO(res.text))
    assert reader.fieldnames == EXPORT_COLUMNS
    data_rows = list(reader)
    assert [r["annee"] for r in data_rows] == ["2000", "2015", "2021"]
    assert all(r["unite"] == "adulte" and r["concept_patrimoine"] == "net" for r in data_rows)


def test_endpoint_honours_ambiguity_contract():
    res = client.get(
        "/api/export.csv",
        params={"source": "DGFiP", "indicateur": "impot_moyen", "groupe": "redevables"},
    )
    assert res.status_code == 422
    assert res.json()["detail"]["error"] == "ambiguous_convention"
