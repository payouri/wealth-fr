"""INSEE Melodi parser (issue #14).

The pipeline ingests INSEE's *Enquête Patrimoine / Histoire de vie et patrimoine*
(HVP) aggregates live from the Melodi API (dataset ``DS_ENQPAT_DET``) instead of
the three hand-curated points. Melodi ships a bundled CSV archive holding a data
file and a metadata (codelist) file; the parser turns the data file into rows of
the tidy §3 schema, decoding the SDMX codes against the metadata.

These tests build *synthetic* Melodi CSVs mirroring the real structure-specific
layout (no binary fixtures committed): dimensions ``GEO, TIME_PERIOD,
ENQPAT_MEASURE, QUANTILE_MEASURE, QUANTILE, PCS, AGE, …`` plus the value column
``OBS_VALUE_NIVEAU``. They assert the *external behaviour* — the tidy rows — never
the parser's internals. Prior art: the synthetic-workbook DGFiP parser test.
"""

from __future__ import annotations

import sys
from pathlib import Path

# The parser lives in the pipeline package at the repo root.
PIPELINE_DIR = Path(__file__).resolve().parents[2] / "pipeline"
if str(PIPELINE_DIR) not in sys.path:
    sys.path.insert(0, str(PIPELINE_DIR))

import build_dataset  # noqa: E402
import insee_parse  # noqa: E402
import netfetch  # noqa: E402

# Structure-specific SDMX-CSV column order of the real DS_ENQPAT_DET data file.
DATA_COLUMNS = [
    "GEO",
    "TIME_PERIOD",
    "ENQPAT_MEASURE",
    "QUANTILE_MEASURE",
    "QUANTILE",
    "PCS",
    "AGE",
    "DEG_URB_UNIT",
    "TPH",
    "COMPARE_TIME",
    "OBS_VALUE_NIVEAU",
]

# A national-total, current-period observation: every breakdown dimension is the
# SDMX total "_T" and COMPARE_TIME is the no-comparison sentinel "_Z".
_TOTAL = {
    "GEO": "2021-FRANCE-FM",
    "PCS": "_T",
    "AGE": "_T",
    "DEG_URB_UNIT": "_T",
    "TPH": "_T",
    "COMPARE_TIME": "_Z",
}


def _obs(
    measure: str,
    value: float,
    *,
    year: int = 2021,
    quantile_measure: str = "PATBRUT",
    quantile: str = "_T",
) -> dict:
    return {
        **_TOTAL,
        "TIME_PERIOD": year,
        "ENQPAT_MEASURE": measure,
        "QUANTILE_MEASURE": quantile_measure,
        "QUANTILE": quantile,
        "OBS_VALUE_NIVEAU": value,
    }


def _write_melodi(tmp_path: Path, observations: list[dict], metadata: list[tuple[str, str, str]]):
    """Write a synthetic Melodi data CSV + metadata (codelist) CSV; return paths."""
    import csv

    tmp_path.mkdir(parents=True, exist_ok=True)
    data_path = tmp_path / "DS_ENQPAT_DET_data.csv"
    with open(data_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=DATA_COLUMNS)
        w.writeheader()
        for o in observations:
            w.writerow({c: o.get(c, "") for c in DATA_COLUMNS})

    meta_path = tmp_path / "DS_ENQPAT_DET_metadata.csv"
    with open(meta_path, "w", newline="", encoding="utf-8") as f:
        mw = csv.writer(f)
        mw.writerow(["dimension", "code", "label"])
        for row in metadata:
            mw.writerow(row)
    return data_path, meta_path


def test_parses_a_nominal_level_into_one_tidy_insee_row(tmp_path: Path) -> None:
    """Tracer bullet: one mean-amount observation → one tidy INSEE Observation.

    The Convention columns travel with the value: source INSEE, unité menage, and
    a nominal (current-euro) level the pipeline will later deflate itself.
    """
    data, meta = _write_melodi(
        tmp_path,
        [_obs("MT_MOY_PATBRUT_HR_COUR", 175000.0, year=2021)],
        [
            (
                "ENQPAT_MEASURE",
                "MT_MOY_PATBRUT_HR_COUR",
                "Montant moyen du patrimoine brut hors reste (euros courants)",
            )
        ],
    )

    rows = insee_parse.parse_melodi_csv(data, meta)

    assert len(rows) == 1
    r = rows[0]
    assert r["source"] == "INSEE"
    assert r["unite"] == "menage"
    assert r["annee"] == 2021
    assert r["indicateur"] == "patrimoine_moyen"
    assert r["valeur"] == 175000.0
    assert r["unite_valeur"] == "euros"
    assert r["euros_constants"] is False


