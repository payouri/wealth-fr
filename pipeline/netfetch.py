"""
netfetch.py — Couche réseau pour build_dataset.py
=================================================
Récupère automatiquement les données depuis les sources publiques.

WID  : API officielle (même endpoint que l'outil R officiel)
       GET {base}/countries-variables?countries=FR&variables=<codes>&years=all
       En-tête  x-api-key: base64(<clef>)
       Code variable complet = {sixlet}_{percentile}_{age}_{pop}
       ex. shweal_p99p100_992_j  (part de patrimoine net, top 1%, adultes, equal-split)
       La clef est fournie via --wid-api-key ou la variable d'env WID_API_KEY.
       (Le repli sur fichier local data/WID_data_FR.csv ne nécessite PAS de clef.)

DGFiP: téléchargement direct du fichier Excel publié (aucune clef requise).
"""

from __future__ import annotations

import os
import re
import time
from pathlib import Path

import requests

WID_API_BASE = "https://rfap9nitz6.execute-api.eu-west-1.amazonaws.com/prod/"
# Clé publique embarquée dans l'outil R officiel (sysdata.rda).
# = base64 des 30 octets bruts ; l'API attend DIRECTEMENT cette chaîne en x-api-key.
WID_API_KEY_PUBLIC = "rYFByOB0ioaPATwHtllMI71zLOZSK0Ic5veQonJP"
# `... or` (et non simple défaut de get) : une variable d'env PRÉSENTE MAIS VIDE
# — ce que produit le compose prod `WID_API_KEY_B64: ${WID_API_KEY_B64:-}` quand le
# secret Coolify n'est pas défini — ne doit pas écraser la clé publique embarquée.
# Sinon x-api-key part vide -> 403 Forbidden et la source WID est silencieusement perdue.
WID_API_KEY_B64 = os.environ.get("WID_API_KEY_B64", "") or WID_API_KEY_PUBLIC

# Sixlets patrimoine -> indicateur tidy
WID_SIXLETS = {
    "shweal": "part_patrimoine",
    "ahweal": "patrimoine_moyen",
    "thweal": "seuil",
    "ghweal": "gini",
}
WID_PERC_LABELS = {
    "p90p100": "top10",
    "p99p100": "top1",
    "p99.9p100": "top0_1",
    "p0p50": "bottom50",
    "p50p90": "middle40",
    "p0p100": "ensemble",
}

# Codes WID complets à récupérer : (code_api, groupe, indicateur)
WID_FETCH_CODES = [
    ("shweal_p90p100_992_j", "top10", "part_patrimoine"),
    ("shweal_p99p100_992_j", "top1", "part_patrimoine"),
    ("shweal_p99.9p100_992_j", "top0_1", "part_patrimoine"),
    ("shweal_p0p50_992_j", "bottom50", "part_patrimoine"),
    ("ghweal_p0p100_992_j", "ensemble", "gini"),
    ("ahweal_p99p100_992_j", "top1", "patrimoine_moyen"),
    ("ahweal_p0p100_992_j", "ensemble", "patrimoine_moyen"),
]

# DGFiP : page de réf. https://www.impots.gouv.fr/impot-sur-la-fortune-immobiliere-ifi
# Il n'existe PAS d'URL unique : l'IFI nationale est publiée en TROIS fichiers
# (même population, trois découpages) sous des liens `/node/<id>` stables qui
# redirigent vers le .xls du millésime courant. On télécharge le lot ; le parseur
# (`dgfip_parse`) reconnaît chaque découpage par sa structure.
DGFIP_SOURCE_URLS_DEFAULT = [
    "https://www.impots.gouv.fr/node/25582",  # IFI — déciles de patrimoine net taxable
    "https://www.impots.gouv.fr/node/25583",  # IFI — déciles de RFR des redevables
    "https://www.impots.gouv.fr/node/25584",  # IFI — tranches de taux marginal
]


