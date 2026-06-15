// The Convention legend for the comparison overlay (jalon 5). Each entry shows
// the line's colour AND its dash pattern (a hue-free swatch) next to the source
// and its Convention (unité · concept), so an overlay is never read as one merged
// series — the guard rail, spelled out (Principle 1).
import type { ComparisonLine } from "@/lib/comparison";

function DashSwatch({ color, dash }: { color: string; dash: string }) {
  return (
    <svg
      width="28"
      height="10"
      viewBox="0 0 28 10"
      aria-hidden="true"
      role="presentation"
      className="shrink-0"
    >
      <line
        x1="1"
        y1="5"
        x2="27"
        y2="5"
        style={{ stroke: color }}
        strokeWidth="2.5"
        strokeDasharray={dash === "0" ? undefined : dash}
        strokeLinecap="round"
      />
    </svg>
  );
}

export default function ConventionLegend({ lines }: { lines: ComparisonLine[] }) {
  return (
    <ul className="flex flex-col gap-2.5">
      {lines.map((line) => (
        <li key={line.key} className="flex items-baseline gap-2.5 text-sm">
          <span className="relative top-[3px]">
            <DashSwatch color={line.color} dash={line.dash} />
          </span>
          <span className="min-w-0">
            <span className="font-semibold text-foreground">{line.convention}</span>
            {!line.hasData && (
              <span className="ml-1.5 text-muted-foreground">
                — aucune donnée sur cette période
              </span>
            )}
          </span>
        </li>
      ))}
    </ul>
  );
}