def test_hors_reste_gini_routed_to_brut_despite_net_metadata_label(tmp_path: Path) -> None:
    """The headline INSEE Gini is ``GINI_PATBRUT_HR``. Melodi's metadata labels it
    "net", but it is authoritatively *brut hors reste* per INSEE's publications —
    the parser must override the mislabel, never trust it."""
    data, meta = _write_melodi(
        tmp_path,
        [_obs("GINI_PATBRUT_HR", 0.662, year=2021)],
        # The deliberate upstream mislabel: "net" in the label, brut in reality.
        [("ENQPAT_MEASURE", "GINI_PATBRUT_HR", "Indice de Gini du patrimoine net hors reste")],
    )

    rows = insee_parse.parse_melodi_csv(data, meta)

    assert len(rows) == 1
    r = rows[0]
    assert r["indicateur"] == "gini"
    assert r["concept_patrimoine"] == "brut_hors_reste"
    assert r["valeur"] == 0.662
    assert r["unite_valeur"] == "indice"


def test_measure_label_is_decoded_from_the_bundled_metadata(tmp_path: Path) -> None:
    """The SDMX codes are decoded against the dataset's own bundled metadata, so
    the human label survives upstream code additions (issue #14): the parser
    carries the metadata's measure label into the Observation's notes."""
    data, meta = _write_melodi(
        tmp_path,
        [_obs("GINI_PATBRUT_HR", 0.662)],
        [("ENQPAT_MEASURE", "GINI_PATBRUT_HR", "Indice de Gini du patrimoine net hors reste")],
    )

    rows = insee_parse.parse_melodi_csv(data, meta)

    assert "Indice de Gini du patrimoine net hors reste" in rows[0]["notes"]


def test_all_inclusive_gini_kept_as_a_distinct_brut_convention(tmp_path: Path) -> None:
    """The all-inclusive ``GINI_PATBRUT`` is a *different quantity* from the
    hors-reste Gini — a separate Convention (``brut``), never merged with it."""
    data, meta = _write_melodi(
        tmp_path,
        [
            _obs("GINI_PATBRUT", 0.645, year=2021),
            _obs("GINI_PATBRUT_HR", 0.662, year=2021),
        ],
        [
            ("ENQPAT_MEASURE", "GINI_PATBRUT", "Indice de Gini du patrimoine brut"),
            ("ENQPAT_MEASURE", "GINI_PATBRUT_HR", "Indice de Gini du patrimoine net hors reste"),
        ],
    )

    rows = insee_parse.parse_melodi_csv(data, meta)

    by_concept = {r["concept_patrimoine"]: r for r in rows if r["indicateur"] == "gini"}
    assert by_concept["brut"]["valeur"] == 0.645
    assert by_concept["brut_hors_reste"]["valeur"] == 0.662


def test_wealth_mass_becomes_share_ladder_with_derived_bottom50(tmp_path: Path) -> None:
    """The cumulative wealth-mass measure (per QUANTILE band) is the top-share
    ladder; the bottom 50 % is derived as ``100 − top50`` within the Convention."""
    data, meta = _write_melodi(
        tmp_path,
        [
            _obs("MASSE_PATBRUT_HR", 30.0, quantile="C99TC100"),  # top1
            _obs("MASSE_PATBRUT_HR", 50.0, quantile="C95TC100"),  # top5
            _obs("MASSE_PATBRUT_HR", 60.0, quantile="D9TD10"),  # top10
            _obs("MASSE_PATBRUT_HR", 92.0, quantile="D5TD10"),  # top50
        ],
        [("ENQPAT_MEASURE", "MASSE_PATBRUT_HR", "Masse de patrimoine brut hors reste détenue")],
    )

    rows = insee_parse.parse_melodi_csv(data, meta)
    shares = {r["groupe"]: r for r in rows if r["indicateur"] == "part_patrimoine"}

    assert {g: shares[g]["valeur"] for g in ("top1", "top5", "top10", "top50")} == {
        "top1": 30.0,
        "top5": 50.0,
        "top10": 60.0,
        "top50": 92.0,
    }
    assert all(r["unite_valeur"] == "%" for r in shares.values())
    assert all(r["concept_patrimoine"] == "brut_hors_reste" for r in shares.values())
    # bottom50 is derived, not measured: 100 − top50.
    assert shares["bottom50"]["valeur"] == 8.0


