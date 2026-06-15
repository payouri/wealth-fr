import type { ConventionChoice, Meta } from "@/api/types";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import type { DashboardParams } from "@/hooks/useDashboardParams";
import {
  CONCEPT_LABEL,
  groupeLabel,
  indicateurMeta,
  SHARE_GROUPES,
  SOURCE_CONVENTION,
  SOURCE_LABEL,
  UNITE_LABEL,
  validComboForSource,
} from "@/lib/domain";

interface FilterBarProps {
  meta: Meta;
  params: DashboardParams;
  update: (patch: Partial<DashboardParams>) => void;
  /** Convention options discovered for the current source (from a 422), if any. */
  conceptChoices: ConventionChoice[] | null;
  /** Convention echoed by the resolved primary series (traceability readout). */
  resolved: { unite?: string; concept?: string } | null;
  /** Euros toggle is inert unless the current indicateur is a level. */
  eurosInert: boolean;
}

function Field({
  label,
  htmlFor,
  children,
}: {
  label: string;
  htmlFor?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <span id={htmlFor} className="text-label font-medium text-muted-foreground">
        {label}
      </span>
      {children}
    </div>
  );
}

export default function FilterBar({
  meta,
  params,
  update,
  conceptChoices,
  resolved,
  eurosInert,
}: FilterBarProps) {
  const meta_ind = indicateurMeta(params.indicateur);
  const isShare = meta_ind.isShare;
  // What the selected source actually measures — the filters offer only these, so
  // the reader can never ask a source for a figure it never measured.
  const byIndicateur = meta.availability?.[params.source] ?? {};
  const sourceIndicateurs = Object.keys(byIndicateur);
  const sourceGroupes = byIndicateur[params.indicateur] ?? [];
  const shareFocus = SHARE_GROUPES.filter((g) => sourceGroupes.includes(g));
  const uniteText = resolved?.unite
    ? (UNITE_LABEL[resolved.unite] ?? resolved.unite)
    : "dérivée de la source";
  const conceptText = params.concept
    ? (CONCEPT_LABEL[params.concept] ?? params.concept)
    : resolved?.concept
      ? (CONCEPT_LABEL[resolved.concept] ?? resolved.concept)
      : null;

  return (
    <section
      aria-label="Filtres"
      className="rounded-lg border border-border bg-secondary px-4 py-4 sm:px-5"
    >
      <div className="grid gap-x-8 gap-y-5 sm:grid-cols-2 lg:grid-cols-[auto_1fr_auto]">
        {/* Source — first-level Convention selector */}
        <Field label="Source" htmlFor="f-source">
          <ToggleGroup
            type="single"
            value={params.source}
            onValueChange={(v) =>
              v &&
              update({
                source: v,
                ...validComboForSource(meta.availability, v, params.indicateur, params.groupe),
              })
            }
            aria-labelledby="f-source"
          >
            {meta.sources.map((s) => (
              <ToggleGroupItem
                key={s}
                value={s}
                className="flex-col items-start gap-0 py-1.5 text-left pointer-coarse:min-h-11"
              >
                <span className="text-sm leading-tight font-semibold">{SOURCE_LABEL[s] ?? s}</span>
                <span className="text-label leading-tight font-normal text-muted-foreground">
                  {SOURCE_CONVENTION[s] ?? ""}
                </span>
              </ToggleGroupItem>
            ))}
          </ToggleGroup>
        </Field>

        {/* Indicateur + groupe */}
        <div className="flex flex-wrap items-start gap-x-8 gap-y-5">
          <Field label="Indicateur" htmlFor="f-indicateur">
            <Select
              value={params.indicateur}
              onValueChange={(v) =>
                update(
                  // Snap the groupe to one this (source, indicateur) measures —
                  // a share indicateur overlays all fractions ("" = no focus).
                  validComboForSource(meta.availability, params.source, v, params.groupe),
                )
              }
            >
              <SelectTrigger className="w-52" aria-labelledby="f-indicateur">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {sourceIndicateurs.map((ind) => (
                  <SelectItem key={ind} value={ind}>
                    {indicateurMeta(ind).label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </Field>

          {isShare ? (
            <Field label="Focus" htmlFor="f-focus">
              <ToggleGroup
                type="single"
                value={params.groupe}
                onValueChange={(v) => update({ groupe: v ?? "" })}
                aria-labelledby="f-focus"
              >
                <ToggleGroupItem value="" aria-label="Toutes les parts">
                  Tout
                </ToggleGroupItem>
                {shareFocus.map((g) => (
                  <ToggleGroupItem key={g} value={g}>
                    {groupeLabel(g)}
                  </ToggleGroupItem>
                ))}
              </ToggleGroup>
            </Field>
          ) : (
            <Field label="Groupe" htmlFor="f-groupe">
              <Select
                value={params.groupe || sourceGroupes[0]}
                onValueChange={(v) => update({ groupe: v })}
              >
                <SelectTrigger className="w-48" aria-labelledby="f-groupe">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {sourceGroupes.map((g) => (
                    <SelectItem key={g} value={g}>
                      {groupeLabel(g)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </Field>
          )}

          {/* Convention: a switcher when the source spans several, else a readout */}
          {conceptChoices && conceptChoices.length > 1 ? (
            <Field label="Convention" htmlFor="f-concept">
              <Select value={params.concept} onValueChange={(v) => update({ concept: v })}>
                <SelectTrigger className="w-44" aria-labelledby="f-concept">
                  <SelectValue placeholder="à choisir" />
                </SelectTrigger>
                <SelectContent>
                  {conceptChoices.map((c) => (
                    <SelectItem key={c.concept_patrimoine} value={c.concept_patrimoine}>
                      {CONCEPT_LABEL[c.concept_patrimoine] ?? c.concept_patrimoine}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </Field>
          ) : (
            <Field label="Convention">
              <p className="flex h-9 items-center text-sm text-foreground">
                <span className="font-medium">{uniteText}</span>
                {conceptText && (
                  <>
                    <span className="px-1.5 text-muted-foreground">·</span>
                    <span className="font-medium">{conceptText}</span>
                  </>
                )}
              </p>
            </Field>
          )}
        </div>

        {/* Euros constants — present, inert on shares/Gini */}
        <Field label="Euros constants">
          <div
            className="flex h-9 items-center gap-2.5 text-sm text-foreground data-[inert=true]:text-muted-foreground"
            data-inert={eurosInert}
          >
            <Switch
              checked={params.euros && !eurosInert}
              disabled={eurosInert}
              onCheckedChange={(c) => update({ euros: c })}
              aria-label="Afficher en euros constants"
            />
            <span>{eurosInert ? "sans objet ici" : params.euros ? "constants" : "nominaux"}</span>
          </div>
          {eurosInert && (
            <span className="text-label text-muted-foreground">
              déflation sur les niveaux (€) uniquement
            </span>
          )}
        </Field>
      </div>
    </section>
  );
}
