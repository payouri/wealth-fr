// Comparison (jalon 5, ADR 0003): overlay WID / INSEE / DGFiP for one
// dimensionless indicateur + groupe. Each line keeps its own Convention (colour,
// dash, legend) — Sources are compared, never merged. Euro levels are excluded:
// the indicateur picker only offers dimensionless quantities.
import { useQuery } from "@tanstack/react-query";
import { Info } from "lucide-react";
import { lazy, Suspense, useEffect, useRef } from "react";
import { ApiError, api } from "@/api/client";
import ConventionLegend from "@/components/ConventionLegend";
import ExportButtons from "@/components/ExportButtons";
import {
  EmptyState,
  ErrorState,
  FigureFrame,
  FigureSkeleton,
  StateNotice,
} from "@/components/figure";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import { useComparisonParams } from "@/hooks/useComparisonParams";
import { buildComparisonLines } from "@/lib/comparison";
import {
  COMPARABLE_INDICATEURS,
  groupeLabel,
  indicateurMeta,
  SOURCE_CONVENTION,
  SOURCE_LABEL,
} from "@/lib/domain";
import { exportStem } from "@/lib/exportChart";

const SeriesChart = lazy(() => import("@/components/SeriesChart"));

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

export default function Comparison() {
  const [params, update] = useComparisonParams();
  const chartRef = useRef<HTMLDivElement>(null);

  const metaQ = useQuery({
    queryKey: ["meta"],
    queryFn: api.meta,
    staleTime: Number.POSITIVE_INFINITY,
  });
  const meta = metaQ.data;

  const isGini = params.indicateur === "gini";
  // Gini is a single whole-distribution index; shares are by fraction.
  const groupeOptions = isGini ? ["ensemble"] : (meta?.groupes ?? []);
  const activeGroupe = isGini ? "ensemble" : params.groupe;

  // Switching to Gini forces the only meaningful groupe, so the URL never holds a
  // groupe that can't exist for the indicateur.
  useEffect(() => {
    if (isGini && params.groupe !== "ensemble") update({ groupe: "ensemble" });
  }, [isGini, params.groupe, update]);

  const compareQ = useQuery({
    queryKey: ["compare", params.indicateur, activeGroupe, params.sources.join(",")],
    queryFn: () =>
      api.compare({
        indicateur: params.indicateur,
        groupe: activeGroupe,
        sources: params.sources,
      }),
    enabled: !!meta && params.sources.length > 0,
  });

  const anneeMin = meta?.annee_min ?? 2000;
  const anneeMax = meta?.annee_max ?? 2024;

  const lines = compareQ.data ? buildComparisonLines(compareQ.data) : [];
  const drawn = lines.filter((l) => l.hasData);
  const representative = compareQ.data?.find((s) => s.points.length > 0);
  // Merge ruptures across the overlaid series (e.g. DGFiP's 2018 break), deduped —
  // but only from sources actually drawn, so a marker never dangles over a source
  // that has no line on this chart.
  const ruptures = [
    ...new Map(
      (compareQ.data ?? [])
        .filter((s) => s.points.length > 0)
        .flatMap((s) => s.ruptures)
        .map((r) => [`${r.annee}-${r.label}`, r]),
    ).values(),
  ];

  const ambiguous = Boolean(
    compareQ.error instanceof ApiError && compareQ.error.ambiguousConvention,
  );
  const hardError = compareQ.isError && !ambiguous;
  const stem = exportStem(["comparaison", params.indicateur, activeGroupe]);

  let body: React.ReactNode;
  if (!meta || compareQ.isPending) {
    body = <FigureSkeleton height={360} />;
  } else if (params.sources.length === 0) {
    body = (
      <StateNotice tone="info" title="Choisissez au moins une source à comparer" height={360}>
        Activez WID, INSEE ou DGFiP ci-dessus pour superposer leurs séries.
      </StateNotice>
    );
  } else if (ambiguous) {
    body = (
      <StateNotice tone="info" title="Convention ambiguë" height={360}>
        Une des sources couvre plusieurs Conventions sur cette période. Affinez le groupe ou
        l'indicateur pour comparer des séries comparables.
      </StateNotice>
    );
  } else if (hardError) {
    body = <ErrorState onRetry={() => compareQ.refetch()} height={360} />;
  } else if (drawn.length === 0) {
    body = <EmptyState height={360} />;
  } else {
    body = (
      <div ref={chartRef}>
        <Suspense fallback={<FigureSkeleton height={360} />}>
          <SeriesChart
            series={drawn}
            ruptures={ruptures}
            uniteValeur={representative?.unite_valeur ?? ""}
            axisLabel={isGini ? "indice (0–1)" : "% du patrimoine"}
            anneeMin={anneeMin}
            anneeMax={anneeMax}
            height={360}
          />
        </Suspense>
      </div>
    );
  }

  if (metaQ.isError) {
    return (
      <FigureFrame title="Comparaison de sources">
        <ErrorState onRetry={() => metaQ.refetch()} />
      </FigureFrame>
    );
  }

  return (
    <div className="space-y-6">
      <header className="max-w-prose space-y-2">
        <h1 className="font-serif text-headline font-semibold text-foreground">
          Comparaison de sources
        </h1>
        <p className="text-body text-muted-foreground">
          Superposez WID, INSEE et DGFiP pour un même indicateur. Chaque source mesure le patrimoine
          selon sa propre Convention : les courbes sont comparées côte à côte, jamais fusionnées en
          une seule série.
        </p>
      </header>

      {/* Controls */}
      <section
        aria-label="Filtres de comparaison"
        className="rounded-lg border border-border bg-secondary px-4 py-4 sm:px-5"
      >
        <div className="flex flex-wrap items-start gap-x-8 gap-y-5">
          <Field label="Indicateur" htmlFor="c-indicateur">
            <Select value={params.indicateur} onValueChange={(v) => update({ indicateur: v })}>
              <SelectTrigger
                className="w-52 pointer-coarse:min-h-11"
                aria-labelledby="c-indicateur"
              >
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {COMPARABLE_INDICATEURS.map((ind) => (
                  <SelectItem key={ind} value={ind}>
                    {indicateurMeta(ind).label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </Field>

          <Field label="Groupe" htmlFor="c-groupe">
            <Select
              value={activeGroupe}
              onValueChange={(v) => update({ groupe: v })}
              disabled={isGini}
            >
              <SelectTrigger className="w-48 pointer-coarse:min-h-11" aria-labelledby="c-groupe">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {groupeOptions.map((g) => (
                  <SelectItem key={g} value={g}>
                    {groupeLabel(g)}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </Field>

          <Field label="Sources superposées" htmlFor="c-sources">
            <ToggleGroup
              type="multiple"
              value={params.sources}
              onValueChange={(v) => update({ sources: v })}
              aria-labelledby="c-sources"
            >
              {(meta?.sources ?? []).map((s) => (
                <ToggleGroupItem
                  key={s}
                  value={s}
                  className="flex-col items-start gap-0 py-1.5 text-left pointer-coarse:min-h-11"
                >
                  <span className="text-sm leading-tight font-semibold">
                    {SOURCE_LABEL[s] ?? s}
                  </span>
                  <span className="text-label leading-tight font-normal text-muted-foreground">
                    {SOURCE_CONVENTION[s] ?? ""}
                  </span>
                </ToggleGroupItem>
              ))}
            </ToggleGroup>
          </Field>
        </div>
      </section>

      {/* The guard-rail banner: shapes are comparable, levels are not (ADR 0003). */}
      <div className="flex items-start gap-2.5 rounded-md border border-border bg-secondary px-4 py-3 text-sm text-foreground">
        <Info className="mt-0.5 size-4 shrink-0 text-primary" aria-hidden />
        <p className="leading-relaxed">
          <span className="font-semibold">Formes comparables, niveaux non comparables.</span> On
          compare l'allure des courbes (part détenue, indice de Gini), pas des montants : les unités
          (par adulte, par ménage, par foyer fiscal) ne sont pas interchangeables.
        </p>
      </div>

      <FigureFrame
        title={indicateurMeta(params.indicateur).label}
        subtitle={
          isGini
            ? "Indice de Gini du patrimoine, par source (0 = égalité, 1 = concentration maximale)."
            : `Part du patrimoine détenue par le groupe « ${groupeLabel(activeGroupe)} », par source.`
        }
        actions={drawn.length > 0 ? <ExportButtons targetRef={chartRef} stem={stem} /> : undefined}
        footer={
          lines.length > 0 ? (
            <div className="space-y-2">
              <p className="font-medium text-foreground">Conventions superposées</p>
              <ConventionLegend lines={lines} />
            </div>
          ) : undefined
        }
      >
        {body}
      </FigureFrame>
    </div>
  );
}
