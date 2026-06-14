import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { Series } from "../api/types";

// STUB: renders one or more series as lines, with rupture markers (e.g. 2018).
// Each line is labelled with its Convention so sources are never read as merged.
export default function SeriesChart({ series }: { series: Series[] }) {
  return (
    <ResponsiveContainer width="100%" height={360}>
      <LineChart>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="annee" type="number" domain={["dataMin", "dataMax"]} />
        <YAxis />
        <Tooltip />
        <Legend />
        {series.map((s) => (
          <Line
            key={`${s.millesime_source}-${s.unite}-${s.concept_patrimoine}-${s.unite_valeur}`}
            data={s.points}
            dataKey="valeur"
            name={`${s.query.source} — ${s.unite}/${s.concept_patrimoine} (${s.unite_valeur})`}
            dot={false}
          />
        ))}
        {series
          .flatMap((s) => s.ruptures)
          .map((r) => (
            <ReferenceLine
              key={`${r.annee}-${r.label}`}
              x={r.annee}
              stroke="#dc2626"
              label={r.label}
            />
          ))}
      </LineChart>
    </ResponsiveContainer>
  );
}
