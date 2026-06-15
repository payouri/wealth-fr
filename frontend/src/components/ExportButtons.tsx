// Export controls for a figure (jalon 9): a server-streamed CSV of the resolved
// rows and a client-side PNG of the chart as drawn. Low-emphasis secondary
// actions — they serve the data, they don't compete with it (Quiet Chrome Rule).
import { FileDown, ImageDown } from "lucide-react";
import { type RefObject, useState } from "react";
import { Button } from "@/components/ui/button";
import { exportChartPng } from "@/lib/exportChart";

interface ExportButtonsProps {
  /** Element wrapping the chart SVG (for the PNG raster). */
  targetRef: RefObject<HTMLElement | null>;
  /** File stem shared by both downloads, e.g. "WID_part_patrimoine_top1". */
  stem: string;
  /** Direct link to /api/export.csv; omit to hide the CSV action (e.g. on an
   *  overlay that has no single-source CSV equivalent). */
  csvUrl?: string;
}

export default function ExportButtons({ targetRef, stem, csvUrl }: ExportButtonsProps) {
  const [busy, setBusy] = useState(false);
  const [failed, setFailed] = useState(false);

  async function onPng() {
    const el = targetRef.current;
    if (!el) return;
    setFailed(false);
    setBusy(true);
    try {
      await exportChartPng(el, `${stem}.png`);
    } catch {
      setFailed(true);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex items-center gap-2">
      {csvUrl && (
        <Button asChild variant="secondary" size="sm" className="pointer-coarse:min-h-11">
          <a href={csvUrl} download={`${stem}.csv`}>
            <FileDown aria-hidden />
            CSV
          </a>
        </Button>
      )}
      <Button
        variant="secondary"
        size="sm"
        className="pointer-coarse:min-h-11"
        onClick={onPng}
        disabled={busy}
      >
        <ImageDown aria-hidden />
        {busy ? "Export…" : "PNG"}
      </Button>
      {failed && (
        <span role="alert" className="text-label text-destructive">
          Export impossible
        </span>
      )}
    </div>
  );
}
