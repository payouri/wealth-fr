// Révisions diff table (jalon 6): Observations a Source revised across millésimes.
// Both vintages are shown side by side with their extraction dates — the
// append-only historisation made visible, never an overwrite (Principle 3).
import { ArrowRight } from "lucide-react";
import type { Meta, RevisionDiff } from "@/api/types";
import { conventionLabel, groupeLabel, indicateurMeta } from "@/lib/domain";
import { revisionDelta } from "@/lib/revisions";

const tnum = { fontFeatureSettings: '"tnum" 1' } as const;

function fmt(value: number): string {
  return new Intl.NumberFormat("fr-FR", { maximumFractionDigits: 3 }).format(value);
}

function fmtDate(iso: string): string {
  if (!iso) return "";
  const d = new Date(iso);
  return Number.isNaN(d.getTime())
    ? iso
    : d.toLocaleDateString("fr-FR", { day: "2-digit", month: "short", year: "numeric" });
}

export default function RevisionsTable({
  revisions,
  meta,
}: {
  revisions: RevisionDiff[];
  /** Carries `tranche_taux` so a revised tranche reads by its rate (issue #15). */
  meta?: Meta;
}) {
  if (revisions.length === 0) {
    return (
      <p className="rounded-md border border-border bg-secondary px-4 py-3 text-sm text-muted-foreground">
        Aucune révision détectée pour le moment : chaque observation n'existe que dans un seul
        millésime. Dès qu'une source recalcule une valeur passée, les deux millésimes apparaîtront
        ici, côte à côte.
      </p>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse text-sm" style={tnum}>
        <caption className="sr-only">
          Observations révisées : valeur d'un millésime à l'autre, dates d'extraction comprises.
        </caption>
        <thead>
          <tr className="border-b border-border text-left text-label text-muted-foreground">
            <th scope="col" className="py-2 pr-4 font-medium">
              Observation
            </th>
            <th scope="col" className="py-2 pr-4 font-medium">
              Millésime initial
            </th>
            <th scope="col" className="py-2 pr-4 font-medium">
              Millésime révisé
            </th>
            <th scope="col" className="py-2 pr-2 text-right font-medium">
              Écart
            </th>
          </tr>
        </thead>
        <tbody>
          {revisions.map((rev) => {
            const diff = revisionDelta(rev);
            if (!diff) return null;
            const sign = diff.delta > 0 ? "+" : "";
            return (
              <tr
                key={`${rev.annee}-${rev.source}-${rev.indicateur}-${rev.groupe}`}
                className="border-b border-border/70 align-top"
              >
                <td className="py-3 pr-4">
                  <p className="font-medium text-foreground">
                    {rev.annee} · {indicateurMeta(rev.indicateur).label}
                  </p>
                  <p className="text-label text-muted-foreground">
                    {conventionLabel(rev.source, rev.unite, rev.concept_patrimoine)} ·{" "}
                    {groupeLabel(rev.groupe, meta)}
                  </p>
                </td>
                <td className="py-3 pr-4">
                  <p className="font-semibold text-foreground">{fmt(diff.from.valeur)}</p>
                  <p className="text-label text-muted-foreground">
                    {diff.from.millesime_source} · {fmtDate(diff.from.date_extraction)}
                  </p>
                </td>
                <td className="py-3 pr-4">
                  <p className="font-semibold text-foreground">{fmt(diff.to.valeur)}</p>
                  <p className="text-label text-muted-foreground">
                    {diff.to.millesime_source} · {fmtDate(diff.to.date_extraction)}
                  </p>
                </td>
                <td className="py-3 pr-2 text-right">
                  <span className="inline-flex items-center gap-1 font-medium text-foreground">
                    <ArrowRight className="size-3.5 text-muted-foreground" aria-hidden />
                    {sign}
                    {fmt(diff.delta)}
                  </span>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
