// Typed mirror of the API contract (HANDOFF.md §6.4) and tidy schema (§3).
// `unite` and `concept_patrimoine` are the Convention — keep them on every value.

export type Source = "WID" | "INSEE" | "DGFiP";
export type Unite = "adulte" | "menage" | "foyer_fiscal";
export type Concept = "net" | "brut" | "total" | "immobilier";
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