def test_mean_amounts_carry_their_concept_and_only_nominal_is_kept(tmp_path: Path) -> None:
    """Mean wealth is a level series spanning all four Conventions. Only the
    nominal (current-euro, ``…_COUR``) measures are ingested — the constant-euro
    variant uses INSEE's base and is excluded (the pipeline self-deflates)."""
    data, meta = _write_melodi(
        tmp_path,
        [
            _obs("MT_MOY_PATBRUT_COUR", 200000.0),
            _obs("MT_MOY_PATBRUT_HR_COUR", 175000.0),
            _obs("MT_MOY_PATNET_COUR", 180000.0),
            _obs("MT_MOY_PATNET_HR_COUR", 160000.0),
            _obs("MT_MOY_PATBRUT_HR_CONS", 999999.0),  # constant-euro, INSEE base — excluded
        ],
        [],
    )

    rows = insee_parse.parse_melodi_csv(data, meta)
    means = {
        r["concept_patrimoine"]: r["valeur"] for r in rows if r["indicateur"] == "patrimoine_moyen"
    }

    assert means == {
        "brut": 200000.0,
        "brut_hors_reste": 175000.0,
        "net": 180000.0,
        "net_hors_reste": 160000.0,
    }
    assert all(r["unite_valeur"] == "euros" for r in rows if r["indicateur"] == "patrimoine_moyen")


def test_median_and_decile_thresholds_become_seuil_groupes(tmp_path: Path) -> None:
    """Median and decile thresholds reuse the ``seuil`` indicateur (matching WID's
    threshold mapping), with the new groupes ``mediane``/``decile_1``/``decile_9``.
    A net median exists as a levels-only series (no net Gini/share in this dataset)."""
    data, meta = _write_melodi(
        tmp_path,
        [
            _obs("MT_MED_PATBRUT_HR", 120000.0),
            _obs("MT_SEUIL_PATBRUT_HR", 5000.0, quantile="D1"),
            _obs("MT_SEUIL_PATBRUT_HR", 600000.0, quantile="D9"),
            _obs("MT_MED_PATNET", 110000.0),  # net is levels-only
        ],
        [],
    )

    rows = insee_parse.parse_melodi_csv(data, meta)
    seuils = [r for r in rows if r["indicateur"] == "seuil"]
    by_key = {(r["concept_patrimoine"], r["groupe"]): r["valeur"] for r in seuils}

    assert by_key[("brut_hors_reste", "mediane")] == 120000.0
    assert by_key[("brut_hors_reste", "decile_1")] == 5000.0
    assert by_key[("brut_hors_reste", "decile_9")] == 600000.0
    assert by_key[("net", "mediane")] == 110000.0
    assert all(r["unite_valeur"] == "euros" for r in seuils)


def test_only_national_wealth_ranked_totals_are_ingested(tmp_path: Path) -> None:
    """Concentration series rank by wealth (``QUANTILE_MEASURE = PATBRUT``); the
    by-living-standard (``NIVVIE``) cross-cut and the per-PCS/per-AGE sub-population
    breakdowns are dropped — only the national total (every breakdown dim ``_T``)
    is kept, so the ingested groupes describe wealth concentration."""
    national = _obs("MT_MOY_PATBRUT_HR_COUR", 175000.0)
    by_living_standard = _obs("MT_MOY_PATBRUT_HR_COUR", 99.0, quantile_measure="NIVVIE")
    by_pcs = {**_obs("MT_MOY_PATBRUT_HR_COUR", 88.0), "PCS": "10"}
    by_age = {**_obs("MT_MOY_PATBRUT_HR_COUR", 77.0), "AGE": "Y_LT30"}

    rows = insee_parse.parse_melodi_csv(
        *_write_melodi(tmp_path, [national, by_living_standard, by_pcs, by_age], [])
    )

    means = [r["valeur"] for r in rows if r["indicateur"] == "patrimoine_moyen"]
    assert means == [175000.0]


