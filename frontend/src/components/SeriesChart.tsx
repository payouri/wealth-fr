import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { Point, Rupture } from "@/api/types";
import { usePrefersReducedMotion } from "@/hooks/usePrefersReducedMotion";
import { formatTick, formatValue } from "@/lib/domain";

export interface ChartSeries {
  key: string;
  label: string; // direct end-of-line label (the non-hue cue alongside colour + dash)
  points: Point[];
  color: string; // CSS var, e.g. var(--color-chart-1)
  dash: string; // strokeDasharray; the hue-free redundant cue
  emphasized?: boolean; // focused groupe — full weight
  dimmed?: boolean; // a sibling is focused — recede
}

interface SeriesChartProps {
  series: ChartSeries[];
  ruptures: Rupture[];
  uniteValeur: string;
  axisLabel: string;
  anneeMin: number;
  anneeMax: number;
  height?: number;
}

type Row = { annee: number } & Record<string, number | null>;

function mergeByYear(series: ChartSeries[]): Row[] {
  const byYear = new Map<number, Row>();
  for (const s of series) {
    for (const p of s.points) {
      let row = byYear.get(p.annee);
      if (!row) {
        row = { annee: p.annee };
        byYear.set(p.annee, row);
      }
      row[s.key] = p.valeur;
    }
  }
  return [...byYear.values()].sort((a, b) => a.annee - b.annee);
}

interface LabelPointProps {
  x?: number | string;
  y?: number | string;
  index?: number;
}

// SVG presentation attributes (stroke/fill) don't resolve `var(--x)` reliably,
// so we read the token's computed value and hand Recharts a concrete colour.
function resolveColor(value: string): string {
  const match = /^var\((--[\w-]+)\)$/.exec(value.trim());
  if (!match || typeof window === "undefined") return value;
  return getComputedStyle(document.documentElement).getPropertyValue(match[1]).trim() || value;
}

export default function SeriesChart({
  series,
  ruptures,
  uniteValeur,
  axisLabel,
  anneeMin,
  anneeMax,
  height = 320,
}: SeriesChartProps) {
  const reducedMotion = usePrefersReducedMotion();
  const data = mergeByYear(series);
  // Last defined index per series — where its direct label is drawn.
  const lastIndex = new Map<string, number>();
  series.forEach((s) => {
    for (let i = data.length - 1; i >= 0; i--) {
      if (data[i][s.key] != null) {
        lastIndex.set(s.key, i);
        break;
      }
    }
  });

  const tnum = { fontFeatureSettings: '"tnum" 1' } as const;
  const ink = resolveColor("var(--color-muted-foreground)");
  const hairline = resolveColor("var(--color-border)");
  const ruptureColor = resolveColor("var(--color-rupture)");

  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={data} margin={{ top: 16, right: 124, bottom: 8, left: 8 }}>
        <CartesianGrid stroke={hairline} strokeOpacity={0.7} vertical={false} />
        <XAxis
          dataKey="annee"
          type="number"
          domain={[anneeMin, anneeMax]}
          allowDecimals={false}
          tickCount={Math.min(7, anneeMax - anneeMin + 1)}
          tick={{ fill: ink, fontSize: 12, style: tnum }}
          tickLine={{ stroke: hairline }}
          axisLine={{ stroke: hairline }}
          tickMargin={8}
        />
        <YAxis
          // Honest origin: the value axis is never truncated (Principle 5).
          domain={uniteValeur === "indice" ? [0, 1] : [0, "auto"]}
          tickFormatter={(v: number) => formatTick(v, uniteValeur)}
          tick={{ fill: ink, fontSize: 12, style: tnum }}
          tickLine={false}
          axisLine={false}
          width={52}
          label={{
            value: axisLabel,
            angle: -90,
            position: "insideLeft",
            style: {
              fill: ink,
              fontSize: 12,
              fontWeight: 500,
              textAnchor: "middle",
            },
          }}
        />
        <Tooltip
          isAnimationActive={false}
          cursor={{ stroke: hairline, strokeWidth: 1 }}
          content={({ active, payload, label }) => {
            if (!active || !payload?.length) return null;
            return (
              <div className="rounded-md border border-border bg-popover px-3 py-2 text-sm shadow-[0_8px_24px_oklch(0.26_0.015_72/0.12)]">
                <p className="mb-1 font-semibold text-foreground" style={tnum}>
                  {label}
                </p>
                <ul className="space-y-0.5">
                  {payload.map((entry) => {
                    const s = series.find((x) => x.key === entry.dataKey);
                    return (
                      <li
                        key={String(entry.dataKey)}
                        className="flex items-center justify-between gap-4"
                      >
                        <span className="flex items-center gap-1.5 text-muted-foreground">
                          <span
                            aria-hidden
                            className="inline-block h-0.5 w-3.5 rounded-full"
                            style={{
                              backgroundColor: resolveColor(s?.color ?? String(entry.color)),
                            }}
                          />
                          {s?.label ?? String(entry.dataKey)}
                        </span>
                        <span className="font-medium text-foreground" style={tnum}>
                          {formatValue(Number(entry.value), uniteValeur)}
                        </span>
                      </li>
                    );
                  })}
                </ul>
              </div>
            );
          }}
        />
        {ruptures.map((r) => (
          <ReferenceLine
            key={`${r.annee}-${r.label}`}
            x={r.annee}
            // Calm amber, never alarm-red: a methodological seam, not a warning.
            stroke={ruptureColor}
            strokeDasharray="5 4"
            strokeWidth={1.5}
            label={{
              value: r.label,
              position: "insideTopRight",
              fill: ruptureColor,
              fontSize: 11,
              fontWeight: 600,
            }}
          />
        ))}
        {series.map((s) => {
          const last = lastIndex.get(s.key);
          const opacity = s.dimmed ? 0.32 : 1;
          const color = resolveColor(s.color);
          return (
            <Line
              key={s.key}
              dataKey={s.key}
              type="monotone"
              stroke={color}
              strokeWidth={s.emphasized ? 3 : 2}
              strokeDasharray={s.dash === "0" ? undefined : s.dash}
              strokeOpacity={opacity}
              // Sparse survey series (1–2 points) would be invisible as a line:
              // show the observations as dots so they remain legible.
              dot={s.points.length <= 2 ? { r: 3, fill: color, strokeWidth: 0 } : false}
              activeDot={{ r: 4, strokeWidth: 0 }}
              connectNulls={false}
              isAnimationActive={!reducedMotion}
              animationDuration={reducedMotion ? 0 : 600}
              label={(props: LabelPointProps) => {
                const { index } = props;
                const x = Number(props.x);
                const y = Number(props.y);
                if (index !== last || Number.isNaN(x) || Number.isNaN(y)) {
                  return <g key={`${s.key}-${index}`} />;
                }
                return (
                  <text
                    key={`${s.key}-label`}
                    x={x + 8}
                    y={y}
                    dy={4}
                    fill={color}
                    fillOpacity={opacity}
                    fontSize={12}
                    fontWeight={s.emphasized ? 700 : 600}
                    style={tnum}
                  >
                    {s.label}
                  </text>
                );
              }}
            />
          );
        })}
      </LineChart>
    </ResponsiveContainer>
  );
}