def dgfip_source_urls() -> list[str]:
    """Registry of DGFiP source URLs, env-overridable.

    `DGFIP_SOURCE_URLS` (comma/whitespace-separated) replaces the default list;
    `DGFIP_IFI_XLS_URL` (legacy single URL) is appended if set, for back-compat.
    """
    raw = os.environ.get("DGFIP_SOURCE_URLS", "")
    urls = [u.strip() for u in re.split(r"[,\s]+", raw) if u.strip()] or list(
        DGFIP_SOURCE_URLS_DEFAULT
    )
    legacy = os.environ.get("DGFIP_IFI_XLS_URL", "").strip()
    if legacy and legacy not in urls:
        urls.append(legacy)
    return urls


def _dest_filename(url: str, resp: requests.Response, fallback_stem: str) -> str:
    """Filename for a downloaded source: Content-Disposition, else URL path.

    DGFiP `/node/<id>` URLs carry no filename in the path, so prefer the server's
    Content-Disposition; otherwise derive a stable name from the node id.
    """
    cd = resp.headers.get("content-disposition", "")
    if (m := re.search(r"filename\*?=(?:UTF-8'')?\"?([^\";]+)", cd)) is not None:
        name = m.group(1).strip()
        if name:
            return name
    tail = url.rstrip("/").split("/")[-1].split("?")[0]
    if tail and Path(tail).suffix.lower() in (".xls", ".xlsx", ".csv", ".zip"):
        return tail
    return f"{fallback_stem}.xls"


def download_sources(urls: list[str], dest_dir: Path, timeout=120) -> list[Path]:
    """Download every DGFiP source URL into `dest_dir`; return the written paths.

    Individual failures are reported and skipped (the loader falls back to the
    curated CSV / pre-filled points when nothing parses — HANDOFF §10).
    """
    dest_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for i, url in enumerate(urls):
        try:
            r = _http_get(url, timeout=timeout, stream=True)
            dest = dest_dir / _dest_filename(url, r, f"dgfip_source_{i}")
            with open(dest, "wb") as f:
                for chunk in r.iter_content(chunk_size=65536):
                    f.write(chunk)
            written.append(dest)
            print(f"[DGFiP] téléchargé : {url} -> {dest.name}")
        except Exception as e:  # noqa: BLE001 — on log et on continue
            print(f"[DGFiP] échec téléchargement {url} ({e}). Source ignorée.")
    return written


def _http_get(url, headers=None, timeout=30, retries=3, stream=False):
    """GET robuste : timeout + retries exponentiels."""
    last = None
    for attempt in range(retries):
        try:
            r = requests.get(url, headers=headers, timeout=timeout, stream=stream)
            r.raise_for_status()
            return r
        except requests.RequestException as e:
            last = e
            time.sleep(2**attempt)
    raise RuntimeError(f"échec GET après {retries} tentatives : {url}\n{last}")


def fetch_wid(api_key_b64: str = WID_API_KEY_B64, areas="FR", codes=WID_FETCH_CODES, timeout=60):
    """Appelle l'API WID et renvoie une liste de dicts bruts :
       {code, groupe, indicateur, year, value}.

    api_key_b64 : clé DÉJÀ encodée en base64 (cf. WID_API_KEY_B64). On ne la
    ré-encode pas : le serveur attend cette chaîne telle quelle dans x-api-key.
    """
    api_key_b64 = api_key_b64 or WID_API_KEY_B64  # clé vide -> repli sur la clé publique
    if not api_key_b64:
        raise ValueError(
            "Clef API WID absente. Fournissez --wid-api-key / WID_API_KEY_B64, "
            "ou utilisez le repli fichier local (data/WID_data_FR.csv)."
        )
    headers = {"x-api-key": api_key_b64}
    var_q = ",".join(c[0] for c in codes)
    url = f"{WID_API_BASE}countries-variables?countries={areas}&variables={var_q}&years=all"
    resp = _http_get(url, headers=headers, timeout=timeout)
    payload = resp.json()

    # Gestion du gros payload (route alternative documentée par l'API).
    if isinstance(payload, dict) and payload.get("status") == "payload_too_large":
        dl = payload.get("download_url")
        if not dl:
            raise RuntimeError("payload_too_large sans download_url.")
        payload = _http_get(dl, timeout=timeout).json()

    meta = {c[0]: (c[1], c[2]) for c in codes}
    rows = []
    # Réponse : { code: [ { pays: { "values":[[year,value],...], "meta":{...} } } ] }
    for code, per_var in (payload or {}).items():
        groupe, indicateur = meta.get(code, (None, None))
        if groupe is None:
            continue
        entries = per_var if isinstance(per_var, list) else [per_var]
        for entry in entries:
            for _, cdata in (entry or {}).items():
                for yv in (cdata or {}).get("values", []):
                    try:
                        # L'API renvoie {"y": year, "v": value} ; on tolère aussi
                        # l'ancien format [year, value] (réponses simulées).
                        if isinstance(yv, dict):
                            year, value = int(yv["y"]), float(yv["v"])
                        else:
                            year, value = int(yv[0]), float(yv[1])
                        rows.append(
                            {
                                "code": code,
                                "groupe": groupe,
                                "indicateur": indicateur,
                                "year": year,
                                "value": value,
                            }
                        )
                    except (TypeError, ValueError, IndexError, KeyError):
                        continue
    return rows


