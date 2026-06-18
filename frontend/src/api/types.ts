// Typed mirror of the API contract — keep in sync with `backend/app/models.py`.
// `unite` and `concept_patrimoine` are the Convention — keep them on every value.

export type Source = "WID" | "INSEE" | "DGFiP";
export type Unite = "adulte" | "menage" | "foyer_fiscal";
// INSEE spans four Conventions: the all-inclusive `brut`/`net` and the *hors reste*
// variants, which exclude INSEE's residual asset category and are a different
// quantity — never merged with the all-inclusive ones (CONTEXT.md "Reste / hors
// reste"). `total`/`immobilier` are DGFiP's ISF/IFI Concepts.
export type Concept =
  | "net"
  | "brut"
  | "brut_hors_reste"
  | "net_hors_reste"
  | "total"
  | "immobilier";
export type Indicateur =
  | "part_patrimoine"
  | "gini"
  | "patrimoine_moyen"
  | "seuil"
  | "nb_foyers"
  | "impot_moyen";

export interface Meta {
  sources: Source[];
  indicateurs: Indicateur[];
  groupes: string[];
  concepts: Concept[];
  unites: Unite[];
  millesimes: string[];
  /** Per-source `{indicateur: [groupes…]}`: what each source actually measures.
   *  The lists above are a union across sources; this map drives the filters so
   *  a source is only ever offered the figures it owns. */
  availability: Record<string, Record<string, string[]>>;
  /** Per `tranche_marginale_*` groupe, its IFI marginal rate as a number (e.g.
   *  `{ tranche_marginale_2: 0.7 }`). Lets the UI label a tranche by its rate
   *  ("Tranche à 0,7 %") rather than the opaque workbook ordinal. Presentation
   *  only — the `groupes`/`availability` lists are unchanged (#15). */
  tranche_taux: Record<string, number>;
  annee_min: number;
  annee_max: number;
}

export interface Point {
  annee: number;
  valeur: number;
}

export interface Rupture {
  annee: number;
  label: string;
}

export interface Series {
  query: Record<string, unknown>;
  unite: Unite;
  concept_patrimoine: Concept;
  unite_valeur: string;
  points: Point[];
  ruptures: Rupture[];
  millesime_source: string;
  date_extraction: string;
}

/** One Convention the caller may pin to resolve a `422` (ADR 0002). */
export interface ConventionChoice {
  unite: string;
  concept_patrimoine: Concept;
}

/** `422` body when filters still span more than one Convention. */
export interface AmbiguousConventionDetail {
  error: "ambiguous_convention";
  choices: ConventionChoice[];
}

export interface RevisionDiff {
  annee: number;
  source: Source;
  concept_patrimoine: Concept;
  unite: Unite;
  groupe: string;
  indicateur: Indicateur;
  valeurs: { millesime_source: string; valeur: number; date_extraction: string }[];
}

/** Provenance + reuse terms per Source (GET /api/sources; data in `data.py` `SOURCE_INFO`). */
export interface SourceInfo {
  source: Source;
  url: string;
  convention: string;
  licence: string;
  attribution: string;
}
