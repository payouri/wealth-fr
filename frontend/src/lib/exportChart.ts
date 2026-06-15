// Client-side export (jalon 9): a PNG of the current chart, and a tiny helper to
// trigger a file download from a URL (the CSV link). The PNG path serialises the
// Recharts SVG and rasterises it onto a paper-coloured canvas, so the exported
// figure matches the on-screen one (honest charts, same encoding).

/** Build a safe, descriptive file stem from filter parts: "WID_part_patrimoine_top1". */
export function exportStem(parts: (string | undefined)[]): string {
  const cleaned = parts
    .filter((p): p is string => !!p && p.length > 0)
    .map((p) => p.replace(/[^\w.-]+/g, "-"));
  return cleaned.length ? cleaned.join("_") : "export";
}

/** Navigate to a URL as a download (used for the server-streamed CSV). */
export function downloadUrl(url: string, filename: string): void {
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
}

// The chart inherits its fonts from the page; a serialised SVG loses that CSS, so
// pin the family explicitly before rasterising.
const FONT_STACK = "'Source Sans 3', system-ui, sans-serif";
const PAPER = "#fbf9f4"; // warm-paper fallback for the exported background

/** Rasterise the first <svg> inside `container` to a PNG and download it. */
export async function exportChartPng(
  container: HTMLElement,
  filename: string,
  scale = 2,
): Promise<void> {
  const svg = container.querySelector("svg");
  if (!svg) throw new Error("No chart SVG found to export.");

  const rect = svg.getBoundingClientRect();
  const width = Math.max(1, Math.round(rect.width));
  const height = Math.max(1, Math.round(rect.height));

  const clone = svg.cloneNode(true) as SVGSVGElement;
  clone.setAttribute("width", String(width));
  clone.setAttribute("height", String(height));
  clone.setAttribute("xmlns", "http://www.w3.org/2000/svg");
  clone.style.fontFamily = FONT_STACK;

  const serialized = new XMLSerializer().serializeToString(clone);
  const svgUrl = `data:image/svg+xml;charset=utf-8,${encodeURIComponent(serialized)}`;

  const image = new Image();
  image.crossOrigin = "anonymous";
  await new Promise<void>((resolve, reject) => {
    image.onload = () => resolve();
    image.onerror = () => reject(new Error("Failed to load the chart image for export."));
    image.src = svgUrl;
  });

  const canvas = document.createElement("canvas");
  canvas.width = width * scale;
  canvas.height = height * scale;
  const ctx = canvas.getContext("2d");
  if (!ctx) throw new Error("Canvas 2D context unavailable.");
  ctx.scale(scale, scale);
  ctx.fillStyle = PAPER;
  ctx.fillRect(0, 0, width, height);
  ctx.drawImage(image, 0, 0, width, height);

  const blob = await new Promise<Blob | null>((resolve) => canvas.toBlob(resolve, "image/png"));
  if (!blob) throw new Error("Failed to encode the PNG.");
  const objectUrl = URL.createObjectURL(blob);
  downloadUrl(objectUrl, filename);
  URL.revokeObjectURL(objectUrl);
}
