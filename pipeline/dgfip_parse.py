#!/usr/bin/env python3
"""
dgfip_parse.py
==============
Parsers for the **real** DGFiP ISF/IFI Excel workbooks (jalon 6.5).

`build_dataset.load_dgfip` used to read either a curated CSV or the pre-filled
`DGFIP_POINTS`; the `--download` path fetched files but nothing parsed them.
This module fills that gap: it turns the official DGFiP workbooks into rows of
the tidy §3 schema (the same dict shape `load_dgfip` stamps and concatenates).

National workbooks recognised (the `*com*` files are commune-level and
deliberately ignored — they are not the national concentration series):

1. **IFI breakdowns** — `nid_25582/25583/25584_*.xls`, one sheet per year. The
   IFI page exposes the *same* population sliced three ways; each slice is a
   distinct Convention dimension, so the décile/tranche index is **namespaced**
   into `groupe` to prevent HIST_KEYS collisions:
     - `/node/25582` patrimoine net taxable → `groupe = decile_patrimoine_{1..10}`
     - `/node/25583` RFR des redevables     → `groupe = decile_rfr_{1..10}`
     - `/node/25584` taux marginal          → `groupe = tranche_marginale_{n}`
   Per (year, slice) it emits whichever of these the sheet carries:
   `impot_moyen`, `patrimoine_moyen` (euros), `nb_foyers` (effectif), `seuil`
   (euros, the borne supérieure). The marginal *rate* is recorded in `notes`
   (no `taux` indicator exists in the contract). Amounts and counts are stored
   in *milliers* → multiplied by 1000; the rate is already a percentage.
   Convention: `concept_patrimoine="immobilier"`, `unite="foyer_fiscal"`.

2. **ISF montants/nombres** — `isf_montants_declares_nombres_1999_2017.xls`
   Sheet `nombres`, row "nombre de déclarations" across year columns. Emits, per
   year, `nb_foyers` (effectif) of ISF redevables.
   Convention: `concept_patrimoine="total"`, `unite="foyer_fiscal"`.

Every emitted row carries its own `millesime_source` (derived from the file) so
that re-extractions of an updated workbook surface as Révisions, not overwrites
(append-only historisation — see AGENTS.md non-negotiable #2). The Convention
columns (`concept_patrimoine`, `unite`) qualify every value and are never mixed
across ISF (total) and IFI (immobilier) — that rupture is the 2018 ISF→IFI break.

`xlrd` reads the legacy `.xls`; `openpyxl` reads `.xlsx` (both via pandas).
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

# Counts and amounts are stored in "milliers" -> multiply by 1000 to reach the
# base unit (euros / effectif). The marginal rate (a %) is excluded from this.
_K = 1000.0

# IFI breakdown sheets are named "a2018" (patrimoine, taux marginal) or
# "ifi_2018" (RFR) — capture the year either way.
_YEAR_SHEET_RE = re.compile(r"^(?:a|ifi_)(\d{4})$", re.IGNORECASE)

# How to recognise each IFI breakdown from its index-column header, the `groupe`
# prefix that namespaces its index, the human label, and the millésime tag.
# (keyword, groupe_prefix, label, millesime_tag) — order matters (RFR before
# PATRIMOINE: the RFR sheet also mentions patrimoine in other columns).
_IFI_KINDS = [
    ("TRANCHE", "tranche_marginale", "tranche de taux marginal", "taux marginal"),
    ("RFR", "decile_rfr", "décile de RFR", "RFR"),
    ("PATRIMOINE", "decile_patrimoine", "décile de patrimoine", "patrimoine"),
]

# Value columns to emit, by header keyword -> (indicateur, unite_valeur). All are
# stored in milliers and scaled by _K. `seuil` (borne supérieure) is handled
# separately; the marginal rate goes to `notes`, not a value column.
_IFI_VALUE_COLS = [
    ("NOMBRE DE REDEVABLES", "nb_foyers", "effectif"),
    ("PATRIMOINE NET TAXABLE MOYEN", "patrimoine_moyen", "euros"),
    ("IMPÔT NET MOYEN", "impot_moyen", "euros"),
]


def _num(x: object) -> float | None:
    """Best-effort numeric parse of a DGFiP cell.

    DGFiP stores numbers inconsistently (real floats, but also text like "1674",
    "5", or the sentinel "." for "not applicable"). Returns None for blanks and
    sentinels so callers can skip them rather than emit a spurious 0.
    """
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return None
    s = str(x).strip().replace("\xa0", "").replace(" ", "")
    if s in ("", ".", "-", "nd", "n.d.", "ns"):
        return None
    s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def _find_col(header: list[object], needle: str) -> int | None:
    """Index of the first header cell containing `needle` (case-insensitive)."""
    up = needle.upper()
    for i, cell in enumerate(header):
        if cell is not None and up in str(cell).upper():
            return i
    return None


def _header_row(raw: pd.DataFrame) -> int | None:
    """Row index of the IFI breakdown header (names the index + impôt columns)."""
    for i in range(min(8, len(raw))):
        cells = raw.iloc[i].tolist()
        if (
            _find_col(cells, "NUMÉRO") is not None
            and _find_col(cells, "IMPÔT NET MOYEN") is not None
        ):
            return i
    return None


# ---------------------------------------------------------------------------
# IFI — déciles (patrimoine / RFR) et tranches de taux marginal
# ---------------------------------------------------------------------------


def parse_ifi_breakdown(path: Path) -> list[dict]:
    """Parse one IFI breakdown workbook (`nid_2558{2,3,4}_*`) -> tidy rows.

    Auto-detects the slice (patrimoine / RFR / taux marginal) from the header so
    each index is namespaced into `groupe`; emits every value column the sheet
    carries plus the `seuil` (borne supérieure).
    """
    xls = pd.ExcelFile(path)
    year_sheets = [
        (s, int(m.group(1))) for s in xls.sheet_names if (m := _YEAR_SHEET_RE.match(str(s)))
    ]
    if not year_sheets:
        return []

    # Detect the breakdown kind from the first sheet's index-column header.
    first = pd.read_excel(path, sheet_name=year_sheets[0][0], header=None)
    hdr = _header_row(first)
    if hdr is None:
        return []
    idx_hdr = str(first.iloc[hdr, _find_col(first.iloc[hdr].tolist(), "NUMÉRO") or 0]).upper()
    prefix = label = tag = None
    for kw, pfx, lbl, mtag in _IFI_KINDS:
        if kw in idx_hdr:
            prefix, label, tag = pfx, lbl, mtag
            break
    if prefix is None:
        return []

    millesime = f"DGFiP IFI {tag} {max(y for _, y in year_sheets)}"
    rows: list[dict] = []
    for sheet, year in year_sheets:
        raw = pd.read_excel(path, sheet_name=sheet, header=None)
        h = _header_row(raw)
        if h is None:
            continue
        header = raw.iloc[h].tolist()
        c_idx = _find_col(header, "NUMÉRO")
        c_borne = _find_col(header, "BORNE SUPÉRIEURE")
        c_taux = _find_col(header, "TAUX")
        value_cols = [(_find_col(header, kw), ind, uv) for kw, ind, uv in _IFI_VALUE_COLS]
        if c_idx is None:
            continue

        for _, r in raw.iloc[h + 1 :].iterrows():
            idx = _num(r.iloc[c_idx])
            if idx is None or not (1 <= idx <= 30):
                continue  # skip the source/footnote rows trailing each sheet
            groupe = f"{prefix}_{int(idx)}"
            note = f"IFI {label} {int(idx)}"
            if c_taux is not None and (taux := _num(r.iloc[c_taux])) is not None:
                note += f" (taux marginal {taux} %)"

            for c, indic, uv in value_cols:
                if c is None:
                    continue
                v = _num(r.iloc[c])
                if v is not None:
                    rows.append(_ifi_row(year, groupe, indic, v * _K, uv, millesime, note))
            if c_borne is not None and (borne := _num(r.iloc[c_borne])) is not None:
                rows.append(
                    _ifi_row(
                        year,
                        groupe,
                        "seuil",
                        borne * _K,
                        "euros",
                        millesime,
                        f"{note} — borne supérieure",
                    )
                )
    return rows


def _ifi_row(year, groupe, indic, valeur, uv, millesime, note) -> dict:
    return {
        "annee": year,
        "source": "DGFiP",
        "concept_patrimoine": "immobilier",
        "unite": "foyer_fiscal",
        "groupe": groupe,
        "indicateur": indic,
        "valeur": round(valeur, 2),
        "unite_valeur": uv,
        "euros_constants": False,
        "millesime_source": millesime,
        "notes": note,
    }


# ---------------------------------------------------------------------------
# ISF — nombre de redevables par année (1999 … 2017)
# ---------------------------------------------------------------------------


def parse_isf_montants(path: Path) -> list[dict]:
    """Parse `isf_montants_declares_nombres_*.xls` -> ISF `nb_foyers` per year.

    Reads the `nombres` sheet, the "nombre de déclarations" row, across the year
    columns of its header row. Fills the documented ISF≤2017 gap (HANDOFF §10).
    """
    xls = pd.ExcelFile(path)
    sheet = next((s for s in xls.sheet_names if str(s).strip().lower() == "nombres"), None)
    if sheet is None:
        return []
    raw = pd.read_excel(path, sheet_name=sheet, header=None)

    # The year header is the row whose cells are 4-digit years.
    year_cols: dict[int, int] = {}
    header_idx = None
    for i in range(min(6, len(raw))):
        cols = {
            j: int(v)
            for j, cell in enumerate(raw.iloc[i].tolist())
            if (v := _num(cell)) is not None and 1990 <= v <= 2035 and float(v).is_integer()
        }
        if cols:
            year_cols, header_idx = cols, i
            break
    if header_idx is None:
        return []

    # The redevables count = the "nombre de déclarations" row.
    count_row = None
    for _, r in raw.iloc[header_idx + 1 :].iterrows():
        label = " ".join(str(c) for c in r.tolist()[:2] if c is not None).lower()
        if "nombre de d" in label and "claration" in label:
            count_row = r
            break
    if count_row is None:
        return []

    millesime = f"DGFiP ISF {max(year_cols.values())}"
    rows: list[dict] = []
    for col, year in year_cols.items():
        n = _num(count_row.iloc[col])
        if n is None:
            continue
        rows.append(
            {
                "annee": year,
                "source": "DGFiP",
                "concept_patrimoine": "total",
                "unite": "foyer_fiscal",
                "groupe": "redevables",
                "indicateur": "nb_foyers",
                "valeur": round(n, 2),
                "unite_valeur": "effectif",
                "euros_constants": False,
                "millesime_source": millesime,
                "notes": "ISF nombre de déclarations (redevables)",
            }
        )
    return rows


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------


def parse_dgfip_excel(path: Path) -> list[dict]:
    """Recognise a DGFiP workbook by its structure and parse it.

    Returns [] for unrecognised files (e.g. the commune-level `*com*` workbooks),
    so a caller iterating a directory can simply skip what it can't read.
    """
    try:
        sheet_names = [str(s) for s in pd.ExcelFile(path).sheet_names]
    except Exception:
        return []

    if any(_YEAR_SHEET_RE.match(s) for s in sheet_names):
        return parse_ifi_breakdown(path)
    if any(s.strip().lower() == "nombres" for s in sheet_names):
        return parse_isf_montants(path)
    return []
