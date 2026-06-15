import { useQueries, useQuery } from "@tanstack/react-query";
import { lazy, Suspense, useEffect, useRef, useState } from "react";
import { ApiError, api } from "@/api/client";
import type { ConventionChoice, Series } from "@/api/types";
import ExportButtons from "@/components/ExportButtons";
import FilterBar from "@/components/FilterBar";
import {
  ConventionPrompt,
  EmptyState,
  ErrorState,
  FigureFrame,
  FigureSkeleton,
  Traceability,
} from "@/components/figure";
import type { ChartSeries } from "@/components/SeriesChart";
import { useDashboardParams } from "@/hooks/useDashboardParams";

// Recharts is heavy; load the chart surface in its own chunk so the shell,
// router and filter bar paint without it (the skeleton covers the gap).
const SeriesChart = lazy(() => import("@/components/SeriesChart"));

import {
  GROUPE_ENCODING,
  groupeLabel,
  indicateurMeta,
  SHARE_GROUPES,
  SOURCE_ENCODING,
  SOURCE_LABEL,
  validComboForSource,
} from "@/lib/domain";
import { exportStem } from "@/lib/exportChart";

type SeriesResult = {
  data?: Series;
  error: Error | null;
  isPending: boolean;
  isError: boolean;
};

function ambiguousFrom(results: SeriesResult[]): ConventionChoice[] | null {
  for (const r of results) {
    if (r.error instanceof ApiError && r.error.ambiguousConvention) {
      return r.error.ambiguousConvention.choices;
    }
  }
  return null;
}

function hardError(results: SeriesResult[]): boolean {
  return results.some(
    (r) => r.isError && !(r.error instanceof ApiError && r.error.ambiguousConvention),
  );
}

interface ChartFigureProps {
  title: string;
  subtitle?: string;
  axisLabel: string;
  results: SeriesResult[];
  seriesFor: (s: Series) => { key: string; label: string; color: string; dash: string };
  emphasizeKey?: string | null;
  anneeMin: number;
  anneeMax: number;
  conceptPinned: boolean;
  onPick: (concept: string) => void;
  onRetry: () => void;
  height?: number;
  /** When set, render CSV/PNG export controls once the figure has data (jalon 9). */
  exportProps?: { stem: string; csvUrl?: string };
}

function ChartFigure({
  title,
  subtitle,
  axisLabel,
  results,
  seriesFor,
  emphasizeKey,
  anneeMin,
  anneeMax,
  conceptPinned,
  onPick,
  onRetry,
  height = 320,
  exportProps,
}: ChartFigureProps) {
  const chartRef = useRef<HTMLDivElement>(null);
  const pending = results.length === 0 || results.some((r) => r.isPending);
  const choices = ambiguousFrom(results);
  const successes = results.flatMap((r) => (r.data ? [r.data] : []));
  const withPoints = successes.filter((s) => s.points.length > 0);
  const representative = withPoints[0] ?? successes[0];

  let body: React.ReactNode;
  if (pending) {
    body = <FigureSkeleton height={height} />;
  } else if (choices && !conceptPinned) {
    body = <ConventionPrompt choices={choices} onPick={onPick} height={height} />;
  } else if (hardError(results)) {
    body = <ErrorState onRetry={onRetry} height={height} />;
  } else if (withPoints.length === 0) {
    body = <EmptyState height={height} />;
  } else {
    const chartSeries: ChartSeries[] = withPoints.map((s) => {
      const meta = seriesFor(s);
      return {
        ...meta,
        points: s.points,
        emphasized: emphasizeKey != null && emphasizeKey === meta.key,
        dimmed: emphasizeKey != null && emphasizeKey !== meta.key,
      };
    });
    body = (
      <Suspense fallback={<FigureSkeleton height={height} />}>
        <SeriesChart
          series={chartSeries}
          ruptures={representative?.ruptures ?? []}
          uniteValeur={representative?.unite_valeur ?? ""}
          axisLabel={axisLabel}
          anneeMin={anneeMin}
          anneeMax={anneeMax}
          height={height}
        />
      </Suspense>
    );
  }

  // Traceability belongs to a figure that actually shows data — not to an
  // empty/loading/prompt state (it would dangle a blank Convention).
  const hasData = withPoints.length > 0;
  return (
    <FigureFrame
      title={title}
      subtitle={subtitle}
      actions={
        hasData && exportProps ? (
          <ExportButtons targetRef={chartRef} stem={exportProps.stem} csvUrl={exportProps.csvUrl} />
        ) : undefined
      }
      footer={hasData && representative ? <Traceability series={representative} /> : undefined}
    >
      <div ref={chartRef}>{body}</div>
    </FigureFrame>
  );
}

