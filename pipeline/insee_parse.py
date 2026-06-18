#!/usr/bin/env python3
"""
insee_parse.py
==============
Parser for the **real** INSEE Melodi *Enquête Patrimoine / HVP* aggregates
(dataset ``DS_ENQPAT_DET``), issue #14. Sibling of ``dgfip_parse``.

``build_dataset.load_insee`` used to emit three hand-curated points. This module
turns INSEE's machine-readable Melodi export into rows of the tidy §3 schema (the
same dict shape ``load_insee`` stamps and concatenates), so INSEE becomes a real,
refreshable Source covering the HVP waves (1998→2024) with Gini, a top-share
ladder and level series.

Melodi ships a bundled CSV archive holding a **data** file and a **metadata**
(codelist) file. The data file is structure-specific SDMX-CSV: one column per
dimension (``GEO, TIME_PERIOD, ENQPAT_MEASURE, QUANTILE_MEASURE, QUANTILE, PCS,
AGE, …``) plus the value column ``OBS_VALUE_NIVEAU``. The measure code lives in
``ENQPAT_MEASURE``; the metadata file decodes the codes to labels.

Conventions (non-negotiable #1): INSEE spans four ``concept_patrimoine`` values —
all-inclusive ``brut``/``net`` and the *hors reste* variants
``brut_hors_reste``/``net_hors_reste`` — each a distinct Convention, never merged.
The Unité is ``menage`` throughout. Only the wealth-ranking axis
(``QUANTILE_MEASURE = PATBRUT``) is ingested; the by-living-standard (``NIVVIE``)
cross-cut is dropped. Only nominal (current-euro, ``…_COUR``) levels are emitted —
the pipeline deflates them itself to the project base, alongside the nominal rows.
"""

from __future__ import annotations

import csv
import tempfile
import zipfile
from pathlib import Path

# The data file is recognised by its value column; whichever CSV in the bundle
# carries it is the data file, the other is the metadata codelist. Identifying by
# content (not filename) survives Melodi renaming the files inside the archive.
_DATA_MARKER = "OBS_VALUE_NIVEAU"

# The SDMX "total" sentinel on a breakdown dimension, and the no-comparison
# sentinel on COMPARE_TIME — together they select the national, current figure.
_TOTAL = "_T"
_NO_COMPARE = "_Z"

# Only populations ranked by wealth are concentration series; the by-living-
# standard cross-cut (QUANTILE_MEASURE = NIVVIE) is a different analytical cut.
_WEALTH_RANKING = "PATBRUT"

# Breakdown dimensions that must be the SDMX total "_T" for the national figure:
# a non-total on any of them is a sub-population cut (by PCS, age, urbanisation,
# household type) we do not ingest as a concentration series.
_BREAKDOWN_DIMS = ("PCS", "AGE", "DEG_URB_UNIT", "TPH")


def _is_national_current(obs: dict) -> bool:
    """True for the national, current-period observation (every breakdown dim
    is the total ``_T`` and COMPARE_TIME is the no-comparison sentinel ``_Z``)."""
    if obs.get("COMPARE_TIME", _NO_COMPARE) != _NO_COMPARE:
        return False
    return all(obs.get(dim, _TOTAL) == _TOTAL for dim in _BREAKDOWN_DIMS)


# Whole-population measures: ENQPAT_MEASURE code -> (indicateur, concept). These
# describe the `ensemble` groupe. The mean-amount measures carry the "…_COUR"
# (courant / nominal) suffix; only those are ingested — the constant-euro variants
# use INSEE's own base, which we never mix with the project base.
_MEASURE_MAP: dict[str, tuple[str, str]] = {
    "MT_MOY_PATBRUT_COUR": ("patrimoine_moyen", "brut"),
    "MT_MOY_PATBRUT_HR_COUR": ("patrimoine_moyen", "brut_hors_reste"),
    "MT_MOY_PATNET_COUR": ("patrimoine_moyen", "net"),
    "MT_MOY_PATNET_HR_COUR": ("patrimoine_moyen", "net_hors_reste"),
    # GINI_PATBRUT_HR is the headline 1998→2024 series. Melodi's metadata labels
    # it "net" — that is an UPSTREAM MISLABEL. It is authoritatively *brut hors
    # reste* per INSEE's publications, so we route it to brut_hors_reste here on
    # purpose. Do NOT "fix" this back to net (issue #14 landmine).
    "GINI_PATBRUT_HR": ("gini", "brut_hors_reste"),
    "GINI_PATBRUT": ("gini", "brut"),
}

# Cumulative wealth-mass measures -> the concept of the resulting `part_patrimoine`
# ladder. The groupe comes from the QUANTILE band (below). Shares exist for the
# brut-family only (issue #14: no net Gini / net share in this dataset).
_MASSE_CONCEPT: dict[str, str] = {
    "MASSE_PATBRUT": "brut",
    "MASSE_PATBRUT_HR": "brut_hors_reste",
}

# QUANTILE band -> share groupe. The mass held by each top band IS its top share.
_QUANTILE_SHARE_GROUPE: dict[str, str] = {
    "C99TC100": "top1",
    "C95TC100": "top5",
    "D9TD10": "top10",
    "D5TD10": "top50",
}

# Median-amount measures -> concept. These reuse the `seuil` indicateur (matching
# WID's threshold mapping) with the `mediane` groupe — no new indicateur. `net`
# carries a median (levels-only); there is no net Gini/share in this dataset.
_MEDIAN_CONCEPT: dict[str, str] = {
    "MT_MED_PATBRUT": "brut",
    "MT_MED_PATBRUT_HR": "brut_hors_reste",
    "MT_MED_PATNET": "net",
    "MT_MED_PATNET_HR": "net_hors_reste",
}

