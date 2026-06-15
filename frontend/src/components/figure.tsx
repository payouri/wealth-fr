// Shared building blocks for a chart figure: the frame (title + body +
// traceability footer) and the four states every figure must cover —
// loading, empty (valid 200, no rows), ambiguous (422), error.
import { AlertTriangle, Inbox, Info, Layers } from "lucide-react";
import type { ConventionChoice, Series } from "@/api/types";
import { Button } from "@/components/ui/button";
import { CONCEPT_LABEL, conventionLabel } from "@/lib/domain";

export function FigureFrame({
  title,
  subtitle,
  children,
  footer,
  actions,
}: {
  title: string;
  subtitle?: string;
  children: React.ReactNode;
  footer?: React.ReactNode;
  /** Low-emphasis controls (e.g. export) aligned to the right of the caption. */
  actions?: React.ReactNode;
}) {
  return (
    <figure className="rounded-lg border border-border bg-background">
      <figcaption className="flex items-start justify-between gap-4 border-b border-border px-5 pt-4 pb-3">
        <div className="min-w-0">
          <h2 className="font-serif text-headline font-semibold text-foreground">{title}</h2>
          {subtitle && <p className="mt-0.5 text-sm text-muted-foreground">{subtitle}</p>}
        </div>
        {actions && <div className="shrink-0 pt-0.5">{actions}</div>}
      </figcaption>
      <div className="px-3 py-4 sm:px-4">{children}</div>
      {footer && (
        <div className="border-t border-border px-5 py-2.5 text-label text-muted-foreground">
          {footer}
        </div>
      )}
    </figure>
  );
}

/** source · Convention · millésime · date d'extraction — always visible, never
 *  a hover afterthought (Principle 2: traceability is a feature). */
export function Traceability({ series }: { series: Series }) {
  const date = series.date_extraction
    ? new Date(series.date_extraction).toLocaleDateString("fr-FR", {
        day: "2-digit",
        month: "long",
        year: "numeric",
      })
    : null;
  return (
    <p style={{ fontFeatureSettings: '"tnum" 1' }}>
      <span className="font-medium text-foreground">
        {conventionLabel(
          String(series.query.source ?? ""),
          series.unite,
          series.concept_patrimoine,
        )}
      </span>
      {series.millesime_source && <> · millésime {series.millesime_source}</>}
      {date && <> · extrait le {date}</>}
    </p>
  );
}

function StatePanel({
  icon,
  title,
  children,
  height = 320,
}: {
  icon: React.ReactNode;
  title: string;
  children?: React.ReactNode;
  height?: number;
}) {
  return (
    <div
      className="flex flex-col items-center justify-center gap-2 px-6 text-center"
      style={{ minHeight: height }}
    >
      <span className="text-muted-foreground" aria-hidden>
        {icon}
      </span>
      <p className="font-medium text-foreground">{title}</p>
      {children && <div className="max-w-md text-sm text-muted-foreground">{children}</div>}
    </div>
  );
}

/** A general-purpose figure state (info / neutral) for cases the four canonical
 *  panels below don't cover — e.g. "pick a source" or a calm ambiguity notice. */
export function StateNotice({
  title,
  children,
  tone = "info",
  height,
}: {
  title: string;
  children?: React.ReactNode;
  tone?: "info" | "neutral";
  height?: number;
}) {
  return (
    <StatePanel
      icon={
        tone === "info" ? <Info className="size-6 text-primary" /> : <Inbox className="size-6" />
      }
      title={title}
      height={height}
    >
      {children}
    </StatePanel>
  );
}

export function FigureSkeleton({ height = 320 }: { height?: number }) {
  return (
    <div
      className="motion-safe:animate-pulse rounded-md bg-secondary"
      style={{ height }}
      role="status"
      aria-label="Chargement du graphique"
    />
  );
}

export function EmptyState({ height }: { height?: number }) {
  return (
    <StatePanel
      icon={<Inbox className="size-6" />}
      title="Aucune donnée pour ce choix"
      height={height}
    >
      Cette combinaison source / indicateur / groupe n'existe pas dans le jeu de données. Essayez un
      autre groupe ou une autre source.
    </StatePanel>
  );
}

export function ErrorState({ onRetry, height }: { onRetry: () => void; height?: number }) {
  return (
    <StatePanel
      icon={<AlertTriangle className="size-6 text-destructive" />}
      title="Le chargement a échoué"
      height={height}
    >
      <p>Impossible de joindre l'API des séries.</p>
      <Button variant="secondary" size="sm" className="mt-3" onClick={onRetry}>
        Réessayer
      </Button>
    </StatePanel>
  );
}

/** The 422 path: the query still spans more than one Convention. We never merge
 *  or guess (CONTEXT.md guard rail) — we ask the reader to pick one. */
export function ConventionPrompt({
  choices,
  onPick,
  height,
}: {
  choices: ConventionChoice[];
  onPick: (concept: string) => void;
  height?: number;
}) {
  return (
    <StatePanel
      icon={<Layers className="size-6 text-primary" />}
      title="Choisir une Convention"
      height={height}
    >
      <p>
        Cette source couvre plusieurs Conventions de mesure qui ne sont pas comparables entre elles.
        Choisissez celle à afficher.
      </p>
      <div className="mt-4 flex flex-wrap justify-center gap-2">
        {choices.map((c) => (
          <Button
            key={c.concept_patrimoine}
            variant="secondary"
            size="sm"
            onClick={() => onPick(c.concept_patrimoine)}
          >
            {CONCEPT_LABEL[c.concept_patrimoine] ?? c.concept_patrimoine}
          </Button>
        ))}
      </div>
    </StatePanel>
  );
}
