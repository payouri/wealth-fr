#!/usr/bin/env python3
"""
build_dataset.py
================
Construit un dataset harmonisé et HISTORISÉ sur la CONCENTRATION DU PATRIMOINE
EN FRANCE depuis les années 2000, en combinant plusieurs sources publiques.

Pourquoi combiner les sources ?
-------------------------------
Les enquêtes par sondage (INSEE) décrivent bien l'ensemble des ménages mais
sous-estiment le tout-haut de la distribution. WID.world corrige ce biais via
données fiscales + comptabilité nationale. Les données fiscales DGFiP (ISF/IFI)
donnent une vue administrative directe du sommet. On garde les trois en
colonne `source`.

Historisation
-------------
Deux niveaux :
  1. Historisation temporelle des DONNÉES : colonne `annee` -> séries depuis 2000.
  2. Historisation des EXTRACTIONS / RÉVISIONS : chaque ligne porte
     `date_extraction` (quand on a tiré la donnée) et `millesime_source`
     (version du fichier source, ex. "WID 2024" / "DGFiP IFI 2024").
     La sortie est écrite en APPEND horodaté : on n'écrase jamais l'historique,
     on empile les extractions successives. On peut ainsi tracer une révision
     (ex. "top 1% en 2015" recalculé entre deux millésimes WID).

Sources
-------
1. WID.world  -> parts du sommet, Gini, moyennes. ADULTE / patrimoine NET.
   Fichier : data/WID_data_FR.csv  (sép. ';' : country;variable;percentile;year;value)
   https://wid.world -> Data -> France -> "Download all data".
2. INSEE      -> Gini, masses détenues. MÉNAGE / patrimoine BRUT.
   Points officiels pré-remplis (Insee Références "Revenus et patrimoine").
3. DGFiP      -> ISF (<=2017, TOUT le patrimoine) puis IFI (>=2018, IMMOBILIER
   seulement) : nb de redevables, patrimoine moyen, impôt moyen. FOYER FISCAL.
   /!\\ RUPTURE DE SÉRIE EN 2018 (ISF -> IFI), encodée via `concept_patrimoine`.
   Excel/CSV : impots.gouv.fr (DGFiP Statistiques) et data.gouv.fr.

Sortie
------
- dataset_concentration_patrimoine_fr.csv   (cumulatif, append horodaté)
- dataset_concentration_patrimoine_fr_<timestamp>.xlsx  (snapshot de l'extraction)

Dépendances : pandas, openpyxl.
Usage :
    python build_dataset.py
    python build_dataset.py --wid data/WID_data_FR.csv --millesime-wid "WID 2024"
    python build_dataset.py --annee-min 2000 --no-append   # réécrit à neuf
"""

from __future__ import annotations

import argparse
import datetime as dt
import os
import sys
from pathlib import Path

import pandas as pd

try:
    import netfetch
except ImportError:
    netfetch = None  # type: ignore[assignment]  # téléchargement réseau indisponible

# ---------------------------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------------------------

DEFAULT_WID_PATH = Path("data/WID_data_FR.csv")
DEFAULT_FISCAL_PATH = Path("data/dgfip_isf_ifi.csv")
OUTPUT_STEM = "dataset_concentration_patrimoine_fr"
BASE_DEFLATION = 2021

# Schéma "tidy" cible : chaque ligne = UNE observation, horodatée.
SCHEMA = [
    "annee",  # année de la donnée (int)
    "source",  # WID | INSEE | DGFiP
    "concept_patrimoine",  # net | brut | immobilier (IFI) | total (ISF)
    "unite",  # adulte | menage | foyer_fiscal
    "groupe",  # ensemble | top10 | top1 | bottom50 | redevables | ...
    "indicateur",  # part_patrimoine | gini | patrimoine_moyen | nb_foyers | impot_moyen
    "valeur",  # float
    "unite_valeur",  # % | indice | euros | euros_constants_<base> | effectif
    "euros_constants",  # bool
    "date_extraction",  # AAAA-MM-JJ : quand la donnée a été tirée  [HISTORISATION]
    "millesime_source",  # version du fichier source                 [HISTORISATION]
    "notes",
]
HIST_KEYS = ["annee", "source", "concept_patrimoine", "unite", "groupe", "indicateur"]