# Decile-threshold measures -> concept; the groupe comes from the QUANTILE
# boundary point. Also `seuil`, with the `decile_1`/`decile_9` groupes.
_SEUIL_CONCEPT: dict[str, str] = {
    "MT_SEUIL_PATBRUT": "brut",
    "MT_SEUIL_PATBRUT_HR": "brut_hors_reste",
    "MT_SEUIL_PATNET": "net",
    "MT_SEUIL_PATNET_HR": "net_hors_reste",
}
_QUANTILE_DECILE_GROUPE: dict[str, str] = {"D1": "decile_1", "D9": "decile_9"}


def _unite_valeur(indicateur: str) -> str:
    """The value's unit, by indicateur (shares %, Gini indice, levels euros)."""
    if indicateur == "gini":
        return "indice"
    if indicateur == "part_patrimoine":
        return "%"
    return "euros"


def _classify(measure: str, quantile: str) -> tuple[str, str, str] | None:
    """Map a (ENQPAT_MEASURE, QUANTILE) pair to (indicateur, concept, groupe).

    Returns None for measures/bands we do not ingest, so the caller skips them.
    """
    if measure in _MASSE_CONCEPT:
        groupe = _QUANTILE_SHARE_GROUPE.get(quantile)
        if groupe is None:
            return None
        return ("part_patrimoine", _MASSE_CONCEPT[measure], groupe)
    if measure in _MEDIAN_CONCEPT:
        return ("seuil", _MEDIAN_CONCEPT[measure], "mediane")
    if measure in _SEUIL_CONCEPT:
        groupe = _QUANTILE_DECILE_GROUPE.get(quantile)
        if groupe is None:
            return None
        return ("seuil", _SEUIL_CONCEPT[measure], groupe)
    mapped = _MEASURE_MAP.get(measure)
    if mapped is None:
        return None
    indicateur, concept = mapped
    return (indicateur, concept, "ensemble")


def parse_melodi_archive(archive_path: Path) -> list[dict]:
    """Parse a bundled Melodi CSV archive (one data file + one metadata file).

    Locates the two CSVs by content (the data file carries ``OBS_VALUE_NIVEAU``),
    so it survives Melodi renaming the members. Returns [] for a non-zip or an
    archive missing the data file, so a caller can fall through to its fallback.
    """
    if not zipfile.is_zipfile(archive_path):
        return []
    with zipfile.ZipFile(archive_path) as z, tempfile.TemporaryDirectory() as tmp:
        members = [m for m in z.namelist() if m.lower().endswith(".csv")]
        data_member = meta_member = None
        for m in members:
            header = z.read(m)[:4096].decode("utf-8", errors="replace")
            if _DATA_MARKER in header:
                data_member = m
            else:
                meta_member = m
        if data_member is None:
            return []
        data_path = Path(z.extract(data_member, tmp))
        meta_path = Path(z.extract(meta_member, tmp)) if meta_member else data_path
        return parse_melodi_csv(data_path, meta_path)


def _load_labels(meta_path: Path) -> dict[str, str]:
    """Decode the bundled metadata (codelist) into {code: label}. Reading the
    labels from the dataset's own metadata — rather than hard-coding them — keeps
    the decode surviving upstream code additions (issue #14). Tolerant of a missing
    or oddly-shaped file (returns {} so the parser still emits rows)."""
    labels: dict[str, str] = {}
    if not meta_path.exists():
        return labels
    with open(meta_path, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            code = (row.get("code") or "").strip()
            label = (row.get("label") or "").strip()
            if code:
                labels[code] = label
    return labels


def parse_melodi_csv(data_path: Path, meta_path: Path) -> list[dict]:
    """Parse a Melodi data CSV (+ metadata codelist) into tidy Observations."""
    labels = _load_labels(meta_path)
    rows: list[dict] = []
    with open(data_path, encoding="utf-8") as f:
        for obs in csv.DictReader(f):
            if obs.get("QUANTILE_MEASURE") != _WEALTH_RANKING:
                continue
            if not _is_national_current(obs):
                continue
            measure = obs.get("ENQPAT_MEASURE", "")
            classified = _classify(measure, obs.get("QUANTILE", ""))
            if classified is None:
                continue
            indicateur, concept, groupe = classified
            value = obs.get("OBS_VALUE_NIVEAU")
            if not value:  # blank / missing -> skip (also narrows away None)
                continue
            rows.append(
                _row(
                    int(obs["TIME_PERIOD"]),
                    concept,
                    groupe,
                    indicateur,
                    float(value),
                    labels.get(measure, ""),
                )
            )
    return rows + _derive_bottom50(rows)


def _row(
    annee: int, concept: str, groupe: str, indicateur: str, valeur: float, label: str = ""
) -> dict:
    note = "INSEE Melodi DS_ENQPAT_DET"
    if label:
        note = f"{note} — {label}"
    return {
        "annee": annee,
        "source": "INSEE",
        "concept_patrimoine": concept,
        "unite": "menage",
        "groupe": groupe,
        "indicateur": indicateur,
        "valeur": valeur,
        "unite_valeur": _unite_valeur(indicateur),
        "euros_constants": False,
        "notes": note,
    }


def _derive_bottom50(rows: list[dict]) -> list[dict]:
    """`bottom50` share = 100 − top50, within each (concept, year). Derived, not
    measured — INSEE publishes the top ladder; the bottom half is its complement."""
    return [
        _row(
            r["annee"], r["concept_patrimoine"], "bottom50", "part_patrimoine", 100.0 - r["valeur"]
        )
        for r in rows
        if r["indicateur"] == "part_patrimoine" and r["groupe"] == "top50"
    ]