def download_file(url: str, dest: Path, timeout=120) -> Path:
    """Télécharge un fichier (ex. Excel DGFiP) — aucune clef requise."""
    if not url:
        raise ValueError("URL de téléchargement vide.")
    dest.parent.mkdir(parents=True, exist_ok=True)
    r = _http_get(url, timeout=timeout, stream=True)
    with open(dest, "wb") as f:
        for chunk in r.iter_content(chunk_size=65536):
            f.write(chunk)
    return dest


def fetch_wid_available(
    api_key_b64=WID_API_KEY_B64,
    areas="FR",
    sixlets=tuple(WID_SIXLETS),
    age="992",
    pop="j",
    timeout=60,
):
    """Découvre, via l'API, les (percentile, age, pop) disponibles pour chaque
    sixlet patrimoine en France. Renvoie la liste des codes complets
    {sixlet}_{percentile}_{age}_{pop} filtrés sur age/pop standard.
    """
    api_key_b64 = api_key_b64 or WID_API_KEY_B64  # clé vide -> repli sur la clé publique
    var_q = ",".join(sixlets)
    url = f"{WID_API_BASE}countries-available-variables?countries={areas}&variables={var_q}"
    payload = _http_get(url, headers={"x-api-key": api_key_b64}, timeout=timeout).json()
    # L'API renvoie une LISTE de dicts (un par variable demandée) ; on les fusionne.
    if isinstance(payload, list):
        merged: dict = {}
        for item in payload:
            if isinstance(item, dict):
                merged.update(item)
        payload = merged

    codes = []
    for variable, per_country in (payload or {}).items():
        sixlet = variable[:6]
        if sixlet not in WID_SIXLETS:
            continue
        for _, combos in (per_country or {}).items():
            for combo in combos or []:
                try:
                    perc, a, p = combo[0], str(combo[1]), str(combo[2])
                except (TypeError, IndexError):
                    continue
                if a != age or p != pop:  # on garde la convention adulte/equal-split
                    continue
                full = f"{sixlet}_{perc}_{a}_{p}"
                groupe = WID_PERC_LABELS.get(perc, perc)  # libellé connu sinon percentile brut
                codes.append((full, groupe, WID_SIXLETS[sixlet]))
    # dédoublonnage en préservant l'ordre
    seen, uniq = set(), []
    for c in codes:
        if c[0] not in seen:
            seen.add(c[0])
            uniq.append(c)
    return uniq


def fetch_wid_full(api_key_b64=WID_API_KEY_B64, areas="FR", timeout=120):
    """Équivalent 'fichier complet' côté API : récupère TOUS les percentiles
    patrimoine disponibles pour la France (parts, moyennes, seuils, Gini),
    convention adulte / equal-split.
    """
    codes = fetch_wid_available(api_key_b64, areas=areas, timeout=timeout)
    if not codes:
        raise RuntimeError("Aucune variable patrimoine découverte pour " + areas)
    # On découpe en lots pour éviter des URL trop longues.
    rows = []
    BATCH = 40
    for i in range(0, len(codes), BATCH):
        rows += fetch_wid(api_key_b64, areas=areas, codes=codes[i : i + BATCH], timeout=timeout)
    return rows