# --- WID -------------------------------------------------------------------
WID_VARS = {
    "shweal992j": "part_patrimoine",
    "ghweal992j": "gini",
    "ahweal992j": "patrimoine_moyen",
    "thweal992j": "seuil",
}
WID_PERC = {
    "p90p100": "top10",
    "p99p100": "top1",
    "p99.9p100": "top0_1",
    "p0p50": "bottom50",
    "p50p90": "middle40",
    "p0p100": "ensemble",
}

# --- INSEE -----------------------------------------------------------------
# (annee, groupe, indicateur, valeur, unite_valeur, note)
# Hand-aligned curated data tables below; keep one row per line.
# fmt: off
INSEE_POINTS = [
    (1998, "ensemble", "gini",            0.639, "indice", "Insee, enquete Patrimoine 1997-98"),
    (2021, "ensemble", "gini",            0.662, "indice", "Insee, HVP 2020-21"),
    (2021, "top50",    "part_patrimoine", 92.0,  "%",      "Insee, HVP 2020-21"),
]

# --- DGFiP ISF/IFI : points officiels pré-remplis --------------------------
# (annee, concept, groupe, indicateur, valeur, unite_valeur, note)
# concept : "total" jusqu'en 2017 (ISF, tout le patrimoine),
#           "immobilier" à partir de 2018 (IFI, immobilier seulement).
# Source : DGFiP Statistiques (impots.gouv.fr). Complétez/actualisez librement.
DGFIP_POINTS = [
    # --- IFI (depuis 2018, immobilier net) ---
    (2018, "immobilier", "redevables",         "nb_foyers",   132722, "effectif", "DGFiP IFI 2018"),
    (2021, "immobilier", "redevables",         "nb_foyers",   150966, "effectif", "DGFiP IFI 2021"),
    (2022, "immobilier", "redevables",         "nb_foyers",   164000, "effectif", "DGFiP IFI 2022 (~164 k foyers, 1,8 Md€)"),
    (2023, "immobilier", "redevables",         "nb_foyers",   176000, "effectif", "DGFiP IFI 2023 (~176 k foyers, 1,9 Md€)"),
    (2024, "immobilier", "redevables",         "nb_foyers",   186000, "effectif", "DGFiP IFI 2024 (~186 k foyers, 2,2 Md€)"),
    # impôt moyen pour les très hauts patrimoines (>10 M€) en 2024
    (2024, "immobilier", "patrimoine_sup_10M", "impot_moyen", 169000, "euros",    "DGFiP IFI 2024 : IFI moyen des foyers >10 M€"),
    # --- ISF (jusqu'en 2017, patrimoine total) — à compléter depuis archives DGFiP ---
    # (2017, "total", "redevables", "nb_foyers", 358000, "effectif", "DGFiP ISF 2017"),
]
# fmt: on

# --- Déflateur IPC INSEE, base 2015 = 100 (à actualiser) -------------------
CPI_2015_100 = {
    2000: 81.0,
    2003: 85.0,
    2006: 89.0,
    2009: 92.0,
    2012: 96.5,
    2015: 100.0,
    2018: 103.5,
    2021: 107.0,
    2022: 113.0,
    2023: 119.0,
    2024: 121.5,
}


# ---------------------------------------------------------------------------
# CHARGEMENT DES SOURCES
# ---------------------------------------------------------------------------


def _stamp(rows: list[dict], extraction_date: str, millesime: str) -> list[dict]:
    """Ajoute les champs d'historisation à chaque ligne."""
    for r in rows:
        r.setdefault("date_extraction", extraction_date)
        r.setdefault("millesime_source", millesime)
    return rows


def _wid_rows_to_tidy(rows, extraction_date, millesime):
    """Convertit les lignes brutes de l'API WID (netfetch.fetch_wid) en tidy."""
    out = []
    for r in rows:
        ind, val = r["indicateur"], r["value"]
        if ind == "part_patrimoine":
            val, uv = val * 100.0, "%"
        elif ind == "gini":
            uv = "indice"
        else:
            uv = "euros"
        out.append(
            {
                "annee": r["year"],
                "source": "WID",
                "concept_patrimoine": "net",
                "unite": "adulte",
                "groupe": r["groupe"],
                "indicateur": ind,
                "valeur": round(val, 4),
                "unite_valeur": uv,
                "euros_constants": False,
                "notes": f"WID API {r['code']}",
            }
        )
    df = pd.DataFrame(_stamp(out, extraction_date, millesime))
    print(f"[WID] {len(df)} observations téléchargées via API ({millesime}).")
    return df