def test_archive_unzips_data_and_metadata_then_parses(tmp_path: Path) -> None:
    """Melodi ships one bundled CSV archive (data file + metadata file). The
    archive seam locates both inside the zip and parses the data file — the loader
    and the live fetch both hand it a single downloaded archive path."""
    import zipfile

    data, meta = _write_melodi(
        tmp_path / "src",
        [_obs("GINI_PATBRUT_HR", 0.662)],
        [("ENQPAT_MEASURE", "GINI_PATBRUT_HR", "Indice de Gini du patrimoine net hors reste")],
    )
    archive = tmp_path / "DS_ENQPAT_DET.zip"
    with zipfile.ZipFile(archive, "w") as z:
        z.write(data, arcname=data.name)
        z.write(meta, arcname=meta.name)

    rows = insee_parse.parse_melodi_archive(archive)

    assert len(rows) == 1
    assert rows[0]["indicateur"] == "gini"
    assert rows[0]["concept_patrimoine"] == "brut_hors_reste"


def _melodi_archive(tmp_path: Path) -> Path:
    import zipfile

    data, meta = _write_melodi(
        tmp_path / "src",
        [_obs("GINI_PATBRUT_HR", 0.662)],
        [("ENQPAT_MEASURE", "GINI_PATBRUT_HR", "Indice de Gini du patrimoine net hors reste")],
    )
    archive = tmp_path / "DS_ENQPAT_DET.zip"
    with zipfile.ZipFile(archive, "w") as z:
        z.write(data, arcname=data.name)
        z.write(meta, arcname=meta.name)
    return archive


def test_load_insee_parses_a_cached_melodi_archive(tmp_path: Path) -> None:
    """Tier 2 of the fallback chain: a present cached Melodi file is parsed into
    live INSEE Observations (stamped with the extraction date + millésime)."""
    df = build_dataset.load_insee(_melodi_archive(tmp_path), "2026-06-16", "INSEE ENQPAT 2026-05")

    assert set(df["source"]) == {"INSEE"}
    assert (df["concept_patrimoine"] == "brut_hors_reste").any()
    assert (df["indicateur"] == "gini").any()
    assert (df["date_extraction"] == "2026-06-16").all()
    assert (df["millesime_source"] == "INSEE ENQPAT 2026-05").all()


def test_load_insee_falls_back_to_hors_reste_stub(tmp_path: Path) -> None:
    """Tier 3: with no cached file, the small curated stub is used — relabelled to
    ``brut_hors_reste`` to be truthful about what INSEE's headline Gini actually is."""
    df = build_dataset.load_insee(tmp_path / "missing.zip", "2026-06-16", "INSEE stub")

    assert set(df["source"]) == {"INSEE"}
    assert set(df["concept_patrimoine"]) == {"brut_hors_reste"}
    assert len(df) == len(build_dataset.INSEE_STUB)


def test_insee_melodi_dataset_is_env_overridable(monkeypatch) -> None:
    """The Melodi dataset id lives in an env-overridable registry, so the fetch can
    be repointed without a code change if INSEE renames the dataset (issue #14)."""
    monkeypatch.delenv("INSEE_MELODI_DATASET", raising=False)
    assert netfetch.insee_melodi_dataset() == "DS_ENQPAT_DET"

    monkeypatch.setenv("INSEE_MELODI_DATASET", "DS_ENQPAT_V2")
    assert netfetch.insee_melodi_dataset() == "DS_ENQPAT_V2"


def test_deep_waves_receive_constant_euro_observations() -> None:
    """INSEE's deep HVP waves (1998, 2004, 2010) must deflate to the project base,
    not be silently dropped — the CPI table is extended to cover them (issue #14)."""
    import pandas as pd

    nominal = pd.DataFrame(
        [
            {
                "annee": year,
                "source": "INSEE",
                "concept_patrimoine": "brut_hors_reste",
                "unite": "menage",
                "groupe": "ensemble",
                "indicateur": "patrimoine_moyen",
                "valeur": 100000.0,
                "unite_valeur": "euros",
                "euros_constants": False,
                "date_extraction": "2026-06-16",
                "millesime_source": "INSEE ENQPAT 2026-05",
                "notes": "",
            }
            for year in (1998, 2004, 2010)
        ]
    )

    out = build_dataset.deflate_levels(nominal, base_year=build_dataset.BASE_DEFLATION)
    deflated_years = set(out[out["euros_constants"]]["annee"])
    assert {1998, 2004, 2010} <= deflated_years