export default function Dashboard() {
  const [params, update] = useDashboardParams();
  const metaQ = useQuery({
    queryKey: ["meta"],
    queryFn: api.meta,
    staleTime: Number.POSITIVE_INFINITY,
  });
  const meta = metaQ.data;

  // Guard hand-typed / deep-linked URLs (and any stale state): if the current
  // (indicateur, groupe) is one this source never measures, snap to a valid combo
  // so a curve always appears. `replace` keeps the back button honest.
  useEffect(() => {
    if (!meta) return;
    const fixed = validComboForSource(
      meta.availability,
      params.source,
      params.indicateur,
      params.groupe,
    );
    if (fixed.indicateur !== params.indicateur || fixed.groupe !== params.groupe) {
      update(fixed, { replace: true });
    }
  }, [meta, params.source, params.indicateur, params.groupe, update]);

  const indMeta = indicateurMeta(params.indicateur);
  const isShare = indMeta.isShare;
  const eurosInert = !indMeta.isLevel;
  const eurosFlag = indMeta.isLevel && params.euros;
  const anneeMin = meta?.annee_min ?? 2000;
  const anneeMax = meta?.annee_max ?? 2024;
  const conceptParam = params.concept || undefined;

  // A source measures only some (indicateur, groupe) combos; the non-share fallback
  // must come from this source's groupes, not the global union (else it lands on a
  // groupe the source never measured and the chart goes silently empty).
  const sourceGroupes = meta?.availability?.[params.source]?.[params.indicateur] ?? [];
  const activeGroupe = isShare ? "" : params.groupe || sourceGroupes[0] || "";
  const primaryGroupes = isShare ? [...SHARE_GROUPES] : activeGroupe ? [activeGroupe] : [];

  const primaryQueries = useQueries({
    queries: (meta ? primaryGroupes : []).map((g) => ({
      queryKey: [
        "series",
        params.source,
        params.indicateur,
        g,
        conceptParam ?? null,
        eurosFlag,
        anneeMin,
      ],
      queryFn: () =>
        api.series({
          source: params.source,
          indicateur: params.indicateur,
          groupe: g,
          concept: conceptParam,
          euros_constants: eurosFlag,
          annee_min: anneeMin,
        }),
    })),
  });

  const giniQ = useQuery({
    queryKey: ["series", params.source, "gini", "ensemble", conceptParam ?? null, anneeMin],
    queryFn: () =>
      api.series({
        source: params.source,
        indicateur: "gini",
        groupe: "ensemble",
        concept: conceptParam,
        annee_min: anneeMin,
      }),
    enabled: !!meta && isShare,
  });

  // Remember which sources span multiple Conventions, so the bar keeps offering
  // the switcher even after a concept is pinned (the 422 then stops firing).
  const [knownChoices, setKnownChoices] = useState<Record<string, ConventionChoice[]>>({});
  const observed = ambiguousFrom(primaryQueries);
  useEffect(() => {
    if (!observed) return;
    setKnownChoices((prev) =>
      prev[params.source] ? prev : { ...prev, [params.source]: observed },
    );
  }, [observed, params.source]);

  const conceptChoices = knownChoices[params.source] ?? observed ?? null;
  const representative = primaryQueries.flatMap((r) => (r.data ? [r.data] : []))[0];

  if (metaQ.isPending) {
    return (
      <div className="space-y-6">
        <FigureSkeleton height={92} />
        <FigureSkeleton height={360} />
      </div>
    );
  }
  if (metaQ.isError || !meta) {
    return (
      <FigureFrame title="Tableau de bord">
        <ErrorState onRetry={() => metaQ.refetch()} />
      </FigureFrame>
    );
  }

  // CSV is single-series by design (no batch endpoint): export the focused
  // groupe, defaulting to the headline top1 on an unfocused shares view. PNG
  // captures the whole figure regardless.
  const exportGroupe = isShare ? params.groupe || "top1" : activeGroupe;
  const exportProps = {
    stem: exportStem([
      params.source,
      params.indicateur,
      exportGroupe,
      eurosFlag ? "euros_constants" : undefined,
    ]),
    csvUrl: api.exportCsvUrl({
      source: params.source,
      indicateur: params.indicateur,
      groupe: exportGroupe,
      concept: conceptParam,
      euros_constants: eurosFlag,
      annee_min: anneeMin,
    }),
  };

  const primaryTitle = isShare ? "Parts du patrimoine détenues par le sommet" : indMeta.label;
  const primarySubtitle = isShare
    ? "Part du patrimoine net total détenue par chaque fraction, en %."
    : indMeta.axis;

  return (
    <div className="space-y-6">
      <FilterBar
        meta={meta}
        params={params}
        update={update}
        conceptChoices={conceptChoices}
        resolved={
          representative
            ? { unite: representative.unite, concept: representative.concept_patrimoine }
            : null
        }
        eurosInert={eurosInert}
      />

      <ChartFigure
        title={primaryTitle}
        subtitle={primarySubtitle}
        axisLabel={isShare ? "% du patrimoine" : indMeta.axis}
        results={primaryQueries}
        anneeMin={anneeMin}
        anneeMax={anneeMax}
        conceptPinned={!!params.concept}
        emphasizeKey={isShare && params.groupe ? params.groupe : null}
        exportProps={exportProps}
        onPick={(concept) => update({ concept })}
        onRetry={() => {
          for (const q of primaryQueries) q.refetch();
        }}
        height={360}
        seriesFor={(s) => {
          const g = String(s.query.groupe ?? "");
          if (isShare) {
            const enc = GROUPE_ENCODING[g] ?? SOURCE_ENCODING[params.source];
            return { key: g, label: groupeLabel(g), color: enc.color, dash: enc.dash };
          }
          const enc = SOURCE_ENCODING[params.source] ?? GROUPE_ENCODING.top10;
          return {
            key: g || params.source,
            label: SOURCE_LABEL[params.source] ?? params.source,
            color: enc.color,
            dash: enc.dash,
          };
        }}
      />

      {isShare && (
        <ChartFigure
          title="Indice de Gini du patrimoine"
          subtitle="Inégalité globale de la distribution : 0 = égalité parfaite, 1 = concentration maximale."
          axisLabel="indice (0–1)"
          results={[giniQ]}
          anneeMin={anneeMin}
          anneeMax={anneeMax}
          conceptPinned={!!params.concept}
          onPick={(concept) => update({ concept })}
          onRetry={() => giniQ.refetch()}
          height={260}
          seriesFor={() => {
            const enc = SOURCE_ENCODING[params.source] ?? GROUPE_ENCODING.top10;
            return {
              key: "gini",
              label: SOURCE_LABEL[params.source] ?? params.source,
              color: enc.color,
              dash: enc.dash,
            };
          }}
        />
      )}
    </div>
  );
}