def load_wid(path: Path, extraction_date: str, millesime: str) -> pd.DataFrame:
    if not path.exists():
        print(
            f"[WID] Fichier introuvable : {path} -> source ignorée "
            "(téléchargez-le sur https://wid.world)."
        )
        return pd.DataFrame(columns=SCHEMA)

    sample = path.read_text(encoding="utf-8", errors="replace")[:2000]
    sep = ";" if sample.count(";") >= sample.count(",") else ","
    raw = pd.read_csv(path, sep=sep, dtype=str, encoding="utf-8")
    raw.columns = [c.strip().lower() for c in raw.columns]
    needed = {"variable", "percentile", "year", "value"}
    if not needed.issubset(raw.columns):
        raise ValueError(f"[WID] Colonnes inattendues : {list(raw.columns)}")

    raw = raw[raw["variable"].isin(WID_VARS) & raw["percentile"].isin(WID_PERC)]
    rows = []
    for _, r in raw.iterrows():
        try:
            year, value = int(float(r["year"])), float(r["value"])
        except (ValueError, TypeError):
            continue
        ind = WID_VARS[r["variable"]]
        if ind == "part_patrimoine":
            value, uv = value * 100.0, "%"
        elif ind == "gini":
            uv = "indice"
        else:
            uv = "euros"
        rows.append(
            {
                "annee": year,
                "source": "WID",
                "concept_patrimoine": "net",
                "unite": "adulte",
                "groupe": WID_PERC[r["percentile"]],
                "indicateur": ind,
                "valeur": round(value, 4),
                "unite_valeur": uv,
                "euros_constants": False,
                "notes": f"WID {r['variable']} {r['percentile']}",
            }
        )
    df = pd.DataFrame(_stamp(rows, extraction_date, millesime))
    print(f"[WID] {len(df)} observations chargées ({millesime}).")
    return df


def load_insee(extraction_date: str, millesime: str) -> pd.DataFrame:
    rows = [
        {
            "annee": a,
            "source": "INSEE",
            "concept_patrimoine": "brut",
            "unite": "menage",
            "groupe": g,
            "indicateur": ind,
            "valeur": v,
            "unite_valeur": uv,
            "euros_constants": False,
            "notes": note,
        }
        for (a, g, ind, v, uv, note) in INSEE_POINTS
    ]
    df = pd.DataFrame(_stamp(rows, extraction_date, millesime))
    print(f"[INSEE] {len(df)} observations chargées ({millesime}).")
    return df


def load_dgfip(path: Path, extraction_date: str, millesime: str) -> pd.DataFrame:
    """Charge les données fiscales ISF/IFI.

    Si un CSV externe est fourni (data/dgfip_isf_ifi.csv), il prime ; sinon on
    utilise les points pré-remplis DGFIP_POINTS. Format CSV attendu :
        annee,concept,groupe,indicateur,valeur,unite_valeur,note
    """
    points: list[tuple] = DGFIP_POINTS
    if path.exists():
        ext = pd.read_csv(path, dtype=str)
        ext.columns = [c.strip().lower() for c in ext.columns]
        points = [
            (
                int(r["annee"]),
                r["concept"],
                r["groupe"],
                r["indicateur"],
                float(r["valeur"]),
                r["unite_valeur"],
                r.get("note", ""),
            )
            for _, r in ext.iterrows()
        ]
        print(f"[DGFiP] CSV externe lu : {path}")

    rows = [
        {
            "annee": a,
            "source": "DGFiP",
            "concept_patrimoine": concept,
            "unite": "foyer_fiscal",
            "groupe": g,
            "indicateur": ind,
            "valeur": v,
            "unite_valeur": uv,
            "euros_constants": False,
            "notes": (note + (" | RUPTURE ISF->IFI 2018" if a == 2018 else "")),
        }
        for (a, concept, g, ind, v, uv, note) in points
    ]
    df = pd.DataFrame(_stamp(rows, extraction_date, millesime))
    print(
        f"[DGFiP] {len(df)} observations chargées ({millesime}). "
        "Rappel : rupture de série ISF(total)->IFI(immobilier) en 2018."
    )
    return df


# ---------------------------------------------------------------------------
# TRAITEMENTS
# ---------------------------------------------------------------------------


def deflate_levels(df: pd.DataFrame, base_year: int) -> pd.DataFrame:
    if base_year not in CPI_2015_100:
        print(f"[deflate] Base {base_year} absente de l'IPC -> ignoré.")
        return df
    base = CPI_2015_100[base_year]
    levels = df[df["unite_valeur"] == "euros"].copy()
    out = []
    for _, r in levels.iterrows():
        cpi = CPI_2015_100.get(int(r["annee"]))
        if cpi is None:
            continue
        r2 = r.copy()
        r2["valeur"] = round(r["valeur"] * base / cpi, 2)
        r2["unite_valeur"] = f"euros_constants_{base_year}"
        r2["euros_constants"] = True
        r2["notes"] = f"{r['notes']} | deflate IPC base {base_year}"
        out.append(r2)
    if out:
        df = pd.concat([df, pd.DataFrame(out)], ignore_index=True)
        print(f"[deflate] {len(out)} niveaux convertis en euros {base_year}.")
    return df


def harmonize(*frames, annee_min: int) -> pd.DataFrame:
    df = pd.concat([f for f in frames if not f.empty], ignore_index=True)
    df = df[df["annee"] >= annee_min]
    for col in SCHEMA:
        if col not in df.columns:
            df[col] = pd.NA
    return (
        df[SCHEMA].sort_values(["indicateur", "source", "groupe", "annee"]).reset_index(drop=True)
    )


# ---------------------------------------------------------------------------
# SORTIE (append horodaté + détection de révisions)
# ---------------------------------------------------------------------------


def write_outputs(df: pd.DataFrame, stem: str, append: bool) -> None:
    csv_path = Path(f"{stem}.csv")

    if append and csv_path.exists():
        prev = pd.read_csv(csv_path)
        # Détection des révisions : même clé (annee+source+...) mais valeur
        # différente dans une extraction antérieure.
        merged = df.merge(prev, on=HIST_KEYS, suffixes=("", "_prev"))
        revised = merged[
            (merged["valeur"] != merged["valeur_prev"])
            & (merged["millesime_source"] != merged["millesime_source_prev"])
        ]
        if len(revised):
            print(
                f"[revision] {len(revised)} valeur(s) révisée(s) depuis une "
                "extraction antérieure (conservées toutes deux dans l'historique)."
            )
            for _, r in revised.head(10).iterrows():
                print(
                    f"   - {r['annee']} {r['source']} {r['groupe']} "
                    f"{r['indicateur']}: {r['valeur_prev']} ({r['millesime_source_prev']}) "
                    f"-> {r['valeur']} ({r['millesime_source']})"
                )
        combined = pd.concat([prev, df], ignore_index=True)
        # Dédoublonnage : une même observation au même millésime ET même date
        # d'extraction n'est pas dupliquée si on relance le script.
        combined = combined.drop_duplicates(
            subset=HIST_KEYS + ["valeur", "millesime_source", "date_extraction"]
        )
    else:
        combined = df

    combined.to_csv(csv_path, index=False, encoding="utf-8")
    print(f"[out] CSV cumulatif : {csv_path}  ({len(combined)} lignes au total)")

    # Snapshot Excel daté de CETTE extraction (data + sources + dico).
    ts = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    xlsx_path = Path(f"{stem}_{ts}.xlsx")
    sources = pd.DataFrame(
        [
            {
                "source": "WID",
                "url": "https://wid.world",
                "convention": "adulte / patrimoine net",
                "concept": "net",
                "remarque": "Corrige le sommet (fiscal + compta nationale).",
            },
            {
                "source": "INSEE",
                "url": "https://www.insee.fr",
                "convention": "menage / patrimoine brut",
                "concept": "brut",
                "remarque": "Enquetes Patrimoine puis HVP.",
            },
            {
                "source": "DGFiP",
                "url": "https://www.impots.gouv.fr",
                "convention": "foyer fiscal",
                "concept": "total (ISF<=2017) / immobilier (IFI>=2018)",
                "remarque": "RUPTURE DE SERIE 2018 : ISF (tout patrimoine) -> IFI (immobilier seul).",
            },
        ]
    )
    dico = pd.DataFrame(
        [
            {"colonne": c, "description": d}
            for c, d in {
                "annee": "Année de l'observation",
                "source": "Producteur (WID, INSEE, DGFiP)",
                "concept_patrimoine": "net | brut | total (ISF) | immobilier (IFI)",
                "unite": "adulte | menage | foyer_fiscal (NON comparables directement)",
                "groupe": "ensemble, top10/top1, bottom50, redevables, ...",
                "indicateur": "part_patrimoine, gini, patrimoine_moyen, nb_foyers, impot_moyen",
                "valeur": "Valeur numérique",
                "unite_valeur": "% | indice | euros | euros_constants_<base> | effectif",
                "euros_constants": "True si valeur déflatée",
                "date_extraction": "[HISTO] date du tirage de la donnée",
                "millesime_source": "[HISTO] version du fichier source",
                "notes": "Variable source, traitement, ruptures.",
            }.items()
        ]
    )
    with pd.ExcelWriter(xlsx_path, engine="openpyxl") as xl:
        df.to_excel(xl, sheet_name="data", index=False)
        sources.to_excel(xl, sheet_name="sources", index=False)
        dico.to_excel(xl, sheet_name="dictionnaire", index=False)
    print(f"[out] Snapshot Excel : {xlsx_path}")


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Construit le dataset patrimoine FR (historisé).")
    p.add_argument("--wid", type=Path, default=DEFAULT_WID_PATH)
    p.add_argument("--fiscal", type=Path, default=DEFAULT_FISCAL_PATH)
    p.add_argument("--annee-min", type=int, default=2000)
    p.add_argument("--base-deflation", type=int, default=BASE_DEFLATION)
    p.add_argument("--millesime-wid", default=f"WID {dt.date.today():%Y}")
    p.add_argument("--millesime-insee", default="INSEE HVP 2020-21")
    p.add_argument("--millesime-dgfip", default=f"DGFiP {dt.date.today():%Y}")
    p.add_argument(
        "--download", action="store_true", help="récupère WID (API) et/ou DGFiP (Excel) en ligne"
    )
    p.add_argument(
        "--full",
        action="store_true",
        help="WID : récupère TOUS les percentiles patrimoine FR (équiv. fichier complet)",
    )
    p.add_argument("--wid-api-key", default=os.environ.get("WID_API_KEY_B64", ""))
    p.add_argument("--dgfip-url", default=os.environ.get("DGFIP_IFI_XLS_URL", ""))
    p.add_argument(
        "--no-append",
        action="store_true",
        help="réécrit le CSV à neuf au lieu d'empiler l'historique",
    )
    args = p.parse_args(argv)

    today = dt.date.today().isoformat()

    # --- WID : API si --download + clef, sinon fichier local ---
    if args.download and netfetch is not None:
        try:
            key = args.wid_api_key or netfetch.WID_API_KEY_B64
            if args.full:
                raw = netfetch.fetch_wid_full(key, areas="FR")
            else:
                raw = netfetch.fetch_wid(key, areas="FR")
            wid = _wid_rows_to_tidy(raw, today, args.millesime_wid)
        except Exception as e:
            print(f"[WID] téléchargement échoué ({e}). Repli sur fichier local.")
            wid = load_wid(args.wid, today, args.millesime_wid)
    else:
        wid = load_wid(args.wid, today, args.millesime_wid)

    # --- DGFiP : télécharge l'Excel puis le loader le lira ---
    if args.download and netfetch is not None and args.dgfip_url:
        try:
            netfetch.download_file(args.dgfip_url, args.fiscal)
            print(f"[DGFiP] Excel téléchargé -> {args.fiscal}")
        except Exception as e:
            print(f"[DGFiP] téléchargement échoué ({e}). Points pré-remplis utilisés.")
    insee = load_insee(today, args.millesime_insee)
    dgfip = load_dgfip(args.fiscal, today, args.millesime_dgfip)

    df = harmonize(wid, insee, dgfip, annee_min=args.annee_min)
    df = deflate_levels(df, base_year=args.base_deflation)
    df = df.sort_values(["indicateur", "source", "groupe", "annee"]).reset_index(drop=True)

    if df.empty:
        print("\n[!] Dataset vide : fournissez au moins une source.", file=sys.stderr)
        return 1

    write_outputs(df, OUTPUT_STEM, append=not args.no_append)
    print("\n=== Apercu de l'extraction ===")
    print(df.groupby(["source", "indicateur"]).size().to_string())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
